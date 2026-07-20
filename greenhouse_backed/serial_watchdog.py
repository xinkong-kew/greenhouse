"""
serial_watchdog.py — 串口数据采集进程看门狗
监视 serial_to_db_fixed.py 进程，崩溃后自动重启
"""
import subprocess
import time
import sys
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SERIAL_SCRIPT = os.path.join(SCRIPT_DIR, "serial_to_db_fixed.py")

def main():
    print("🔍 [看门狗] 启动串口数据采集进程监控...")
    
    restart_count = 0
    while True:
        try:
            print(f"🚀 [看门狗] 启动 serial_to_db_fixed.py (第 {restart_count + 1} 次启动)")
            proc = subprocess.Popen(
                [sys.executable, SERIAL_SCRIPT],
                cwd=SCRIPT_DIR,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            
            # 实时输出日志
            for line in iter(proc.stdout.readline, ''):
                if line:
                    print(line.rstrip())
            
            # 进程结束
            return_code = proc.wait()
            restart_count += 1
            print(f"⚠️ [看门狗] 进程已退出 (返回码: {return_code})，5秒后重启...")
            time.sleep(5)
            
        except KeyboardInterrupt:
            print("\n🛑 [看门狗] 收到终止信号，退出")
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except:
                proc.kill()
            break
        except Exception as e:
            print(f"❌ [看门狗] 错误: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()