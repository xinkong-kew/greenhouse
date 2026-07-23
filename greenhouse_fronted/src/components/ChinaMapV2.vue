<template>
  <div class="map-overlay" @click.self="closeMap">
    <div class="map-container">
      <!-- 头部 -->
      <div class="map-header">
        <h3 v-if="!selectedProvinceName">🗺️ 中国地图 - 点击省份查看城市</h3>
        <h3 v-else>🗺️ {{ selectedProvinceName }} - 点击城市选择</h3>
        <button class="btn-back" v-if="selectedProvinceName" @click="backToChina">← 返回中国</button>
        <span class="map-current" v-if="currentCity">当前：{{ currentCity }}</span>
        <button class="btn-close" @click="closeMap">✕</button>
      </div>

      <!-- 加载状态 -->
      <div v-if="loading" class="map-loading">
        <div class="loading-spinner"></div>
        <span>加载地图数据...</span>
      </div>
      <div v-else-if="error" class="map-error">{{ error }}</div>

      <!-- ===== 二级地图：省份城市地图 ===== -->
      <div v-else-if="selectedProvinceName" class="province-map-wrapper">
        <div v-if="provinceLoading" class="province-loading">
          <div class="loading-spinner"></div>
          <span>加载城市数据...</span>
        </div>
        <svg v-else
          viewBox="0 0 800 600"
          class="province-svg"
          xmlns="http://www.w3.org/2000/svg"
        >
          <!-- 城市边界 -->
          <g v-for="(cityFeat, idx) in provinceFeatures" :key="idx">
            <path
              v-for="(pathD, pIdx) in getProvincePaths(cityFeat)"
              :key="pIdx"
              :d="pathD"
              class="city-boundary"
              :class="{
                'city-hover': hoveredCity === cityFeat.properties.name,
                'city-selected': currentCity === getCityShortName(cityFeat.properties.name)
              }"
              @click="onCityClick(cityFeat)"
              @mouseenter="hoveredCity = cityFeat.properties.name"
              @mouseleave="hoveredCity = null"
            />
            <!-- 城市名称 -->
            <text
              :x="getProvinceCentroid(cityFeat)[0]"
              :y="getProvinceCentroid(cityFeat)[1]"
              class="city-label"
              text-anchor="middle"
              dominant-baseline="central"
              style="pointer-events: none;"
            >
              {{ getCityShortName(cityFeat.properties.name) }}
            </text>
          </g>
        </svg>

        <!-- 底部城市列表 -->
        <div class="province-city-strip">
          <div
            class="strip-city"
            v-for="(cityFeat, idx) in provinceFeatures"
            :key="idx"
            :class="{ selected: currentCity === getCityShortName(cityFeat.properties.name) }"
            @click="onCityClick(cityFeat)"
          >
            🏙️ {{ getCityShortName(cityFeat.properties.name) }}
          </div>
        </div>
      </div>

      <!-- ===== 一级地图：中国地图 ===== -->
      <div v-else class="map-svg-wrapper">
        <svg
          :viewBox="`0 0 ${svgW} ${svgH}`"
          class="china-svg"
          xmlns="http://www.w3.org/2000/svg"
        >
          <!-- 南海诸岛 -->
          <g :transform="`translate(${svgW - 120}, ${svgH - 120}) scale(0.25)`">
            <rect x="0" y="0" width="200" height="200" fill="rgba(0,255,136,0.03)" stroke="rgba(0,255,136,0.15)" stroke-width="2"/>
            <text x="100" y="105" text-anchor="middle" fill="rgba(200,214,229,0.3)" font-size="24">南海诸岛</text>
          </g>

          <g v-for="(feat, idx) in chinaFeatures" :key="idx">
            <path
              v-for="(pathD, pIdx) in getChinaPaths(feat)"
              :key="pIdx"
              :d="pathD"
              class="province-path"
              :class="{ 'province-hover': hoveredProvince === feat.properties.name }"
              @click="onProvinceClick(feat)"
              @mouseenter="hoveredProvince = feat.properties.name"
              @mouseleave="hoveredProvince = null"
            />
            <text
              :x="getChinaCentroid(feat)[0]"
              :y="getChinaCentroid(feat)[1]"
              class="province-label"
              text-anchor="middle"
              dominant-baseline="central"
              style="pointer-events: none;"
            >
              {{ getShortProvinceName(feat.properties.name) }}
            </text>
          </g>
        </svg>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { getCityEnglish } from '../data/china_cities.js'
import { chinaRegions } from '../data/china_cities.js'

const props = defineProps({
  currentCity: { type: String, default: '' }
})
const emit = defineEmits(['close', 'select'])

// ===== 状态 =====
const loading = ref(true)
const error = ref('')
const chinaFeatures = ref([])           // 一级：中国省份features
const hoveredProvince = ref(null)
const selectedProvinceName = ref(null)  // 选中省份简称
const selectedProvinceFull = ref(null)  // 选中省份全名
const provinceFeatures = ref([])        // 二级：省份城市features
const provinceLoading = ref(false)      // 省份数据加载中
const hoveredCity = ref(null)

// GeoJSON 缓存（避免重复请求）
const geoCache = {}

const svgW = 800
const svgH = 680

// ===== 省份简称映射 =====
const shortNameMap = {
  '北京市':'北京','天津市':'天津','上海市':'上海','重庆市':'重庆',
  '香港特别行政区':'香港','澳门特别行政区':'澳门',
  '内蒙古自治区':'内蒙古','广西壮族自治区':'广西',
  '西藏自治区':'西藏','宁夏回族自治区':'宁夏','新疆维吾尔自治区':'新疆',
  '黑龙江省':'黑龙江','吉林省':'吉林','辽宁省':'辽宁',
  '河北省':'河北','山西省':'山西','陕西省':'陕西',
  '甘肃省':'甘肃','青海省':'青海','山东省':'山东',
  '河南省':'河南','江苏省':'江苏','安徽省':'安徽',
  '浙江省':'浙江','福建省':'福建','江西省':'江西',
  '湖北省':'湖北','湖南省':'湖南','广东省':'广东',
  '四川省':'四川','贵州省':'贵州','云南省':'云南',
  '海南省':'海南','台湾省':'台湾'
}

function getShortProvinceName(name) { return shortNameMap[name] || name }
function getProvinceFullName(short) {
  for (const [k,v] of Object.entries(shortNameMap)) { if (v === short) return k }
  return short
}

// 城市名简化（去掉"市"后缀）
function getCityShortName(name) {
  return name ? name.replace(/市$/, '').replace(/地区$/, '').replace(/自治州$/, '州').replace(/盟$/, '') : ''
}

// ===== 投影函数 =====
function project(lon, lat, params = {}) {
  const clon = params.clon ?? 104, clat = params.clat ?? 35
  const scale = params.scale ?? 9.8
  const ox = params.ox ?? svgW / 2, oy = params.oy ?? svgH / 2 - 20
  return [(lon - clon) * scale + ox, -(lat - clat) * scale + oy]
}

// ===== GeoJSON → SVG路径 =====
function geoToPaths(geom, proj) {
  if (!geom) return []
  const paths = []
  const proc = (coords) => {
    const ring = coords[0]
    if (!ring || ring.length < 3) return ''
    const parts = ring.map((p, i) => {
      const [x, y] = project(p[0], p[1], proj)
      return `${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`
    })
    parts.push('Z')
    return parts.join('')
  }
  if (geom.type === 'Polygon') {
    paths.push(proc(geom.coordinates))
  } else if (geom.type === 'MultiPolygon') {
    geom.coordinates.forEach(poly => paths.push(proc(poly)))
  }
  return paths
}

// ===== 计算中心点 =====
function calcCentroid(geom, proj) {
  if (!geom) return [400, 340]
  let coords = []
  if (geom.type === 'Polygon') coords = geom.coordinates[0]
  else if (geom.type === 'MultiPolygon') coords = geom.coordinates[0]?.[0]
  if (!coords || coords.length === 0) return [400, 340]
  let sx = 0, sy = 0, n = 0
  coords.forEach(p => {
    const [x, y] = project(p[0], p[1], proj)
    sx += x; sy += y; n++
  })
  return [sx / n, sy / n]
}

// ===== 一级地图 =====
function getChinaPaths(feat) {
  return geoToPaths(feat.geometry, {})
}
function getChinaCentroid(feat) {
  return calcCentroid(feat.geometry, {})
}

// ===== 二级地图：省份投影参数 =====
function getProvinceProjection() {
  if (!provinceFeatures.value.length) return {}
  let minLng = Infinity, maxLng = -Infinity, minLat = Infinity, maxLat = -Infinity
  provinceFeatures.value.forEach(feat => {
    const geom = feat.geometry
    let allCoords = []
    if (geom.type === 'Polygon') allCoords = geom.coordinates[0]
    else if (geom.type === 'MultiPolygon') geom.coordinates.forEach(p => { if (p[0]) allCoords = allCoords.concat(p[0]) })
    allCoords.forEach(p => {
      if (p[0] < minLng) minLng = p[0]
      if (p[0] > maxLng) maxLng = p[0]
      if (p[1] < minLat) minLat = p[1]
      if (p[1] > maxLat) maxLat = p[1]
    })
  })
  const rangeLng = maxLng - minLng || 1, rangeLat = maxLat - minLat || 1
  const scale = Math.min(600 / rangeLng, 500 / rangeLat) * 0.85
  return {
    clon: (minLng + maxLng) / 2, clat: (minLat + maxLat) / 2,
    scale, ox: 400, oy: 300
  }
}

function getProvincePaths(feat) {
  const proj = getProvinceProjection()
  return geoToPaths(feat.geometry, proj)
}
function getProvinceCentroid(feat) {
  const proj = getProvinceProjection()
  return calcCentroid(feat.geometry, proj)
}

// ===== 事件处理 =====
async function onProvinceClick(feat) {
  const adcode = feat.properties.adcode
  const fullName = feat.properties.name
  selectedProvinceFull.value = fullName
  selectedProvinceName.value = getShortProvinceName(fullName)
  provinceFeatures.value = []
  hoveredCity.value = null
  provinceLoading.value = true

  // 优先从缓存读取
  if (geoCache[adcode]) {
    provinceFeatures.value = geoCache[adcode]
    provinceLoading.value = false
    return
  }

  try {
    const url = `/api/map/geo/${adcode}_full.json`
    const res = await fetch(url)
    if (res.ok) {
      const data = await res.json()
      if (data.features) {
        geoCache[adcode] = data.features  // 写入缓存
        provinceFeatures.value = data.features
      }
    }
  } catch (e) {
    console.warn('省份城市数据加载失败', e)
  }
  provinceLoading.value = false
}

function onCityClick(feat) {
  const cityFull = feat.properties.name
  const cityName = getCityShortName(cityFull)
  const provShort = selectedProvinceName.value
  let cityEn = getCityEnglish(provShort, cityName)

  // 如果城市名未在映射表中找到（返回了中文名），使用省份主城市（列表中第一个英文名）
  if (/[\u4e00-\u9fff]/.test(cityEn) && cityEn === cityName) {
    const province = chinaRegions.flatMap(r => r.provinces).find(p => p.name === provShort)
    if (province && province.cities.length > 0) {
      cityEn = province.cities[0] // 第一个是英文名（省会/首府）
    }
  }

  emit('select', { province: provShort, city: cityName, cityEn })
}

function backToChina() {
  selectedProvinceName.value = null
  selectedProvinceFull.value = null
  provinceFeatures.value = []
  hoveredCity.value = null
}

function closeMap() { emit('close') }

// ===== 初始化 =====
onMounted(async () => {
  try {
    const res = await fetch('/api/map/geo/100000_full.json')
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    if (data.features) {
      chinaFeatures.value = data.features
    }
    loading.value = false
  } catch (e) {
    console.error('加载地图数据失败:', e)
    error.value = '地图数据加载失败，请检查网络连接'
    loading.value = false
  }
})
</script>

<style>
.map-overlay {
  position: fixed; inset: 0;
  background: rgba(0,0,0,0.75);
  backdrop-filter: blur(6px);
  display: flex; align-items: center; justify-content: center;
  z-index: 9999; padding: 16px;
}
.map-container {
  background: #0a0e1a;
  border: 1px solid rgba(0,255,136,0.15);
  border-radius: 16px;
  width: 95vw; max-width: 860px; max-height: 92vh;
  display: flex; flex-direction: column;
  box-shadow: 0 8px 48px rgba(0,0,0,0.6);
  overflow: hidden;
}
.map-header {
  display: flex; align-items: center; gap: 10px;
  padding: 14px 20px;
  border-bottom: 1px solid rgba(0,255,136,0.1);
  flex-shrink: 0;
}
.map-header h3 { font-size: 15px; font-weight: 700; color: #00ff88; margin: 0; }
.btn-back {
  background: rgba(0,212,255,0.1); border: 1px solid rgba(0,212,255,0.2);
  color: #00d4ff; padding: 4px 12px; border-radius: 6px;
  cursor: pointer; font-size: 12px; white-space: nowrap;
}
.btn-back:hover { background: rgba(0,212,255,0.2); }
.map-current { font-size: 12px; color: rgba(200,214,229,0.5); margin-left: auto; white-space: nowrap; }
.btn-close {
  background: none; border: 1px solid rgba(200,214,229,0.15);
  color: rgba(200,214,229,0.5); width: 28px; height: 28px;
  border-radius: 50%; cursor: pointer; font-size: 14px;
  display: flex; align-items: center; justify-content: center; flex-shrink: 0;
}
.btn-close:hover { background: rgba(255,71,87,0.15); border-color: rgba(255,71,87,0.3); color: #ff4757; }

/* 加载 */
.map-loading {
  display: flex; flex-direction: column; align-items: center;
  justify-content: center; padding: 60px 20px; gap: 16px;
  color: rgba(200,214,229,0.5); font-size: 14px;
}
.loading-spinner {
  width: 36px; height: 36px;
  border: 3px solid rgba(0,255,136,0.1);
  border-top-color: #00ff88; border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
.map-error { padding: 40px; text-align: center; color: #ff6b6b; font-size: 14px; }

/* 省份加载 */
.province-loading {
  display: flex; flex-direction: column; align-items: center;
  justify-content: center; padding: 60px; gap: 16px;
  color: rgba(200,214,229,0.5); font-size: 14px; flex: 1;
}

/* ===== 一级地图：中国 ===== */
.map-svg-wrapper {
  flex: 1; padding: 10px; overflow: hidden;
  display: flex; align-items: center; justify-content: center; min-height: 400px;
}
.china-svg { width: 100%; height: 100%; max-height: 70vh; }
.province-path {
  fill: rgba(0,255,136,0.06); stroke: rgba(0,255,136,0.2);
  stroke-width: 1; stroke-linejoin: round; cursor: pointer; transition: all 0.2s;
}
.province-path:hover, .province-hover {
  fill: rgba(0,255,136,0.15); stroke: rgba(0,255,136,0.5); stroke-width: 1.5;
}
.province-label {
  fill: rgba(200,214,229,0.6); font-size: 10px; font-weight: 600;
  user-select: none; transition: fill 0.2s;
}

/* ===== 二级地图：省份城市 ===== */
.province-map-wrapper {
  flex: 1; padding: 10px; overflow: hidden;
  display: flex; flex-direction: column; align-items: center;
  min-height: 350px;
}
.province-svg { width: 100%; max-height: 55vh; }

.city-boundary {
  fill: rgba(0,255,136,0.04);
  stroke: rgba(0,255,136,0.2);
  stroke-width: 1;
  stroke-linejoin: round;
  cursor: pointer;
  transition: all 0.2s;
}
.city-boundary:hover, .city-hover {
  fill: rgba(0,255,136,0.12);
  stroke: rgba(0,255,136,0.5);
  stroke-width: 1.5;
}
.city-selected {
  fill: rgba(0,212,255,0.2);
  stroke: #00d4ff;
  stroke-width: 2;
}
.city-label {
  fill: rgba(200,214,229,0.55);
  font-size: 11px;
  font-weight: 600;
  user-select: none;
  transition: fill 0.2s;
}
.city-hover + .city-label,
.city-boundary:hover + .city-label {
  fill: #00ff88;
  font-weight: 700;
}

/* 底部城市条 */
.province-city-strip {
  display: flex; flex-wrap: wrap; gap: 6px;
  padding: 10px 16px; justify-content: center;
  border-top: 1px solid rgba(0,255,136,0.06);
  width: 100%; flex-shrink: 0; overflow-y: auto; max-height: 100px;
}
.strip-city {
  padding: 4px 10px;
  background: rgba(0,255,136,0.03);
  border: 1px solid rgba(0,255,136,0.08);
  border-radius: 6px; font-size: 11px;
  color: rgba(200,214,229,0.6);
  cursor: pointer; transition: all 0.2s; white-space: nowrap;
}
.strip-city:hover { background: rgba(0,255,136,0.1); border-color: rgba(0,255,136,0.2); color: #00ff88; }
.strip-city.selected { background: rgba(0,255,136,0.15); border-color: #00ff88; color: #00ff88; font-weight: 600; }

@media (max-width: 600px) {
  .map-container { border-radius: 12px; width: 100vw; max-height: 100vh; }
  .province-label { font-size: 7px !important; }
  .city-label { font-size: 8px !important; }
  .map-header h3 { font-size: 12px; }
  .map-current { display: none; }
}
</style>