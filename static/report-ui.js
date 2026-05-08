const tickerInput = document.getElementById('ticker-filter');
const actionSelect = document.getElementById('action-filter');
const typeSelect = document.getElementById('type-filter');
const rows = Array.from(document.querySelectorAll('#decision-table tbody tr'));
const riskHistoryFilter = document.getElementById('risk-history-filter');
const riskHistoryTypeFilter = document.getElementById('risk-history-type-filter');
const riskRows = Array.from(document.querySelectorAll('#risk-history-table tbody tr'));

if (typeSelect) {
  const types = [...new Set(rows.map((r) => r.dataset.type).filter(Boolean))].sort();
  types.forEach((t) => {
    const opt = document.createElement('option');
    opt.value = t;
    opt.textContent = t;
    typeSelect.appendChild(opt);
  });
}

function applyDecisionFilter() {
  const tickerNeedle = (tickerInput.value || '').toLowerCase().trim();
  const actionNeedle = actionSelect.value || '';
  const typeNeedle = typeSelect.value || '';
  rows.forEach((row) => {
    const ticker = (row.dataset.ticker || '').toLowerCase();
    const action = row.dataset.action || '';
    const type = row.dataset.type || '';
    const matchesTicker = !tickerNeedle || ticker.includes(tickerNeedle);
    const matchesAction = !actionNeedle || action === actionNeedle;
    const matchesType = !typeNeedle || type === typeNeedle;
    row.style.display = matchesTicker && matchesAction && matchesType ? '' : 'none';
  });
}

if (tickerInput) tickerInput.addEventListener('input', applyDecisionFilter);
if (actionSelect) actionSelect.addEventListener('change', applyDecisionFilter);
if (typeSelect) typeSelect.addEventListener('change', applyDecisionFilter);

function applyRiskHistoryFilter() {
  if (!riskHistoryFilter || !riskHistoryTypeFilter) return;
  const qualityNeedle = riskHistoryFilter.value || '';
  const typeNeedle = riskHistoryTypeFilter.value || '';
  riskRows.forEach((row) => {
    const typeCell = row.children[1];
    const qualityCell = row.children[5];
    const type = (typeCell.textContent || '').trim();
    const quality = (qualityCell.textContent || '').trim();
    const matchesQuality = !qualityNeedle || quality === qualityNeedle;
    const matchesType = !typeNeedle || type === typeNeedle;
    row.style.display = matchesQuality && matchesType ? '' : 'none';
  });
}

if (riskHistoryFilter) riskHistoryFilter.addEventListener('change', applyRiskHistoryFilter);
if (riskHistoryTypeFilter) riskHistoryTypeFilter.addEventListener('change', applyRiskHistoryFilter);

let sortState = { col: null, dir: 'asc' };

function sortRows(col) {
  sortState.dir = sortState.col === col && sortState.dir === 'asc' ? 'desc' : 'asc';
  sortState.col = col;
  const tbody = document.querySelector('#decision-table tbody');
  const sorted = [...rows].sort((a, b) => {
    const av = parseFloat(a.dataset[col] || 0);
    const bv = parseFloat(b.dataset[col] || 0);
    return sortState.dir === 'asc' ? av - bv : bv - av;
  });
  sorted.forEach((r) => tbody.appendChild(r));
  document.querySelectorAll('#decision-table th.sortable').forEach((th) => {
    th.dataset.dir = th.dataset.sort === col ? sortState.dir : '';
  });
  applyDecisionFilter();
}

document.querySelectorAll('#decision-table th.sortable').forEach((th) => {
  th.addEventListener('click', () => sortRows(th.dataset.sort));
});

const copySizingBtn = document.getElementById('copy-sizing');
if (copySizingBtn) {
  copySizingBtn.addEventListener('click', () => {
    const table = document.getElementById('sizing-table');
    if (!table) return;
    const headers = Array.from(table.querySelectorAll('thead th')).map((th) => th.textContent.trim());
    const dataRows = Array.from(table.querySelectorAll('tbody tr')).map((r) =>
      Array.from(r.querySelectorAll('td')).map((td) => td.textContent.trim()).join('\t')
    );
    navigator.clipboard.writeText([headers.join('\t'), ...dataRows].join('\r\n')).then(() => {
      copySizingBtn.textContent = '✓ Copiado';
      setTimeout(() => { copySizingBtn.textContent = 'Copiar'; }, 2000);
    });
  });
}

const toggleTechBtn = document.getElementById('toggle-tech-cols');
if (toggleTechBtn) {
  toggleTechBtn.addEventListener('click', () => {
    const table = document.querySelector('.technical-table');
    if (!table) return;
    const expanded = table.classList.toggle('show-secondary');
    toggleTechBtn.textContent = expanded ? 'Ocultar columnas secundarias' : 'Mostrar más columnas';
  });
}

// View navigation
const viewButtons = Array.from(document.querySelectorAll('[data-view-nav] [data-target-view]'));
const viewSections = Array.from(document.querySelectorAll('.report-view[data-view]'));

function activateView(viewName) {
  const isAll = viewName === 'all';
  document.body.classList.toggle('view-all', isAll);
  viewSections.forEach((section) => {
    section.classList.toggle('is-active', !isAll && section.dataset.view === viewName);
  });
  viewButtons.forEach((btn) => {
    btn.classList.toggle('active', btn.dataset.targetView === viewName);
  });
  const hashTarget = isAll ? 'all' : viewName;
  history.replaceState(null, '', '#' + hashTarget);
}

function activateViewFromHash() {
  const hash = window.location.hash.replace('#', '');
  const validViews = viewSections.map((s) => s.dataset.view).concat(['all']);
  const target = validViews.includes(hash) ? hash : 'dashboard';
  activateView(target);
}

viewButtons.forEach((btn) => {
  btn.addEventListener('click', () => activateView(btn.dataset.targetView));
});

window.addEventListener('hashchange', activateViewFromHash);
activateViewFromHash();

function updateQuickNavOverflow() {
  const quickNav = document.querySelector('.quick-nav');
  if (!quickNav) return;
  const overflow = quickNav.scrollWidth - quickNav.clientWidth > 4;
  quickNav.classList.toggle('is-scrollable', overflow);
  quickNav.classList.toggle('has-overflow-left', quickNav.scrollLeft > 4);
  quickNav.classList.toggle('has-overflow-right', quickNav.scrollLeft + quickNav.clientWidth < quickNav.scrollWidth - 4);
}

const quickNav = document.querySelector('.quick-nav');
if (quickNav) {
  quickNav.addEventListener('scroll', updateQuickNavOverflow, { passive: true });
  window.addEventListener('resize', updateQuickNavOverflow);
  updateQuickNavOverflow();
}

const csvDownloadBtn = document.querySelector('[data-csv-download]');
if (csvDownloadBtn) {
  const decodeHtmlEntities = (input) => {
    const textarea = document.createElement('textarea');
    textarea.innerHTML = input;
    return textarea.value;
  };
  csvDownloadBtn.addEventListener('click', () => {
    const filename = csvDownloadBtn.dataset.csvDownload || 'cartera.csv';
    const csvEl = document.getElementById('report-csv-data');
    if (!csvEl) return;
    const csvText = decodeHtmlEntities(csvEl.textContent || '');
    const blob = new Blob([csvText], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  });
}

document.querySelectorAll('details').forEach((det) => {
  const summary = det.querySelector('summary');
  if (!summary) return;
  const slug = summary.textContent.trim().toLowerCase()
    .replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, '').slice(0, 60);
  const key = 'det-' + slug;
  const saved = localStorage.getItem(key);
  if (saved === 'open') det.open = true;
  else if (saved === 'closed') det.open = false;
  det.addEventListener('toggle', () => {
    localStorage.setItem(key, det.open ? 'open' : 'closed');
  });
});

