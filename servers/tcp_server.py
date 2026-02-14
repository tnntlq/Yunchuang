# servers/tcp_server.py
import time
import cv2
import numpy as np
from flask import Flask, Response, render_template_string
import logging

logger = logging.getLogger(__name__)

class TCPServer:
    """TCP服务器类"""
    
    def __init__(self, config, capture_instance):
        self.config = config
        self.capture_instance = capture_instance
        self.app = self._create_flask_app()
    
    def _generate_frames(self):
        """生成帧（用于TCP网络流）"""
        last_time = 0
        self.config.frame_count = 0
        self.config.start_time = time.time()
        
        while self.config.is_running:
            if time.time() - last_time < 1.0 / self.config.fps:
                time.sleep(0.01)
                continue
            last_time = time.time()
            
            # 捕获窗口内容
            frame, win = self.capture_instance.capture_window_content()
            if frame is None:
                # 生成错误信息帧
                img = np.zeros((360, 640, 3), dtype=np.uint8)
                cv2.putText(img, "⚠️ 未检测到目标窗口", (80, 150), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)
                cv2.putText(img, f"标题: '{self.config.window_title}'", (120, 200), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 200, 200), 1)
                if self.capture_instance.win_api_available:
                    cv2.putText(img, "💡 已启用后台捕获", (100, 250), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (100, 200, 100), 1)
                else:
                    cv2.putText(img, "💡 安装pywin32以启用后台捕获", (60, 250), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (100, 200, 100), 1)
                _, buffer = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 70])
                yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
                continue
            
            self.config.last_frame = frame.copy()
            
            if self.config.show_debug:
                fps = self.config.frame_count / (time.time() - self.config.start_time + 0.001)
                info = f"{win.title} | {win.width}x{win.height} | FPS:{fps:.1f}"
                if self.config.use_win_api and self.capture_instance.win_api_available:
                    info += " | Windows API"
                cv2.putText(frame, info, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 
                           0.6, (0, 255, 0), 1, cv2.LINE_AA)
            
            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, self.config.quality])
            self.config.frame_count += 1
            yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

    def _create_flask_app(self):
        app = Flask(__name__)
        
        @app.route('/')
        def index():
            self.config.connected_clients += 1
            html = '''
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
                <title>云窗---云上之窗，让世界仰望你的美</title>
                <style>
                    * { margin:0; padding:0; box-sizing:border-box; }
                    body { 
                        background:#0f0f1b; 
                        color:#e0e0ff; 
                        font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif; 
                        padding:12px; 
                        max-width:100%;
                        margin:0 auto;
                    }
                    header { text-align:center; padding:15px 0; }
                    h1 { font-size:1.9em; margin:8px 0; color:#4da6ff; text-shadow:0 0 10px rgba(77,166,255,0.5); }
                    .container { 
                        background:#1a1a2e; 
                        border-radius:16px; 
                        overflow:hidden; 
                        box-shadow:0 10px 30px rgba(0,0,0,0.7);
                        position:relative;
                        max-width:100vw;
                        margin:0 auto;
                    }
                    #video-container {
                        position:relative;
                        width:100%;
                        overflow:hidden;
                        /* 默认适配模式 */
                        max-width:100%;
                        margin:0 auto;
                    }
                    #video { 
                        width:100%; 
                        display:block; 
                        background:#000; 
                        object-fit: contain; /* 保持宽高比 */
                        max-width:100%;
                        max-height:80vh;
                        margin:0 auto;
                    }
                    /* 拉伸模式 */
                    .stretch #video {
                        object-fit: fill;
                        width:100%;
                        height: 80vh;
                    }
                    /* 填充模式 */
                    .fill #video {
                        object-fit: cover;
                        width:100%;
                        height: 80vh;
                    }
                    .tip { 
                        background:#252540; 
                        padding:12px; 
                        border-radius:10px; 
                        margin:15px 0; 
                        font-size:0.95em; 
                        line-height:1.5;
                        text-align: center;
                    }
                    .status { 
                        text-align:center; 
                        padding:8px; 
                        color:#aaa; 
                        font-size:0.9em; 
                        background:#252540;
                        border-radius:8px;
                        margin-bottom:10px;
                    }
                    .controls {
                        display:flex;
                        justify-content: center;
                        gap:10px;
                        padding:10px;
                        flex-wrap:wrap;
                    }
                    .control-btn {
                        background:#313244;
                        color:white;
                        border:none;
                        padding:8px 15px;
                        border-radius:20px;
                        cursor:pointer;
                        font-size:0.9em;
                    }
                    .control-btn.active {
                        background:#4da6ff;
                        color:white;
                    }
                    .footer { 
                        text-align:center; 
                        margin-top:10px; 
                        color:#666; 
                        font-size:0.85em; 
                        padding:10px 0;
                    }
                    @media (max-width: 768px) {
                        body { padding:8px; }
                        h1 { font-size:1.6em; }
                        .container { border-radius:12px; }
                    }
                    @media (prefers-color-scheme: light) {
                        body { background:#f5f7ff; color:#222; }
                        .container { background:#ffffff; box-shadow:0 5px 20px rgba(0,0,0,0.1); }
                        .tip { background:#f0f4ff; }
                        .status { background:#e8eeff; }
                    }
                    
                    /* 流客户端指示器 */
                    .stream-indicator {
                        position: absolute;
                        top: 10px;
                        right: 10px;
                        background: #4da6ff;
                        color: white;
                        padding: 5px 10px;
                        border-radius: 15px;
                        font-size: 0.8em;
                        z-index: 10;
                    }
                </style>
            </head>
            <body>
                <header>
                    <h1>📱 云窗-屏幕中转</h1>
                    <div class="status">• 计算机和手机需在同一WiFi下 • 点击画面可全屏显示\n采用TCP+UDP双协议传输</div>
                </header>
                
                <div class="container">
                    <div id="video-container">
                        <div class="stream-indicator">流端口: {{ stream_port }}</div>
                        <img id="video" src="{{ url_for('video_feed') }}" alt="屏幕流">
                    </div>
                    
                    <div class="controls">
                        <button class="control-btn active" onclick="setAdaptMode('contain')">适应屏幕</button>
                        <button class="control-btn" onclick="setAdaptMode('fill')">填充屏幕</button>
                        <button class="control-btn" onclick="setAdaptMode('cover')">覆盖屏幕</button>
                    </div>
                </div>
                
                <div class="tip">
                    🔒 安全: 仅限局域网使用 | 延迟约0.8秒 | 
                    当前共享: <b>{{ window_title }}</b> | 尺寸: <span id="resolution">加载中...</span>
                    {% if win_api_available %}
                    <br><span style="color: #a6e3a1;">✅ 已启用Windows API后台捕获</span>
                    {% else %}
                    <br><span style="color: #f38ba8;">⚠️ 缺少pywin32，后台捕获受限，联系开发者</span>
                    {% endif %}
                </div>
                
                <div class="footer">
                    Python Flask • TCP: {{ ip }}:{{ tcp_port }} | 流: {{ ip }}:{{ stream_port }} • {{ time }}
                </div>

                <script>
                    const video = document.getElementById('video');
                    const container = document.getElementById('video-container');
                    const resolutionSpan = document.getElementById('resolution');
                    
                    // 默认适应模式
                    video.style.objectFit = 'contain';
                    
                    // 设置适配模式
                    function setAdaptMode(mode) {
                        const buttons = document.querySelectorAll('.control-btn');
                        buttons.forEach(btn => btn.classList.remove('active'));
                        event.target.classList.add('active');
                        
                        switch(mode) {
                            case 'contain':
                                video.style.objectFit = 'contain';
                                video.style.width = '100%';
                                video.style.height = 'auto';
                                break;
                            case 'fill':
                                video.style.objectFit = 'fill';
                                video.style.width = '100%';
                                video.style.height = '80vh';
                                break;
                            case 'cover':
                                video.style.objectFit = 'cover';
                                video.style.width = '100%';
                                video.style.height = '80vh';
                                break;
                        }
                    }
                    
                    // 监听视频元数据加载事件
                    video.addEventListener('loadedmetadata', function() {
                        resolutionSpan.textContent = this.videoWidth + '×' + this.videoHeight;
                    });
                    
                    // 监听视频尺寸变化
                    video.addEventListener('resize', function() {
                        resolutionSpan.textContent = this.videoWidth + '×' + this.videoHeight;
                    });
                    
                    // 错误处理
                    video.onerror = () => {
                        setTimeout(() => { 
                            video.src = video.src.split('?')[0] + '?t=' + new Date().getTime(); 
                        }, 2000);
                    };
                    
                    // 点击进入全屏
                    video.addEventListener('click', () => {
                        if (video.requestFullscreen) video.requestFullscreen();
                        else if (video.webkitRequestFullscreen) video.webkitRequestFullscreen();
                        else if (video.msRequestFullscreen) video.msRequestFullscreen();
                    });
                    
                    // 防止页面缩放
                    document.addEventListener('touchmove', e => {
                        if (e.scale !== 1) e.preventDefault();
                    }, { passive: false });
                    
                    // 检测设备方向
                    window.addEventListener('orientationchange', function() {
                        setTimeout(function() {
                            // 重新计算容器尺寸
                            const viewport = document.querySelector('meta[name=viewport]');
                            viewport.setAttribute('content', 'width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no');
                        }, 300);
                    }, false);
                    
                    // 定期检查连接状态
                    setInterval(() => {
                        fetch('/check_connection', { method: 'post' })
                            .catch(e => console.log('连接检查失败:', e));
                    }, 5000);
                </script>
            </body>
            </html>
            '''
            return render_template_string(
                html,
                window_title=self.config.window_title,
                ip=self.config.local_ip,
                tcp_port=self.config.tcp_port,
                stream_port=self.config.stream_port,
                time=time.strftime('%H:%M'),
                win_api_available=self.capture_instance.win_api_available
            )
        
        @app.route('/video_feed')
        def video_feed():
            return Response(self._generate_frames(),
                            mimetype='multipart/x-mixed-replace; boundary=frame')
        
        @app.route('/check_connection', methods=['POST'])
        def check_connection():
            """检查连接状态"""
            return {"status": "connected", "clients": len(self.config.stream_clients)}

        return app

    def run(self):
        """运行TCP服务器"""
        try:
            self.app.run(host='0.0.0.0', port=self.config.tcp_port, threaded=True, debug=False)
        except Exception as e:
            logger.error(f"TCP服务器启动失败: {e}")