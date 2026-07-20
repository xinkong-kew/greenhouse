"""
weather_agent.py — 智能天气感知与大棚自动管理智能体

功能：
1. 读取 OpenWeatherMap 未来天气预报
2. 根据天气 + 当前传感器数据做智能决策
3. 自动生成设备控制建议并记录日志
4. 提供 API 接口供前端展示

使用方法：
1. 在 https://openweathermap.org/api 注册免费账号获取 API Key
2. 将 API Key 填入本文件顶部的 WEATHER_API_KEY
"""

import requests
import json
import time
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import threading
import sys

# ==================== 配置 ====================

# OpenWeatherMap API 配置（免费版可获取5天/3小时预报）
# 注册地址: https://openweathermap.org/api
WEATHER_API_KEY = "368cdf1c280124d8e888710b87d5aaae"  # ← 替换为你的 Key

# 大棚所在地（城市名或 lat,lon）
WEATHER_CITY = "Zhengzhou"          # 城市名（英文）
WEATHER_LAT = None                  # 如果设置了 lat/lon，优先使用
WEATHER_LON = None

# 天气检查间隔（秒）
WEATHER_CHECK_INTERVAL = 1800       # 30分钟检查一次天气变化
AGENT_DECISION_INTERVAL = 300       # 5分钟做一次决策

# 传感器阈值（用于决策参考）
THRESHOLDS = {
    'temp_high': 35.0,              # 温度过高阈值
    'temp_low': 5.0,                # 温度过低阈值
    'hum_high': 85.0,               # 湿度过高阈值
    'hum_low': 30.0,                # 湿度过低阈值
    'soil_dry': 30.0,               # 土壤干燥阈值
    'soil_wet': 80.0,               # 土壤过湿阈值
    'water_low': 20.0,              # 水位过低阈值
    'water_high': 90.0,             # 水位过高阈值
}


class WeatherAgent:
    """天气感知与智能决策智能体"""

    def __init__(self):
        self.forecast_cache = None          # 缓存的天气预报
        self.forecast_time = None           # 上次获取天气时间
        self.decisions: List[Dict] = []     # 决策日志
        self.max_decisions = 100            # 最多保留的决策数
        self.current_advice: Dict = {}      # 当前建议摘要
        self.enabled = True                 # 智能体是否启用
        self.lock = threading.Lock()

    # ==================== 天气获取 ====================

    def fetch_forecast(self) -> Optional[Dict]:
        """获取天气预报（5天/3小时间隔）"""
        if WEATHER_API_KEY == "YOUR_OPENWEATHERMAP_API_KEY":
            return None

        try:
            # 构建请求 URL
            if WEATHER_LAT and WEATHER_LON:
                url = (
                    f"https://api.openweathermap.org/data/2.5/forecast"
                    f"?lat={WEATHER_LAT}&lon={WEATHER_LON}"
                    f"&appid={WEATHER_API_KEY}&units=metric&lang=zh_cn"
                )
            else:
                url = (
                    f"https://api.openweathermap.org/data/2.5/forecast"
                    f"?q={WEATHER_CITY}"
                    f"&appid={WEATHER_API_KEY}&units=metric&lang=zh_cn"
                )

            resp = requests.get(url, timeout=10)
            if resp.status_code != 200:
                print(f"[天气Agent] API 返回错误: {resp.status_code}", flush=True)
                print(f"[天气Agent] 请求URL: {url}", flush=True)
                print(f"[天气Agent] 响应内容: {resp.text[:200]}", flush=True)
                
                # 尝试带国家代码的城市名
                if WEATHER_CITY and ',' not in WEATHER_CITY:
                    print(f"[天气Agent] 尝试添加国家代码 CN...", flush=True)
                    url_cn = (
                        f"https://api.openweathermap.org/data/2.5/forecast"
                        f"?q={WEATHER_CITY},CN"
                        f"&appid={WEATHER_API_KEY}&units=metric&lang=zh_cn"
                    )
                    resp_cn = requests.get(url_cn, timeout=10)
                    if resp_cn.status_code == 200:
                        print(f"[天气Agent] 使用 {WEATHER_CITY},CN 成功", flush=True)
                        resp = resp_cn
                    else:
                        print(f"[天气Agent] 添加CN后仍失败: {resp_cn.status_code}", flush=True)
                        return None
                else:
                    return None

            data = resp.json()

            # 解析为精简格式
            forecast_list = []
            for item in data.get('list', []):
                forecast_list.append({
                    'dt': item['dt'],
                    'time': datetime.fromtimestamp(item['dt']).strftime('%m-%d %H:00'),
                    'temp': round(item['main']['temp'], 1),
                    'feels_like': round(item['main']['feels_like'], 1),
                    'temp_min': round(item['main']['temp_min'], 1),
                    'temp_max': round(item['main']['temp_max'], 1),
                    'humidity': item['main']['humidity'],
                    'pressure': item['main']['pressure'],
                    'weather': item['weather'][0]['description'],
                    'weather_code': item['weather'][0]['id'],
                    'weather_main': item['weather'][0]['main'],
                    'clouds': item['clouds']['all'],
                    'wind_speed': item['wind']['speed'],
                    'pop': item.get('pop', 0),          # 降雨概率 0-1
                    'rain': item.get('rain', {}).get('3h', 0) if 'rain' in item else 0
                })

            result = {
                'city': data.get('city', {}).get('name', WEATHER_CITY),
                'country': data.get('city', {}).get('country', ''),
                'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'forecast': forecast_list[:16]  # 只保留2天（48小时/3小时间隔=16个点）
            }

            # 计算摘要
            result['summary'] = self._calc_forecast_summary(forecast_list[:16])

            return result

        except requests.exceptions.Timeout:
            print("[天气Agent] 请求超时", flush=True)
            return None
        except requests.exceptions.ConnectionError:
            print("[天气Agent] 网络连接失败", flush=True)
            return None
        except Exception as e:
            print(f"[天气Agent] 获取天气错误: {e}", flush=True)
            return None

    def _calc_forecast_summary(self, forecast_list: List[Dict]) -> Dict:
        """计算天气预报摘要"""
        if not forecast_list:
            return {}

        temps = [f['temp'] for f in forecast_list]
        hums = [f['humidity'] for f in forecast_list]

        # 只检查近12小时（4个预报点）是否有雨，而不是5天
        near_term = forecast_list[:4]
        near_has_rain = any(f.get('pop', 0) > 0.3 for f in near_term)
        near_heavy_rain = any(f.get('pop', 0) > 0.7 for f in near_term)

        # 检查极端温度（5天范围）
        extreme_high = max(temps) >= THRESHOLDS['temp_high']
        extreme_low = min(temps) <= THRESHOLDS['temp_low']

        # 当前天气状况（第一个预报点）
        current = forecast_list[0] if forecast_list else {}
        current_weather = current.get('weather', '未知')
        current_pop = current.get('pop', 0)
        now_is_raining = current_pop > 0.5 or current.get('rain', 0) > 0

        # 今天白天和今晚的简要描述
        now = datetime.now()
        today_forecasts = [f for f in forecast_list
                          if datetime.fromtimestamp(f['dt']).date() == now.date()]
        tonight_forecasts = [f for f in forecast_list
                            if datetime.fromtimestamp(f['dt']).date() == now.date()
                            and datetime.fromtimestamp(f['dt']).hour >= 18]

        return {
            'max_temp': round(max(temps), 1),
            'min_temp': round(min(temps), 1),
            'avg_temp': round(sum(temps) / len(temps), 1),
            'avg_hum': round(sum(hums) / len(hums), 1),
            'has_rain': near_has_rain,              # 仅近12小时
            'heavy_rain': near_heavy_rain,          # 仅近12小时
            'now_is_raining': now_is_raining,        # 当前是否正在下雨
            'current_weather': current_weather,      # 当前天气描述
            'current_pop': current_pop,              # 当前降雨概率
            'extreme_high': extreme_high,
            'extreme_low': extreme_low,
            'today_desc': today_forecasts[len(today_forecasts)//2]['weather'] if today_forecasts else '未知',
            'tonight_desc': tonight_forecasts[-1]['weather'] if tonight_forecasts else '未知'
        }

    # ==================== 智能决策 ====================

    def make_decisions(self, sensor_data: Optional[Dict] = None) -> List[Dict]:
        """基于天气预报 + 当前传感器数据做出决策"""
        decisions = []
        forecast = self.forecast_cache

        if not forecast:
            decisions.append({
                'time': datetime.now().strftime('%H:%M:%S'),
                'level': 'info',
                'type': 'system',
                'action': '等待天气预报数据...',
                'reason': '天气数据尚未获取'
            })
            return decisions

        summary = forecast.get('summary', {})
        next_12h = forecast['forecast'][:4] if len(forecast['forecast']) >= 4 else forecast['forecast']

        # --- 决策 1: 降雨判断（仅看近12小时） ---
        if summary.get('now_is_raining'):
            decisions.append({
                'time': datetime.now().strftime('%H:%M:%S'),
                'level': 'warning',
                'type': 'rain',
                'action': '⚠️ 当前正在下雨，建议关闭水泵',
                'reason': f'当前降雨概率 {summary.get("current_pop",0)*100:.0f}%，自然降雨可补充水分'
            })
        elif summary.get('heavy_rain'):
            decisions.append({
                'time': datetime.now().strftime('%H:%M:%S'),
                'level': 'warning',
                'type': 'rain',
                'action': '⚠️ 未来12小时预计有大雨，建议关闭水泵',
                'reason': f'大雨即将来临，自然降雨可补充水分，避免过度灌溉'
            })
        elif summary.get('has_rain'):
            decisions.append({
                'time': datetime.now().strftime('%H:%M:%S'),
                'level': 'info',
                'type': 'rain',
                'action': '🌧️ 未来12小时可能有雨，建议减少灌溉量',
                'reason': '预计有降雨，适当降低土壤湿度目标值'
            })

        # --- 决策 2: 高温判断 ---
        if summary.get('extreme_high'):
            decisions.append({
                'time': datetime.now().strftime('%H:%M:%S'),
                'level': 'warning',
                'type': 'temp',
                'action': '🔥 建议开启风扇通风降温',
                'reason': f'预计最高温度 {summary["max_temp"]}°C，超过 {THRESHOLDS["temp_high"]}°C 阈值'
            })

        # --- 决策 3: 低温判断 ---
        if summary.get('extreme_low'):
            decisions.append({
                'time': datetime.now().strftime('%H:%M:%S'),
                'level': 'warning',
                'type': 'temp',
                'action': '🥶 建议关闭通风，开启保温措施',
                'reason': f'预计最低温度 {summary["min_temp"]}°C，低于 {THRESHOLDS["temp_low"]}°C 阈值'
            })

        # --- 决策 4: 结合当前传感器数据 ---
        if sensor_data:
            soil = sensor_data.get('latest_soil', 50)
            temp = sensor_data.get('latest_temp', 25)
            hum = sensor_data.get('latest_hum', 60)
            water = sensor_data.get('latest_water', 50)

            # 土壤湿度 + 天气综合判断
            if soil < THRESHOLDS['soil_dry'] and not summary.get('has_rain'):
                decisions.append({
                    'time': datetime.now().strftime('%H:%M:%S'),
                    'level': 'warning',
                    'type': 'soil',
                    'action': '💧 建议开启水泵灌溉',
                    'reason': f'土壤湿度 {soil}% 偏低，且近期无雨，需人工灌溉'
                })
            elif soil < THRESHOLDS['soil_dry'] and summary.get('has_rain'):
                decisions.append({
                    'time': datetime.now().strftime('%H:%M:%S'),
                    'level': 'info',
                    'type': 'soil',
                    'action': '⏳ 暂缓灌溉，等待自然降雨',
                    'reason': f'土壤湿度 {soil}% 偏低，但预报有雨，可等待自然降雨'
                })

            # 湿度判断
            if hum > THRESHOLDS['hum_high']:
                decisions.append({
                    'time': datetime.now().strftime('%H:%M:%S'),
                    'level': 'info',
                    'type': 'hum',
                    'action': '💨 建议开启风扇促进通风排湿',
                    'reason': f'湿度 {hum}% 过高，易引发病害'
                })

            # 水位判断
            if water < THRESHOLDS['water_low']:
                decisions.append({
                    'time': datetime.now().strftime('%H:%M:%S'),
                    'level': 'warning',
                    'type': 'water',
                    'action': '🚱 水位过低，请检查水源',
                    'reason': f'水位仅 {water}%，可能需要补充水源'
                })

        # --- 决策 5: 综合建议 ---
        if summary.get('extreme_high') or summary.get('extreme_low'):
            decisions.append({
                'time': datetime.now().strftime('%H:%M:%S'),
                'level': 'info',
                'type': 'advice',
                'action': '📋 建议关注天气预报变化，提前做好大棚防护措施',
                'reason': f'未来天气波动较大（{summary["min_temp"]}~{summary["max_temp"]}°C）'
            })

        # 如果没有触发任何决策，生成一条正常信息
        if not decisions:
            decisions.append({
                'time': datetime.now().strftime('%H:%M:%S'),
                'level': 'info',
                'type': 'normal',
                'action': '✅ 天气状况良好，大棚运行正常',
                'reason': f'未来气温 {summary["min_temp"]}~{summary["max_temp"]}°C，{summary.get("today_desc", "天气正常")}'
            })

        return decisions

    def update_forecast(self):
        """更新天气预报缓存"""
        forecast = self.fetch_forecast()
        if forecast:
            with self.lock:
                self.forecast_cache = forecast
                self.forecast_time = datetime.now()
            print(f"[天气Agent] 天气已更新: {forecast['city']} "
                  f"{forecast['summary'].get('min_temp','?')}~{forecast['summary'].get('max_temp','?')}°C "
                  f"{forecast['summary'].get('today_desc','')}", flush=True)
            return True
        return False

    def run_decisions(self, sensor_data: Optional[Dict] = None):
        """执行一次完整的决策流程"""
        if not self.enabled:
            return

        # 如果缓存过期或无缓存，先更新天气
        if (self.forecast_cache is None or
            self.forecast_time is None or
            (datetime.now() - self.forecast_time).total_seconds() > WEATHER_CHECK_INTERVAL):
            self.update_forecast()

        # 做决策
        new_decisions = self.make_decisions(sensor_data)

        with self.lock:
            # 追加到日志
            self.decisions.extend(new_decisions)
            # 保留最近 N 条
            if len(self.decisions) > self.max_decisions:
                self.decisions = self.decisions[-self.max_decisions:]
            # 更新当前建议
            self.current_advice = {
                'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'forecast': {
                    'city': self.forecast_cache.get('city', '') if self.forecast_cache else '',
                    'summary': self.forecast_cache.get('summary', {}) if self.forecast_cache else {},
                    'update_time': self.forecast_cache.get('update_time', '') if self.forecast_cache else ''
                } if self.forecast_cache else {},
                'decisions': [d for d in new_decisions if d['level'] in ('warning', 'danger')],
                'all_decisions': new_decisions,
                'info_count': sum(1 for d in new_decisions if d['level'] == 'info'),
                'warning_count': sum(1 for d in new_decisions if d['level'] == 'warning'),
                'enabled': self.enabled
            }

    def get_status(self) -> Dict:
        """获取智能体当前状态"""
        with self.lock:
            # 最新5条决策
            recent = self.decisions[-5:] if self.decisions else []
            return {
                'enabled': self.enabled,
                'forecast': self.forecast_cache,
                'forecast_time': self.forecast_time.strftime('%Y-%m-%d %H:%M:%S') if self.forecast_time else None,
                'current_advice': self.current_advice,
                'recent_decisions': recent,
                'total_decisions': len(self.decisions)
            }

    def get_forecast(self) -> Optional[Dict]:
        """获取缓存的天气预报"""
        with self.lock:
            return self.forecast_cache

    def get_decisions(self, limit: int = 20) -> List[Dict]:
        """获取决策日志"""
        with self.lock:
            return self.decisions[-limit:]

    def toggle(self, enabled: Optional[bool] = None) -> bool:
        """启用/禁用智能体"""
        if enabled is not None:
            self.enabled = enabled
        else:
            self.enabled = not self.enabled
        return self.enabled

    def set_city(self, city_name: str) -> bool:
        """动态切换城市并刷新天气预报"""
        global WEATHER_CITY, WEATHER_LAT, WEATHER_LON
        WEATHER_CITY = city_name
        WEATHER_LAT = None
        WEATHER_LON = None
        print(f"[天气Agent] 切换城市至: {city_name}", flush=True)
        return self.update_forecast()

    def get_current_city(self) -> str:
        """获取当前城市名"""
        global WEATHER_CITY
        return WEATHER_CITY


# ==================== 后台运行线程 ====================

def agent_background_worker(agent: WeatherAgent, get_sensor_callback):
    """智能体后台工作线程"""
    print("[天气Agent] 智能体后台线程启动")
    
    # 立即获取一次天气（不延迟）
    try:
        agent.update_forecast()
        # 通知主线程天气已就绪
        if hasattr(agent, '_on_ready') and agent._on_ready:
            agent._on_ready()
    except Exception as e:
        print(f"[天气Agent] 首次获取天气失败: {e}", flush=True)
    
    while True:
        try:
            # 获取当前传感器数据
            sensor_data = get_sensor_callback() if get_sensor_callback else None
            
            # 执行决策
            agent.run_decisions(sensor_data)
            
        except Exception as e:
            print(f"[天气Agent] 后台工作错误: {e}", flush=True)
        
        # 每隔决策间隔运行一次
        time.sleep(AGENT_DECISION_INTERVAL)


# ==================== 快捷创建函数 ====================

def create_agent(get_sensor_callback=None, on_ready=None) -> WeatherAgent:
    """创建并启动天气智能体"""
    agent = WeatherAgent()
    if on_ready:
        agent._on_ready = on_ready
    
    # 启动后台线程
    thread = threading.Thread(
        target=agent_background_worker,
        args=(agent, get_sensor_callback),
        daemon=True,
        name="WeatherAgent"
    )
    thread.start()
    
    return agent