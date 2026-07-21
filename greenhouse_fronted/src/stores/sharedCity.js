/**
 * 共享城市状态 - 首页和控制面板共用
 * 使用 localStorage 持久化，页面切换时自动同步
 */
import { reactive } from 'vue'

const STORAGE_KEY = 'greenhouse_city'
const DEFAULT_CITY = '郑州'
const DEFAULT_CITY_EN = 'zhengzhou'

// 从 localStorage 读取初始值
function loadFromStorage() {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved) {
      const parsed = JSON.parse(saved)
      return { name: parsed.name || DEFAULT_CITY, nameEn: parsed.nameEn || DEFAULT_CITY_EN }
    }
  } catch {}
  return { name: DEFAULT_CITY, nameEn: DEFAULT_CITY_EN }
}

const initial = loadFromStorage()

export const sharedCity = reactive({
  name: initial.name,
  nameEn: initial.nameEn
})

export function updateCity(cityChinese, cityEnglish) {
  sharedCity.name = cityChinese
  sharedCity.nameEn = cityEnglish || sharedCity.nameEn
  // 持久化到 localStorage
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({
      name: sharedCity.name,
      nameEn: sharedCity.nameEn
    }))
  } catch {}
}

// 页面初始化时调用，确保城市与服务器同步
export function initCityFromServer(cityChinese, cityEnglish) {
  if (!cityChinese) return
  // 如果 localStorage 中有值，优先使用本地保存的
  const saved = loadFromStorage()
  if (saved.name !== DEFAULT_CITY) {
    // 本地有用户手动选择的城市，不覆盖
    return
  }
  updateCity(cityChinese, cityEnglish || '')
}