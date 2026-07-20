"""
wsgi.py - Gunicorn 生产环境入口
用法: gunicorn -k eventlet -w 1 wsgi:app
"""
import os
import sys

# 将当前目录加入 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入 app 和 socketio（会触发 init_app() 自动初始化）
from app_ultra_fast import app, socketio

# Gunicorn 需要暴露的变量
application = app

if __name__ == '__main__':
    socketio.run(app, debug=False, host='0.0.0.0', port=int(os.getenv('SERVER_PORT', '5000')))