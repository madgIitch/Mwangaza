/*
  MWANGAZA MOCKUP INTERACTIONS
  ----------------------------

  CODEX ADAPTATION NOTE — DATA FLOW
  1. `regions` is the mock data source.
  2. Replace it with data returned by your backend/GEE service.
  3. Preserve the shape below or add a mapper in `normaliseApiRegion()`.
  4. Call `selectRegion(regionName)` after fresh data arrives.

  The UI is deliberately framework-free so each section can be copied into a
  React component, Streamlit custom component or static prototype.
*/

const regions = {
  Somalia: {
    risk: 'red', riskLabel: 'Severe', alert: 'Severe vegetation stress',
    ndvi: '-0.38', ndviUnit: 'unitless', ndviDelta: '↓ -0.12 vs last month',
    rainfall: '-62%', rainfallUnit: 'vs baseline', rainfallDelta: '↓ -18% vs last month',
    temperature: '+2.4°C', temperatureUnit: 'vs baseline', temperatureDelta: '↑ +0.6°C vs last month',
    score: '0.86', scoreUnit: '/ 1.0', scoreDelta: '↑ 0.11 vs last month',
    quality: 'High', qualityUnit: '92% confidence', qualityDelta: '● Stable',
    exposed: '4.2M', exposedUnit: 'people', exposedDelta: '↑ 0.3M vs last month',
    ndviCurrent: [-0.42, -0.19, -0.17, -0.39, -0.34, -0.49],
    ndviBaseline: [0.02, 0.42, 0.29, 0.20, 0.10, 0.02],
    rainCurrent: [40, 145, 74, 38, -34, -70, -58, -72, -66, -76, -70],
    rainBaseline: [92, 103, 108, 116, 112, 72, 50, 44, 40, 36, 35],
    recommendations: ['Pre-position water supplies', 'Increase field monitoring', 'Prepare livestock support', 'Share alert with local partners']
  },
  'Northern Kenya': {
    mapRegion: 'Kenya', risk: 'orange', riskLabel: 'High', alert: 'Rainfall deficit',
    ndvi: '-0.21', ndviUnit: 'unitless', ndviDelta: '↓ -0.08 vs last month',
    rainfall: '-44%', rainfallUnit: 'vs baseline', rainfallDelta: '↓ -12% vs last month',
    temperature: '+1.8°C', temperatureUnit: 'vs baseline', temperatureDelta: '↑ +0.3°C vs last month',
    score: '0.69', scoreUnit: '/ 1.0', scoreDelta: '↑ 0.07 vs last month',
    quality: 'High', qualityUnit: '90% confidence', qualityDelta: '● Stable',
    exposed: '2.1M', exposedUnit: 'people', exposedDelta: '↑ 0.1M vs last month',
    ndviCurrent: [-0.25, -0.13, -0.05, -0.19, -0.14, -0.28], ndviBaseline: [0.06, 0.38, 0.31, 0.23, 0.14, 0.08],
    rainCurrent: [60, 118, 84, 54, 18, -38, -28, -46, -42, -51, -48], rainBaseline: [95, 103, 110, 115, 111, 76, 55, 50, 45, 41, 39],
    recommendations: ['Inspect priority water points', 'Target mobile field surveys', 'Protect livestock corridors', 'Brief county response teams']
  },
  Ethiopia: {
    risk: 'yellow', riskLabel: 'Watch', alert: 'Watch conditions',
    ndvi: '-0.08', ndviUnit: 'unitless', ndviDelta: '↓ -0.03 vs last month',
    rainfall: '-21%', rainfallUnit: 'vs baseline', rainfallDelta: '↓ -5% vs last month',
    temperature: '+1.1°C', temperatureUnit: 'vs baseline', temperatureDelta: '↑ +0.2°C vs last month',
    score: '0.48', scoreUnit: '/ 1.0', scoreDelta: '↑ 0.03 vs last month',
    quality: 'High', qualityUnit: '94% confidence', qualityDelta: '● Stable',
    exposed: '5.6M', exposedUnit: 'people', exposedDelta: '↑ 0.2M vs last month',
    ndviCurrent: [-0.10, 0.02, 0.10, -0.04, 0.03, -0.09], ndviBaseline: [0.08, 0.39, 0.34, 0.27, 0.18, 0.11],
    rainCurrent: [82, 127, 100, 82, 55, 10, 8, 0, 4, -5, 0], rainBaseline: [96, 104, 111, 116, 113, 80, 58, 50, 47, 44, 42],
    recommendations: ['Maintain weekly monitoring', 'Validate anomalies with local teams', 'Review contingency stocks', 'Prepare watch bulletin']
  },
  'South Sudan': {
    risk: 'green', riskLabel: 'Low', alert: 'No immediate risk',
    ndvi: '+0.07', ndviUnit: 'unitless', ndviDelta: '↑ +0.02 vs last month',
    rainfall: '+8%', rainfallUnit: 'vs baseline', rainfallDelta: '↑ +4% vs last month',
    temperature: '+0.4°C', temperatureUnit: 'vs baseline', temperatureDelta: '↑ +0.1°C vs last month',
    score: '0.22', scoreUnit: '/ 1.0', scoreDelta: '↓ 0.02 vs last month',
    quality: 'High', qualityUnit: '91% confidence', qualityDelta: '● Stable',
    exposed: '0.8M', exposedUnit: 'people', exposedDelta: '↓ 0.1M vs last month',
    ndviCurrent: [0.02, 0.15, 0.24, 0.12, 0.17, 0.08], ndviBaseline: [0.03, 0.28, 0.27, 0.23, 0.16, 0.09],
    rainCurrent: [98, 150, 129, 116, 87, 49, 56, 45, 43, 38, 42], rainBaseline: [93, 102, 110, 115, 110, 73, 52, 47, 42, 39, 37],
    recommendations: ['Continue routine monitoring', 'Maintain local reporting channels', 'Review seasonal outlook', 'Document positive field conditions']
  },
  Sudan: {
    risk: 'yellow', riskLabel: 'Watch', alert: 'Below-average rainfall',
    ndvi: '-0.11', ndviUnit: 'unitless', ndviDelta: '↓ -0.04 vs last month', rainfall: '-26%', rainfallUnit: 'vs baseline', rainfallDelta: '↓ -7% vs last month',
    temperature: '+1.5°C', temperatureUnit: 'vs baseline', temperatureDelta: '↑ +0.2°C vs last month', score: '0.51', scoreUnit: '/ 1.0', scoreDelta: '↑ 0.04 vs last month',
    quality: 'Medium', qualityUnit: '84% confidence', qualityDelta: '● Stable', exposed: '3.5M', exposedUnit: 'people', exposedDelta: '↑ 0.2M vs last month',
    ndviCurrent: [-.16,-.04,.02,-.12,-.08,-.17], ndviBaseline: [.03,.30,.27,.22,.13,.05], rainCurrent: [72,110,88,65,32,-8,-16,-24,-20,-28,-25], rainBaseline: [90,100,108,112,106,70,52,47,43,39,37],
    recommendations: ['Track pastoral zones', 'Review water access data', 'Coordinate field verification', 'Prepare watch update']
  },
  Uganda: {
    risk: 'green', riskLabel: 'Low', alert: 'Seasonal conditions stable',
    ndvi: '+0.10', ndviUnit: 'unitless', ndviDelta: '↑ +0.03 vs last month', rainfall: '+12%', rainfallUnit: 'vs baseline', rainfallDelta: '↑ +6% vs last month',
    temperature: '+0.3°C', temperatureUnit: 'vs baseline', temperatureDelta: '→ no material change', score: '0.18', scoreUnit: '/ 1.0', scoreDelta: '↓ 0.03 vs last month',
    quality: 'High', qualityUnit: '95% confidence', qualityDelta: '● Stable', exposed: '0.5M', exposedUnit: 'people', exposedDelta: '↓ 0.1M vs last month',
    ndviCurrent: [.06,.17,.28,.19,.22,.12], ndviBaseline: [.02,.24,.25,.21,.15,.08], rainCurrent: [110,155,134,120,90,58,61,54,50,45,48], rainBaseline: [92,102,109,113,108,74,53,49,44,41,39],
    recommendations: ['Continue routine monitoring', 'Preserve field reporting cadence', 'Review crop calendar', 'Share positive status update']
  },
  Kenya: null,
  Eritrea: null,
  Djibouti: null
};

// Reuse a detailed regional record for map-only countries in this mockup.
regions.Kenya = { ...regions['Northern Kenya'], mapRegion: 'Kenya' };
regions.Eritrea = { ...regions.Ethiopia, risk: 'orange', riskLabel: 'High', alert: 'Vegetation stress increasing', exposed: '0.9M' };
regions.Djibouti = { ...regions.Somalia, risk: 'red', riskLabel: 'Severe', alert: 'Water scarcity risk', exposed: '0.4M' };

const alerts = [
  { rank: 1, region: 'Somalia', level: 'red', title: 'Somalia — Red', subtitle: 'Severe vegetation stress', date: '18 May 2025' },
  { rank: 2, region: 'Northern Kenya', level: 'orange', title: 'Northern Kenya — Orange', subtitle: 'Rainfall deficit', date: '18 May 2025' },
  { rank: 3, region: 'Ethiopia', level: 'yellow', title: 'Ethiopia — Yellow', subtitle: 'Watch conditions', date: '18 May 2025' },
  { rank: 4, region: 'South Sudan', level: 'green', title: 'South Sudan — Green', subtitle: 'No immediate risk', date: '18 May 2025' }
];

const metricDefinitions = [
  { key: 'ndvi', title: 'NDVI anomaly', icon: 'i-leaf' },
  { key: 'rainfall', title: 'Rainfall anomaly', icon: 'i-rain' },
  { key: 'temperature', title: 'Land Surface<br>Temperature anomaly', icon: 'i-temp' },
  { key: 'score', title: 'Composite drought<br>score', icon: 'i-gauge' },
  { key: 'quality', title: 'Data quality', icon: 'i-shield' },
  { key: 'exposed', title: 'Potentially exposed<br>population', icon: 'i-users' }
];

let selectedRegion = 'Somalia';
let toastTimer;

function icon(id, className = '') {
  return `<svg class="${className}" aria-hidden="true"><use href="#${id}"></use></svg>`;
}

function renderAlerts() {
  const container = document.querySelector('#alert-list');
  container.innerHTML = alerts.map(alert => `
    <div class="alert-row">
      <div class="alert-rank">${alert.rank}</div>
      <div class="alert-level-icon ${alert.level}">${icon('i-warning')}</div>
      <div class="alert-copy">
        <h3>${alert.title}</h3>
        <p>${alert.subtitle}</p>
        <span class="alert-date">${icon('i-calendar')} ${alert.date}</span>
      </div>
      <button class="alert-detail-button ${alert.level}" data-alert-region="${alert.region}">View details ${icon('i-chevron')}</button>
    </div>
  `).join('');
}

function populateRegionSelect() {
  const select = document.querySelector('#region-select');
  select.innerHTML = Object.keys(regions).map(region => `<option value="${region}">${region}</option>`).join('');
  select.value = selectedRegion;
}

function renderMetrics(regionName) {
  const data = regions[regionName];
  const metricGrid = document.querySelector('#metric-grid');
  metricGrid.innerHTML = metricDefinitions.map(def => {
    const value = data[def.key];
    const unit = data[`${def.key}Unit`];
    const delta = data[`${def.key}Delta`];
    const tone = def.key === 'quality' ? 'good' : def.key === 'exposed' ? 'neutral' : (String(value).startsWith('+') && def.key === 'ndvi' ? 'good' : 'bad');
    const deltaClass = delta.includes('Stable') ? 'stable' : delta.startsWith('↓') ? 'down' : delta.startsWith('↑') ? 'up' : '';
    return `
      <div class="metric-card">
        <div class="metric-title">${icon(def.icon)}<span>${def.title}</span></div>
        <div class="metric-value ${tone}">${value}${def.key === 'score' ? ` <small>${unit}</small>` : ''}</div>
        <div class="metric-unit">${def.key === 'score' ? data.riskLabel : unit}</div>
        <div class="metric-sub"><span class="${deltaClass}">${delta}</span></div>
      </div>
    `;
  }).join('');
}

function renderRecommendations(regionName) {
  const icons = ['i-droplet', 'i-monitor', 'i-cow', 'i-share'];
  document.querySelector('#recommendations-list').innerHTML = regions[regionName].recommendations
    .map((text, index) => `<li>${icon(icons[index])}<span>${text}</span></li>`).join('');
}

/**
 * Draws a light-weight SVG line chart.
 * CODEX ADAPTATION NOTE: replace this with Plotly/ECharts if the production
 * app needs tooltips, brushing, accessibility tables or many time points.
 */
function drawLineChart(svgId, currentValues, baselineValues, type) {
  const svg = document.querySelector(svgId);
  const width = 530, height = 150;
  const pad = { left: 37, right: 10, top: 6, bottom: 27 };
  const labels = type === 'ndvi' ? ['Dec', 'Jan', 'Feb', 'Mar', 'Apr', 'May'] : ['Dec', 'Jan', '', 'Feb', '', 'Mar', '', 'Apr', '', '', 'May'];
  const min = type === 'ndvi' ? -0.6 : -100;
  const max = type === 'ndvi' ? 0.6 : 200;
  const yTicks = type === 'ndvi' ? [-0.6, -0.3, 0, 0.3, 0.6] : [-100, 0, 100, 200];
  const allLength = Math.max(currentValues.length, baselineValues.length);
  const x = i => pad.left + (i / (allLength - 1)) * (width - pad.left - pad.right);
  const y = value => pad.top + (max - value) / (max - min) * (height - pad.top - pad.bottom);
  const points = values => values.map((value, i) => `${x(i).toFixed(1)},${y(value).toFixed(1)}`).join(' ');

  let html = '';
  yTicks.forEach(tick => {
    html += `<line class="chart-gridline" x1="${pad.left}" x2="${width-pad.right}" y1="${y(tick)}" y2="${y(tick)}" />`;
    html += `<text class="chart-axis-label" x="4" y="${y(tick)+3}">${type === 'rain' ? `${tick}%` : tick.toFixed(1)}</text>`;
  });
  labels.forEach((label, i) => {
    if (!label) return;
    html += `<text class="chart-axis-label" text-anchor="middle" x="${x(i)}" y="${height-8}">${label}</text>`;
  });
  html += `<polyline class="chart-baseline" points="${points(baselineValues)}" />`;
  html += `<polyline class="chart-current ${type}" points="${points(currentValues)}" />`;
  html += currentValues.map((value, i) => `<circle class="chart-point ${type}" cx="${x(i)}" cy="${y(value)}" r="2.7" />`).join('');
  svg.innerHTML = html;
}

function updateMapSelection(regionName) {
  const mapName = regions[regionName].mapRegion || regionName;
  document.querySelectorAll('.country').forEach(country => {
    country.classList.toggle('active', country.dataset.region === mapName);
  });
}

function selectRegion(regionName) {
  if (!regions[regionName]) return;
  selectedRegion = regionName;
  const data = regions[regionName];
  document.querySelector('#selected-region-label').textContent = regionName;
  document.querySelector('#selected-region-label').style.color = ({ red:'#e32d2a', orange:'#ef7411', yellow:'#d8a000', green:'#18813a' })[data.risk];
  document.querySelector('#trends-region').textContent = `(${regionName})`;
  document.querySelector('#region-select').value = regionName;
  renderMetrics(regionName);
  renderRecommendations(regionName);
  drawLineChart('#ndvi-chart', data.ndviCurrent, data.ndviBaseline, 'ndvi');
  drawLineChart('#rain-chart', data.rainCurrent, data.rainBaseline, 'rain');
  updateMapSelection(regionName);
}

function showAlertDetails(regionName) {
  const data = regions[regionName];
  const modal = document.querySelector('#detail-modal');
  document.querySelector('#modal-title').textContent = `${regionName}: ${data.riskLabel} drought risk`;
  document.querySelector('#modal-body').textContent = `${data.alert}. The composite drought score is ${data.score}/1.0 and the estimated potentially exposed population is ${data.exposed}. Use this prototype together with field observations and local expert judgement.`;
  modal.showModal();
}

function showToast(message) {
  const toast = document.querySelector('#toast');
  toast.textContent = message;
  toast.classList.add('visible');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove('visible'), 2200);
}

function downloadBlob(filename, content, type) {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

function exportSelected(format) {
  const data = { region: selectedRegion, updatedAt: '2025-05-18T08:30:00+03:00', ...regions[selectedRegion] };
  if (format === 'json') {
    downloadBlob(`mwangaza-${selectedRegion.toLowerCase().replaceAll(' ', '-')}.json`, JSON.stringify(data, null, 2), 'application/json');
  } else {
    const rows = Object.entries(data).filter(([,value]) => !Array.isArray(value) && typeof value !== 'object');
    const csv = ['metric,value', ...rows.map(([key, value]) => `"${key}","${String(value).replaceAll('"','""')}"`)].join('\n');
    downloadBlob(`mwangaza-${selectedRegion.toLowerCase().replaceAll(' ', '-')}.csv`, csv, 'text/csv');
  }
  showToast(`${format.toUpperCase()} export generated for ${selectedRegion}`);
}

function bindEvents() {
  document.querySelectorAll('.nav-item').forEach(button => button.addEventListener('click', () => {
    document.querySelectorAll('.nav-item').forEach(item => item.classList.remove('active'));
    button.classList.add('active');
    if (button.dataset.view !== 'overview') showToast(`${button.textContent.trim()} is a prototype navigation item`);
  }));

  document.querySelectorAll('.language-btn').forEach(button => button.addEventListener('click', () => {
    document.querySelectorAll('.language-btn').forEach(item => item.classList.remove('active'));
    button.classList.add('active');
    showToast(`Language set to ${button.dataset.lang} (translation strings not loaded in mockup)`);
  }));

  const bandwidthToggle = document.querySelector('#bandwidth-toggle');
  bandwidthToggle.addEventListener('click', () => {
    const on = !bandwidthToggle.classList.contains('on');
    bandwidthToggle.classList.toggle('on', on);
    bandwidthToggle.setAttribute('aria-checked', String(on));
    document.body.classList.toggle('low-bandwidth', on);
    showToast(on ? 'Low bandwidth mode enabled' : 'Low bandwidth mode disabled');
  });

  document.querySelector('#region-select').addEventListener('change', event => selectRegion(event.target.value));

  document.querySelectorAll('.country').forEach(country => {
    const activate = () => selectRegion(country.dataset.region);
    country.addEventListener('click', activate);
    country.addEventListener('keydown', event => {
      if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); activate(); }
    });
  });

  document.querySelector('#alert-list').addEventListener('click', event => {
    const button = event.target.closest('[data-alert-region]');
    if (!button) return;
    selectRegion(button.dataset.alertRegion);
    showAlertDetails(button.dataset.alertRegion);
  });

  document.querySelector('#view-all-alerts').addEventListener('click', () => showToast('All current alerts are already shown in this mockup'));
  document.querySelector('#generate-report').addEventListener('click', () => window.print());
  document.querySelectorAll('[data-export]').forEach(button => button.addEventListener('click', () => exportSelected(button.dataset.export)));
  document.querySelector('.guidance-link').addEventListener('click', () => showAlertDetails(selectedRegion));

  // Map control buttons are present for fidelity. The production map library
  // should own zoom/reset/layer behaviour.
  document.querySelectorAll('.map-controls button').forEach(button => button.addEventListener('click', () => showToast(`${button.title} control clicked`)));
}

function init() {
  renderAlerts();
  populateRegionSelect();
  selectRegion(selectedRegion);
  bindEvents();
}

document.addEventListener('DOMContentLoaded', init);
