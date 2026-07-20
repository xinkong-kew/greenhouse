<template>
  <div class="history-page">
    <!-- 历史数据图表 -->
    <div class="section">
      <h2 class="section-title">📊 历史数据曲线</h2>

      <div class="date-picker card">
        <div class="date-picker-inner">
          <label class="date-label">时间范围：</label>
          <select v-model="rangeType" class="date-input" @change="fetchHistory">
            <option value="today">今天</option>
            <option value="7days">最近7天</option>
            <option value="month">最近30天</option>
          </select>
          <button class="btn-query" @click="fetchHistory">📈 查询</button>
        </div>
      </div>

      <div class="chart-container card">
        <canvas ref="chartCanvas"></canvas>
      </div>

      <div class="chart-controls">
        <button
          v-for="s in sensorOptions"
          :key="s.key"
          class="btn-sensor"
          :class="{ active: selectedSensor === s.key }"
          @click="switchSensor(s.key)"
        >
          {{ s.icon }} {{ s.label }}
        </button>
      </div>

      <!-- 统计卡片 -->
      <div class="stats-grid" v-if="stats">
        <div class="stat-item" v-for="s in sensorOptions" :key="s.key">
          <span class="stat-label">{{ s.icon }} {{ s.label }}</span>
          <span class="stat-value">{{ stats[s.key]?.avg?.toFixed(1) ?? '--' }} <small>{{ s.unit }}</small></span>
          <div class="stat-sub">
            <span class="stat-min">↓ {{ stats[s.key]?.min?.toFixed(1) ?? '--' }}</span>
            <span class="stat-max">↑ {{ stats[s.key]?.max?.toFixed(1) ?? '--' }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 历史数据台：最近500条 -->
    <div class="section">
      <h2 class="section-title">📋 历史数据台 <span class="data-count">(最近 {{ totalRecords }} 条记录)</span></h2>

      <div class="table-container card">
        <div class="table-wrapper">
          <table class="data-table">
            <thead>
              <tr>
                <th>时间</th>
                <th>🌡️ 温度 (°C)</th>
                <th>💧 湿度 (%)</th>
                <th>🌱 土壤湿度 (%)</th>
                <th>💦 水位 (cm)</th>
                <th>🫁 CO2 (ppm)</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="records.length === 0">
                <td colspan="6" class="empty-row">暂无数据</td>
              </tr>
              <tr v-for="(item, index) in records" :key="index">
                <td class="cell-time">{{ item.ts }}</td>
                <td :class="getCellClass(item.temperature, 'temp')">{{ formatVal(item.temperature) }}</td>
                <td :class="getCellClass(item.humidity, 'hum')">{{ formatVal(item.humidity) }}</td>
                <td :class="getCellClass(item.soil_moisture, 'soil')">{{ formatVal(item.soil_moisture) }}</td>
                <td :class="getCellClass(item.water_level, 'water')">{{ formatVal(item.water_level) }}</td>
                <td :class="getCellClass(item.co2, 'co2')">{{ formatVal(item.co2) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div class="table-footer">
          <span>共 {{ totalRecords }} 条记录，显示最近 500 条</span>
          <button class="btn btn-sm" @click="refreshTable">🔄 刷新</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import Chart from 'chart.js/auto'

const chartCanvas = ref(null)
let chartInstance = null

const rangeType = ref('7days')
const selectedSensor = ref('temperature')
const records = ref([])
const totalRecords = ref(0)
const stats = ref(null)

const sensorOptions = [
  { key: 'temperature', label: '温度', icon: '🌡️', unit: '°C', color: '#e74c3c' },
  { key: 'humidity', label: '湿度', icon: '💧', unit: '%', color: '#3498db' },
  { key: 'soil_moisture', label: '土壤湿度', icon: '🌱', unit: '%', color: '#f39c12' },
  { key: 'water_level', label: '水位', icon: '💦', unit: 'cm', color: '#1abc9c' },
  { key: 'co2', label: 'CO2', icon: '🫁', unit: 'ppm', color: '#9b59b6' }
]

function formatVal(val) {
  if (val === null || val === undefined) return '--'
  return Number(val).toFixed(1)
}

function getCellClass(val, type) {
  if (val === null || val === undefined) return ''
  const v = Number(val)
  let cls = 'cell-val'
  if (type === 'temp') {
    if (v > 35) cls += ' cell-danger'
    else if (v > 30) cls += ' cell-warning'
    else if (v < 5) cls += ' cell-danger'
    else if (v < 10) cls += ' cell-warning'
    else cls += ' cell-normal'
  } else if (type === 'hum') {
    if (v > 85 || v < 20) cls += ' cell-danger'
    else if (v > 70 || v < 30) cls += ' cell-warning'
    else cls += ' cell-normal'
  } else if (type === 'soil') {
    if (v > 80 || v < 10) cls += ' cell-danger'
    else if (v > 60 || v < 20) cls += ' cell-warning'
    else cls += ' cell-normal'
  } else if (type === 'water') {
    if (v > 40 || v < 5) cls += ' cell-danger'
    else if (v > 30 || v < 10) cls += ' cell-warning'
    else cls += ' cell-normal'
  } else if (type === 'co2') {
    if (v > 1500 || v < 200) cls += ' cell-danger'
    else if (v > 1000 || v < 300) cls += ' cell-warning'
    else cls += ' cell-normal'
  }
  return cls
}

async function fetchHistory() {
  try {
    const res = await fetch(`/api/history?range=${rangeType.value}`)
    const json = await res.json()
    if (json.success) {
      renderChart(json.chart, json.stats)
      const raw = json.records || []
      raw.sort((a, b) => new Date(b.ts) - new Date(a.ts))
      records.value = raw
      totalRecords.value = json.total_records || 0
      stats.value = json.stats || null
    }
  } catch {
    renderMockChart()
  }
}

async function refreshTable() {
  try {
    const res = await fetch(`/api/history?range=${rangeType.value}`)
    const json = await res.json()
    if (json.success) {
      const raw = json.records || []
      raw.sort((a, b) => new Date(b.ts) - new Date(a.ts))
      records.value = raw
      totalRecords.value = json.total_records || 0
    }
  } catch {
    // 静默
  }
}

function renderChart(chart, stats) {
  if (!chartCanvas.value || !chart) return

  const sensor = sensorOptions.find(s => s.key === selectedSensor.value)
  if (!sensor) return

  let dataKey, label, color

  switch (selectedSensor.value) {
    case 'temperature': dataKey = 'temperatures'; color = '#e74c3c'; label = '温度'; break
    case 'humidity': dataKey = 'humidities'; color = '#3498db'; label = '湿度'; break
    case 'soil_moisture': dataKey = 'soil_moistures'; color = '#f39c12'; label = '土壤湿度'; break
    case 'water_level': dataKey = 'water_levels'; color = '#1abc9c'; label = '水位'; break
    case 'co2': dataKey = 'co2_values'; color = '#9b59b6'; label = 'CO2'; break
    default: dataKey = 'temperatures'; color = '#e74c3c'; label = '温度'
  }

  const labels = chart.labels || []
  const values = chart[dataKey] || []

  if (chartInstance) chartInstance.destroy()

  chartInstance = new Chart(chartCanvas.value, {
    type: 'line',
    data: {
      labels,
      datasets: [{
        label: `${label} (${sensor.unit})`,
        data: values,
        borderColor: color,
        backgroundColor: color + '20',
        fill: true,
        tension: 0.3,
        pointRadius: 3,
        pointHoverRadius: 6
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: true,
          position: 'top',
          labels: { color: '#c8d6e5', font: { size: 12 } }
        },
        tooltip: { mode: 'index', intersect: false }
      },
      scales: {
        x: {
          display: true,
          ticks: { color: 'rgba(200,214,229,0.5)', maxRotation: 45, maxTicksLimit: 15, font: { size: 10 } },
          grid: { color: 'rgba(0,255,136,0.04)' }
        },
        y: {
          display: true,
          ticks: { color: 'rgba(200,214,229,0.5)', font: { size: 10 } },
          grid: { color: 'rgba(0,255,136,0.04)' },
          beginAtZero: false
        }
      }
    }
  })
}

function renderMockChart() {
  if (!chartCanvas.value) return
  const now = Date.now()
  const labels = []
  const values = []
  const sensor = sensorOptions.find(s => s.key === selectedSensor.value)
  const base = selectedSensor.value === 'temperature' ? 25 : selectedSensor.value === 'humidity' ? 60 : selectedSensor.value === 'soil_moisture' ? 45 : selectedSensor.value === 'water_level' ? 20 : 400
  const range = selectedSensor.value === 'temperature' ? 10 : selectedSensor.value === 'co2' ? 300 : 20

  for (let i = 168; i >= 0; i--) {
    const d = new Date(now - i * 3600000)
    labels.push(`${d.getMonth() + 1}/${d.getDate()} ${String(d.getHours()).padStart(2, '0')}:00`)
    values.push(Math.round((base + Math.sin(i * 0.2) * range * 0.5 + (Math.random() - 0.5) * 3) * 10) / 10)
  }

  if (chartInstance) chartInstance.destroy()

  chartInstance = new Chart(chartCanvas.value, {
    type: 'line',
    data: {
      labels,
      datasets: [{
        label: sensor ? `${sensor.label} (${sensor.unit})` : selectedSensor.value,
        data: values,
        borderColor: sensor ? sensor.color : '#2ecc71',
        backgroundColor: sensor ? sensor.color + '20' : '#2ecc7120',
        fill: true,
        tension: 0.3,
        pointRadius: 2,
        pointHoverRadius: 6
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: true, position: 'top', labels: { color: '#c8d6e5', font: { size: 12 } } },
        tooltip: { mode: 'index', intersect: false }
      },
      scales: {
        x: { ticks: { color: 'rgba(200,214,229,0.5)', maxRotation: 45, maxTicksLimit: 15, font: { size: 10 } }, grid: { color: 'rgba(0,255,136,0.04)' } },
        y: { ticks: { color: 'rgba(200,214,229,0.5)', font: { size: 10 } }, grid: { color: 'rgba(0,255,136,0.04)' }, beginAtZero: false }
      }
    }
  })
}

function switchSensor(key) {
  selectedSensor.value = key
  nextTick(() => {
    fetchHistory()
  })
}

onMounted(() => {
  nextTick(() => {
    fetchHistory()
  })
})
</script>

<style scoped>
.history-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
  height: 100%;
  overflow: hidden;
}

.section {
  width: 100%;
  flex-shrink: 0;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.data-count {
  font-size: 12px;
  font-weight: 400;
  color: rgba(200, 214, 229, 0.4);
}

.date-picker {
  margin-bottom: 2px;
  padding: 8px 12px;
}

.date-picker-inner {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.date-label {
  font-size: 12px;
  color: rgba(200, 214, 229, 0.6);
  font-weight: 500;
}

.date-input {
  padding: 5px 10px;
  background: rgba(0, 255, 136, 0.04);
  border: 1px solid rgba(0, 255, 136, 0.12);
  border-radius: 6px;
  font-size: 12px;
  color: #c8d6e5;
  outline: none;
  cursor: pointer;
}

.date-input:focus {
  border-color: rgba(0, 255, 136, 0.3);
}

.btn-query {
  padding: 5px 14px;
  background: rgba(0, 255, 136, 0.12);
  color: #00ff88;
  border: 1px solid rgba(0, 255, 136, 0.2);
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-query:hover {
  background: rgba(0, 255, 136, 0.2);
}

.chart-container {
  position: relative;
  height: 200px;
  padding: 10px 12px;
}

.chart-container canvas {
  width: 100% !important;
  height: 100% !important;
}

.chart-controls {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-top: 4px;
}

.btn-sensor {
  padding: 4px 12px;
  background: rgba(0, 255, 136, 0.03);
  color: rgba(200, 214, 229, 0.6);
  border: 1px solid rgba(0, 255, 136, 0.08);
  border-radius: 6px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-sensor:hover {
  border-color: rgba(0, 255, 136, 0.25);
  color: #00ff88;
}

.btn-sensor.active {
  background: rgba(0, 255, 136, 0.12);
  color: #00ff88;
  border-color: rgba(0, 255, 136, 0.25);
}

/* ===== 统计卡片 ===== */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 8px;
  margin-top: 8px;
}

.stat-item {
  background: rgba(0, 255, 136, 0.03);
  border: 1px solid rgba(0, 255, 136, 0.08);
  border-radius: 8px;
  padding: 10px;
  text-align: center;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.stat-label {
  font-size: 11px;
  color: rgba(200, 214, 229, 0.5);
  font-weight: 500;
}

.stat-value {
  font-size: 20px;
  font-weight: 700;
  color: #00ff88;
  font-family: 'Courier New', monospace;
}

.stat-value small {
  font-size: 11px;
  color: rgba(200, 214, 229, 0.4);
  font-weight: 400;
}

.stat-sub {
  display: flex;
  justify-content: center;
  gap: 12px;
  font-size: 11px;
  font-family: 'Courier New', monospace;
}

.stat-min {
  color: #3498db;
}

.stat-max {
  color: #e74c3c;
}

/* ===== 数据表格 ===== */
.table-container {
  padding: 0;
  overflow: hidden;
}

.table-wrapper {
  overflow-x: auto;
  max-height: 280px;
  overflow-y: auto;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}

.data-table thead {
  position: sticky;
  top: 0;
  z-index: 1;
}

.data-table th {
  padding: 7px 10px;
  text-align: left;
  font-weight: 600;
  font-size: 12px;
  color: rgba(200, 214, 229, 0.7);
  background: rgba(0, 20, 10, 0.95);
  border-bottom: 1px solid rgba(0, 255, 136, 0.1);
  white-space: nowrap;
}

.data-table td {
  padding: 5px 10px;
  border-bottom: 1px solid rgba(0, 255, 136, 0.04);
  font-size: 12px;
  font-family: 'Courier New', monospace;
}

.data-table tbody tr:hover {
  background: rgba(0, 255, 136, 0.04);
}

.data-table tbody tr:nth-child(even) {
  background: rgba(0, 255, 136, 0.02);
}

.cell-time {
  color: rgba(200, 214, 229, 0.5);
  font-size: 11px;
  white-space: nowrap;
}

.cell-val {
  font-weight: 600;
}

.cell-normal {
  color: #00ff88;
}

.cell-warning {
  color: #ffa500;
}

.cell-danger {
  color: #ff4757;
}

.empty-row {
  text-align: center;
  padding: 30px !important;
  color: rgba(200, 214, 229, 0.3);
  font-size: 13px;
}

.table-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 14px;
  border-top: 1px solid rgba(0, 255, 136, 0.08);
  font-size: 11px;
  color: rgba(200, 214, 229, 0.4);
}

.table-footer .btn {
  padding: 4px 10px;
  font-size: 11px;
}

@media (max-width: 768px) {
  .chart-container {
    height: 160px;
  }
  .date-picker-inner {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>

<!-- 手机模式全局样式 -->
<style>
.mobile-mode .history-page {
  padding: 0;
  height: auto;
  overflow: visible;
}

.mobile-mode .history-page .section {
  margin-bottom: 10px;
}

.mobile-mode .history-page .section-title {
  font-size: 14px;
  margin-bottom: 8px;
}

.mobile-mode .date-picker-inner {
  flex-wrap: wrap;
  gap: 6px;
}

.mobile-mode .date-picker-inner .date-label {
  font-size: 12px;
}

.mobile-mode .date-picker-inner .date-input {
  font-size: 13px;
  padding: 6px 8px;
  flex: 1;
  min-width: 0;
}

.mobile-mode .date-picker-inner .btn-query {
  font-size: 12px;
  padding: 6px 12px;
}

.mobile-mode .chart-card {
  min-height: 200px;
}

.mobile-mode .chart-card canvas {
  max-height: 200px;
}

.mobile-mode .stats-grid {
  grid-template-columns: 1fr 1fr;
  gap: 6px;
}

.mobile-mode .stat-item {
  padding: 8px;
}

.mobile-mode .stat-label {
  font-size: 11px;
}

.mobile-mode .stat-value {
  font-size: 16px;
}

.mobile-mode .data-table-wrapper {
  overflow-x: auto;
}

.mobile-mode .data-table {
  font-size: 11px;
}

.mobile-mode .data-table th,
.mobile-mode .data-table td {
  padding: 6px 8px;
  white-space: nowrap;
}

.mobile-mode .card {
  padding: 12px;
}

.mobile-mode .glow-card {
  padding: 12px;
}
</style>