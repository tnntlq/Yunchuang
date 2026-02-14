
# main.py
import sys
import os
import logging

# 添加模块路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import AppConfig
from utils.screen_capture import ScreenCapture
from utils.window_manager import WindowManager
from servers.tcp_server import TCPServer
from servers.stream_server import DualprotocolStreamServer   #双协议流(传输)服务器
from gui.main_gui import ScreenShareGUI
import tkinter as tk

def check_dependencies():
    """检查必需的依赖项"""
    missing = []
    packages = {
        'cv2': 'opencv-python',
        'mss': 'mss',
        'flask': 'flask',
        'PIL': 'Pillow',
        'qrcode': 'qrcode[pil]',
        'pygetwindow': 'pygetwindow',
        'psutil': 'psutil'
    }
    
    for module, pkg in packages.items():
        try:
            __import__(module)
        except ImportError:
            missing.append(pkg)
    
    # 检查Windows API库
    try:
        import win32gui
        import win32ui
        import win32con
        logging.info("✅ 已检测到pywin32库，支持Windows API后台捕获")
    except ImportError:
        missing.append('pywin32')  # 添加到缺失列表以提示

    if missing:
        logging.error(f"❌ 缺失必需的包: {', '.join(missing)}")
        logging.info(f"请运行: pip install {' '.join(missing)}")
        return False
    
    logging.info("✅ 所有依赖项均已安装")
    return True

if __name__ == "__main__":
    if not check_dependencies():
        sys.exit(1)
    
    # 创建配置实例
    config = AppConfig()
    
    # 创建各个模块实例
    capture_instance = ScreenCapture(config)
    tcp_server = TCPServer(config, capture_instance)
    stream_server = DualprotocolStreamServer(config, capture_instance)
    
    # 启动GUI
    root = tk.Tk()
    # 设置DPI感知（Windows高DPI优化）
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except:
        pass

    app = ScreenShareGUI(root, config, capture_instance, tcp_server, stream_server)
    root.mainloop()