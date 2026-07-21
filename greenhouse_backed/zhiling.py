"""
串口 AT 指令发送脚本 - ADP-L610 双向通信
1. POST 发送传感器数据到服务器
2. GET 读取服务器控制命令
3. 比对状态差异，自动发送控制指令
"""

import serial
import serial.tools.list_ports
import time
import json
import re

# ==================== 配置 ====================
# ADP-L610 4G 模块（HTTP 通信）
SERIAL_PORT_ADP = 'COM23'
BAUDRATE_ADP = 115200

# Arduino 控制板（设备控制）
SERIAL_PORT_CTRL = 'COM28'
BAUDRATE_CTRL = 9600

CMD_INTERVAL = 0.5      # 每条指令间隔（秒）
CYCLE_INTERVAL = 3       # 每轮执行间隔（秒）
LINE_ENDING = '\r\n'    # AT 指令换行符

# ==================== 传感器数据（POST） ====================
HTTP_POST_DATA = '{"temp":26.5,"hum":60.2,"soil":45.0,"co2":420,"flame":0,"pump":1}'
HTTP_DATA_LEN = len(HTTP_POST_DATA.encode('utf-8'))

# ==================== 本地设备状态追踪 ====================
# 记录当前已知的设备状态，与服务器比对后决定是否发送控制指令
CURRENT_DEVICE_STATE = {
    'pump': False,
    'fan': False,
    'motor': False,
    'buzzer': False,
    'flame': True,    # 默认自动
    'human': True,    # 默认自动
}

# 设备控制命令映射（与 Arduino 端格式一致）
DEVICE_CMD_MAP = {
    'pump':   {True: '1',        False: '0'},
    'fan':    {True: 'FAN_ON',   False: 'FAN_OFF'},
    'motor':  {True: 'MOTOR_ON', False: 'MOTOR_OFF'},
    'buzzer': {True: 'BUZZER_ON',False: 'BUZZER_OFF'},
    'flame':  {True: 'FLAME_AUTO',False: 'FLAME_OFF'},
    'human':  {True: 'HUMAN_AUTO',False: 'HUMAN_OFF'},
}


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
    # 查找 JSON 部分（从 { 到 }）
    json_match = re.search(r'\{.*\}', text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            return None
    return None


def send_control_command(ser_ctrl, device, turn_on):
    """向控制板串口发送设备控制指令"""
    cmd = DEVICE_CMD_MAP.get(device, {}).get(turn_on)
    if not cmd:
        print(f"[控制] ⚠️ 未知设备: {device}")
        return False

    ser_ctrl.write((cmd + '\n').encode('utf-8'))
    status = "开启" if turn_on else "关闭"
    print(f"[控制] 🔧 {device} → {status} (指令: {cmd}) → {SERIAL_PORT_CTRL}")
    time.sleep(0.3)
    # 更新本地状态
    CURRENT_DEVICE_STATE[device] = turn_on
    return True


def execute_post_sequence(ser):
    """执行 POST 数据发送序列"""
    print("  ── POST 发送传感器数据 ──")
    # 1. AT+MIPCALL=1
    send_at(ser, 'AT+MIPCALL=1', wait=CMD_INTERVAL)
    # 2. 设置 URL
    send_at(ser, 'AT+HTTPSET="URL","shijie-smartline.club:80/api/adp610/data"', wait=CMD_INTERVAL)
    # 3. 设置 User-Agent
    send_at(ser, 'AT+HTTPSET="UAGENT","fibocom"', wait=CMD_INTERVAL)
    # 4. 设置数据长度
    send_at(ser, f'AT+HTTPDATA={HTTP_DATA_LEN}', wait=CMD_INTERVAL)
    # 5. 发送 JSON 数据
    send_raw(ser, HTTP_POST_DATA, wait=CMD_INTERVAL)
    # 6. 执行 POST
    send_at(ser, 'AT+HTTPACT=1,30', wait=1.0)


def execute_get_sequence(ser):
    """执行 GET 命令读取序列，返回解析后的服务器指令"""
    print("  ── GET 读取服务器指令 ──")
    # 1. AT+MIPCALL=1
    send_at(ser, 'AT+MIPCALL=1', wait=CMD_INTERVAL)
    # 2. 设置 URL（同一地址，服务器根据 method 区分）
    send_at(ser, 'AT+HTTPSET="URL","shijie-smartline.club:80/api/adp610/data"', wait=CMD_INTERVAL)
    # 3. 设置 User-Agent
    send_at(ser, 'AT+HTTPSET="UAGENT","fibocom"', wait=CMD_INTERVAL)
    # 4. 执行 GET 请求
    send_at(ser, 'AT+HTTPACT=0,30', wait=2.0)
    # 5. 读取响应内容
    resp = send_at(ser, 'AT+HTTPREAD', wait=1.0)
    # 解析 JSON
    data = parse_httpread_response(resp)
    if data and data.get('success') and data.get('commands'):
        return data['commands']
    return None


def sync_device_state(ser_ctrl, server_commands):
    """比对服务器指令与本地状态，发送差异控制指令到控制板"""
    if not server_commands:
        return False

    device_cmds = server_commands.get('device', {})
    if not device_cmds:
        return False

    changed = False
    for device, target_state in device_cmds.items():
        if device not in CURRENT_DEVICE_STATE:
            continue
        current = CURRENT_DEVICE_STATE[device]
        if current != target_state:
            print(f"  ⚡ 状态变化: {device} ({current} → {target_state})")
            send_control_command(ser_ctrl, device, target_state)
            changed = True

    if not changed:
        print("  ✅ 所有设备状态一致，无需修改")
    return changed


def main():
    print(f"🚀 ADP-L610 双向通信工具")
    print(f"ADP-L610 (HTTP): {SERIAL_PORT_ADP} @ {BAUDRATE_ADP} baud")
    print(f"控制板 (指令):   {SERIAL_PORT_CTRL} @ {BAUDRATE_CTRL} baud")
    print(f"服务器: shijie-smartline.club:80/api/adp610/data")
    print(f"发送数据: {HTTP_POST_DATA}")
    print(f"指令间隔: {CMD_INTERVAL}s | 循环间隔: {CYCLE_INTERVAL}s\n")

    # 列出可用串口
    list_ports()
    print()

    # 连接 ADP-L610 串口（HTTP 通信，带重试）
    ser_adp = None
    while ser_adp is None:
        try:
            ser_adp = serial.Serial(
                port=SERIAL_PORT_ADP,
                baudrate=BAUDRATE_ADP,
                timeout=1,
                write_timeout=1
            )
            print(f"✅ ADP-L610 已连接: {SERIAL_PORT_ADP}\n")
        except serial.SerialException as e:
            print(f"❌ {SERIAL_PORT_ADP} 连接失败: {e}")
            print(f"⏳ 5 秒后重试...")
            time.sleep(5)

    # 连接控制板串口（设备控制，带重试）
    ser_ctrl = None
    while ser_ctrl is None:
        try:
            ser_ctrl = serial.Serial(
                port=SERIAL_PORT_CTRL,
                baudrate=BAUDRATE_CTRL,
                timeout=1,
                write_timeout=1
            )
            print(f"✅ 控制板已连接: {SERIAL_PORT_CTRL}\n")
        except serial.SerialException as e:
            print(f"❌ {SERIAL_PORT_CTRL} 连接失败: {e}")
            print(f"⏳ 5 秒后重试...")
            time.sleep(5)

    round_count = 0
    try:
        while True:
            round_count += 1
            print(f"\n{'='*50}")
            print(f"📡 第 {round_count} 轮")
            print(f"{'='*50}")

            # ===== 第一步：POST 发送传感器数据 =====
            execute_post_sequence(ser_adp)

            # ===== 第二步：GET 读取服务器指令 =====
            server_commands = execute_get_sequence(ser_adp)

            # ===== 第三步：比对状态并发送控制指令到控制板 =====
            if server_commands:
                print("  ── 比对设备状态 ──")
                print(f"  服务器指令: {json.dumps(server_commands, ensure_ascii=False)}")
                sync_device_state(ser_ctrl, server_commands)
            else:
                print("  ⚠️ 未能获取服务器指令，跳过状态比对")

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
            print("🔌 控制板串口已关闭")


if __name__ == '__main__':
    main()