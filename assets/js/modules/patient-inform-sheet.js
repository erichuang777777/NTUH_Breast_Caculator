(function(global){
  'use strict';

  function esc(value){
    return String(value == null ? '' : value).replace(/[<>&"]/g, c => ({'<':'&lt;','>':'&gt;','&':'&amp;','"':'&quot;'}[c]));
  }

  function hasValue(value){
    return value !== undefined && value !== null && String(value).trim() !== '';
  }

  function display(value, fallback){
    return hasValue(value) ? esc(value) : `<span class="muted">${esc(fallback || '待補')}</span>`;
  }

  function parsePercent(value){
    const raw = String(value == null ? '' : value).trim();
    if(!raw) return null;
    if(raw === '+') return 100;
    if(raw === '-') return 0;
    const match = raw.match(/\d+(?:\.\d+)?/);
    if(!match) return null;
    return Math.max(0, Math.min(100, Number(match[0])));
  }

  function percentLabel(value){
    const raw = String(value == null ? '' : value).trim();
    if(!raw) return '';
    if(raw === '+') return '+';
    if(raw === '-') return '-';
    if(/^\d+(?:\.\d+)?$/.test(raw)) return `${raw}%`;
    return raw;
  }

  function sideLabel(side){
    return ({L:'左乳', R:'右乳', B:'雙側'}[side] || '');
  }

  function quadrantLabel(q){
    return ({UO:'外上', UI:'內上', LO:'外下', LI:'內下', central:'中央/乳頭', overlapping:'跨象限'}[q] || '部位待補');
  }

  function gradeLabel(g){
    const s = String(g || '').trim().toLowerCase();
    const roman = ({'1':'I','2':'II','3':'III',i:'I',ii:'II',iii:'III'}[s] || '');
    return roman ? `Gr${roman}` : '';
  }

  function sizeCm(size){
    const n = Number(String(size || '').replace(/[^\d.]/g, ''));
    if(!Number.isFinite(n) || n <= 0) return '';
    return `${(n / 10).toFixed(1).replace(/\.0$/, '')} cm`;
  }

  function stageValue(derived){
    const st = (derived && derived.stage) || {};
    const tnm = [st.T, st.N, st.M].filter(Boolean).join('');
    const prefix = st.kind === 'pTNM' ? 'p' : (st.kind === 'ypTNM' ? 'yp' : (st.kind === 'cTNM' ? 'c' : ''));
    return {
      tnm: tnm ? `${prefix}${tnm}` : '',
      anatomic: st.anatomic || '',
      prognostic: st.prognostic || ''
    };
  }

  function stageLadder(stage){
    const active = String(stage || '').replace(/[ABC]$/i, '');
    return `<div class="stage-ladder">${['I','II','III','IV'].map(s => (
      `<div class="stage-step ${active === s ? 'active' : ''}"><span>${s}</span></div>`
    )).join('')}</div>`;
  }

  function breastMap(p, derived){
    p = p || {};
    const q = p.quadrant || '';
    const active = cls => q === cls ? ' active' : '';
    const icd = (derived && derived.icd) || {};
    return `<div class="breast-map-card">
      <svg class="breast-map" viewBox="0 0 160 132" role="img" aria-label="乳房象限圖">
        <path class="breast-outline" d="M80 8c32 0 58 25 58 56 0 33-26 60-58 60S22 97 22 64C22 33 48 8 80 8Z"/>
        <path class="quad${active('UI')}" d="M80 18c-25 0-46 20-46 45h46Z"/>
        <path class="quad${active('UO')}" d="M80 18c25 0 46 20 46 45H80Z"/>
        <path class="quad${active('LI')}" d="M34 63c0 27 21 49 46 49V63Z"/>
        <path class="quad${active('LO')}" d="M80 63v49c25 0 46-22 46-49Z"/>
        <circle class="nipple${active('central')}" cx="80" cy="63" r="10"/>
        ${q === 'overlapping' ? '<circle class="overlap-ring" cx="80" cy="63" r="50"/>' : ''}
      </svg>
      <div class="map-meta">
        <b>${display(sideLabel(p.side), '側別待補')} ${esc(quadrantLabel(q))}</b>
        <span>${display(icd.ntuhNo ? `重卡 ${icd.ntuhNo}` : '', '重卡待補')} ${icd.code ? `｜${esc(icd.code)}` : ''}</span>
      </div>
    </div>`;
  }

  function biomarkerBar(label, value, options){
    const pct = parsePercent(value);
    const width = pct == null ? 0 : pct;
    const tone = options && options.tone ? options.tone : '';
    return `<div class="bio-row ${tone}">
      <div class="bio-head"><b>${esc(label)}</b><span>${display(percentLabel(value), '待補')}</span></div>
      <div class="bio-track"><i style="width:${width}%"></i></div>
    </div>`;
  }

  function binaryMarkerBar(label, status, detail){
    const normalized = String(status || '').trim().toLowerCase();
    const positive = ['+','pos','positive','3+'].includes(normalized);
    const negative = ['-','neg','negative','0','1+','low'].includes(normalized);
    const labelText = positive ? '陽性' : (negative ? '陰性' : '');
    const detailText = detail ? `｜${detail}` : '';
    const displayText = labelText ? `${labelText}${detailText}` : detail;
    return `<div class="bio-row binary ${positive ? 'positive' : (negative ? 'negative' : '')}">
      <div class="bio-head"><b>${esc(label)}</b><span>${display(displayText, '待補')}</span></div>
      <div class="binary-track"><i class="neg">陰性</i><i class="pos">陽性</i><b class="marker"></b></div>
    </div>`;
  }

  function her2BinaryStatus(p){
    p = p || {};
    if(p.her2 === '+') return '+';
    if(p.her2 === '-' || p.her2 === 'low') return '-';
    if(p.her2_fish === '+') return '+';
    if(p.her2_fish === '-') return '-';
    const ihc = String(p.her2_ihc || '').trim();
    if(ihc === '3+' || ihc === '3') return '+';
    if(['0','1','1+'].includes(ihc)) return '-';
    return '';
  }

  function her2Detail(p){
    p = p || {};
    const parts = [];
    if(p.her2_ihc) parts.push(`IHC ${p.her2_ihc}`);
    if(p.her2_fish) parts.push(`FISH ${p.her2_fish === '+' ? 'positive' : (p.her2_fish === '-' ? 'negative' : p.her2_fish)}`);
    return parts.join(' / ');
  }

  function gradeMeter(grade){
    const g = Number(String(grade || '').replace(/[^\d]/g, ''));
    return `<div class="grade-meter">${[1,2,3].map(n => `<span class="${g === n ? 'active' : ''}">G${n}</span>`).join('')}</div>`;
  }

  function predictPanel(predict){
    if(!predict || predict.status !== 'ok'){
      return `<div class="empty-visual">PREDICT 3.0<br><span>${esc((predict && predict.message) || '資料不足或不適用')}</span></div>`;
    }
    const ten = Number(predict.tenYearSurvival);
    const benefit = Number(predict.tenYearBenefit);
    const safeTen = Number.isFinite(ten) ? Math.max(0, Math.min(100, ten)) : 0;
    const safeBenefit = Number.isFinite(benefit) ? Math.max(0, Math.min(20, benefit)) : 0;
    return `<div class="predict-visual">
      <div class="predict-main">
        <div class="ring" style="--pct:${safeTen * 3.6}deg"><span>${Number.isFinite(ten) ? ten.toFixed(1) : '—'}%</span></div>
        <b>10 年整體存活率</b>
      </div>
      <div class="predict-benefit">
        <span>治療效益估算</span>
        <div class="benefit-track"><i style="width:${Math.min(100, safeBenefit * 5)}%"></i></div>
        <b>${Number.isFinite(benefit) ? `+${benefit.toFixed(1)}%` : '待補'}</b>
      </div>
    </div>`;
  }

  function planCard(title, items, foot){
    const rows = (items || []).filter(hasValue);
    return `<div class="plan-card">
      <h3>${esc(title)}</h3>
      ${rows.length ? rows.map(x => `<div class="plan-row">${esc(x)}</div>`).join('') : '<div class="plan-empty">尚未填寫</div>'}
      ${foot ? `<div class="plan-foot">${esc(foot)}</div>` : ''}
    </div>`;
  }

  function cycleStrip(regimen){
    if(!regimen || !regimen.selected) return '<div class="cycle-empty">尚未選擇化療配方</div>';
    const match = String(regimen.schedule || '').match(/[×x]\s*(\d+)/i);
    const n = match ? Math.max(1, Math.min(12, Number(match[1]))) : 4;
    return `<div class="cycle-strip">${Array.from({length:n}).map((_, i) => `<span>${i + 1}</span>`).join('')}</div>`;
  }

  function render(payload){
    payload = payload || {};
    const bundle = payload.bundle || {};
    const p = bundle.patient_context || {};
    const derived = bundle.derived || {};
    const stage = stageValue(derived);
    const regimen = payload.regimen || {};
    const predict = payload.predict || {};
    const today = payload.date || new Date().toLocaleDateString('zh-TW');
    const subtype = derived.subtype || '';
    const her2Status = her2BinaryStatus(p);
    const her2Text = her2Detail(p);
    const chemoItems = regimen.selected ? [
      regimen.name,
      regimen.schedule,
      (regimen.drugs || []).join(' + '),
      `估算總藥費：${regimen.price || '待計算'}`,
      `基準：${regimen.priceBasis || '待確認'}`
    ] : [];
    const medItems = (payload.medications || []).map(m => `${m.name}｜${m.schedule || '療程待填'}｜${m.cost || '費用待估'}`);
    const regimenPrice = regimen.selected ? regimen.price : '';
    const regimenSelfPay = regimen.selected ? (regimen.selfPay || []).join('、') : '';
    const regimenBasis = regimen.selected ? regimen.priceBasis : '';
    const regimenNhi = regimen.selected ? (regimen.nhi || []).join('、') : '';

    return `<!DOCTYPE html><html lang="zh-TW"><head><meta charset="utf-8">
      <title>乳癌病人治療說明單</title>
      <style>
        @page{size:A4;margin:10mm}
        *{box-sizing:border-box}
        body{margin:0;font-family:"Noto Sans TC","Microsoft JhengHei",Arial,sans-serif;color:#172033;background:#fff;font-size:11px;line-height:1.35}
        .sheet{width:190mm;min-height:277mm;margin:0 auto;padding:0;display:grid;grid-template-rows:auto auto 1fr auto;gap:7mm}
        .top{display:grid;grid-template-columns:1.1fr .9fr;gap:6mm;align-items:stretch;border-bottom:2px solid #0f766e;padding-bottom:5mm}
        h1{margin:0 0 2mm;color:#0f766e;font-size:21px;letter-spacing:.02em}
        .subtitle{color:#64748b;font-size:10px}.date{text-align:right;color:#64748b;font-weight:700}
        .hero-line{margin-top:5mm;font-size:17px;font-weight:900;color:#111827}
        .hero-line span{color:#0f766e}
        .hero-sub{margin-top:2mm;color:#475569;font-size:12px;font-weight:800}
        .breast-map-card{display:grid;grid-template-columns:38mm minmax(0,1fr);gap:4mm;align-items:center;border:1px solid #d8e3ee;border-radius:8px;padding:4mm;background:#f8fafc}
        .breast-map{width:38mm;height:32mm}.breast-outline{fill:#fff;stroke:#94a3b8;stroke-width:2}.quad{fill:#e2e8f0;stroke:#fff;stroke-width:1.2}.quad.active{fill:#fb7185}.nipple{fill:#fbcfe8;stroke:#be185d}.nipple.active{fill:#be185d}.overlap-ring{fill:none;stroke:#be185d;stroke-width:4;stroke-dasharray:5 4}
        .map-meta b{display:block;font-size:14px;color:#be185d}.map-meta span{display:block;margin-top:1mm;color:#475569;font-weight:800}
        .section{border:1px solid #d8e3ee;border-radius:9px;background:#fff;padding:4mm;break-inside:avoid}
        .section h2{margin:0 0 3mm;color:#0f766e;font-size:13px}
        .grid2{display:grid;grid-template-columns:1fr 1fr;gap:5mm}
        .grid3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:4mm}
        .kpi{display:grid;grid-template-rows:8mm 4mm;align-items:end;gap:1mm}.kpi b{display:flex;align-items:flex-end;min-height:8mm;font-size:18px;line-height:1;color:#172033}.kpi span{font-size:9px;line-height:1;color:#64748b;font-weight:800;text-transform:uppercase}
        .stage-ladder{display:grid;grid-template-columns:repeat(4,1fr);gap:2mm;margin-top:2mm}.stage-step{height:10mm;border-radius:5mm;background:#e2e8f0;display:grid;place-items:center;font-weight:900;color:#64748b}.stage-step.active{background:#0f766e;color:#fff}
        .bio-row{margin-bottom:2.5mm}.bio-head{display:flex;justify-content:space-between;font-weight:900}.bio-head b{color:#334155}.bio-head span{color:#0f766e}.bio-track{height:5mm;background:#e2e8f0;border-radius:5mm;overflow:hidden}.bio-track i{display:block;height:100%;background:#0f766e;border-radius:5mm}.bio-row.hot .bio-track i{background:#be185d}
        .binary-track{position:relative;display:grid;grid-template-columns:1fr 1fr;height:6mm;border-radius:999px;background:#e2e8f0;overflow:hidden;color:#64748b;font-size:8px;font-weight:900}.binary-track i{position:relative;z-index:2;display:grid;place-items:center;font-style:normal}.binary-track .marker{position:absolute;top:0;bottom:0;width:50%;border-radius:999px;background:#94a3b8;transition:left .15s ease}.bio-row.binary:not(.positive):not(.negative) .marker{display:none}.bio-row.binary.negative .marker{left:0;background:#64748b}.bio-row.binary.positive .marker{left:50%;background:#be185d}.bio-row.binary.negative .neg,.bio-row.binary.positive .pos{color:#fff}
        .grade-meter{display:grid;grid-template-columns:repeat(3,1fr);gap:2mm}.grade-meter span{border-radius:6px;background:#e2e8f0;text-align:center;padding:2mm 0;font-weight:900;color:#64748b}.grade-meter span.active{background:#f59e0b;color:#fff}
        .badge-line{display:flex;gap:2mm;flex-wrap:wrap;margin-top:2mm}.badge{border:1px solid #cbd5e1;border-radius:999px;padding:1.2mm 2.5mm;font-weight:900;color:#334155;background:#f8fafc}
        .predict-visual{display:grid;grid-template-columns:33mm 1fr;gap:5mm;align-items:center}.ring{width:28mm;height:28mm;border-radius:50%;background:conic-gradient(#0f766e var(--pct),#e2e8f0 0);display:grid;place-items:center}.ring span{width:20mm;height:20mm;border-radius:50%;background:#fff;display:grid;place-items:center;font-size:13px;font-weight:900;color:#0f766e}.predict-main b{display:block;text-align:center;font-size:9px;margin-top:1mm}.benefit-track{height:6mm;background:#e2e8f0;border-radius:999px;overflow:hidden;margin:2mm 0}.benefit-track i{display:block;height:100%;background:#be185d}.predict-benefit span{color:#64748b;font-weight:800}.predict-benefit b{font-size:15px;color:#be185d}
        .empty-visual,.cycle-empty,.plan-empty{border:1px dashed #cbd5e1;border-radius:8px;padding:4mm;text-align:center;color:#64748b;background:#f8fafc;font-weight:800}.empty-visual span{font-size:10px}
        .plan-card{border:1px solid #e2e8f0;border-radius:8px;background:#f8fafc;padding:3mm;min-height:30mm}.plan-card h3{margin:0 0 2mm;font-size:12px;color:#172033}.plan-row{border-bottom:1px solid #e2e8f0;padding:1.3mm 0;font-weight:800}.plan-foot{margin-top:2mm;color:#64748b;font-size:9px}
        .cycle-strip{display:flex;gap:1.5mm;flex-wrap:wrap}.cycle-strip span{width:8mm;height:8mm;border-radius:50%;display:grid;place-items:center;background:#0f766e;color:#fff;font-weight:900}
        .fineprint{border-top:1px solid #e2e8f0;padding-top:3mm;color:#64748b;font-size:9px}
        .muted{color:#94a3b8}.actions{position:fixed;top:8px;right:8px}.actions button{border:0;border-radius:6px;background:#0f766e;color:#fff;padding:8px 12px;font-family:inherit;font-weight:900}
        @media print{.actions{display:none}.sheet{width:auto;min-height:auto}}
      </style></head><body>
      <div class="actions"><button onclick="window.print()">列印 / PDF</button></div>
      <main class="sheet">
        <header class="top">
          <div>
            <h1>乳癌治療說明單</h1>
            <div class="subtitle">一頁式門診溝通摘要，實際治療依醫師判斷與健保審查調整</div>
            <div class="hero-line">${display(sideLabel(p.side), '側別待補')}｜<span>${display(sizeCm(p.size), '大小待補')}</span>｜${display(subtype, '亞型待補')}</div>
            <div class="hero-sub">${display(stage.tnm, 'TNM 待補')} ${stage.anatomic ? `｜stage ${esc(stage.anatomic)}` : ''} ${stage.prognostic ? `｜預後 ${esc(stage.prognostic)}` : ''}</div>
          </div>
          <div>
            <div class="date">${esc(today)}</div>
            ${breastMap(p, derived)}
          </div>
        </header>

        <section class="grid3">
          <div class="section">
            ${stageLadder(stage.anatomic)}
            <div class="badge-line"><span class="badge">${display(stage.tnm, 'TNM 待補')}</span><span class="badge">${stage.prognostic ? `預後 ${esc(stage.prognostic)}` : '預後待補'}</span></div>
          </div>
          <div class="section">
            <h2>腫瘤特徵</h2>
            <div class="grid2">
              <div class="kpi"><b>${display(sizeCm(p.size), '—')}</b><span>Size</span></div>
              <div class="kpi"><b>${display(gradeLabel(p.grade), '—')}</b><span>Grade</span></div>
            </div>
            ${gradeMeter(p.grade)}
          </div>
          <div class="section">
            <h2>PREDICT 3.0</h2>
            ${predictPanel(predict)}
          </div>
        </section>

        <section class="grid2">
          <div class="section">
            <h2>受體 / 生物標記</h2>
            ${biomarkerBar('ER', p.er)}
            ${biomarkerBar('PR', p.pr)}
            ${binaryMarkerBar('HER2', her2Status, her2Text)}
            ${biomarkerBar('Ki-67', p.ki67, {tone:'hot'})}
          </div>
          <div class="section">
            <h2>預計藥物治療</h2>
            ${planCard('標靶 / 免疫 / 內分泌', medItems, '請由醫師於門診確認療程、給付與自費項目。')}
          </div>
          <div class="section">
            <h2>化療處方計畫</h2>
            ${cycleStrip(regimen)}
            ${planCard('Regimen', chemoItems, '費用為初步估算，實際依劑量與院內計價。')}
          </div>
          <div class="section">
            <h2>費用摘要</h2>
            <div class="grid2">
              <div class="kpi"><b>${display(regimenPrice, '待估')}</b><span>化療/配方總估</span></div>
              <div class="kpi"><b>${display(regimenSelfPay, '待確認')}</b><span>自費項目</span></div>
            </div>
            <div class="badge-line"><span class="badge">${display(regimenBasis, '費用基準待補')}</span><span class="badge">${display(regimenNhi, '健保項目待確認')}</span></div>
          </div>
        </section>

        <footer class="fineprint">
          本說明單供病人與家屬理解目前已填資料與預計治療討論方向。未填或不確定資料以「待補」呈現；不保證健保給付或最終療程。實際治療需依完整病理、影像、身體狀況、醫師判斷、健保署公告與院內流程確認。
        </footer>
      </main>
      </body></html>`;
  }

  global.OncoBreastPatientInformSheet = { render };
})(window);
