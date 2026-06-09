(function(global){
  'use strict';

  const DEFAULT_CONFIG_KEY = 'nhi_dashboard_agent_api_config';
  const CLOUD_MODEL = 'gpt-oss:120b';
  const LOCAL_MODEL = 'gemma4:31B';

  function defaultModel(locationLike){
    const loc = locationLike || global.location || {};
    const host = loc.hostname || '';
    return (host === '127.0.0.1' || host === 'localhost') ? LOCAL_MODEL : CLOUD_MODEL;
  }

  function normalizeModel(value, locationLike){
    const raw = String(value || '').trim();
    if(!raw) return defaultModel(locationLike);
    if(raw.toLowerCase() === 'gemma4:31b-cloud' || raw.toLowerCase() === 'gemma4:31b') return LOCAL_MODEL;
    if(raw.toLowerCase() === 'gptoss120b') return CLOUD_MODEL;
    return raw;
  }

  function defaultConfig(locationLike){
    const loc = locationLike || global.location || {};
    const protocol = loc.protocol || '';
    const host = loc.hostname || '';
    const port = String(loc.port || '');
    const hasHttpApi = protocol === 'http:' || protocol === 'https:';
    const isLocal = host === '127.0.0.1' || host === 'localhost';
    const endpoint = hasHttpApi
      ? (isLocal && port !== '8080' ? 'http://127.0.0.1:8080/api/agent' : '/api/agent')
      : '';
    return {
      enabled: hasHttpApi,
      endpoint,
      model: defaultModel(loc),
      headers: hasHttpApi ? { 'x-client-app': isLocal ? 'oncobreast-local-ollama-demo' : 'oncobreast-copilot' } : {}
    };
  }

  function readConfig(options){
    const opts = options || {};
    const storage = opts.storage || global.localStorage;
    const key = opts.storageKey || DEFAULT_CONFIG_KEY;
    const fallback = opts.fallback || defaultConfig(opts.location || global.location);
    const loc = opts.location || global.location || {};
    try {
      const host = loc.hostname || '';
      const isLocal = host === '127.0.0.1' || host === 'localhost';
      const raw = storage && storage.getItem ? storage.getItem(key) : '';
      if(!raw) return fallback;
      const saved = JSON.parse(raw || '{}');
      const endpoint = String(saved.endpoint || '').trim();
      if(!endpoint && fallback && fallback.endpoint) return fallback;
      if(isLocal) return fallback;
      if(/^https?:\/\/(127\.0\.0\.1|localhost)(:|\/|$)/i.test(endpoint)) return fallback;
      return {
        enabled: !!saved.enabled,
        endpoint,
        model: normalizeModel(saved.model || fallback.model, loc),
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
      model: normalizeModel((config && config.model) || '', opts.location || global.location),
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
      preferred_model: opts.model || opts.preferred_model || '',
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
    const data = await res.json().catch(() => ({}));
    if(!res.ok) {
      return {
        ok: false,
        status: res.status,
        error: data.error || data.message || `Agent API HTTP ${res.status}`,
        detail: data.detail || ''
      };
    }
    return data;
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
