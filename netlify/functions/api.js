const fs = require('fs');
const path = require('path');
const { calculateScores, stagingScore } = require('./_shared/calculators');

const API_DIR = path.resolve(__dirname, '../../data/api');
const I18N_CACHE_DIR = path.resolve(__dirname, '../../data/i18n_cache');
const FEEDBACK_REPO = process.env.FEEDBACK_GITHUB_REPO || 'erichuang777777/NTUH_Breast_Caculator';
const FEEDBACK_LABEL = process.env.FEEDBACK_GITHUB_LABEL || 'feedback-board';
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
