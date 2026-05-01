const tickerInput = document.getElementById('ticker-filter');
const actionSelect = document.getElementById('action-filter');
const typeSelect = document.getElementById('type-filter');
const rows = Array.from(document.querySelectorAll('#decision-table tbody tr'));
const riskHistoryFilter = document.getElementById('risk-history-filter');
const riskHistoryTypeFilter = document.getElementById('risk-history-type-filter');
const riskRows = Array.from(document.querySelectorAll('#risk-history-table tbody tr'));
const navLinks = Array.from(document.querySelectorAll('.quick-nav a[href^="#"]'));
const observedSections = Array.from(document.querySelectorAll('section[id]'));

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

tickerInput.addEventListener('input', applyDecisionFilter);
actionSelect.addEventListener('change', applyDecisionFilter);
typeSelect.addEventListener('change', applyDecisionFilter);

function applyRiskHistoryFilter() {
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

riskHistoryFilter.addEventListener('change', applyRiskHistoryFilter);
riskHistoryTypeFilter.addEventListener('change', applyRiskHistoryFilter);

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
      copySizingBtn.textContent = '\u2713 Copiado';
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

function setActiveNavByHash() {
  const hash = window.location.hash;
  if (!hash) return;
  navLinks.forEach((link) => {
    link.classList.toggle('active', link.getAttribute('href') === hash);
  });
}

const observer = new IntersectionObserver((entries) => {
  const visible = entries
    .filter((entry) => entry.isIntersecting)
    .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
  if (!visible) return;
  const id = `#${visible.target.id}`;
  navLinks.forEach((link) => {
    link.classList.toggle('active', link.getAttribute('href') === id);
  });
}, { threshold: [0.2, 0.45, 0.7] });

observedSections.forEach((section) => observer.observe(section));
setActiveNavByHash();
window.addEventListener('hashchange', setActiveNavByHash);

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
