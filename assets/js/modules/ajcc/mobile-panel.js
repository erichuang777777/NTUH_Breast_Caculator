(function () {
  const config = window.NHI_APP_CONFIG && window.NHI_APP_CONFIG.ajcc;
  if (!config) return;

  const state = { mode: 'pathological' };

  const modeMap = {
    clinical: { t: 'ajccT', n: 'ajccN', m: 'ajccM', label: 'Clinical Prognostic Stage' },
    pathological: { t: 'ajccPT', n: 'ajccPN', m: 'ajccPM', label: 'Pathologic Prognostic Stage' }
  };

  function el(id) {
    return document.getElementById(id);
  }

  function selectedIds() {
    return modeMap[state.mode] || modeMap.pathological;
  }

  function getValue(id) {
    const node = el(id);
    return node ? node.value : '';
  }

  function setValue(id, value) {
    const node = el(id);
    if (node) node.value = value;
  }

  function makeButtons(items, group, className) {
    return items.map((item) => {
      const sub = item.sub ? `<span class="sub">${item.sub}</span>` : '';
      const small = group === 'oncotype' && item.label === '?' ? ' small' : '';
      return `<button type="button" class="${className}${small}" data-group="${group}" data-value="${item.value}" data-label="${item.label}">${item.label}${sub}</button>`;
    }).join('');
  }

  function buildPanel() {
    const pageBody = document.querySelector('#ajccPage .page-body');
    if (!pageBody || document.querySelector('.ajcc-mobile-panel')) return;

    const panel = document.createElement('section');
    panel.className = 'ajcc-mobile-panel';
    panel.innerHTML = `
      <div class="ajcc-mobile-mode">
        <button type="button" class="ajcc-mobile-icon" data-action="back" aria-label="Back">C</button>
        <button type="button" data-mode="clinical">Clinical</button>
        <button type="button" data-mode="pathological" class="active">Pathological</button>
        <button type="button" class="ajcc-mobile-icon" data-action="reset" aria-label="Reset">R</button>
      </div>
      <div class="ajcc-mobile-body">
        <div class="ajcc-mobile-row ajcc-mobile-row-t">
          <div class="ajcc-mobile-row-label">T</div>
          <div class="ajcc-mobile-buttons">${makeButtons(config.tOptions, 't', 'ajcc-mobile-btn')}</div>
        </div>
        <div class="ajcc-mobile-row ajcc-mobile-row-n">
          <div class="ajcc-mobile-row-label">N</div>
          <div class="ajcc-mobile-buttons">${makeButtons(config.nOptions, 'n', 'ajcc-mobile-btn')}</div>
        </div>
        <div class="ajcc-mobile-row ajcc-mobile-row-m">
          <div class="ajcc-mobile-row-label">M</div>
          <div class="ajcc-mobile-buttons ajcc-mobile-m-buttons">${makeButtons(config.mOptions, 'm', 'ajcc-mobile-btn')}</div>
        </div>
        <div class="ajcc-mobile-pf">
          <div class="ajcc-mobile-pf-content">
            <div class="ajcc-mobile-pf-row ajcc-mobile-grade-row">
              <div class="ajcc-mobile-row-label">G</div>
              <div class="ajcc-mobile-grade-buttons">${makeButtons(config.gradeOptions, 'grade', 'ajcc-mobile-pf-btn')}</div>
            </div>
            <div class="ajcc-mobile-pf-row ajcc-mobile-marker-row">
              ${makeButtons([config.markerOptions.her2[0], config.markerOptions.er[0], config.markerOptions.pr[0]], 'marker-pos', 'ajcc-mobile-pf-btn')}
            </div>
            <div class="ajcc-mobile-pf-row ajcc-mobile-marker-row">
              ${makeButtons([config.markerOptions.her2[1], config.markerOptions.er[1], config.markerOptions.pr[1]], 'marker-neg', 'ajcc-mobile-pf-btn')}
            </div>
            <div class="ajcc-mobile-pf-row ajcc-mobile-oncotype-row">${makeButtons(config.oncotypeOptions, 'oncotype', 'ajcc-mobile-pf-btn')}</div>
          </div>
        </div>
      </div>
      <div class="ajcc-mobile-result">
        <div class="ajcc-mobile-result-cell">
          <div class="ajcc-mobile-stage" id="ajccMobileAnatomic">--</div>
          <div class="ajcc-mobile-result-label">Anatomic Stage</div>
        </div>
        <div class="ajcc-mobile-result-cell">
          <div class="ajcc-mobile-stage" id="ajccMobilePrognostic">--</div>
          <div class="ajcc-mobile-result-label" id="ajccMobilePrognosticLabel">Pathologic Prognostic Stage</div>
        </div>
      </div>
    `;
    pageBody.insertBefore(panel, pageBody.firstChild);
    bindPanel(panel);
    syncFromDesktop();
    refresh();
    updateRouteClass();
  }

  function bindPanel(panel) {
    panel.addEventListener('click', (event) => {
      const button = event.target.closest('button');
      if (!button) return;

      if (button.dataset.action === 'back') {
        if (window.showLanding) window.showLanding();
        updateRouteClass();
        return;
      }
      if (button.dataset.action === 'reset') {
        if (window.resetAJCC) window.resetAJCC();
        state.mode = 'pathological';
        setValue('ajccPM', 'M0');
        refresh();
        return;
      }
      if (button.dataset.mode) {
        state.mode = button.dataset.mode;
        const ids = selectedIds();
        if (!getValue(ids.m)) setValue(ids.m, 'M0');
        if (window.setAJCCMode) window.setAJCCMode('quick');
        refresh();
        return;
      }

      const group = button.dataset.group;
      if (!group) return;
      handleSelection(group, button.dataset.value, button.dataset.label);
      refresh();
    });
  }

  function handleSelection(group, value, label) {
    const ids = selectedIds();
    if (group === 't') setValue(ids.t, value);
    if (group === 'n') setValue(ids.n, value);
    if (group === 'm') setValue(ids.m, value);
    if (group === 'grade') setValue('ajccGrade', toggleable('ajccGrade', value));
    if (group === 'marker-pos' || group === 'marker-neg') {
      if (label && label.indexOf('HER2') === 0) setValue('ajccHER2', toggleable('ajccHER2', value));
      if (label && label.indexOf('ER') === 0) setValue('ajccER', toggleable('ajccER', value));
      if (label && label.indexOf('PR') === 0) setValue('ajccPR', toggleable('ajccPR', value));
    }
    if (group === 'oncotype') setValue('ajccOncotype', value);
    if (!getValue(ids.m)) setValue(ids.m, 'M0');
    if (window.calcAJCC) window.calcAJCC();
  }

  function toggleable(id, value) {
    return getValue(id) === value ? '' : value;
  }

  function activeValueFor(group, label) {
    const ids = selectedIds();
    if (group === 't') return getValue(ids.t);
    if (group === 'n') return getValue(ids.n);
    if (group === 'm') return getValue(ids.m);
    if (group === 'grade') return getValue('ajccGrade');
    if (group === 'oncotype') return getValue('ajccOncotype');
    if (group === 'marker-pos' || group === 'marker-neg') {
      if (label && label.indexOf('HER2') === 0) return getValue('ajccHER2');
      if (label && label.indexOf('ER') === 0) return getValue('ajccER');
      if (label && label.indexOf('PR') === 0) return getValue('ajccPR');
    }
    return '';
  }

  function syncFromDesktop() {
    const ids = selectedIds();
    if (!getValue(ids.m)) setValue(ids.m, 'M0');
  }

  function refresh() {
    syncFromDesktop();
    document.querySelectorAll('.ajcc-mobile-mode button').forEach((button) => {
      button.classList.toggle('active', button.dataset.mode === state.mode);
    });
    document.querySelectorAll('.ajcc-mobile-panel [data-group]').forEach((button) => {
      button.classList.toggle('active', button.dataset.value === activeValueFor(button.dataset.group, button.dataset.label));
    });
    const label = el('ajccMobilePrognosticLabel');
    if (label) label.textContent = selectedIds().label;
    renderResults();
  }

  function renderResults() {
    const ids = selectedIds();
    const t = getValue(ids.t);
    const n = getValue(ids.n);
    const m = getValue(ids.m);
    const anat = t && n && m && window._ajccAnatomic ? window._ajccAnatomic(t, n, m) : '';
    const anatomicEl = el('ajccMobileAnatomic');
    const prognosticEl = el('ajccMobilePrognostic');

    if (anatomicEl) anatomicEl.textContent = anat && anat !== '?' ? anat : '--';
    if (!anat || anat === '?') {
      if (prognosticEl) prognosticEl.textContent = '--';
      return;
    }

    const grade = getValue('ajccGrade');
    const er = getValue('ajccER');
    const pr = getValue('ajccPR');
    const her2 = getValue('ajccHER2');
    if (!grade || !er || !pr || !her2 || !window._ajcc9Lookup) {
      if (prognosticEl) prognosticEl.textContent = anat;
      return;
    }

    const nCalc = window._ajccNForCalc ? window._ajccNForCalc(n) : n;
    const prog = window._ajcc9Lookup(t, nCalc, m, grade, er, pr, her2);
    if (prognosticEl) prognosticEl.textContent = prog || anat;
  }

  function updateRouteClass() {
    const active = !!document.querySelector('#ajccPage.active');
    document.body.classList.toggle('ajcc-mobile-active', active);
  }

  document.addEventListener('DOMContentLoaded', () => {
    buildPanel();
    updateRouteClass();
    const observer = new MutationObserver(updateRouteClass);
    const page = document.getElementById('ajccPage');
    if (page) observer.observe(page, { attributes: true, attributeFilter: ['class'] });
  });
  window.AJCCMobilePanel = { refresh, updateRouteClass };
})();
