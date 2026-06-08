(function(global){
  'use strict';

  function readHistory(options){
    const opts = options || {};
    const storage = opts.storage || global.localStorage;
    const key = opts.storageKey;
    const initialMessage = opts.initialMessage || '';
    try {
      const history = JSON.parse((storage && storage.getItem && storage.getItem(key)) || '[]');
      if(Array.isArray(history) && history.length) return history;
    } catch(e){
      if(opts.onError) opts.onError(e);
    }
    return [{ role:'agent', response:initialMessage }];
  }

  function saveHistory(history, options){
    const opts = options || {};
    const storage = opts.storage || global.localStorage;
    const key = opts.storageKey;
    const maxItems = opts.maxItems || 12;
    try {
      if(storage && storage.setItem) storage.setItem(key, JSON.stringify((history || []).slice(-maxItems)));
      return true;
    } catch(e){
      if(opts.onError) opts.onError(e);
      return false;
    }
  }

  function pushHistory(history, role, response, options){
    const next = Array.isArray(history) ? history.slice() : [];
    next.push({ role: role === 'user' ? 'user' : 'agent', response });
    saveHistory(next, options);
    return next;
  }

  function clearHistory(options){
    const opts = options || {};
    const storage = opts.storage || global.localStorage;
    const key = opts.storageKey;
    try {
      if(storage && storage.removeItem) storage.removeItem(key);
      return true;
    } catch(e){
      if(opts.onError) opts.onError(e);
      return false;
    }
  }

  function estimateTokens(text){
    const s = String(text || '');
    if(!s) return 0;
    const cjk = (s.match(/[\u4e00-\u9fff]/g) || []).length;
    const nonCjk = s.length - cjk;
    return Math.ceil(cjk * 1.15 + nonCjk / 4);
  }

  function compactLen(value){
    if(value == null) return 0;
    try { return JSON.stringify(value).length; }
    catch(e){ return String(value || '').length; }
  }

  function contextUsage(options){
    const opts = options || {};
    const history = opts.history || [];
    const patient = opts.patientContext || {};
    const derived = opts.derived || {};
    const reportText = opts.reportText || '';
    const inputText = opts.inputText || '';
    const tools = opts.tools || [];
    const limit = opts.limit || 8192;
    const maxTurns = opts.maxTurns || 12;
    const overheadTokens = opts.overheadTokens || 1350;
    const patientChars = compactLen(patient) + compactLen(derived);
    const tokens = overheadTokens
      + estimateTokens(JSON.stringify(history))
      + estimateTokens(JSON.stringify(patient))
      + estimateTokens(JSON.stringify(derived))
      + estimateTokens(reportText)
      + estimateTokens(inputText)
      + estimateTokens(JSON.stringify(tools));
    return {
      tokens,
      percent: Math.min(999, Math.round(tokens / limit * 100)),
      limit,
      turns: Math.max(0, history.length - 1),
      maxTurns,
      chars: {
        history: compactLen(history),
        patient: patientChars,
        report: String(reportText || '').length,
        input: String(inputText || '').length,
        tools: compactLen(tools)
      }
    };
  }

  function meterHtml(usage){
    const u = usage || contextUsage();
    const tone = u.percent >= 90 ? 'danger' : (u.percent >= 70 ? 'warn' : 'ok');
    const label = u.percent >= 90 ? '接近上限' : (u.percent >= 70 ? '偏高' : '正常');
    const reportPart = u.chars && u.chars.report ? ` · 報告 ${Math.round(u.chars.report / 100) / 10}k字` : '';
    return `<div class="dashboard-agent-context-meter ${tone}" title="前端粗估 token：含固定 overhead（system prompt、工具/JSON 包裝）、patient context、工具 registry、對話紀錄與已貼上的報告文字；實際 token 以模型 tokenizer 為準。">
      <div class="dashboard-agent-context-line">
        <span>Context est. ${u.tokens.toLocaleString()} / ${u.limit.toLocaleString()}</span>
        <b>${label} ${u.percent}%</b>
      </div>
      <div class="dashboard-agent-context-bar"><i style="width:${Math.min(100, u.percent)}%"></i></div>
      <div class="dashboard-agent-context-meta">對話 ${u.turns}/${u.maxTurns}${reportPart}</div>
      ${u.percent >= 70 ? '<button class="dashboard-agent-context-action" type="button" onclick="dashboardAgentClearHistory()">清除對話紀錄</button>' : ''}
    </div>`;
  }

  global.OncoBreastAgentPanelState = {
    readHistory,
    saveHistory,
    pushHistory,
    clearHistory,
    estimateTokens,
    compactLen,
    contextUsage,
    meterHtml
  };
})(window);
