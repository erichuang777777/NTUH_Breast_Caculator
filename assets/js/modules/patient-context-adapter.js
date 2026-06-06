(function(global){
  'use strict';

  const DEFAULT_STORAGE_KEY = '_patient_workspace';

  function clone(value){
    if(value == null || typeof value !== 'object') return value;
    try { return JSON.parse(JSON.stringify(value)); }
    catch(e){ return Array.isArray(value) ? value.slice() : {...value}; }
  }

  function create(defaults, data){
    return {...(defaults || {}), ...(data || {})};
  }

  function load(options){
    const opts = options || {};
    const storage = opts.storage || global.localStorage;
    const key = opts.storageKey || DEFAULT_STORAGE_KEY;
    let patient = create(opts.defaults, {});
    try {
      const saved = storage && storage.getItem ? storage.getItem(key) : '';
      if(saved) patient = create(opts.defaults, JSON.parse(saved));
    } catch(e){
      if(opts.onError) opts.onError(e);
    }
    if(typeof opts.migrate === 'function') patient = opts.migrate(patient) || patient;
    if(typeof opts.normalize === 'function') patient = opts.normalize(patient) || patient;
    return patient;
  }

  function save(patient, options){
    const opts = options || {};
    const storage = opts.storage || global.localStorage;
    const key = opts.storageKey || DEFAULT_STORAGE_KEY;
    try {
      if(storage && storage.setItem) storage.setItem(key, JSON.stringify(patient || {}));
      return true;
    } catch(e){
      if(opts.onError) opts.onError(e);
      return false;
    }
  }

  function clear(options){
    const opts = options || {};
    const storage = opts.storage || global.localStorage;
    const key = opts.storageKey || DEFAULT_STORAGE_KEY;
    try {
      if(storage && storage.removeItem) storage.removeItem(key);
      return true;
    } catch(e){
      if(opts.onError) opts.onError(e);
      return false;
    }
  }

  function validPatchEntries(patch, defaults){
    const schema = defaults || {};
    return Object.entries(patch || {}).filter(([key, value]) => {
      return Object.prototype.hasOwnProperty.call(schema, key)
        && value !== undefined
        && value !== null
        && value !== '';
    });
  }

  function applyPatch(patient, patch, defaults, normalizers){
    const target = patient || {};
    const applied = [];
    validPatchEntries(patch, defaults).forEach(([key, value]) => {
      const normalize = normalizers && normalizers[key];
      target[key] = normalize ? normalize(value, target) : String(value);
      applied.push(key);
    });
    return { patient: target, applied };
  }

  function bundle(patient, options){
    const opts = options || {};
    return {
      schema: opts.schema || 'onco_breast_patient_context_bundle.v1',
      generated_at: new Date().toISOString(),
      patient_context: clone(patient || {}),
      derived: clone(opts.derived || {}),
      source: opts.source || 'workspace'
    };
  }

  global.OncoBreastPatientContext = {
    storageKey: DEFAULT_STORAGE_KEY,
    create,
    load,
    save,
    clear,
    applyPatch,
    validPatchEntries,
    bundle
  };
})(window);
