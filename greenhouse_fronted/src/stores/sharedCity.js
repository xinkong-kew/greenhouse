/**
 * 共享城市状态 - 首页和控制面板共用
 * 两边切换城市时自动同步
 */
import { reactive } from 'vue'

export const sharedCity = reactive({
  name: '郑州',
  nameEn: 'zhengzhou'
})

export function updateCity(cityChinese, cityEnglish) {
  sharedCity.name = cityChinese
  sharedCity.nameEn = cityEnglish
}