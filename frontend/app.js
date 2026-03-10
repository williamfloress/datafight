/**
 * DATAFIGHT Frontend - Pipeline en memoria: un botón analiza y muestra predicciones
 */

const PELEAS_GRID = document.getElementById('peleasGrid');
const EVENTO_NOMBRE = document.getElementById('eventoNombre');
const EVENTO_FECHA = document.getElementById('eventoFecha');
const EVENTO_LINK = document.getElementById('eventoLink');
const EVENTO_LINK_WRAPPER = document.getElementById('eventoLinkWrapper');
const ERROR_MESSAGE = document.getElementById('errorMessage');
const LOADING = document.getElementById('loading');
const BTN_ANALIZAR = document.getElementById('btnAnalizar');
const BTN_LIMPIAR = document.getElementById('btnLimpiar');

const API_BASE = window.location.origin;
const STORAGE_KEY = 'datafight_predicciones';

function escapeHtml(text) {
  if (!text) return '';
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

function formatProbabilidad(value) {
  if (typeof value !== 'number') return '—';
  return `${Math.round(value * 100)}%`;
}

function formatStat(value) {
  if (value == null) return '—';
  if (typeof value === 'number') return value % 1 === 0 ? value : value.toFixed(2);
  return String(value);
}

function renderUltimasPeleas(arr) {
  if (!arr || arr.length === 0) return '—';
  return arr.map(r => {
    const cls = r === 'W' ? 'racha-win' : r === 'L' ? 'racha-loss' : 'racha-draw';
    return `<span class="racha-badge ${cls}">${escapeHtml(r)}</span>`;
  }).join(' ');
}

function renderFisicoComparativo(p1, p2) {
  const s1 = p1.estadisticas || {};
  const s2 = p2.estadisticas || {};
  const attrs = [
    { label: 'Estatura', p1: s1.height, p2: s2.height },
    { label: 'Peso', p1: s1.weight, p2: s2.weight },
    { label: 'Alcance', p1: s1.reach, p2: s2.reach },
    { label: 'Edad', p1: p1.edad, p2: p2.edad },
    { label: 'Postura', p1: s1.stance, p2: s2.stance },
  ];
  let html = attrs.map(({ label, p1: v1, p2: v2 }) => {
    const val1 = v1 != null && v1 !== '' ? escapeHtml(String(v1)) : '—';
    const val2 = v2 != null && v2 !== '' ? escapeHtml(String(v2)) : '—';
    return `
    <div class="stat-row">
      <span class="stat-val stat-p1">${val1}</span>
      <span class="stat-label">${escapeHtml(label)}</span>
      <span class="stat-val stat-p2">${val2}</span>
    </div>`;
  }).join('');

  html += `
    <div class="stat-row">
      <span class="stat-val stat-p1">${renderUltimasPeleas(p1.ultimas_peleas)}</span>
      <span class="stat-label">Racha</span>
      <span class="stat-val stat-p2">${renderUltimasPeleas(p2.ultimas_peleas)}</span>
    </div>`;

  return html;
}

function renderStatsComparativo(p1, p2) {
  const s1 = p1.estadisticas || {};
  const s2 = p2.estadisticas || {};
  const str1 = s1.striking || {};
  const str2 = s2.striking || {};
  const gr1 = s1.grappling || {};
  const gr2 = s2.grappling || {};

  const stats = [
    { label: 'SLpM', p1: str1.slpm, p2: str2.slpm },
    { label: 'SApM', p1: str1.sapm, p2: str2.sapm },
    { label: 'Str. Acc.', p1: str1.str_acc, p2: str2.str_acc },
    { label: 'Str. Def.', p1: str1.str_def, p2: str2.str_def },
    { label: 'TD Avg.', p1: gr1.td_avg, p2: gr2.td_avg },
    { label: 'TD Def.', p1: gr1.td_def, p2: gr2.td_def },
  ];

  return stats.map(({ label, p1: v1, p2: v2 }) => `
    <div class="stat-row">
      <span class="stat-val stat-p1">${formatStat(v1)}</span>
      <span class="stat-label">${escapeHtml(label)}</span>
      <span class="stat-val stat-p2">${formatStat(v2)}</span>
    </div>
  `).join('');
}

function renderPelea(pelea, index) {
  const p1 = pelea.peleador_1;
  const p2 = pelea.peleador_2;
  const prob1 = p1.probabilidad_victoria ?? 0;
  const prob2 = p2.probabilidad_victoria ?? 0;
  const favorito1 = prob1 >= prob2;

  const p1Nombre = escapeHtml(p1.nombre);
  const p2Nombre = escapeHtml(p2.nombre);
  const p1Record = escapeHtml(p1.record || '—');
  const p2Record = escapeHtml(p2.record || '—');
  const weightClass = escapeHtml(pelea.weight_class || '');

  return `
    <article class="pelea-card" data-index="${index}">
      <div class="pelea-card__header">${weightClass}</div>
      <div class="pelea-card__body">
        <div class="peleador ${favorito1 ? 'peleador--favorito' : ''}">
          <span class="peleador__nombre">
            <a href="${escapeHtml(p1.perfil || '#')}" target="_blank" rel="noopener">${p1Nombre}</a>
          </span>
          <span class="peleador__record">${p1Record}</span>
          <span class="peleador__prob">${formatProbabilidad(prob1)}</span>
          ${favorito1 ? '<span class="peleador__badge">Favorito</span>' : ''}
        </div>
        <span class="pelea-vs">VS</span>
        <div class="peleador ${!favorito1 ? 'peleador--favorito' : ''}">
          <span class="peleador__nombre">
            <a href="${escapeHtml(p2.perfil || '#')}" target="_blank" rel="noopener">${p2Nombre}</a>
          </span>
          <span class="peleador__record">${p2Record}</span>
          <span class="peleador__prob">${formatProbabilidad(prob2)}</span>
          ${!favorito1 ? '<span class="peleador__badge">Favorito</span>' : ''}
        </div>
      </div>
      <div class="pelea-card__body">
        <div class="prob-bar">
          <div class="prob-bar__segment prob-bar__segment--${favorito1 ? 'favorito' : 'otro'}" style="width: ${prob1 * 100}%"></div>
          <div class="prob-bar__segment prob-bar__segment--${!favorito1 ? 'favorito' : 'otro'}" style="width: ${prob2 * 100}%"></div>
        </div>
      </div>
      <div class="pelea-card__stats">
        <div class="stats-header">
          <span class="stats-p1">${escapeHtml(p1.nombre)}</span>
          <span class="stats-label">Atributos físicos</span>
          <span class="stats-p2">${escapeHtml(p2.nombre)}</span>
        </div>
        ${renderFisicoComparativo(p1, p2)}
        <div class="stats-header stats-header--mt">
          <span class="stats-p1">${escapeHtml(p1.nombre)}</span>
          <span class="stats-label">Estadísticas <button type="button" class="stats-help-btn" title="Ver glosario de estadísticas" aria-label="Ayuda">?</button></span>
          <span class="stats-p2">${escapeHtml(p2.nombre)}</span>
        </div>
        ${renderStatsComparativo(p1, p2)}
      </div>
    </article>
  `;
}

function renderEvento(evento) {
  if (!evento) return;
  EVENTO_NOMBRE.textContent = evento.nombre || 'Evento UFC';
  EVENTO_FECHA.textContent = evento.fecha || '';
  if (evento.url_detalles) {
    EVENTO_LINK.href = evento.url_detalles;
    EVENTO_LINK_WRAPPER.hidden = false;
  } else {
    EVENTO_LINK_WRAPPER.hidden = true;
  }
}

function showError(msg) {
  LOADING.hidden = true;
  PELEAS_GRID.hidden = true;
  ERROR_MESSAGE.hidden = false;
  const hint = ERROR_MESSAGE.querySelector('.error-hint');
  if (hint) hint.textContent = msg || 'El análisis toma entre 2 y 5 minutos.';
}

function showContent(data) {
  LOADING.hidden = true;
  ERROR_MESSAGE.hidden = true;
  PELEAS_GRID.hidden = false;

  renderEvento(data.evento);

  const peleas = data.peleas || [];
  PELEAS_GRID.innerHTML = peleas.map((pelea, i) => renderPelea(pelea, i)).join('');

  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
  } catch (_) {}
}

async function limpiarAnalisis() {
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch (_) {}
  try {
    await fetch(`${API_BASE}/api/limpiar`, { method: 'POST' });
  } catch (_) {}
  EVENTO_NOMBRE.textContent = 'Descubre las probabilidades del próximo evento UFC';
  EVENTO_FECHA.textContent = '';
  EVENTO_LINK.href = '#';
  EVENTO_LINK_WRAPPER.hidden = true;
  PELEAS_GRID.innerHTML = '';
  PELEAS_GRID.hidden = true;
  showError();
}

function formatTiempoRestante(segundos) {
  const m = Math.floor(segundos / 60);
  const s = Math.floor(segundos % 60);
  return m > 0 ? `${m} min ${s} s` : `${s} s`;
}

async function analizarProximoEvento() {
  const actionsEl = document.querySelector('.actions');
  if (actionsEl) actionsEl.hidden = true;
  ERROR_MESSAGE.hidden = true;
  LOADING.hidden = false;
  LOADING.querySelector('p').textContent = 'Analizando el próximo evento... Esto puede tardar 2-5 minutos.';
  try {
    const res = await fetch(`${API_BASE}/api/actualizar`, { method: 'POST' });
    const data = await res.json();

    if (res.status === 429) {
      if (actionsEl) actionsEl.hidden = false;
      alert(data.message || 'Por favor espera unos minutos antes de solicitar un nuevo análisis.');
      return;
    }

    if (data.ok && data.predicciones) {
      showContent(data.predicciones);
    } else {
      if (actionsEl) actionsEl.hidden = false;
      alert('Error: ' + (data.error || data.message || 'No se pudo completar el análisis. Intenta de nuevo.'));
    }
  } catch (err) {
    if (actionsEl) actionsEl.hidden = false;
    alert('Error de conexión: ' + err.message);
  } finally {
    LOADING.hidden = true;
    if (actionsEl) actionsEl.hidden = false;
  }
}

async function loadPredicciones() {
  try {
    const cached = localStorage.getItem(STORAGE_KEY);
    if (cached) {
      const data = JSON.parse(cached);
      if (data.peleas && data.peleas.length > 0) {
        showContent(data);
        return;
      }
    }
  } catch (_) {}

  try {
    const res = await fetch(`${API_BASE}/api/predicciones`);
    const data = await res.json().catch(() => ({}));
    if (data.peleas && data.peleas.length > 0) {
      showContent(data);
      return;
    }
  } catch (_) {}

  showError();
}

function initStatsHelp() {
  const modal = document.getElementById('statsHelpModal');
  const backdrop = modal?.querySelector('.stats-help-modal__backdrop');
  const closeBtn = modal?.querySelector('.stats-help-modal__close');

  function openModal() {
    if (!modal) return;
    modal.hidden = false;
    modal.setAttribute('aria-hidden', 'false');
  }

  function closeModal() {
    if (!modal) return;
    modal.hidden = true;
    modal.setAttribute('aria-hidden', 'true');
  }

  PELEAS_GRID.addEventListener('click', (e) => {
    if (e.target.closest('.stats-help-btn')) openModal();
  });
  backdrop?.addEventListener('click', closeModal);
  closeBtn?.addEventListener('click', closeModal);
}

document.addEventListener('DOMContentLoaded', () => {
  loadPredicciones();
  BTN_ANALIZAR.addEventListener('click', analizarProximoEvento);
  BTN_LIMPIAR.addEventListener('click', limpiarAnalisis);
  initStatsHelp();
});
