(function(global){
  'use strict';

  const BENCHMARK_CORPUS_URL = 'data/agent_bench/bench_v1.json';
  const BENCHMARK_FULL_RESULT_URL = 'data/agent_bench/bench_v1_results_2026-06-05.json';
  const BENCHMARK_FAILED_RERUN_URL = 'data/agent_bench/bench_failed_rerun_final_2026-06-06.json';
  const BENCHMARK_ADVERSARIAL_CORPUS_URL = 'data/agent_bench/bench_adversarial_2026-06-06.json';
  const BENCHMARK_ADVERSARIAL_RESULT_URL = 'data/agent_bench/bench_adversarial_results_2026-06-06.json';

  const state = {
    corpus: null,
    fullResult: null,
    rerunResult: null,
    adversarialResult: null
  };

  function escapeHtml(value){
    if(typeof global.esc === 'function') return global.esc(value);
    return String(value == null ? '' : value).replace(/[<>&"]/g, c => ({'<':'&lt;','>':'&gt;','&':'&amp;','"':'&quot;'}[c]));
  }

  function loadPrompt(){
    if(typeof global.loadAgentSystemPrompt === 'function') global.loadAgentSystemPrompt();
  }

  async function loadBenchmarkBrowser(){
    const summaryEl = document.getElementById('benchmarkSummary');
    const listEl = document.getElementById('benchmarkList');
    if(!summaryEl || !listEl) return;
    loadPrompt();
    if(state.corpus){
      renderBenchmarkBrowser();
      return;
    }
    summaryEl.textContent = '讀取 benchmark 題庫中...';
    try {
      if(global.OncoBreastBenchmarkLoader){
        const loaded = await global.OncoBreastBenchmarkLoader.load({
          sources: {
            mainCorpus: BENCHMARK_CORPUS_URL,
            fullResult: BENCHMARK_FULL_RESULT_URL,
            rerunResult: BENCHMARK_FAILED_RERUN_URL,
            adversarialCorpus: BENCHMARK_ADVERSARIAL_CORPUS_URL,
            adversarialResult: BENCHMARK_ADVERSARIAL_RESULT_URL
          }
        });
        state.corpus = loaded.corpus;
        state.fullResult = loaded.results.full;
        state.rerunResult = loaded.results.rerun;
        state.adversarialResult = loaded.results.adversarial;
      } else {
        const [corpusRes, resultRes, rerunRes, adversarialCorpusRes, adversarialResultRes] = await Promise.all([
          fetch(BENCHMARK_CORPUS_URL),
          fetch(BENCHMARK_FULL_RESULT_URL),
          fetch(BENCHMARK_FAILED_RERUN_URL),
          fetch(BENCHMARK_ADVERSARIAL_CORPUS_URL),
          fetch(BENCHMARK_ADVERSARIAL_RESULT_URL)
        ]);
        const mainCorpus = await corpusRes.json();
        const adversarialCorpus = adversarialCorpusRes.ok ? await adversarialCorpusRes.json() : null;
        const mainCases = (mainCorpus.cases || []).map(c => ({...c, benchmark_set:'main'}));
        const adversarialCases = adversarialCorpus && adversarialCorpus.cases
          ? adversarialCorpus.cases.map(c => ({...c, benchmark_set:'adversarial'}))
          : [];
        state.corpus = {
          ...mainCorpus,
          cases: mainCases.concat(adversarialCases),
          adversarial_source: adversarialCorpus ? adversarialCorpus.source : null
        };
        state.fullResult = resultRes.ok ? await resultRes.json() : null;
        state.rerunResult = rerunRes.ok ? await rerunRes.json() : null;
        state.adversarialResult = adversarialResultRes.ok ? await adversarialResultRes.json() : null;
      }
      populateCategoryFilter();
      renderBenchmarkBrowser();
    } catch(err){
      summaryEl.textContent = 'Benchmark 題庫讀取失敗';
      listEl.innerHTML = `<div class="api-benchmark-error">${escapeHtml(String(err && err.message || err))}</div>`;
    }
  }

  function populateCategoryFilter(){
    const sel = document.getElementById('benchmarkCategoryFilter');
    if(!sel || sel.options.length > 1 || !state.corpus) return;
    Array.from(new Set((state.corpus.cases || []).map(c => c.category))).sort().forEach(cat => {
      const opt = document.createElement('option');
      opt.value = cat;
      opt.textContent = cat;
      sel.appendChild(opt);
    });
  }

  function expectedText(expected){
    expected = expected || {};
    const lines = [];
    if(expected.must_call && expected.must_call.length) lines.push(`工具：${expected.must_call.join(' / ')}`);
    if(expected.contains_any && expected.contains_any.length) lines.push(`需包含任一：${expected.contains_any.filter(Boolean).join('、')}`);
    if(expected.contains_regex && expected.contains_regex.length) lines.push(`答案規則：${expected.contains_regex.join('； ')}`);
    if(expected.expected_patch) lines.push(`欄位抽取：${Object.entries(expected.expected_patch).map(([k,v]) => `${k}=${v}`).join('、')}`);
    if(expected.must_not_regex && expected.must_not_regex.length) lines.push(`不可包含：${expected.must_not_regex.join('； ')}`);
    return lines.join('\n') || '無額外答案規則';
  }

  function answerCell(expected){
    expected = expected || {};
    if(expected.expected_patch) return Object.entries(expected.expected_patch).map(([k,v]) => `${k}=${v}`).join('、');
    const parts = [];
    if(expected.contains_any && expected.contains_any.length) parts.push(`包含：${expected.contains_any.filter(Boolean).join(' / ')}`);
    if(expected.contains_regex && expected.contains_regex.length) parts.push(`規則：${expected.contains_regex.join('； ')}`);
    if(expected.must_not_regex && expected.must_not_regex.length) parts.push(`排除：${expected.must_not_regex.join('； ')}`);
    return parts.join('\n') || '見 expected JSON';
  }

  function resultMap(){
    if(global.OncoBreastBenchmarkLoader){
      return global.OncoBreastBenchmarkLoader.resultMap([
        { source:'full', result:state.fullResult },
        { source:'rerun', result:state.rerunResult },
        { source:'adversarial', result:state.adversarialResult }
      ]);
    }
    const map = {};
    const rows = result => (result && (result.case_results || result.results)) || [];
    rows(state.fullResult).forEach(r => { if(r && r.id) map[r.id] = {...r, _run_source:'full'}; });
    rows(state.rerunResult).forEach(r => { if(r && r.id) map[r.id] = {...r, _run_source:'rerun'}; });
    rows(state.adversarialResult).forEach(r => { if(r && r.id) map[r.id] = {...r, _run_source:'adversarial'}; });
    return map;
  }

  function statusBadge(result){
    if(!result) return '<span class="bench-pending">NO RUN</span>';
    return result.passed ? '<span class="bench-pass">PASS</span>' : '<span class="bench-fail">FAIL</span>';
  }

  function runBadge(result){
    if(!result) return '<span class="bench-pending">NO RUN</span>';
    if(result._run_source === 'rerun') return '<span class="bench-rerun">RERUN 2026-06-06</span>';
    if(result._run_source === 'adversarial') return '<span class="bench-adversarial">ADVERSARIAL</span>';
    return '<span class="bench-fullrun">FULL 2026-06-05</span>';
  }

  function summaryHtml(allCases, cases, map, filter){
    const full = state.fullResult && state.fullResult.summary ? state.fullResult.summary : null;
    const rerun = state.rerunResult && state.rerunResult.summary ? state.rerunResult.summary : null;
    const adversarial = state.adversarialResult && state.adversarialResult.summary ? state.adversarialResult.summary : null;
    const latestPassed = allCases.filter(c => map[c.id] && map[c.id].passed).length;
    const latestTotal = allCases.length;
    const parts = [];
    if(full) parts.push(`原始 full run ${full.passed}/${full.total} 通過 (${Math.round((full.pass_rate || 0) * 1000) / 10}%)`);
    if(rerun) parts.push(`prompt 修正後失敗題重測 ${rerun.passed}/${rerun.total} 通過`);
    if(adversarial) parts.push(`困難題 ${adversarial.passed}/${adversarial.total} 通過`);
    const combined = latestTotal ? `目前表格合併顯示 ${latestPassed}/${latestTotal} PASS` : '尚無題庫';
    const note = adversarial ? '包含主題庫與 adversarial 困難題；困難題用來暴露錯誤，不用來灌高通過率。' : (rerun ? '尚未重跑完整 300 題；合併結果 = 原始通過題 + 失敗題重測。' : '目前只載入原始 full run。');
    return `<b>${escapeHtml(combined)}</b><span>${escapeHtml(parts.join('； ') || '尚無結果檔')}</span><span>${escapeHtml(note)}</span><span>目前顯示 ${cases.length}/${allCases.length} 題${filter ? ' · ' + escapeHtml(filter) : ''}</span>`;
  }

  function renderBenchmarkBrowser(){
    const summaryEl = document.getElementById('benchmarkSummary');
    const listEl = document.getElementById('benchmarkList');
    if(!state.corpus || !summaryEl || !listEl) return;
    const filter = (document.getElementById('benchmarkCategoryFilter') || {}).value || '';
    const allCases = state.corpus.cases || [];
    const cases = filter ? allCases.filter(c => c.category === filter) : allCases;
    const map = resultMap();
    summaryEl.innerHTML = summaryHtml(allCases, cases, map, filter);
    listEl.innerHTML = `<table class="api-benchmark-table">
      <thead>
        <tr>
          <th>ID</th>
          <th>Status</th>
          <th>Run</th>
          <th>Category</th>
          <th>Question</th>
          <th>Reference answer</th>
          <th>Agent answer</th>
          <th>Actual called_tools</th>
          <th>Checks / error</th>
        </tr>
      </thead>
      <tbody>
        ${cases.map((c, idx) => {
          const expected = c.expected || {};
          const r = map[c.id];
          const reference = c.reference_answer || answerCell(expected);
          const tools = r ? (r.called_tools || []).join('\n') : (expected.must_call || []).map(t => `expected only: ${t}`).join('\n');
          const note = c.failure_note ? `Failure note: ${c.failure_note}` : '';
          const checkText = r ? (r.passed ? (r.checks || []).join('\n') : (r.error || 'failed')) : expectedText(expected);
          const checks = [note, checkText].filter(Boolean).join('\n\n');
          return `<tr>
            <td><code>${escapeHtml(c.id || String(idx + 1))}</code></td>
            <td>${statusBadge(r)}</td>
            <td>${runBadge(r)}</td>
            <td>${escapeHtml(c.category || '')}</td>
            <td class="question">${escapeHtml(c.question || '')}</td>
            <td><pre>${escapeHtml(reference)}</pre></td>
            <td><pre>${escapeHtml(r ? (r.agent_reply || '') : '尚未執行 agent')}</pre></td>
            <td><pre>${escapeHtml(tools)}</pre></td>
            <td><pre>${escapeHtml(checks)}</pre></td>
          </tr>`;
        }).join('')}
      </tbody>
    </table>`;
  }

  global.OncoBreastBenchmarkBrowser = {
    load: loadBenchmarkBrowser,
    render: renderBenchmarkBrowser,
    state
  };
  global.loadBenchmarkBrowser = loadBenchmarkBrowser;
  global.renderBenchmarkBrowser = renderBenchmarkBrowser;
})(window);
