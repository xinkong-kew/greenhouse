import serial
import serial.tools.list_ports
import mysql.connector
import time
from datetime import datetime
import re
import math
import traceback
import json
import os

# ==================== 配置 ====================
# 串口命令队列文件（由 app_ultra_fast.py 写入）
CMD_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'serial_cmd.json')

# 设备状态内存缓存（由 send_cmd 解析指令更新）
DEVICE_STATES = {
    'pump': False,
    'fan': False,
    'motor': False,
    'buzzer': False,
    'flame': False,   # False=关闭, True=自动
    'human': False    # False=关闭, True=自动
}

# 设备名到数据库字段名的映射
DEVICE_DB_FIELDS = {
    'pump': 'pump_status',
    'fan': 'fan_status',
    'motor': 'motor_status',
    'buzzer': 'buzzer_status'
}

# ==================== 数据库配置（支持环境变量覆盖） ====================
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', '3306')),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', 'hyqiuyu45'),
    'database': os.getenv('DB_NAME', 'sensor_db'),
    'auth_plugin': 'mysql_native_password',
    'use_pure': True,
    'connect_timeout': 5
}

# 串口配置（Linux 下自动检测，也可通过环境变量 SERIAL_PORT 指定）
SERIAL_PORT_OVERRIDE = os.getenv('SERIAL_PORT', None)  # 例如: /dev/ttyUSB0 或 COM3

# 串口数据正则
SERIAL_PATTERN = re.compile(
    r'土壤=(\d+)\s+CO2=(\d+)\s+人体=(\d)\s+火焰=(\d)\s+'
    r'距离=(-?[\d.]+)cm\s+温度=([\d.]+)℃\s+湿度=([\d.]+)%'
)


def find_arduino_port():
    """查找 Arduino 串口（支持环境变量 SERIAL_PORT 覆盖）"""
    # 如果环境变量指定了串口，直接使用
    if SERIAL_PORT_OVERRIDE:
        print(f"🔌 使用环境变量指定的串口: {SERIAL_PORT_OVERRIDE}")
        return SERIAL_PORT_OVERRIDE
    
    # 自动检测
    ports = list(serial.tools.list_ports.comports())
    keywords = ['CH340', 'Arduino', 'USB-SERIAL', 'CP210']
    for port in ports:
        for kw in keywords:
            if kw.upper() in port.description.upper():
                try:
                    s = serial.Serial(port.device, 9600, timeout=1)
                    s.close()
                    return port.device
                except:
                    continue
    for port in ports:
        try:
            s = serial.Serial(port.device, 9600, timeout=1)
            s.close()
            return port.device
        except:
            continue
    return None


def wait_for_arduino():
    """等待 Arduino 连接"""
    while True:
        port = find_arduino_port()
        if port:
            return port
        print("⏳ 等待 Arduino 连接...")
        time.sleep(3)


def connect_db():
    """连接数据库"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        print(f"数据库连接失败: {e}")
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
        for col in ['co2']:
            try:
                c.execute(f"ALTER TABLE sensor_data ADD COLUMN {col} INT")
                conn.commit()
                print(f"✅ 已添加缺失的列: {col}")
            except Exception:
                pass  # 列已存在，忽略
        c.close()
    except Exception as e:
        print(f"建表失败: {e}")


def insert_sensor_data(conn, temp, hum, soil, water, co2_val, flame, pump, fan, motor, buzzer):
    """插入一条传感器数据"""
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
        print(f"写入失败: {e}")
        return False


def send_cmd(ser):
    """检查命令队列文件，发送指令到串口，并更新内存设备状态"""
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
            ser.write((cmd + '\n').encode('utf-8'))
            print(f"📤 发送指令: {cmd}")
            
            # 解析指令，更新内存设备状态
            # 格式: fan_on → fan=True, fan_off → fan=False
            # 报警指令: FLAME_AUTO → flame=True, FLAME_OFF → flame=False
            parts = cmd.split()
            cmd_name = parts[0]  # 例如: fan_on, SET_temp, FLAME_AUTO
            if '_' in cmd_name and not cmd_name.startswith('SET'):
                dev_name, dev_action = cmd_name.split('_', 1)
                dev_name_lower = dev_name.lower()
                if dev_name_lower in DEVICE_STATES:
                    if dev_action.lower() == 'off':
                        DEVICE_STATES[dev_name_lower] = False
                    elif dev_action.lower() in ('on', 'auto'):
                        DEVICE_STATES[dev_name_lower] = True
                    print(f"   → 设备状态更新: {dev_name_lower} = {DEVICE_STATES[dev_name_lower]}")
            
            # 清空命令
            with open(CMD_FILE, 'w') as f:
                json.dump({'cmd': '', 'pending': False}, f)
            time.sleep(0.2)
    except Exception:
        pass


def main():
    print("🚀 串口数据采集启动")
    
    # 连接数据库
    conn = connect_db()
    if not conn:
        print("❌ 无法连接数据库，退出")
        return
    ensure_table(conn)
    print("✅ 数据库连接成功")
    
    # 连接串口
    port = wait_for_arduino()
    ser = serial.Serial(port, 9600, timeout=2)
    print(f"✅ 串口已连接: {port}")
    
    print("📡 开始采集数据...")
    error_count = 0
    
    while True:
        try:
            # 发送待处理命令
            send_cmd(ser)
            
            # 读取一行串口数据
            raw = ser.readline()
            if not raw:
                error_count += 1
                if error_count > 10:
                    raise Exception("串口连续无数据")
                time.sleep(0.5)
                continue
            
            line = raw.decode('utf-8', errors='ignore').strip()
            if not line:
                continue
            
            # 跳过非传感器行
            if not line.startswith('土壤='):
                continue
            
            # 正则解析
            m = SERIAL_PATTERN.match(line)
            if not m:
                continue
            
            # 提取数据
            soil_raw = int(m.group(1))
            co2_raw = int(m.group(2))
            human_level = int(m.group(3))
            flame_level = int(m.group(4))
            distance = float(m.group(5))
            temperature = float(m.group(6))
            humidity = float(m.group(7))
            
            # 数据转换
            soil_moisture = round(soil_raw / 1023.0 * 100, 1)
            soil_moisture = max(0, min(100, soil_moisture))
            
            if distance < 0:
                water_level = 0.0
            else:
                water_level = max(0, min(100, round((1 - distance / 50.0) * 100, 1)))
            
            flame_detected = (flame_level == 0)
            
            # 从内存缓存读取设备状态（由 send_cmd 根据指令更新）
            pump_status = DEVICE_STATES.get('pump', False)
            fan_status = DEVICE_STATES.get('fan', False)
            motor_status = DEVICE_STATES.get('motor', False)
            buzzer_status = DEVICE_STATES.get('buzzer', False)
            
            # 跳过无效传感器数据
            if math.isnan(temperature) or math.isnan(humidity):
                time.sleep(0.5)
                continue
            if not (-20 <= temperature <= 60 and 0 <= humidity <= 100):
                time.sleep(0.5)
                continue
            
            # 写入数据库（失败时重连一次）
            ok = insert_sensor_data(conn, temperature, humidity, soil_moisture,
                                    water_level, co2_raw,
                                    flame_detected,
                                    pump_status, fan_status, motor_status, buzzer_status)
            if not ok:
                print("⚠️ 数据库写入失败，尝试重连...")
                try:
                    conn.close()
                except:
                    pass
                time.sleep(1)
                conn = connect_db()
                if conn:
                    ok = insert_sensor_data(conn, temperature, humidity, soil_moisture,
                                           water_level, co2_raw,
                                           flame_detected,
                                           pump_status, fan_status, motor_status, buzzer_status)
            
            if ok:
                error_count = 0
                print(f"[{datetime.now().strftime('%H:%M:%S')}] "
                      f"温度={temperature:.1f}℃ 湿度={humidity:.1f}% "
                      f"土壤={soil_moisture:.1f}% 水位={water_level:.1f}%")
            
            time.sleep(0.5)
            
        except serial.SerialException as e:
            print(f"⚠️ 串口断开: {e}")
            traceback.print_exc()
            # 等待并重连串口
            try:
                ser.close()
            except:
                pass
            time.sleep(3)
            port = wait_for_arduino()
            ser = serial.Serial(port, 9600, timeout=2)
            print(f"✅ 串口已重连: {port}")
            
        except Exception as e:
            error_count += 1
            print(f"⚠️ 错误 ({error_count}): {e}")
            traceback.print_exc()
            
            if error_count >= 5:
                print("💥 连续错误过多，重置连接...")
                error_count = 0
                try:
                    ser.close()
                except:
                    pass
                try:
                    conn.close()
                except:
                    pass
                time.sleep(3)
                conn = connect_db()
                if conn:
                    ensure_table(conn)
                port = wait_for_arduino()
                ser = serial.Serial(port, 9600, timeout=2)
                print("✅ 已重置连接")
            
            time.sleep(2)


if __name__ == '__main__':
    restart_count = 0
    while True:
        try:
            main()
        except KeyboardInterrupt:
            print("\n🛑 程序退出")
            break
        except Exception as e:
            restart_count += 1
            print(f"💥 严重崩溃 ({restart_count}): {e}")
            traceback.print_exc()
            print(f"🔁 10秒后重启...")
            time.sleep(10)