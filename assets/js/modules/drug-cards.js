// ── Patch: render drug items as cards instead of table rows ──
// Override the table-based render with card-based render

const _origBreastBody_setter = Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'innerHTML');

function renderDrugCards(drugs, containerId, infoId, specialty) {
  const list = document.getElementById(containerId);
  const info = document.getElementById(infoId);
  if(!list) return;
  
  if(info) {
    const filtered = drugs.filter(d => d.specialty_id === specialty || specialty === 'all');
    // info text set by caller
  }

  list.innerHTML = drugs.map(d => {
    const stages = d.stage ? d.stage.split(',') : [];
    const stageMap = {early:'早期',advanced:'局部晚期',metastatic:'轉移性'};
    const stageTags = stages.map(s => `<span class="tag tag-stage">${stageMap[s]||s}</span>`).join('');
    const lineTags = d.therapy_line ? `<span class="tag tag-line">${d.therapy_line}L</span>` : '';
    const authTag = d.prior_auth ? '<span class="tag tag-auth">事前審查</span>' : '';
    const specTag = d.specialty_id==='oncology_breast' 
      ? '<span class="tag tag-breast">乳癌</span>' 
      : d.specialty_id==='oncology_heme' 
        ? '<span class="tag tag-heme">血腫</span>' : '';
    
    // Clinical marker tags
    const tags = d.clinical_tags || {};
    let markerTags = '';
    if(tags.brca) markerTags += '<span class="tag tag-marker">BRCA</span>';
    if(tags.pik3ca) markerTags += '<span class="tag tag-marker">PIK3CA</span>';
    if(tags.esr1) markerTags += '<span class="tag tag-marker">ESR1</span>';
    if(tags.tnbc) markerTags += '<span class="tag tag-marker">TNBC</span>';
    if(tags.ln) markerTags += '<span class="tag tag-marker">N+</span>';
    if(tags.her2==='positive') markerTags += '<span class="tag tag-marker">HER2+</span>';
    if(tags.er_pr==='positive') markerTags += '<span class="tag tag-marker">ER+</span>';
    if(tags.flt3) markerTags += '<span class="tag tag-marker">FLT3</span>';
    if(tags.ph_positive) markerTags += '<span class="tag tag-marker">Ph+</span>';

    const priceHtml = d.nhi_price 
      ? `<div class="price-display">
          <div class="price-main">NT$ ${d.nhi_price.toLocaleString()}</div>
          <span class="price-unit">${d.price_unit||''}</span>
        </div>`
      : '<span class="price-na">詢價</span>';

    const nhiInd = d.prior_auth 
      ? '<span class="nhi-indicator auth-req">需事前審查</span>'
      : '<span class="nhi-indicator covered">健保給付</span>';

    const tradeName = d.trade_names ? `<span class="drug-name-trade"> / ${d.trade_names}</span>` : '';

    return `<div class="drug-item" onclick="openDetail(${d.id})">
      <div class="drug-item-left">
        <div class="drug-name-main">${d.generic_name}${tradeName}</div>
        <div class="drug-tags">
          ${specTag}${stageTags}${lineTags}${authTag}${markerTags}
        </div>
      </div>
      <div class="drug-item-right">
        ${priceHtml}
        ${nhiInd}
      </div>
    </div>`;
  }).join('') || '<div class="empty-state"><div class="empty-icon">💊</div><p>找不到符合條件的藥物</p></div>';
}

// Global search across all drugs
function handleGlobalSearch(val) {
  const q = val.trim().toLowerCase();
  const results = document.getElementById('globalResults');
  const deptSection = document.getElementById('deptSection');
  const list = document.getElementById('globalList');
  const count = document.getElementById('globalCount');

  if(!q) {
    results.style.display = 'none';
    deptSection.style.display = '';
    return;
  }

  deptSection.style.display = 'none';
  results.style.display = '';

  const hits = _STATIC_DRUGS.filter(d => drugSearchText(d).includes(q));

  count.textContent = `找到 ${hits.length} 筆結果`;
  renderDrugCards(hits, 'globalList', null, 'all');
}

// Override filterBreast to also update card list
const _origFilterBreast = filterBreast;
filterBreast = function() {
  _origFilterBreast();
  // After table is updated, sync to card list
  syncTableToCards('breastBody', 'breastList', 'breastInfo');
};


function syncTableToCards(tableBodyId, listId, infoId) {
  const tbody = document.getElementById(tableBodyId);
  const list = document.getElementById(listId);
  if(!tbody || !list) return;

  // Extract drug IDs from hidden table rows (they have onclick="openDetail(N)")
  const rows = Array.from(tbody.querySelectorAll('tr[onclick]'));
  const ids = rows.map(r => {
    const m = r.getAttribute('onclick').match(/(?:openDetail|showDetail)\((\d+)\)/);
    return m ? parseInt(m[1]) : null;
  }).filter(Boolean);

  const drugs = ids.map(id => _STATIC_DRUGS.find(d => d.id === id)).filter(Boolean);
  
  // Update count display
  const infoEl = document.getElementById(infoId);
  if(infoEl) infoEl.textContent = `共 ${drugs.length} 筆藥物`;

  list.innerHTML = drugs.map(d => {
    const stages = d.stage ? d.stage.split(',') : [];
    const stageMap = {early:'早期',advanced:'局部晚期',metastatic:'轉移性'};
    const stageTags = stages.map(s => `<span class="tag tag-stage">${stageMap[s]||s}</span>`).join('');
    const lineTags = d.therapy_line ? `<span class="tag tag-line">${d.therapy_line}L</span>` : '';
    const authTag = d.prior_auth ? '<span class="tag tag-auth">事前審查</span>' : '';
    const ctags = d.clinical_tags || {};
    let markerTags = '';
    if(ctags.brca) markerTags += '<span class="tag tag-marker">BRCA</span>';
    if(ctags.pik3ca) markerTags += '<span class="tag tag-marker">PIK3CA</span>';
    if(ctags.esr1) markerTags += '<span class="tag tag-marker">ESR1</span>';
    if(ctags.tnbc) markerTags += '<span class="tag tag-marker">TNBC</span>';
    if(ctags.ln) markerTags += '<span class="tag tag-marker">N+</span>';
    if(ctags.her2==='positive') markerTags += '<span class="tag tag-marker">HER2+</span>';
    if(ctags.er_pr==='positive') markerTags += '<span class="tag tag-marker">ER+</span>';
    if(ctags.flt3) markerTags += '<span class="tag tag-marker">FLT3</span>';
    if(ctags.ph_positive) markerTags += '<span class="tag tag-marker">Ph+</span>';
    if(Array.isArray(ctags.disease)) ctags.disease.slice(0,2).forEach(x => { markerTags += `<span class="tag tag-marker">${x}</span>`; });

    const priceHtml = d.nhi_price 
      ? `<div class="price-display"><div class="price-main">NT$ ${d.nhi_price.toLocaleString()}</div><span class="price-unit">${d.price_unit||''}</span></div>`
      : '<span class="price-na">詢價</span>';
    const nhiInd = d.prior_auth 
      ? '<span class="nhi-indicator auth-req">需事前審查</span>'
      : '<span class="nhi-indicator covered">健保給付</span>';
    const tradeName = d.trade_names ? `<span class="drug-name-trade"> / ${d.trade_names}</span>` : '';

    return `<div class="drug-item" onclick="openDetail(${d.id})">
      <div class="drug-item-left">
        <div class="drug-name-main">${d.generic_name}${tradeName}</div>
        <div class="drug-tags">${stageTags}${lineTags}${authTag}${markerTags}</div>
      </div>
      <div class="drug-item-right">${priceHtml}${nhiInd}</div>
    </div>`;
  }).join('') || '<div class="empty-state"><div class="empty-icon">💊</div><p>找不到符合條件的藥物</p></div>';
}

// Hook into showBreast to init card list
const _origShowBreast = showBreast;
showBreast = function() {
  _origShowBreast();
  setTimeout(() => syncTableToCards('breastBody', 'breastList', 'breastInfo'), 50);
};

// ── Compare Feature ──────────────────────────────────────────────────────────
function toggleCompare(id){
    const idx=compareList.findIndex(x=>x.id===id);
    if(idx>=0){compareList.splice(idx,1);}
    else{
        if(compareList.length>=4){alert('最多比較 4 種藥物');return;}
        const drug=_STATIC_DRUGS.find(d=>d.id===id);
        if(drug)compareList.push(drug);
    }
    updateCmpBar();
    document.querySelectorAll('.cmp-btn[data-id="'+id+'"]').forEach(btn=>{
        btn.classList.toggle('active',compareList.some(x=>x.id===id));
    });
}
function updateCmpBar(){
    const bar=document.getElementById('cmpBar');
    const chips=document.getElementById('cmpChips');
    if(compareList.length===0){bar.classList.remove('show');return;}
    bar.classList.add('show');
    chips.innerHTML=compareList.map(d=>`<span class="cmp-chip">${esc(d.generic_name)}<button onclick="toggleCompare(${d.id})">&#x2715;</button></span>`).join('');
}
function clearCompare(){compareList=[];document.querySelectorAll('.cmp-btn.active').forEach(b=>b.classList.remove('active'));updateCmpBar();}
function closeCompareModal(){document.getElementById('cmpModal').classList.remove('show');}
function openCompare(){
    if(compareList.length<2){alert('請至少選擇 2 種藥物進行比較');return;}
    renderCompare();
    document.getElementById('cmpModal').classList.add('show');
}
function renderCompare(){
    const drugs=compareList;
    const cols=drugs.map(d=>`<th style="min-width:160px;background:var(--surface-2);padding:.6rem .8rem;border-bottom:2px solid var(--border-2)">${esc(d.generic_name)}<br><span style="font-size:.72rem;font-weight:400;color:var(--text-muted)">${esc(d.trade_names||'')}</span></th>`).join('');
    const rowDefs=[
        ['健保給付狀態', d=>{
            const ok=hasAnyFilter()?matchesFilters(d,activeFilters):null;
            return ok===true?'<span style="color:var(--nhi);font-weight:600">&#10003; 符合給付</span>':ok===false?'<span style="color:var(--self)">&#36; 不符合（可自費）</span>':'<span style="color:var(--text-muted)">未套用篩選</span>';
        }],
        ['健保藥價', d=>d.nhi_price?`<strong style="color:#7c3aed">NT$ ${Number(d.nhi_price).toLocaleString()}</strong><br><span style="font-size:.75rem;color:var(--text-muted)">${esc(d.price_unit||'')}</span>`:'<span style="color:var(--text-muted)">未收載</span>'],
        ['事前審查', d=>d.prior_auth?'<span class="badge badge-auth">需審查</span>':'<span style="color:var(--nhi);font-weight:600">免審查</span>'],
        ['療程線', d=>d.therapy_line?'第'+d.therapy_line+'線':'<span style="color:var(--text-muted)">-</span>'],
        ['分期', d=>stageLabel(d.stage)],
        ['適應症', d=>d.indication?d.indication.split(' | ').map(p=>'<p style="margin-bottom:.25rem;font-size:.82rem">'+esc(p)+'</p>').join(''):'<span style="color:var(--text-muted)">-</span>'],
        ['給付條件', d=>d.conditions?d.conditions.split(' | ').map(p=>'<p style="margin-bottom:.25rem;font-size:.82rem">'+esc(p)+'</p>').join(''):'<span style="color:var(--text-muted)">-</span>'],
    ];
    let html=`<h2 style="margin-bottom:1.2rem">費用比較表</h2><div style="overflow-x:auto"><table style="width:100%;border-collapse:collapse;font-size:.875rem"><thead><tr><th style="background:var(--surface-2);text-align:left;padding:.6rem .8rem;min-width:90px;border-bottom:2px solid var(--border-2)"></th>${cols}</tr></thead><tbody>`;
    rowDefs.forEach(([label,fn])=>{
        const cells=drugs.map(d=>`<td style="padding:.6rem .8rem;border-bottom:1px solid var(--border);vertical-align:top">${fn(d)}</td>`).join('');
        html+=`<tr><td style="padding:.6rem .8rem;border-bottom:1px solid var(--border);font-weight:600;background:var(--surface-2);white-space:nowrap">${label}</td>${cells}</tr>`;
    });
    html+=`</tbody></table></div><div class="btn-row" style="margin-top:1.5rem"><button class="btn btn-primary btn-sm" onclick="printCompare()">&#128438; 列印比較表</button><button class="btn btn-outline btn-sm" onclick="closeCompareModal()">關閉</button></div>`;
    document.getElementById('cmpBody').innerHTML=html;
}
function printCompare(){
    const today=new Date().toLocaleDateString('zh-TW');
    const tblEl=document.getElementById('cmpBody').querySelector('table');
    if(!tblEl){alert('請先開啟比較表');return;}
    const tbl=tblEl.outerHTML;
    const w=window.open('','_blank','width=900,height=700');
    if(!w){alert('請允許彈出視窗以列印');return;}
    w.document.write('<!DOCTYPE html><html><head><meta charset="UTF-8"><title>藥物費用比較 '+today+'<\/title><style>body{font-family:sans-serif;padding:2rem;font-size:13px;color:#0f172a}h1{font-size:1.1rem;margin-bottom:.3rem}.sub{color:#64748b;font-size:.82rem;margin-bottom:1.2rem}table{width:100%;border-collapse:collapse}th,td{padding:.45rem .65rem;border:1px solid #e2e8f0;vertical-align:top;text-align:left}th{background:#f1f5f9;font-weight:600}.footer{margin-top:1.5rem;font-size:.72rem;color:#94a3b8;border-top:1px solid #e2e8f0;padding-top:.6rem}@media print{body{padding:.5rem}}<\/style><\/head><body><h1>健保腫瘤藥物費用比較表<\/h1><div class="sub">列印日期：'+today+'<\/div>'+tbl+'<div class="footer">本資料僅供門診說明參考，實際給付以健保署公告為準。<\/div><\/body><\/html>');
    w.document.close();
    setTimeout(()=>w.print(),300);
}

// ── Patient Summary Print ─────────────────────────────────────────────────────
function printPatientSummary(id){
    const drug=_STATIC_DRUGS.find(d=>d.id===id);
    if(!drug)return;
    const today=new Date().toLocaleDateString('zh-TW');
    const ok=hasAnyFilter()?matchesFilters(drug,activeFilters):null;
    const coverageHtml=ok===true
        ?'<div style="background:#ecfdf5;border:1px solid #6ee7b7;border-radius:8px;padding:.7rem 1rem"><strong style="color:#047857">&#10003; 符合健保給付條件<\/strong><\/div>'
        :ok===false
        ?'<div style="background:#fef2f2;border:1px solid #fca5a5;border-radius:8px;padding:.7rem 1rem"><strong style="color:#b91c1c">目前條件不符合健保給付，此藥可自費使用<\/strong><\/div>'
        :'<div style="background:#eff6ff;border:1px solid #bfdbfe;border-radius:8px;padding:.7rem 1rem"><strong style="color:#1e40af">請搭配病人受體狀態篩選以確認給付資格<\/strong><\/div>';
    const priceHtml=drug.nhi_price?'<strong style="color:#7c3aed">NT$ '+Number(drug.nhi_price).toLocaleString()+' \/ '+(drug.price_unit||'')+'<\/strong>':'尚無藥價資料';
    const condList=drug.conditions?'<ul style="margin:.4rem 0 0 1.1rem">'+drug.conditions.split(' | ').map(c=>'<li style="margin-bottom:.25rem">'+c+'<\/li>').join('')+'<\/ul>':'<p style="color:#64748b">無特定條件<\/p>';
    const authHtml=drug.prior_auth
        ?'<div style="background:#fffbeb;border:1px solid #fde68a;border-radius:8px;padding:.7rem 1rem"><strong style="color:#b45309">需申請事前審查<\/strong><p style="margin:.4rem 0 0;font-size:.85rem;color:#555">請備妃以下資料供醫師申請：<\/p><ul style="margin:.3rem 0 0 1.1rem;font-size:.85rem;color:#555"><li>病理報告（含受體狀態 HER2 \/ ER \/ PR）<\/li><li>前線治療失敗紀錄（如適用）<\/li><li>影像學檢查報告（如適用）<\/li><li>基因或生物標記檢測報告（如適用）<\/li><\/ul><\/div>'
        :'<p style="color:#047857;font-weight:600">&#10003; 無需事前審查<\/p>';
    const indicHtml=drug.indication?'<p>'+drug.indication.replace(/ \| /g,'；')+'<\/p>':'';
    const w=window.open('','_blank','width=680,height=820');
    if(!w){alert('請允許彈出視窗以列印');return;}
    w.document.write('<!DOCTYPE html><html><head><meta charset="UTF-8"><title>'+esc(drug.generic_name)+' - 病患摘要<\/title><style>body{font-family:sans-serif;padding:2rem;color:#0f172a;font-size:14px;max-width:580px;margin:0 auto}h1{font-size:1.3rem;margin-bottom:.2rem}.trade{color:#64748b;font-size:.9rem;margin-bottom:.2rem}.date{font-size:.78rem;color:#94a3b8;margin-bottom:1.2rem;padding-bottom:.8rem;border-bottom:1px solid #e2e8f0}h2{font-size:.95rem;font-weight:700;margin:1.1rem 0 .35rem;color:#334155}p,li{line-height:1.7;font-size:.9rem}.footer{margin-top:2rem;font-size:.72rem;color:#94a3b8;border-top:1px solid #e2e8f0;padding-top:.6rem}@media print{body{padding:.8rem}}<\/style><\/head><body>');
    w.document.write('<h1>'+esc(drug.generic_name)+'<\/h1>');
    if(drug.trade_names)w.document.write('<div class="trade">商品名：'+esc(drug.trade_names)+'<\/div>');
    w.document.write('<div class="date">說明日期：'+today+'<\/div>');
    w.document.write('<h2>健保給付狀態<\/h2>'+coverageHtml);
    w.document.write('<h2>藥品費用<\/h2><p>健保藥價：'+priceHtml+'<\/p>');
    w.document.write('<h2>給付條件<\/h2>'+condList);
    w.document.write('<h2>事前審查<\/h2>'+authHtml);
    if(indicHtml)w.document.write('<h2>適應症<\/h2>'+indicHtml);
    w.document.write('<div class="footer">本資料僅供門診說明參考，實際給付以健保署公告為準。藥價依健保支付標準，自費藥品市場價格可能不同。<\/div>');
    w.document.write('<scr'+'ipt>window.onload=function(){window.print()}<\/scr'+'ipt><\/body><\/html>');
    w.document.close();
}


// ═══════════════════════════════════════════════════════
//  住院化療計算 (Inpatient Chemo Calculator)
// ═══════════════════════════════════════════════════════
let _inpInited = false;
let _inpWt = 60, _inpHt = 165, _inpBSA = 1.66, _inpCrCl = 80;
let _inpAge = 50, _inpSex = 'F', _inpCr = 0.8;
let _inpPriceType = 'nhi';
let _inpSelectedRegimen = null;
let _inpLastTotal = 0;
let _inpLastPriceLabel = '';

// ── Drug price data (NHI=115年健保支付價, Self=台大醫院2024/12參考) ──
const INP_DRUG_DATA = {
  // ── Anthracyclines ──
  epirubicin: {
    name: 'Epirubicin (表柔比星)', unit_label: 'mg/vial',
    vials: [
      {size:50, nhi:2470, self:3200, label:'50mg/vial'},
      {size:10, nhi:600,  self:780,  label:'10mg/vial'}
    ]
  },
  doxorubicin: {
    name: 'Doxorubicin HCl (小紅莓)', unit_label: 'mg/vial',
    vials: [
      {size:50, nhi:1350, self:1700, label:'50mg/vial'},
      {size:10, nhi:280,  self:350,  label:'10mg/vial'}
    ]
  },
  doxorubicin_lipo: {
    name: 'Doxorubicin Liposomal (Lipo-Dox)', unit_label: 'mg/vial',
    vials: [
      {size:20, nhi:15400, self:19000, label:'20mg/vial'},
      {size:10, nhi:8200,  self:10000, label:'10mg/vial'}
    ]
  },
  // ── Alkylating agents ──
  cyclophosphamide: {
    name: 'Cyclophosphamide (環磷醯胺)', unit_label: 'mg/vial',
    vials: [
      {size:1000, nhi:280, self:350, label:'1000mg/vial'},
      {size:500,  nhi:160, self:200, label:'500mg/vial'}
    ]
  },
  // ── Taxanes ──
  docetaxel: {
    name: 'Docetaxel / Taxotere (紫杉特爾)', unit_label: 'mg/vial',
    vials: [
      {size:80, nhi:9874, self:13800, label:'80mg/4mL'},
      {size:20, nhi:2802, self:4187,  label:'20mg/1mL'}
    ]
  },
  paclitaxel: {
    name: 'Paclitaxel (太平洋紫杉醇)', unit_label: 'mg/vial',
    vials: [
      {size:90, nhi:894, self:1566, label:'90mg/15mL'},
      {size:30, nhi:509, self:942,  label:'30mg/5mL'}
    ]
  },
  nab_paclitaxel: {
    name: 'nab-Paclitaxel (Abraxane)', unit_label: 'mg/vial',
    vials: [
      {size:100, nhi:10500, self:14000, label:'100mg/vial'}
    ]
  },
  // ── Platinum ──
  carboplatin: {
    name: 'Carboplatin (卡鉑)', unit_label: 'mg/vial',
    vials: [
      {size:450, nhi:3195, self:4281, label:'450mg/40mL'},
      {size:150, nhi:1442, self:2055, label:'150mg/15mL'}
    ]
  },
  cisplatin: {
    name: 'Cisplatin (順鉑)', unit_label: 'mg/vial',
    vials: [
      {size:50, nhi:260, self:320, label:'50mg/50mL'},
      {size:10, nhi:60,  self:80,  label:'10mg/10mL'}
    ]
  },
  // ── HER2 targeted ──
  trastuzumab: {
    name: 'Trastuzumab IV (Herceptin)', unit_label: 'mg/vial',
    vials: [
      {size:440, nhi:32885, self:48230, label:'440mg/vial'}
    ]
  },
  pertuzumab: {
    name: 'Pertuzumab (Perjeta)', unit_label: 'mg/vial',
    vials: [
      {size:420, nhi:49966, self:65105, label:'420mg/vial'}
    ]
  },
  phesgo: {
    name: 'Phesgo SC (Pertuzumab/Trastuzumab)', unit_label: 'fixed dose syringe',
    fixedDoses: {
      loading: {nhi:null, self:125306, label:'15mL: pertuzumab 1200mg + trastuzumab 600mg，皮下注射約8分鐘'},
      maintenance: {nhi:null, self:76241, label:'10mL: pertuzumab 600mg + trastuzumab 600mg，q3w 皮下注射約5分鐘'}
    }
  },
  trastuzumab_emtansine: {
    name: 'T-DM1 (Kadcyla)', unit_label: 'mg/vial',
    vials: [
      {size:160, nhi:56604, self:57970, label:'160mg/vial'},
      {size:100, nhi:35506, self:40257, label:'100mg/vial'}
    ]
  },
  // ── Immunotherapy ──
  pembrolizumab: {
    name: 'Pembrolizumab (Keytruda)', unit_label: 'mg/vial',
    vials: [
      {size:100, nhi:54267, self:74645, label:'100mg/4mL'}
    ]
  },
  // ── Other cytotoxics ──
  gemcitabine: {
    name: 'Gemcitabine (健擇 Gemzar)', unit_label: 'mg/vial',
    vials: [
      {size:1000, nhi:320, self:420, label:'1000mg/vial'},
      {size:200,  nhi:80,  self:105, label:'200mg/vial'}
    ]
  },
  vinorelbine: {
    name: 'Vinorelbine (溫諾平 Navelbine)', unit_label: 'mg/vial',
    vials: [
      {size:50, nhi:1200, self:1500, label:'50mg/5mL'},
      {size:10, nhi:280,  self:350,  label:'10mg/1mL'}
    ]
  },
  eribulin: {
    name: 'Eribulin (艾瑞布林 Halaven)', unit_label: 'mg/vial',
    vials: [
      {size:1, nhi:11800, self:14800, label:'1mg/2mL'}
    ]
  },
  // ── Oral ──
  capecitabine: {
    name: 'Capecitabine (Xeloda 截瘤達)', unit_label: 'mg/tab', isOral: true,
    vials: [
      {size:500, nhi:88, self:120, label:'500mg/tab'}
    ]
  }
};

// ── Regimen definitions (NCCN 2024-2025 / Taiwan Practice) ──
const INP_REGIMENS = [
  // ════════════════════════════════
  // HER2- 輔助 / 術前化療
  // ════════════════════════════════
  {
    id:'ec', name:'EC', group:'HER2- 輔助/術前',
    desc:'Epirubicin 90mg/m² + Cyclophosphamide 600mg/m²  q3w × 4',
    default_cycles:4, freq:'q3w',
    drugs:[
      {key:'epirubicin',       dose_type:'bsa', dose:90,  unit:'mg/m²'},
      {key:'cyclophosphamide', dose_type:'bsa', dose:600, unit:'mg/m²'}
    ]
  },
  {
    id:'ac', name:'AC', group:'HER2- 輔助/術前',
    desc:'Doxorubicin 60mg/m² + Cyclophosphamide 600mg/m²  q3w × 4',
    default_cycles:4, freq:'q3w',
    drugs:[
      {key:'doxorubicin',      dose_type:'bsa', dose:60,  unit:'mg/m²'},
      {key:'cyclophosphamide', dose_type:'bsa', dose:600, unit:'mg/m²'}
    ]
  },
  {
    id:'dd_ac', name:'dd-AC (q2w)', group:'HER2- 輔助/術前',
    desc:'Dose-dense Doxorubicin 60mg/m² + Cyclophosphamide 600mg/m²  q2w × 4（需 G-CSF）',
    default_cycles:4, freq:'q2w',
    drugs:[
      {key:'doxorubicin',      dose_type:'bsa', dose:60,  unit:'mg/m²'},
      {key:'cyclophosphamide', dose_type:'bsa', dose:600, unit:'mg/m²'}
    ]
  },
  {
    id:'tc', name:'TC', group:'HER2- 輔助/術前',
    desc:'Docetaxel 75mg/m² + Cyclophosphamide 600mg/m²  q3w × 4',
    default_cycles:4, freq:'q3w',
    drugs:[
      {key:'docetaxel',        dose_type:'bsa', dose:75,  unit:'mg/m²'},
      {key:'cyclophosphamide', dose_type:'bsa', dose:600, unit:'mg/m²'}
    ]
  },
  {
    id:'ec_t', name:'EC → T', group:'HER2- 輔助/術前',
    desc:'EC × 4  q3w → Docetaxel 75mg/m² × 4  q3w',
    sequential:true,
    phases:[
      {name:'EC Phase', default_cycles:4, freq:'q3w',
       drugs:[
         {key:'epirubicin',       dose_type:'bsa', dose:90,  unit:'mg/m²'},
         {key:'cyclophosphamide', dose_type:'bsa', dose:600, unit:'mg/m²'}
       ]},
      {name:'T Phase', default_cycles:4, freq:'q3w',
       drugs:[
         {key:'docetaxel', dose_type:'bsa', dose:75, unit:'mg/m²'}
       ]}
    ]
  },
  {
    id:'ac_t', name:'AC → T (q3w)', group:'HER2- 輔助/術前',
    desc:'AC × 4  q3w → Paclitaxel 175mg/m² × 4  q3w（或 Docetaxel 75×4）',
    sequential:true,
    phases:[
      {name:'AC Phase', default_cycles:4, freq:'q3w',
       drugs:[
         {key:'doxorubicin',      dose_type:'bsa', dose:60,  unit:'mg/m²'},
         {key:'cyclophosphamide', dose_type:'bsa', dose:600, unit:'mg/m²'}
       ]},
      {name:'T Phase', default_cycles:4, freq:'q3w',
       drugs:[
         {key:'paclitaxel', dose_type:'bsa', dose:175, unit:'mg/m²'}
       ]}
    ]
  },
  {
    id:'dd_act', name:'dd-AC → dd-T', group:'HER2- 輔助/術前',
    desc:'Dose-dense AC × 4  q2w → Paclitaxel 175mg/m² × 4  q2w（均需 G-CSF）',
    sequential:true,
    phases:[
      {name:'dd-AC Phase', default_cycles:4, freq:'q2w',
       drugs:[
         {key:'doxorubicin',      dose_type:'bsa', dose:60,  unit:'mg/m²'},
         {key:'cyclophosphamide', dose_type:'bsa', dose:600, unit:'mg/m²'}
       ]},
      {name:'dd-T Phase', default_cycles:4, freq:'q2w',
       drugs:[
         {key:'paclitaxel', dose_type:'bsa', dose:175, unit:'mg/m²'}
       ]}
    ]
  },
  {
    id:'tac', name:'TAC', group:'HER2- 輔助/術前',
    desc:'Docetaxel 75mg/m² + Doxorubicin 50mg/m² + Cyclophosphamide 500mg/m²  q3w × 6',
    default_cycles:6, freq:'q3w',
    drugs:[
      {key:'docetaxel',        dose_type:'bsa', dose:75,  unit:'mg/m²'},
      {key:'doxorubicin',      dose_type:'bsa', dose:50,  unit:'mg/m²'},
      {key:'cyclophosphamide', dose_type:'bsa', dose:500, unit:'mg/m²'}
    ]
  },

  // ════════════════════════════════
  // HER2+ 術前 / 輔助
  // ════════════════════════════════
  {
    id:'tch', name:'TCH', group:'HER2+ 術前/輔助',
    desc:'Docetaxel 75mg/m² + Carboplatin AUC5 + Herceptin  q3w × 6',
    default_cycles:6, freq:'q3w',
    drugs:[
      {key:'docetaxel',   dose_type:'bsa', dose:75, unit:'mg/m²'},
      {key:'carboplatin', dose_type:'auc', dose:5,  unit:'AUC'},
      {key:'trastuzumab', dose_type:'kg',  dose:6,  loading:8, unit:'mg/kg'}
    ]
  },
  {
    id:'tchp', name:'TCHP', group:'HER2+ 術前/輔助',
    desc:'Docetaxel + Carboplatin AUC5 + Herceptin + Perjeta  q3w × 6',
    default_cycles:6, freq:'q3w',
    drugs:[
      {key:'docetaxel',   dose_type:'bsa',   dose:75,  unit:'mg/m²'},
      {key:'carboplatin', dose_type:'auc',   dose:5,   unit:'AUC'},
      {key:'trastuzumab', dose_type:'kg',    dose:6,   loading:8,   unit:'mg/kg'},
      {key:'pertuzumab',  dose_type:'fixed', dose:420, loading:840, unit:'mg'}
    ]
  },
  {
    id:'tchp_phesgo', name:'TCHP + Phesgo SC', group:'HER2+ 術前/輔助',
    desc:'Docetaxel + Carboplatin AUC5 + Phesgo SC  q3w × 6（第1 cycle loading，後續 maintenance）',
    default_cycles:6, freq:'q3w',
    drugs:[
      {key:'docetaxel',   dose_type:'bsa', dose:75, unit:'mg/m²'},
      {key:'carboplatin', dose_type:'auc', dose:5,  unit:'AUC'},
      {key:'phesgo',      dose_type:'fixed_sc_combo', dose:0, unit:'fixed dose'}
    ]
  },
  {
    id:'ec_thp', name:'EC → THP', group:'HER2+ 術前/輔助',
    desc:'EC × 4  q3w → Docetaxel+Herceptin+Perjeta × 4  q3w（經典術前方案）',
    sequential:true,
    phases:[
      {name:'EC Phase', default_cycles:4, freq:'q3w',
       drugs:[
         {key:'epirubicin',       dose_type:'bsa', dose:90,  unit:'mg/m²'},
         {key:'cyclophosphamide', dose_type:'bsa', dose:600, unit:'mg/m²'}
       ]},
      {name:'THP Phase', default_cycles:4, freq:'q3w',
       drugs:[
         {key:'docetaxel',   dose_type:'bsa',   dose:75,  unit:'mg/m²'},
         {key:'trastuzumab', dose_type:'kg',    dose:6,   loading:8,   unit:'mg/kg'},
         {key:'pertuzumab',  dose_type:'fixed', dose:420, loading:840, unit:'mg'}
       ]}
    ]
  },
  {
    id:'ac_wph', name:'AC → wPH', group:'HER2+ 術前/輔助',
    desc:'AC × 4  q3w → weekly Paclitaxel 80mg/m² + Herceptin × 12週',
    sequential:true,
    phases:[
      {name:'AC Phase', default_cycles:4, freq:'q3w',
       drugs:[
         {key:'doxorubicin',     dose_type:'bsa', dose:60,  unit:'mg/m²'},
         {key:'cyclophosphamide',dose_type:'bsa', dose:600, unit:'mg/m²'}
       ]},
      {name:'wPH Phase (weekly × 12)', default_cycles:12, freq:'weekly',
       drugs:[
         {key:'paclitaxel',   dose_type:'bsa', dose:80, unit:'mg/m²'},
         {key:'trastuzumab',  dose_type:'kg',  dose:2,  loading:4, unit:'mg/kg'}
       ]}
    ]
  },
  {
    id:'wp_h', name:'wP + H', group:'HER2+ 術前/輔助',
    desc:'Weekly Paclitaxel 80mg/m² + Herceptin 2mg/kg  每週 × 12',
    default_cycles:12, freq:'weekly',
    drugs:[
      {key:'paclitaxel',  dose_type:'bsa', dose:80, unit:'mg/m²'},
      {key:'trastuzumab', dose_type:'kg',  dose:2,  loading:4, unit:'mg/kg'}
    ]
  },
  {
    id:'tdm1_adj', name:'T-DM1 輔助', group:'HER2+ 術前/輔助',
    desc:'T-DM1 3.6mg/kg  q3w × 14（術後有殘餘病灶，非 pCR）',
    default_cycles:14, freq:'q3w',
    drugs:[
      {key:'trastuzumab_emtansine', dose_type:'kg', dose:3.6, unit:'mg/kg'}
    ]
  },

  // ════════════════════════════════
  // TNBC 術前化療
  // ════════════════════════════════
  {
    id:'keynote522', name:'KEYNOTE-522', group:'TNBC 術前',
    desc:'Pembro+wP+Carbo × 4  q3w → Pembro+AC × 4  q3w（術後 Pembro 維持 × 9）',
    sequential:true,
    phases:[
      {name:'Phase 1: Keytruda + wP + Carbo (q3w × 4)', default_cycles:4, freq:'q3w',
       drugs:[
         {key:'pembrolizumab', dose_type:'fixed', dose:200, unit:'mg'},
         {key:'paclitaxel',    dose_type:'bsa',   dose:80,  unit:'mg/m²（每週）'},
         {key:'carboplatin',   dose_type:'auc',   dose:5,   unit:'AUC'}
       ]},
      {name:'Phase 2: Keytruda + AC (q3w × 4)', default_cycles:4, freq:'q3w',
       drugs:[
         {key:'pembrolizumab',    dose_type:'fixed', dose:200, unit:'mg'},
         {key:'doxorubicin',      dose_type:'bsa',   dose:60,  unit:'mg/m²'},
         {key:'cyclophosphamide', dose_type:'bsa',   dose:600, unit:'mg/m²'}
       ]}
    ]
  },
  {
    id:'neopact', name:'NeoPACT', group:'TNBC 術前',
    desc:'Docetaxel 75mg/m² + Carboplatin AUC6 + Pembrolizumab 200mg  q3w × 6（無 anthracycline）',
    default_cycles:6, freq:'q3w',
    drugs:[
      {key:'docetaxel',     dose_type:'bsa',   dose:75,  unit:'mg/m²'},
      {key:'carboplatin',   dose_type:'auc',   dose:6,   unit:'AUC'},
      {key:'pembrolizumab', dose_type:'fixed', dose:200, unit:'mg'}
    ]
  },
  {
    id:'wp_carbo', name:'wP + Carbo', group:'TNBC 術前',
    desc:'Weekly Paclitaxel 80mg/m² + Carboplatin AUC5  q3w × 4（無免疫治療）',
    default_cycles:4, freq:'q3w',
    drugs:[
      {key:'paclitaxel',  dose_type:'bsa', dose:80, unit:'mg/m²（每週）'},
      {key:'carboplatin', dose_type:'auc', dose:5,  unit:'AUC'}
    ]
  },
  {
    id:'ec_wpc', name:'EC → wP + Carbo', group:'TNBC 術前',
    desc:'EC × 4  q3w → weekly Paclitaxel 80mg/m² + Carboplatin AUC2 weekly × 12',
    sequential:true,
    phases:[
      {name:'EC Phase', default_cycles:4, freq:'q3w',
       drugs:[
         {key:'epirubicin',       dose_type:'bsa', dose:90,  unit:'mg/m²'},
         {key:'cyclophosphamide', dose_type:'bsa', dose:600, unit:'mg/m²'}
       ]},
      {name:'wP + Carbo Phase (weekly × 12)', default_cycles:12, freq:'weekly',
       drugs:[
         {key:'paclitaxel',  dose_type:'bsa', dose:80, unit:'mg/m²'},
         {key:'carboplatin', dose_type:'auc', dose:2,  unit:'AUC (weekly)'}
       ]}
    ]
  },

  // ════════════════════════════════
  // HER2+ 轉移性
  // ════════════════════════════════
  {
    id:'thp_meta', name:'THP (轉移)', group:'HER2+ 轉移',
    desc:'Docetaxel 75mg/m² + Herceptin + Perjeta  q3w（CLEOPATRA 方案，一線）',
    default_cycles:8, freq:'q3w',
    drugs:[
      {key:'docetaxel',   dose_type:'bsa',   dose:75,  unit:'mg/m²'},
      {key:'trastuzumab', dose_type:'kg',    dose:6,   loading:8,   unit:'mg/kg'},
      {key:'pertuzumab',  dose_type:'fixed', dose:420, loading:840, unit:'mg'}
    ]
  },
  {
    id:'thp_phesgo_meta', name:'THP + Phesgo SC (轉移)', group:'HER2+ 轉移',
    desc:'Docetaxel 75mg/m² + Phesgo SC  q3w（第1 cycle loading，後續 maintenance）',
    default_cycles:8, freq:'q3w',
    drugs:[
      {key:'docetaxel', dose_type:'bsa', dose:75, unit:'mg/m²'},
      {key:'phesgo',    dose_type:'fixed_sc_combo', dose:0, unit:'fixed dose'}
    ]
  },
  {
    id:'hp_maintenance', name:'HP 維持', group:'HER2+ 轉移',
    desc:'Herceptin 6mg/kg + Perjeta 420mg  q3w（化療完成後繼續維持）',
    default_cycles:12, freq:'q3w',
    drugs:[
      {key:'trastuzumab', dose_type:'kg',    dose:6,   unit:'mg/kg'},
      {key:'pertuzumab',  dose_type:'fixed', dose:420, unit:'mg'}
    ]
  },
  {
    id:'phesgo_maintenance', name:'Phesgo SC 維持', group:'HER2+ 轉移',
    desc:'Phesgo SC  q3w（第1 cycle loading，後續 maintenance；若已完成 loading 請以維持週期估算）',
    default_cycles:12, freq:'q3w',
    drugs:[
      {key:'phesgo', dose_type:'fixed_sc_combo', dose:0, unit:'fixed dose'}
    ]
  },
  {
    id:'tdm1_meta', name:'T-DM1 (轉移)', group:'HER2+ 轉移',
    desc:'T-DM1 3.6mg/kg  q3w（二線或以上）',
    default_cycles:8, freq:'q3w',
    drugs:[
      {key:'trastuzumab_emtansine', dose_type:'kg', dose:3.6, unit:'mg/kg'}
    ]
  },
  {
    id:'vh', name:'Vinorelbine + H', group:'HER2+ 轉移',
    desc:'Vinorelbine 25mg/m² d1,d8 + Herceptin 6mg/kg  q3w（輕鬆方案）',
    default_cycles:6, freq:'q3w',
    drugs:[
      {key:'vinorelbine', dose_type:'bsa', dose:25, unit:'mg/m² d1,d8'},
      {key:'trastuzumab', dose_type:'kg',  dose:6,  loading:8, unit:'mg/kg'}
    ]
  },

  // ════════════════════════════════
  // TNBC 轉移性 / 免疫治療
  // ════════════════════════════════
  {
    id:'pembro_wp_meta', name:'Keytruda + wP (轉移)', group:'TNBC 轉移/免疫',
    desc:'Pembrolizumab 200mg + weekly Paclitaxel 80mg/m²  q3w（KEYNOTE-355，PD-L1 CPS≥10）',
    default_cycles:8, freq:'q3w',
    drugs:[
      {key:'pembrolizumab', dose_type:'fixed', dose:200, unit:'mg'},
      {key:'paclitaxel',    dose_type:'bsa',   dose:80,  unit:'mg/m²（每週）'}
    ]
  },
  {
    id:'pembro_gc', name:'Keytruda + GC (轉移)', group:'TNBC 轉移/免疫',
    desc:'Pembrolizumab 200mg + Gemcitabine 1000mg/m² + Carboplatin AUC2  d1,d8  q3w',
    default_cycles:6, freq:'q3w',
    drugs:[
      {key:'pembrolizumab', dose_type:'fixed', dose:200, unit:'mg'},
      {key:'gemcitabine',   dose_type:'bsa',   dose:1000, unit:'mg/m² d1,d8'},
      {key:'carboplatin',   dose_type:'auc',   dose:2,   unit:'AUC d1,d8'}
    ]
  },
  {
    id:'pembro_alone_adj', name:'Keytruda 維持', group:'TNBC 轉移/免疫',
    desc:'Pembrolizumab 200mg  q3w × 9（KEYNOTE-522 術後輔助維持）',
    default_cycles:9, freq:'q3w',
    drugs:[
      {key:'pembrolizumab', dose_type:'fixed', dose:200, unit:'mg'}
    ]
  },

  // ════════════════════════════════
  // 單藥化療
  // ════════════════════════════════
  {
    id:'docetaxel_mono', name:'Docetaxel', group:'單藥化療',
    desc:'Docetaxel 75mg/m²  q3w',
    default_cycles:6, freq:'q3w',
    drugs:[
      {key:'docetaxel', dose_type:'bsa', dose:75, unit:'mg/m²'}
    ]
  },
  {
    id:'paclitaxel_q3w', name:'Paclitaxel q3w', group:'單藥化療',
    desc:'Paclitaxel 175mg/m²  q3w',
    default_cycles:6, freq:'q3w',
    drugs:[
      {key:'paclitaxel', dose_type:'bsa', dose:175, unit:'mg/m²'}
    ]
  },
  {
    id:'paclitaxel_weekly', name:'wPaclitaxel', group:'單藥化療',
    desc:'Paclitaxel 80mg/m²  每週',
    default_cycles:12, freq:'weekly',
    drugs:[
      {key:'paclitaxel', dose_type:'bsa', dose:80, unit:'mg/m²'}
    ]
  },
  {
    id:'nab_paclitaxel_mono', name:'nab-Paclitaxel', group:'單藥化療',
    desc:'nab-Paclitaxel 260mg/m²  q3w（或 150mg/m² 每週）',
    default_cycles:6, freq:'q3w',
    drugs:[
      {key:'nab_paclitaxel', dose_type:'bsa', dose:260, unit:'mg/m²'}
    ]
  },
  {
    id:'carbo_mono', name:'Carboplatin', group:'單藥化療',
    desc:'Carboplatin AUC5  q3w（BRCA 突變適用）',
    default_cycles:6, freq:'q3w',
    drugs:[
      {key:'carboplatin', dose_type:'auc', dose:5, unit:'AUC'}
    ]
  },
  {
    id:'gc_combo', name:'GC', group:'單藥化療',
    desc:'Gemcitabine 1000mg/m² + Carboplatin AUC2  d1,d8  q3w',
    default_cycles:6, freq:'q3w',
    drugs:[
      {key:'gemcitabine', dose_type:'bsa', dose:1000, unit:'mg/m² d1,d8'},
      {key:'carboplatin', dose_type:'auc', dose:2,    unit:'AUC d1,d8'}
    ]
  },
  {
    id:'vinorelbine_mono', name:'Vinorelbine', group:'單藥化療',
    desc:'Vinorelbine 25mg/m²  d1,d8  q3w',
    default_cycles:6, freq:'q3w',
    drugs:[
      {key:'vinorelbine', dose_type:'bsa', dose:25, unit:'mg/m² d1,d8'}
    ]
  },
  {
    id:'eribulin_mono', name:'Eribulin', group:'單藥化療',
    desc:'Eribulin 1.4mg/m²  d1,d8  q3w（二線以上，EMBRACE 試驗）',
    default_cycles:6, freq:'q3w',
    drugs:[
      {key:'eribulin', dose_type:'bsa', dose:1.4, unit:'mg/m² d1,d8'}
    ]
  },
  {
    id:'xeloda', name:'Xeloda', group:'單藥化療',
    desc:'Capecitabine 1000mg/m² BID × 14天  q3w',
    default_cycles:8, freq:'q3w',
    drugs:[
      {key:'capecitabine', dose_type:'bsa', dose:1000, unit:'mg/m² BID', isOral:true, freq_daily:2, days:14}
    ]
  },

  // ════════════════════════════════
  // 免疫治療單藥
  // ════════════════════════════════
  {
    id:'pembro_alone', name:'Pembrolizumab', group:'免疫治療',
    desc:'Pembrolizumab 200mg  q3w（或 400mg q6w）',
    default_cycles:18, freq:'q3w',
    drugs:[
      {key:'pembrolizumab', dose_type:'fixed', dose:200, unit:'mg'}
    ]
  }
];

// ── Vial optimizer (greedy, cheapest combo ≥ required dose) ──
function inpOptimizeVials(doseMg, drugKey, priceType){
  const drug = INP_DRUG_DATA[drugKey];
  if(!drug || !drug.vials) return {cost:0, combo:[], totalMg:doseMg};
  const vials = [...drug.vials].sort((a,b)=>b.size-a.size);
  const large = vials[0], small = vials[vials.length-1];
  let best = {cost:Infinity, combo:[], totalMg:0};
  const maxL = Math.ceil(doseMg/large.size)+1;
  for(let nL=0; nL<=maxL; nL++){
    const rem = doseMg - nL*large.size;
    let nS = 0;
    if(rem > 0 && large!==small) nS = Math.ceil(rem/small.size);
    else if(rem > 0) continue;
    const total = nL*large.size + nS*small.size;
    if(total < doseMg-0.01) continue;
    const cost = nL*(large[priceType]||large.nhi) + nS*(small[priceType]||small.nhi);
    if(cost < best.cost){
      best = {cost, totalMg:total, combo:[]};
      if(nL>0) best.combo.push({n:nL, label:large.label, price:large[priceType]||large.nhi});
      if(nS>0) best.combo.push({n:nS, label:small.label, price:small[priceType]||small.nhi});
    }
  }
  return best;
}

// ── Dose calculators ──
function inpCalcDose(drug, wt, bsa, crCl){
  if(drug.dose_type==='bsa')   return drug.dose * bsa;
  if(drug.dose_type==='kg')    return drug.dose * wt;
  if(drug.dose_type==='auc'){
    const aucVal = (drug.key==='carboplatin' && document.getElementById('inpAucTarget'))
      ? parseFloat(document.getElementById('inpAucTarget').value)||drug.dose
      : drug.dose;
    return aucVal * (crCl + 25); // Calvert
  }
  if(drug.dose_type==='fixed') return drug.dose;
  return drug.dose;
}
function inpCalcLoading(drug, wt){
  if(!drug.loading) return 0;
  return drug.dose_type==='kg' ? drug.loading * wt : drug.loading;
}

// ── Cockcroft-Gault ──
function calcInpCrCl(age, sex, wt, cr){
  return ((140-age) * wt * (sex==='F'?0.85:1.0)) / (72*cr);
}

// ── Patient update ──
function updateInpPatient(syncWorkspace){
  _inpWt  = parseFloat(document.getElementById('inpWt').value)||60;
  _inpHt  = parseFloat(document.getElementById('inpHt').value)||165;
  _inpAge = parseInt(document.getElementById('inpAge').value)||50;
  _inpSex = document.getElementById('inpSex').value;
  _inpCr  = parseFloat(document.getElementById('inpCr').value)||0.8;
  _inpBSA  = Math.sqrt((_inpHt*_inpWt)/3600);
  _inpCrCl = calcInpCrCl(_inpAge, _inpSex, _inpWt, _inpCr);
  document.getElementById('inpBSA').textContent  = 'BSA: '+_inpBSA.toFixed(2)+' m²';
  document.getElementById('inpCrCl').textContent = 'CrCl: '+Math.round(_inpCrCl)+' mL/min';
  if(syncWorkspace !== false && typeof setPatientField === 'function'){
    setPatientField('weight', String(_inpWt));
    setPatientField('height', String(_inpHt));
    setPatientField('age', String(_inpAge));
    setPatientField('sex', _inpSex);
    setPatientField('scr', String(_inpCr));
  }
  if(_inpSelectedRegimen) calcInpRegimen();
  if(document.body && document.body.classList.contains('modal-dashboard-mode') && typeof renderModalDashboardOverview === 'function'){
    renderModalDashboardOverview();
  }
}

function setInpPrice(type){
  _inpPriceType = type;
  document.getElementById('inpPriceNHI').classList.toggle('active', type==='nhi');
  document.getElementById('inpPriceSelf').classList.toggle('active', type==='self');
  if(_inpSelectedRegimen) calcInpRegimen();
}

function selectInpRegimen(id){
  _inpSelectedRegimen = INP_REGIMENS.find(r=>r.id===id);
  if(!_inpSelectedRegimen) return;
  document.querySelectorAll('.inp-reg-btn[data-id]').forEach(b=>{
    b.classList.toggle('active', b.dataset.id===id);
  });
  // Set default cycles
  const reg = _inpSelectedRegimen;
  const totalCycles = reg.sequential
    ? reg.phases.reduce((s,p)=>s+p.default_cycles,0)
    : reg.default_cycles;
  document.getElementById('inpCycles').value = totalCycles;
  document.getElementById('inpOptions').style.display='';
  // Show/hide AUC override for carboplatin regimens
  const allDrugs = reg.sequential ? reg.phases.flatMap(p=>p.drugs) : (reg.drugs||[]);
  const carbAuc = allDrugs.find(d=>d.key==='carboplatin' && d.dose_type==='auc');
  const aucOverride = document.getElementById('inpAucOverride');
  if(carbAuc){
    aucOverride.style.display='';
    document.getElementById('inpAucTarget').value = carbAuc.dose;
  } else {
    aucOverride.style.display='none';
  }
  calcInpRegimen();
  if(document.body && document.body.classList.contains('modal-dashboard-mode') && typeof renderModalDashboardOverview === 'function'){
    renderModalDashboardOverview();
  }
  setTimeout(()=>document.getElementById('inpOptions').scrollIntoView({behavior:'smooth',block:'nearest'}),100);
}

// ── Main calculation ──
function calcInpRegimen(){
  const reg = _inpSelectedRegimen;
  if(!reg) return;
  const pk = _inpPriceType;
  let detailHtml = '', grandTotal = 0;

  if(reg.sequential && reg.phases){
    reg.phases.forEach(phase=>{
      const {html, subtotal} = inpRenderPhase(phase.name, phase.drugs, phase.default_cycles, pk, phase.freq);
      detailHtml += html;
      grandTotal += subtotal;
    });
  } else {
    const cycles = parseInt(document.getElementById('inpCycles').value)||4;
    const {html, subtotal} = inpRenderPhase(reg.name, reg.drugs, cycles, pk, reg.freq);
    detailHtml += html;
    grandTotal += subtotal;
  }

  document.getElementById('inpDetail').innerHTML = detailHtml;

  const priceLabel = pk==='nhi' ? '健保藥價' : '台大自費藥價';
  _inpLastTotal = grandTotal;
  _inpLastPriceLabel = priceLabel;
  document.getElementById('inpSummary').innerHTML = `
    <div class="inp-summary">
      <div class="inp-sum-line" style="font-weight:700;font-size:.9rem;margin-bottom:.2rem">
        <span>${reg.name}　全療程費用</span>
        <span style="font-size:.77rem;font-weight:400;color:var(--text-muted)">${priceLabel}</span>
      </div>
      <div class="inp-sum-line" style="font-size:.78rem;color:var(--text-muted);margin-bottom:.3rem">
        <span>體重 ${_inpWt}kg　BSA ${_inpBSA.toFixed(2)} m²　CrCl ${Math.round(_inpCrCl)} mL/min</span>
      </div>
      <div class="inp-sum-line inp-sum-total">
        <span>合計（${priceLabel}）</span>
        <span>NT$ ${grandTotal.toLocaleString()}</span>
      </div>
      <div class="inp-sum-note">※ BSA 採 Mosteller 公式；Carboplatin 依 Calvert 公式（劑量 = AUC × (CrCl＋25)）；CrCl 依 Cockcroft-Gault 計算。Herceptin 首劑 8mg/kg 後續 6mg/kg，Perjeta 首劑 840mg 後續 420mg。Phesgo 以第1 cycle 15mL loading、後續 10mL maintenance 計算。安瓿以最少抽藥負擔與足量覆蓋估算（剩餘藥液捨棄不計）。藥價來源：NHI＝健保署115/03/23公告PDF（115/04/01生效），NTUH＝台大醫院2024/12參考藥價。本計算僅供估算參考，實際醫令以醫師處方為準。</div>
      <div style="text-align:center;margin-top:.8rem">
        <button class="btn btn-outline btn-sm" onclick="printInpRegimen()">&#128438; 列印 / 匯出 PDF</button>
      </div>
    </div>`;
}

function inpRenderPhase(phaseName, drugs, cycles, pk, freq){
  let drugRows = '', subtotal = 0;
  drugs.forEach(drug=>{
    const drugData = INP_DRUG_DATA[drug.key];
    if(!drugData) return;

    const doseMg    = inpCalcDose(drug, _inpWt, _inpBSA, _inpCrCl);
    const loadingMg = inpCalcLoading(drug, _inpWt);

    // Dose label
    let doseLabel = '';
    if(drug.dose_type==='bsa')
      doseLabel = drug.dose+' mg/m² × BSA '+_inpBSA.toFixed(2)+' = <strong>'+Math.round(doseMg)+'mg</strong>';
    else if(drug.dose_type==='kg')
      doseLabel = drug.dose+' mg/kg × '+_inpWt+'kg = <strong>'+Math.round(doseMg)+'mg</strong>'+(loadingMg?'；首劑 <strong>'+Math.round(loadingMg)+'mg</strong>':'');
    else if(drug.dose_type==='auc')
      doseLabel = 'AUC '+drug.dose+' × ('+Math.round(_inpCrCl)+'+25) = <strong>'+Math.round(doseMg)+'mg</strong>';
    else
      doseLabel = '<strong>'+doseMg+'mg</strong>（固定劑量）';

    let vialInfo = '', costTotal = 0, perCycleDisplay = null;

    if(drug.dose_type === 'fixed_sc_combo' && drugData.fixedDoses){
      const loading = drugData.fixedDoses.loading;
      const maint = drugData.fixedDoses.maintenance;
      const loadPrice = loading[pk] || loading.self || loading.nhi || 0;
      const maintPrice = maint[pk] || maint.self || maint.nhi || 0;
      costTotal = (cycles >= 1 ? loadPrice : 0) + Math.max(0, cycles-1) * maintPrice;
      perCycleDisplay = maintPrice;
      doseLabel = '<strong>首劑 15mL</strong>；後續 <strong>10mL q3w</strong>';
      vialInfo = '首劑: '+loading.label+' NT$'+loadPrice.toLocaleString()+
        (cycles>1?' | 後續(×'+(cycles-1)+'): '+maint.label+' NT$'+maintPrice.toLocaleString():'');
    } else if(drug.isOral || drugData.isOral){
      // Oral tablets
      const tabSize  = drugData.vials[0].size;
      const tabPrice = drugData.vials[0][pk]||drugData.vials[0].nhi;
      const tabsPerDose = Math.ceil(doseMg/tabSize);
      const freqD = drug.freq_daily||2;
      const days  = drug.days||14;
      const tabsPerCycle = tabsPerDose*freqD*days;
      costTotal = tabsPerCycle*tabPrice*cycles;
      vialInfo = tabsPerDose+'錠 × '+freqD+'次/天 × '+days+'天 = '+tabsPerCycle+'錠/cycle　單錠 NT$'+tabPrice;
    } else if(loadingMg>0 && cycles>=1){
      const loadOpt = inpOptimizeVials(loadingMg, drug.key, pk);
      const maintOpt= inpOptimizeVials(doseMg,    drug.key, pk);
      costTotal = loadOpt.cost + maintOpt.cost*(cycles-1);
      const loadStr = loadOpt.combo.map(c=>c.n+'×'+c.label).join(' + ')||'—';
      const maintStr= maintOpt.combo.map(c=>c.n+'×'+c.label).join(' + ')||'—';
      vialInfo = '首劑: '+loadStr+(cycles>1?' | 後續(×'+(cycles-1)+'): '+maintStr:'');
      perCycleDisplay = maintOpt.cost;
    } else {
      const opt = inpOptimizeVials(doseMg, drug.key, pk);
      costTotal = opt.cost*cycles;
      vialInfo = opt.combo.map(c=>c.n+'×'+c.label).join(' + ')||'—';
      perCycleDisplay = opt.cost;
    }

    subtotal += costTotal;
    drugRows += `<div class="inp-drug-row">
      <div class="inp-drug-info">
        <div class="inp-drug-name">${drugData.name}</div>
        <div class="inp-drug-dose">${doseLabel}</div>
        <div class="inp-vial-combo">${vialInfo}</div>
      </div>
      <div class="inp-drug-cost">
        <div>× ${cycles} = NT$ ${costTotal.toLocaleString()}</div>
        <div style="font-size:.7rem;font-weight:400;color:var(--text-muted)">單一 cycle NT$ ${Math.round(perCycleDisplay != null ? perCycleDisplay : costTotal/cycles).toLocaleString()}</div>
      </div>
    </div>`;
  });

  const cycleDays = freq==='weekly'?7:freq==='q2w'?14:freq==='q4w'?28:21;
  const months = (cycles*cycleDays/30).toFixed(1);
  const html = `<div class="inp-phase-box">
    <h4><span>${phaseName}　<small style="font-weight:400;font-size:.73rem">${freq} × ${cycles} cycles</small></span>
        <span style="font-size:.73rem;color:var(--text-muted)">~${months} 個月</span></h4>
    ${drugRows}
    <div style="display:flex;justify-content:space-between;font-size:.78rem;font-weight:600;margin-top:.4rem;padding-top:.4rem;border-top:1px dashed var(--border)">
      <span>Phase 小計</span>
      <span style="color:#0d9488">單一 cycle NT$ ${Math.round(subtotal/cycles).toLocaleString()}　/　全程 NT$ ${subtotal.toLocaleString()}</span>
    </div>
  </div>`;
  return {html, subtotal};
}

// ── Print ──
function printInpRegimen(){
  const reg = _inpSelectedRegimen;
  if(!reg){alert('請先選擇處方');return;}
  const today = new Date().toLocaleDateString('zh-TW');
  const detail  = document.getElementById('inpDetail').innerHTML;
  const summary = document.getElementById('inpSummary').innerHTML;
  const w = window.open('','_blank','width=720,height=920');
  if(!w){alert('請允許彈出視窗');return;}
  w.document.write(`<!DOCTYPE html><html><head><meta charset="UTF-8">
  <title>${reg.name} 住院化療費用計算 ${today}</title>
  <style>
    body{font-family:'Noto Sans TC',sans-serif;padding:1.5rem;font-size:13px;color:#0f172a;max-width:680px;margin:0 auto}
    h1{font-size:1.1rem;margin-bottom:.2rem}
    .sub{color:#64748b;font-size:.82rem;margin-bottom:1.2rem;padding-bottom:.6rem;border-bottom:1px solid #e2e8f0}
    .inp-phase-box{border:1px solid #e2e8f0;border-radius:8px;padding:.8rem;margin-bottom:.75rem}
    .inp-phase-box h4{font-size:.85rem;color:#0d9488;margin-bottom:.5rem;display:flex;justify-content:space-between}
    .inp-drug-row{display:flex;align-items:flex-start;gap:.5rem;padding:.35rem 0;border-bottom:1px solid #f1f5f9;flex-wrap:wrap}
    .inp-drug-row:last-child{border:none}
    .inp-drug-info{flex:1}.inp-drug-name{font-weight:600;font-size:.82rem}
    .inp-drug-dose{font-size:.72rem;color:#64748b}.inp-vial-combo{font-size:.72rem;color:#0d9488;font-weight:500}
    .inp-drug-cost{font-weight:700;font-size:.82rem;color:#0d9488;min-width:130px;text-align:right}
    .inp-summary{background:#f0fdfa;border:1px solid #99f6e4;border-radius:8px;padding:1rem}
    .inp-sum-line{display:flex;justify-content:space-between;padding:.25rem 0;font-size:.85rem}
    .inp-sum-total{font-weight:700;font-size:.95rem;color:#0f766e;border-top:2px solid #99f6e4;margin-top:.4rem;padding-top:.5rem}
    .inp-sum-note{font-size:.68rem;color:#94a3b8;margin-top:.6rem;font-style:italic;line-height:1.6}
    .footer{margin-top:1.5rem;font-size:.7rem;color:#94a3b8;border-top:1px solid #e2e8f0;padding-top:.5rem}
    @media print{body{padding:.5rem}}
  </style></head><body>
  <h1>${reg.name}　住院化療費用計算</h1>
  <div class="sub">列印日期：${today}　　體重：${_inpWt} kg　BSA：${_inpBSA.toFixed(2)} m²　CrCl：${Math.round(_inpCrCl)} mL/min　　藥價基準：${_inpPriceType==='nhi'?'健保藥價（公告115/03/23，生效115/04/01）':'台大自費藥價 (2024/12)'}</div>
  ${detail}
  ${summary}
  <div class="footer">本資料僅供醫療人員估算參考，實際劑量與費用以醫師處方及醫院計費為準。</div>
  <script>window.onload=function(){window.print()}<\/script>
  </body></html>`);
  w.document.close();
}

// ═══════════════════════════════════════════════════════
//  ICD碼查詢 (ICD Code Lookup for 重大傷病卡)
// ═══════════════════════════════════════════════════════
let _drugCardsIcdInited = false;

const ICD_ZONES = {
  UO: { label:'外上象限 (Upper-Outer Quadrant)', right:'C50.411', left:'C50.412', ntuhRight:'756', ntuhLeft:'754', hospitalRight:'C50411', hospitalLeft:'C50412', desc:'外上象限為最常見乳癌發生部位' },
  UI: { label:'內上象限 (Upper-Inner Quadrant)', right:'C50.211', left:'C50.212', ntuhRight:'750', ntuhLeft:'748', hospitalRight:'C50211', hospitalLeft:'C50212', desc:'' },
  LO: { label:'外下象限 (Lower-Outer Quadrant)', right:'C50.511', left:'C50.512', ntuhRight:'508', ntuhLeft:'506', hospitalRight:'C50511', hospitalLeft:'C50512', desc:'' },
  LI: { label:'內下象限 (Lower-Inner Quadrant)', right:'C50.311', left:'C50.312', ntuhRight:'502', ntuhLeft:'500', hospitalRight:'C50311', hospitalLeft:'C50312', desc:'' },
  nipple: { label:'乳頭及乳暈 (Nipple & Areola)', right:'C50.011', left:'C50.012', ntuhRight:'531', ntuhLeft:'529', hospitalRight:'C50011', hospitalLeft:'C50012', desc:'' }
};

const ICD_SIDE_CODES = [
  { code:'C50.811', ntuhCode:'577', hospitalCode:'C50811', side:'右乳', desc:'Malignant neoplasm of overlapping sites of right female breast — 跨象限/重疊部位（右乳）' },
  { code:'C50.812', ntuhCode:'561', hospitalCode:'C50812', side:'左乳', desc:'Malignant neoplasm of overlapping sites of left female breast — 跨象限/重疊部位（左乳）' },
  { code:'C50.111', ntuhCode:'383', hospitalCode:'C50111', side:'右乳', desc:'Malignant neoplasm of central portion of right female breast — 中央區（右乳）' },
  { code:'C50.112', ntuhCode:'381', hospitalCode:'C50112', side:'左乳', desc:'Malignant neoplasm of central portion of left female breast — 中央區（左乳）' },
  { code:'C50.611', ntuhCode:'358', hospitalCode:'C50611', side:'右乳', desc:'Malignant neoplasm of axillary tail of right female breast — 腋窩尾部（右乳）' },
  { code:'C50.612', ntuhCode:'356', hospitalCode:'C50612', side:'左乳', desc:'Malignant neoplasm of axillary tail of left female breast — 腋窩尾部（左乳）' },
  { code:'C50.911', ntuhCode:'731', hospitalCode:'C50911', side:'右乳', desc:'Malignant neoplasm of unspecified site of right female breast — 未明確部位（右乳）' },
  { code:'C50.912', ntuhCode:'728', hospitalCode:'C50912', side:'左乳', desc:'Malignant neoplasm of unspecified site of left female breast — 未明確部位（左乳）' },
  { code:'C50.A1', ntuhCode:'', hospitalCode:'', side:'右乳', desc:'Malignant inflammatory neoplasm of right breast — 炎性乳癌（右乳；院內清單未見對應編號）' },
  { code:'C50.A2', ntuhCode:'', hospitalCode:'', side:'左乳', desc:'Malignant inflammatory neoplasm of left breast — 炎性乳癌（左乳；院內清單未見對應編號）' },
];

const ICD_DCIS_CODES = [
  { code:'D05.11', side:'右乳', desc:'Intraductal carcinoma in situ of right breast — 右乳導管原位癌 (DCIS)' },
  { code:'D05.12', side:'左乳', desc:'Intraductal carcinoma in situ of left breast — 左乳導管原位癌 (DCIS)' },
  { code:'D05.01', side:'右乳', desc:'Lobular carcinoma in situ of right breast — 右乳小葉原位癌 (LCIS)' },
  { code:'D05.02', side:'左乳', desc:'Lobular carcinoma in situ of left breast — 左乳小葉原位癌 (LCIS)' },
  { code:'D05.81', side:'右乳', desc:'Other specified type of carcinoma in situ of right breast — 右乳其他原位癌' },
  { code:'D05.82', side:'左乳', desc:'Other specified type of carcinoma in situ of left breast — 左乳其他原位癌' },
  { code:'D05.10', side:'不明確', desc:'Intraductal carcinoma in situ of unspecified breast — 未指定側導管原位癌' },
  { code:'D05.00', side:'不明確', desc:'Lobular carcinoma in situ of unspecified breast — 未指定側小葉原位癌' },
];

function drugCardsSelectIcdZone(side, zone){
  document.querySelectorAll('.icd-q').forEach(el=>el.classList.remove('selected'));
  document.querySelectorAll(`.icd-q[data-side="${side}"][data-zone="${zone}"]`).forEach(el=>el.classList.add('selected'));
  const info = ICD_ZONES[zone];
  if(!info) return;
  const sideLabel = side==='R' ? '右乳' : '左乳';
  const code = side==='R' ? info.right : info.left;
  const ntuhCode = side==='R' ? info.ntuhRight : info.ntuhLeft;
  const hospitalCode = side==='R' ? info.hospitalRight : info.hospitalLeft;
  const zoneDesc = zone==='UO'?'（最常見乳癌部位）':zone==='nipple'?'（乳頭/乳暈區）':'';
  if(typeof setPatientField === 'function'){
    setPatientField('side', side);
    setPatientField('quadrant', zone);
  } else if(typeof _patient !== 'undefined') {
    _patient.side = side;
    _patient.quadrant = zone;
  }
  document.getElementById('icdPopupArea').innerHTML = `
    <div class="icd-popup">
      <div class="icd-popup-title">${sideLabel}　${info.label}</div>
      <div style="font-size:.75rem;color:var(--text-muted);margin:.2rem 0 .5rem">${zoneDesc}院內重卡申請優先使用「院內編號」；點擊可複製。</div>
      <div class="icd-code-row">
        <span class="icd-code ntuh-code" id="icdCopyCode" onclick="icdCopy('${ntuhCode}')">${ntuhCode}</span>
        <span style="font-size:.82rem"><strong>院內重卡編號</strong>　${sideLabel}　${info.label}</span>
      </div>
      <div class="icd-code-row">
        <span class="icd-code" onclick="icdCopy('${hospitalCode}')">${hospitalCode}</span>
        <span style="font-size:.82rem">院內診斷碼（ICD 去點號）</span>
      </div>
      <div class="icd-code-row">
        <span class="icd-code" onclick="icdCopy('${code}')">${code}</span>
        <span style="font-size:.82rem">ICD-10-CM 對照</span>
      </div>
      <div style="margin-top:.7rem;padding-top:.5rem;border-top:1px solid #fda4af;font-size:.72rem;color:var(--text-muted)">
        <div>重大傷病申請代碼：<strong style="color:#be123c">010</strong>（乳癌）</div>
        <div style="margin-top:.2rem">院內重卡編號：<strong style="color:#be123c">${ntuhCode}</strong>　院內診斷碼：<strong style="color:#be123c">${hospitalCode}</strong>　ICD-10-CM：<strong style="color:#be123c">${code}</strong></div>
      </div>
    </div>`;
}

function drugCardsIcdCopy(code){
  const done = () => {
    const el = document.getElementById('icdCopyCode');
    if(el){ el.textContent = code+' ✓'; setTimeout(()=>{ if(el) el.textContent=code; },1500); }
  };
  if(navigator.clipboard && navigator.clipboard.writeText){
    navigator.clipboard.writeText(code).then(done).catch(()=>window.prompt('請複製代碼', code));
  } else {
    window.prompt('請複製代碼', code);
  }
}

function drugCardsInitIcdPage(){
  _drugCardsIcdInited = true;
  const makeRow = (c) => {
    const ntuh = c.ntuhCode || '';
    const hospital = c.hospitalCode || '';
    const ntuhCell = ntuh
      ? `<span class="icd-code ntuh-code" style="min-width:72px" onclick="icdCopy('${ntuh}')" title="點擊複製院內重卡編號">${ntuh}</span>`
      : `<span class="icd-code icd-code-empty" style="min-width:72px" title="院內清單未收載">—</span>`;
    const hospitalCell = hospital
      ? `<span class="icd-code" style="min-width:72px" onclick="icdCopy('${hospital}')" title="點擊複製院內診斷碼">${hospital}</span>`
      : `<span class="icd-code icd-code-empty" style="min-width:72px" title="院內診斷碼未收載">—</span>`;
    return `<div class="icd-side-item">
      ${ntuhCell}
      ${hospitalCell}
      <span class="icd-code" style="min-width:72px" onclick="icdCopy('${c.code}')" title="點擊複製 ICD">${c.code}</span>
      <span><strong style="color:#be123c">${c.side}</strong>　${c.desc}</span>
    </div>`;
  };
  document.getElementById('icdSideList').innerHTML = ICD_SIDE_CODES.map(makeRow).join('');
  document.getElementById('icdDcislist').innerHTML = ICD_DCIS_CODES.map(makeRow).join('');
}

// ═══════════════════════════════════════════════════════
//  手術自費醫材清單
// ═══════════════════════════════════════════════════════
let _surgInited = false;

const SURG_DEFAULT_ITEMS = [
  { group:'前哨淋巴精準定位', en:'Lymphscintigraphy', zh:'前哨淋巴掃描', code:'000TP144', price:3463, note:'' },
  { group:'前哨淋巴精準定位', en:'Patent Blue', zh:'拍得藍注射液', code:'PAT1PC03', price:2125, note:'' },
  { group:'前哨淋巴精準定位', en:'Diagnogreen', zh:'循血綠注射劑', code:'DIA1PA22', price:2125, note:'' },
  { group:'前哨淋巴精準定位', en:'SPY-PHI Drape', zh:'手持攝影頭滅菌套', code:'20509712', price:2160, note:'' },
  { group:'前哨淋巴精準定位', en:'SPY-PHI Stryker', zh:'螢光顯影開機費', code:'0YHB1009', price:20000, note:'' },
  { group:'術中使用', en:'Plasma Blade', zh:'低溫電漿手術刀', code:'20325608', price:17550, note:'' },
  { group:'術中使用', en:'SURGIFLO', zh:'止血劑', code:'20452030', price:24440, note:'可減少術後腫脹、減少引流量，腋下淋巴廓清及大範圍切除患者可考慮使用' },
  { group:'術中使用', en:'Wound Retractor', zh:'傷口撐開/保護器', code:'20437224', price:2180, note:'傷口保護器可在術中保護傷口，不受器械及電燒傷害' },
  { group:'術中使用', en:'Collagen Dressing', zh:'膠原蛋白敷料（癒立安）', code:'20452396', price:22750, note:'用於填塞切除後之空腔，可加速內部傷口復原' },
  { group:'術後照護用品', en:'Gen Tek Carefix', zh:'術後衣', code:'20449990', price:8515, note:'' },
  { group:'術後照護用品', en:'台灣富盛得術後衣', zh:'壓迫緊密但拆裝容易，返家後可重複使用（加贈腋下加壓帶）', code:'—', price:2800, note:'' },
  { group:'術後照護用品', en:'芙爾摩莎超薄彈力膜', zh:'術後衣', code:'—', price:2200, note:'' },
  { group:'術後照護用品', en:'SurgiSeal', zh:'速近傷口黏膠劑', code:'20471332', price:6760, note:'' },
  { group:'術後照護用品', en:'TissueAid', zh:'高黏度組織黏著劑', code:'20471326', price:3227, note:'' },
  { group:'內視鏡乳房手術', en:'Trocar (5mm)', zh:'安德派思腹腔鏡套管', code:'20220080', price:1138, note:'' },
  { group:'內視鏡乳房手術', en:'Trocar (12mm)', zh:'安德派思腹腔鏡套管', code:'20220079', price:1208, note:'' },
  { group:'內視鏡乳房手術', en:'Laparoscopy', zh:'內視鏡使用費', code:'28014C00', price:5959, note:'' },
  { group:'內視鏡乳房手術', en:'NELIS Glove Port', zh:'內視鏡用端口', code:'20437242', price:26000, note:'' },
  { group:'內視鏡乳房手術', en:'Suction Irrigation', zh:'內視鏡用沖吸管組', code:'20219907', price:2470, note:'' },
  { group:'內視鏡乳房手術', en:'LigaSure Maryland', zh:'利嘉修爾鉗口閉合器', code:'20445100', price:29025, note:'' },
  { group:'乳房微創手術', en:'"SenoRx" EnCor Biopsy Probe', zh:'安可兒切片探針（含附件）', code:'20281007', price:15525, note:'' },
  { group:'整形式乳房手術', en:'Oncoplasty Surgery', zh:'整形式乳頭提升', code:'000B4348', price:18000, note:'' },
  { group:'整形式乳房手術', en:'疤痕重整（特小）', zh:'疤痕重整（特小）', code:'000B4355', price:5000, note:'' },
  { group:'整形式乳房手術', en:'疤痕重整（超大）', zh:'疤痕重整（超大）', code:'000B4357', price:20000, note:'' },
  { group:'整形式乳房手術', en:'Breast Reconstruction', zh:'乳房重建技術費', code:'0YHB1003', price:50000, note:'' },
  { group:'整形式乳房手術', en:'Tissue Expander', zh:'光滑面組織擴張器', code:'20381010', price:14598, note:'用於橋接二階段重建，可先進行後續療程，完成治療再進行完整重建手術' },
  { group:'基因檢測', en:'NGS Hereditary Breast Cancer Gene', zh:'次世代定序遺傳性基因變異檢測', code:'000X0230', price:30000, note:'' },
  { group:'基因檢測', en:'Oncotype Dx / FoundationOne CDx', zh:'安可待乳癌腫瘤基因檢測/全方位癌症基因組織檢測', code:'—', price:170000, note:'約17萬，實際依廠商報價' },
];
let SURG_ITEMS = [];
const SURG_ITEMS_KEY = '_surgery_items_v1';
const SURG_CONTEXT_KEY = '_surgery_context_v1';

function initSurgeryList(){
  _surgInited = true;
  loadSurgeryItems();
  loadSurgeryContext();
  renderSurgeryList();
}

function loadSurgeryItems(){
  try {
    const saved = localStorage.getItem(SURG_ITEMS_KEY);
    SURG_ITEMS = saved ? JSON.parse(saved) : JSON.parse(JSON.stringify(SURG_DEFAULT_ITEMS));
    if(!Array.isArray(SURG_ITEMS)) throw new Error('invalid surgery list');
  } catch(e){
    SURG_ITEMS = JSON.parse(JSON.stringify(SURG_DEFAULT_ITEMS));
  }
}

function saveSurgeryItems(){
  try { localStorage.setItem(SURG_ITEMS_KEY, JSON.stringify(SURG_ITEMS)); } catch(e){}
}

function renderSurgeryList(){
  const groups = {};
  SURG_ITEMS.forEach((item, idx)=>{
    if(!groups[item.group]) groups[item.group]=[];
    groups[item.group].push({...item, idx});
  });
  let html = '';
  Object.keys(groups).forEach(g=>{
    html += `<div class="surg-group-title">${g}</div>`;
    groups[g].forEach(item=>{
      html += `<div class="surg-item" id="surg_row_${item.idx}">
        <input type="checkbox" id="surg_${item.idx}" data-price="${item.price}" onchange="updateSurgTotal()">
        <div class="surg-item-info">
          <div class="surg-item-name">${item.en}</div>
          <div class="surg-item-zh">${item.zh}</div>
          ${item.code!=='—'?`<div class="surg-item-code">院內碼：${item.code}</div>`:''}
          ${item.note?`<div class="surg-note">※ ${item.note}</div>`:''}
        </div>
        <div class="surg-item-price">NT$ ${(Number(item.price)||0).toLocaleString()}</div>
      </div>`;
    });
  });
  document.getElementById('surgeryList').innerHTML = html;
  updateSurgTotal();
  renderSurgeryAdmin();
}

function loadSurgeryContext(){
  try {
    const saved = JSON.parse(localStorage.getItem(SURG_CONTEXT_KEY) || '{}');
    if(saved.hospital && document.getElementById('surgHospital')) document.getElementById('surgHospital').value = saved.hospital;
    if(saved.code && document.getElementById('surgMaintCode')) document.getElementById('surgMaintCode').value = saved.code;
  } catch(e){}
  updateSurgeryContext();
}

function updateSurgeryContext(){
  const hospitalEl = document.getElementById('surgHospital');
  const codeEl = document.getElementById('surgMaintCode');
  const hospital = hospitalEl ? hospitalEl.value : 'NTUCC';
  const code = codeEl ? (codeEl.value.trim() || 'NTUCC HSW') : 'NTUCC HSW';
  const label = hospitalEl ? hospitalEl.options[hospitalEl.selectedIndex].text : '台大癌醫';
  const pill = document.getElementById('surgContextPill');
  if(pill) pill.textContent = `${hospital} ${code.replace(/^.*?\s/, '')}`;
  try { localStorage.setItem(SURG_CONTEXT_KEY, JSON.stringify({hospital, hospitalLabel: label, code})); } catch(e){}
}

function toggleSurgeryAdmin(){
  const panel = document.getElementById('surgAdminPanel');
  if(!panel) return;
  panel.classList.toggle('show');
  renderSurgeryAdmin();
}

function renderSurgeryAdmin(){
  const el = document.getElementById('surgAdminList');
  if(!el) return;
  el.innerHTML = SURG_ITEMS.map((item, idx)=>`<div class="surg-admin-row">
    <span><strong>${item.en || item.zh || '未命名'}</strong> · ${item.group || '未分類'} · NT$ ${(Number(item.price)||0).toLocaleString()}</span>
    <span style="display:flex;gap:.3rem"><button class="btn btn-outline btn-sm" onclick="editSurgeryItem(${idx})">編輯</button><button class="btn btn-outline btn-sm" onclick="deleteSurgeryItem(${idx})">刪除</button></span>
  </div>`).join('');
}

function clearSurgeryEdit(){
  ['surgEditIndex','surgEditGroup','surgEditEn','surgEditZh','surgEditCode','surgEditPrice','surgEditNote'].forEach(id=>{
    const e = document.getElementById(id); if(e) e.value = '';
  });
}

function editSurgeryItem(idx){
  const item = SURG_ITEMS[idx]; if(!item) return;
  document.getElementById('surgEditIndex').value = idx;
  document.getElementById('surgEditGroup').value = item.group || '';
  document.getElementById('surgEditEn').value = item.en || '';
  document.getElementById('surgEditZh').value = item.zh || '';
  document.getElementById('surgEditCode').value = item.code || '';
  document.getElementById('surgEditPrice').value = item.price || 0;
  document.getElementById('surgEditNote').value = item.note || '';
}

function saveSurgeryEdit(){
  const item = {
    group: document.getElementById('surgEditGroup').value.trim() || '未分類',
    en: document.getElementById('surgEditEn').value.trim(),
    zh: document.getElementById('surgEditZh').value.trim(),
    code: document.getElementById('surgEditCode').value.trim() || '—',
    price: Math.max(0, Math.round(+document.getElementById('surgEditPrice').value || 0)),
    note: document.getElementById('surgEditNote').value.trim()
  };
  if(!item.en && !item.zh){ alert('請至少填入品名或中文說明'); return; }
  const idx = document.getElementById('surgEditIndex').value;
  if(idx !== '' && SURG_ITEMS[+idx]) SURG_ITEMS[+idx] = item;
  else SURG_ITEMS.push(item);
  saveSurgeryItems();
  clearSurgeryEdit();
  renderSurgeryList();
}

function deleteSurgeryItem(idx){
  if(!SURG_ITEMS[idx]) return;
  if(!confirm('刪除此項目？')) return;
  SURG_ITEMS.splice(idx, 1);
  saveSurgeryItems();
  renderSurgeryList();
}

function resetSurgeryItems(){
  if(!confirm('恢復預設清單？目前維護的修改會被覆蓋。')) return;
  SURG_ITEMS = JSON.parse(JSON.stringify(SURG_DEFAULT_ITEMS));
  saveSurgeryItems();
  clearSurgeryEdit();
  renderSurgeryList();
}

function exportSurgeryItems(){
  const data = JSON.stringify(SURG_ITEMS, null, 2);
  const blob = new Blob([data], {type:'application/json'});
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `surgery_items_${new Date().toISOString().slice(0,10)}.json`;
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(()=>URL.revokeObjectURL(url), 1000);
}

function parseSurgeryCSV(text){
  const lines = text.split(/\r?\n/).filter(x=>x.trim());
  if(lines.length < 2) return [];
  const headers = lines.shift().split(',').map(h=>h.trim().toLowerCase());
  return lines.map(line=>{
    const cols = line.split(',').map(x=>x.trim());
    const obj = {};
    headers.forEach((h,i)=> obj[h] = cols[i] || '');
    return {
      group: obj.group || obj['分類'] || '未分類',
      en: obj.en || obj.name || obj['品名'] || '',
      zh: obj.zh || obj['中文'] || obj.description || '',
      code: obj.code || obj['院內碼'] || '—',
      price: Math.max(0, Math.round(+(obj.price || obj['價格'] || 0))),
      note: obj.note || obj['備註'] || ''
    };
  }).filter(x=>x.en || x.zh);
}

function importSurgeryItems(event){
  const file = event.target.files && event.target.files[0];
  if(!file) return;
  const reader = new FileReader();
  reader.onload = ev => {
    try {
      const text = ev.target.result;
      const list = file.name.toLowerCase().endsWith('.csv') ? parseSurgeryCSV(text) : JSON.parse(text);
      if(!Array.isArray(list) || !list.length) throw new Error('empty list');
      SURG_ITEMS = list.map(x=>({
        group: x.group || '未分類',
        en: x.en || x.name || '',
        zh: x.zh || x.description || '',
        code: x.code || '—',
        price: Math.max(0, Math.round(+x.price || 0)),
        note: x.note || ''
      })).filter(x=>x.en || x.zh);
      if(!SURG_ITEMS.length) throw new Error('no valid rows');
      saveSurgeryItems();
      renderSurgeryList();
      alert('已更新手術醫材清單');
    } catch(e){
      alert('上傳失敗：請使用 JSON 陣列，或 CSV 欄位 group,en,zh,code,price,note');
    } finally {
      event.target.value = '';
    }
  };
  reader.readAsText(file, 'utf-8');
}

function updateSurgTotal(){
  let total = 0;
  document.querySelectorAll('#surgeryList input[type=checkbox]:checked').forEach(cb=>{
    total += parseInt(cb.dataset.price)||0;
    cb.closest('.surg-item').style.background='#f0fdf4';
    cb.closest('.surg-item').style.borderColor='#6ee7b7';
  });
  document.querySelectorAll('#surgeryList input[type=checkbox]:not(:checked)').forEach(cb=>{
    cb.closest('.surg-item').style.background='';
    cb.closest('.surg-item').style.borderColor='';
  });
  document.getElementById('surgTotal').textContent = 'NT$ '+total.toLocaleString();
}

function clearSurgeryChecks(){
  document.querySelectorAll('#surgeryList input[type=checkbox]').forEach(cb=>cb.checked=false);
  updateSurgTotal();
}

function printSurgeryList(){
  const checked = [];
  document.querySelectorAll('#surgeryList input[type=checkbox]:checked').forEach(cb=>{
    const row = cb.closest('.surg-item');
    const name = row.querySelector('.surg-item-name').textContent;
    const zh   = row.querySelector('.surg-item-zh').textContent;
    const price= parseInt(cb.dataset.price)||0;
    checked.push({name, zh, price});
  });
  if(checked.length===0){alert('請先勾選項目');return;}
  const total = checked.reduce((s,c)=>s+c.price,0);
  const today = new Date().toLocaleDateString('zh-TW');
  const hospitalEl = document.getElementById('surgHospital');
  const hospitalLabel = hospitalEl ? hospitalEl.options[hospitalEl.selectedIndex].text : '台大癌醫';
  const maintCodeEl = document.getElementById('surgMaintCode');
  const maintCode = ((maintCodeEl ? maintCodeEl.value : '') || 'NTUCC HSW').trim();
  const rows = checked.map(c=>`<tr><td>${c.name}</td><td>${c.zh}</td><td style="text-align:right">NT$ ${c.price.toLocaleString()}</td></tr>`).join('');
  const w = window.open('','_blank','width=700,height=800');
  if(!w){alert('請允許彈出視窗');return;}
  w.document.write(`<!DOCTYPE html><html><head><meta charset="UTF-8"><title>手術自費清單 ${today}</title>
  <style>body{font-family:'Noto Sans TC',sans-serif;padding:1.5rem;font-size:13px;max-width:620px;margin:0 auto}
  h1{font-size:1.1rem}table{width:100%;border-collapse:collapse;margin-top:1rem}
  th{background:#f0fdf4;padding:.4rem .6rem;font-size:.78rem;text-align:left;border:1px solid #a7f3d0}
  td{padding:.35rem .6rem;border:1px solid #e2e8f0;font-size:.8rem}
  tfoot td{font-weight:700;background:#ecfdf5;color:#059669}
  .note{font-size:.68rem;color:#94a3b8;margin-top:1rem;font-style:italic}
  @media print{body{padding:.3rem}}</style></head><body>
  <h1>手術自費醫材清單</h1>
  <div style="color:#6b7280;font-size:.8rem;margin-bottom:.5rem">院區：${hospitalLabel}；維護代號：${maintCode}；列印日期：${today}</div>
  <table><thead><tr><th>品項</th><th>中文名稱</th><th style="text-align:right">定價</th></tr></thead>
  <tbody>${rows}</tbody>
  <tfoot><tr><td colspan="2">合計</td><td style="text-align:right">NT$ ${total.toLocaleString()}</td></tr></tfoot>
  </table>
  <div class="note">※ 本清單為估算參考用，實際費用依各院區公告與住院時簽署之自費同意書為準。</div>
  <scr`+'ipt>window.onload=function(){window.print()}</scr'+'ipt></body></html>');
  w.document.close();
}

// ═══════════════════════════════════════════════════════
//  臨床試驗搜尋 (ClinicalTrials.gov API v2)
// ═══════════════════════════════════════════════════════
let _lastTrialResults = [];
let _lastTrialTotal = 0;
async function searchTrials(){
  const keyword  = document.getElementById('trialKeyword').value.trim() || 'breast cancer';
  const location = document.getElementById('trialLocation').value.trim() || 'Taiwan';
  const status   = document.getElementById('trialStatus').value;
  const el = document.getElementById('trialResults');
  el.innerHTML = '<div style="color:var(--text-muted);padding:1rem">搜尋中，請稍候…</div>';
  _lastTrialResults = [];
  _lastTrialTotal = 0;

  try {
    const params = new URLSearchParams({
      'query.cond': keyword,
      'query.locn': location,
      'pageSize': 100,
      'fields': 'NCTId,BriefTitle,OverallStatus,Phase,StartDate,PrimaryCompletionDate,LeadSponsorName,LocationFacility,LocationCity,LocationCountry,BriefSummary,EligibilityCriteria',
      'format': 'json'
    });
    if(status) params.set('filter.overallStatus', status);

    const resp = await fetch(`https://clinicaltrials.gov/api/v2/studies?${params}`);
    if(!resp.ok) throw new Error('API error: '+resp.status);
    const data = await resp.json();
    const studies = data.studies || [];
    _lastTrialTotal = data.totalCount || studies.length;

    if(studies.length===0){
      el.innerHTML='<div style="padding:1rem;color:var(--text-muted)">未找到符合條件的試驗。請嘗試修改關鍵字或地點。</div>';
      return;
    }

    let html = `<div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:.4rem;margin-bottom:.6rem">
        <div style="font-size:.78rem;color:var(--text-muted)">符合條件 ${_lastTrialTotal} 筆（顯示前 ${studies.length} 筆）</div>
        <div style="display:flex;gap:.35rem">
          <button class="btn btn-outline btn-sm" onclick="exportTrialsCSV()" title="匯出為 CSV (Excel 可開啟)">&#11015;&#65039; CSV</button>
          <button class="btn btn-outline btn-sm" onclick="printTrialsList()" title="列印或存成 PDF">&#128438; 列印/PDF</button>
        </div>
      </div>`;
    studies.forEach(s=>{
      const ps = s.protocolSection||{};
      const id = ps.identificationModule||{};
      const statusMod = ps.statusModule||{};
      const design = ps.designModule||{};
      const sponsor = ps.sponsorCollaboratorsModule||{};
      const locations = ps.contactsLocationsModule||{};
      const desc = ps.descriptionModule||{};
      const elig = ps.eligibilityModule||{};

      const nctId = id.nctId||'';
      const title = id.briefTitle||'(no title)';
      const overallStatus = statusMod.overallStatus||'';
      const phase = (design.phases||[]).join(', ')||'N/A';
      const leadSponsor = sponsor.leadSponsor && sponsor.leadSponsor.name ? sponsor.leadSponsor.name : '';
      const twLocs = (locations.locations||[]).filter(l=>l.country==='Taiwan');
      const locs = twLocs.map(l=>`${l.facility||''} (${l.city||''})`).slice(0,3).join('、');
      const startDate = statusMod.startDateStruct && statusMod.startDateStruct.date ? statusMod.startDateStruct.date : '';
      const completionDate = statusMod.primaryCompletionDateStruct && statusMod.primaryCompletionDateStruct.date ? statusMod.primaryCompletionDateStruct.date : '';
      const briefSummary = desc.briefSummary || '';
      const eligibility = elig.eligibilityCriteria || '';

      _lastTrialResults.push({
        nctId, title, overallStatus, phase, leadSponsor,
        locs, startDate, completionDate, briefSummary, eligibility
      });

      const badgeClass = overallStatus==='RECRUITING'?'recruiting':'active';
      const badgeLabel = overallStatus==='RECRUITING'?'招募中':overallStatus==='ACTIVE_NOT_RECRUITING'?'進行中':'其他';

      html += `<div class="trial-card">
        <div style="display:flex;gap:.5rem;align-items:flex-start;flex-wrap:wrap">
          <span class="trial-badge ${badgeClass}">${badgeLabel}</span>
          <span class="trial-badge trial-phase">${phase}</span>
        </div>
        <div class="trial-title" style="margin-top:.3rem">${title}</div>
        <div class="trial-meta">
          <span>&#128196; <a href="https://clinicaltrials.gov/study/${nctId}" target="_blank" style="color:#0369a1">${nctId}</a></span>
          ${leadSponsor?`<span>&#127970; ${leadSponsor}</span>`:''}
        </div>
        ${locs?`<div class="trial-locations">&#128205; 台灣試驗中心：${locs}</div>`:''}
      </div>`;
    });
    el.innerHTML = html;
    if(document.body && document.body.classList.contains('modal-dashboard-mode') && typeof renderModalDashboardOverview === 'function'){
      renderModalDashboardOverview();
    }
  } catch(err){
    el.innerHTML = `<div style="padding:1rem;color:#ef4444">搜尋失敗：${err.message}。請確認網路連線，或稍後再試。</div>`;
  }
}

function _csvEsc(v){
  v = String(v==null?'':v).replace(/\r?\n/g,' ').replace(/\s+/g,' ').trim();
  return /[",]/.test(v) ? `"${v.replace(/"/g,'""')}"` : v;
}
function exportTrialsCSV(){
  if(!_lastTrialResults.length){ alert('尚無試驗資料可匯出'); return; }
  const headers = ['NCT編號','試驗名稱','期別','狀態','主辦單位','台灣試驗中心','開始日期','預計完成日期','摘要','招募條件'];
  const rows = _lastTrialResults.map(t => [
    t.nctId, t.title, t.phase, t.overallStatus, t.leadSponsor,
    t.locs, t.startDate, t.completionDate, t.briefSummary, t.eligibility
  ].map(_csvEsc).join(','));
  const csv = '﻿' + headers.join(',') + '\r\n' + rows.join('\r\n');
  const blob = new Blob([csv], {type:'text/csv;charset=utf-8;'});
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `clinical_trials_${new Date().toISOString().slice(0,10)}.csv`;
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(()=>URL.revokeObjectURL(url), 1000);
}
function printTrialsList(){
  if(!_lastTrialResults.length){ alert('尚無試驗資料可列印'); return; }
  const today = new Date().toLocaleDateString('zh-TW');
  const esc = s => String(s==null?'':s).replace(/[<>&]/g, c=>({'<':'&lt;','>':'&gt;','&':'&amp;'}[c]));
  let body = '';
  _lastTrialResults.forEach((t,i) => {
    const recBadge = t.overallStatus==='RECRUITING' ? '<span class="badge rec">招募中</span>' :
                     t.overallStatus==='ACTIVE_NOT_RECRUITING' ? '<span class="badge">進行中</span>' :
                     `<span class="badge">${esc(t.overallStatus)}</span>`;
    body += `<div class="trial">
      <div><span class="nct">${i+1}. ${esc(t.nctId)}</span> &nbsp; ${recBadge}<span class="badge">${esc(t.phase)}</span></div>
      <div class="title">${esc(t.title)}</div>
      <div class="meta"><span class="label">主辦：</span>${esc(t.leadSponsor)||'—'}</div>
      ${t.locs ? `<div class="meta"><span class="label">台灣試驗中心：</span>${esc(t.locs)}</div>` : ''}
      <div class="meta"><span class="label">開始：</span>${esc(t.startDate)||'—'} &nbsp; <span class="label">預計完成：</span>${esc(t.completionDate)||'—'}</div>
      ${t.briefSummary ? `<div class="summary">${esc(t.briefSummary.slice(0,500))}${t.briefSummary.length>500?'…':''}</div>` : ''}
    </div>`;
  });
  const html = `<!DOCTYPE html><html><head><meta charset="utf-8"><title>臨床試驗清單 ${today}</title>
    <style>
      body{font-family:'Microsoft JhengHei','Noto Sans CJK TC',sans-serif;padding:18px;font-size:11px;color:#1f2937;line-height:1.45}
      h1{font-size:16px;margin:0;color:#0369a1}
      .header{display:flex;justify-content:space-between;align-items:center;border-bottom:2px solid #0369a1;padding-bottom:8px;margin-bottom:14px}
      .meta-line{font-size:10px;color:#6b7280}
      .trial{border:1px solid #e5e7eb;border-left:3px solid #0369a1;border-radius:4px;padding:9px 11px;margin-bottom:8px;page-break-inside:avoid}
      .nct{font-weight:600;color:#0369a1}
      .badge{display:inline-block;padding:1px 6px;border-radius:8px;font-size:9px;font-weight:600;background:#e0f2fe;color:#075985;margin-right:4px}
      .badge.rec{background:#dcfce7;color:#166534}
      .title{font-weight:700;font-size:12px;margin:4px 0;color:#111827}
      .meta{font-size:10px;color:#4b5563;margin:2px 0}
      .label{font-weight:600;color:#374151}
      .summary{font-size:10px;color:#374151;margin-top:5px;padding-top:5px;border-top:1px dashed #e5e7eb}
      @media print { body{padding:0} .no-print{display:none} }
      .actions{position:fixed;top:10px;right:10px}
      .actions button{background:#0369a1;color:white;border:0;padding:8px 14px;border-radius:6px;font-size:12px;cursor:pointer;font-family:inherit}
    </style></head><body>
    <div class="actions no-print"><button onclick="window.print()">&#128438; 列印 / 存 PDF</button></div>
    <div class="header">
      <div><h1>&#129514; 乳癌相關臨床試驗清單</h1><div class="meta-line">資料來源：ClinicalTrials.gov</div></div>
      <div class="meta-line" style="text-align:right">${today}<br>共 ${_lastTrialResults.length} 筆</div>
    </div>${body}</body></html>`;
  const w = window.open('', '_blank');
  if(!w){ alert('請允許彈出視窗以列印試驗清單'); return; }
  w.document.write(html);
  w.document.close();
}

Object.assign(window, {
  initSurgeryList,
  renderSurgeryList,
  loadSurgeryItems,
  loadSurgeryContext,
  updateSurgeryContext,
  toggleSurgeryAdmin,
  renderSurgeryAdmin,
  clearSurgeryEdit,
  editSurgeryItem,
  saveSurgeryEdit,
  deleteSurgeryItem,
  resetSurgeryItems,
  exportSurgeryItems,
  importSurgeryItems,
  updateSurgTotal,
  clearSurgeryChecks,
  printSurgeryList,
  searchTrials,
  exportTrialsCSV,
  printTrialsList
});

// ── Init ──
function initInpCalc(){
  _inpInited = true;
  const groups = {};
  INP_REGIMENS.forEach(r=>{
    if(!groups[r.group]) groups[r.group]=[];
    groups[r.group].push(r);
  });
  let html = '';
  Object.keys(groups).forEach(g=>{
    html += `<div style="margin-bottom:.8rem">
      <div style="font-size:.7rem;font-weight:700;text-transform:uppercase;letter-spacing:.06em;color:var(--text-faint);margin-bottom:.35rem">${g}</div>
      <div style="display:flex;gap:.4rem;flex-wrap:wrap">`;
    groups[g].forEach(r=>{
      html += `<button class="cond-btn inp-reg-btn" data-id="${r.id}" onclick="selectInpRegimen('${r.id}')" title="${r.desc}">${r.name}</button>`;
    });
    html += '</div></div>';
  });
  document.getElementById('inpRegimenPicker').innerHTML = html;
  updateInpPatient(false);
}
