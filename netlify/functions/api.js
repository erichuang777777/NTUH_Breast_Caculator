const fs = require('fs');
const path = require('path');
const { calculateScores, stagingScore } = require('./_shared/calculators');

const API_DIR = path.resolve(__dirname, '../../data/api');
const I18N_CACHE_DIR = path.resolve(__dirname, '../../data/i18n_cache');
const FEEDBACK_REPO = process.env.FEEDBACK_GITHUB_REPO || 'erichuang777777/NTUH_Breast_Caculator';
const FEEDBACK_LABEL = process.env.FEEDBACK_GITHUB_LABEL || 'feedback-board';
const OLLAMA_HOST = (process.env.OLLAMA_HOST || 'https://ollama.com').replace(/\/+$/, '');
const OLLAMA_MODEL = process.env.OLLAMA_MODEL || 'gpt-oss:120b';
const OLLAMA_TIMEOUT_MS = Number(process.env.OLLAMA_TIMEOUT_MS || process.env.OLLAMA_TIMEOUT_SECONDS || 90000);
const PATIENT_PATCH_FIELDS = new Set([
  'age', 'menopause', 'side', 'symptoms', 'ecog', 'dm', 'htn', 'cad', 'size', 'tumor_kind',
  'grade', 'cT', 'cN', 'cM', 'pT', 'pN', 'pM', 'er', 'pr', 'her2', 'her2_ihc', 'her2_fish',
  'ki67', 'oncotype_rs', 'nodes_pos', 'nodes_total', 'sln_pos', 'sln_total', 'aln_pos',
  'aln_total', 'pni', 'lvi', 'margin_involved', 'post_nac_response', 'brca', 'pdl1',
  'pik3ca', 'esr1', 'civic_variant', 'height', 'weight', 'scr', 'breast_surgery',
  'axillary_surgery',
]);
const AGENT_SYSTEM_PROMPT = [
  '你是 OncoBreast Calculator 的臨床工作區 copilot，面向醫師與護理師。',
  '請用繁體中文，回答要精簡、臨床可讀。',
  '你的主要任務有兩種：1. 使用者給 free text 時，抽取欄位並回傳 patient_patch 供前端寫入；2. 使用者問問題時，優先從 system_context 的本系統資料與計算結果回答。',
  '你只能使用 system_context、網站內資料庫、網站內計算器與使用者提供的文字；不可聲稱已查詢外部網站、最新 guideline、文獻或院外資料。',
  '本工具定位為 information retrieval 與網站內工具調用輔助，不是臨床推論引擎；若問題需要外部 guideline、正式治療建議或醫囑，必須說明超出本系統邊界。',
  '回答前你已取得 system_context，裡面是本網站工具已經先執行的結果，包括欄位抽取、分期、風險分數、藥物查詢與配方查詢。回答時要以這些結果為主，不要假裝沒有調用工具。',
  '若 system_context.drug_matches 或 formulation_matches 有資料，不能回答「系統沒有資料」；應列出查到的藥名、商品名、stage、給付/事審重點。',
  '若使用者詢問藥物、價格、給付或適應症，但 system_context.drug_matches 與 formulation_matches 都沒有資料，必須回答「本網站資料庫內目前沒有查到」，不可用模型記憶補外部藥物資訊。',
  '此時還必須明確寫出「無法根據網站資料提供用途、價格或給付資訊」。',
  '若 system_context.support_resources 有資料，回答病患可尋求幫助時只能列出這些支援資源、申請方式、窗口與文件；若沒有資料，請說明網站內尚未建置該資源。',
  '回答 support_resources 時必須逐項列出 system_context.support_resources 的 exact title，不可只用泛稱。',
  '藥物回答若 drug_matches 有 line_label，必須列出該 line_label；若 indication 不是乳癌，仍需說明資料列線別並註明目前未列乳癌適應症。',
  '若使用者問價錢、費用、price 或 cost，必須從 system_context 的 nhi_price、price_unit、formulation_matches 列出可查到的價格與單位；沒有價格才說未列價格。',
  '若使用者問分期，必須優先引用 system_context.staging.ajcc_v8.selected，並說明使用 clinical 或 pathologic basis；不要自行改寫成其他期別。',
  '若 system_context.staging.stageability_note 存在，代表本系統簡化 AJCC 計算器不支援或不適用該 TNM，必須回答「無法判定」或「不適用」，不可自行推論期別。',
  '若使用者問 CTS5/IHC4/NPI/Magee/PEPI/PREDICT/Oncotype 或 risk score，必須引用 system_context.risk_scores 中可得的分數；若缺欄位，必須引用 system_context.missing_fields 列出缺少欄位。',
  '若 system_context.missing_fields 非空，回答中必須清楚列出缺少欄位；不能假裝可完整計算。',
  '若 system_context.context_conflicts 非空，表示右側輸入文字與左側 workspace patient context 不一致；必須先列出衝突欄位與兩邊數值。預設以 workspace patient context 計算，不可默默改用右側文字覆蓋。',
  '若 answer_hints 要求 echo patient_context TNM，回答需包含該 TNM 字串，例如 T3N1M0。',
  'Perjeta/Pertuzumab 靜脈製劑與 Phesgo 皮下注射複方必須分開說明，不可把 Phesgo 的自費狀態套到 Perjeta/Pertuzumab。',
  '若 system_context.answer_hints 有提醒，必須逐條遵守；若提醒要求特定關鍵字或資料庫 title，回答中必須出現。',
  '一般自然語言問題要直接回答，不要自動打開工具。',
  '只有當使用者明確要求「打開、開啟、呼叫、調用、切到、open、show」某個工具時，才從 tool_registry 選 tool_id；其他情況 tool_id 必須是空字串。',
  'patient_patch 只能使用這些欄位：age, menopause, side, symptoms, ecog, dm, htn, cad, size, tumor_kind, grade, cT, cN, cM, pT, pN, pM, er, pr, her2, her2_ihc, her2_fish, ki67, oncotype_rs, nodes_pos, nodes_total, sln_pos, sln_total, aln_pos, aln_total, pni, lvi, margin_involved, post_nac_response, brca, pdl1, pik3ca, esr1, civic_variant, height, weight, scr, breast_surgery, axillary_surgery。',
  '若只是回答問題，不需要 patient_patch；若抽取欄位有不確定，reply 要說需要人工確認。',
  '回傳 patient_patch 時，不要說已更新或已寫入；只能說已抓到候選欄位，請使用者確認後套用。',
  '回答不能取代醫師判斷、正式 guideline、院內政策或健保事前審查。',
  '邊界：不要給最終醫囑、不要保證健保一定給付、不要編造 guideline 或資料庫中沒有的內容、不要處理或要求姓名/身分證/病歷號等可識別資料。',
  '若使用者要正式治療決策，需提醒仍要依完整病理、病期、治療線別、院內政策與事前審查確認。',
  '若資訊不足，先列出缺少欄位。',
  '請只輸出 JSON，格式為 {"reply":"...", "tool_id":"", "patient_patch":{}, "citations":[]}。',
  '不要輸出 Markdown，不要使用 ``` code fence。',
].join('\n');

function json(statusCode, body, extraHeaders = {}) {
  return {
    statusCode,
    headers: {
      'content-type': 'application/json; charset=utf-8',
      'access-control-allow-origin': '*',
      'access-control-allow-methods': 'GET,POST,OPTIONS',
      'access-control-allow-headers': 'content-type, authorization, x-contact-email, x-client-app',
      ...extraHeaders,
    },
    body: JSON.stringify(body),
  };
}

function readJson(name) {
  return JSON.parse(fs.readFileSync(path.join(API_DIR, `${name}.json`), 'utf8'));
}

function readI18nCache(lang) {
  const safe = String(lang || '').toLowerCase().replace(/[^a-z]/g, '') || 'en';
  const file = path.join(I18N_CACHE_DIR, `${safe}.json`);
  if (!fs.existsSync(file)) return {};
  try {
    const parsed = JSON.parse(fs.readFileSync(file, 'utf8'));
    return parsed && typeof parsed === 'object' ? parsed : {};
  } catch (err) {
    return {};
  }
}

function bodyJson(event) {
  if (!event.body) return {};
  try {
    return JSON.parse(event.isBase64Encoded ? Buffer.from(event.body, 'base64').toString('utf8') : event.body);
  } catch (err) {
    return null;
  }
}

function sanitizeFeedbackText(value, maxLength) {
  return String(value || '').replace(/[\u0000-\u0008\u000b\u000c\u000e-\u001f]/g, '').trim().slice(0, maxLength);
}

function parseAgentJsonText(text) {
  const raw = String(text || '').trim();
  if (!raw) return {};
  try {
    return JSON.parse(raw);
  } catch (err) {
    const match = raw.match(/\{[\s\S]*\}/);
    if (!match) return { reply: raw };
    try {
      return JSON.parse(match[0]);
    } catch (innerErr) {
      return { reply: raw };
    }
  }
}

function sanitizePatientPatch(value) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return {};
  const patch = {};
  for (const [key, raw] of Object.entries(value)) {
    if (!PATIENT_PATCH_FIELDS.has(key)) continue;
    if (raw === undefined || raw === null || raw === '') continue;
    patch[key] = String(raw).slice(0, 120);
  }
  return patch;
}

function normalizeOllamaModel(value) {
  const raw = String(value || '').trim();
  if (!raw) return OLLAMA_MODEL;
  return /^[A-Za-z0-9._:/+-]{1,120}$/.test(raw) ? raw : OLLAMA_MODEL;
}

function agentQuestionIntents(message) {
  const text = String(message || '').toLowerCase();
  const checks = [
    ['price', ['價錢', '價格', '費用', '多少錢', 'price', 'cost', '自費', '健保價']],
    ['drug_indication', ['藥', 'drug', '用藥', '適應症', '給付', '健保', '事前', '事審', '可用', '可以用', 'regimen', '配方']],
    ['staging', ['分期', 'stage', 'ajcc', 'ct', 'cn', 'cm', 'pt', 'pn', 'pm']],
    ['risk_scores', ['predict', 'cts5', 'ihc4', 'pepi', 'npi', 'magee', 'oncotype', '分數', 'score', '風險']],
  ];
  const intents = [];
  for (const [intent, words] of checks) {
    if (words.some(w => text.includes(w))) intents.push(intent);
  }
  if (!intents.includes('drug_indication') && ['資料庫', '查得到', '查到', '核對', '能不能用', '是否在', '只准用網站資料'].some(k => text.includes(k))) {
    intents.push('drug_indication');
  }
  return intents;
}

function agentDrugTerms(message, patient) {
  const text = `${message || ''} ${JSON.stringify(patient || {})}`.toLowerCase();
  const p = patient || {};
  const terms = [];
  const add = items => terms.push(...items);
  if (['herceptin', 'trastuzumab', '賀癌平'].some(k => text.includes(k))) add(['trastuzumab', 'herceptin', 'trastuzumab_sc']);
  if (['perjeta', 'pertuzumab', 'phesgo', '賀疾妥'].some(k => text.includes(k))) add(['pertuzumab', 'perjeta', 'phesgo']);
  if (['arimidex', 'anastrozole'].some(k => text.includes(k))) add(['anastrozole', 'arimidex']);
  if (['femara', 'letrozole', 'lovizol'].some(k => text.includes(k))) add(['letrozole', 'femara', 'lovizol']);
  if (['zoladex', 'goserelin'].some(k => text.includes(k))) add(['goserelin', 'zoladex']);
  if (['her2', 'her-2', '陽性', 'erbb2'].some(k => text.includes(k))) add(['trastuzumab', 'herceptin', 'pertuzumab', 'perjeta', 'phesgo', 'emtansine', 'deruxtecan', 'lapatinib', 'tucatinib', 'neratinib', 'her2']);
  if (['pembro', 'keytruda', '免疫', 'tnbc', '三陰', 'keynote-522', 'kn522'].some(k => text.includes(k))) add(['pembrolizumab', 'keytruda', 'atezolizumab', 'tnbc']);
  if (['er+', 'hr+', '荷爾蒙', '停經', 'cdk', 'pik3ca', 'esr1'].some(k => text.includes(k))) add(['palbociclib', 'ribociclib', 'abemaciclib', 'alpelisib', 'fulvestrant', 'letrozole', 'anastrozole', 'exemestane', 'tamoxifen']);
  if (['藥', '給付', '健保', 'drug', 'regimen', '配方', '化療'].some(k => text.includes(k))) add(['breast']);
  if (String(p.her2 || '').trim() === '+') add(['trastuzumab', 'herceptin', 'pertuzumab', 'perjeta', 'phesgo', 'emtansine', 'deruxtecan', 'lapatinib', 'tucatinib', 'neratinib', 'her2']);
  if (String(p.er || '').trim() === '+' || String(p.pr || '').trim() === '+') add(['palbociclib', 'ribociclib', 'abemaciclib', 'alpelisib', 'fulvestrant', 'letrozole', 'anastrozole', 'exemestane', 'tamoxifen']);
  if (String(p.er || '').trim() === '-' && String(p.pr || '').trim() === '-' && String(p.her2 || '').trim() === '-') add(['pembrolizumab', 'keytruda', 'atezolizumab', 'sacituzumab', 'tnbc']);
  if (String(p.brca || '').trim() === '+') add(['olaparib']);
  if (String(p.pik3ca || '').trim() === '+') add(['alpelisib']);
  if (String(p.esr1 || '').trim() === '+') add(['fulvestrant']);
  return [...new Set(terms)].slice(0, 24);
}

function agentMissingFields(message, patient) {
  const intents = agentQuestionIntents(message);
  const data = patient || {};
  const hasAny = keys => keys.some(k => data[k] !== undefined && data[k] !== null && data[k] !== '');
  const out = {};
  if (intents.includes('staging')) {
    const missing = [
      ['T', ['cT', 'pT']],
      ['N', ['cN', 'pN']],
      ['M', ['cM', 'pM']],
    ].filter(([, keys]) => !hasAny(keys)).map(([label]) => label);
    if (missing.length) out.staging = missing;
  }
  if (intents.includes('risk_scores')) {
    const missing = [
      ['age', ['age']],
      ['tumor size', ['size', 'size_mm', 'tumor_size_mm']],
      ['positive nodes', ['nodes_pos', 'positive_nodes', 'cN', 'pN']],
      ['grade', ['grade']],
      ['ER', ['er', 'er_hscore']],
      ['HER2', ['her2', 'her2_ihc', 'her2_fish']],
    ].filter(([, keys]) => !hasAny(keys)).map(([label]) => label);
    if (missing.length) out.predict = missing;
  }
  return out;
}

function agentDrugMatches(message, patient) {
  const intents = agentQuestionIntents(message);
  const context = { drug_matches: [], formulation_matches: [], citations: [], called_tools: [], answer_hints: [] };
  if (!intents.includes('drug_indication') && !intents.includes('price')) return context;
  const terms = agentDrugTerms(message, patient);
  const msgLower = String(message || '').toLowerCase();
  const patientText = JSON.stringify(patient || {}).toLowerCase();
  const her2Positive = String((patient || {}).her2 || '').trim() === '+';
  const nodeStage = String((patient || {}).cN || (patient || {}).pN || '').toLowerCase();
  const nodePositive = Number((patient || {}).nodes_pos || 0) > 0 || /^n[1-3]/.test(nodeStage);
  if (['perjeta', 'pertuzumab', 'phesgo'].some(k => msgLower.includes(k)) || (her2Positive && nodePositive)) {
    context.answer_hints.push('HER2 positive + LN positive query: system should include Pertuzumab/Perjeta when drug_matches contains Perjeta/Pertuzumab/Phesgo; do not answer that Perjeta has no data.');
  }
  if (patientText.includes('tnbc') || patientText.includes('三陰') || ((patient || {}).er === '-' && (patient || {}).pr === '-' && (patient || {}).her2 === '-')) {
    context.answer_hints.push('TNBC query: for early/neoadjuvant M0 disease, prioritize KEYNOTE-522/KN522 style treatment if Pembrolizumab/Keytruda is present.');
  }
  if (!terms.length) {
    context.answer_hints.push('Drug database miss: answer must include exact idea 本網站資料庫內目前沒有查到，且必須說 無法根據網站資料提供用途、價格或給付資訊；不可用外部知識補充。');
    return context;
  }
  const drugs = readJson('drugs').filter(d => d.specialty_id === 'oncology_breast');
  const searchableTerms = terms.filter(t => t !== 'breast');
  let rows = drugs;
  if (searchableTerms.length) {
    rows = drugs.filter(d => {
      const hay = [
        d.generic_name,
        d.trade_names,
        d.indication,
        d.stage,
        d.conditions,
        JSON.stringify(d.clinical_tags || {}),
      ].join(' ').toLowerCase();
      return searchableTerms.some(t => hay.includes(String(t).toLowerCase()));
    });
  }
  const exactTerms = searchableTerms.filter(t => String(t).length >= 4);
  rows.sort((a, b) => {
    const aName = `${a.generic_name || ''} ${a.trade_names || ''}`.toLowerCase();
    const bName = `${b.generic_name || ''} ${b.trade_names || ''}`.toLowerCase();
    const aExact = exactTerms.some(t => aName.includes(t)) ? 0 : 1;
    const bExact = exactTerms.some(t => bName.includes(t)) ? 0 : 1;
    if (aExact !== bExact) return aExact - bExact;
    return String(a.generic_name || '').localeCompare(String(b.generic_name || ''));
  });
  rows = rows.slice(0, 18);
  context.called_tools.push('drug-search');
  context.drug_matches = rows.map(r => {
    const generic = String(r.generic_name || '').toLowerCase();
    const trade = String(r.trade_names || '').toLowerCase();
    let coverageStatus = r.nhi_price == null ? '未列健保價/可能自費，需依院內資料確認' : '健保價可查';
    if (r.prior_auth) coverageStatus += '，需事前審查';
    if (generic.includes('phesgo') || trade.includes('phesgo')) coverageStatus = 'Phesgo 目前資料標示為自費/健保未給付，不可套用到 Perjeta 靜脈製劑';
    return {
      id: r.id,
      generic_name: r.generic_name,
      trade_names: r.trade_names || '',
      stage: r.stage || '',
      therapy_line: r.therapy_line || null,
      line_label: r.therapy_line ? `第${r.therapy_line}線` : '未指定線別',
      prior_auth: !!r.prior_auth,
      coverage_status: coverageStatus,
      nhi_price: r.nhi_price,
      price_unit: r.price_unit || '',
      indication_excerpt: String(r.indication || '').slice(0, 450),
      conditions_excerpt: String(r.conditions || '').slice(0, 450),
    };
  });
  context.citations = rows.map(r => ({ source: 'data/api/drugs.json', id: `drug:${r.id}`, title: r.generic_name })).slice(0, 8);
  if (!rows.length) {
    context.answer_hints.push('Drug database miss: answer must include exact idea 本網站資料庫內目前沒有查到，且必須說 無法根據網站資料提供用途、價格或給付資訊；不可用外部知識補充。');
  }
  const formTerms = [];
  const termSet = new Set(terms.map(t => String(t).toLowerCase()));
  if (['trastuzumab', 'pertuzumab', 'emtansine', 'deruxtecan', 'her2'].some(t => termSet.has(t))) formTerms.push('trastuzumab', 'pertuzumab', 'trastuzumab_emtansine', 'trastuzumab_deruxtecan', 'phesgo');
  if (['pembrolizumab', 'keytruda'].some(t => termSet.has(t))) formTerms.push('pembrolizumab');
  if (['letrozole', 'femara', 'lovizol'].some(t => termSet.has(t))) formTerms.push('letrozole');
  if (['anastrozole', 'arimidex'].some(t => termSet.has(t))) formTerms.push('anastrozole');
  if (['goserelin', 'zoladex'].some(t => termSet.has(t))) formTerms.push('goserelin');
  if (formTerms.length) {
    const wanted = new Set(formTerms);
    context.formulation_matches = readJson('formulations')
      .filter(f => wanted.has(f.drug_key))
      .slice(0, 16)
      .map(f => ({
        drug_key: f.drug_key,
        brand_name: f.brand_name,
        formulation: f.formulation,
        dose_mg: f.dose_mg,
        vial_unit: f.dose_unit,
        category: f.category,
        nhi_price: f.nhi_price,
        self_pay_price: f.ntuh_price,
        nhi_covered: f.nhi_covered,
        regimen_tags: f.regimen_use,
      }));
    if (context.formulation_matches.length) context.called_tools.push('formulation-lookup');
  }
  return context;
}

function buildAgentSystemContext(message, patient, provided) {
  if (provided && typeof provided === 'object' && Object.keys(provided).length > 1) return provided;
  const context = {
    called_tools: [],
    question_intents: agentQuestionIntents(message),
    workspace_patient_context: patient || {},
    effective_patient_context: patient || {},
    missing_fields: agentMissingFields(message, patient),
    staging: null,
    risk_scores: {},
    drug_matches: [],
    formulation_matches: [],
    answer_hints: [],
    citations: [],
  };
  try {
    context.staging = stagingScore(patient || {});
    context.called_tools.push('calculate/staging-score');
  } catch (err) {
    context.staging = null;
  }
  try {
    context.risk_scores = calculateScores(patient || {}) || {};
    if (Object.keys(context.risk_scores).length) context.called_tools.push('calculate/risk-scores');
  } catch (err) {
    context.risk_scores = {};
  }
  const drugContext = agentDrugMatches(message, patient || {});
  context.called_tools.push(...drugContext.called_tools);
  context.drug_matches = drugContext.drug_matches;
  context.formulation_matches = drugContext.formulation_matches;
  context.answer_hints.push(...drugContext.answer_hints);
  context.citations.push(...drugContext.citations);
  context.called_tools = [...new Set(context.called_tools)];
  return context;
}

function compactAgentPayload(body) {
  const payload = body || {};
  const patient = payload.patient_context || {};
  const model = normalizeOllamaModel(payload.preferred_model || payload.model || (payload.client && payload.client.model));
  return {
    message: String(payload.message || '').slice(0, 4000),
    patient_context: patient,
    derived: payload.derived || {},
    report_text: String(payload.report_text || '').slice(0, 8000),
    tool_registry: Array.isArray(payload.tool_registry) ? payload.tool_registry.slice(0, 24) : [],
    client: payload.client || {},
    system_context: buildAgentSystemContext(payload.message || '', patient, payload.system_context),
    preferred_model: model,
  };
}

async function callOllamaAgent(body) {
  const apiKey = process.env.OLLAMA_API_KEY || '';
  if (!apiKey) {
    return { ok: false, status: 503, error: 'OLLAMA_API_KEY is not configured on Netlify.' };
  }
  const agentContext = compactAgentPayload(body);
  if (!agentContext.message.trim()) {
    return { ok: false, status: 400, error: 'message required' };
  }
  const selectedModel = normalizeOllamaModel(agentContext.preferred_model);
  const allowedTools = new Set(agentContext.tool_registry.map(t => String((t && t.id) || '')).filter(Boolean));
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), Math.max(1000, OLLAMA_TIMEOUT_MS));
  try {
    const res = await fetch(`${OLLAMA_HOST}/api/chat`, {
      method: 'POST',
      headers: {
        'content-type': 'application/json',
        authorization: `Bearer ${apiKey}`,
      },
      body: JSON.stringify({
        model: selectedModel,
        stream: false,
        format: 'json',
        messages: [
          { role: 'system', content: AGENT_SYSTEM_PROMPT },
          { role: 'user', content: JSON.stringify(agentContext) },
        ],
        options: {
          temperature: 0.2,
          num_ctx: 8192,
        },
      }),
      signal: controller.signal,
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      return { ok: false, status: res.status, error: data.error || data.message || 'Ollama Cloud request failed.' };
    }
    const content = String(((data.message || {}).content) || '').trim();
    const answer = parseAgentJsonText(content);
    let toolId = String(answer.tool_id || '').trim();
    if (toolId && allowedTools.size && !allowedTools.has(toolId)) toolId = '';
    const reply = String(answer.reply || answer.message || answer.text || '').trim() || 'Ollama Cloud 有回應，但沒有產生可顯示的文字。';
    return {
      ok: true,
      reply,
      tool_id: toolId,
      patient_patch: sanitizePatientPatch(answer.patient_patch),
      citations: Array.isArray(answer.citations) ? answer.citations.slice(0, 8) : [],
      called_tools: Array.isArray(answer.called_tools) ? answer.called_tools.slice(0, 8) : ['ollama-cloud'],
      model: selectedModel,
      runtime: 'ollama-cloud',
    };
  } catch (err) {
    return { ok: false, status: 502, error: 'Ollama Cloud agent unavailable', detail: err.name === 'AbortError' ? 'timeout' : err.message };
  } finally {
    clearTimeout(timer);
  }
}

async function checkOllamaStatus(modelOverride) {
  const selectedModel = normalizeOllamaModel(modelOverride);
  const apiKey = process.env.OLLAMA_API_KEY || '';
  if (!apiKey) {
    return {
      ok: false,
      configured: false,
      connected: false,
      status: 'missing_key',
      message: 'OLLAMA_API_KEY is not configured on Netlify.',
      model: selectedModel,
      runtime: 'ollama-cloud',
    };
  }
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), Math.min(Math.max(1000, OLLAMA_TIMEOUT_MS), 12000));
  try {
    const res = await fetch(`${OLLAMA_HOST}/api/tags`, {
      method: 'GET',
      headers: { authorization: `Bearer ${apiKey}` },
      signal: controller.signal,
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      return {
        ok: false,
        configured: true,
        connected: false,
        status: 'cloud_error',
        message: data.error || data.message || `Ollama Cloud returned HTTP ${res.status}`,
        model: selectedModel,
        runtime: 'ollama-cloud',
      };
    }
    const models = Array.isArray(data.models) ? data.models : [];
    const modelNames = models.map(m => String(m.name || m.model || '').trim()).filter(Boolean);
    return {
      ok: true,
      configured: true,
      connected: true,
      status: 'connected',
      message: 'Ollama Cloud connected.',
      model: selectedModel,
      model_available: modelNames.length ? modelNames.includes(selectedModel) : null,
      model_count: models.length,
      models: modelNames.slice(0, 50),
      runtime: 'ollama-cloud',
    };
  } catch (err) {
    return {
      ok: false,
      configured: true,
      connected: false,
      status: err.name === 'AbortError' ? 'timeout' : 'network_error',
      message: err.name === 'AbortError' ? 'Ollama Cloud status check timed out.' : err.message,
      model: selectedModel,
      runtime: 'ollama-cloud',
    };
  } finally {
    clearTimeout(timer);
  }
}

async function githubFeedbackRequest(pathname, options = {}) {
  const token = process.env.FEEDBACK_GITHUB_TOKEN || '';
  const headers = {
    accept: 'application/vnd.github+json',
    'user-agent': 'oncobreast-copilot-feedback',
    ...(options.headers || {}),
  };
  if (token) headers.authorization = `Bearer ${token}`;
  return fetch(`https://api.github.com/repos/${FEEDBACK_REPO}${pathname}`, { ...options, headers });
}

async function listFeedback(limit) {
  const perPage = Math.max(1, Math.min(Number(limit) || 10, 20));
  const res = await githubFeedbackRequest(`/issues?state=open&labels=${encodeURIComponent(FEEDBACK_LABEL)}&per_page=${perPage}&sort=created&direction=desc`);
  if (!res.ok) return { ok: false, status: res.status, items: [] };
  const rows = await res.json();
  return {
    ok: true,
    mode: 'github-issues',
    items: (Array.isArray(rows) ? rows : []).map(item => ({
      id: item.id,
      number: item.number,
      title: item.title,
      module: '',
      type: '',
      created_at: item.created_at,
      url: item.html_url,
    })),
  };
}

async function createFeedback(body) {
  const token = process.env.FEEDBACK_GITHUB_TOKEN || '';
  if (!token) return { ok: false, status: 503, error: 'Feedback backend is not configured.' };
  const title = sanitizeFeedbackText(body.title || '[回報] 未命名', 180);
  const reportBody = sanitizeFeedbackText(body.body || '', 12000);
  const module = sanitizeFeedbackText(body.module || '', 80);
  const type = sanitizeFeedbackText(body.type || '', 40);
  const footer = [
    '',
    '---',
    `source: Oncobreast copilot feedback board`,
    module ? `module: ${module}` : '',
    type ? `type: ${type}` : '',
    body.app_version ? `app_version: ${sanitizeFeedbackText(body.app_version, 40)}` : '',
  ].filter(Boolean).join('\n');
  const res = await githubFeedbackRequest('/issues', {
    method: 'POST',
    headers: {'content-type': 'application/json'},
    body: JSON.stringify({
      title,
      body: `${reportBody || '(no body)'}${footer}`,
      labels: [FEEDBACK_LABEL],
    }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) return { ok: false, status: res.status, error: data.message || 'Failed to create feedback.' };
  return {
    ok: true,
    item: {
      id: data.id,
      number: data.number,
      title: data.title,
      module,
      type,
      created_at: data.created_at,
      url: data.html_url,
    },
  };
}

function apiPath(event) {
  const raw = event.path || '';
  const prefix = '/.netlify/functions/api';
  let p = raw.startsWith(prefix) ? raw.slice(prefix.length) : raw;
  if (p.startsWith('/api/')) p = p.slice(4);
  if (p === '') p = '/';
  return p;
}

exports.handler = async function handler(event) {
  if (event.httpMethod === 'OPTIONS') return json(204, {});
  const method = event.httpMethod || 'GET';
  const p = apiPath(event);
  const qs = event.queryStringParameters || {};

  try {
    if (method === 'GET' && (p === '/' || p === '/health')) {
      return json(200, {
        ok: true,
        runtime: 'netlify-functions',
        mode: 'read-only',
        api_policy: {
          public_read: true,
          recommended_headers: ['x-contact-email', 'x-client-app'],
          write_access: 'Use authenticated hospital backend for patient data, EMR writes, and admin updates.',
        },
      });
    }

    if (method === 'GET' && p === '/agent-prompt') return json(200, { ok: true, version: '2026-06-06', prompt: AGENT_SYSTEM_PROMPT });
    if (method === 'GET' && p === '/agent-status') {
      const result = await checkOllamaStatus(qs.model);
      return json(result.ok ? 200 : (result.configured ? 502 : 503), result);
    }
    if (method === 'GET' && p === '/config') return json(200, readJson('config'));
    if (method === 'GET' && p === '/stats') return json(200, readJson('stats'));
    if (method === 'GET' && p === '/feedback') {
      const result = await listFeedback(qs.limit);
      return json(result.ok ? 200 : result.status || 503, result);
    }
    if (method === 'POST' && p === '/feedback') {
      const body = bodyJson(event);
      if (body === null) return json(400, { ok: false, error: 'Invalid JSON body' });
      const result = await createFeedback(body);
      return json(result.ok ? 200 : result.status || 503, result);
    }

    if (method === 'POST' && p === '/agent') {
      const body = bodyJson(event);
      if (body === null) return json(400, { ok: false, error: 'Invalid JSON body' });
      const result = await callOllamaAgent(body);
      return json(result.ok ? 200 : result.status || 502, result);
    }

    if (method === 'GET' && p === '/drugs') {
      let drugs = readJson('drugs');
      const cat = qs.category || qs.specialty || '';
      const q = (qs.q || '').toLowerCase();
      if (cat) drugs = drugs.filter(d => d.specialty_id === cat);
      if (q) {
        drugs = drugs.filter(d =>
          String(d.generic_name || '').toLowerCase().includes(q) ||
          String(d.trade_names || '').toLowerCase().includes(q)
        );
      }
      return json(200, drugs);
    }

    const drugMatch = p.match(/^\/drug\/(\d+)$/);
    if (method === 'GET' && drugMatch) {
      const id = Number(drugMatch[1]);
      const drug = readJson('drugs').find(d => d.id === id);
      return drug ? json(200, drug) : json(404, { error: 'Not found' });
    }

    if (method === 'GET' && p === '/formulations') {
      let rows = readJson('formulations');
      if (qs.drug) rows = rows.filter(r => r.drug_key === qs.drug);
      return json(200, rows);
    }

    if (method === 'POST' && p === '/calculate/risk-scores') {
      const body = bodyJson(event);
      if (body === null) return json(400, { error: 'Invalid JSON body' });
      return json(200, { ok: true, scores: calculateScores(body) });
    }

    if (method === 'POST' && p === '/calculate/staging-score') {
      const body = bodyJson(event);
      if (body === null) return json(400, { error: 'Invalid JSON body' });
      return json(200, { ok: true, result: stagingScore(body) });
    }

    if (method === 'POST' && p === '/translate') {
      const body = bodyJson(event);
      if (body === null) return json(400, { ok: false, error: 'Invalid JSON body' });
      const lang = String(body.lang || '').toLowerCase();
      if (!['zh', 'en', 'id', 'ja'].includes(lang)) return json(400, { ok: false, error: 'Unsupported language' });
      const rawTexts = Array.isArray(body.texts) ? body.texts : [];
      const texts = [];
      const seen = new Set();
      for (const item of rawTexts) {
        const text = String(item || '').trim();
        if (!text || seen.has(text)) continue;
        seen.add(text);
        texts.push(text.length > 1800 ? text.slice(0, 1800) : text);
        if (texts.length >= 120) break;
      }
      if (lang === 'zh') {
        return json(200, { ok: true, lang, translations: Object.fromEntries(texts.map(t => [t, t])), cached: texts.length, translated: 0, mode: 'identity' });
      }
      const cache = readI18nCache(lang);
      const translations = {};
      let cached = 0;
      for (const text of texts) {
        if (cache[text]) {
          translations[text] = cache[text];
          cached += 1;
        } else {
          translations[text] = text;
        }
      }
      return json(200, {
        ok: true,
        lang,
        translations,
        cached,
        translated: 0,
        mode: 'cache-only',
        note: 'Netlify read-only runtime uses prebuilt data/i18n_cache files. Run the local Python/Ollama server to generate more translations.',
      });
    }

    if (['POST', 'PUT', 'DELETE'].includes(method)) {
      return json(405, { error: 'This Netlify deployment is read-only. Use the local API server for admin writes.' });
    }

    return json(404, { error: 'Not found' });
  } catch (err) {
    return json(500, { error: 'API error', detail: err.message });
  }
};

exports.config = {
  path: '/api/*',
};
