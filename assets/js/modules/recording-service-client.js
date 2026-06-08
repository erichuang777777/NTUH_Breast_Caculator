(function(global){
  'use strict';

  const DEFAULT_CONFIG_KEY = 'nhi_patient_center_recording_service_config';

  function defaultConfig(){
    return {
      enabled: false,
      baseUrl: '',
      headers: {}
    };
  }

  function cleanBaseUrl(value){
    return String(value || '').trim().replace(/\/+$/, '');
  }

  function readConfig(options){
    const opts = options || {};
    const storage = opts.storage || global.localStorage;
    const key = opts.storageKey || DEFAULT_CONFIG_KEY;
    const fallback = opts.fallback || defaultConfig();
    try {
      const raw = storage && storage.getItem ? storage.getItem(key) : '';
      if(!raw) return fallback;
      const saved = JSON.parse(raw || '{}');
      return {
        enabled: !!saved.enabled,
        baseUrl: cleanBaseUrl(saved.baseUrl),
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
      baseUrl: cleanBaseUrl(config && config.baseUrl),
      headers: config && config.headers && typeof config.headers === 'object' ? config.headers : {}
    };
    try {
      if(storage && storage.setItem) storage.setItem(key, JSON.stringify(cfg));
    } catch(e){
      if(opts.onError) opts.onError(e);
    }
    return cfg;
  }

  function ensureConfig(config){
    const cfg = config || {};
    if(!cfg.enabled || !cleanBaseUrl(cfg.baseUrl)){
      throw new Error('Recording service is not configured.');
    }
    return {
      enabled: true,
      baseUrl: cleanBaseUrl(cfg.baseUrl),
      headers: cfg.headers && typeof cfg.headers === 'object' ? cfg.headers : {}
    };
  }

  async function request(config, path, options){
    const cfg = ensureConfig(config);
    const opts = options || {};
    const fetchImpl = opts.fetch || global.fetch;
    const headers = {...(cfg.headers || {}), ...(opts.headers || {})};
    const res = await fetchImpl(cfg.baseUrl + path, {
      method: opts.method || 'GET',
      headers,
      body: opts.body
    });
    const text = await res.text();
    let data = {};
    if(text){
      try { data = JSON.parse(text); }
      catch(e){ data = { raw:text }; }
    }
    if(!res.ok){
      const message = data && (data.error || data.message) ? (data.error || data.message) : `Recording service HTTP ${res.status}`;
      throw new Error(message);
    }
    return data;
  }

  function buildEncounterPayload(options){
    const opts = options || {};
    return {
      patient_context: opts.patientContext || {},
      derived: opts.derived || {},
      consent_confirmed: !!opts.consentConfirmed,
      client: {
        app: 'OncoBreast Calculator Patient Center',
        version: opts.version || '',
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || ''
      }
    };
  }

  async function health(config, options){
    return await request(config, '/health', { ...(options || {}), method:'GET' });
  }

  async function createEncounter(config, payload, options){
    return await request(config, '/encounters', {
      ...(options || {}),
      method: 'POST',
      headers: {
        'content-type': 'application/json',
        ...((options && options.headers) || {})
      },
      body: JSON.stringify(payload || {})
    });
  }

  async function uploadAudio(config, encounterId, blob, metadata, options){
    if(!encounterId) throw new Error('Missing encounter id.');
    if(!blob || !blob.size) throw new Error('Missing audio blob.');
    const form = new FormData();
    form.append('audio', blob, metadata && metadata.filename ? metadata.filename : 'recording.webm');
    form.append('metadata', JSON.stringify(metadata || {}));
    return await request(config, `/encounters/${encodeURIComponent(encounterId)}/audio`, {
      ...(options || {}),
      method: 'POST',
      body: form
    });
  }

  async function processEncounter(config, encounterId, payload, options){
    if(!encounterId) throw new Error('Missing encounter id.');
    return await request(config, `/encounters/${encodeURIComponent(encounterId)}/process`, {
      ...(options || {}),
      method: 'POST',
      headers: {
        'content-type': 'application/json',
        ...((options && options.headers) || {})
      },
      body: JSON.stringify(payload || {})
    });
  }

  async function getEncounter(config, encounterId, options){
    if(!encounterId) throw new Error('Missing encounter id.');
    return await request(config, `/encounters/${encodeURIComponent(encounterId)}`, {
      ...(options || {}),
      method: 'GET'
    });
  }

  global.OncoBreastRecordingServiceClient = {
    configKey: DEFAULT_CONFIG_KEY,
    defaultConfig,
    readConfig,
    writeConfig,
    buildEncounterPayload,
    health,
    createEncounter,
    uploadAudio,
    processEncounter,
    getEncounter
  };
})(window);
