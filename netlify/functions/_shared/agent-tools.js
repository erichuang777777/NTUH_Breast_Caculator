const { calculateScores, stagingScore } = require('./calculators');

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

function patientStageGroup(patient) {
  const m = String((patient || {}).cM || (patient || {}).pM || '').toUpperCase();
  if (m === 'M1') return 'metastatic';
  const t = String((patient || {}).cT || (patient || {}).pT || '').toUpperCase();
  const n = String((patient || {}).cN || (patient || {}).pN || '').toUpperCase();
  if (/^T[34]/.test(t) || /^N[23]/.test(n)) return 'advanced';
  if (t || n || m === 'M0') return 'early';
  return '';
}

function isDrugCompatibleWithPatient(drug, patient) {
  const tags = drug && drug.clinical_tags && typeof drug.clinical_tags === 'object' ? drug.clinical_tags : {};
  const p = patient || {};
  const her2 = String(p.her2 || '').trim();
  const hr = (String(p.er || '').trim() === '+' || String(p.pr || '').trim() === '+') ? 'positive'
    : (String(p.er || '').trim() === '-' && String(p.pr || '').trim() === '-' ? 'negative' : '');
  if (tags.her2 && her2) {
    const expected = her2 === '+' ? 'positive' : 'negative';
    if (tags.her2 !== expected && tags.her2 !== 'both') return false;
  }
  if (tags.er_pr && hr) {
    if (tags.er_pr !== hr && tags.er_pr !== 'both') return false;
  }
  const stageGroup = patientStageGroup(p);
  if (stageGroup && drug.stage) {
    const stageText = String(drug.stage || '').toLowerCase();
    if (stageText && !stageText.includes(stageGroup)) return false;
  }
  return true;
}

function patientDrugPriority(drug, patient, exactTerms) {
  const tags = drug && drug.clinical_tags && typeof drug.clinical_tags === 'object' ? drug.clinical_tags : {};
  const p = patient || {};
  const name = `${drug.generic_name || ''} ${drug.trade_names || ''}`.toLowerCase();
  let score = 100;
  if (String(p.her2 || '').trim() === '+' && tags.her2 === 'positive') score -= 40;
  if ((String(p.er || '').trim() === '+' || String(p.pr || '').trim() === '+') && tags.er_pr === 'positive') score -= 20;
  if (String(p.er || '').trim() === '-' && String(p.pr || '').trim() === '-' && String(p.her2 || '').trim() === '-' && tags.er_pr === 'negative') score -= 30;
  if ((exactTerms || []).some(t => name.includes(t))) score -= 10;
  if (drug.nhi_price != null) score -= 3;
  if (drug.prior_auth) score += 1;
  return score;
}

function agentDrugMatches(message, patient, readJson) {
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
  rows = rows.filter(d => isDrugCompatibleWithPatient(d, patient));
  const exactTerms = searchableTerms.filter(t => String(t).length >= 4);
  rows.sort((a, b) => {
    const priority = patientDrugPriority(a, patient, exactTerms) - patientDrugPriority(b, patient, exactTerms);
    if (priority !== 0) return priority;
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

function buildAgentSystemContext(message, patient, provided, options = {}) {
  if (provided && typeof provided === 'object' && Object.keys(provided).length > 1) return provided;
  if (typeof options.readJson !== 'function') throw new Error('agent tool engine requires readJson(name)');
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
  const drugContext = agentDrugMatches(message, patient || {}, options.readJson);
  context.called_tools.push(...drugContext.called_tools);
  context.drug_matches = drugContext.drug_matches;
  context.formulation_matches = drugContext.formulation_matches;
  context.answer_hints.push(...drugContext.answer_hints);
  context.citations.push(...drugContext.citations);
  context.called_tools = [...new Set(context.called_tools)];
  return context;
}

module.exports = {
  agentQuestionIntents,
  agentDrugTerms,
  agentMissingFields,
  buildAgentSystemContext,
};
