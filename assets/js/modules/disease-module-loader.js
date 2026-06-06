(function(global){
  'use strict';

  const DEFAULT_REGISTRY = {
    breast: 'assets/js/modules/disease/breast/manifest.json'
  };

  const state = {
    registry: {...DEFAULT_REGISTRY},
    manifests: {}
  };

  function register(id, url){
    if(!id || !url) return;
    state.registry[String(id)] = String(url);
  }

  function list(){
    return Object.keys(state.registry).map(id => ({
      id,
      url: state.registry[id],
      loaded: !!state.manifests[id],
      label: state.manifests[id] ? state.manifests[id].label : id
    }));
  }

  function validateManifest(manifest){
    const errors = [];
    if(!manifest || typeof manifest !== 'object') errors.push('manifest must be an object');
    if(manifest && manifest.schema !== 'onco_disease_module_manifest.v1') errors.push('schema must be onco_disease_module_manifest.v1');
    if(manifest && !manifest.id) errors.push('id is required');
    if(manifest && !manifest.label) errors.push('label is required');
    ['field_groups', 'tools', 'agent_tools'].forEach(key => {
      if(manifest && manifest[key] != null && !Array.isArray(manifest[key])) errors.push(`${key} must be an array`);
    });
    return { ok: errors.length === 0, errors };
  }

  async function load(id, options){
    const opts = options || {};
    const fetchImpl = opts.fetch || global.fetch;
    const key = String(id || 'breast');
    if(state.manifests[key] && !opts.reload) return state.manifests[key];
    const url = opts.url || state.registry[key];
    if(!url) throw new Error(`Unknown disease module: ${key}`);
    const res = await fetchImpl(url, { cache: opts.cache || 'no-store' });
    if(!res.ok) throw new Error(`Failed to load disease manifest ${key}: ${res.status}`);
    const manifest = await res.json();
    const validation = validateManifest(manifest);
    if(!validation.ok) throw new Error(`Invalid disease manifest ${key}: ${validation.errors.join('; ')}`);
    state.manifests[key] = manifest;
    return manifest;
  }

  function get(id){
    return state.manifests[String(id || 'breast')] || null;
  }

  function agentTools(id){
    const manifest = get(id);
    return manifest && Array.isArray(manifest.agent_tools) ? manifest.agent_tools : [];
  }

  function fieldGroups(id){
    const manifest = get(id);
    return manifest && Array.isArray(manifest.field_groups) ? manifest.field_groups : [];
  }

  function tools(id){
    const manifest = get(id);
    return manifest && Array.isArray(manifest.tools) ? manifest.tools : [];
  }

  global.OncoDiseaseModules = {
    register,
    list,
    load,
    get,
    validateManifest,
    agentTools,
    fieldGroups,
    tools,
    state
  };
})(window);
