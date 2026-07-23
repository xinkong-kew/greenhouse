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
      { name: '河北', cities: ['Shijiazhuang', '石家庄', 'Baoding', '保定', 'Tangshan', '唐山', 'Handan', '邯郸', 'Qinhuangdao', '秦皇岛', 'Xingtai', '邢台', 'Zhangjiakou', '张家口', 'Chengde', '承德', 'Cangzhou', '沧州', 'Langfang', '廊坊', 'Hengshui', '衡水'] },
      { name: '山西', cities: ['Taiyuan', '太原', 'Datong', '大同', 'Linfen', '临汾', 'Changzhi', '长治', 'Yangquan', '阳泉', 'Jincheng', '晋城', 'Shuozhou', '朔州', 'Jinzhong', '晋中', 'Yuncheng', '运城', 'Xinzhou', '忻州', 'Lvliang', '吕梁'] },
      { name: '内蒙古', cities: ['Hohhot', '呼和浩特', 'Baotou', '包头', 'Chifeng', '赤峰', 'Ordos', '鄂尔多斯', 'Tongliao', '通辽', 'Hulunbuir', '呼伦贝尔', 'Ulanqab', '乌兰察布', 'Bayannur', '巴彦淖尔', 'Wuhai', '乌海'] }
    ]
  },
  {
    name: '东北',
    provinces: [
      { name: '辽宁', cities: ['Shenyang', '沈阳', 'Dalian', '大连', 'Anshan', '鞍山', 'Jinzhou', '锦州', 'Fushun', '抚顺', 'Benxi', '本溪', 'Dandong', '丹东', 'Yingkou', '营口', 'Fuxin', '阜新', 'Liaoyang', '辽阳', 'Panjin', '盘锦', 'Tieling', '铁岭', 'Chaoyang', '朝阳', 'Huludao', '葫芦岛'] },
      { name: '吉林', cities: ['Changchun', '长春', 'Jilin', '吉林', 'Yanji', '延吉', 'Tonghua', '通化', 'Siping', '四平', 'Liaoyuan', '辽源', 'Baishan', '白山', 'Songyuan', '松原', 'Baicheng', '白城'] },
      { name: '黑龙江', cities: ['Harbin', '哈尔滨', 'Daqing', '大庆', 'Qiqihar', '齐齐哈尔', 'Mudanjiang', '牡丹江', 'Jixi', '鸡西', 'Hegang', '鹤岗', 'Shuangyashan', '双鸭山', 'Yichun', '伊春', 'Jiamusi', '佳木斯', 'Qitaihe', '七台河', 'Heihe', '黑河', 'Suihua', '绥化'] }
    ]
  },
  {
    name: '华东',
    provinces: [
      { name: '上海', cities: ['Shanghai', '上海'] },
      { name: '江苏', cities: ['Nanjing', '南京', 'Suzhou', '苏州', 'Wuxi', '无锡', 'Changzhou', '常州', 'Yangzhou', '扬州', 'Xuzhou', '徐州', 'Nantong', '南通', 'Lianyungang', '连云港', 'Huai\'an', '淮安', 'Yancheng', '盐城', 'Zhenjiang', '镇江', 'Taizhou', '泰州', 'Suqian', '宿迁'] },
      { name: '浙江', cities: ['Hangzhou', '杭州', 'Ningbo', '宁波', 'Wenzhou', '温州', 'Shaoxing', '绍兴', 'Jiaxing', '嘉兴', 'Huzhou', '湖州', 'Jinhua', '金华', 'Quzhou', '衢州', 'Zhoushan', '舟山', 'Taizhou', '台州', 'Lishui', '丽水'] },
      { name: '安徽', cities: ['Hefei', '合肥', 'Wuhu', '芜湖', 'Bengbu', '蚌埠', 'Huangshan', '黄山', 'Huainan', '淮南', 'Ma\'anshan', '马鞍山', 'Huaibei', '淮北', 'Tongling', '铜陵', 'Anqing', '安庆', 'Chuzhou', '滁州', 'Fuyang', '阜阳', 'Suzhou', '宿州', 'Lu\'an', '六安', 'Bozhou', '亳州', 'Chizhou', '池州', 'Xuancheng', '宣城'] },
      { name: '福建', cities: ['Fuzhou', '福州', 'Xiamen', '厦门', 'Quanzhou', '泉州', 'Zhangzhou', '漳州', 'Putian', '莆田', 'Sanming', '三明', 'Nanping', '南平', 'Longyan', '龙岩', 'Ningde', '宁德'] },
      { name: '江西', cities: ['Nanchang', '南昌', 'Jiujiang', '九江', 'Ganzhou', '赣州', 'Jingdezhen', '景德镇', 'Pingxiang', '萍乡', 'Xinyu', '新余', 'Yingtan', '鹰潭', 'Ji\'an', '吉安', 'Yichun', '宜春', 'Fuzhou', '抚州', 'Shangrao', '上饶'] },
      { name: '山东', cities: ['Jinan', '济南', 'Qingdao', '青岛', 'Yantai', '烟台', 'Weihai', '威海', 'Linyi', '临沂', 'Zibo', '淄博', 'Zaozhuang', '枣庄', 'Dongying', '东营', 'Weifang', '潍坊', 'Jining', '济宁', 'Tai\'an', '泰安', 'Rizhao', '日照', 'Dezhou', '德州', 'Liaocheng', '聊城', 'Binzhou', '滨州', 'Heze', '菏泽'] }
    ]
  },
  {
    name: '华中',
    provinces: [
      { name: '河南', cities: ['Zhengzhou', '郑州', 'Luoyang', '洛阳', 'Kaifeng', '开封', 'Nanyang', '南阳', 'Xinxiang', '新乡', 'Pingdingshan', '平顶山', 'Anyang', '安阳', 'Hebi', '鹤壁', 'Jiaozuo', '焦作', 'Puyang', '濮阳', 'Xuchang', '许昌', 'Luohe', '漯河', 'Sanmenxia', '三门峡', 'Shangqiu', '商丘', 'Xinyang', '信阳', 'Zhoukou', '周口', 'Zhumadian', '驻马店'] },
      { name: '湖北', cities: ['Wuhan', '武汉', 'Yichang', '宜昌', 'Xiangyang', '襄阳', 'Jingzhou', '荆州', 'Huangshi', '黄石', 'Shiyan', '十堰', 'Ezhou', '鄂州', 'Jingmen', '荆门', 'Xiaogan', '孝感', 'Huanggang', '黄冈', 'Xianning', '咸宁', 'Suizhou', '随州', 'Enshi', '恩施'] },
      { name: '湖南', cities: ['Changsha', '长沙', 'Zhuzhou', '株洲', 'Xiangtan', '湘潭', 'Hengyang', '衡阳', 'Zhangjiajie', '张家界', 'Shaoyang', '邵阳', 'Yueyang', '岳阳', 'Changde', '常德', 'Yiyang', '益阳', 'Chenzhou', '郴州', 'Yongzhou', '永州', 'Huaihua', '怀化', 'Loudi', '娄底', 'Xiangxi', '湘西'] }
    ]
  },
  {
    name: '华南',
    provinces: [
      { name: '广东', cities: ['Guangzhou', '广州', 'Shenzhen', '深圳', 'Zhuhai', '珠海', 'Dongguan', '东莞', 'Foshan', '佛山', 'Shantou', '汕头', 'Shaoguan', '韶关', 'Jiangmen', '江门', 'Zhanjiang', '湛江', 'Maoming', '茂名', 'Zhaoqing', '肇庆', 'Huizhou', '惠州', 'Meizhou', '梅州', 'Shanwei', '汕尾', 'Heyuan', '河源', 'Yangjiang', '阳江', 'Qingyuan', '清远', 'Zhongshan', '中山', 'Chaozhou', '潮州', 'Jieyang', '揭阳', 'Yunfu', '云浮'] },
      { name: '广西', cities: ['Nanning', '南宁', 'Guilin', '桂林', 'Liuzhou', '柳州', 'Beihai', '北海', 'Wuzhou', '梧州', 'Qinzhou', '钦州', 'Guigang', '贵港', 'Yulin', '玉林', 'Baise', '百色', 'Hezhou', '贺州', 'Hechi', '河池', 'Laibin', '来宾', 'Chongzuo', '崇左'] },
      { name: '海南', cities: ['Haikou', '海口', 'Sanya', '三亚', 'Sansha', '三沙', 'Danzhou', '儋州'] },
      { name: '香港', cities: ['Hong Kong', '香港'] },
      { name: '澳门', cities: ['Macau', '澳门'] }
    ]
  },
  {
    name: '西南',
    provinces: [
      { name: '重庆', cities: ['Chongqing', '重庆'] },
      { name: '四川', cities: ['Chengdu', '成都', 'Mianyang', '绵阳', 'Deyang', '德阳', 'Leshan', '乐山', 'Zigong', '自贡', 'Panzhihua', '攀枝花', 'Luzhou', '泸州', 'Guangyuan', '广元', 'Suining', '遂宁', 'Neijiang', '内江', 'Ziyang', '资阳', 'Yibin', '宜宾', 'Nanchong', '南充', 'Dazhou', '达州', 'Yaan', '雅安', 'Guangan', '广安', 'Bazhong', '巴中', 'Meishan', '眉山', 'Xichang', '凉山'] },
      { name: '贵州', cities: ['Guiyang', '贵阳', 'Zunyi', '遵义', 'Anshun', '安顺', 'Kaili', '凯里', 'Liping', '黎平', 'Liupanshui', '六盘水', 'Bijie', '毕节', 'Tongren', '铜仁'] },
      { name: '云南', cities: ['Kunming', '昆明', 'Dali', '大理', 'Lijiang', '丽江', 'Jinghong', '西双版纳', 'Qujing', '曲靖', 'Yuxi', '玉溪', 'Baoshan', '保山', 'Zhaotong', '昭通', 'Pu\'er', '普洱', 'Lincang', '临沧', 'Chuxiong', '楚雄', 'Gejiu', '红河', 'Wenshan', '文山', 'Dehong', '德宏', 'Shangri-La', '迪庆'] },
      { name: '西藏', cities: ['Lhasa', '拉萨', 'Shigatse', '日喀则', 'Nyingchi', '林芝', 'Lhasa', '那曲', 'Shigatse', '阿里', 'Qamdo', '昌都', 'Shannan', '山南'] }
    ]
  },
  {
    name: '西北',
    provinces: [
      { name: '陕西', cities: ['Xi\'an', '西安', 'Xianyang', '咸阳', 'Baoji', '宝鸡', 'Yan\'an', '延安', 'Weinan', '渭南', 'Hanzhong', '汉中', 'Ankang', '安康', 'Shangluo', '商洛', 'Tongchuan', '铜川'] },
      { name: '甘肃', cities: ['Lanzhou', '兰州', 'Tianshui', '天水', 'Dunhuang', '敦煌', 'Jiuquan', '酒泉', 'Baiyin', '白银', 'Wuwei', '武威', 'Zhangye', '张掖', 'Pingliang', '平凉', 'Qingyang', '庆阳', 'Dingxi', '定西', 'Longnan', '陇南'] },
      { name: '青海', cities: ['Xining', '西宁', 'Golmud', '格尔木', 'Yushu', '玉树', 'Haidong', '海东'] },
      { name: '宁夏', cities: ['Yinchuan', '银川', 'Shizuishan', '石嘴山', 'Guyuan', '固原', 'Wuzhong', '吴忠', 'Zhongwei', '中卫'] },
      { name: '新疆', cities: ['Urumqi', '乌鲁木齐', 'Kashgar', '喀什', 'Turpan', '吐鲁番', 'Hami', '哈密', 'Yining', '伊宁', 'Karamay', '克拉玛依', 'Korla', '库尔勒', 'Aksu', '阿克苏', 'Hotan', '和田'] }
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