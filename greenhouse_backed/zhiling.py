"""
串口 AT 指令发送脚本
向 COM23 端口循环发送 ADP-L610 的 HTTP AT 指令序列
"""

import serial
import serial.tools.list_ports
import time

# ==================== 配置 ====================
SERIAL_PORT = 'COM23'
BAUDRATE = 115200
CMD_INTERVAL = 0.5      # 每条指令间隔（秒）
CYCLE_INTERVAL = 1       # 每轮执行间隔（秒）
LINE_ENDING = '\r\n'    # AT 指令换行符

# ==================== 配置 ====================
# HTTP POST 数据
HTTP_POST_DATA = '{"temp":26.5,"hum":60.2,"soil":45.0,"co2":420,"flame":0,"pump":1}'
HTTP_DATA_LEN = len(HTTP_POST_DATA.encode('utf-8'))  # 自动计算字节长度


def list_ports():
    """列出所有可用串口"""
    ports = list(serial.tools.list_ports.comports())
    print("可用串口:")
    for p in ports:
        print(f"  {p.device} - {p.description}")
    return ports


def send_at_command(ser, cmd, wait=0.5, echo=True):
    """发送一条 AT 指令并读取响应"""
    full_cmd = cmd + LINE_ENDING
    ser.write(full_cmd.encode('utf-8'))
    if echo:
        print(f"[发送] {cmd}")
    time.sleep(wait)
    response = b''
    timeout = time.time() + 2
    while time.time() < timeout:
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


def send_raw(ser, data, wait=0.5, echo=True):
    """发送原始数据并读取响应"""
    ser.write(data.encode('utf-8'))
    if echo:
        if len(data) > 60:
            print(f"[发送] {data[:60]}... (共 {len(data)} 字节)")
        else:
            print(f"[发送] {data}")
    time.sleep(wait)
    response = b''
    timeout = time.time() + 2
    while time.time() < timeout:
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


def main():
    print(f"🚀 ADP-L610 HTTP AT 指令循环发送工具")
    print(f"目标端口: {SERIAL_PORT} @ {BAUDRATE} baud")
    print(f"API: shijie-smartline.club:80/api/adp610/data")
    print(f"HTTP 数据: {HTTP_POST_DATA}")
    print(f"数据长度: {HTTP_DATA_LEN} 字节")
    print(f"指令间隔: {CMD_INTERVAL}s | 循环间隔: {CYCLE_INTERVAL}s\n")

    # 列出可用串口
    list_ports()
    print()

    # 连接串口（带重试）
    ser = None
    while ser is None:
        try:
            ser = serial.Serial(
                port=SERIAL_PORT,
                baudrate=BAUDRATE,
                timeout=1,
                write_timeout=1
            )
            print(f"✅ 串口已连接: {SERIAL_PORT}\n")
        except serial.SerialException as e:
            print(f"❌ 连接失败: {e}")
            print(f"⏳ 5 秒后重试...")
            time.sleep(5)

    round_count = 0
    try:
        while True:
            round_count += 1
            print(f"\n{'='*50}")
            print(f"📡 第 {round_count} 轮发送开始")
            print(f"{'='*50}")

            # 1. AT+MIPCALL=1
            send_at_command(ser, 'AT+MIPCALL=1', wait=CMD_INTERVAL)

            # 2. AT+HTTPSET="URL","shijie-smartline.club:80/api/adp610/data"
            send_at_command(ser,
                'AT+HTTPSET="URL","shijie-smartline.club:80/api/adp610/data"',
                wait=CMD_INTERVAL)

            # 3. AT+HTTPSET="UAGENT","fibocom"
            send_at_command(ser,
                'AT+HTTPSET="UAGENT","fibocom"',
                wait=CMD_INTERVAL)

            # 4. AT+HTTPDATA=<字符长度>
            send_at_command(ser,
                f'AT+HTTPDATA={HTTP_DATA_LEN}',
                wait=CMD_INTERVAL)

            # 5. 发送 JSON 数据
            send_raw(ser, HTTP_POST_DATA, wait=CMD_INTERVAL)

            # 6. AT+HTTPACT=1,30
            send_at_command(ser,
                'AT+HTTPACT=1,30',
                wait=CMD_INTERVAL)

            print(f"\n✅ 第 {round_count} 轮发送完成")
            print(f"--- 等待 {CYCLE_INTERVAL} 秒后开始下一轮 ---")
            time.sleep(CYCLE_INTERVAL)

    except KeyboardInterrupt:
        print("\n\n🛑 用户中断")
    except serial.SerialException as e:
        print(f"\n❌ 串口错误: {e}")
    except Exception as e:
        print(f"\n❌ 错误: {e}")
    finally:
        if ser and ser.is_open:
            ser.close()
            print("🔌 串口已关闭")


if __name__ == '__main__':
    main()