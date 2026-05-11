function num(value) {
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}

function logistic(x) {
  return 1 / (1 + Math.exp(-x));
}

function riskClass(pct, lowCut = 10, highCut = 30) {
  if (pct < lowCut) return 'low';
  if (pct < highCut) return 'medium';
  return 'high';
}

function cts5(input) {
  const nodes = num(input.nodes_pos ?? input.positive_nodes);
  const sizeMm = num(input.size_mm ?? input.tumor_size_mm);
  const grade = num(input.grade);
  const age = num(input.age);
  if (nodes === null || sizeMm === null || grade === null || age === null || sizeMm <= 0 || age <= 0) return null;
  const score = 0.438 * nodes + 0.988 * (0.093 * sizeMm - 0.001 * sizeMm * sizeMm) + 0.375 * grade + 0.017 * age;
  const distantRecurrence10y = (1 - Math.exp(-0.00223 * Math.exp(score))) * 100;
  let cls = 'low';
  if (score >= 3.86) cls = 'high';
  else if (score >= 3.13) cls = 'medium';
  return { score, distant_recurrence_10y_pct: distantRecurrence10y, risk: cls };
}

function npi(input) {
  const sizeMm = num(input.size_mm ?? input.tumor_size_mm);
  const grade = num(input.grade);
  const nodes = num(input.nodes_pos ?? input.positive_nodes);
  if (sizeMm === null || grade === null || nodes === null || sizeMm <= 0) return null;
  let nodeStage = 1;
  if (nodes >= 4) nodeStage = 3;
  else if (nodes >= 1) nodeStage = 2;
  const score = 0.2 * (sizeMm / 10) + nodeStage + grade;
  let group = 'Excellent';
  let risk = 'low';
  if (score <= 2.4) group = 'Excellent';
  else if (score <= 3.4) group = 'Good';
  else if (score <= 4.4) { group = 'Moderate I'; risk = 'medium'; }
  else if (score <= 5.4) { group = 'Moderate II'; risk = 'medium'; }
  else if (score <= 6.4) { group = 'Poor'; risk = 'high'; }
  else { group = 'Very Poor'; risk = 'high'; }
  return { score, group, risk };
}

function ihc4(input) {
  const erH = num(input.er_hscore);
  const prH = num(input.pr_hscore);
  const her2 = input.her2 === '+' || input.her2 === 'pos' || input.her2 === 1 ? 1 : 0;
  const ki67 = num(input.ki67);
  if (erH === null || prH === null || ki67 === null) return null;
  const er10 = erH / 30;
  const pr10 = prH / 30;
  const ki67d = ki67 / 100;
  const score = 94.7 * (-0.100 * er10 - 0.079 * pr10 + 0.586 * her2 + 0.240 * Math.log(1 + 10 * ki67d));
  let risk = 'low';
  if (score >= 25) risk = 'high';
  else if (score >= 0) risk = 'medium';
  return { score, risk };
}

function magee(input) {
  const grade = num(input.grade);
  const tubule = num(input.tubule_score ?? 3);
  const nuclear = num(input.nuclear_score ?? grade);
  const mitotic = num(input.mitotic_score ?? grade);
  const ns = num(input.nottingham_score ?? (tubule + nuclear + mitotic));
  const sizeMm = num(input.size_mm ?? input.tumor_size_mm);
  const erH = num(input.er_hscore);
  const prH = num(input.pr_hscore);
  const ki67 = num(input.ki67);
  const her2cat = input.her2 === '+' || input.her2 === 'pos' ? 2 : 0;
  if ([ns, sizeMm, erH, prH, ki67].some(v => v === null)) return null;
  const her2 = her2cat === 2 ? 1 : 0;
  const m1 = 15.31385 + ns * 1.4055 - erH * 0.01924 - prH * 0.02925 + her2 * 11.99435 + sizeMm * 0.0986;
  const m2 = 18.8042 + ns * 2.34123 - erH * 0.03749 - prH * 0.03065 + her2 * 11.8378 + sizeMm * 0.13838 + ki67 * 0.0035;
  const erCat = erH >= 200 ? 0 : (erH >= 10 ? 1 : 2);
  const prCat = prH >= 200 ? 0 : (prH >= 10 ? 1 : 2);
  const hCat = her2cat >= 2 ? 4 : 0;
  const nsCat = ns <= 5 ? 0 : (ns <= 7 ? 1 : 2);
  const kiCat = ki67 < 10 ? 0 : (ki67 < 20 ? 1 : 2);
  const sizeCat = sizeMm < 10 ? 0 : (sizeMm < 20 ? 1 : (sizeMm < 30 ? 2 : 3));
  const m3 = 13.424 + erCat * 1.4 + prCat * 1.6 + hCat * 5 + nsCat * 3 + kiCat * 1.6 + sizeCat * 0.5;
  const average = (m1 + m2 + m3) / 3;
  let risk = 'low';
  if (average >= 31) risk = 'high';
  else if (average >= 18) risk = 'medium';
  return { m1, m2, m3, average, risk };
}

function rcb(input) {
  const d1 = num(input.rcb_d1);
  const d2 = num(input.rcb_d2);
  const finvPct = num(input.rcb_finv_pct);
  const ln = num(input.rcb_ln_positive);
  const dmet = num(input.rcb_largest_met_mm);
  if ([d1, d2, finvPct, ln, dmet].some(v => v === null)) return null;
  const finv = finvPct / 100;
  const dprim = Math.sqrt(Math.max(d1, 0) * Math.max(d2, 0));
  const primary = dprim > 0 && finv > 0 ? 1.4 * Math.pow(finv * dprim, 0.17) : 0;
  const nodal = ln > 0 && dmet > 0 ? Math.pow(4 * (1 - Math.pow(0.75, ln)) * dmet, 0.17) : 0;
  const score = primary + nodal;
  let group = 'RCB-0';
  let risk = 'low';
  if (score === 0) group = 'RCB-0';
  else if (score <= 1.36) group = 'RCB-I';
  else if (score <= 3.28) { group = 'RCB-II'; risk = 'medium'; }
  else { group = 'RCB-III'; risk = 'high'; }
  return { score, group, risk, dprim, primary_component: primary, nodal_component: nodal };
}

function nonSln(input) {
  const sizeCm = num(input.size_cm ?? (num(input.size_mm) !== null ? num(input.size_mm) / 10 : null));
  const multifocal = input.multifocal ? 1 : 0;
  const lvi = input.lvi ? 1 : 0;
  const positiveSln = num(input.positive_sln);
  const negativeSln = num(input.negative_sln);
  if ([sizeCm, positiveSln, negativeSln].some(v => v === null)) return null;
  const logit = 0.267 * sizeCm + 1.443 * multifocal + 1.078 * lvi + 0.471 * positiveSln - 0.618 * negativeSln - 2.541;
  const risk = logistic(logit) * 100;
  return { logit, risk_pct: risk, risk: riskClass(risk, 10, 30) };
}

function ajccNForCalc(n) {
  if (!n) return n;
  if (n === 'N0i-' || n === 'N0i+' || n === 'pN0i-' || n === 'pN0i+') return 'N0';
  return String(n).replace(/^p/, '');
}

function ajccAnatomic(input) {
  const t = String(input.T || input.t || '').replace(/^p/, '');
  const n = ajccNForCalc(input.N || input.n);
  const m = String(input.M || input.m || '').replace(/^p/, '');
  if (!t || !n || !m) return null;
  if (m === 'M1') return 'IV';
  if (t === 'Tis') return n === 'N0' ? '0' : null;
  const ti = ({ T1: 1, T2: 2, T3: 3, T4: 4 })[t];
  const ni = ({ N0: 0, N1: 1, N2: 2, N3: 3 })[n];
  if (ti === undefined || ni === undefined || m !== 'M0') return null;
  if (ni === 3) return 'IIIC';
  if (ti === 4) return ni <= 2 ? 'IIIB' : 'IIIC';
  if (ni === 2) return ti <= 3 ? 'IIIA' : 'IIIB';
  if (ti === 3 && ni === 1) return 'IIIA';
  if (ti === 3 && ni === 0) return 'IIB';
  if (ti === 2 && ni === 1) return 'IIB';
  if (ti === 2 && ni === 0) return 'IIA';
  if (ti === 1 && ni === 1) return 'IIA';
  if (ti === 1 && ni === 0) return 'IA';
  return null;
}

function calculateScores(input = {}) {
  const scores = {
    cts5: cts5(input),
    npi: npi(input),
    ihc4: ihc4(input),
    magee: magee(input),
    rcb: rcb(input),
    non_sln: nonSln(input),
  };
  return Object.fromEntries(Object.entries(scores).filter(([, value]) => value !== null));
}

function stagingScore(input = {}) {
  const clinical = ajccAnatomic({ T: input.cT, N: input.cN, M: input.cM });
  const pathologic = ajccAnatomic({ T: input.pT, N: input.pN, M: input.pM });
  return {
    ajcc_v8: {
      clinical,
      pathologic,
      selected: pathologic || clinical,
      selected_basis: pathologic ? 'pathologic' : (clinical ? 'clinical' : null),
    },
    scores: calculateScores(input),
  };
}

module.exports = { calculateScores, stagingScore };
