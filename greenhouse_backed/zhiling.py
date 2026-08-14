"""
串口 AT 指令发送脚本 - ADP-L610 双向通信
1. 从 COM28 (Arduino) 读取真实传感器数据
2. POST 发送传感器数据到服务器
3. GET 读取服务器控制命令
4. 比对状态差异，自动发送控制指令
5. 下发阈值设置到 Arduino
"""

import serial
import serial.tools.list_ports
import time
import json
import re
import mysql.connector
import math
from datetime import datetime
import os

# ==================== 本地命令文件（与 app_ultra_fast.py 共享） ====================
CMD_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'serial_cmd.json')

# 设备状态共享文件（zhiling.py 写入，app_ultra_fast.py 读取）
DEVICE_STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'device_state.json')

# ==================== 配置 ====================
# ADP-L610 4G 模块（HTTP 通信）
SERIAL_PORT_ADP = 'COM23'
BAUDRATE_ADP = 115200

# Arduino 控制板（传感器 + 设备控制）
SERIAL_PORT_CTRL = 'COM28'
BAUDRATE_CTRL = 9600

CMD_INTERVAL = 0.1      # 每条指令间隔（秒）
CYCLE_INTERVAL = 0.6       # 每轮执行间隔（秒）
LINE_ENDING = '\r\n'    # AT 指令换行符
SENSOR_READ_TIMEOUT = 4  # 读取传感器超时（秒）

# ==================== 串口数据正则 ====================
# Arduino 输出格式（带 [#] 前缀或不带均可）
SERIAL_PATTERN = re.compile(
    r'土壤=(\d+)%\s+CO2=(\d+)\s+人体=(\d)\s+火焰=(\d)\s+'
    r'水位=([\d.]+)%\s+距离=(-?[\d.]+)cm\s+'
    r'温度=([\d.]+)℃\s+湿度=([\d.]+)%'
)

# ==================== 本地设备状态追踪 ====================
CURRENT_DEVICE_STATE = {
    'pump': 'off',
    'fan': 'off',
    'motor': 'off',
    'flame': 'auto',
    'human': 'auto',
}

# 本地命令变更标记（避免服务器命令覆盖本地操作）
LOCAL_CHANGED = set()
# 本地锁定时间戳（超时后自动解除，默认5秒）
LOCAL_CHANGED_TIMES = {}
LOCAL_CHANGED_TIMEOUT = 5.0

# 本地阈值缓存（避免重复发送相同值）
CURRENT_THRESHOLDS = {
    'temp': None,
    'hum': None,
    'soil': None,
    'water': None,
    'co2': None,
}

# 设备控制命令映射（与 Arduino 端格式一致）
DEVICE_CMD_MAP = {
    'pump':   {'on': '1',           'off': '0',        'auto': 'auto'},
    'fan':    {'on': 'FAN_ON',      'off': 'FAN_OFF',   'auto': 'FAN_AUTO'},
    'motor':  {'on': 'SERVO_180',  'off': 'SERVO_0', 'auto': 'SERVO_AUTO'},
    'flame':  {'on': 'FLAME_ON',    'off': 'FLAME_OFF', 'auto': 'FLAME_AUTO'},
    'human':  {'on': 'HUMAN_ON',    'off': 'HUMAN_OFF', 'auto': 'HUMAN_AUTO'},
}

# 阈值指令映射
THRESHOLD_CMD_MAP = {
    'temp': 'SET_TEMP',
    'hum': 'SET_HUMI',
    'soil': 'SET_SOIL',
    'water': 'SET_WATER',
    'co2': 'SET_CO2',
}

# ==================== 数据库配置（与 serial_to_db_fixed.py 一致） ====================
DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': 'hyqiuyu45',
    'database': 'sensor_db',
    'auth_plugin': 'mysql_native_password',
    'use_pure': True,
    'connect_timeout': 5
}


def connect_db():
    """连接数据库"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        print(f"[数据库] 连接失败: {e}")
        return None


def ensure_table(conn):
    """确保数据表存在"""
    try:
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS sensor_data (
                id INT AUTO_INCREMENT PRIMARY KEY,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                temperature FLOAT,
                humidity FLOAT,
                soil_moisture FLOAT,
                water_level FLOAT,
                co2 INT,
                flame_detected BOOLEAN DEFAULT FALSE,
                pump_status BOOLEAN DEFAULT FALSE,
                fan_status BOOLEAN DEFAULT FALSE,
                motor_status BOOLEAN DEFAULT FALSE,
                buzzer_status BOOLEAN DEFAULT FALSE
            )
        """)
        conn.commit()
        # 兼容旧表：尝试添加可能缺失的列
        for col in ['co2', 'flame_status', 'human_status', 'human_detected']:
            try:
                col_type = 'INT' if col in ('co2',) else 'TINYINT(1) DEFAULT 0'
                c.execute(f"ALTER TABLE sensor_data ADD COLUMN {col} {col_type}")
                conn.commit()
                print(f"✅ 已添加缺失的列: {col}")
            except Exception:
                pass  # 列已存在，忽略
        c.close()
    except Exception as e:
        print(f"[数据库] 建表失败: {e}")


def insert_sensor_data(conn, temp, hum, soil, water, co2_val, flame, human_det, pump, fan, motor, buzzer,
                       flame_status=None, human_status=None):
    """插入一条传感器数据到数据库"""
    try:
        c = conn.cursor()
        c.execute("""
            INSERT INTO sensor_data 
            (timestamp, temperature, humidity, soil_moisture, water_level, co2,
             flame_detected, human_detected, pump_status, fan_status, motor_status, buzzer_status,
             flame_status, human_status) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (datetime.now(), temp, hum, soil, water, co2_val, flame, human_det, pump, fan, motor, buzzer,
              flame_status if flame_status is not None else (1 if CURRENT_DEVICE_STATE.get('flame') in ('on', 'auto') else 0),
              human_status if human_status is not None else (1 if CURRENT_DEVICE_STATE.get('human') in ('on', 'auto') else 0)))
        conn.commit()
        c.close()
        return True
    except mysql.connector.Error as e:
        print(f"[数据库] 写入失败: {e}")
        return False


def list_ports():
    """列出所有可用串口"""
    ports = list(serial.tools.list_ports.comports())
    print("可用串口:")
    for p in ports:
        print(f"  {p.device} - {p.description}")
    return ports


def send_at(ser, cmd, wait=0.5, echo=True):
    """发送一条 AT 指令并读取响应"""
    ser.write((cmd + LINE_ENDING).encode('utf-8'))
    if echo:
        print(f"[发送] {cmd}")
    time.sleep(wait)
    return _read_response(ser, timeout=2)


def send_raw(ser, data, wait=0.5, echo=True):
    """发送原始数据并读取响应"""
    ser.write(data.encode('utf-8'))
    if echo:
        preview = data[:60] + '...' if len(data) > 60 else data
        print(f"[发送] {preview} (共 {len(data)} 字节)")
    time.sleep(wait)
    return _read_response(ser, timeout=2)


def _read_response(ser, timeout=2):
    """读取串口响应"""
    response = b''
    deadline = time.time() + timeout
    while time.time() < deadline:
        if ser.in_waiting:
            response += ser.read(ser.in_waiting)
            time.sleep(0.1)
        else:
            break
    if response:
        text = response.decode('utf-8', errors='ignore').strip()
        for line in text.split('\n'):
            line = line.strip()
            if line:
                print(f"[接收] {line}")
    return response


def parse_httpread_response(response):
    """解析 AT+HTTPREAD 返回的 HTTP 响应，提取 JSON 数据"""
    if not response:
        return None
    text = response.decode('utf-8', errors='ignore')
    json_match = re.search(r'\{.*\}', text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            return None
    return None


# ==================== 读取 Arduino 传感器数据 ====================

def read_sensor_line(ser_ctrl):
    """从 Arduino 串口读取一行传感器数据，返回解析后的字典"""
    # 先清空旧缓冲，避免读到过期数据
    ser_ctrl.reset_input_buffer()
    deadline = time.time() + SENSOR_READ_TIMEOUT
    while time.time() < deadline:
        try:
            raw = ser_ctrl.readline()
        except serial.SerialException:
            break
        if not raw:
            continue
        line = raw.decode('utf-8', errors='ignore').strip()
        if not line:
            continue
        # 尝试匹配传感器数据
        m = SERIAL_PATTERN.search(line)
        if m:
            soil_raw = int(m.group(1))
            co2_raw = int(m.group(2))
            human_level = int(m.group(3))
            flame_level = int(m.group(4))
            water_percent = float(m.group(5))
            distance = float(m.group(6))
            temperature = float(m.group(7))
            humidity = float(m.group(8))

            # 土壤（Arduino 已映射为百分比，直接使用）
            soil_percent = max(0, min(100, soil_raw))

            # 火焰：level==0 表示检测到火焰（火焰传感器输出 LOW=0 表示有火）
            flame_detected = 1 if (flame_level == 0) else 0
            # 人体：level!=0 表示检测到人体（PIR 传感器输出 HIGH=1 表示有人）
            human_detected = 1 if (human_level != 0) else 0

            print(f"  [传感器] 温度={temperature:.1f}℃ 湿度={humidity:.1f}% "
                  f"土壤={soil_percent:.1f}% 水位={water_percent:.1f}% "
                  f"CO2={co2_raw} 火焰={flame_detected} 人体={human_detected}")

            return {
                'temp': round(temperature, 1),
                'hum': round(humidity, 1),
                'soil': soil_percent,
                'co2': co2_raw,
                'flame': flame_detected,
                'human': human_detected,
                'water': round(water_percent, 1),
                'distance': round(distance, 1),
            }
        else:
            # 非传感器行（如阈值汇总），解析实际设备状态
            if '阈值汇总:' in line:
                parse_arduino_status(line)
            else:
                print(f"  [Arduino输出] {line}")
    print("  ⚠️ 读取传感器超时，使用上次数据")
    return None


# 阈值汇总正则 - 解析 Arduino 实际设备状态（火焰/人体为可选，兼容旧版固件）
THRESHOLD_SUMMARY_PATTERN = re.compile(
    r'阈值汇总:.*?风扇=(\S+)\s+水泵=(\S+)\s+舵机=(\S+)(?:\s+火焰=(\S+))?(?:\s+人体=(\S+))?'
)

# 阈值数值正则
THRESHOLD_VALUES_PATTERN = re.compile(
    r'阈值汇总:.*?温度=([\d.]+)C\s+湿度=([\d.]+)%\s+土壤=(\d+)%\s+CO2=(\d+)\s+水位=(\d+)%'
)

# 阈值数值缓存
THRESHOLD_VALUES = {'temp': 30.0, 'hum': 80.0, 'soil': 60, 'co2': 700, 'water': 20}

# 上次传感器数据缓存（用于推断自动模式下设备状态）
LAST_SENSOR = {'soil': 50, 'temp': 25, 'co2': 400}


def parse_arduino_status(line):
    """从 Arduino 阈值汇总行解析设备实际状态，更新 CURRENT_DEVICE_STATE"""
    # 先解析阈值数值
    tv = THRESHOLD_VALUES_PATTERN.search(line)
    if tv:
        THRESHOLD_VALUES['temp'] = float(tv.group(1))
        THRESHOLD_VALUES['hum'] = float(tv.group(2))
        THRESHOLD_VALUES['soil'] = int(tv.group(3))
        THRESHOLD_VALUES['co2'] = int(tv.group(4))
        THRESHOLD_VALUES['water'] = int(tv.group(5))
    
    m = THRESHOLD_SUMMARY_PATTERN.search(line)
    if not m:
        return False
    # 风扇/水泵/舵机状态
    fan_status = m.group(1)
    pump_status = m.group(2)
    motor_status = m.group(3)
    # 火焰/人体蜂鸣模式（可选字段，旧版固件可能不输出）
    flame_status = m.group(4)
    human_status = m.group(5)

    # 火焰/人体使用标准映射
    mode_map = {'自动': 'auto', '开启': 'on', '关闭': 'off'}
    if flame_status and flame_status in mode_map:
        CURRENT_DEVICE_STATE['flame'] = mode_map[flame_status]
    if human_status and human_status in mode_map:
        CURRENT_DEVICE_STATE['human'] = mode_map[human_status]

    # 风扇/水泵/舵机：推断实际状态
    # 自动模式下根据传感器数据推断是否开启
    soil_m = LAST_SENSOR.get('soil', 50)
    temp_c = LAST_SENSOR.get('temp', 25)
    co2_v = LAST_SENSOR.get('co2', 400)
    
    if fan_status == '自动':
        CURRENT_DEVICE_STATE['fan'] = 'on' if temp_c > THRESHOLD_VALUES['temp'] else 'off'
    elif fan_status in mode_map:
        CURRENT_DEVICE_STATE['fan'] = mode_map[fan_status]
    
    if pump_status == '自动':
        CURRENT_DEVICE_STATE['pump'] = 'on' if soil_m < THRESHOLD_VALUES['soil'] else 'off'
    elif pump_status in mode_map:
        CURRENT_DEVICE_STATE['pump'] = mode_map[pump_status]
    
    if motor_status == '自动':
        CURRENT_DEVICE_STATE['motor'] = 'on' if co2_v > THRESHOLD_VALUES['co2'] else 'off'
    elif motor_status in mode_map:
        CURRENT_DEVICE_STATE['motor'] = mode_map[motor_status]

    print(f"  [Arduino状态] 风扇={fan_status}({CURRENT_DEVICE_STATE['fan']}) 水泵={pump_status}({CURRENT_DEVICE_STATE['pump']}) 舵机={motor_status}({CURRENT_DEVICE_STATE['motor']}) 火焰={flame_status or 'N/A'} 人体={human_status or 'N/A'}")
    print(f"  [阈值] 温度={THRESHOLD_VALUES['temp']}C 土壤={THRESHOLD_VALUES['soil']}% CO2={THRESHOLD_VALUES['co2']}")
    
    # 写入共享文件（供 app_ultra_fast.py 读取）
    _write_device_state_to_file()
    return True


def _write_device_state_to_file():
    """将当前设备状态写入共享JSON文件，供 app_ultra_fast.py 读取"""
    try:
        with open(DEVICE_STATE_FILE, 'w') as f:
            json.dump(CURRENT_DEVICE_STATE, f)
    except Exception as e:
        print(f"  ⚠️ 写入设备状态文件失败: {e}")

def send_control_command(ser_ctrl, device, action):
    """向控制板串口发送设备控制指令（action: 'on'/'off'/'auto'）"""
    cmd = DEVICE_CMD_MAP.get(device, {}).get(action)
    if not cmd:
        print(f"[控制] ⚠️ 未知设备/动作: {device}={action}")
        return False

    old_state = CURRENT_DEVICE_STATE.get(device, '未知')
    ser_ctrl.write((cmd + '\n').encode('utf-8'))
    ser_ctrl.flush()
    status_map = {'on': '开启', 'off': '关闭', 'auto': '自动'}
    print(f"[控制] 🔧 {device} → {status_map.get(action, action)} (指令: {cmd}) → {SERIAL_PORT_CTRL}")
    print(f"   → 状态变更: {old_state} → {action}")
    time.sleep(0.3)
    CURRENT_DEVICE_STATE[device] = action
    return True


def send_control_command_local(ser_ctrl, device, action):
    """通过本地命令文件发送指令，并标记为本地变更（避免服务器覆盖）"""
    ok = send_control_command(ser_ctrl, device, action)
    if ok:
        LOCAL_CHANGED.add(device)
        LOCAL_CHANGED_TIMES[device] = time.time()
        print(f"  🔒 标记 {device} 为本地变更，服务器同步将跳过（超时{int(LOCAL_CHANGED_TIMEOUT)}秒）")
    return ok


def check_local_commands(ser_ctrl):
    """检查本地命令文件（serial_cmd.json），处理待发送指令"""
    try:
        if not os.path.exists(CMD_FILE):
            return
        with open(CMD_FILE, 'r') as f:
            content = f.read().strip()
        if not content:
            return
        cmd_data = json.loads(content)
        if not cmd_data.get('pending') or not cmd_data.get('cmd'):
            return
        
        cmd = cmd_data['cmd'].strip()
        
        # 如果 serial_to_db_fixed.py 已处理（processed=true），只更新 CURRENT_DEVICE_STATE 并清空文件
        if cmd_data.get('processed'):
            print(f"  📋 检测到 serial_to_db_fixed.py 已处理指令: {cmd}")
            # 解析指令更新 CURRENT_DEVICE_STATE
            if cmd in ('1', '0', 'auto'):
                action_map = {'1': 'on', '0': 'off', 'auto': 'auto'}
                CURRENT_DEVICE_STATE['pump'] = action_map[cmd]
                print(f"  → CURRENT_DEVICE_STATE 更新: pump = {CURRENT_DEVICE_STATE['pump']}")
                LOCAL_CHANGED.add('pump')
                LOCAL_CHANGED_TIMES['pump'] = time.time()
            else:
                parts = cmd.split('_', 1)
                if len(parts) == 2:
                    dev_name = parts[0].lower()
                    act_name = parts[1].lower()
                    if dev_name in DEVICE_CMD_MAP:
                        CURRENT_DEVICE_STATE[dev_name] = act_name
                        print(f"  → CURRENT_DEVICE_STATE 更新: {dev_name} = {act_name}")
                        # 加入本地锁定，防止 sync_device_state 立即用服务器旧值覆盖
                        LOCAL_CHANGED.add(dev_name)
                        LOCAL_CHANGED_TIMES[dev_name] = time.time()
            # 清空文件
            with open(CMD_FILE, 'w') as f:
                json.dump({'cmd': '', 'pending': False}, f)
            return
        
        # 处理水泵特殊指令：1/0/auto（无下划线格式）
        if cmd in ('1', '0', 'auto'):
            action_map = {'1': 'on', '0': 'off', 'auto': 'auto'}
            send_control_command_local(ser_ctrl, 'pump', action_map[cmd])
        else:
            # 解析指令格式：HUMAN_OFF → device='human', action='off'
            parts = cmd.split('_', 1)
            if len(parts) == 2:
                dev_name = parts[0].lower()
                act_name = parts[1].lower()
                # 跳过 SET_xxx 指令（阈值指令由 sync_thresholds 处理）
                if dev_name.startswith('set'):
                    cmd_upper = cmd.upper()
                    for th_type, prefix in THRESHOLD_CMD_MAP.items():
                        if cmd_upper.startswith(prefix):
                            value_str = cmd_upper[len(prefix):].strip()
                            try:
                                value = float(value_str)
                                send_threshold_command(ser_ctrl, th_type, value)
                            except ValueError:
                                pass
                            break
                elif dev_name in DEVICE_CMD_MAP:
                    send_control_command_local(ser_ctrl, dev_name, act_name)
                # 舵机指令特殊处理：SERVO_180 → motor on
                elif dev_name == 'servo':
                    # 映射 servo → motor
                    action_map = {'180': 'on', '0': 'off', 'auto': 'auto'}
                    mapped_action = action_map.get(act_name)
                    if mapped_action:
                        send_control_command_local(ser_ctrl, 'motor', mapped_action)
                    else:
                        # 其他角度指令（如 SERVO_90），直接发送到串口
                        ser_ctrl.write((cmd + '\n').encode('utf-8'))
                        print(f"[控制] 🔧 舵机 → {act_name}° (指令: {cmd}) → {SERIAL_PORT_CTRL}")
                        time.sleep(0.3)
        # 清空命令文件
        with open(CMD_FILE, 'w') as f:
            json.dump({'cmd': '', 'pending': False}, f)
    except Exception as e:
        print(f"[本地命令] 处理失败: {e}")


def send_threshold_command(ser_ctrl, th_type, value):
    """向控制板发送阈值设置指令"""
    if value is None:
        return False
    cmd_prefix = THRESHOLD_CMD_MAP.get(th_type)
    if not cmd_prefix:
        return False
    # 跳过已发送过的相同值
    if CURRENT_THRESHOLDS.get(th_type) == value:
        return False

    cmd = f"{cmd_prefix} {value}"
    ser_ctrl.write((cmd + '\n').encode('utf-8'))
    print(f"[阈值] 📤 {th_type} → {value} (指令: {cmd}) → {SERIAL_PORT_CTRL}")
    time.sleep(0.3)
    CURRENT_THRESHOLDS[th_type] = value
    return True


# ==================== HTTP 通信序列 ====================


def get_device_inferred_state(device_name, sensor_data):
    """获取设备推断状态：auto模式下根据传感器数据推断实际开关状态
    
    Returns: 1 (开启) 或 0 (关闭)
    """
    state = CURRENT_DEVICE_STATE.get(device_name, 'off')
    if state == 'auto':
        if device_name == 'pump':
            soil_m = sensor_data.get('soil', 50) if sensor_data else LAST_SENSOR.get('soil', 50)
            return 1 if soil_m < THRESHOLD_VALUES.get('soil', 60) else 0
        elif device_name == 'fan':
            temp_c = sensor_data.get('temp', 25) if sensor_data else LAST_SENSOR.get('temp', 25)
            return 1 if temp_c > THRESHOLD_VALUES.get('temp', 30) else 0
        elif device_name == 'motor':
            co2_v = sensor_data.get('co2', 400) if sensor_data else LAST_SENSOR.get('co2', 400)
            return 1 if co2_v > THRESHOLD_VALUES.get('co2', 700) else 0
    return 1 if state == 'on' else 0

def execute_post_sequence(ser_adp, sensor_data):
    """执行 POST 数据发送序列，使用真实传感器数据"""
    if not sensor_data:
        print("  ⚠️ 无传感器数据，跳过 POST")
        return

    # 构建 JSON 载荷（使用服务器字段名）
    payload = {
        'temp': sensor_data.get('temp', 0),
        'hum': sensor_data.get('hum', 0),
        'soil': sensor_data.get('soil', 0),
        'water': sensor_data.get('water', 0),
        'co2': sensor_data.get('co2', 0),
        'flame': sensor_data.get('flame', 0),
        'human': sensor_data.get('human', 0),
        'pump': get_device_inferred_state('pump', sensor_data),
        'fan': get_device_inferred_state('fan', sensor_data),
        'motor': get_device_inferred_state('motor', sensor_data),
        # 添加警报模式状态（1=开启/自动, 0=关闭）
        'flame_status': 1 if CURRENT_DEVICE_STATE.get('flame') in ('on', 'auto') else 0,
        'human_status': 1 if CURRENT_DEVICE_STATE.get('human') in ('on', 'auto') else 0,
        # 发送实际模式字符串，让服务器更新 device_action_cache
        'human_mode': CURRENT_DEVICE_STATE.get('human', 'auto'),
        'flame_mode': CURRENT_DEVICE_STATE.get('flame', 'auto'),
    }
    json_str = json.dumps(payload, ensure_ascii=False)
    data_len = len(json_str.encode('utf-8'))

    print(f"  ── POST 发送传感器数据 ({data_len} 字节) ──")
    print(f"  JSON: {json_str}")

    send_at(ser_adp, 'AT+MIPCALL=1', wait=CMD_INTERVAL)
    send_at(ser_adp, 'AT+HTTPSET="URL","shijie-smartline.club:80/api/adp610/data"', wait=CMD_INTERVAL)
    send_at(ser_adp, 'AT+HTTPSET="UAGENT","fibocom"', wait=CMD_INTERVAL)
    send_at(ser_adp, f'AT+HTTPDATA={data_len}', wait=CMD_INTERVAL)
    send_raw(ser_adp, json_str, wait=CMD_INTERVAL)
    send_at(ser_adp, 'AT+HTTPACT=1,30', wait=1.0)


def execute_get_sequence(ser_adp):
    """执行 GET 命令读取序列，返回解析后的服务器指令"""
    print("  ── GET 读取服务器指令 ──")
    send_at(ser_adp, 'AT+MIPCALL=1', wait=CMD_INTERVAL)
    send_at(ser_adp, 'AT+HTTPSET="URL","shijie-smartline.club:80/api/adp610/data"', wait=CMD_INTERVAL)
    send_at(ser_adp, 'AT+HTTPSET="UAGENT","fibocom"', wait=CMD_INTERVAL)
    send_at(ser_adp, 'AT+HTTPACT=0,30', wait=2.0)
    resp = send_at(ser_adp, 'AT+HTTPREAD', wait=1.0)
    data = parse_httpread_response(resp)
    if data and data.get('success') and data.get('commands'):
        return data['commands']
    return None


# ==================== 状态同步 ====================

def sync_device_state(ser_ctrl, server_commands):
    """比对服务器指令与本地状态，发送差异控制指令（跳过近期本地变更的设备）"""
    if not server_commands:
        return False

    device_cmds = server_commands.get('device', {})
    if not device_cmds:
        # 服务器没有设备指令，解除所有本地锁定（服务器已同步）
        if LOCAL_CHANGED:
            print(f"  🔓 解除所有本地锁定: {LOCAL_CHANGED}")
            LOCAL_CHANGED.clear()
            LOCAL_CHANGED_TIMES.clear()
        return False

    # 检查超时的本地锁定（超过5秒自动解除）
    now = time.time()
    expired = [d for d in list(LOCAL_CHANGED) if d in LOCAL_CHANGED_TIMES and now - LOCAL_CHANGED_TIMES[d] > LOCAL_CHANGED_TIMEOUT]
    if expired:
        print(f"  🔓 本地锁定超时，自动解除: {expired}")
        for d in expired:
            LOCAL_CHANGED.discard(d)
            LOCAL_CHANGED_TIMES.pop(d, None)

    changed = False
    for device, target_action in device_cmds.items():
        if device not in CURRENT_DEVICE_STATE:
            continue
        # 跳过本地变更的设备（等待服务器同步更新）
        if device in LOCAL_CHANGED:
            remain = int(LOCAL_CHANGED_TIMEOUT - (now - LOCAL_CHANGED_TIMES.get(device, now)))
            print(f"  ⏭️ 跳过 {device}：本地已变更（剩余{max(0, remain)}秒解锁）")
            continue
        current = CURRENT_DEVICE_STATE[device]
        if current != target_action:
            print(f"  ⚡ 状态变化: {device} ({current} → {target_action})")
            send_control_command(ser_ctrl, device, target_action)
            changed = True

    # 解除已与服务器同步的本地锁定
    for device in list(LOCAL_CHANGED):
        if device in device_cmds and CURRENT_DEVICE_STATE.get(device) == device_cmds[device]:
            LOCAL_CHANGED.discard(device)
            LOCAL_CHANGED_TIMES.pop(device, None)
            print(f"  🔓 {device} 已与服务器同步，解除本地锁定")

    if not changed:
        print("  ✅ 所有设备状态一致，无需修改")
    return changed


def sync_thresholds(ser_ctrl, server_commands):
    """从服务器读取阈值并下发到 Arduino"""
    if not server_commands:
        return False

    th_cmds = server_commands.get('threshold', {})
    if not th_cmds:
        return False

    changed = False
    for th_type, value in th_cmds.items():
        if value is not None:
            if send_threshold_command(ser_ctrl, th_type, value):
                changed = True

    if not changed:
        print("  ✅ 阈值一致，无需修改")
    return changed


# ==================== 主循环 ====================

def main():
    print(f"🚀 ADP-L610 双向通信工具（真实传感器数据 + 数据库写入）")
    print(f"ADP-L610 (HTTP): {SERIAL_PORT_ADP} @ {BAUDRATE_ADP} baud")
    print(f"Arduino (传感器): {SERIAL_PORT_CTRL} @ {BAUDRATE_CTRL} baud")
    print(f"数据库: {DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}")
    print(f"服务器: shijie-smartline.club:80/api/adp610/data")
    print(f"指令间隔: {CMD_INTERVAL}s | 循环间隔: {CYCLE_INTERVAL}s\n")

    last_sensor_data = None

    list_ports()
    print()

    # ===== 连接数据库 =====
    db_conn = connect_db()
    if db_conn:
        ensure_table(db_conn)
        print("✅ 数据库连接成功\n")
    else:
        print("❌ 数据库连接失败，将跳过数据库写入\n")

    # ===== 连接 ADP-L610 =====
    ser_adp = None
    while ser_adp is None:
        try:
            ser_adp = serial.Serial(
                port=SERIAL_PORT_ADP, baudrate=BAUDRATE_ADP,
                timeout=1, write_timeout=1
            )
            print(f"✅ ADP-L610 已连接: {SERIAL_PORT_ADP}\n")
        except serial.SerialException as e:
            print(f"❌ {SERIAL_PORT_ADP} 连接失败: {e}")
            time.sleep(5)

    # ===== 连接 Arduino =====
    ser_ctrl = None
    while ser_ctrl is None:
        try:
            ser_ctrl = serial.Serial(
                port=SERIAL_PORT_CTRL, baudrate=BAUDRATE_CTRL,
                timeout=1, write_timeout=1
            )
            time.sleep(2)
            ser_ctrl.reset_input_buffer()
            print(f"✅ Arduino 已连接: {SERIAL_PORT_CTRL}\n")
        except serial.SerialException as e:
            print(f"❌ {SERIAL_PORT_CTRL} 连接失败: {e}")
            time.sleep(5)

    round_count = 0
    try:
        while True:
            round_count += 1
            print(f"\n{'='*50}")
            print(f"📡 第 {round_count} 轮")
            print(f"{'='*50}")

            # ===== 第一步：读取 Arduino 传感器数据 =====
            sensor_data = read_sensor_line(ser_ctrl)
            if sensor_data:
                last_sensor_data = sensor_data
            else:
                sensor_data = last_sensor_data

            # ===== 第二步：检查本地命令文件（独立于传感器数据，确保始终处理） =====
            check_local_commands(ser_ctrl)
            # 立即写文件，确保 device_state.json 与 CURRENT_DEVICE_STATE 同步
            _write_device_state_to_file()

            if sensor_data:
                
                # ===== 写入数据库 =====
                if db_conn:
                    ok = insert_sensor_data(
                        db_conn,
                        sensor_data.get('temp', 0),
                        sensor_data.get('hum', 0),
                        sensor_data.get('soil', 0),
                        sensor_data.get('water', 0),
                        sensor_data.get('co2', 0),
                        sensor_data.get('flame', 0),
                        sensor_data.get('human', 0),  # human_detected
                        get_device_inferred_state('pump', sensor_data),
                        get_device_inferred_state('fan', sensor_data),
                        get_device_inferred_state('motor', sensor_data),
                        0,  # buzzer 始终为 0
                    )
                    if not ok:
                        print("⚠️ 数据库写入失败，尝试重连...")
                        try:
                            db_conn.close()
                        except:
                            pass
                        time.sleep(1)
                        db_conn = connect_db()
                        if db_conn:
                            insert_sensor_data(
                                db_conn,
                                sensor_data.get('temp', 0),
                                sensor_data.get('hum', 0),
                                sensor_data.get('soil', 0),
                                sensor_data.get('water', 0),
                                sensor_data.get('co2', 0),
                                sensor_data.get('flame', 0),
                                sensor_data.get('human', 0),  # human_detected
                                get_device_inferred_state('pump', sensor_data),
                                get_device_inferred_state('fan', sensor_data),
                                get_device_inferred_state('motor', sensor_data),
                                0,
                            )

            # ===== 第三步：POST 发送传感器数据到服务器 =====
            execute_post_sequence(ser_adp, sensor_data)

            # ===== 第三步：GET 读取服务器指令 =====
            server_commands = execute_get_sequence(ser_adp)

            if server_commands:
                print(f"  服务器指令: {json.dumps(server_commands, ensure_ascii=False)}")

                # ===== 第四步：比对设备状态 =====
                print("  ── 比对设备状态 ──")
                sync_device_state(ser_ctrl, server_commands)

                # ===== 第五步：下发阈值 =====
                print("  ── 比对阈值 ──")
                sync_thresholds(ser_ctrl, server_commands)
                # 同步后写文件，确保文件反映最新状态
                _write_device_state_to_file()
            else:
                print("  ⚠️ 未能获取服务器指令")

            print(f"\n✅ 第 {round_count} 轮完成")
            print(f"--- 等待 {CYCLE_INTERVAL} 秒后开始下一轮 ---")
            time.sleep(CYCLE_INTERVAL)

    except KeyboardInterrupt:
        print("\n\n🛑 用户中断")
    except serial.SerialException as e:
        print(f"\n❌ 串口错误: {e}")
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if ser_adp and ser_adp.is_open:
            ser_adp.close()
            print("🔌 ADP-L610 串口已关闭")
        if ser_ctrl and ser_ctrl.is_open:
            ser_ctrl.close()
            print("🔌 Arduino 串口已关闭")
        if db_conn:
            try:
                db_conn.close()
                print("🔌 数据库连接已关闭")
            except:
                pass


if __name__ == '__main__':
    main()