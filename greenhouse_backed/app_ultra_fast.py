# app_ultra_fast.py - 超快速响应版本
import os
import sys
# 必须在 Flask 导入前设置，跳过 dotenv 加载避免 KeyboardInterrupt
os.environ['FLASK_SKIP_DOTENV'] = '1'
# 设置控制台编码为 UTF-8，避免 emoji 打印时 GBK 报错
if sys.stdout.encoding and sys.stdout.encoding.upper() != 'UTF-8':
    sys.stdout.reconfigure(encoding='utf-8')
os.environ['PYTHONIOENCODING'] = 'utf-8'

from flask import Flask, render_template, request, jsonify, Response
from flask_socketio import SocketIO, emit
import mysql.connector
import json
from datetime import datetime, timedelta
import threading
import time
import requests
import os
import subprocess
import socket

import serial
import serial.tools.list_ports

# 导入天气智能体
from weather_agent import create_agent, WeatherAgent

# ==================== 环境变量配置（生产环境覆盖） ====================
# 数据库配置
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = int(os.getenv('DB_PORT', '3306'))
DB_USER = os.getenv('DB_USER', 'root')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'hyqiuyu45')
DB_NAME = os.getenv('DB_NAME', 'sensor_db')

# 阿里云百炼 AI 配置
DASHSCOPE_API_KEY = os.getenv('DASHSCOPE_API_KEY', 'sk-323c8937b04841b983cee01f92d37d50')
DASHSCOPE_BASE_URL = os.getenv('DASHSCOPE_BASE_URL', 'https://dashscope.aliyuncs.com/compatible-mode/v1')
DASHSCOPE_MODEL = os.getenv('DASHSCOPE_MODEL', 'deepseek-v4-flash')

# 服务端口
SERVER_PORT = int(os.getenv('SERVER_PORT', '5000'))

# 后端图片目录
BACKEND_IMAGE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'image')

# ==================== 应用实例 ====================
# 前端构建输出目录
FRONTEND_DIST = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'greenhouse_fronted', 'dist')

app = Flask(__name__, 
    template_folder=FRONTEND_DIST,
    static_folder=os.path.join(FRONTEND_DIST, 'assets'),
    static_url_path='/assets')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key')
app.config['TEMPLATES_AUTO_RELOAD'] = True
socketio = SocketIO(app, cors_allowed_origins="*")

# 数据库配置对象
db_config = {
    'host': DB_HOST,
    'port': DB_PORT,
    'user': DB_USER,
    'password': DB_PASSWORD,
    'database': DB_NAME,
    'auth_plugin': 'mysql_native_password',
    'use_pure': True,
    'ssl_disabled': True
}

# 全局缓存 - 用于快速访问最新数据
latest_cache = {
    'data': None,
    'timestamp': None,
    'update_count': 0
}

# 设备状态缓存 - 专门用于设备状态快速更新
device_status_cache = {
    'pump_status': False,
    'fan_status': False,
    'motor_status': False,
    'buzzer_status': False,
    'flame_status': True,   # 默认自动
    'human_status': True,   # 默认自动
    'flame_detected': False,
    'last_update': None
}

# 设备动作缓存 - 存储 'on'/'off'/'auto' 字符串，供 zhiling.py 精确控制
# 解决 device_status_cache 只存 bool 无法区分 on 和 auto 的问题
device_action_cache = {
    'pump': 'off',
    'fan': 'off',
    'motor': 'off',
    'flame': 'auto',
    'human': 'auto',
}

# 阈值缓存 - 记录已设置的阈值
threshold_cache = {}

# 阈值数据库表名
THRESHOLD_TABLE = 'threshold_config'

def _ensure_threshold_table():
    """确保阈值配置表存在"""
    conn = get_db_connection()
    if not conn:
        return
    try:
        c = conn.cursor()
        c.execute(f"""
            CREATE TABLE IF NOT EXISTS {THRESHOLD_TABLE} (
                id INT AUTO_INCREMENT PRIMARY KEY,
                config_key VARCHAR(50) NOT NULL UNIQUE,
                config_value FLOAT,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        c.close()
        conn.close()
    except mysql.connector.Error as e:
        print(f"[阈值] 建表失败: {e}")
        try:
            conn.close()
        except:
            pass

def _load_thresholds_from_db():
    """从数据库加载阈值到缓存"""
    _ensure_threshold_table()
    conn = get_db_connection()
    if not conn:
        return
    try:
        c = conn.cursor(dictionary=True)
        c.execute(f"SELECT config_key, config_value FROM {THRESHOLD_TABLE}")
        rows = c.fetchall()
        c.close()
        conn.close()
        for row in rows:
            threshold_cache[row['config_key']] = row['config_value']
        if rows:
            print(f"[阈值] 已从数据库加载 {len(rows)} 个阈值")
    except mysql.connector.Error as e:
        print(f"[阈值] 加载失败: {e}")
        try:
            conn.close()
        except:
            pass

def _save_threshold_to_db(th_type, value):
    """保存阈值到数据库"""
    conn = get_db_connection()
    if not conn:
        return
    try:
        c = conn.cursor()
        c.execute(f"""
            INSERT INTO {THRESHOLD_TABLE} (config_key, config_value, updated_at)
            VALUES (%s, %s, NOW())
            ON DUPLICATE KEY UPDATE config_value = %s, updated_at = NOW()
        """, (th_type, value, value))
        conn.commit()
        c.close()
        conn.close()
    except mysql.connector.Error as e:
        print(f"[阈值] 保存到数据库失败: {e}")
        try:
            conn.close()
        except:
            pass

# ==================== 天气智能体 ====================
weather_agent = None
weather_agent_ready = False
server_started = False  # 标记服务器是否已就绪

def agent_sensor_callback():
    """提供给智能体的传感器数据回调"""
    return get_sensor_data_only()

def weather_push_thread():
    """定期推送天气预报和智能体决策到前端"""
    # 等待服务器完全就绪后再开始推送
    while not server_started:
        time.sleep(1)
    time.sleep(2)  # 额外等待，确保 socketio 完全初始化
    
    push_count = 0
    while True:
        try:
            if weather_agent_ready and weather_agent:
                # 如果天气缓存为空，尝试获取
                status = weather_agent.get_status()
                if status.get('forecast') is None:
                    weather_agent.update_forecast()
                    status = weather_agent.get_status()
                
                socketio.emit('weather_update', {
                    'forecast': status.get('forecast'),
                    'current_advice': status.get('current_advice'),
                    'recent_decisions': status.get('recent_decisions', []),
                    'forecast_time': status.get('forecast_time'),
                    'enabled': status.get('enabled', True)
                })
                push_count += 1
        except Exception as e:
            print(f"[天气推送] 错误: {e}")
        # 前3次快速推送(每3秒)，之后每30秒
        if push_count < 3:
            time.sleep(3)
        else:
            time.sleep(30)

# ==================== 阿里云百炼 AI 助手 ====================
def test_dashscope_connection():
    if DASHSCOPE_API_KEY == "YOUR_DASHSCOPE_API_KEY":
        return False
    try:
        headers = {
            "Authorization": f"Bearer {DASHSCOPE_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": DASHSCOPE_MODEL,
            "messages": [{"role": "user", "content": "ping"}],
            "max_tokens": 5
        }
        response = requests.post(
            f"{DASHSCOPE_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
            timeout=10
        )
        return response.status_code == 200
    except:
        return False

def generate_ai_response(user_message, sensor_context):
    """使用阿里云百炼 API 生成 AI 响应"""
    if DASHSCOPE_API_KEY == "YOUR_DASHSCOPE_API_KEY":
        return "请先配置阿里云百炼 API Key（在 app_ultra_fast.py 中设置 DASHSCOPE_API_KEY）"
    try:
        # 构建系统提示词
        system_prompt = f"""你是一个智能温室监控系统的AI助手。当前温室状态：
- 温度: {sensor_context.get('temperature', 0):.1f}°C
- 湿度: {sensor_context.get('humidity', 0):.1f}%
- 土壤湿度: {sensor_context.get('soil_moisture', 0):.1f}%
- 水位: {sensor_context.get('water_level', 0):.1f}%
- 水泵状态: {'运行中' if sensor_context.get('pump_status') else '待机'}
- 风扇状态: {'运行中' if sensor_context.get('fan_status') else '待机'}
- 马达状态: {'运行中' if sensor_context.get('motor_status') else '待机'}
- 火焰检测: {'检测到火焰' if sensor_context.get('flame_detected') else '正常'}

请基于这些数据回答用户的问题，提供专业的温室管理建议。回答要简洁明了，重点突出。"""

        headers = {
            "Authorization": f"Bearer {DASHSCOPE_API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": DASHSCOPE_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            "stream": False,
            "temperature": 0.7,
            "top_p": 0.9,
            "max_tokens": 500
        }

        response = requests.post(
            f"{DASHSCOPE_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            content = result.get('choices', [{}])[0].get('message', {}).get('content', '抱歉，我无法生成回答。')
            # 去除 markdown 加粗标记
            content = content.replace('**', '')
            return content
        else:
            return f"API 返回错误 (状态码: {response.status_code})，请检查 API Key 和网络连接。"

    except requests.exceptions.Timeout:
        return "AI响应超时，请稍后再试。"
    except requests.exceptions.ConnectionError:
        return "无法连接到阿里云百炼 API，请检查网络连接。"
    except Exception as e:
        print(f"AI生成错误: {e}")
        return "AI服务暂时不可用，请稍后再试。"

def get_db_connection():
    """建立数据库连接"""
    try:
        conn = mysql.connector.connect(**db_config)
        return conn
    except mysql.connector.Error as err:
        print(f"数据库连接错误: {err}")
        return None

def get_latest_realtime_data_cached():
    """获取缓存的实时数据"""
    return latest_cache['data'] if latest_cache['data'] else {}

def get_device_status_only():
    """仅获取设备状态，超快速查询"""
    conn = get_db_connection()
    if not conn:
        return device_status_cache
    
    cursor = conn.cursor()
    try:
        # 只查询设备状态字段，最快速查询
        cursor.execute("""
            SELECT flame_detected, pump_status, fan_status, motor_status, buzzer_status, timestamp
            FROM sensor_data 
            ORDER BY timestamp DESC 
            LIMIT 1
        """)
        result = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if result:
            new_status = {
                'flame_detected': bool(result[0]),
                'pump_status': bool(result[1]),
                'fan_status': bool(result[2]),
                'motor_status': bool(result[3]),
                'buzzer_status': bool(result[4]),
                'last_update': result[5].isoformat() if result[5] else None
            }
            
            # 检查是否有状态变化
            status_changed = False
            for key in ['flame_detected', 'pump_status', 'fan_status', 'motor_status', 'buzzer_status']:
                # 如果数据库值 ≠ 缓存值，说明有变化
                if device_status_cache[key] != new_status[key]:
                    status_changed = True
                    # 如果数据库返回 False 但缓存是 True，说明是 API 刚更新的状态但数据库还没同步
                    # 此时保留缓存的值，不向下覆盖
                    if new_status[key] is False and device_status_cache[key] is True:
                        new_status[key] = True
            
            # 更新缓存
            device_status_cache.update(new_status)
            
            return device_status_cache, status_changed
        
        return device_status_cache, False
        
    except mysql.connector.Error as err:
        print(f"设备状态查询错误: {err}")
        cursor.close()
        conn.close()
        return device_status_cache, False

def get_sensor_data_only():
    """仅获取传感器数据"""
    conn = get_db_connection()
    if not conn:
        return None
    
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT temperature, humidity, soil_moisture, water_level, co2, 
                   flame_status, human_status, timestamp
            FROM sensor_data 
            ORDER BY timestamp DESC 
            LIMIT 1
        """)
        result = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if result:
            return {
                'latest_temp': float(result[0]) if result[0] is not None else 0,
                'latest_hum': float(result[1]) if result[1] is not None else 0,
                'latest_soil': float(result[2]) if result[2] is not None else 0,
                'latest_water': float(result[3]) if result[3] is not None else 0,
                'latest_co2': int(result[4]) if result[4] is not None else 0,
                'flame_status': bool(result[5]) if result[5] is not None else True,
                'human_status': bool(result[6]) if result[6] is not None else True,
                'timestamp': result[7].isoformat() if result[7] else None
            }
        
        return None
        
    except mysql.connector.Error as err:
        print(f"传感器数据查询错误: {err}")
        cursor.close()
        conn.close()
        return None

def get_chart_data():
    """获取图表数据（包含历史数据，较慢）"""
    conn = get_db_connection()
    if not conn:
        return None
    
    cursor = conn.cursor(dictionary=True)
    try:
        # 获取最近20分钟的数据
        twenty_minutes_ago = datetime.now() - timedelta(minutes=20)
        cursor.execute("""
            SELECT 
                DATE_FORMAT(timestamp, '%H:%i') as time_label,
                temperature, 
                humidity,
                soil_moisture, 
                water_level,
                co2,
                timestamp
            FROM sensor_data 
            WHERE timestamp >= %s 
            ORDER BY timestamp
        """, (twenty_minutes_ago,))
        raw_chart_data = cursor.fetchall()
        
        # 在Python中进行数据聚合，按分钟分组
        chart_data = {}
        for row in raw_chart_data:
            time_key = row['time_label']
            if time_key not in chart_data:
                chart_data[time_key] = {
                    'time_label': time_key,
                    'temperatures': [],
                    'humidities': [],
                    'soil_moistures': [],
                    'water_levels': [],
                    'co2_values': []
                }
            
            # 收集数据用于平均值计算
            if row['temperature'] is not None:
                chart_data[time_key]['temperatures'].append(row['temperature'])
            if row['humidity'] is not None:
                chart_data[time_key]['humidities'].append(row['humidity'])
            if row['soil_moisture'] is not None:
                chart_data[time_key]['soil_moistures'].append(row['soil_moisture'])
            if row['water_level'] is not None:
                chart_data[time_key]['water_levels'].append(row['water_level'])
            if row['co2'] is not None:
                chart_data[time_key]['co2_values'].append(row['co2'])
        
        # 计算平均值
        processed_chart_data = []
        for time_key in sorted(chart_data.keys()):
            data = chart_data[time_key]
            processed_chart_data.append({
                'time_label': data['time_label'],
                'avg_temperature': sum(data['temperatures']) / len(data['temperatures']) if data['temperatures'] else 0,
                'avg_humidity': sum(data['humidities']) / len(data['humidities']) if data['humidities'] else 0,
                'avg_soil_moisture': sum(data['soil_moistures']) / len(data['soil_moistures']) if data['soil_moistures'] else 0,
                'avg_water_level': sum(data['water_levels']) / len(data['water_levels']) if data['water_levels'] else 0,
                'avg_co2': round(sum(data['co2_values']) / len(data['co2_values'])) if data['co2_values'] else 0
            })
        
        cursor.close()
        conn.close()
        
        # 准备图表数据
        result = {
            'timestamps': [row['time_label'] for row in processed_chart_data],
            'temperatures': [row['avg_temperature'] for row in processed_chart_data],
            'humidities': [row['avg_humidity'] for row in processed_chart_data],
            'soil_moistures': [row['avg_soil_moisture'] for row in processed_chart_data],
            'water_levels': [row['avg_water_level'] for row in processed_chart_data],
            'co2_values': [row['avg_co2'] for row in processed_chart_data]
        }
        
        return result
        
    except mysql.connector.Error as err:
        print(f"图表数据查询错误: {err}")
        cursor.close()
        conn.close()
        return None

def run_with_restart(target_func, name, interval=1):
    """以守护线程方式运行目标函数，崩溃后自动重启"""
    def wrapper():
        while True:
            try:
                target_func()
            except Exception as e:
                print(f"[{name}] 线程崩溃: {e}，5秒后重启...")
            time.sleep(5)
    thread = threading.Thread(target=wrapper, daemon=True, name=name)
    thread.start()
    return thread

def ultra_fast_device_monitor():
    """超快速设备状态监控 - 0.5秒更新"""
    while True:
        try:
            status, changed = get_device_status_only()
            
            if changed:
                # 立即推送设备状态变化
                try:
                    socketio.emit('device_status_update', status)
                except:
                    pass
                
                # 构建状态信息
                status_info = []
                if status['pump_status']: status_info.append("水泵运行")
                if status['fan_status']: status_info.append("风扇运行")
                if status['motor_status']: status_info.append("马达运行")
                if status['buzzer_status']: status_info.append("蜂鸣器响")
                if status['flame_detected']: status_info.append("🔥火焰报警")
                
                status_str = " | ".join(status_info) if status_info else "系统正常"
                print(f"[设备状态] {status_str}")
                        
        except Exception as e:
            print(f"设备状态监控错误: {e}")
            
        time.sleep(0.5)  # 每0.5秒检查设备状态

def fast_sensor_monitor():
    """快速传感器数据监控 - 1秒更新"""
    last_timestamp = None
    
    while True:
        try:
            sensor_data = get_sensor_data_only()
            
            if sensor_data and sensor_data['timestamp'] != last_timestamp:
                # 将 latest_* 键名转为前端期望的键名
                frontend_data = {
                    'temperature': sensor_data.get('latest_temp'),
                    'humidity': sensor_data.get('latest_hum'),
                    'soil_moisture': sensor_data.get('latest_soil'),
                    'water_level': sensor_data.get('latest_water'),
                    'co2': sensor_data.get('latest_co2'),
                    'timestamp': sensor_data.get('timestamp'),
                }
                
                # 合并设备状态
                combined_data = {**frontend_data, **device_status_cache}
                
                # 更新缓存
                latest_cache['data'] = combined_data
                latest_cache['timestamp'] = sensor_data['timestamp']
                latest_cache['update_count'] += 1
                
                # 推送传感器数据
                try:
                    socketio.emit('sensor_data_update', frontend_data)
                except:
                    pass
                
                # 推送完整实时数据（兼容）
                socketio.emit('realtime_update', combined_data)
                
                last_timestamp = sensor_data['timestamp']
                
                print(f"[传感器] 温度={sensor_data['latest_temp']:.1f}°C, "
                      f"湿度={sensor_data['latest_hum']:.1f}%, "
                      f"土壤={sensor_data['latest_soil']:.1f}%, "
                      f"水位={sensor_data['latest_water']:.1f}%")
                        
        except Exception as e:
            print(f"传感器监控错误: {e}")
            
        time.sleep(1)  # 每1秒检查传感器数据

def chart_data_monitor():
    """图表数据监控线程 - 30秒更新"""
    while True:
        try:
            chart_data = get_chart_data()
            
            if chart_data:
                socketio.emit('chart_update', chart_data)
                print(f"[图表] 推送图表数据，数据点数: {len(chart_data['timestamps'])}")
                        
        except Exception as e:
            print(f"图表监控错误: {e}")
            
        time.sleep(30)  # 每30秒推送一次图表数据

def combined_data_monitor():
    """组合数据监控 - 兼容原有接口 - 2秒更新"""
    while True:
        try:
            if latest_cache['data']:
                # 推送缓存的数据
                socketio.emit('data_update', latest_cache['data'])
                        
        except Exception as e:
            print(f"组合监控错误: {e}")
            
        time.sleep(2)  # 每2秒推送组合数据

@socketio.on('connect')
def handle_connect():
    """客户端连接时发送初始数据"""
    print('Client connected')
    
    # 立即发送设备状态
    status, _ = get_device_status_only()
    emit('device_status_update', status)
    
    # 发送传感器数据
    sensor_data = get_sensor_data_only()
    if sensor_data:
        emit('sensor_data_update', sensor_data)
        
        # 合并数据
        combined_data = {**sensor_data, **device_status_cache}
        emit('realtime_update', combined_data)
        emit('data_update', combined_data)  # 兼容
    
    # 发送图表数据
    chart_data = get_chart_data()
    if chart_data:
        emit('chart_update', chart_data)

@socketio.on('request_data')
def handle_request_data():
    """处理客户端请求数据 - 立即响应"""
    # 立即发送设备状态
    status, _ = get_device_status_only()
    emit('device_status_update', status)
    
    # 立即发送传感器数据
    sensor_data = get_sensor_data_only()
    if sensor_data:
        emit('sensor_data_update', sensor_data)
        
        # 发送组合数据（兼容）
        combined_data = {**sensor_data, **device_status_cache}
        emit('realtime_update', combined_data)
        emit('data_update', combined_data)

@socketio.on('request_device_status')
def handle_request_device_status():
    """专门的设备状态请求 - 超快响应"""
    status, _ = get_device_status_only()
    emit('device_status_update', status)

@socketio.on('request_chart_data')
def handle_request_chart_data():
    """处理客户端请求图表数据"""
    chart_data = get_chart_data()
    if chart_data:
        emit('chart_update', chart_data)

@socketio.on('request_weather')
def handle_request_weather():
    """处理客户端请求天气数据 - 强制刷新后返回"""
    if weather_agent:
        try:
            # 强制刷新天气预报（用户点击刷新按钮时）
            weather_agent.update_forecast()
            status = weather_agent.get_status()
        except Exception as e:
            print(f"[天气] 刷新天气失败: {e}")
            status = weather_agent.get_status() if weather_agent else {}
        
        emit('weather_update', {
            'forecast': status.get('forecast'),
            'current_advice': status.get('current_advice'),
            'recent_decisions': status.get('recent_decisions', []),
            'forecast_time': status.get('forecast_time'),
            'enabled': status.get('enabled', True)
        })

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

@app.route('/sketch.jpg')
def serve_sketch():
    """提供正视图图片"""
    from flask import send_from_directory
    return send_from_directory(BACKEND_IMAGE_DIR, '9af14f0c83b95eb0dd53b7e03aa9d4e2.jpg')

@app.route('/favicon.svg')
def serve_favicon():
    """提供favicon"""
    from flask import send_from_directory
    return send_from_directory(FRONTEND_DIST, 'favicon.svg')

@app.route('/topview.jpg')
def serve_topview():
    """提供俯视图图片"""
    from flask import send_from_directory
    return send_from_directory(BACKEND_IMAGE_DIR, '85b3b531d09233b253bfd207caee1ca4.jpg')

@app.route('/greenhouse_model.glb')
def serve_model():
    """提供3D模型"""
    from flask import send_from_directory
    return send_from_directory(FRONTEND_DIST, 'greenhouse_model.glb')

@app.route('/')
def index():
    """SPA 主入口"""
    return render_template('index.html')

@app.route('/fast')
def fast_index():
    """SPA 快速入口"""
    return render_template('index.html')

@app.route('/greenhouse')
def greenhouse():
    """SPA 温室页面"""
    return render_template('index.html')

@app.route('/api/ai/status')
def ai_status():
    """检查AI服务状态"""
    connected = test_dashscope_connection()
    if DASHSCOPE_API_KEY == "YOUR_DASHSCOPE_API_KEY":
        return jsonify({
            'connected': False,
            'message': '请先配置阿里云百炼 API Key（在 app_ultra_fast.py 中设置 DASHSCOPE_API_KEY）',
            'model': None
        })
    return jsonify({
        'connected': connected,
        'message': 'AI助手已就绪' if connected else '无法连接到阿里云百炼 API，请检查 API Key 和网络连接',
        'model': DASHSCOPE_MODEL if connected else None
    })

@app.route('/api/ai/chat', methods=['POST'])
def ai_chat():
    """AI聊天接口"""
    try:
        data = request.get_json()
        user_message = data.get('message', '').strip()
        context = data.get('context', {})
        
        if not user_message:
            return jsonify({
                'success': False,
                'error': '消息不能为空'
            })
        
        # 检查AI服务连接
        if DASHSCOPE_API_KEY == "YOUR_DASHSCOPE_API_KEY":
            return jsonify({
                'success': False,
                'error': 'API Key 未配置',
                'response': '请先配置阿里云百炼 API Key（在 app_ultra_fast.py 中设置 DASHSCOPE_API_KEY）'
            })
        if not test_dashscope_connection():
            return jsonify({
                'success': False,
                'error': '无法连接到AI服务',
                'response': '很抱歉，AI助手目前不可用。请检查阿里云百炼 API Key 和网络连接，或稍后再试。'
            })
        
        # 从数据库获取实时传感器数据
        sensor_data = get_sensor_data_only()
        device_status, _ = get_device_status_only()
        
        # 构建传感器上下文（覆盖前端传入的 context）
        context = {
            'temperature': sensor_data.get('latest_temp', 0) if sensor_data else 0,
            'humidity': sensor_data.get('latest_hum', 0) if sensor_data else 0,
            'soil_moisture': sensor_data.get('latest_soil', 0) if sensor_data else 0,
            'water_level': sensor_data.get('latest_water', 0) if sensor_data else 0,
            'pump_status': device_status.get('pump_status', False) if device_status else False,
            'fan_status': device_status.get('fan_status', False) if device_status else False,
            'motor_status': device_status.get('motor_status', False) if device_status else False,
            'flame_detected': device_status.get('flame_detected', False) if device_status else False,
        }
        
        # 生成AI响应
        ai_response = generate_ai_response(user_message, context)
        
        return jsonify({
            'success': True,
            'response': ai_response,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        print(f"AI聊天错误: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'response': '处理您的请求时出现错误，请稍后再试。'
        })

# ==================== 天气智能体 API ====================

@app.route('/api/weather')
def api_weather():
    """获取天气预报"""
    if not weather_agent:
        return jsonify({'success': False, 'error': '智能体未初始化'})
    forecast = weather_agent.get_forecast()
    if forecast:
        return jsonify({'success': True, 'forecast': forecast})
    return jsonify({'success': False, 'error': '天气预报数据不可用，请先配置 WEATHER_API_KEY'})

@app.route('/api/weather/refresh')
def api_weather_refresh():
    """手动刷新天气预报"""
    if not weather_agent:
        return jsonify({'success': False, 'error': '智能体未初始化'})
    success = weather_agent.update_forecast()
    return jsonify({'success': success, 'message': '天气已更新' if success else '更新失败'})

@app.route('/api/weather/set_city', methods=['POST'])
def api_weather_set_city():
    """切换天气预报城市"""
    if not weather_agent:
        return jsonify({'success': False, 'error': '智能体未初始化'})
    data = request.get_json() or {}
    city = data.get('city', '').strip()
    if not city:
        return jsonify({'success': False, 'error': '城市名不能为空'})
    success = weather_agent.set_city(city)
    if success:
        # 获取最新天气数据
        try:
            status = weather_agent.get_status()
            forecast = status.get('forecast')
            socketio.emit('weather_update', {
                'forecast': forecast,
                'current_advice': status.get('current_advice'),
                'recent_decisions': status.get('recent_decisions', []),
                'forecast_time': status.get('forecast_time'),
                'enabled': status.get('enabled', True)
            })
        except Exception as e:
            print(f"[天气] 推送新城市天气失败: {e}")
        
        # 返回天气数据，前端直接使用
        status = weather_agent.get_status()
        return jsonify({
            'success': True,
            'city': city,
            'message': f'已切换至 {city}',
            'forecast': status.get('forecast'),
            'forecast_time': status.get('forecast_time')
        })
    return jsonify({'success': False, 'error': f'切换城市失败，请检查城市名: {city}'})

@app.route('/api/weather/current_city')
def api_weather_current_city():
    """获取当前天气预报城市"""
    if not weather_agent:
        return jsonify({'success': False, 'error': '智能体未初始化'})
    city = weather_agent.get_current_city()
    return jsonify({'success': True, 'city': city})

@app.route('/api/agent/status')
def api_agent_status():
    """获取智能体状态"""
    if not weather_agent:
        return jsonify({'success': False, 'error': '智能体未初始化'})
    status = weather_agent.get_status()
    return jsonify({'success': True, **status})

@app.route('/api/agent/decisions')
def api_agent_decisions():
    """获取决策日志"""
    if not weather_agent:
        return jsonify({'success': False, 'error': '智能体未初始化'})
    limit = request.args.get('limit', 20, type=int)
    decisions = weather_agent.get_decisions(limit)
    return jsonify({'success': True, 'decisions': decisions, 'total': len(weather_agent.decisions)})

@app.route('/api/agent/toggle', methods=['POST'])
def api_agent_toggle():
    """切换智能体启用/禁用"""
    if not weather_agent:
        return jsonify({'success': False, 'error': '智能体未初始化'})
    data = request.get_json() or {}
    enabled = data.get('enabled')
    status = weather_agent.toggle(enabled)
    return jsonify({'success': True, 'enabled': status})

# ==================== 明天天气预报与建议 API ====================

@app.route('/api/weather/tomorrow_suggestions')
def api_tomorrow_suggestions():
    """获取明天天气预报及可执行建议（含设备控制指令）"""
    if not weather_agent:
        return jsonify({'success': False, 'error': '智能体未初始化'})
    
    forecast = weather_agent.get_forecast()
    if not forecast or not forecast.get('forecast'):
        # 尝试刷新
        weather_agent.update_forecast()
        forecast = weather_agent.get_forecast()
    
    if not forecast or not forecast.get('forecast'):
        return jsonify({'success': False, 'error': '天气预报数据不可用，请先配置 WEATHER_API_KEY'})
    
    # 获取明天的预报
    tomorrow = datetime.now() + timedelta(days=1)
    tomorrow_date = tomorrow.date()
    
    tomorrow_forecasts = [f for f in forecast['forecast']
                         if datetime.fromtimestamp(f['dt']).date() == tomorrow_date]
    
    if not tomorrow_forecasts:
        # 如果预报数据不足2天，使用剩余所有数据作为"明天"参考
        half = len(forecast['forecast']) // 2
        tomorrow_forecasts = forecast['forecast'][half:]
    
    if not tomorrow_forecasts:
        return jsonify({'success': False, 'error': '明天预报数据不足'})
    
    # 分析明天天气
    temps = [f['temp'] for f in tomorrow_forecasts]
    max_temp = max(temps)
    min_temp = min(temps)
    avg_temp = sum(temps) / len(temps)
    
    has_rain = any(f.get('pop', 0) > 0.3 for f in tomorrow_forecasts)
    heavy_rain = any(f.get('pop', 0) > 0.7 for f in tomorrow_forecasts)
    
    # 获取当前传感器数据辅助判断
    sensor_data = get_sensor_data_only()
    soil_moisture = sensor_data.get('latest_soil', 50) if sensor_data else 50
    
    # 生成建议和可执行指令
    suggestions = []
    
    # --- 降雨建议 ---
    if heavy_rain:
        suggestions.append({
            'type': 'device',
            'icon': '⛈️',
            'suggestion': '明天预计有大雨，建议关闭水泵',
            'reason': f'降雨概率 {(max(f.get("pop",0) for f in tomorrow_forecasts)*100):.0f}%，自然降雨可充分补充水分',
            'commands': [
                {'device': 'pump', 'action': 'off', 'label': '关闭水泵'}
            ]
        })
    elif has_rain:
        suggestions.append({
            'type': 'device',
            'icon': '🌧️',
            'suggestion': '明天预计有雨，建议减少灌溉或关闭水泵',
            'reason': '有降雨预报，适当降低灌溉量防止过湿',
            'commands': [
                {'device': 'pump', 'action': 'off', 'label': '关闭水泵'}
            ]
        })
    elif soil_moisture < 30:
        # 土壤干燥且无雨，建议灌溉
        suggestions.append({
            'type': 'device',
            'icon': '💧',
            'suggestion': '明天无雨且土壤偏干，建议开启水泵灌溉',
            'reason': f'土壤湿度 {soil_moisture:.0f}% 偏低，无降雨预报，需人工灌溉',
            'commands': [
                {'device': 'pump', 'action': 'on', 'label': '开启水泵'}
            ]
        })
    
    # --- 高温建议 ---
    if max_temp >= 35:
        suggestions.append({
            'type': 'device',
            'icon': '🔥',
            'suggestion': '明天高温，建议开启风扇通风降温',
            'reason': f'预计最高温度 {max_temp:.1f}°C，超过35°C阈值',
            'commands': [
                {'device': 'fan', 'action': 'on', 'label': '开启风扇'}
            ]
        })
    elif max_temp >= 30:
        suggestions.append({
            'type': 'device',
            'icon': '🌡️',
            'suggestion': '明天温度较高，可提前开启风扇通风',
            'reason': f'预计最高温度 {max_temp:.1f}°C，建议提前通风',
            'commands': [
                {'device': 'fan', 'action': 'on', 'label': '开启风扇'}
            ]
        })
    
    # --- 低温建议 ---
    if min_temp <= 5:
        suggestions.append({
            'type': 'device',
            'icon': '🥶',
            'suggestion': '明天低温，建议关闭风扇保温',
            'reason': f'预计最低温度 {min_temp:.1f}°C，低于5°C阈值',
            'commands': [
                {'device': 'fan', 'action': 'off', 'label': '关闭风扇'}
            ]
        })
    
    # --- 阈值调整建议 ---
    # 大雨/有雨时建议降低土壤湿度阈值，避免误触灌溉
    if heavy_rain or has_rain:
        suggestions.append({
            'type': 'threshold',
            'icon': '🌱',
            'suggestion': '明天有雨，建议调低土壤湿度阈值',
            'reason': '降低土壤湿度报警阈值，避免因降雨触发误报警',
            'commands': [
                {'type': 'threshold', 'sensorType': 'soil', 'value': 40, 'label': '土壤阈值→40%'}
            ]
        })
    elif soil_moisture < 30:
        # 土壤干且无雨，建议提高土壤湿度阈值保持灌溉
        suggestions.append({
            'type': 'threshold',
            'icon': '🌱',
            'suggestion': '土壤偏干且无雨，建议提高土壤湿度阈值',
            'reason': f'当前土壤湿度 {soil_moisture:.0f}%，适当提高阈值保持灌溉频率',
            'commands': [
                {'type': 'threshold', 'sensorType': 'soil', 'value': 60, 'label': '土壤阈值→60%'}
            ]
        })

    # 高温时建议提高温度阈值
    if max_temp >= 35:
        suggestions.append({
            'type': 'threshold',
            'icon': '🌡️',
            'suggestion': '明天高温，建议调高温度报警阈值',
            'reason': f'预计最高 {max_temp:.1f}°C，提高温度阈值避免频繁报警',
            'commands': [
                {'type': 'threshold', 'sensorType': 'temp', 'value': 38, 'label': '温度阈值→38°C'}
            ]
        })

    # 低温时建议降低温度阈值
    if min_temp <= 5:
        suggestions.append({
            'type': 'threshold',
            'icon': '🌡️',
            'suggestion': '明天低温，建议调低温度报警阈值',
            'reason': f'预计最低 {min_temp:.1f}°C，降低温度阈值避免低温误报',
            'commands': [
                {'type': 'threshold', 'sensorType': 'temp', 'value': 3, 'label': '温度阈值→3°C'}
            ]
        })

    # --- 默认正常建议 ---
    if not suggestions:
        suggestions.append({
            'type': 'info',
            'icon': '✅',
            'suggestion': '明天天气正常，设备按当前设置运行即可',
            'reason': f'气温 {min_temp:.1f}~{max_temp:.1f}°C，无极端天气',
            'commands': []
        })
    
    # 明天的天气描述
    mid_idx = len(tomorrow_forecasts) // 2
    weather_desc = tomorrow_forecasts[mid_idx].get('weather', '未知')
    weather_main = tomorrow_forecasts[mid_idx].get('weather_main', '')
    weather_code = tomorrow_forecasts[mid_idx].get('weather_code', 800)
    
    return jsonify({
        'success': True,
        'tomorrow': {
            'date': tomorrow_date.strftime('%Y-%m-%d'),
            'max_temp': round(max_temp, 1),
            'min_temp': round(min_temp, 1),
            'avg_temp': round(avg_temp, 1),
            'avg_hum': round(sum(f['humidity'] for f in tomorrow_forecasts) / len(tomorrow_forecasts), 1),
            'has_rain': has_rain,
            'heavy_rain': heavy_rain,
            'weather_desc': weather_desc,
            'weather_main': weather_main,
            'weather_code': weather_code
        },
        'suggestions': suggestions
    })

# ==================== 地图数据代理 API（含路径简化） ====================

import math

def _dp_distance(p, a, b):
    """点到线段的垂直距离（经纬度坐标）"""
    x0, y0 = p
    x1, y1 = a
    x2, y2 = b
    if x1 == x2 and y1 == y2:
        return math.sqrt((x0 - x1)**2 + (y0 - y1)**2)
    num = abs((y2 - y1) * x0 - (x2 - x1) * y0 + x2 * y1 - y2 * x1)
    den = math.sqrt((y2 - y1)**2 + (x2 - x1)**2)
    return num / den

def _douglas_peucker(points, epsilon):
    """Douglas-Peucker 路径简化算法"""
    if len(points) <= 2:
        return points
    dmax, idx = 0, 0
    for i in range(1, len(points) - 1):
        d = _dp_distance(points[i], points[0], points[-1])
        if d > dmax:
            dmax, idx = d, i
    if dmax > epsilon:
        left = _douglas_peucker(points[:idx + 1], epsilon)
        right = _douglas_peucker(points[idx:], epsilon)
        return left[:-1] + right
    return [points[0], points[-1]]

def _simplify_ring(ring, epsilon):
    """简化单个环（首尾相连的闭合环）"""
    if len(ring) <= 4:
        return ring
    if ring[0] == ring[-1]:
        simplified = _douglas_peucker(ring[:-1], epsilon)
        simplified.append(simplified[0])
        return simplified
    return _douglas_peucker(ring, epsilon)

def simplify_geojson(geojson, epsilon=0.008):
    """简化GeoJSON中的路径坐标，减少渲染点数
    
    根据几何类型直接处理坐标层级：
    - Polygon:     coordinates = [[ring1], [ring2], ...]  每个ring是[[lng,lat],...]
    - MultiPolygon: coordinates = [[[ring1],[ring2]], ...] 每组polygon内是rings
    
    Args:
        geojson: 解析后的GeoJSON字典
        epsilon: 简化阈值（度），0.008≈0.9km，可减少约70%点
    Returns:
        简化后的GeoJSON字典
    """
    if not geojson or 'features' not in geojson:
        return geojson
    for feature in geojson['features']:
        geom = feature.get('geometry')
        if not geom or not geom.get('coordinates'):
            continue
        gtype = geom['type']
        coords = geom['coordinates']
        if gtype == 'Polygon':
            # Polygon: [[lng,lat], [lng,lat], ...] 直接是rings列表
            geom['coordinates'] = [
                _simplify_ring(ring, epsilon) for ring in coords
            ]
        elif gtype == 'MultiPolygon':
            # MultiPolygon: [[[ring1],[ring2]], [[ring3],[ring4]]]
            geom['coordinates'] = [
                [_simplify_ring(ring, epsilon) for ring in polygon]
                for polygon in coords
            ]
    return geojson

@app.route('/api/map/geo/<path:adcode>')
def api_map_geo(adcode):
    """代理获取DataV地图GeoJSON数据，自动简化路径减少渲染卡顿"""
    try:
        url = f"https://geo.datav.aliyun.com/areas_v3/bound/{adcode}"
        resp = requests.get(url, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            # 简化路径：减少约50%的坐标点
            simplified = simplify_geojson(data, epsilon=0.02)
            return Response(
                json.dumps(simplified, ensure_ascii=False),
                mimetype='application/json'
            )
        return jsonify({'success': False, 'error': f'地图数据获取失败: {resp.status_code}'}), 502
    except Exception as e:
        print(f"[地图代理] 错误: {e}")
        return jsonify({'success': False, 'error': str(e)}), 502

# ==================== 健康检查 ====================

@app.route('/api/health')
def api_health():
    """系统健康检查"""
    return jsonify({
        'success': True,
        'status': 'running',
        'db_connected': get_db_connection() is not None,
        'weather_agent_ready': weather_agent_ready,
        'server_started': server_started
    })

# ==================== 阈值设置 API ====================

@app.route('/api/threshold/set', methods=['POST'])
def api_threshold_set():
    """设置传感器阈值：向串口发送 SET_xxx 指令"""
    data = request.get_json() or {}
    th_type = data.get('type', '')       # temp, hum, soil, water, co2
    value = data.get('value', 0)
    
    type_map = {
        'temp': 'SET_TEMP',
        'hum': 'SET_HUMI',
        'soil': 'SET_SOIL',
        'water': 'SET_WATER',
        'co2': 'SET_CO2'
    }
    cmd_prefix = type_map.get(th_type)
    if not cmd_prefix:
        return jsonify({'success': False, 'error': f'未知类型: {th_type}'})
    
    cmd = f"{cmd_prefix} {value}"
    try:
        with open(CMD_FILE, 'w') as f:
            json.dump({'cmd': cmd, 'pending': True}, f)
        # 缓存已设置的阈值
        threshold_cache[th_type] = value
        # 写入数据库持久化
        _save_threshold_to_db(th_type, value)
        print(f"[阈值] 写入指令: {cmd}")
        return jsonify({'success': True, 'cmd': cmd, 'message': f'指令 {cmd} 已发送'})
    except Exception as e:
        print(f"[阈值] 错误: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/threshold/query', methods=['POST'])
def api_threshold_query():
    """查询传感器阈值：从缓存中获取已设置的阈值"""
    data = request.get_json() or {}
    th_type = data.get('type', '')       # temp, hum, soil, water, co2
    
    if not th_type:
        return jsonify({'success': False, 'error': '缺少参数 type'})
    
    # 从缓存中获取已设置的阈值，如果没有则返回默认值
    value = threshold_cache.get(th_type, None)
    
    # 同时向串口发送查询指令（兼容 Arduino 响应）
    type_map = {
        'temp': 'GET_TEMP',
        'hum': 'GET_HUMI',
        'soil': 'GET_SOIL',
        'water': 'GET_WATER',
        'co2': 'GET_CO2'
    }
    cmd = type_map.get(th_type)
    if cmd:
        try:
            with open(CMD_FILE, 'w') as f:
                json.dump({'cmd': cmd, 'pending': True}, f)
        except Exception:
            pass
    
    label_map = {
        'temp': '温度', 'hum': '湿度',
        'soil': '土壤湿度', 'water': '水位', 'co2': 'CO2'
    }
    label = label_map.get(th_type, th_type)
    
    if value is not None:
        return jsonify({
            'success': True,
            'type': th_type,
            'value': value,
            'message': f'当前{label}的阈值是{value}'
        })
    else:
        return jsonify({
            'success': True,
            'type': th_type,
            'value': None,
            'message': f'当前{label}的阈值尚未设置'
        })

# ==================== 设备控制 API ====================

# 串口命令队列文件（仅用于发送指令到 Arduino）
CMD_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'serial_cmd.json')

def send_serial_command_direct(cmd):
    """尝试直接通过串口发送指令到 Arduino（绕过命令文件）"""
    try:
        # 查找 Arduino 串口
        ports = list(serial.tools.list_ports.comports())
        keywords = ['CH340', 'Arduino', 'USB-SERIAL', 'CP210']
        for port in ports:
            for kw in keywords:
                if kw.upper() in port.description.upper():
                    try:
                        s = serial.Serial(port.device, 9600, timeout=1)
                        s.write((cmd + '\n').encode('utf-8'))
                        s.close()
                        print(f"📤 [直接串口] 发送指令: {cmd} → {port.device}")
                        return True
                    except:
                        continue
    except Exception as e:
        print(f"⚠️ 直接串口发送失败: {e}")
    return False

@app.route('/api/device/control', methods=['POST'])
def api_device_control():
    """控制设备开关：更新数据库、缓存，并写入串口指令"""
    data = request.get_json() or {}
    device = data.get('device', '')
    action = data.get('action', '')
    
    if not device or not action:
        return jsonify({'success': False, 'error': '缺少参数'})
    
    # 根据 Arduino 指令格式生成命令
    # 风扇: FAN_ON, FAN_OFF, FAN_AUTO
    # 水泵: 1(开), 0(关), auto(自动)
    # 火焰/人体: FLAME_ON/OFF/AUTO, HUMAN_ON/OFF/AUTO
    if device == 'pump':
        # 水泵特殊处理：1=开, 0=关, auto=自动
        cmd_map = {'on': '1', 'off': '0', 'auto': 'auto'}
        cmd = cmd_map.get(action, action)
    else:
        # 其他设备全部大写: FAN_ON, FLAME_AUTO, etc.
        dev_upper = device.upper()
        act_upper = action.upper()
        cmd = f"{dev_upper}_{act_upper}"
    
    is_on = (action == 'on' or action == 'auto')
    
    db_field_map = {
        'pump': 'pump_status', 'fan': 'fan_status',
        'motor': 'motor_status', 'buzzer': 'buzzer_status'
    }
    db_field = db_field_map.get(device)
    # 警报设备（flame/human）无数据库字段，仅通过缓存和串口管理
    is_alarm = device in ('flame', 'human')
    
    try:
        # 1. 更新数据库最新一条记录
        if db_field and not is_alarm:
            conn = get_db_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute(f"""
                    UPDATE sensor_data SET {db_field} = %s
                    ORDER BY timestamp DESC LIMIT 1
                """, (is_on,))
                conn.commit()
                cursor.close()
                conn.close()
        elif is_alarm:
            # 警报设备也写入数据库，持久化状态
            db_col = f'{device}_status'
            conn = get_db_connection()
            if conn:
                cursor = conn.cursor()
                try:
                    cursor.execute(f"""
                        UPDATE sensor_data SET {db_col} = %s
                        ORDER BY timestamp DESC LIMIT 1
                    """, (is_on,))
                    conn.commit()
                except Exception:
                    pass  # 旧表可能没有该列，忽略
                cursor.close()
                conn.close()
        
        # 2. 更新内存缓存
        if db_field:
            device_status_cache[db_field] = is_on
        elif is_alarm:
            device_status_cache[f'{device}_status'] = is_on
        # 更新动作缓存（存储 'on'/'off'/'auto' 字符串）
        device_action_cache[device] = action
        
        # 3. 尝试直接通过串口发送指令（立即生效）
        direct_ok = send_serial_command_direct(cmd)
        if not direct_ok:
            # 如果直接发送失败，写入命令文件（serial_to_db_fixed.py 会读取并发送）
            with open(CMD_FILE, 'w') as f:
                json.dump({'cmd': cmd, 'pending': True}, f)
            print(f"📝 [命令文件] {cmd} → 已写入队列，等待 serial_to_db_fixed.py 发送")
        else:
            # 直接发送成功，清空命令文件避免重复发送
            with open(CMD_FILE, 'w') as f:
                json.dump({'cmd': '', 'pending': False}, f)
        
        print(f"[设备控制] {cmd} → 数据库+缓存已更新")
        return jsonify({'success': True, 'cmd': cmd, 'message': f'{device} 已{"开启" if is_on else "关闭"}'})
    except Exception as e:
        print(f"[设备控制] 错误: {e}")
        return jsonify({'success': False, 'error': str(e)})

# ==================== ADP-L610 Arduino 数据接收 API ====================

# 字段名映射表：将外部设备可能的字段名统一映射到数据库字段
ADP610_FIELD_MAP = {
    # 温度
    'temperature': 'temperature', 'temp': 'temperature', 't': 'temperature',
    # 湿度
    'humidity': 'humidity', 'hum': 'humidity', 'h': 'humidity',
    # 土壤湿度
    'soil_moisture': 'soil_moisture', 'soil': 'soil_moisture', 'soilMoisture': 'soil_moisture',
    # 水位
    'water_level': 'water_level', 'water': 'water_level', 'waterLevel': 'water_level',
    'distance': 'water_level', 'dist': 'water_level',
    # CO2
    'co2': 'co2', 'co2_value': 'co2', 'co2Value': 'co2',
    # 火焰检测
    'flame_detected': 'flame_detected', 'flame': 'flame_detected', 'flameDetected': 'flame_detected',
    # 人体检测
    'human_detected': 'human_detected', 'human': 'human_detected', 'humanDetected': 'human_detected',
    # 设备状态
    'pump_status': 'pump_status', 'pump': 'pump_status',
    'fan_status': 'fan_status', 'fan': 'fan_status',
    'motor_status': 'motor_status', 'motor': 'motor_status',
    'buzzer_status': 'buzzer_status', 'buzzer': 'buzzer_status',
}

@app.route('/api/adp610/data', methods=['GET', 'POST'])
def api_adp610_data():
    """ADP-L610 Arduino 数据接口

    POST: 接收传感器数据，字段名灵活映射
    GET:  返回当前设备控制命令（供开发板轮询）
    """
    if request.method == 'GET':
        return api_device_commands()

    """支持 JSON 格式 POST，字段名灵活映射（如 temperature/temp、humidity/hum 等）。
    示例请求:
        POST /api/adp610/data
        Content-Type: application/json
        {
            "temperature": 25.5,
            "humidity": 65.2,
            "soil_moisture": 45.0,
            "water_level": 18.5,
            "co2": 400,
            "flame_detected": 0
        }
    """
    try:
        # 打印原始请求体（无论是否为 JSON）
        raw_body = request.get_data(as_text=True)
        print(f"[ADP-L610] 原始请求体: {raw_body}")
        print(f"[ADP-L610] 请求头: {dict(request.headers)}")

        data = request.get_json(force=True, silent=True)
        if not data:
            return jsonify({'success': False, 'error': f'请求体不是有效的 JSON，原始内容: {raw_body[:500]}'}), 400

        print(f"[ADP-L610] 解析后数据: {json.dumps(data, ensure_ascii=False)}")

        # 解析字段：将外部字段名映射到数据库字段名
        parsed = {}
        for ext_key, ext_value in data.items():
            db_key = ADP610_FIELD_MAP.get(ext_key.lower())
            if db_key:
                parsed[db_key] = ext_value

        if not parsed:
            return jsonify({'success': False, 'error': '未识别到有效的数据字段'}), 400

        # 构建插入数据
        now = datetime.now()
        insert_data = {
            'timestamp': now,
            'temperature': parsed.get('temperature'),
            'humidity': parsed.get('humidity'),
            'soil_moisture': parsed.get('soil_moisture'),
            'water_level': parsed.get('water_level'),
            'co2': parsed.get('co2'),
            'flame_detected': bool(parsed.get('flame_detected', 0)),
            'pump_status': bool(parsed.get('pump_status', False)),
            'fan_status': bool(parsed.get('fan_status', False)),
            'motor_status': bool(parsed.get('motor_status', False)),
            'buzzer_status': bool(parsed.get('buzzer_status', False)),
        }

        # 写入数据库
        conn = get_db_connection()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO sensor_data
                    (timestamp, temperature, humidity, soil_moisture, water_level, co2,
                     flame_detected, pump_status, fan_status, motor_status, buzzer_status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    insert_data['timestamp'],
                    insert_data['temperature'],
                    insert_data['humidity'],
                    insert_data['soil_moisture'],
                    insert_data['water_level'],
                    insert_data['co2'],
                    insert_data['flame_detected'],
                    insert_data['pump_status'],
                    insert_data['fan_status'],
                    insert_data['motor_status'],
                    insert_data['buzzer_status'],
                ))
                conn.commit()
                cursor.close()
                conn.close()
                print(f"[ADP-L610] 数据已写入数据库")
            except mysql.connector.Error as e:
                print(f"[ADP-L610] 数据库写入失败: {e}")
                try:
                    conn.close()
                except:
                    pass

        # 更新缓存并推送实时数据
        sensor_update = {
            'latest_temp': insert_data['temperature'],
            'latest_hum': insert_data['humidity'],
            'latest_soil': insert_data['soil_moisture'],
            'latest_water': insert_data['water_level'],
            'latest_co2': insert_data['co2'],
            'timestamp': now.isoformat(),
        }
        latest_cache['data'] = {**sensor_update, **device_status_cache}
        latest_cache['timestamp'] = now.isoformat()
        latest_cache['update_count'] += 1

        # 实时推送
        try:
            socketio.emit('realtime_update', {
                'temperature': insert_data['temperature'],
                'humidity': insert_data['humidity'],
                'soil_moisture': insert_data['soil_moisture'],
                'water_level': insert_data['water_level'],
                'co2': insert_data['co2'],
                'flame_detected': insert_data['flame_detected'],
                'pump_status': insert_data['pump_status'],
                'fan_status': insert_data['fan_status'],
                'motor_status': insert_data['motor_status'],
                'buzzer_status': insert_data['buzzer_status'],
                'timestamp': now.isoformat(),
            })
        except Exception as e:
            print(f"[ADP-L610] Socket.IO 推送失败: {e}")

        # 记录日志
        temp_str = f"{insert_data['temperature']:.1f}°C" if insert_data['temperature'] is not None else "--"
        hum_str = f"{insert_data['humidity']:.1f}%" if insert_data['humidity'] is not None else "--"
        soil_str = f"{insert_data['soil_moisture']:.1f}%" if insert_data['soil_moisture'] is not None else "--"
        water_str = f"{insert_data['water_level']:.1f}%" if insert_data['water_level'] is not None else "--"
        print(f"[ADP-L610] 温度={temp_str} 湿度={hum_str} 土壤={soil_str} 水位={water_str}")

        return jsonify({
            'success': True,
            'message': '数据已接收',
            'received_fields': list(parsed.keys()),
            'timestamp': now.isoformat(),
        })

    except Exception as e:
        print(f"[ADP-L610] 处理错误: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/adp610/health')
def api_adp610_health():
    """ADP-L610 接口健康检查"""
    return jsonify({
        'success': True,
        'status': 'ready',
        'endpoint': '/api/adp610/data',
        'method': 'POST',
        'content_type': 'application/json',
        'timestamp': datetime.now().isoformat(),
    })

@app.route('/api/device/commands', methods=['GET'])
def api_device_commands():
    """获取当前控制命令状态（开发板轮询用）
    
    设备状态从内存缓存读取（前端修改后立即更新，不会被新数据覆盖）
    传感器数据从数据库读取最新记录
    阈值从数据库读取（缓存后备）
    """
    db_sensor = {}
    db_threshold = {}

    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT temperature, humidity, soil_moisture, water_level, co2
                FROM sensor_data
                ORDER BY timestamp DESC
                LIMIT 1
            """)
            row = cursor.fetchone()
            if row:
                db_sensor = {
                    'temperature': float(row[0]) if row[0] is not None else None,
                    'humidity': float(row[1]) if row[1] is not None else None,
                    'soil_moisture': float(row[2]) if row[2] is not None else None,
                    'water_level': float(row[3]) if row[3] is not None else None,
                    'co2': int(row[4]) if row[4] is not None else None,
                }
            # 读取阈值
            cursor.execute(f"SELECT config_key, config_value FROM {THRESHOLD_TABLE}")
            for row in cursor.fetchall():
                db_threshold[row[0]] = row[1]
            cursor.close()
            conn.close()
        except mysql.connector.Error:
            cursor.close()
            conn.close()

    commands = {
        'sensor': {
            'temperature': db_sensor.get('temperature'),
            'humidity': db_sensor.get('humidity'),
            'soil_moisture': db_sensor.get('soil_moisture'),
            'water_level': db_sensor.get('water_level'),
            'co2': db_sensor.get('co2'),
        },
        # 设备状态从动作缓存读取（存储 'on'/'off'/'auto' 字符串）
        'device': {
            'pump': device_action_cache.get('pump', 'off'),
            'fan': device_action_cache.get('fan', 'off'),
            'motor': device_action_cache.get('motor', 'off'),
            'buzzer': device_action_cache.get('buzzer', 'off'),
            'flame': device_action_cache.get('flame', 'auto'),
            'human': device_action_cache.get('human', 'auto'),
        },
        'threshold': {
            'temp': db_threshold.get('temp', threshold_cache.get('temp')),
            'hum': db_threshold.get('hum', threshold_cache.get('hum')),
            'soil': db_threshold.get('soil', threshold_cache.get('soil')),
            'water': db_threshold.get('water', threshold_cache.get('water')),
            'co2': db_threshold.get('co2', threshold_cache.get('co2')),
        },
        'timestamp': datetime.now().isoformat()
    }
    return jsonify({'success': True, 'commands': commands})

@app.route('/api/agent/refresh', methods=['POST'])
def api_agent_refresh():
    """手动刷新天气预报"""
    if not weather_agent:
        return jsonify({'success': False, 'error': '智能体未初始化'})
    success = weather_agent.update_forecast()
    return jsonify({'success': success, 'message': '天气已更新' if success else '更新失败'})

@app.route('/api/recent_data')
def api_recent_data():
    """获取最近20分钟的传感器数据（用于首页迷你图表）"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'error': '数据库连接失败'})
    
    cursor = conn.cursor(dictionary=True)
    try:
        twenty_minutes_ago = datetime.now() - timedelta(minutes=20)
        cursor.execute("""
            SELECT 
                timestamp,
                temperature, humidity, soil_moisture, water_level
            FROM sensor_data 
            WHERE timestamp >= %s 
            ORDER BY timestamp ASC
        """, (twenty_minutes_ago,))
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        
        # 格式化数据
        data = []
        for r in rows:
            data.append({
                'timestamp': r['timestamp'].strftime('%H:%M') if r['timestamp'] else '',
                'temperature': r['temperature'],
                'humidity': r['humidity'],
                'soil_moisture': r['soil_moisture'],
                'water_level': r['water_level']
            })
        
        return jsonify({'success': True, 'data': data})
    except mysql.connector.Error as err:
        cursor.close()
        conn.close()
        return jsonify({'success': False, 'error': str(err)})

@app.route('/api/history/500')
def api_history_500():
    """获取最近500条传感器数据"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'error': '数据库连接失败'})
    
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT 
                timestamp,
                temperature, humidity, soil_moisture, water_level
            FROM sensor_data 
            ORDER BY timestamp DESC 
            LIMIT 500
        """)
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        
        # 倒序排列（最早的在前）
        rows.reverse()
        
        data = []
        for r in rows:
            data.append({
                'timestamp': r['timestamp'].strftime('%Y-%m-%d %H:%M:%S') if r['timestamp'] else '',
                'temperature': r['temperature'],
                'humidity': r['humidity'],
                'soil_moisture': r['soil_moisture'],
                'water_level': r['water_level']
            })
        
        return jsonify({'success': True, 'data': data, 'total': len(data)})
    except mysql.connector.Error as err:
        cursor.close()
        conn.close()
        return jsonify({'success': False, 'error': str(err)})

@app.route('/history')
def history():
    """历史数据页面（SPA）"""
    return render_template('index.html')

@app.route('/control')
def control():
    """设备控制页面（SPA）"""
    return render_template('index.html')

@app.route('/api/history')
def api_history():
    """获取历史数据 API
    ?range=today|7days|month
    """
    range_type = request.args.get('range', 'today')
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'error': '数据库连接失败'})
    
    cursor = conn.cursor(dictionary=True)
    try:
        now = datetime.now()
        if range_type == 'today':
            start_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif range_type == '7days':
            start_time = now - timedelta(days=7)
        elif range_type == 'month':
            start_time = now - timedelta(days=30)
        else:
            start_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        cursor.execute("""
            SELECT 
                timestamp,
                temperature, humidity, soil_moisture, water_level, co2,
                flame_detected, pump_status, fan_status, motor_status, buzzer_status
            FROM sensor_data 
            WHERE timestamp >= %s 
            ORDER BY timestamp ASC
        """, (start_time,))
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        
        # 用Python格式化时间字符串
        def fmt_ts(dt):
            if dt is None:
                return '--'
            return dt.strftime('%Y-%m-%d %H:%M')
        
        # 计算统计信息
        temps = [r['temperature'] for r in rows if r['temperature'] is not None]
        hums = [r['humidity'] for r in rows if r['humidity'] is not None]
        soils = [r['soil_moisture'] for r in rows if r['soil_moisture'] is not None]
        waters = [r['water_level'] for r in rows if r['water_level'] is not None]
        co2s = [r['co2'] for r in rows if r['co2'] is not None]
        
        stats = {
            'temperature': {
                'avg': round(sum(temps)/len(temps), 1) if temps else 0,
                'min': round(min(temps), 1) if temps else 0,
                'max': round(max(temps), 1) if temps else 0
            },
            'humidity': {
                'avg': round(sum(hums)/len(hums), 1) if hums else 0,
                'min': round(min(hums), 1) if hums else 0,
                'max': round(max(hums), 1) if hums else 0
            },
            'soil_moisture': {
                'avg': round(sum(soils)/len(soils), 1) if soils else 0,
                'min': round(min(soils), 1) if soils else 0,
                'max': round(max(soils), 1) if soils else 0
            },
            'water_level': {
                'avg': round(sum(waters)/len(waters), 1) if waters else 0,
                'min': round(min(waters), 1) if waters else 0,
                'max': round(max(waters), 1) if waters else 0
            },
            'co2': {
                'avg': round(sum(co2s)/len(co2s)) if co2s else 0,
                'min': min(co2s) if co2s else 0,
                'max': max(co2s) if co2s else 0
            }
        }
        
        # 按小时聚合（用于图表）
        hourly = {}
        for r in rows:
            ts = r['timestamp']
            if ts is None:
                continue
            hour_key = ts.strftime('%m-%d %H:00')
            if hour_key not in hourly:
                hourly[hour_key] = {'temps': [], 'hums': [], 'soils': [], 'waters': [], 'co2s': [], 'count': 0}
            if r['temperature'] is not None: hourly[hour_key]['temps'].append(r['temperature'])
            if r['humidity'] is not None: hourly[hour_key]['hums'].append(r['humidity'])
            if r['soil_moisture'] is not None: hourly[hour_key]['soils'].append(r['soil_moisture'])
            if r['water_level'] is not None: hourly[hour_key]['waters'].append(r['water_level'])
            if r['co2'] is not None: hourly[hour_key]['co2s'].append(r['co2'])
            hourly[hour_key]['count'] += 1
        
        chart_labels = []
        chart_temps = []
        chart_hums = []
        chart_soils = []
        chart_waters = []
        chart_co2s = []
        
        for k in sorted(hourly.keys()):
            d = hourly[k]
            chart_labels.append(k)
            chart_temps.append(round(sum(d['temps'])/len(d['temps']), 1) if d['temps'] else 0)
            chart_hums.append(round(sum(d['hums'])/len(d['hums']), 1) if d['hums'] else 0)
            chart_soils.append(round(sum(d['soils'])/len(d['soils']), 1) if d['soils'] else 0)
            chart_waters.append(round(sum(d['waters'])/len(d['waters']), 1) if d['waters'] else 0)
            chart_co2s.append(round(sum(d['co2s'])/len(d['co2s'])) if d['co2s'] else 0)
        
        return jsonify({
            'success': True,
            'range': range_type,
            'total_records': len(rows),
            'stats': stats,
            'chart': {
                'labels': chart_labels,
                'temperatures': chart_temps,
                'humidities': chart_hums,
                'soil_moistures': chart_soils,
                'water_levels': chart_waters,
                'co2_values': chart_co2s
            },
            'records': [{
                'ts': fmt_ts(r['timestamp']),
                'temperature': r['temperature'],
                'humidity': r['humidity'],
                'soil_moisture': r['soil_moisture'],
                'water_level': r['water_level'],
                'co2': r['co2'],
                'flame_detected': bool(r['flame_detected']),
                'pump_status': bool(r['pump_status']),
                'fan_status': bool(r['fan_status']),
                'motor_status': bool(r['motor_status']),
                'buzzer_status': bool(r['buzzer_status'])
            } for r in rows[-500:]]  # 最近500条
        })
        
    except mysql.connector.Error as err:
        cursor.close()
        conn.close()
        return jsonify({'success': False, 'error': str(err)})

def kill_port(port):
    """强制结束占用指定端口的进程 - 使用 netstat+taskkill，稳定快速"""
    for attempt in range(3):
        try:
            if os.name == 'nt':  # Windows
                # netstat 查找所有含该端口的连接（比 PowerShell 快，无启动开销）
                result = subprocess.run(
                    f'netstat -ano | findstr ":{port} "',
                    capture_output=True, text=True, shell=True, timeout=3
                )
                pids = set()
                for line in result.stdout.split('\n'):
                    line = line.strip()
                    if not line or ':' not in line:
                        continue
                    parts = [p for p in line.split() if p]
                    if len(parts) >= 5:
                        try:
                            pid = int(parts[-1])
                            if pid > 0:
                                pids.add(pid)
                        except ValueError:
                            pass
                if not pids:
                    if attempt < 2:
                        time.sleep(1)
                    continue
                for pid in pids:
                    subprocess.run(['taskkill', '/F', '/PID', str(pid)],
                                  capture_output=True, text=True, timeout=3)
                    print(f"🔌 已释放端口 {port} (PID: {pid})")
                time.sleep(0.5)
                return
            else:  # Linux/Mac
                result = subprocess.run(
                    f'lsof -ti:{port} | xargs kill -9',
                    capture_output=True, text=True, shell=True, timeout=3
                )
                if result.returncode == 0:
                    print(f"🔌 已释放端口 {port}")
                    return
                if attempt < 2:
                    time.sleep(1)
        except (subprocess.TimeoutExpired, KeyboardInterrupt):
            if attempt < 2:
                time.sleep(1)
        except Exception as e:
            if attempt < 2:
                time.sleep(1)

# ==================== 应用初始化标志 ====================
_app_initialized = False

def init_app():
    """初始化应用（启动所有后台线程、检查依赖），支持生产环境调用"""
    global _app_initialized, weather_agent, weather_agent_ready, server_started
    if _app_initialized:
        return
    _app_initialized = True
    
    print("⚡ 启动超快速响应温室监控Web应用...")
    
    # 1. 测试数据库连接
    test_conn = get_db_connection()
    if test_conn:
        print("✅ 数据库连接成功")
        # 兼容旧表：尝试添加可能缺失的列
        try:
            c = test_conn.cursor()
            for col in ['co2']:
                try:
                    c.execute(f"ALTER TABLE sensor_data ADD COLUMN {col} INT")
                    test_conn.commit()
                    print(f"✅ 已添加缺失的列: {col}")
                except Exception:
                    pass  # 列已存在，忽略
            c.close()
        except Exception:
            pass
        test_conn.close()
        # 从数据库加载阈值
        _load_thresholds_from_db()
    else:
        print("❌ 数据库连接失败")
        print("请确保 MySQL 服务已启动")
        # 生产环境不退出，让服务器继续运行但记录错误
    
    # 2. 测试AI服务连接
    if DASHSCOPE_API_KEY == "YOUR_DASHSCOPE_API_KEY":
        print("⚠️  AI助手未配置 - 请在环境变量中设置 DASHSCOPE_API_KEY")
        print("   获取 API Key: https://bailian.console.aliyun.com/")
    elif test_dashscope_connection():
        print(f"🤖 AI助手已就绪 (模型: {DASHSCOPE_MODEL})")
    else:
        print("⚠️  AI助手不可用 - 请检查阿里云百炼 API Key 和网络连接")
        print("   获取 API Key: https://bailian.console.aliyun.com/")
    
    # 3. 初始化天气智能体
    print("🌤️  初始化天气智能体...")
    
    def on_weather_ready():
        """天气首次就绪后立即推送到前端"""
        global weather_agent_ready
        weather_agent_ready = True
        try:
            if weather_agent:
                status = weather_agent.get_status()
                socketio.emit('weather_update', {
                    'forecast': status.get('forecast'),
                    'current_advice': status.get('current_advice'),
                    'recent_decisions': status.get('recent_decisions', []),
                    'forecast_time': status.get('forecast_time'),
                    'enabled': status.get('enabled', True)
                })
                print("🌤️  天气数据已就绪并推送到前端")
        except Exception as e:
            print(f"[天气推送] 首次推送失败: {e}")
    
    weather_agent = create_agent(
        get_sensor_callback=agent_sensor_callback,
        on_ready=on_weather_ready
    )
    weather_agent_ready = True
    print("🌤️  天气智能体已启动")
    
    # 4. 启动天气推送线程
    weather_push = threading.Thread(target=weather_push_thread, daemon=True, name="WeatherPush")
    weather_push.start()
    print("🌤️  天气预报推送线程已启动")
    
    # 5. 初始化缓存
    print("🔄 初始化数据缓存...")
    sensor_data = get_sensor_data_only()
    device_status, _ = get_device_status_only()
    if sensor_data:
        latest_cache['data'] = {**sensor_data, **device_status}
        print("✅ 缓存初始化完成")
    
    # 6. 启动多个监控线程（使用自动重启包装）
    print("⚡ 启动超快速设备状态监控线程 (0.5秒间隔)")
    run_with_restart(ultra_fast_device_monitor, "DeviceMonitor")
    
    print("🚀 启动快速传感器数据监控线程 (1秒间隔)")
    run_with_restart(fast_sensor_monitor, "SensorMonitor")
    
    print("📊 启动图表数据监控线程 (30秒间隔)")
    run_with_restart(chart_data_monitor, "ChartMonitor")
    
    print("🔄 启动兼容数据监控线程 (2秒间隔)")
    run_with_restart(combined_data_monitor, "CombinedMonitor")
    
    print("🌐 应用初始化完成，等待 HTTP 服务就绪...")
    print("⚡ 超快响应页面: /fast")
    print("🏠 完整温室界面: /greenhouse")
    print("🤖 AI助手: 已集成")
    server_started = True

# 在模块加载时自动初始化（支持 Gunicorn 生产部署）
try:
    init_app()
except Exception as e:
    print(f"❌ 应用初始化失败: {e}")
    print("💡 请检查：")
    print("   1. MySQL 服务是否已启动")
    print("   2. 端口 5000 是否被占用（会自动清理）")
    print("   3. 网络连接是否正常")
    print("⏳ 5 秒后重试...")
    time.sleep(5)
    try:
        init_app()
    except Exception as e2:
        print(f"❌ 重试仍失败: {e2}")
        print("请手动检查环境后重试")

if __name__ == '__main__':
    # 开发模式：使用 Flask 开发服务器
    try:
        print(f"🌐 Web服务器启动: http://localhost:{SERVER_PORT}")
        print("📊 设备状态更新: 0.5秒响应")
        print("📊 传感器数据: 1秒更新")
        socketio.run(app, debug=False, host='0.0.0.0', port=SERVER_PORT, load_dotenv=False)
    except OSError as e:
        if "address already in use" in str(e).lower() or "10048" in str(e):
            print(f"❌ 端口 {SERVER_PORT} 仍被占用，尝试强制清理...")
            kill_port(SERVER_PORT)
            time.sleep(2)
            print("🔄 重新启动...")
            socketio.run(app, debug=False, host='0.0.0.0', port=SERVER_PORT, load_dotenv=False)
        else:
            print(f"❌ 启动失败: {e}")
    except Exception as e:
        print(f"❌ 启动失败: {e}")
