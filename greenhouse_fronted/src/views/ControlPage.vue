<template>
  <div class="control-page">
    <!-- 🌤️ 天气预测与建议 -->
    <div class="section">
      <h2 class="section-title">🌤️ 天气预测与建议</h2>
      <div class="weather-predict card">
        <div class="predict-header">
          <button class="btn" @click="predictTomorrow" :disabled="predictLoading">
            🔮 {{ predictResult ? '收起预测' : '预测明天天气' }}
          </button>
          <button class="btn btn-sm btn-city" @click="showCityMap = true" title="切换城市">🗺️ {{ sharedCity.name }}</button>
          <span class="predict-date" v-if="predictResult">{{ predictResult.tomorrow.date }}</span>
          <span class="predict-hint" v-if="!predictResult && !predictLoading">点击按钮，智能分析明天天气并给出设备控制建议</span>
        </div>

        <!-- 城市选择地图（可视化中国地图） -->
        <ChinaMapV2
          v-if="showCityMap"
          :currentCity="sharedCity.name"
          @close="showCityMap = false"
          @select="onCitySelect"
        />

        <div v-if="predictLoading" class="predict-loading">
          <span class="loading-dot"></span>
          <span class="loading-dot"></span>
          <span class="loading-dot"></span>
          <span class="loading-text">正在分析天气预报...</span>
        </div>

        <div v-if="predictResult" class="predict-result">
          <!-- 明天天气概览 -->
          <div class="tomorrow-overview">
            <div class="to-item">
              <span class="to-icon">🌡️</span>
              <div class="to-info">
                <span class="to-label">最高温</span>
                <span class="to-val hot">{{ predictResult.tomorrow.max_temp }}°C</span>
              </div>
            </div>
            <div class="to-item">
              <span class="to-icon">🌡️</span>
              <div class="to-info">
                <span class="to-label">最低温</span>
                <span class="to-val cold">{{ predictResult.tomorrow.min_temp }}°C</span>
              </div>
            </div>
            <div class="to-item">
              <span class="to-icon">💧</span>
              <div class="to-info">
                <span class="to-label">平均湿度</span>
                <span class="to-val">{{ predictResult.tomorrow.avg_hum }}%</span>
              </div>
            </div>
            <div class="to-item">
              <span class="to-icon">🌤️</span>
              <div class="to-info">
                <span class="to-label">天气状况</span>
                <span class="to-val" :class="{rainy: predictResult.tomorrow.has_rain}">
                  {{ predictResult.tomorrow.weather_desc }}
                </span>
              </div>
            </div>
          </div>

          <!-- 建议列表 -->
          <div class="suggestions-list">
            <div class="sg-item" v-for="(sg, i) in predictResult.suggestions" :key="i">
              <div class="sg-left">
                <span class="sg-icon">{{ sg.icon }}</span>
              </div>
              <div class="sg-body">
                <div class="sg-suggestion">{{ sg.suggestion }}</div>
                <div class="sg-reason">{{ sg.reason }}</div>
              </div>
              <div class="sg-actions" v-if="sg.commands.length > 0">
                <button
                  v-for="(cmd, ci) in sg.commands"
                  :key="ci"
                  class="btn btn-sm btn-apply"
                  @click="applySuggestion(cmd, sg)"
                >
                  📤 {{ cmd.label }}
                </button>
              </div>
            </div>
          </div>
        </div>

        <div v-if="predictError" class="predict-error">{{ predictError }}</div>
      </div>
    </div>

    <!-- 指令日志 -->
    <div class="section">
      <h2 class="section-title">📋 指令日志</h2>
      <div class="cmd-log card">
        <div class="cmd-log-list" v-if="cmdLogs.length > 0">
          <div class="cmd-item" v-for="(log, i) in cmdLogs" :key="i">
            <span class="cmd-time">{{ log.time }}</span>
            <span class="cmd-type" :class="log.type">{{ log.typeLabel }}</span>
            <span class="cmd-desc">{{ log.desc }}</span>
          </div>
        </div>
        <div class="cmd-empty" v-else>暂无指令记录，操作设备或设置阈值后将显示在此处</div>
      </div>
    </div>

    <!-- 设备控制 -->
    <div class="section">
      <h2 class="section-title">⚙️ 设备控制</h2>
      <div class="device-horizontal">
        <div class="control-card card" v-for="device in deviceList" :key="device.key">
          <div class="device-icon">{{ device.icon }}</div>
          <div class="device-name">{{ device.label }}</div>
          <div class="toggle-wrapper">
            <label class="toggle-switch">
              <input
                type="checkbox"
                :checked="deviceStatus[device.key]"
                @change="toggleDevice(device.key)"
              />
              <span class="toggle-slider"></span>
            </label>
            <span :class="deviceStatus[device.key] ? 'status-on' : 'status-off'">
              {{ deviceStatus[device.key] ? (deviceAutoMode[device.key] ? '自动' : '已开启') : '已关闭' }}
            </span>
            <button class="btn btn-sm btn-auto" @click="setDeviceAuto(device.key)" :title="'切换' + device.label + '为自动模式'" v-if="device.key !== 'flame' && device.key !== 'human'">
              🔄 自动
            </button>
          </div>
        </div>
        <!-- 一键自动卡片 -->
        <div class="control-card card all-auto-card" @click="setAllAuto">
          <div class="all-auto-label">一键自动</div>
          <div class="all-auto-sub" v-if="!allAutoLoading">全部切换自动模式</div>
          <div class="all-auto-sub loading" v-else>正在设置...</div>
        </div>
      </div>
    </div>

    <!-- 阈值设置 -->
    <div class="section">
      <h2 class="section-title">🎯 阈值设置</h2>
      <div class="threshold-grid">
        <div class="threshold-card card" v-for="item in thresholdList" :key="item.key">
          <div class="threshold-header">
            <span class="threshold-icon">{{ item.icon }}</span>
            <span class="threshold-label">{{ item.label }}</span>
          </div>
          <div class="threshold-value-row">
            <span class="threshold-num">{{ thresholdValues[item.key] ?? item.default }}</span>
            <span class="threshold-unit">{{ item.unit }}</span>
          </div>
          <div class="slider-wrapper">
            <input
              type="range"
              class="t-slider"
              :min="item.min"
              :max="item.max"
              :step="item.step"
              :value="thresholdValues[item.key] ?? item.default"
              @input="onThresholdInput(item.key, $event)"
            />
          </div>
          <div class="threshold-actions">
            <button class="btn btn-primary btn-sm" @click="sendThreshold(item.key)">
              📤 发送
            </button>
            <button class="btn btn-secondary btn-sm" @click="resetThreshold(item.key, item.default)">
              ↩️ 重置
            </button>
            <button class="btn btn-sm btn-query" @click="queryThreshold(item.key)">
              🔍 查询
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref, onMounted, onUnmounted } from 'vue'
import socket from '../utils/socket.js'
import ChinaMapV2 from '../components/ChinaMapV2.vue'
import { sharedCity, updateCity } from '../stores/sharedCity.js'

const deviceList = [
  { key: 'pump', label: '水泵', icon: '🚰' },
  { key: 'fan', label: '风扇', icon: '🌀' },
  { key: 'motor', label: '舵机', icon: '🔄' },
  { key: 'flame', label: '火焰警报', icon: '🔥' },
  { key: 'human', label: '安防警报', icon: '🚨' }
]

const deviceStatus = reactive({
  pump: true,    // 默认自动（与 Arduino pumpManual=false 一致）
  fan: true,     // 默认自动（与 Arduino fanManualOverride=false 一致）
  motor: false,  // 默认手动（与 Arduino servoAutoMode=false 一致）
  flame: true,   // 默认自动（与 Arduino flameBeepMode=BEEP_AUTO 一致）
  human: true    // 默认自动（与 Arduino humanBeepMode=BEEP_AUTO 一致）
})

// 设备是否处于自动模式（用于区分"自动"和"已开启"的显示）
const deviceAutoMode = reactive({
  pump: true,
  fan: true,
  motor: false,
  flame: true,
  human: true
})

const allAutoLoading = ref(false)

const thresholdList = [
  { key: 'temp', label: '温度', icon: '🌡️', unit: '°C', min: 0, max: 60, step: 0.5, default: 30 },
  { key: 'humidity', label: '湿度', icon: '💧', unit: '%', min: 0, max: 100, step: 1, default: 80 },
  { key: 'soil', label: '土壤湿度', icon: '🌱', unit: '%', min: 0, max: 100, step: 1, default: 60 },
  { key: 'water', label: '水位', icon: '💦', unit: '%', min: 0, max: 100, step: 1, default: 20 },
  { key: 'co2', label: 'CO2 浓度', icon: '🫁', unit: 'ppm', min: 0, max: 2000, step: 10, default: 700 }
]

const thresholdValues = reactive({})

// ===== 天气预测与建议 =====
const predictLoading = ref(false)
const predictResult = ref(null)
const predictError = ref('')
const showCityMap = ref(false)

async function onCitySelect({ province, city, cityEn }) {
  showCityMap.value = false
  updateCity(city, cityEn)
  try {
    await fetch('/api/weather/set_city', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ city: cityEn })
    })
  } catch {
    // 静默
  }
}

async function predictTomorrow() {
  // 如果已显示预测结果，再次点击则收起
  if (predictResult.value) {
    predictResult.value = null
    return
  }
  predictLoading.value = true
  predictResult.value = null
  predictError.value = ''
  try {
    const res = await fetch('/api/weather/tomorrow_suggestions')
    const data = await res.json()
    if (data.success) {
      predictResult.value = data
    } else {
      predictError.value = data.error || '预测失败，请稍后重试'
    }
  } catch (e) {
    predictError.value = '网络请求失败，请检查服务器连接'
  }
  predictLoading.value = false
}

async function applySuggestion(cmd, sg) {
  try {
    if (cmd.type === 'threshold') {
      // 阈值调整建议 → 调用阈值API
      const res = await fetch('/api/threshold/set', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ type: cmd.sensorType, value: cmd.value })
      })
      const data = await res.json()
      if (data.success) {
        addCmdLog('threshold', `[天气建议] ${cmd.label}`)
        // 同步更新本地阈值显示
        const keyMap = { soil: 'soil', temp: 'temp', hum: 'humidity', water: 'water', co2: 'co2' }
        const localKey = keyMap[cmd.sensorType] || cmd.sensorType
        if (thresholdValues[localKey] !== undefined) {
          thresholdValues[localKey] = cmd.value
        }
      } else {
        addCmdLog('threshold', `[天气建议] 执行失败: ${data.error}`)
      }
    } else {
      // 设备控制建议
      const res = await fetch('/api/device/control', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ device: cmd.device, action: cmd.action })
      })
      const data = await res.json()
      if (data.success) {
        // 更新本地设备状态
        deviceStatus[cmd.device] = cmd.action === 'on'
        addCmdLog('device', `[天气建议] ${cmd.label}`)
      } else {
        addCmdLog('device', `[天气建议] 执行失败: ${data.error}`)
      }
    }
  } catch (e) {
    addCmdLog('device', `[天气建议] 请求失败: ${e.message}`)
  }
}

// ===== 指令日志 =====
const cmdLogs = ref([])
const MAX_LOGS = 20

function addCmdLog(type, desc) {
  const now = new Date()
  const time = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}:${String(now.getSeconds()).padStart(2, '0')}`
  const typeMap = {
    device: { typeLabel: '设备', cls: 'device' },
    threshold: { typeLabel: '阈值', cls: 'threshold' }
  }
  const info = typeMap[type] || typeMap.device
  cmdLogs.value.unshift({
    time,
    type: info.cls,
    typeLabel: info.typeLabel,
    desc
  })
  if (cmdLogs.value.length > MAX_LOGS) {
    cmdLogs.value = cmdLogs.value.slice(0, MAX_LOGS)
  }
}

// ===== 设备控制 =====
function toggleDevice(device) {
  const current = deviceStatus[device]
  const isAlarm = device === 'flame' || device === 'human'
  // 警报设备：左=关闭(off)，右=自动(auto)；普通设备：左=关闭(off)，右=开启(on)
  const action = current ? 'off' : (isAlarm ? 'auto' : 'on')
  const labelMap = { pump: '水泵', fan: '风扇', motor: '舵机', flame: '火焰警报', human: '安防警报' }

  fetch('/api/device/control', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ device, action })
  })
    .then(res => res.json())
    .then(data => {
      if (data.success) {
        deviceStatus[device] = !current
        // 警报设备：auto 模式时标记为自动；普通设备：手动操作退出自动模式
        if (isAlarm) {
          deviceAutoMode[device] = (action === 'auto')
        } else {
          deviceAutoMode[device] = false
        }
        const actionText = isAlarm ? (action === 'auto' ? '自动' : '关闭') : (action === 'on' ? '开启' : '关闭')
        addCmdLog('device', `${labelMap[device] || device} → ${actionText}`)
      } else {
        addCmdLog('device', `${labelMap[device] || device} 操作失败: ${data.error || '未知错误'}`)
      }
    })
    .catch(() => {
      deviceStatus[device] = !current
      if (isAlarm) {
        deviceAutoMode[device] = (action === 'auto')
      }
      const actionText = isAlarm ? (action === 'auto' ? '自动' : '关闭') : (action === 'on' ? '开启' : '关闭')
      addCmdLog('device', `${labelMap[device] || device} → ${actionText}`)
    })
}

function setDeviceAuto(device) {
  const labelMap = { pump: '水泵', fan: '风扇', motor: '舵机' }
  fetch('/api/device/control', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ device, action: 'auto' })
  })
    .then(res => res.json())
    .then(data => {
      if (data.success) {
        deviceStatus[device] = true
        deviceAutoMode[device] = true
        addCmdLog('device', `${labelMap[device] || device} → 启动自动工作模式`)
      } else {
        addCmdLog('device', `${labelMap[device] || device} 自动模式设置失败`)
      }
    })
    .catch(() => {
      deviceStatus[device] = true
      deviceAutoMode[device] = true
      addCmdLog('device', `${labelMap[device] || device} → 启动自动工作模式`)
    })
}

function setAllAuto() {
  allAutoLoading.value = true
  addCmdLog('device', '🤖 一键自动：设置全部设备为自动模式')

  const promises = deviceList.map(device => {
    return fetch('/api/device/control', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ device: device.key, action: 'auto' })
    })
      .then(res => res.json())
      .then(data => {
        if (data.success) {
          deviceStatus[device.key] = true
          deviceAutoMode[device.key] = true
        }
      })
      .catch(() => {
        deviceStatus[device.key] = true
        deviceAutoMode[device.key] = true
      })
  })

  Promise.all(promises).then(() => {
    allAutoLoading.value = false
    addCmdLog('device', '✅ 全部设备已切换为自动模式')
  })
}

function onThresholdInput(key, event) {
  thresholdValues[key] = Number(event.target.value)
}

function sendThreshold(key) {
  const value = thresholdValues[key]
  if (value === undefined || value === null) return
  const labelMap = { temp: '温度', humidity: '湿度', soil: '土壤湿度', water: '水位', co2: 'CO2' }
  // 后端 type 映射：humidity → hum
  const typeMap = { temp: 'temp', humidity: 'hum', soil: 'soil', water: 'water', co2: 'co2' }
  const type = typeMap[key] || key

  fetch('/api/threshold/set', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ type, value })
  })
    .then(res => res.json())
    .then(data => {
      if (data.success) {
        addCmdLog('threshold', `${labelMap[key] || key} 阈值 → ${value}`)
      }
    })
    .catch(() => {
      addCmdLog('threshold', `${labelMap[key] || key} 阈值 → ${value}`)
    })
}

function resetThreshold(key, defaultVal) {
  thresholdValues[key] = defaultVal
}

function queryThreshold(key) {
  const labelMap = { temp: '温度', humidity: '湿度', soil: '土壤湿度', water: '水位', co2: 'CO2' }
  // 后端 type 映射：humidity → hum
  const typeMap = { temp: 'temp', humidity: 'hum', soil: 'soil', water: 'water', co2: 'co2' }
  const type = typeMap[key] || key

  fetch('/api/threshold/query', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ type })
  })
    .then(res => res.json())
    .then(data => {
      if (data.success && data.message) {
        addCmdLog('threshold', data.message)
      } else {
        addCmdLog('threshold', `查询失败: ${data.error || '未知错误'}`)
      }
    })
    .catch(() => {
      addCmdLog('threshold', `查询请求失败: ${labelMap[key] || key}`)
    })
}

onMounted(() => {
  thresholdList.forEach(item => {
    thresholdValues[item.key] = item.default
  })
})

onUnmounted(() => {
})
</script>

<style scoped>
.control-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
  height: 100%;
  min-height: 0;
  overflow-y: auto;
  padding-right: 4px;
}

/* ========== 天气预测与建议 ========== */
.weather-predict {
  padding: 12px 14px;
}

.predict-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 10px;
}

.predict-date {
  font-size: 13px;
  font-weight: 600;
  color: #00ff88;
  padding: 2px 10px;
  background: rgba(0, 255, 136, 0.08);
  border-radius: 10px;
  border: 1px solid rgba(0, 255, 136, 0.15);
}

.predict-hint {
  font-size: 12px;
  color: rgba(200, 214, 229, 0.35);
  font-style: italic;
}

/* 加载动画 */
.predict-loading {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 12px 0;
}

.loading-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #00ff88;
  animation: loadingBounce 1.4s infinite ease-in-out;
}

.loading-dot:nth-child(2) { animation-delay: 0.2s; }
.loading-dot:nth-child(3) { animation-delay: 0.4s; }

.loading-text {
  font-size: 12px;
  color: rgba(200, 214, 229, 0.5);
  margin-left: 8px;
}

@keyframes loadingBounce {
  0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; }
  40% { transform: scale(1); opacity: 1; }
}

/* 明天天气概览 */
.tomorrow-overview {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
  margin-bottom: 12px;
  padding: 10px;
  background: rgba(0, 255, 136, 0.03);
  border-radius: 8px;
  border: 1px solid rgba(0, 255, 136, 0.06);
}

.to-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.to-icon {
  font-size: 20px;
  flex-shrink: 0;
}

.to-info {
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.to-label {
  font-size: 10px;
  color: rgba(200, 214, 229, 0.4);
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

.to-val {
  font-size: 15px;
  font-weight: 700;
  color: #c8d6e5;
  font-family: 'Courier New', monospace;
}

.to-val.hot { color: #ff6b6b; }
.to-val.cold { color: #00d4ff; }
.to-val.rainy { color: #4fc3f7; }

/* 建议列表 */
.suggestions-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.sg-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  background: rgba(0, 255, 136, 0.03);
  border-radius: 8px;
  border: 1px solid rgba(0, 255, 136, 0.06);
  transition: all 0.2s;
}

.sg-item:hover {
  background: rgba(0, 255, 136, 0.06);
  border-color: rgba(0, 255, 136, 0.15);
}

.sg-left {
  flex-shrink: 0;
}

.sg-icon {
  font-size: 22px;
}

.sg-body {
  flex: 1;
  min-width: 0;
}

.sg-suggestion {
  font-size: 13px;
  font-weight: 600;
  color: #c8d6e5;
  margin-bottom: 2px;
}

.sg-reason {
  font-size: 11px;
  color: rgba(200, 214, 229, 0.4);
}

.sg-actions {
  display: flex;
  gap: 6px;
  flex-shrink: 0;
}

.btn-apply {
  background: rgba(0, 212, 255, 0.12);
  border-color: rgba(0, 212, 255, 0.25);
  color: #00d4ff;
  font-size: 11px;
  padding: 4px 10px;
  white-space: nowrap;
}

.btn-apply:hover {
  background: rgba(0, 212, 255, 0.25);
  border-color: rgba(0, 212, 255, 0.4);
  box-shadow: 0 0 12px rgba(0, 212, 255, 0.15);
}

.btn-city {
  font-size: 12px;
  padding: 3px 10px;
  background: rgba(0, 212, 255, 0.08);
  border-color: rgba(0, 212, 255, 0.15);
  color: #00d4ff;
  white-space: nowrap;
}
.btn-city:hover {
  background: rgba(0, 212, 255, 0.2);
  border-color: rgba(0, 212, 255, 0.35);
}

.predict-error {
  padding: 10px;
  font-size: 12px;
  color: #ff6b6b;
  background: rgba(255, 107, 107, 0.08);
  border-radius: 8px;
  border: 1px solid rgba(255, 107, 107, 0.15);
  text-align: center;
}

@media (max-width: 768px) {
  .tomorrow-overview {
    grid-template-columns: repeat(2, 1fr);
  }
  .sg-item {
    flex-wrap: wrap;
  }
  .sg-actions {
    width: 100%;
    justify-content: flex-end;
  }
}

.section {
  width: 100%;
  flex-shrink: 0;
  min-height: 0;
}

/* ========== 指令日志 ========== */
.cmd-log {
  max-height: 90px;
  overflow-y: auto;
  padding: 6px 10px;
}

.cmd-log-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.cmd-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 3px 8px;
  font-size: 11px;
  border-radius: 4px;
  background: rgba(0, 255, 136, 0.02);
}

.cmd-item:nth-child(odd) {
  background: rgba(0, 255, 136, 0.04);
}

.cmd-time {
  font-family: 'Courier New', monospace;
  font-size: 10px;
  color: rgba(200, 214, 229, 0.35);
  white-space: nowrap;
  flex-shrink: 0;
}

.cmd-type {
  padding: 1px 6px;
  border-radius: 10px;
  font-size: 9px;
  font-weight: 600;
  white-space: nowrap;
  flex-shrink: 0;
}

.cmd-type.device {
  background: rgba(0, 212, 255, 0.12);
  color: #00d4ff;
}

.cmd-type.threshold {
  background: rgba(255, 165, 0, 0.12);
  color: #ffa500;
}

.cmd-desc {
  color: rgba(200, 214, 229, 0.6);
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.cmd-empty {
  text-align: center;
  padding: 10px;
  color: rgba(200, 214, 229, 0.3);
  font-size: 12px;
}

/* ========== Device Control Cards ========== */
.device-horizontal {
  display: flex;
  gap: 12px;
  width: 100%;
}

.control-card {
  flex: 1;
  min-width: 0;
  text-align: center;
  padding: 14px 12px;
}

.control-card .device-icon {
  font-size: 30px;
  margin-bottom: 4px;
}

.control-card .device-name {
  font-size: 13px;
  font-weight: 600;
  color: #c8d6e5;
  margin-bottom: 10px;
}

.toggle-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
}

/* Toggle Switch */
.toggle-switch {
  position: relative;
  display: inline-block;
  width: 48px;
  height: 24px;
  cursor: pointer;
}

.toggle-switch input {
  opacity: 0;
  width: 0;
  height: 0;
}

.toggle-slider {
  position: absolute;
  inset: 0;
  background: rgba(200, 214, 229, 0.15);
  border-radius: 24px;
  transition: background 0.3s;
}

.toggle-slider::before {
  content: '';
  position: absolute;
  width: 18px;
  height: 18px;
  left: 3px;
  bottom: 3px;
  background: #fff;
  border-radius: 50%;
  transition: transform 0.3s;
  box-shadow: 0 1px 4px rgba(0,0,0,0.2);
}

.toggle-switch input:checked + .toggle-slider {
  background: #27ae60;
}

.toggle-switch input:checked + .toggle-slider::before {
  transform: translateX(24px);
}

/* ========== Threshold Cards ========== */
.threshold-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  max-width: 780px;
  margin: 0 auto;
}

.threshold-card {
  text-align: center;
  padding: 12px 10px;
}

.threshold-header {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  margin-bottom: 4px;
}

.threshold-icon {
  font-size: 18px;
}

.threshold-label {
  font-size: 13px;
  font-weight: 600;
  color: #c8d6e5;
}

.threshold-value-row {
  margin-bottom: 6px;
}

.threshold-num {
  font-size: 22px;
  font-weight: 700;
  color: #00ff88;
  font-family: 'Courier New', monospace;
}

.threshold-unit {
  font-size: 12px;
  color: rgba(200, 214, 229, 0.4);
  margin-left: 4px;
}

.slider-wrapper {
  padding: 0 2px;
  margin-bottom: 8px;
}

.t-slider {
  width: 100%;
  height: 5px;
  -webkit-appearance: none;
  appearance: none;
  background: rgba(0, 255, 136, 0.12);
  border-radius: 3px;
  outline: none;
  cursor: pointer;
}

.t-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #00ff88;
  cursor: pointer;
  transition: transform 0.2s;
  box-shadow: 0 0 8px rgba(0, 255, 136, 0.3);
}

.t-slider::-webkit-slider-thumb:hover {
  transform: scale(1.15);
}

.t-slider::-moz-range-thumb {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #00ff88;
  cursor: pointer;
  border: none;
}

.threshold-actions {
  display: flex;
  gap: 6px;
  justify-content: center;
}

.threshold-actions .btn {
  padding: 4px 10px;
  font-size: 11px;
}

@media (max-width: 768px) {
  .threshold-grid {
    grid-template-columns: 1fr;
    max-width: 100%;
  }
  .device-horizontal {
    flex-direction: column;
  }
}

.btn-auto {
  font-size: 11px;
  padding: 3px 8px;
  background: rgba(0, 212, 255, 0.1);
  border-color: rgba(0, 212, 255, 0.2);
  color: #00d4ff;
}
.btn-auto:hover {
  background: rgba(0, 212, 255, 0.2);
  border-color: rgba(0, 212, 255, 0.35);
}

.all-auto-card {
  cursor: pointer;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.15) 0%, rgba(118, 75, 162, 0.15) 100%);
  border: 1px dashed rgba(102, 126, 234, 0.3);
  transition: all 0.3s ease;
  min-height: 120px;
  user-select: none;
}
.all-auto-card:hover {
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.25) 0%, rgba(118, 75, 162, 0.25) 100%);
  border-color: rgba(102, 126, 234, 0.5);
  transform: translateY(-2px);
}
.all-auto-card .all-auto-icon-wrap {
  font-size: 30px;
  line-height: 1;
}
.all-auto-card .all-auto-label {
  font-size: 13px;
  font-weight: 600;
  color: #c8d6e5;
}
.all-auto-card .all-auto-sub {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.4);
}
.all-auto-card .all-auto-sub.loading {
  color: #00d4ff;
}
.btn-query {
  font-size: 11px;
  padding: 3px 8px;
  background: rgba(255, 193, 7, 0.1);
  border-color: rgba(255, 193, 7, 0.2);
  color: #ffc107;
}
.btn-query:hover {
  background: rgba(255, 193, 7, 0.2);
  border-color: rgba(255, 193, 7, 0.35);
}
</style>

<!-- 手机模式全局样式 -->
<style>
.mobile-mode .control-page {
  padding: 0;
  height: auto;
  overflow: visible;
}

.mobile-mode .control-page .section {
  margin-bottom: 10px;
}

.mobile-mode .control-page .section-title {
  font-size: 14px;
  margin-bottom: 8px;
}

.mobile-mode .control-page .sections-row {
  grid-template-columns: 1fr;
  gap: 10px;
}

.mobile-mode .predict-header {
  flex-wrap: wrap;
  gap: 6px;
}

.mobile-mode .predict-header .btn {
  font-size: 12px;
  padding: 6px 12px;
}

.mobile-mode .tomorrow-overview {
  grid-template-columns: 1fr 1fr;
  gap: 6px;
}

.mobile-mode .to-item {
  padding: 8px;
}

.mobile-mode .to-val {
  font-size: 16px;
}

.mobile-mode .sg-item {
  flex-direction: column;
  align-items: flex-start;
  gap: 8px;
  padding: 10px;
}

.mobile-mode .sg-actions {
  width: 100%;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.mobile-mode .sg-actions .btn {
  flex: 1;
  min-width: 0;
  font-size: 11px;
  padding: 6px 8px;
}

.mobile-mode .device-horizontal {
  flex-direction: column;
  gap: 8px;
}

.mobile-mode .device-card {
  padding: 12px;
}

.mobile-mode .device-info {
  flex-direction: row;
  align-items: center;
  gap: 8px;
}

.mobile-mode .device-label {
  font-size: 13px;
}

.mobile-mode .device-status-text {
  font-size: 11px;
}

.mobile-mode .threshold-grid {
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.mobile-mode .threshold-item {
  padding: 8px;
}

.mobile-mode .threshold-label {
  font-size: 12px;
}

.mobile-mode .threshold-input {
  font-size: 14px;
  padding: 6px 8px;
}

.mobile-mode .threshold-actions {
  flex-direction: column;
  gap: 6px;
}

.mobile-mode .threshold-actions .btn {
  width: 100%;
}

.mobile-mode .cmd-log-list {
  max-height: 200px;
}

.mobile-mode .cmd-item {
  padding: 6px 8px;
  font-size: 12px;
  flex-wrap: wrap;
  gap: 4px;
}

.mobile-mode .card {
  padding: 12px;
}

.mobile-mode .glow-card {
  padding: 12px;
}
</style>