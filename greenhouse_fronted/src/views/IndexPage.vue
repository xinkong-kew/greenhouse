<template>
  <div class="dashboard">
    <!-- ===== 左栏：传感器 + 设备 ===== -->
    <div class="col-left">
      <!-- 传感器数据 -->
      <div class="glow-card">
        <div class="glow-card-title">📡 传感器数据</div>
        <div class="sensor-grid">
          <div class="sensor-item">
            <div class="sensor-icon">🌡️</div>
            <div class="sensor-info">
              <div class="sensor-label">温度</div>
              <div class="sensor-val">{{ sensors.temp || '--' }}</div>
            </div>
            <div class="sensor-tag" :class="sensors.tempTag">{{ sensors.tempTag || '' }}</div>
          </div>
          <div class="sensor-item">
            <div class="sensor-icon">💧</div>
            <div class="sensor-info">
              <div class="sensor-label">湿度</div>
              <div class="sensor-val">{{ sensors.hum || '--' }}</div>
            </div>
            <div class="sensor-tag" :class="sensors.humTag">{{ sensors.humTag || '' }}</div>
          </div>
          <div class="sensor-item">
            <div class="sensor-icon">🌱</div>
            <div class="sensor-info">
              <div class="sensor-label">土壤湿度</div>
              <div class="sensor-val">{{ sensors.soil || '--' }}</div>
            </div>
            <div class="sensor-tag" :class="sensors.soilTag">{{ sensors.soilTag || '' }}</div>
          </div>
          <div class="sensor-item">
            <div class="sensor-icon">💦</div>
            <div class="sensor-info">
              <div class="sensor-label">水位</div>
              <div class="sensor-val">{{ sensors.water || '--' }}</div>
            </div>
            <div class="sensor-tag" :class="sensors.waterTag">{{ sensors.waterTag || '' }}</div>
          </div>
          <div class="sensor-item">
            <div class="sensor-icon">🫁</div>
            <div class="sensor-info">
              <div class="sensor-label">CO₂</div>
              <div class="sensor-val">{{ sensors.co2 || '--' }}</div>
            </div>
            <div class="sensor-tag" :class="sensors.co2Tag">{{ sensors.co2Tag || '' }}</div>
          </div>
        </div>
      </div>

      <!-- 设备状态 -->
      <div class="glow-card">
        <div class="glow-card-title">🔌 设备状态</div>
        <div class="device-grid">
          <div class="device-item" :class="{ active: devices.pump.state }">
            <div class="device-icon">🚰</div>
            <div class="device-name">水泵</div>
            <div class="device-indicator" :class="devices.pump.state ? 'on' : 'off'"></div>
          </div>
          <div class="device-item" :class="{ active: devices.fan.state }">
            <div class="device-icon">🌀</div>
            <div class="device-name">风扇</div>
            <div class="device-indicator" :class="devices.fan.state ? 'on' : 'off'"></div>
          </div>
          <div class="device-item" :class="{ active: devices.motor.state }">
            <div class="device-icon">🔄</div>
            <div class="device-name">舵机</div>
            <div class="device-indicator" :class="devices.motor.state ? 'on' : 'off'"></div>
          </div>
          <div class="device-item" :class="{ active: devices.flame.state }">
            <div class="device-icon">🔥</div>
            <div class="device-name">火焰警报</div>
            <div class="device-indicator" :class="devices.flame.state ? 'on' : 'off'"></div>
          </div>
          <div class="device-item" :class="{ active: devices.human.state }">
            <div class="device-icon">🚨</div>
            <div class="device-name">安防警报</div>
            <div class="device-indicator" :class="devices.human.state ? 'on' : 'off'"></div>
          </div>
        </div>
      </div>

      <!-- 最近20分钟数据 -->
      <div class="glow-card mini-chart-card">
        <div class="glow-card-title">📈 最近20分钟数据</div>
        <div class="mini-chart-row">
          <div class="mini-chart-half">
            <div class="mini-chart-subtitle">🌡️ 温湿度</div>
            <div class="mini-chart-container">
              <canvas ref="chartTempHum"></canvas>
            </div>
          </div>
          <div class="mini-chart-half">
            <div class="mini-chart-subtitle">🌱 土壤湿度 & 水位</div>
            <div class="mini-chart-container">
              <canvas ref="chartSoilWater"></canvas>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ===== 中栏：天气 + 智能管家 ===== -->
    <div class="col-center">
      <!-- 天气预报 -->
      <div class="glow-card weather-card">
        <div class="glow-card-title">
          🌤️ 天气预报
          <span class="weather-city">{{ sharedCity.name || '加载中...' }}</span>
          <button class="btn btn-sm btn-city" @click="showCityMap = true" title="切换城市">🗺️</button>
          <button class="btn btn-sm" @click="refreshWeather" style="margin-left:auto">🔄</button>
        </div>

        <!-- 城市选择地图（可视化中国地图） -->
        <ChinaMapV2
          v-if="showCityMap"
          :currentCity="sharedCity.name"
          @close="showCityMap = false"
          @select="onCitySelect"
        />
        <div class="weather-main">
          <div class="weather-temp-box">
            <div class="weather-temp">{{ weather.temp || '--' }}</div>
            <div class="weather-icon-big">{{ weather.icon || '🌤️' }}</div>
            <div class="weather-desc">{{ weather.desc || '--' }}</div>
          </div>
          <div class="weather-detail-grid">
            <div class="wd-item">
              <span class="wd-label">💧 湿度</span>
              <span class="wd-val">{{ weather.hum || '--' }}</span>
            </div>
            <div class="wd-item">
              <span class="wd-label">💨 风速</span>
              <span class="wd-val">{{ weather.wind || '--' }}</span>
            </div>
            <div class="wd-item">
              <span class="wd-label">🌧️ 降雨</span>
              <span class="wd-val">{{ weather.rain || '--' }}</span>
            </div>
            <div class="wd-item">
              <span class="wd-label">🔽 气压</span>
              <span class="wd-val">{{ weather.pressure || '--' }}</span>
            </div>
          </div>
        </div>
        <div class="weather-forecast" v-if="forecastList.length > 0">
          <div class="fc-item" v-for="(item, index) in forecastList" :key="index"
               :class="{ 'fc-rain': item.rain, 'fc-hot': item.hot }">
            <div class="fc-time">{{ item.time }}</div>
            <div class="fc-icon">{{ item.icon }}</div>
            <div class="fc-temp">{{ item.temp }}</div>
          </div>
        </div>
      </div>

      <!-- 作品线稿图 -->
      <div class="glow-card sketch-card">
        <div class="glow-card-title">🎨 作品线稿</div>
        <div class="sketch-grid">
          <div class="sketch-item">
            <div class="sketch-label">正视图</div>
            <div class="sketch-image-wrapper" @click="openLightbox('/sketch.jpg', '正视图')">
              <img src="/sketch.jpg" alt="正视图" class="sketch-image" />
            </div>
          </div>
          <div class="sketch-item">
            <div class="sketch-label">俯视图</div>
            <div class="sketch-image-wrapper" @click="openLightbox('/topview.jpg', '俯视图')">
              <img src="/topview.jpg" alt="俯视图" class="sketch-image" />
            </div>
          </div>
        </div>
      </div>

      <!-- 图片查看器 -->
      <div v-if="lightboxVisible" class="lightbox-overlay" @click.self="closeLightbox">
        <div class="lightbox-content">
          <button class="lightbox-close" @click="closeLightbox">&times;</button>
          <img :src="lightboxSrc" :alt="lightboxAlt" class="lightbox-image" />
          <div class="lightbox-label">{{ lightboxAlt }}</div>
        </div>
      </div>

      <!-- 智能管家 -->
      <div class="glow-card agent-card">
        <div class="glow-card-title">
          🤖 智能管家
          <span class="agent-badge" :class="agent.badgeClass" v-html="agent.badgeText"></span>
          <span class="agent-count">📋 {{ agent.decisions.length }} 条</span>
          <button class="btn btn-sm btn-predict" @click="predictTomorrowAgent" :disabled="agentPredictLoading" style="margin-left:auto">
            🔮 {{ agentPredictResult ? '收起预测' : '明天预测' }}
          </button>
        </div>

        <!-- 明天天气预测（内联展开） -->
        <div v-if="agentPredictResult" class="agent-predict-inline">
          <div class="api-summary">
            <span class="api-date">{{ agentPredictResult.tomorrow.date }}</span>
            <span class="api-temp" :class="{hot: agentPredictResult.tomorrow.max_temp >= 35, cold: agentPredictResult.tomorrow.min_temp <= 5}">
              {{ agentPredictResult.tomorrow.min_temp }}~{{ agentPredictResult.tomorrow.max_temp }}°C
            </span>
            <span class="api-weather">{{ agentPredictResult.tomorrow.weather_desc }}</span>
            <span v-if="agentPredictResult.tomorrow.has_rain" class="api-rain">🌧️ 有雨</span>
          </div>
          <div class="api-suggestions">
            <div class="api-sg" v-for="(sg, i) in agentPredictResult.suggestions" :key="i">
              <span>{{ sg.icon }}</span>
              <span>{{ sg.suggestion }}</span>
              <span class="api-sg-reason">{{ sg.reason }}</span>
            </div>
          </div>
          <div class="api-goto">
            <router-link to="/control" class="btn btn-sm">📤 前往控制面板应用建议 →</router-link>
          </div>
        </div>
        <div v-if="agentPredictLoading" class="agent-predict-loading">⏳ 正在分析明天天气...</div>

        <div class="agent-decisions" v-if="agent.decisions.length > 0">
          <div class="ad-item" v-for="(d, index) in agent.decisions" :key="index">
            <span class="ad-level">{{ d.levelIcon }}</span>
            <span class="ad-time">{{ d.time }}</span>
            <span class="ad-action">{{ d.action }}</span>
            <span class="ad-reason">{{ d.reason }}</span>
          </div>
        </div>
        <div class="agent-empty" v-else>⏳ 等待智能体生成决策...</div>
      </div>
    </div>

    <!-- ===== 右栏：AI 助手 + 监控画面 ===== -->
    <div class="col-right">
      <!-- 上半部分：AI 助手 -->
      <div class="glow-card chat-card">
        <div class="glow-card-title">🤖 AI 助手</div>
        <div class="chat-messages" ref="chatRef">
          <div class="msg msg-ai" v-for="(msg, i) in chatMessages" :key="i">
            <div class="msg-avatar">{{ msg.role === 'ai' ? '🤖' : '👤' }}</div>
            <div class="msg-content">
              <div class="msg-text">{{ msg.text }}</div>
              <div class="msg-time">{{ msg.time }}</div>
            </div>
          </div>
          <div class="msg-typing" v-if="chatLoading">
            <span class="typing-dot"></span>
            <span class="typing-dot"></span>
            <span class="typing-dot"></span>
          </div>
        </div>
        <div class="chat-input-row">
          <div class="quick-questions">
            <button
              v-for="(q, i) in quickQuestions"
              :key="i"
              class="qq-btn"
              @click="sendQuickQuestion(q.text)"
            >
              {{ q.icon }} {{ q.text }}
            </button>
          </div>
          <div class="chat-input-bar">
            <input
              class="chat-input"
              v-model="chatInput"
              @keydown.enter="sendChatMessage"
              placeholder="输入您的问题..."
            />
            <button class="btn" @click="sendChatMessage" :disabled="chatLoading || !chatInput.trim()">
              发送
            </button>
          </div>
        </div>
      </div>

      <!-- 下半部分：监控画面 -->
      <div class="glow-card monitor-card">
        <div class="glow-card-title">📹 监控画面</div>
        <div class="monitor-container">
          <iframe
            class="monitor-iframe"
            :src="monitorUrl"
            frameborder="0"
            allowfullscreen
            referrerpolicy="no-referrer"
            @load="monitorLoading = false"
          ></iframe>
          <div class="monitor-overlay" v-if="monitorLoading">
            <span class="monitor-loading-text">⏳ 加载监控画面...</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref, onMounted, onUnmounted, nextTick, watch } from 'vue'
import socket from '../utils/socket.js'
import Chart from 'chart.js/auto'
import ChinaMapV2 from '../components/ChinaMapV2.vue'
import { sharedCity, updateCity, initCityFromServer } from '../stores/sharedCity.js'

// ===== 传感器 =====
const sensors = reactive({
  temp: '--', tempTag: '',
  hum: '--', humTag: '',
  soil: '--', soilTag: '',
  water: '--', waterTag: '',
  co2: '--', co2Tag: ''
})

// ===== 设备 =====
const devices = reactive({
  pump: { state: false },
  fan: { state: false },
  motor: { state: false },
  flame: { state: false },
  human: { state: false }
})

// ===== 天气 =====
const weather = reactive({
  city: '', temp: '', desc: '', icon: '',
  hum: '', wind: '', rain: '', pressure: ''
})
const forecastList = ref([])
const showCityMap = ref(false)

// ===== 图片查看器 =====
const lightboxVisible = ref(false)
const lightboxSrc = ref('')
const lightboxAlt = ref('')

function openLightbox(src, alt) {
  lightboxSrc.value = src
  lightboxAlt.value = alt
  lightboxVisible.value = true
}

function closeLightbox() {
  lightboxVisible.value = false
}

async function onCitySelect({ province, city, cityEn }) {
  showCityMap.value = false
  updateCity(city, cityEn)
  // 清除旧天气数据，显示加载状态
  weather.city = city
  weather.temp = '--'
  weather.desc = '加载中...'
  weather.icon = '🌤️'
  try {
    const res = await fetch('/api/weather/set_city', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ city: cityEn })
    })
    const data = await res.json()
    if (data.success && data.forecast) {
      // 直接使用API返回的天气数据更新界面
      applyWeatherData(data.forecast, city)
    } else {
      // 备用：通过socket请求
      setTimeout(() => socket.emit('request_weather'), 500)
    }
  } catch {
    setTimeout(() => socket.emit('request_weather'), 500)
  }
}

// 直接应用天气数据到界面，不依赖socket事件
function applyWeatherData(forecast, cityName) {
  if (!forecast) return
  weather.city = cityName
  updateCity(cityName, forecast.city_en || '')
  const fc = forecast.forecast || []
  if (fc.length > 0) {
    const cur = fc[0]
    weather.temp = cur.temp !== undefined ? cur.temp.toFixed(1) + '°C' : '--'
    weather.desc = cur.weather || '--'
    weather.icon = getWeatherIcon(cur.weather_code)
    weather.hum = cur.humidity !== undefined ? cur.humidity + '%' : '--'
    weather.wind = cur.wind_speed !== undefined ? cur.wind_speed + 'm/s' : '--'
    weather.rain = cur.pop !== undefined ? (cur.pop * 100).toFixed(0) + '%' : '--'
    weather.pressure = cur.pressure !== undefined ? cur.pressure + 'hPa' : '--'
  }
  // 更新预报列表（24小时，每3小时一次，共8个）
  const forecastListRaw = fc.slice(0, 8)
  forecastList.value = forecastListRaw.map(f => ({
    time: f.time ? f.time.slice(5) : '',
    icon: getWeatherIcon(f.weather_code),
    temp: f.temp !== undefined ? f.temp.toFixed(0) + '°' : '--',
    rain: f.weather && (f.weather.includes('雨') || f.weather.includes('雪') || f.weather.includes('雷')),
    hot: f.temp_max !== undefined && f.temp_max > 35
  }))
}

// ===== 智能管家 =====
const agent = reactive({
  badgeClass: 'off', badgeText: '加载中...', decisions: []
})

// ===== AI 聊天 =====
const chatMessages = ref([
  { role: 'ai', text: '您好！我是智能温室助手，有什么可以帮您的？', time: '' }
])
const chatInput = ref('')
const chatLoading = ref(false)
const chatRef = ref(null)

// ===== 监控画面 =====
const monitorUrl = ref('http://10.116.27.43')
const monitorLoading = ref(true)

// ===== 常用问题快捷按钮 =====
const quickQuestions = [
  { icon: '🌡️', text: '当前环境如何' },
  { icon: '⚠️', text: '有什么异常' },
  { icon: '📊', text: '数据趋势分析' },
  { icon: '💡', text: '优化建议' }
]

function sendQuickQuestion(text) {
  chatInput.value = text
  sendChatMessage()
}

// ===== 迷你图表（双曲面图） =====
const chartTempHum = ref(null)
const chartSoilWater = ref(null)
let chartTempHumInstance = null
let chartSoilWaterInstance = null
const chartData = ref({
  timestamps: [],
  temperatures: [],
  humidities: [],
  soil_moistures: [],
  water_levels: [],
  co2_values: []
})

function renderCharts() {
  const data = chartData.value
  // 即使无数据也显示框架，生成20分钟每分钟的标签
  const labels = data.timestamps.length ? data.timestamps : generateTimeLabels()
  const hasData = data.timestamps.length > 0

  // 图1：温湿度曲面图
  if (chartTempHum.value) {
    if (chartTempHumInstance) chartTempHumInstance.destroy()
    chartTempHumInstance = new Chart(chartTempHum.value, {
      type: 'line',
      data: {
        labels,
        datasets: [
          {
            label: '温度 (°C)',
            data: hasData ? data.temperatures : [],
            borderColor: '#e74c3c',
            backgroundColor: 'rgba(231, 76, 60, 0.2)',
            fill: true,
            tension: 0.3,
            pointRadius: 1.5,
            pointHoverRadius: 4,
            borderWidth: 1.5
          },
          {
            label: '湿度 (%)',
            data: hasData ? data.humidities : [],
            borderColor: '#3498db',
            backgroundColor: 'rgba(52, 152, 219, 0.2)',
            fill: true,
            tension: 0.3,
            pointRadius: 1.5,
            pointHoverRadius: 4,
            borderWidth: 1.5
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: true,
            position: 'top',
            labels: { color: 'rgba(200,214,229,0.6)', font: { size: 9 }, boxWidth: 12, padding: 6 }
          },
          tooltip: { mode: 'index', intersect: false, bodyFont: { size: 10 } }
        },
        scales: {
          x: {
            ticks: { color: 'rgba(200,214,229,0.35)', font: { size: 8 }, maxTicksLimit: 10, maxRotation: 0 },
            grid: { color: 'rgba(0,255,136,0.04)' }
          },
          y: {
            ticks: { color: 'rgba(200,214,229,0.35)', font: { size: 8 }, maxTicksLimit: 4 },
            grid: { color: 'rgba(0,255,136,0.04)' }
          }
        },
        animation: { duration: 300 }
      }
    })
  }

  // 图2：土壤湿度 & 水位曲面图
  if (chartSoilWater.value) {
    if (chartSoilWaterInstance) chartSoilWaterInstance.destroy()
    chartSoilWaterInstance = new Chart(chartSoilWater.value, {
      type: 'line',
      data: {
        labels,
        datasets: [
          {
            label: '土壤湿度 (%)',
            data: hasData ? data.soil_moistures : [],
            borderColor: '#f39c12',
            backgroundColor: 'rgba(243, 156, 18, 0.2)',
            fill: true,
            tension: 0.3,
            pointRadius: 1.5,
            pointHoverRadius: 4,
            borderWidth: 1.5
          },
          {
            label: '水位 (%)',
            data: hasData ? data.water_levels : [],
            borderColor: '#1abc9c',
            backgroundColor: 'rgba(26, 188, 156, 0.2)',
            fill: true,
            tension: 0.3,
            pointRadius: 1.5,
            pointHoverRadius: 4,
            borderWidth: 1.5
          },
          {
            label: 'CO₂ (ppm)',
            data: hasData ? data.co2_values : [],
            borderColor: '#9b59b6',
            backgroundColor: 'rgba(155, 89, 182, 0.2)',
            fill: true,
            tension: 0.3,
            pointRadius: 1.5,
            pointHoverRadius: 4,
            borderWidth: 1.5
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: true,
            position: 'top',
            labels: { color: 'rgba(200,214,229,0.6)', font: { size: 9 }, boxWidth: 12, padding: 6 }
          },
          tooltip: { mode: 'index', intersect: false, bodyFont: { size: 10 } }
        },
        scales: {
          x: {
            ticks: { color: 'rgba(200,214,229,0.35)', font: { size: 8 }, maxTicksLimit: 10, maxRotation: 0 },
            grid: { color: 'rgba(0,255,136,0.04)' }
          },
          y: {
            ticks: { color: 'rgba(200,214,229,0.35)', font: { size: 8 }, maxTicksLimit: 4 },
            grid: { color: 'rgba(0,255,136,0.04)' }
          }
        },
        animation: { duration: 300 }
      }
    })
  }
}

// 生成20分钟每分钟的时间标签（用于空图表框架）
function generateTimeLabels() {
  const now = new Date()
  const labels = []
  for (let i = 19; i >= 0; i--) {
    const t = new Date(now.getTime() - i * 60000)
    labels.push(`${String(t.getHours()).padStart(2, '0')}:${String(t.getMinutes()).padStart(2, '0')}`)
  }
  return labels
}

function updateCharts(chartSrcData) {
  if (!chartSrcData || !chartSrcData.timestamps) return
  chartData.value = {
    timestamps: chartSrcData.timestamps,
    temperatures: chartSrcData.temperatures,
    humidities: chartSrcData.humidities,
    soil_moistures: chartSrcData.soil_moistures,
    water_levels: chartSrcData.water_levels,
    co2_values: chartSrcData.co2_values
  }
  nextTick(renderCharts)
}

async function fetchChartData() {
  try {
    const res = await fetch('/api/recent_data')
    const json = await res.json()
    if (json.success && json.data.length > 0) {
      const d = json.data
      chartData.value = {
        timestamps: d.map(r => r.timestamp),
        temperatures: d.map(r => r.temperature),
        humidities: d.map(r => r.humidity),
        soil_moistures: d.map(r => r.soil_moisture),
        water_levels: d.map(r => r.water_level),
        co2_values: d.map(r => r.co2)
      }
      nextTick(renderCharts)
    }
  } catch {
    // 静默
  }
}

function refreshWeather() {
  socket.emit('request_weather')
}

// ===== 智能管家 - 明天天气预测 =====
const agentPredictLoading = ref(false)
const agentPredictResult = ref(null)

async function predictTomorrowAgent() {
  // 如果已显示预测结果，再次点击则收起
  if (agentPredictResult.value) {
    agentPredictResult.value = null
    return
  }
  agentPredictLoading.value = true
  agentPredictResult.value = null
  try {
    const res = await fetch('/api/weather/tomorrow_suggestions')
    const data = await res.json()
    if (data.success) {
      agentPredictResult.value = data
    }
  } catch {
    // 静默处理
  }
  agentPredictLoading.value = false
}

function scrollChat() {
  nextTick(() => {
    if (chatRef.value) {
      chatRef.value.scrollTop = chatRef.value.scrollHeight
    }
  })
}

async function sendChatMessage() {
  const msg = chatInput.value.trim()
  if (!msg || chatLoading.value) return
  chatInput.value = ''
  chatLoading.value = true

  const now = new Date()
  const timeStr = `${String(now.getHours()).padStart(2,'0')}:${String(now.getMinutes()).padStart(2,'0')}`
  chatMessages.value.push({ role: 'user', text: msg, time: timeStr })
  scrollChat()

  try {
    const res = await fetch('/api/ai/chat', {
     method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: msg })
    })
    const data = await res.json()
    const reply = data.response || data.message || '抱歉，暂时无法回复。'
    chatMessages.value.push({ role: 'ai', text: reply, time: timeStr })
  } catch {
    chatMessages.value.push({ role: 'ai', text: '连接失败，请稍后重试。', time: timeStr })
  }
  chatLoading.value = false
  scrollChat()
}

// ===== REST API 轮询回退（当 Socket.IO 连接不可用时） =====
let weatherPollTimer = null

async function fetchWeatherAgentData() {
  try {
    const res = await fetch('/api/agent/status')
    const data = await res.json()
    if (data.success && data.forecast) {
      handleWeatherUpdate(data)
    }
  } catch {
    // 静默
  }
}

// ===== Socket 事件处理 =====
function handleRealtimeUpdate(data) {
  if (!data) return
  if (data.temperature != null) sensors.temp = data.temperature.toFixed(1) + '°C'
  if (data.humidity != null) sensors.hum = data.humidity.toFixed(1) + '%'
  if (data.soil_moisture != null) sensors.soil = data.soil_moisture.toFixed(1) + '%'
  if (data.water_level != null) sensors.water = data.water_level.toFixed(1) + '%'
  if (data.temp_tag != null) sensors.tempTag = data.temp_tag
  if (data.hum_tag != null) sensors.humTag = data.hum_tag
  if (data.soil_tag != null) sensors.soilTag = data.soil_tag
  if (data.water_tag != null) sensors.waterTag = data.water_tag
  if (data.co2 != null) sensors.co2 = data.co2 + ''
  if (data.co2_tag != null) sensors.co2Tag = data.co2_tag
  if (data.pump_status != null) devices.pump.state = data.pump_status
  if (data.fan_status != null) devices.fan.state = data.fan_status
  if (data.motor_status != null) devices.motor.state = data.motor_status
  if (data.flame_status != null) devices.flame.state = data.flame_status
  if (data.human_status != null) devices.human.state = data.human_status
}

function handleWeatherUpdate(data) {
  if (!data) return
  const fc = data.forecast || {}
  const decisions = data.recent_decisions || []
  // 如果用户手动选择了城市，保留中文名
  if (!weather.city || weather.city === '加载中...' || weather.city === '未知') {
    weather.city = fc.city || '未知'
    initCityFromServer(weather.city, fc.city_en || '')
  }
  const forecastListRaw = fc.forecast || []
  if (forecastListRaw.length > 0) {
    const cur = forecastListRaw[0]
    weather.temp = cur.temp !== undefined ? cur.temp.toFixed(1) + '°C' : '--'
    weather.desc = cur.weather || '--'
    weather.icon = getWeatherIcon(cur.weather_code)
    weather.hum = cur.humidity !== undefined ? cur.humidity + '%' : '--'
    weather.wind = cur.wind_speed !== undefined ? cur.wind_speed + 'm/s' : '--'
    weather.rain = cur.pop !== undefined ? (cur.pop * 100).toFixed(0) + '%' : '--'
    weather.pressure = cur.pressure !== undefined ? cur.pressure + 'hPa' : '--'
  }
  forecastList.value = forecastListRaw.slice(0, 8).map(f => ({
    time: f.time ? f.time.slice(5) : '',
    icon: getWeatherIcon(f.weather_code),
    temp: f.temp !== undefined ? f.temp.toFixed(0) + '°' : '--',
    rain: f.weather && (f.weather.includes('雨') || f.weather.includes('雪') || f.weather.includes('雷')),
    hot: f.temp_max !== undefined && f.temp_max > 35
  }))
  if (data.enabled !== undefined) {
    agent.badgeClass = data.enabled ? 'on' : 'off'
    agent.badgeText = data.enabled ? '运行中' : '已停用'
  } else if (decisions.length > 0) {
    agent.badgeClass = 'on'
    agent.badgeText = '运行中'
  }
  const levelIcons = { warning: '⚠️', danger: '🚨', info: '💡' }
  agent.decisions = decisions.slice().reverse().slice(0, 8).map(d => ({
    levelIcon: levelIcons[d.level] || '💡',
    time: d.time || '',
    action: d.action || '',
    reason: d.reason || ''
  }))
}

function getWeatherIcon(code) {
  if (!code && code !== 0) return '🌤️'
  // 从高到低判断，避免低范围码捕获所有高范围码
  if (code >= 800) {
    if (code === 800) return '☀️'    // 晴
    if (code === 801) return '🌤️'   // 少云
    return '☁️'                       // 多云/阴
  }
  if (code >= 700) return '🌫️'      // 雾/霾
  if (code >= 600) return '❄️'      // 雪
  if (code >= 500) return '🌧️'      // 雨
  if (code >= 300) return '🌦️'      // 毛毛雨
  if (code >= 200) return '⛈️'      // 雷暴
  return '☁️'
}

function onKeydown(e) {
  if (e.key === 'Escape') closeLightbox()
}

onMounted(async () => {
  socket.on('realtime_update', handleRealtimeUpdate)
  socket.on('weather_update', handleWeatherUpdate)
  socket.on('chart_update', updateCharts)
  socket.emit('request_weather')
  socket.emit('request_chart_data')
  // 初始渲染图表框架（无数据时显示空坐标轴）
  nextTick(renderCharts)
  fetchChartData()
  setInterval(fetchChartData, 30000)

  // 获取当前城市
  try {
    const res = await fetch('/api/weather/current_city')
    const data = await res.json()
    if (data.success && data.city) {
      weather.city = data.city
      initCityFromServer(data.city, data.city_en || '')
    }
  } catch {
    // 静默
  }

  // REST API 轮询回退：每15秒通过 API 获取天气和智能体数据
  // 当 Socket.IO 连接不可用时（如 Nginx 未代理 /socket.io/），此机制确保数据仍能显示
  fetchWeatherAgentData()
  weatherPollTimer = setInterval(fetchWeatherAgentData, 15000)

  document.addEventListener('keydown', onKeydown)
})

onUnmounted(() => {
  socket.off('realtime_update', handleRealtimeUpdate)
  socket.off('weather_update', handleWeatherUpdate)
  socket.off('chart_update', updateCharts)
  if (weatherPollTimer) {
    clearInterval(weatherPollTimer)
    weatherPollTimer = null
  }
  document.removeEventListener('keydown', onKeydown)
})
</script>

<style scoped>
.dashboard {
  display: grid;
  grid-template-columns: 22% 43% 35%;
  gap: 14px;
  height: calc(100vh - 52px - 32px);
  min-height: 0;
}

/* ===== 列通用 ===== */
.col-left, .col-center, .col-right {
  display: flex;
  flex-direction: column;
  gap: 14px;
  min-height: 0;
  overflow: hidden;
}

.col-left > .glow-card,
.col-center > .glow-card,
.col-right > .glow-card {
  flex-shrink: 0;
}

/* 左栏填充剩余空间 */
.col-left {
  overflow-y: auto;
}

/* ===== 迷你图表（双曲面图） ===== */
.mini-chart-card {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.mini-chart-row {
  display: flex;
  gap: 10px;
  flex: 1;
  min-height: 0;
}

.mini-chart-half {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.mini-chart-subtitle {
  font-size: 10px;
  color: rgba(200, 214, 229, 0.4);
  text-align: center;
  margin-bottom: 4px;
  letter-spacing: 0.3px;
}

.mini-chart-container {
  flex: 1;
  position: relative;
  min-height: 80px;
}

.mini-chart-container canvas {
  width: 100% !important;
  height: 100% !important;
}

/* ===== 左栏：传感器 ===== */
.sensor-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px;
}

.sensor-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  background: rgba(0, 255, 136, 0.03);
  border-radius: 8px;
  border: 1px solid rgba(0, 255, 136, 0.06);
}

.sensor-icon {
  font-size: 22px;
  width: 32px;
  text-align: center;
}

.sensor-info {
  flex: 1;
  min-width: 0;
}

.sensor-label {
  font-size: 11px;
  color: rgba(200, 214, 229, 0.5);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.sensor-val {
  font-size: 18px;
  font-weight: 700;
  color: #00ff88;
  font-family: 'Courier New', monospace;
}

.sensor-tag {
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 10px;
  font-weight: 600;
  white-space: nowrap;
}
.sensor-tag.normal { background: rgba(0, 255, 136, 0.12); color: #00ff88; }
.sensor-tag.warning { background: rgba(255, 165, 0, 0.15); color: #ffa500; }
.sensor-tag.danger { background: rgba(255, 71, 87, 0.15); color: #ff4757; }
.sensor-tag.high { background: rgba(255, 71, 87, 0.15); color: #ff4757; }
.sensor-tag.low { background: rgba(0, 212, 255, 0.12); color: #00d4ff; }

/* ===== 左栏：设备 ===== */
.device-grid {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 8px;
}

.device-item {
  text-align: center;
  padding: 12px 8px;
  background: rgba(0, 255, 136, 0.03);
  border-radius: 8px;
  border: 1px solid rgba(0, 255, 136, 0.06);
  transition: all 0.3s;
}

.device-item.active {
  background: rgba(0, 255, 136, 0.08);
  border-color: rgba(0, 255, 136, 0.25);
  box-shadow: 0 0 16px rgba(0, 255, 136, 0.06);
}

.device-icon {
  font-size: 26px;
  margin-bottom: 4px;
}

.device-name {
  font-size: 12px;
  color: rgba(200, 214, 229, 0.6);
  margin-bottom: 6px;
}

.device-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin: 0 auto;
  transition: all 0.3s;
}

.device-indicator.on {
  background: #00ff88;
  box-shadow: 0 0 8px rgba(0, 255, 136, 0.6);
}

.device-indicator.off {
  background: rgba(200, 214, 229, 0.15);
}

/* ===== 中栏：天气 ===== */
.weather-card .glow-card-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.weather-city {
  font-size: 13px;
  color: rgba(200, 214, 229, 0.5);
  font-weight: 400;
  text-transform: none;
  letter-spacing: 0;
}

.btn-city {
  font-size: 14px;
  padding: 2px 8px;
  background: rgba(0, 212, 255, 0.08);
  border-color: rgba(0, 212, 255, 0.15);
  color: #00d4ff;
}
.btn-city:hover {
  background: rgba(0, 212, 255, 0.2);
  border-color: rgba(0, 212, 255, 0.35);
}

.weather-main {
  display: flex;
  gap: 16px;
  margin-bottom: 10px;
}

.weather-temp-box {
  text-align: center;
  min-width: 100px;
}

.weather-temp {
  font-size: 36px;
  font-weight: 700;
  color: #00ff88;
  font-family: 'Courier New', monospace;
  line-height: 1;
}

.weather-icon-big {
  font-size: 36px;
  margin: 6px 0;
}

.weather-desc {
  font-size: 13px;
  color: rgba(200, 214, 229, 0.6);
}

.weather-detail-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px 16px;
  flex: 1;
  align-content: center;
}

.wd-item {
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.wd-label {
  font-size: 11px;
  color: rgba(200, 214, 229, 0.4);
}

.wd-val {
  font-size: 15px;
  font-weight: 600;
  color: #c8d6e5;
  font-family: 'Courier New', monospace;
}

/* 预报横条 */
.weather-forecast {
  display: flex;
  gap: 6px;
  padding-top: 10px;
  border-top: 1px solid rgba(0, 255, 136, 0.08);
}

.fc-item {
  flex: 1;
  text-align: center;
  padding: 6px 4px;
  border-radius: 8px;
  background: rgba(0, 255, 136, 0.03);
  border: 1px solid rgba(0, 255, 136, 0.06);
  transition: all 0.2s;
}

.fc-item.fc-rain {
  background: rgba(0, 150, 255, 0.08);
  border-color: rgba(0, 150, 255, 0.15);
}

.fc-item.fc-hot {
  background: rgba(255, 165, 0, 0.08);
  border-color: rgba(255, 165, 0, 0.15);
}

.fc-time {
  font-size: 10px;
  color: rgba(200, 214, 229, 0.4);
  margin-bottom: 2px;
}

.fc-icon {
  font-size: 18px;
  margin-bottom: 2px;
}

.fc-temp {
  font-size: 12px;
  font-weight: 600;
  color: #c8d6e5;
}

/* ===== 中栏：智能管家 ===== */
.agent-card {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.agent-badge {
  padding: 2px 10px;
  border-radius: 20px;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0;
  text-transform: none;
}
.agent-badge.on {
  background: rgba(0, 255, 136, 0.12);
  color: #00ff88;
  border: 1px solid rgba(0, 255, 136, 0.2);
}
.agent-badge.off {
  background: rgba(200, 214, 229, 0.06);
  color: rgba(200, 214, 229, 0.4);
  border: 1px solid rgba(200, 214, 229, 0.1);
}

.agent-count {
  font-size: 11px;
  color: rgba(200, 214, 229, 0.4);
  font-weight: 400;
  letter-spacing: 0;
  text-transform: none;
}

.agent-decisions {
  display: flex;
  flex-direction: column;
  gap: 3px;
  flex: 1;
  overflow-y: auto;
  min-height: 0;
}

.ad-item {
  display: flex;
  gap: 8px;
  padding: 5px 8px;
  font-size: 12px;
  border-radius: 6px;
  background: rgba(0, 255, 136, 0.02);
  align-items: flex-start;
  flex-wrap: wrap;
}

.ad-item:nth-child(odd) {
  background: rgba(0, 255, 136, 0.04);
}

.ad-level { font-size: 13px; flex-shrink: 0; }
.ad-time { color: rgba(200, 214, 229, 0.4); font-family: monospace; font-size: 11px; white-space: nowrap; flex-shrink: 0; }
.ad-action { font-weight: 600; color: #c8d6e5; flex-shrink: 0; font-size: 12px; }
.ad-reason { color: rgba(200, 214, 229, 0.5); flex: 1; font-size: 11px; }

.agent-empty {
  text-align: center;
  padding: 20px;
  color: rgba(200, 214, 229, 0.3);
  font-size: 13px;
}

/* 明天预测按钮 */
.btn-predict {
  font-size: 11px;
  padding: 3px 10px;
  background: rgba(0, 212, 255, 0.1);
  border-color: rgba(0, 212, 255, 0.2);
  color: #00d4ff;
  letter-spacing: 0;
  text-transform: none;
}
.btn-predict:hover {
  background: rgba(0, 212, 255, 0.2);
  border-color: rgba(0, 212, 255, 0.35);
}

/* ===== 作品线稿图预留区域 ===== */
.sketch-card {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.sketch-grid {
  flex: 1;
  display: flex;
  gap: 12px;
  min-height: 0;
}

.sketch-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.sketch-label {
  text-align: center;
  font-size: 13px;
  color: rgba(0, 255, 136, 0.8);
  margin-bottom: 6px;
  font-weight: 500;
  letter-spacing: 2px;
}

.sketch-image-wrapper {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  border-radius: 8px;
  background: rgba(0, 255, 136, 0.02);
  border: 1px solid rgba(0, 255, 136, 0.08);
  min-height: 80px;
}

.sketch-image {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
  border-radius: 6px;
  transition: transform 0.3s ease;
}

.sketch-image:hover {
  transform: scale(1.02);
}

.sketch-image-wrapper {
  cursor: pointer;
}

/* ===== 图片查看器（Lightbox） ===== */
.lightbox-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.85);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  animation: fadeIn 0.2s ease;
}

.lightbox-content {
  position: relative;
  max-width: 90vw;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.lightbox-close {
  position: absolute;
  top: -40px;
  right: 0;
  background: none;
  border: none;
  color: #fff;
  font-size: 32px;
  cursor: pointer;
  line-height: 1;
  opacity: 0.8;
  transition: opacity 0.2s;
}

.lightbox-close:hover {
  opacity: 1;
}

.lightbox-image {
  max-width: 90vw;
  max-height: 80vh;
  object-fit: contain;
  border-radius: 8px;
  box-shadow: 0 4px 30px rgba(0, 0, 0, 0.5);
}

.lightbox-label {
  margin-top: 12px;
  color: rgba(255, 255, 255, 0.8);
  font-size: 14px;
  letter-spacing: 2px;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

/* 内联预测结果 */
.agent-predict-inline {
  padding: 8px 10px;
  margin-bottom: 8px;
  background: rgba(0, 212, 255, 0.04);
  border: 1px solid rgba(0, 212, 255, 0.1);
  border-radius: 8px;
}

.api-summary {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 6px;
  flex-wrap: wrap;
}

.api-date {
  font-size: 11px;
  font-weight: 600;
  color: rgba(200, 214, 229, 0.5);
  font-family: monospace;
}

.api-temp {
  font-size: 15px;
  font-weight: 700;
  color: #00ff88;
  font-family: 'Courier New', monospace;
}
.api-temp.hot { color: #ff6b6b; }
.api-temp.cold { color: #00d4ff; }

.api-weather {
  font-size: 12px;
  color: rgba(200, 214, 229, 0.6);
}

.api-rain {
  font-size: 11px;
  color: #4fc3f7;
  padding: 1px 8px;
  background: rgba(79, 195, 247, 0.1);
  border-radius: 8px;
}

.api-suggestions {
  display: flex;
  flex-direction: column;
  gap: 3px;
  margin-bottom: 6px;
}

.api-sg {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #c8d6e5;
  padding: 3px 6px;
  background: rgba(0, 255, 136, 0.02);
  border-radius: 4px;
}

.api-sg-reason {
  font-size: 10px;
  color: rgba(200, 214, 229, 0.35);
  flex: 1;
}

.api-goto {
  text-align: right;
}

.api-goto .btn {
  font-size: 10px;
  padding: 2px 10px;
  color: #00d4ff;
  border-color: rgba(0, 212, 255, 0.2);
  background: rgba(0, 212, 255, 0.06);
  text-decoration: none;
}

.agent-predict-loading {
  padding: 8px 10px;
  margin-bottom: 8px;
  font-size: 12px;
  color: rgba(200, 214, 229, 0.4);
  text-align: center;
}

/* ===== 右栏：AI 聊天 ===== */
.chat-card {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  max-height: 55%;
}

/* ===== 监控画面 ===== */
.monitor-card {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.monitor-container {
  flex: 1;
  position: relative;
  overflow: hidden;
  border-radius: 8px;
  background: #000;
}

.monitor-iframe {
  width: 100%;
  height: 100%;
  border: none;
}

.monitor-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.6);
  z-index: 1;
}

.monitor-loading-text {
  color: rgba(0, 255, 136, 0.8);
  font-size: 14px;
  letter-spacing: 1px;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 8px 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-height: 0;
}

.msg {
  display: flex;
  gap: 8px;
  max-width: 90%;
}

.msg-ai { align-self: flex-start; }
.msg-ai + .msg-user { margin-top: 4px; }

.msg-avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  flex-shrink: 0;
  background: rgba(0, 255, 136, 0.08);
  border: 1px solid rgba(0, 255, 136, 0.1);
}

.msg-content {
  background: rgba(0, 255, 136, 0.04);
  border: 1px solid rgba(0, 255, 136, 0.08);
  border-radius: 8px;
  padding: 8px 12px;
  min-width: 0;
}

.msg-user .msg-content {
  background: rgba(0, 212, 255, 0.06);
  border-color: rgba(0, 212, 255, 0.12);
}

.msg-text {
  font-size: 13px;
  color: #c8d6e5;
  line-height: 1.5;
  word-break: break-word;
}

.msg-time {
  font-size: 10px;
  color: rgba(200, 214, 229, 0.3);
  margin-top: 4px;
}

/* 打字动画 */
.msg-typing {
  display: flex;
  gap: 4px;
  padding: 12px 16px;
  align-self: flex-start;
  background: rgba(0, 255, 136, 0.04);
  border-radius: 20px;
  border: 1px solid rgba(0, 255, 136, 0.08);
}

.typing-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: rgba(0, 255, 136, 0.4);
  animation: typingBounce 1.4s infinite ease-in-out;
}

.typing-dot:nth-child(2) { animation-delay: 0.2s; }
.typing-dot:nth-child(3) { animation-delay: 0.4s; }

@keyframes typingBounce {
  0%, 80%, 100% { transform: scale(0.6); }
  40% { transform: scale(1); }
}

/* 聊天输入 */
.chat-input-row {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding-top: 10px;
  border-top: 1px solid rgba(0, 255, 136, 0.08);
  margin-top: auto;
}

.quick-questions {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}

.qq-btn {
  padding: 4px 10px;
  font-size: 11px;
  background: rgba(0, 255, 136, 0.06);
  border: 1px solid rgba(0, 255, 136, 0.1);
  border-radius: 12px;
  color: rgba(200, 214, 229, 0.6);
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
}

.qq-btn:hover {
  background: rgba(0, 255, 136, 0.12);
  border-color: rgba(0, 255, 136, 0.25);
  color: #00ff88;
}

.chat-input-bar {
  display: flex;
  gap: 8px;
}

.chat-input {
  flex: 1;
  padding: 8px 12px;
  background: rgba(0, 255, 136, 0.04);
  border: 1px solid rgba(0, 255, 136, 0.12);
  border-radius: 8px;
  font-size: 13px;
  color: #c8d6e5;
  outline: none;
  transition: border-color 0.2s;
}

.chat-input:focus {
  border-color: rgba(0, 255, 136, 0.3);
}

.chat-input::placeholder {
  color: rgba(200, 214, 229, 0.3);
}

.chat-input-row .btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

/* ===== Responsive ===== */
@media (max-width: 1100px) {
  .dashboard {
    grid-template-columns: 1fr 1fr;
    height: auto;
  }
  .col-right {
    grid-column: 1 / -1;
  }
}

@media (max-width: 768px) {
  .dashboard {
    grid-template-columns: 1fr;
  }
}
</style>

<!-- 手机模式全局样式 -->
<style>
/* 手机模式下首页布局调整 */
.mobile-mode .dashboard {
  display: flex;
  flex-direction: column;
  gap: 10px;
  height: auto;
  min-height: 0;
}

.mobile-mode .col-left,
.mobile-mode .col-center,
.mobile-mode .col-right {
  width: 100%;
  overflow: visible;
}

.mobile-mode .sensor-grid {
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.mobile-mode .sensor-item {
  padding: 10px;
}

.mobile-mode .sensor-val {
  font-size: 16px;
}

.mobile-mode .device-grid {
  gap: 8px;
}

.mobile-mode .device-item {
  padding: 10px;
}

.mobile-mode .device-name {
  font-size: 13px;
}

.mobile-mode .mini-chart-row {
  flex-direction: column;
}

.mobile-mode .weather-main {
  flex-direction: column;
  align-items: flex-start;
  gap: 10px;
}

.mobile-mode .weather-temp-box {
  flex-direction: row;
  align-items: center;
  gap: 10px;
  width: 100%;
}

.mobile-mode .weather-temp {
  font-size: 28px;
}

.mobile-mode .weather-icon-big {
  font-size: 36px;
}

.mobile-mode .weather-detail-grid {
  grid-template-columns: 1fr 1fr;
  gap: 6px;
}

.mobile-mode .weather-forecast {
  gap: 4px;
  overflow-x: auto;
}

.mobile-mode .fc-item {
  min-width: 58px;
  padding: 6px 4px;
}

.mobile-mode .agent-decisions {
  max-height: 200px;
}

.mobile-mode .ad-item {
  flex-wrap: wrap;
  gap: 4px;
  padding: 6px 0;
}

.mobile-mode .chat-card {
  max-height: 300px;
}

.mobile-mode .chat-messages {
  max-height: 180px;
}

.mobile-mode .quick-questions {
  flex-wrap: wrap;
  gap: 4px;
}

.mobile-mode .qq-btn {
  font-size: 11px;
  padding: 4px 8px;
}

.mobile-mode .monitor-card {
  min-height: 200px;
}

.mobile-mode .glow-card {
  padding: 12px;
}

.mobile-mode .glow-card-title {
  font-size: 12px;
  margin-bottom: 8px;
}

.mobile-mode .btn-sm {
  padding: 4px 8px;
  font-size: 11px;
}

.mobile-mode .agent-predict-inline {
  padding: 8px;
}

.mobile-mode .api-summary {
  flex-wrap: wrap;
  gap: 6px;
}

.mobile-mode .sketch-card {
  min-height: 80px;
}

.mobile-mode .sketch-grid {
  gap: 8px;
}

.mobile-mode .sketch-item {
  min-height: 0;
}

.mobile-mode .sketch-label {
  font-size: 11px;
  margin-bottom: 4px;
}

.mobile-mode .sketch-image-wrapper {
  min-height: 50px;
  padding: 4px;
}
</style>