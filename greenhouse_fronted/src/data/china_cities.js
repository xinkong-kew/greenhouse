/**
 * 中国省份城市数据
 * 按地理区域分组，包含主要城市
 */
export const chinaRegions = [
  {
    name: '华北',
    provinces: [
      { name: '北京', cities: ['Beijing', '北京'] },
      { name: '天津', cities: ['Tianjin', '天津'] },
      { name: '河北', cities: ['Shijiazhuang', '石家庄', 'Baoding', '保定', 'Tangshan', '唐山', 'Handan', '邯郸', 'Qinhuangdao', '秦皇岛'] },
      { name: '山西', cities: ['Taiyuan', '太原', 'Datong', '大同', 'Linfen', '临汾', 'Changzhi', '长治'] },
      { name: '内蒙古', cities: ['Hohhot', '呼和浩特', 'Baotou', '包头', 'Chifeng', '赤峰', 'Ordos', '鄂尔多斯'] }
    ]
  },
  {
    name: '东北',
    provinces: [
      { name: '辽宁', cities: ['Shenyang', '沈阳', 'Dalian', '大连', 'Anshan', '鞍山', 'Jinzhou', '锦州'] },
      { name: '吉林', cities: ['Changchun', '长春', 'Jilin', '吉林', 'Yanji', '延吉', 'Tonghua', '通化'] },
      { name: '黑龙江', cities: ['Harbin', '哈尔滨', 'Daqing', '大庆', 'Qiqihar', '齐齐哈尔', 'Mudanjiang', '牡丹江'] }
    ]
  },
  {
    name: '华东',
    provinces: [
      { name: '上海', cities: ['Shanghai', '上海'] },
      { name: '江苏', cities: ['Nanjing', '南京', 'Suzhou', '苏州', 'Wuxi', '无锡', 'Changzhou', '常州', 'Yangzhou', '扬州'] },
      { name: '浙江', cities: ['Hangzhou', '杭州', 'Ningbo', '宁波', 'Wenzhou', '温州', 'Shaoxing', '绍兴', 'Jiaxing', '嘉兴'] },
      { name: '安徽', cities: ['Hefei', '合肥', 'Wuhu', '芜湖', 'Bengbu', '蚌埠', 'Huangshan', '黄山'] },
      { name: '福建', cities: ['Fuzhou', '福州', 'Xiamen', '厦门', 'Quanzhou', '泉州', 'Zhangzhou', '漳州'] },
      { name: '江西', cities: ['Nanchang', '南昌', 'Jiujiang', '九江', 'Ganzhou', '赣州', 'Jingdezhen', '景德镇'] },
      { name: '山东', cities: ['Jinan', '济南', 'Qingdao', '青岛', 'Yantai', '烟台', 'Weihai', '威海', 'Linyi', '临沂'] }
    ]
  },
  {
    name: '华中',
    provinces: [
      { name: '河南', cities: ['Zhengzhou', '郑州', 'Luoyang', '洛阳', 'Kaifeng', '开封', 'Nanyang', '南阳', 'Xinxiang', '新乡'] },
      { name: '湖北', cities: ['Wuhan', '武汉', 'Yichang', '宜昌', 'Xiangyang', '襄阳', 'Jingzhou', '荆州'] },
      { name: '湖南', cities: ['Changsha', '长沙', 'Zhuzhou', '株洲', 'Xiangtan', '湘潭', 'Hengyang', '衡阳', 'Zhangjiajie', '张家界'] }
    ]
  },
  {
    name: '华南',
    provinces: [
      { name: '广东', cities: ['Guangzhou', '广州', 'Shenzhen', '深圳', 'Zhuhai', '珠海', 'Dongguan', '东莞', 'Foshan', '佛山', 'Shantou', '汕头'] },
      { name: '广西', cities: ['Nanning', '南宁', 'Guilin', '桂林', 'Liuzhou', '柳州', 'Beihai', '北海'] },
      { name: '海南', cities: ['Haikou', '海口', 'Sanya', '三亚', 'Sansha', '三沙'] },
      { name: '香港', cities: ['Hong Kong', '香港'] },
      { name: '澳门', cities: ['Macau', '澳门'] }
    ]
  },
  {
    name: '西南',
    provinces: [
      { name: '重庆', cities: ['Chongqing', '重庆'] },
      { name: '四川', cities: ['Chengdu', '成都', 'Mianyang', '绵阳', 'Deyang', '德阳', 'Leshan', '乐山', 'Zigong', '自贡'] },
      { name: '贵州', cities: ['Guiyang', '贵阳', 'Zunyi', '遵义', 'Anshun', '安顺', 'Liping', '黎平'] },
      { name: '云南', cities: ['Kunming', '昆明', 'Dali', '大理', 'Lijiang', '丽江', 'Xishuangbanna', '西双版纳'] },
      { name: '西藏', cities: ['Lhasa', '拉萨', 'Xigaze', '日喀则', 'Nyingchi', '林芝'] }
    ]
  },
  {
    name: '西北',
    provinces: [
      { name: '陕西', cities: ['Xi\'an', '西安', 'Xianyang', '咸阳', 'Baoji', '宝鸡', 'Yan\'an', '延安'] },
      { name: '甘肃', cities: ['Lanzhou', '兰州', 'Tianshui', '天水', 'Dunhuang', '敦煌', 'Jiuquan', '酒泉'] },
      { name: '青海', cities: ['Xining', '西宁', 'Golmud', '格尔木', 'Yushu', '玉树'] },
      { name: '宁夏', cities: ['Yinchuan', '银川', 'Shizuishan', '石嘴山', 'Guyuan', '固原'] },
      { name: '新疆', cities: ['Urumqi', '乌鲁木齐', 'Kashgar', '喀什', 'Turpan', '吐鲁番', 'Hami', '哈密', 'Yining', '伊宁'] }
    ]
  }
]

/**
 * 获取省份对应的英文城市名（用于 OpenWeatherMap API）
 * @param {string} provinceName - 省份名称
 * @param {string} cityChinese - 城市中文名
 * @returns {string} 英文城市名
 */
export function getCityEnglish(provinceName, cityChinese) {
  for (const region of chinaRegions) {
    for (const prov of region.provinces) {
      if (prov.name === provinceName) {
        // cities 数组是 [英文名, 中文名, 英文名, 中文名, ...]
        for (let i = 0; i < prov.cities.length; i += 2) {
          if (prov.cities[i + 1] === cityChinese) {
            return prov.cities[i]
          }
        }
      }
    }
  }
  // 默认返回中文名（OpenWeatherMap 也支持中文城市名）
  return cityChinese
}