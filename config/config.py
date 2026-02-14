# config.py
import socket
import time
import threading
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('screen_share.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AppConfig:
    """应用程序配置类"""
    def __init__(self):
        self.window_title = ""
        self.tcp_port = 5001
        self.stream_port = 5002  # 流端口
        self.quality = 65
        self.fps = 12
        self.show_debug = True
        self.is_running = False
        self.last_frame = None
        self.frame_count = 0
        self.start_time = time.time()
        self.connected_clients = 0
        self.local_ip = self.get_local_ip()
        
        # 流相关配置
        self.stream_socket = None
        self.stream_clients = {}  # 存储客户端连接 {socket: address}
        self.stream_server_running = False
        
        # 屏幕适配选项
        self.mobile_adapt_mode = "fit"  # fit=适应屏幕, stretch=拉伸填充, aspect=保持宽高比
        self.use_win_api = True  # 是否使用Windows API模式
        
        # 线程控制
        self.tcp_server_thread = None
        self.stream_server_thread = None
        
        # 资源清理锁
        self.cleanup_lock = threading.Lock()
        
    def get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('8.8.8.8', 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"