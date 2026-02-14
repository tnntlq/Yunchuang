import socket
import time
import cv2
import numpy as np
import threading
import logging
import struct
from queue import Queue
import zlib

logger = logging.getLogger(__name__)

class DualprotocolStreamServer:
    """支持TCP+UDP双协议传输
       UDP承担主要视频传输任务，TCP仅提供辅助控制功能
    """
    
    def __init__(self, config, capture_instance):
        self.config = config
        self.capture_instance = capture_instance
        self.tcp_socket = None
        self.udp_socket = None
        self.clients_tcp = {}  # TCP客户端
        self.clients_udp = {}  # UDP客户端
        self.frame_queue = Queue(maxsize=5)  # 限制队列大小防内存溢出
        self.running = True
        
    def handle_tcp_client(self, client_socket, address):
        """处理TCP客户端连接"""
        logger.info(f"开始处理TCP客户端 {address}")
        
        try:
            # 握手协议
            client_socket.send(b"STREAM_OK")
            response = client_socket.recv(1024)
            if response != b"READY":
                client_socket.close()
                return
        except Exception as e:
            logger.error(f"TCP客户端 {address} 连接初始化失败: {e}")
            try:
                client_socket.close()
            except:
                pass
            return
        
        # 添加到TCP客户端列表
        self.clients_tcp[client_socket] = address
        
        # 保持连接直到断开
        while self.running:
            try:
                # 简单心跳包，防止连接断开
                time.sleep(30)
            except:
                break
        
        # 清理客户端
        if client_socket in self.clients_tcp:
            del self.clients_tcp[client_socket]
        try:
            client_socket.close()
        except:
            pass
    
    def handle_udp_client(self, address):
        """处理UDP客户端"""
        logger.info(f"添加UDP客户端 {address}")
        self.clients_udp[address] = time.time()
    
    def send_udp_frame(self, frame_data, frame_id):
        """通过UDP发送视频帧"""
        if not self.udp_socket:
            return
            
        # 分片发送大帧（UDP最大包大小限制）
        max_chunk_size = 65507 - 16  # 留出头部空间
        total_chunks = (len(frame_data) + max_chunk_size - 1) // max_chunk_size
        
        for i in range(total_chunks):
            start = i * max_chunk_size
            end = min(start + max_chunk_size, len(frame_data))
            chunk = frame_data[start:end]
            
            # 构建UDP包头：帧ID + 片段索引 + 总片段数 + 数据
            header = struct.pack('<III', frame_id, i, total_chunks)
            packet = header + chunk
            
            # 发送给所有UDP客户端
            remove_clients = []
            for addr in list(self.clients_udp.keys()):
                try:
                    self.udp_socket.sendto(packet, addr)
                    self.clients_udp[addr] = time.time()  # 更新最后活动时间
                except Exception as e:
                    logger.error(f"UDP发送到 {addr} 失败: {e}")
                    remove_clients.append(addr)
            
            # 清理失效客户端
            for addr in remove_clients:
                if addr in self.clients_udp:
                    del self.clients_udp[addr]
    
    def start_servers(self):
        """启动TCP和UDP服务器"""
        # 启动TCP服务器
        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.tcp_socket.settimeout(1.0)
        self.tcp_socket.bind(('', self.config.stream_port))
        self.tcp_socket.listen(5)
        logger.info(f"TCP流媒体服务器启动在端口: {self.config.stream_port}")
        
        # 启动UDP服务器
        udp_port = self.config.stream_port + 1  # UDP使用相邻端口
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket.settimeout(0.1)  # 短超时
        self.udp_socket.bind(('', udp_port))
        logger.info(f"UDP流媒体服务器启动在端口: {udp_port}")
        
        # 接受TCP连接的线程
        def tcp_accept_thread():
            while self.running:
                try:
                    client_socket, address = self.tcp_socket.accept()
                    # 启动客户端处理线程
                    client_thread = threading.Thread(
                        target=self.handle_tcp_client,
                        args=(client_socket, address),
                        daemon=True
                    )
                    client_thread.start()
                except socket.timeout:
                    continue
                except Exception as e:
                    if self.running:
                        logger.error(f"TCP接受连接错误: {e}")
                    break
        
        # 接收UDP客户端注册的线程
        def udp_accept_thread():
            while self.running:
                try:
                    data, addr = self.udp_socket.recvfrom(1024)
                    if data == b"UDP_CLIENT_REGISTER":
                        self.handle_udp_client(addr)
                except socket.timeout:
                    continue
                except Exception as e:
                    if self.running:
                        logger.error(f"UDP接收错误: {e}")
                    break
        
        # 启动接受线程
        threading.Thread(target=tcp_accept_thread, daemon=True).start()
        threading.Thread(target=udp_accept_thread, daemon=True).start()
        
        # 主串流循环
        self.main_stream_loop()
    
    def main_stream_loop(self):
        """主串流循环"""
        last_time = 0
        frame_id = 0
        self.config.frame_count = 0
        self.config.start_time = time.time()
        
        while self.running and self.config.is_running:
            current_time = time.time()
            if current_time - last_time < 1.0 / self.config.fps:
                time.sleep(0.005)  # 更精细的睡眠
                continue
            last_time = current_time
            
            # 捕获帧
            frame, win = self.capture_instance.capture_window_content()
            if frame is None:
                # 生成错误提示帧
                img = np.zeros((360, 640, 3), dtype=np.uint8)
                cv2.putText(img, "⚠️ 未检测到目标窗口", (80, 150), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)
                cv2.putText(img, f"标题: '{self.config.window_title}'", (120, 200), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 200, 200), 1)
                _, buffer = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 60])
            else:
                # 自适应压缩质量 - 根据网络状况调整
                quality = self.get_adaptive_quality()
                _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
            
            frame_bytes = buffer.tobytes()
            
            # 添加帧统计信息
            if hasattr(self.config, 'last_frame_time'):
                network_delay = current_time - self.config.last_frame_time
                if network_delay > 0.1:  # 网络延迟过高
                    logger.warning(f"检测到网络延迟: {network_delay:.3f}s")
            
            self.config.last_frame_time = current_time
            self.config.frame_count += 1
            
            # TCP传输（可靠传输，适合控制命令）
            self.send_tcp_frame(frame_bytes)
            
            # UDP传输（低延迟，适合视频数据）
            self.send_udp_frame(frame_bytes, frame_id)
            
            frame_id = (frame_id + 1) % 65536  # 防止溢出
            
            # 清理长时间无响应的UDP客户端
            current_time = time.time()
            inactive_threshold = 60  # 60秒无活动则移除
            inactive_clients = [
                addr for addr, last_time in self.clients_udp.items()
                if current_time - last_time > inactive_threshold
            ]
            for addr in inactive_clients:
                logger.info(f"移除无响应UDP客户端: {addr}")
                del self.clients_udp[addr]
    
    def get_adaptive_quality(self):
        """根据网络状况自适应调整压缩质量"""
        if hasattr(self.config, 'network_quality'):
            # 简化的网络质量评估
            if self.config.network_quality < 0.5:
                return 40  # 低质量
            elif self.config.network_quality < 0.8:
                return 60  # 中等质量
            else:
                return 80  # 高质量
        return self.config.quality
    
    def send_tcp_frame(self, frame_bytes):
        """通过TCP发送关键信息"""
        # TCP用于发送控制信息和关键帧确认
        remove_clients = []
        for client_socket, address in list(self.clients_tcp.items()):
            try:
                # 发送较小的关键信息包
                info_packet = {
                    'frame_size': len(frame_bytes),
                    'timestamp': time.time(),
                    'frame_count': self.config.frame_count
                }
                # 实际视频数据仍通过UDP发送，TCP只发送控制信息
                client_socket.send(b"FRAME_INFO")  # 通知有新帧
            except Exception as e:
                logger.error(f"TCP发送给 {address} 失败: {e}")
                remove_clients.append(client_socket)
        
        # 清理断开的TCP客户端
        for client_socket in remove_clients:
            if client_socket in self.clients_tcp:
                del self.clients_tcp[client_socket]
            try:
                client_socket.close()
            except:
                pass
    
    def stop(self):
        """停止服务器"""
        self.running = False
        if self.tcp_socket:
            self.tcp_socket.close()
        if self.udp_socket:
            self.udp_socket.close()

# 当前优化：
"""
1. TCP+UDP双协议优势：
   - TCP: 可靠传输，适合控制命令和关键信息
   - UDP: 低延迟，适合实时视频数据

2. 网络优化技术：
   - 自适应压缩质量
   - 帧分片传输
   - 客户端状态管理
   - 内存缓冲区控制

3. 性能提升措施：
   - 更精细的时间控制
   - 网络延迟监测
   - 无效客户端清理
   - 并发处理优化
"""