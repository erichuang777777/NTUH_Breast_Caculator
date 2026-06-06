(function(global){
  'use strict';

  const DEFAULT_SOURCES = {
    mainCorpus: 'data/agent_bench/bench_v1.json',
    fullResult: 'data/agent_bench/bench_v1_results_2026-06-05.json',
    rerunResult: 'data/agent_bench/bench_failed_rerun_final_2026-06-06.json',
    adversarialCorpus: 'data/agent_bench/bench_adversarial_2026-06-06.json',
    adversarialResult: 'data/agent_bench/bench_adversarial_results_2026-06-06.json'
  };

  async function readJson(fetchImpl, url, required){
    const res = await fetchImpl(url);
    if(!res.ok){
      if(required) throw new Error(`Failed to load ${url}: ${res.status}`);
      return null;
    }
    return await res.json();
  }

  function rows(result){
    return (result && (result.case_results || result.results)) || [];
  }

  function resultMap(results){
    const map = {};
    (results || []).forEach(item => {
      const source = item && item.source;
      rows(item && item.result).forEach(row => {
        if(row && row.id) map[row.id] = {...row, _run_source: source || 'unknown'};
      });
    });
    return map;
  }

  function tagCases(cases, setName){
    return (cases || []).map(c => ({...c, benchmark_set:setName}));
  }

  async function load(options){
    const opts = options || {};
    const fetchImpl = opts.fetch || global.fetch;
    const sources = {...DEFAULT_SOURCES, ...(opts.sources || {})};
    const [mainCorpus, fullResult, rerunResult, adversarialCorpus, adversarialResult] = await Promise.all([
      readJson(fetchImpl, sources.mainCorpus, true),
      readJson(fetchImpl, sources.fullResult, false),
      readJson(fetchImpl, sources.rerunResult, false),
      readJson(fetchImpl, sources.adversarialCorpus, false),
      readJson(fetchImpl, sources.adversarialResult, false)
    ]);
    const cases = tagCases(mainCorpus.cases, 'main').concat(tagCases(adversarialCorpus && adversarialCorpus.cases, 'adversarial'));
    return {
      corpus: {
        ...mainCorpus,
        cases,
        adversarial_source: adversarialCorpus ? adversarialCorpus.source : null
      },
      results: {
        full: fullResult,
        rerun: rerunResult,
        adversarial: adversarialResult
      },
      resultMap: resultMap([
        { source:'full', result:fullResult },
        { source:'rerun', result:rerunResult },
        { source:'adversarial', result:adversarialResult }
      ])
    };
  }

  global.OncoBreastBenchmarkLoader = {
    sources: DEFAULT_SOURCES,
    load,
    rows,
    resultMap
  };
})(window);
