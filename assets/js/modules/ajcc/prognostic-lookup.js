// ── AJCC prognostic lookup wrapper ──
function _ajcc9Lookup(t, n, m, grade, er, pr, her2){
    const lookupTable = globalThis.AJCC9_LOOKUP || (typeof AJCC9_LOOKUP !== 'undefined' ? AJCC9_LOOKUP : null);
    if(!lookupTable) return null;
    t = _ajccCleanToken(t, 'T');
    n = _ajccCleanToken(n, 'N');
    m = _ajccCleanToken(m, 'M');
    grade = _gradeNumber(grade);
    if(m === 'M1') return 'IV';
    n = _ajccNForCalc(n);
    // Reduce T1mi/T1a/T1b/T1c → T1; T4a/b/c/d → T4
    const tCat = t.startsWith('T1') ? 'T1' : (t.startsWith('T4') ? 'T4' : t);
    // Reduce N2a/b → N2; N3a/b/c → N3
    const nCat = n.startsWith('N2') ? 'N2' : (n.startsWith('N3') ? 'N3' : n);
    if(!grade || !er || !pr || !her2) return null;
    const erC = (er === '+') ? 'P' : 'N';
    const prC = (pr === '+') ? 'P' : 'N';
    const her2C = (her2 === '+') ? 'P' : 'N';
    const key = `${tCat}|${nCat}|${m}|${grade}|${her2C}|${erC}|${prC}`;
    return lookupTable[key] || null;
}
window.addEventListener('load', () => {
    if(typeof refreshDashboardResults === 'function') refreshDashboardResults();
});
