(function(global){
  'use strict';

  const DEFAULT_CONFIG_KEY = 'nhi_dashboard_agent_api_config';

  function defaultConfig(locationLike){
    const loc = locationLike || global.location || {};
    const host = loc.hostname || '';
    const isLocal = host === '127.0.0.1' || host === 'localhost';
    return {
      enabled: isLocal,
      endpoint: isLocal ? '/api/agent' : '',
      headers: isLocal ? { 'x-client-app':'oncobreast-local-ollama-demo' } : {}
    };
  }

  function readConfig(options){
    const opts = options || {};
    const storage = opts.storage || global.localStorage;
    const key = opts.storageKey || DEFAULT_CONFIG_KEY;
    const fallback = opts.fallback || defaultConfig(opts.location || global.location);
    try {
      const raw = storage && storage.getItem ? storage.getItem(key) : '';
      if(!raw) return fallback;
      const saved = JSON.parse(raw || '{}');
      return {
        enabled: !!saved.enabled,
        endpoint: String(saved.endpoint || '').trim(),
        headers: saved.headers && typeof saved.headers === 'object' ? saved.headers : {}
      };
    } catch(e){
      if(opts.onError) opts.onError(e);
      return fallback;
    }
  }

  function writeConfig(config, options){
    const opts = options || {};
    const storage = opts.storage || global.localStorage;
    const key = opts.storageKey || DEFAULT_CONFIG_KEY;
    const cfg = {
      enabled: !!(config && config.enabled),
      endpoint: String((config && config.endpoint) || '').trim(),
      headers: config && config.headers && typeof config.headers === 'object' ? config.headers : {}
    };
    try {
      if(storage && storage.setItem) storage.setItem(key, JSON.stringify(cfg));
    } catch(e){
      if(opts.onError) opts.onError(e);
    }
    return cfg;
  }

  function toolRegistry(tools){
    return (tools || []).map(t => ({ id:t.id, label:t.label, aliases:t.aliases || [] }));
  }

  function buildPayload(options){
    const opts = options || {};
    const ctx = opts.context || {};
    return {
      message: opts.message || '',
      patient_context: ctx.p || opts.patient_context || {},
      derived: opts.derived || {
        stage: ctx.stage || {},
        subtype: ctx.subtype || '',
        missing: ctx.missing || [],
        phase_label: ctx.phaseLabel || ''
      },
      report_text: opts.reportText || '',
      tool_registry: toolRegistry(opts.tools || []),
      client: {
        app: opts.app || 'OncoBreast Calculator',
        version: opts.version || ''
      }
    };
  }

  async function post(config, payload, options){
    const cfg = config || {};
    if(!cfg.enabled || !cfg.endpoint) return null;
    const opts = options || {};
    const fetchImpl = opts.fetch || global.fetch;
    const res = await fetchImpl(cfg.endpoint, {
      method: 'POST',
      headers: {
        'content-type': 'application/json',
        'x-client-app': opts.clientApp || 'oncobreast-copilot',
        ...(cfg.headers || {})
      },
      body: JSON.stringify(payload || {})
    });
    if(!res.ok) return null;
    return await res.json().catch(() => ({}));
  }

  global.OncoBreastAgentAdapter = {
    configKey: DEFAULT_CONFIG_KEY,
    defaultConfig,
    readConfig,
    writeConfig,
    toolRegistry,
    buildPayload,
    post
  };
})(window);
