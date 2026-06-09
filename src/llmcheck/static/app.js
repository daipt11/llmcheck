/* ════════════════════════════════════════════════════════════════
   llmcheck Web UI — app.js
   Handles: Model CRUD, real-time SSE check, filters, modals, toasts
   ════════════════════════════════════════════════════════════════ */

'use strict';

// ── Constants ─────────────────────────────────────────────────────────────────

const AVAILABLE_TAGS = [
  { key: 'reasoning', label: 'Reasoning', desc: 'Suy luận mạnh' },
  { key: 'general',   label: 'General',   desc: 'Đa năng' },
  { key: 'coding',    label: 'Coding',    desc: 'Lập trình / Code' },
  { key: 'agent',     label: 'Agent',     desc: 'Agent, Tool-use, Search' },
  { key: 'fast',      label: 'Fast',      desc: 'Tốc độ cao' },
  { key: 'lite',      label: 'Lite',      desc: 'Nhẹ, tiết kiệm' },
  { key: 'vision',    label: 'Vision',    desc: 'Xử lý hình ảnh' },
  { key: 'large',     label: 'Large',     desc: 'Model lớn, mạnh' },
];

// ── State ─────────────────────────────────────────────────────────────────────

let allModels   = [];           // full model list from API
let checkStatus = {};           // { [id]: { status, latency, error } }
let selectedTags = new Set();   // tags chosen in the modal
let customTags   = new Set();   // user-defined custom tags in the modal
let activeCheckSource = null;   // current SSE EventSource
let sortState    = 'none';      // 'none', 'asc', 'desc'

// ── DOM helpers ───────────────────────────────────────────────────────────────

const $  = id => document.getElementById(id);
const el = (tag, cls, text) => {
  const e = document.createElement(tag);
  if (cls)  e.className   = cls;
  if (text) e.textContent = text;
  return e;
};

// ── Toast ─────────────────────────────────────────────────────────────────────

function showToast(message, type = 'info', duration = 3500) {
  const container = $('toast-container');
  const toast = el('div', `toast toast-${type}`);
  const iconName  = { success: 'check_circle', error: 'error', info: 'info' }[type] || 'info';
  toast.innerHTML = `<span class="material-symbols-outlined">${iconName}</span><span style="margin-left:8px;">${message}</span>`;
  container.appendChild(toast);
  setTimeout(() => {
    toast.classList.add('toast-out');
    toast.addEventListener('animationend', () => toast.remove(), { once: true });
  }, duration);
}

// ── API helpers ───────────────────────────────────────────────────────────────

async function apiFetch(path, options = {}) {
  const res = await fetch(path, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

// ── Render ────────────────────────────────────────────────────────────────────

function renderTags(tagsStr) {
  if (!tagsStr) return '';
  return tagsStr.split(',')
    .map(t => t.trim()).filter(Boolean)
    .map(t => `<span class="tag">${t}</span>`)
    .join('');
}

function renderStatusCell(model) {
  const cs = checkStatus[model._id];
  if (!cs) {
    return `<span class="status-badge status-idle"><span class="material-symbols-outlined" style="font-size:14px;">remove</span></span>`;
  }
  if (cs.status === 'checking') {
    return `<span class="status-badge status-checking"><span class="material-symbols-outlined spinning" style="font-size:14px;">sync</span></span>`;
  }
  if (cs.status === 'ok') {
    return `<span class="status-badge status-ok"><span class="material-symbols-outlined" style="font-size:14px;">check</span> ok</span>`;
  }
  // error
  const errShort = (cs.error || 'Error').replace(/"/g, '&quot;');
  return `<span class="status-badge status-error error-tooltip" data-error="${errShort}"><span class="material-symbols-outlined" style="font-size:14px;">close</span> err</span>`;
}

function renderLatencyCell(model) {
  const cs = checkStatus[model._id];
  if (!cs || cs.status !== 'ok') return `<span class="cell-latency">–</span>`;
  return `<span class="cell-latency">${cs.latency}s</span>`;
}

function buildRow(model) {
  const tr = document.createElement('tr');
  tr.dataset.id = model._id;

  tr.innerHTML = `
    <td><span class="cell-id">#${model._id}</span></td>
    <td><span class="cell-name">${escHtml(model.name || '')}</span></td>
    <td>${renderTags(model.tags)}</td>
    <td><span class="cell-supplier">${escHtml(model.supplier || '–')}</span></td>
    <td class="cell-status-${model._id}">${renderStatusCell(model)}</td>
    <td class="cell-latency-${model._id}">${renderLatencyCell(model)}</td>
    <td>
      <div class="row-actions">
        <button class="action-btn check" title="Check this model" onclick="checkOne('${model._id}')"><span class="material-symbols-outlined" style="font-size:16px;">search</span></button>
        <button class="action-btn" title="Edit model" onclick="openEditModal('${model._id}')"><span class="material-symbols-outlined" style="font-size:16px;">edit</span></button>
        <button class="action-btn danger" title="Delete model" onclick="confirmDelete('${model._id}', '${escHtml(model.name || '')}')"><span class="material-symbols-outlined" style="font-size:16px;">delete</span></button>
      </div>
    </td>
  `;
  return tr;
}

function escHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function renderTable(models) {
  const tbody   = $('models-tbody');
  const table   = $('models-table');
  const loading = $('table-loading');
  const empty   = $('empty-state');
  const stats   = $('stats-bar');

  loading.style.display = 'none';

  if (!models.length) {
    table.style.display = 'none';
    empty.style.display = 'block';
    stats.style.display = 'none';
    return;
  }

  empty.style.display = 'none';
  table.style.display = 'table';
  stats.style.display = 'flex';

  tbody.innerHTML = '';
  
  let displayModels = [...models];
  if (sortState === 'asc') {
    displayModels.sort((a, b) => (a.name || '').localeCompare(b.name || ''));
  } else if (sortState === 'desc') {
    displayModels.sort((a, b) => (b.name || '').localeCompare(a.name || ''));
  }

  displayModels.forEach(m => tbody.appendChild(buildRow(m)));
  updateStats(models);
}

function updateStats(models) {
  $('stat-total').textContent = `${models.length} models`;
  const checked = Object.values(checkStatus);
  const ok      = checked.filter(c => c.status === 'ok').length;
  const err     = checked.filter(c => c.status === 'error').length;
  $('stat-ok').innerHTML      = ok  ? `<span class="material-symbols-outlined" style="font-size:14px;vertical-align:bottom;">check</span> ${ok} online`  : '';
  $('stat-error').innerHTML   = err ? `<span class="material-symbols-outlined" style="font-size:14px;vertical-align:bottom;">close</span> ${err} offline` : '';
}

// Update only status & latency cells without re-rendering whole table
function patchRowStatus(modelId) {
  const statusCell  = document.querySelector(`.cell-status-${modelId}`);
  const latencyCell = document.querySelector(`.cell-latency-${modelId}`);
  const model = allModels.find(m => m._id === modelId);
  if (statusCell && model)  statusCell.innerHTML  = renderStatusCell(model);
  if (latencyCell && model) latencyCell.innerHTML = renderLatencyCell(model);
}

// ── Load models ───────────────────────────────────────────────────────────────

async function loadModels(params = {}) {
  $('table-loading').style.display = 'flex';
  $('models-table').style.display  = 'none';
  $('empty-state').style.display   = 'none';

  const qs = new URLSearchParams(params).toString();
  try {
    allModels = await apiFetch(`/api/models${qs ? '?' + qs : ''}`);
    renderTable(allModels);
  } catch (e) {
    showToast(`Failed to load models: ${e.message}`, 'error');
    $('table-loading').style.display = 'none';
  }
}

// ── Filters ───────────────────────────────────────────────────────────────────

$('btn-apply-filter').addEventListener('click', () => {
  const params = {};
  const s = $('filter-supplier').value.trim();
  const t = $('filter-tag').value.trim();
  if (s) params.supplier = s;
  if (t) params.tag = t;
  loadModels(params);
});

$('btn-clear-filter').addEventListener('click', () => {
  $('filter-supplier').value = '';
  $('filter-tag').value      = '';
  loadModels();
});

// Allow pressing Enter in filter inputs
['filter-supplier', 'filter-tag'].forEach(id => {
  $(id).addEventListener('keydown', e => {
    if (e.key === 'Enter') $('btn-apply-filter').click();
  });
});

// Sort by Name
$('sort-name').addEventListener('click', () => {
  if (sortState === 'none') sortState = 'asc';
  else if (sortState === 'asc') sortState = 'desc';
  else sortState = 'none';
  
  const icon = $('sort-name-icon');
  if (sortState === 'asc') icon.textContent = 'arrow_upward';
  else if (sortState === 'desc') icon.textContent = 'arrow_downward';
  else icon.textContent = 'unfold_more';
  
  renderTable(allModels);
});

// ── Check (SSE) ───────────────────────────────────────────────────────────────

function startSSECheck(url, modelIds) {
  // Cancel any ongoing check
  if (activeCheckSource) {
    activeCheckSource.close();
    activeCheckSource = null;
  }

  // Set all target models to "checking"
  modelIds.forEach(id => {
    checkStatus[id] = { status: 'checking', latency: null, error: null };
    patchRowStatus(id);
  });

  const src = new EventSource(url);
  activeCheckSource = src;

  src.onmessage = (evt) => {
    const data = JSON.parse(evt.data);
    if (data.done) {
      src.close();
      activeCheckSource = null;
      $('btn-check-all').disabled = false;
      $('btn-check-all').innerHTML = '<span class="btn-icon material-symbols-outlined">search</span> Check All';
      updateStats(allModels);
      return;
    }

    checkStatus[data.id] = {
      status:  data.status,
      latency: data.latency,
      error:   data.error,
    };
    patchRowStatus(data.id);
    updateStats(allModels);
  };

  src.onerror = () => {
    src.close();
    activeCheckSource = null;
    $('btn-check-all').disabled = false;
    $('btn-check-all').innerHTML = '<span class="btn-icon material-symbols-outlined">search</span> Check All';
    showToast('Connection error during check', 'error');
  };
}

$('btn-check-all').addEventListener('click', () => {
  if (!allModels.length) { showToast('No models to check', 'info'); return; }
  $('btn-check-all').disabled = true;
  $('btn-check-all').innerHTML = '<span class="btn-icon material-symbols-outlined spinning">sync</span> Checking…';
  startSSECheck('/api/check', allModels.map(m => m._id));
});

function checkOne(modelId) {
  startSSECheck(`/api/check/${modelId}`, [modelId]);
}

// ── Modal helpers ─────────────────────────────────────────────────────────────

function openModal() {
  const overlay = $('modal-overlay');
  overlay.style.display = 'flex';
  requestAnimationFrame(() => $('form-name').focus());
}

function closeModal() {
  $('modal-overlay').style.display = 'none';
  resetForm();
}

function resetForm() {
  $('model-form').reset();
  $('form-model-id').value = '';
  $('form-error').style.display = 'none';
  selectedTags.clear();
  customTags.clear();
  renderTagOptions();
}

// ── Tag selector in modal ─────────────────────────────────────────────────────

function renderTagOptions() {
  const container = $('tags-container');
  container.innerHTML = '';

  AVAILABLE_TAGS.forEach(t => {
    const chip = el('span', `tag-option ${selectedTags.has(t.key) ? 'selected' : ''}`, t.key);
    chip.title = t.desc;
    chip.addEventListener('click', () => {
      if (selectedTags.has(t.key)) selectedTags.delete(t.key);
      else                          selectedTags.add(t.key);
      chip.classList.toggle('selected');
    });
    container.appendChild(chip);
  });

  customTags.forEach(tag => {
    const chip = el('span', 'tag-option custom selected', tag);
    const rm   = el('span', 'tag-remove material-symbols-outlined', 'close');
    rm.style.fontSize = '12px';
    rm.addEventListener('click', (e) => {
      e.stopPropagation();
      customTags.delete(tag);
      selectedTags.delete(tag);
      renderTagOptions();
    });
    chip.appendChild(rm);
    container.appendChild(chip);
  });
}

$('btn-add-custom-tag').addEventListener('click', () => {
  const input = $('custom-tag-input');
  const tag   = input.value.trim().toLowerCase();
  if (tag && !AVAILABLE_TAGS.find(t => t.key === tag)) {
    customTags.add(tag);
    selectedTags.add(tag);
    renderTagOptions();
  }
  input.value = '';
});

$('custom-tag-input').addEventListener('keydown', e => {
  if (e.key === 'Enter') { e.preventDefault(); $('btn-add-custom-tag').click(); }
});

// ── API key visibility toggle ─────────────────────────────────────────────────

$('toggle-api-key').addEventListener('click', () => {
  const input = $('form-api-key');
  const isPass = input.type === 'password';
  input.type = isPass ? 'text' : 'password';
  $('toggle-api-key').textContent = isPass ? 'visibility_off' : 'visibility';
});

$('copy-api-key').addEventListener('click', async () => {
  const input = $('form-api-key');
  if (!input.value) return;
  try {
    await navigator.clipboard.writeText(input.value);
    showToast('API Key copied to clipboard', 'success');
  } catch (err) {
    showToast('Failed to copy API key', 'error');
  }
});

['copy-provider', 'copy-model', 'copy-base-url'].forEach(btnId => {
  const btn = $(btnId);
  if (btn) {
    btn.addEventListener('click', async () => {
      const inputId = btnId.replace('copy-', 'form-');
      const input = $(inputId);
      if (!input || !input.value) return;
      try {
        await navigator.clipboard.writeText(input.value);
        showToast('Copied to clipboard', 'success');
      } catch (err) {
        showToast('Failed to copy', 'error');
      }
    });
  }
});

// ── Add Model ─────────────────────────────────────────────────────────────────

function openAddModal() {
  $('modal-title').textContent = 'Add Model';
  resetForm();
  renderTagOptions();
  openModal();
}

$('btn-add-model').addEventListener('click', openAddModal);

// ── Edit Model ────────────────────────────────────────────────────────────────

async function openEditModal(modelId) {
  $('modal-title').textContent = 'Edit Model';
  resetForm();

  try {
    const model = await apiFetch(`/api/models/${modelId}`);
    $('form-model-id').value  = model._id;
    $('form-name').value      = model.name      || '';
    $('form-supplier').value  = model.supplier  || '';
    $('form-provider').value  = model.provider  || '';
    $('form-model').value     = model.model     || '';
    $('form-base-url').value  = model.base_url  || '';
    $('form-api-key').value   = model.api_key   || '';

    // Restore tags
    const existing = (model.tags || '').split(',').map(t => t.trim()).filter(Boolean);
    existing.forEach(t => {
      selectedTags.add(t);
      if (!AVAILABLE_TAGS.find(at => at.key === t)) customTags.add(t);
    });

    renderTagOptions();
    openModal();
  } catch (e) {
    showToast(`Failed to load model: ${e.message}`, 'error');
  }
}

// ── Delete Model ──────────────────────────────────────────────────────────────

let pendingDeleteId = null;

function confirmDelete(modelId, name) {
  pendingDeleteId = modelId;
  $('confirm-message').textContent = `Are you sure you want to delete "${name}"? This cannot be undone.`;
  $('confirm-overlay').style.display = 'flex';
}

$('btn-confirm-cancel').addEventListener('click', () => {
  pendingDeleteId = null;
  $('confirm-overlay').style.display = 'none';
});

$('btn-confirm-delete').addEventListener('click', async () => {
  if (!pendingDeleteId) return;
  try {
    await apiFetch(`/api/models/${pendingDeleteId}`, { method: 'DELETE' });
    delete checkStatus[pendingDeleteId];
    showToast('Model deleted', 'success');
    loadModels();
  } catch (e) {
    showToast(`Delete failed: ${e.message}`, 'error');
  }
  pendingDeleteId = null;
  $('confirm-overlay').style.display = 'none';
});

// ── Save (Add or Edit) ────────────────────────────────────────────────────────

$('model-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  $('form-error').style.display = 'none';

  const modelId   = $('form-model-id').value;
  const name      = $('form-name').value.trim();
  const supplier  = $('form-supplier').value.trim();
  const provider  = $('form-provider').value.trim();
  const modelName = $('form-model').value.trim();
  const apiKey    = $('form-api-key').value.trim();
  const baseUrl   = $('form-base-url').value.trim();
  const tags      = [...selectedTags].sort().join(',');

  if (!name || !provider || !modelName) {
    const errEl = $('form-error');
    errEl.textContent = 'Name, Provider, and Model Name are required.';
    errEl.style.display = 'block';
    return;
  }

  const payload = { name, provider, model: modelName, api_key: apiKey, base_url: baseUrl, supplier, tags };
  const saveBtn = $('btn-save');
  saveBtn.disabled = true;
  saveBtn.textContent = 'Saving…';

  try {
    if (modelId) {
      await apiFetch(`/api/models/${modelId}`, { method: 'PUT', body: JSON.stringify(payload) });
      showToast('Model updated', 'success');
    } else {
      await apiFetch('/api/models', { method: 'POST', body: JSON.stringify(payload) });
      showToast('Model added', 'success');
    }
    closeModal();
    loadModels();
  } catch (err) {
    const errEl = $('form-error');
    errEl.textContent = err.message;
    errEl.style.display = 'block';
  } finally {
    saveBtn.disabled = false;
    saveBtn.textContent = 'Save';
  }
});

// ── Modal close handlers ──────────────────────────────────────────────────────

$('modal-close').addEventListener('click', closeModal);
$('btn-cancel').addEventListener('click', closeModal);

$('modal-overlay').addEventListener('click', (e) => {
  if (e.target === $('modal-overlay')) closeModal();
});

document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    if ($('modal-overlay').style.display !== 'none')   closeModal();
    if ($('confirm-overlay').style.display !== 'none') {
      pendingDeleteId = null;
      $('confirm-overlay').style.display = 'none';
    }
  }
});

// ── Init ──────────────────────────────────────────────────────────────────────

loadModels();
