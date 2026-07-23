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

# ==================== 配置 ====================
# ADP-L610 4G 模块（HTTP 通信）
SERIAL_PORT_ADP = 'COM23'
BAUDRATE_ADP = 115200

# Arduino 控制板（传感器 + 设备控制）
SERIAL_PORT_CTRL = 'COM28'
BAUDRATE_CTRL = 9600

CMD_INTERVAL = 0.2      # 每条指令间隔（秒）
CYCLE_INTERVAL = 1       # 每轮执行间隔（秒）
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
        c.close()
    except Exception as e:
        print(f"[数据库] 建表失败: {e}")


def insert_sensor_data(conn, temp, hum, soil, water, co2_val, flame, pump, fan, motor, buzzer):
    """插入一条传感器数据到数据库"""
    try:
        c = conn.cursor()
        c.execute("""
            INSERT INTO sensor_data 
            (timestamp, temperature, humidity, soil_moisture, water_level, co2,
             flame_detected, pump_status, fan_status, motor_status, buzzer_status) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (datetime.now(), temp, hum, soil, water, co2_val, flame, pump, fan, motor, buzzer))
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

            # 火焰：level==0 表示检测到火焰
            flame_detected = 1 if (flame_level == 0) else 0

            print(f"  [传感器] 温度={temperature:.1f}℃ 湿度={humidity:.1f}% "
                  f"土壤={soil_percent:.1f}% 水位={water_percent:.1f}% "
                  f"CO2={co2_raw} 火焰={flame_detected} 人体={human_level}")

            return {
                'temp': round(temperature, 1),
                'hum': round(humidity, 1),
                'soil': soil_percent,
                'co2': co2_raw,
                'flame': flame_detected,
                'human': human_level,
                'water': round(water_percent, 1),
                'distance': round(distance, 1),
            }
        else:
            # 非传感器行（如阈值汇总），打印出来便于调试
            print(f"  [Arduino输出] {line}")
    print("  ⚠️ 读取传感器超时，使用上次数据")
    return None


# 阈值汇总正则 - 解析 Arduino 实际设备状态
THRESHOLD_SUMMARY_PATTERN = re.compile(
    r'阈值汇总:.*?风扇=(\S+)\s+水泵=(\S+)\s+舵机=(\S+)'
)


def parse_arduino_status(line):
    """从 Arduino 阈值汇总行解析设备实际状态，更新 CURRENT_DEVICE_STATE"""
    m = THRESHOLD_SUMMARY_PATTERN.search(line)
    if not m:
        return False
    # 风扇=自动 → 'auto', 风扇=手动 → 保持原值不变
    fan_status = m.group(1)
    pump_status = m.group(2)
    motor_status = m.group(3)

    if fan_status == '自动':
        CURRENT_DEVICE_STATE['fan'] = 'auto'
    if pump_status == '自动':
        CURRENT_DEVICE_STATE['pump'] = 'auto'
    if motor_status == '自动':
        CURRENT_DEVICE_STATE['motor'] = 'auto'

    print(f"  [Arduino状态] 风扇={fan_status} 水泵={pump_status} 舵机={motor_status}")
    return True

def send_control_command(ser_ctrl, device, action):
    """向控制板串口发送设备控制指令（action: 'on'/'off'/'auto'）"""
    cmd = DEVICE_CMD_MAP.get(device, {}).get(action)
    if not cmd:
        print(f"[控制] ⚠️ 未知设备/动作: {device}={action}")
        return False

    ser_ctrl.write((cmd + '\n').encode('utf-8'))
    status_map = {'on': '开启', 'off': '关闭', 'auto': '自动'}
    print(f"[控制] 🔧 {device} → {status_map.get(action, action)} (指令: {cmd}) → {SERIAL_PORT_CTRL}")
    time.sleep(0.3)
    CURRENT_DEVICE_STATE[device] = action
    return True


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
        if cmd_data.get('pending') and cmd_data.get('cmd'):
            cmd = cmd_data['cmd'].strip()
            # 解析指令格式：HUMAN_OFF → device='human', action='off'
            parts = cmd.split('_', 1)
            if len(parts) == 2:
                dev_name = parts[0].lower()
                act_name = parts[1].lower()
                # 水泵特殊处理：1/0/auto
                if dev_name == '1':
                    dev_name, act_name = 'pump', 'on'
                elif dev_name == '0':
                    dev_name, act_name = 'pump', 'off'
                elif dev_name == 'auto':
                    dev_name, act_name = 'pump', 'auto'
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
                    send_control_command(ser_ctrl, dev_name, act_name)
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
        'pump': 1 if CURRENT_DEVICE_STATE.get('pump') else 0,
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
    """比对服务器指令与本地状态，发送差异控制指令（action: 'on'/'off'/'auto'）"""
    if not server_commands:
        return False

    device_cmds = server_commands.get('device', {})
    if not device_cmds:
        return False

    changed = False
    for device, target_action in device_cmds.items():
        if device not in CURRENT_DEVICE_STATE:
            continue
        current = CURRENT_DEVICE_STATE[device]
        if current != target_action:
            print(f"  ⚡ 状态变化: {device} ({current} → {target_action})")
            send_control_command(ser_ctrl, device, target_action)
            changed = True

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
                        1 if CURRENT_DEVICE_STATE.get('pump') else 0,
                        1 if CURRENT_DEVICE_STATE.get('fan') else 0,
                        1 if CURRENT_DEVICE_STATE.get('motor') else 0,
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
                                1 if CURRENT_DEVICE_STATE.get('pump') else 0,
                                1 if CURRENT_DEVICE_STATE.get('fan') else 0,
                                1 if CURRENT_DEVICE_STATE.get('motor') else 0,
                                0,
                            )

            # ===== 第二步：检查本地命令文件（来自 Web 前端控制） =====
            check_local_commands(ser_ctrl)

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