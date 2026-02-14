# gui/main_gui.py
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import cv2
import numpy as np
from PIL import Image, ImageTk
import qrcode
import psutil
import os

class ScreenShareGUI:
    def __init__(self, root, config, capture_instance, tcp_server, stream_server):
        self.root = root
        self.config = config
        self.capture_instance = capture_instance
        self.tcp_server = tcp_server
        self.stream_server = stream_server
        
        self.root.title("云窗---Web服务启动器")
        self.root.iconbitmap('E:\\py项目库与工程文件\\TSW增强工具API版1.0\\正式工具代码部分\\移动端访问\分布架构\\app.ico')
        self.root.geometry("1050x950")
        self.root.minsize(1050, 950)
        self.root.configure(bg="#1e1e2e")

        
        # 创建主要内容框架
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # 创建UI
        self.create_widgets()
        self.refresh_window_list()
        
        # 状态更新定时器
        self.root.after(100, self.update_status)
        self.root.after(200, self.update_preview)
        
        # 窗口关闭处理
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def show_qr_window(self, url):
        """创建独立的二维码扫描窗口"""
        # 避免重复弹窗
        if hasattr(self, 'qr_win') and self.qr_win.winfo_exists():
            self.qr_win.lift()
            return
        
        # 创建新窗口
        qr_win = tk.Toplevel(self.root)
        qr_win.title("📱 扫描二维码快速访问")
        qr_win.geometry("420x520")
        qr_win.configure(bg="#1e1e2e")
        qr_win.resizable(False, False)
        qr_win.attributes('-topmost', True)  # 始终置顶
        
        # 居中显示
        qr_win.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - 420) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - 520) // 2
        qr_win.geometry(f"+{x}+{y}")
        
        # 生成高质量二维码 (400x400)
        qr = qrcode.QRCode(box_size=10, border=4, error_correction=qrcode.constants.ERROR_CORRECT_H)
        qr.add_data(url)
        img = qr.make_image(fill_color="#89b4fa", back_color="#1e1e2e").convert('RGB')
        img = img.resize((400, 400), Image.LANCZOS)
        img_tk = ImageTk.PhotoImage(img)
        
        # 添加到窗口
        qr_label = tk.Label(qr_win, image=img_tk, bg="#1e1e2e")
        qr_label.image = img_tk  # 防止垃圾回收
        qr_label.pack(pady=(20, 10))
        
        # 显示地址 + 复制按钮
        url_label = tk.Label(qr_win, text=url, bg="#1e1e2e", fg="#f9e2af", 
                            font=("Consolas", 10), wraplength=380)
        url_label.pack(pady=(0, 10))
        
        copy_btn = tk.Button(qr_win, text="📋 复制地址", 
                            command=lambda: [qr_win.clipboard_clear(), 
                                        qr_win.clipboard_append(url),
                                        setattr(copy_btn, 'text', '✅ 已复制')],
                            bg="#313244", fg="white", relief="flat", padx=20)
        copy_btn.pack()
        
        # 关闭仅隐藏窗口（不停止服务）
        qr_win.protocol("WM_DELETE_WINDOW", qr_win.destroy)
        self.qr_win = qr_win  # 保存引用

    def create_widgets(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TFrame", background="#1e1e2e")
        style.configure("TLabel", background="#1e1e2e", foreground="#cdd6f4", font=("Segoe UI", 10))
        style.configure("TButton", font=("Segoe UI", 10, "bold"), padding=6)
        style.configure("Start.TButton", background="#31748f", foreground="white")
        style.configure("Stop.TButton", background="#b74c52", foreground="white")
        style.configure("TCombobox", fieldbackground="#313244", background="#313244", foreground="#cdd6f4")
        style.configure("TEntry", fieldbackground="#313244", foreground="#cdd6f4")
        style.map("TCombobox", fieldbackground=[('readonly', '#313244')])
        
        # 顶部标题
        title_frame = ttk.Frame(self.main_frame)
        title_frame.pack(fill="x", padx=20, pady=(15, 10))
        ttk.Label(title_frame, text="🖥️ 云窗---让世界仰望你的美", 
                 font=("Segoe UI", 18, "bold"), foreground="#89b4fa").pack()
        ttk.Label(title_frame, text="实时共享计算机软件窗口至手机/平板浏览器\n             采用TCP+UDP双协议传输", 
                 font=("Segoe UI", 10), foreground="#a6adc8").pack()
        
        # ================== 核心布局：三个区域 ==================
        # 区域1：控制面板 + 预览（左右分割）
        main_pane = ttk.PanedWindow(self.main_frame, orient=tk.HORIZONTAL)
        main_pane.pack(fill="both", expand=True, padx=20, pady=(0, 15))
        
        # 左侧面板：控制设置
        left_frame = ttk.Frame(main_pane)
        main_pane.add(left_frame, weight=1)
        
        # 右侧面板：状态+预览+指南
        right_frame = ttk.Frame(main_pane)
        main_pane.add(right_frame, weight=1)
        
        # --- 左侧面板内容 ---
        control_frame = ttk.LabelFrame(left_frame, text="⚙️ 共享设置", padding=15)
        control_frame.pack(fill="both", expand=True, pady=(0, 10))
        
        # 窗口选择
        ttk.Label(control_frame, text="1. 选择要共享的软件窗口(看不到就刷新):").grid(row=0, column=0, sticky="w", pady=(0,5))
        window_frame = ttk.Frame(control_frame)
        window_frame.grid(row=1, column=0, sticky="ew", pady=(0,15))
        self.window_var = tk.StringVar()
        self.window_combo = ttk.Combobox(window_frame, textvariable=self.window_var, width=35, state="readonly")
        self.window_combo.pack(side="left", padx=(0,5))
        ttk.Button(window_frame, text="🔄 刷新", command=self.refresh_window_list, width=8).pack(side="left")
        
        # 端口设置，可自定义
        ttk.Label(control_frame, text="2. 服务端口（可修改）:").grid(row=2, column=0, sticky="w", pady=(5,5))
        port_frame = ttk.Frame(control_frame)
        port_frame.grid(row=3, column=0, sticky="ew", pady=(0,15))
        
        ttk.Label(port_frame, text="TCP:").pack(side="left", padx=(0,2))
        self.tcp_port_var = tk.StringVar(value=str(self.config.tcp_port))
        ttk.Entry(port_frame, textvariable=self.tcp_port_var, width=8).pack(side="left", padx=(0,5))
        
        ttk.Label(port_frame, text="Stream:").pack(side="left", padx=(5,2))
        self.stream_port_var = tk.StringVar(value=str(self.config.stream_port))
        ttk.Entry(port_frame, textvariable=self.stream_port_var, width=8).pack(side="left", padx=(0,5))
        
        ttk.Label(port_frame, text="(TCP用于网页访问，Stream用于实时传输)").pack(side="left", padx=(5,0))
        
        # 高级参数
        ttk.Label(control_frame, text="3. 高级参数(若调整需要重启服务)").grid(row=4, column=0, sticky="w", pady=(5,5))
        param_frame = ttk.Frame(control_frame)
        param_frame.grid(row=5, column=0, sticky="ew", pady=(0,20))
        
        ttk.Label(param_frame, text="质量(1-100):").grid(row=0, column=0, sticky="w")
        self.quality_var = tk.IntVar(value=self.config.quality)
        ttk.Scale(param_frame, from_=30, to=95, variable=self.quality_var, 
                 orient="horizontal", length=150).grid(row=0, column=1, padx=(5,0))
        self.quality_label = ttk.Label(param_frame, text=str(self.config.quality))
        self.quality_label.grid(row=0, column=2, padx=(5,0))
        self.quality_var.trace("w", lambda *args: self.quality_label.config(text=str(self.quality_var.get())))
        
        ttk.Label(param_frame, text="FPS(1-30):").grid(row=1, column=0, sticky="w", pady=(8,0))
        self.fps_var = tk.IntVar(value=self.config.fps)
        ttk.Scale(param_frame, from_=5, to=30, variable=self.fps_var, 
                 orient="horizontal", length=150).grid(row=1, column=1, padx=(5,0), pady=(8,0))
        self.fps_label = ttk.Label(param_frame, text=str(self.config.fps))
        self.fps_label.grid(row=1, column=2, padx=(5,0), pady=(8,0))
        self.fps_var.trace("w", lambda *args: self.fps_label.config(text=str(self.fps_var.get())))
        
        # 后台捕获选项
        ttk.Label(control_frame, text="4. 捕获模式:").grid(row=6, column=0, sticky="w", pady=(10,5))
        mode_frame = ttk.Frame(control_frame)
        mode_frame.grid(row=7, column=0, sticky="ew", pady=(0,15))
        
        self.win_api_var = tk.BooleanVar(value=self.config.use_win_api)
        if self.capture_instance.win_api_available:
            api_check = ttk.Checkbutton(mode_frame, text="✅ Windows API捕获（推荐）", 
                                       variable=self.win_api_var, command=self.toggle_win_api)
            api_check.pack(anchor="w")
            ttk.Label(mode_frame, text="• 即使窗口被遮挡也能捕获", 
                     foreground="#a6adc8", font=("Segoe UI", 9)).pack(anchor="w", padx=(20,0))
        else:
            ttk.Label(mode_frame, text="⚠️ pywin32库缺失，捕获功能受限，联系开发者", 
                     foreground="#f38ba8", font=("Segoe UI", 9)).pack(anchor="w")
            ttk.Label(mode_frame, text="• 需安装: pip install pywin32", 
                     foreground="#f38ba8", font=("Segoe UI", 9)).pack(anchor="w")
        
        # 按钮区域
        btn_frame = ttk.Frame(control_frame)
        btn_frame.grid(row=8, column=0, pady=(10,0))
        self.start_btn = ttk.Button(btn_frame, text="🚀 开启共享服务", 
                                   style="Start.TButton", command=self.start_server, width=22)
        self.start_btn.pack(side="left", padx=(0,5))
        self.stop_btn = ttk.Button(btn_frame, text="⏹️ 停止服务", 
                                  style="Stop.TButton", command=self.stop_server, width=22, state="disabled")
        self.stop_btn.pack(side="left")
        
        # 二维码显示按钮 - 移到开启服务按钮下方
        qr_btn_frame = ttk.Frame(control_frame)
        qr_btn_frame.grid(row=9, column=0, pady=(10,0))
        self.show_qr_button = ttk.Button(qr_btn_frame, text="📱 显示二维码", 
                                        command=self.open_qr_window, width=22)
        self.show_qr_button.pack()
        
        # 系统资源显示 - 添加在二维码按钮下方，带大小控制
        system_resource_frame = ttk.Frame(control_frame)
        system_resource_frame.grid(row=10, column=0, pady=(10,0))
        
        # 使用ttk.Label并设置字体大小和背景样式
        self.system_resource_label = ttk.Label(
            system_resource_frame, 
            text="系统资源: CPU 0% | 内存 0% | 磁盘 0%", 
            font=("Segoe UI", 15),  # 控制字体大小
            foreground="#a6adc8",
            background="#313244",   # 设置背景颜色
            padding=(10, 5)         # 控制内边距
        )
        self.system_resource_label.pack()
        
        # --- 右侧面板内容 ---
        # 状态面板
        status_frame = ttk.LabelFrame(right_frame, text="📊 服务状态", padding=12)
        status_frame.pack(fill="x", pady=(0, 10))
        
        self.status_text = tk.Text(status_frame, height=4, width=70, 
                                  bg="#181825", fg="#cdd6f4", font=("Consolas", 9), 
                                  relief="flat", wrap="word")
        self.status_text.insert("1.0", "● 等待开启服务...\n● 请选择要共享的软件窗口\n● TCP端口用于网页访问，Stream端口用于实时传输")
        self.status_text.config(state="disabled")
        self.status_text.pack(fill="x")
        
        # 预览区域
        preview_frame = ttk.LabelFrame(right_frame, text="📺 窗口预览（服务开启后实时显示）", padding=10)
        preview_frame.pack(fill="both", expand=True, pady=(0, 10))
        
        self.preview_label = ttk.Label(preview_frame, text="服务开启后将显示实时预览\n(当前无活动窗口)", 
                                      font=("Segoe UI", 11), foreground="#a6adc8", 
                                      background="#181825", relief="solid", padding=25)
        self.preview_label.pack(fill="both", expand=True)
        
        # 用户指南 - 简化版本（无滚动）
        guide_frame = ttk.LabelFrame(right_frame, text="📖 使用指南", padding=12)
        guide_frame.pack(fill="both", expand=True)
        
        guide_content = (
            "✅ 使用步骤:\n"
            "1️⃣ 从下拉列表选择软件窗口（点击🔄刷新最新列表）\n"
            "2️⃣ （可选）调整质量/FPS：低配置电脑建议质量60+ FPS 10\n"
            "3️⃣ 选择捕获模式：\n"
            "   • Windows API捕获（推荐）：\n"
            "     - 窗口被遮挡时仍能正常捕获，最小化无法捕获\n"
            "     - 需要pywin32库，若提示缺失，联系开发者\n"
            "   • 常规屏幕捕获：\n"
            "     - 窗口必须可见才能捕获\n"
            "4️⃣ 点击'🚀 开启共享服务' → 首次使用允许防火墙通过！\n"
            "5️⃣ TCP端口用于网页访问，Stream端口用于实时传输\n"
            "6️⃣ 手机连接同WiFi → 扫描二维码或输入TCP地址\n\n"
            "⚠️ 注意事项:\n"
            "• 仅限局域网使用，切勿暴露至公网！\n"
            "• 最小化时窗口不渲染，无法捕获\n"
            "• Stream传输延迟更低，TCP用于控制界面\n"
            "• 若未安装pywin32，联系开发者\n\n"
            "🔧 故障排除:\n"
            "• 若无法捕获窗口，请确保窗口最大化且未被其他窗口遮挡\n"
            "• 检查防火墙设置，确保Python程序有网络访问权限\n"
            "• 若使用Windows API模式，重启程序可能需要重新授权\n"
            "• 网络不稳定时，降低质量及FPS参数\n"
            "• 手机访问时，确保在同一WiFi网络下\n\n"
            "💡 高级技巧:\n"
            "• 使用Windows API模式捕获被遮挡窗口\n"
            "• TCP端口用于网页界面，Stream端口用于实时传输\n"
            "• 可同时使用两个端口获得更好体验\n"
            "• Stream传输延迟更低，适合实时操作\n"
            "• 网页界面更适合长期观看\n\n"
            "📞 技术支持:\n"
            "• 如遇问题，联系开发者\n"
            "• 提供具体错误信息及系统环境\n"
            "• 我们将尽快提供解决方案\n"
            "• 欢迎反馈改进意见\n"

            """
            本程序采用：TCP+UDP双协议技术进行传输,在我们的系统中，TCP和UDP被分配了不同的职责：
            1.UDP（用户数据报协议） - 承担主要视频流传输任务
            核心作用： 负责传输实时的视频帧数据。
            优势： 由于视频流对少量丢包有一定容忍度（特别是经过压缩编码后），UDP的低延迟特性使得观众几乎可以实时看到屏幕上的变化，非常适合直播、远程演示等场景。

            2.TCP（传输控制协议） - 承担辅助控制和可靠性保障任务
            核心作用： 负责传输控制信息和关键元数据。
            优势： 利用其可靠的传输特性，确保重要指令和状态信息不丢失。

            3.总结
            确保重要指令和状态信息不丢失，主要是通过TCP协议传输以下关键信息：
            连接握手： 客户端连接后，服务器发送STREAM_OK_TCP，客户端回复READY，确保双方连接建立并准备就绪，此过程必须可靠。
            维持连接： TCP长连接本身可让服务器感知客户端是否在线，连接断开即刻可知。
            控制信息： 发送帧大小、帧序号等元数据（如send_tcp_control_info），这些小量但关键的信息若丢失会影响客户端同步，需TCP保证送达。
            TCP的可靠传输特性确保了这些基础通信流程的稳定，而视频数据则由UDP承载以保证低延迟。

            """
        )
        
        if not self.capture_instance.win_api_available:
            guide_content = guide_content.replace("✅ 使用步骤:", "⚠️ 重要提醒:\n⚠️ 未安装pywin32库，仅支持常规捕获模式\n⚠️ 联系开发者\n\n✅ 使用步骤:")
        
        # 在指南框架中添加文本（无滚动）
        guide_text = tk.Text(guide_frame, wrap="word", bg="#181825", 
                             fg="#cdd6f4", font=("Segoe UI", 9), relief="flat", 
                             padx=10, pady=10, height=15, width=60)
        guide_text.insert("1.0", guide_content)
        guide_text.config(state="disabled")
        guide_text.pack(fill="both", expand=True, padx=5, pady=5)
        
        # ================== 底部状态栏 ==================
        self.bottom_status = ttk.Label(self.main_frame, 
                                     text="💡 准备就绪 | 提示：首次使用确认防火墙允许Python通过", 
                                     background="#313244", foreground="#a6adc8", 
                                     font=("Segoe UI", 9), anchor="w", padding=(15, 8))
        self.bottom_status.pack(side="bottom", fill="x", padx=20, pady=(10, 0))
    
    def open_qr_window(self):
        """打开二维码窗口"""
        if self.config.is_running:
            access_url = f"http://{self.config.local_ip}:{self.config.tcp_port}"
            self.show_qr_window(access_url)
        else:
            messagebox.showwarning("警告", "请先开启服务再显示二维码！")
    
    def toggle_win_api(self):
        """切换Windows API模式"""
        self.config.use_win_api = self.win_api_var.get()
    
    def refresh_window_list(self):
        import pygetwindow as gw
        windows = [t for t in gw.getAllTitles() if t.strip() and len(t) < 60]
        windows = sorted(set(windows))
        
        current = self.window_var.get()
        self.window_combo['values'] = windows
        
        if not current and windows:
            defaults = ["微信", "QQ", "钉钉", "Chrome", "Edge", "记事本"]
            for default in defaults:
                for win in windows:
                    if default in win:
                        self.window_var.set(win)
                        return
            self.window_var.set(windows[0])
        elif current in windows:
            self.window_var.set(current)
    
    def update_status(self):
        # 获取系统资源使用情况
        cpu_percent = psutil.cpu_percent(interval=None)
        memory_percent = psutil.virtual_memory().percent
        disk_percent = psutil.disk_usage('/').percent
        
        # 更新系统资源显示标签
        resource_text = f"系统资源: CPU {cpu_percent}% | 内存 {memory_percent}% | 磁盘 {disk_percent}%"
        self.system_resource_label.config(text=resource_text)
        
        if self.config.is_running:
            # 安全计算FPS
            elapsed_time = time.time() - self.config.start_time + 0.001
            fps = self.config.frame_count / elapsed_time
            
            # 安全获取分辨率
            resolution_str = "N/A"
            if self.config.last_frame is not None:
                try:
                    resolution_str = f"{self.config.last_frame.shape[1]}x{self.config.last_frame.shape[0]}"
                except AttributeError:
                    resolution_str = "N/A"
            
            status = (
                f"● 服务运行中 | TCP端口: {self.config.tcp_port} | Stream端口: {self.config.stream_port} | 目标窗口: '{self.config.window_title}'\n"
                f"● 本地访问: http://localhost:{self.config.tcp_port} | 手机访问: http://{self.config.local_ip}:{self.config.tcp_port}\n"
                f"● 流传输: http://{self.config.local_ip}:{self.config.stream_port} | 已连接设备: {len(self.stream_server.clients_tcp) + len(self.stream_server.clients_udp)}\n"
                f"● 状态: 分辨率 {resolution_str} "
                f"| 实时FPS: {fps:.1f} | 捕获模式: {'Windows API' if self.config.use_win_api and self.capture_instance.win_api_available else '常规屏幕'}\n"
            )
            self.bottom_status.config(text=f"🟢 服务运行中 | TCP: http://{self.config.local_ip}:{self.config.tcp_port} | Stream: {self.config.stream_port} | 资源: CPU {cpu_percent}% 内存 {memory_percent}%", 
                                    foreground="#a6e3a1")
        else:
            status = (
                f"● 服务已停止 | 本机IP: {self.config.local_ip}\n"
                f"● TCP端口用于网页访问，Stream端口用于实时传输\n"
                f"● 当前模式: {'Windows API捕获' if self.config.use_win_api and self.capture_instance.win_api_available else '常规屏幕捕获'}\n"
                f"● 防火墙提示：首次使用需要允许Python通过\n"
            )
            self.bottom_status.config(text="💡 准备就绪 | 提示：首次使用确认防火墙允许Python通过", 
                                    foreground="#a6adc8")
        
        self.status_text.config(state="normal")
        self.status_text.delete("1.0", "end")
        self.status_text.insert("1.0", status)
        self.status_text.config(state="disabled")
        
        self.root.after(500, self.update_status)
    
    def update_preview(self):
        if self.config.is_running and self.config.last_frame is not None:
            frame = self.config.last_frame.copy()
            h, w = frame.shape[:2]
            scale = min(350/w, 230/h, 1.0)
            if scale < 1.0:
                frame = cv2.resize(frame, (int(w*scale), int(h*scale)))
            
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(rgb)
            img_tk = ImageTk.PhotoImage(img)
            
            self.preview_label.config(image=img_tk, text="")
            self.preview_label.image = img_tk
        elif not self.config.is_running:
            self.preview_label.config(image="", text="服务开启后将显示实时预览\n(当前无活动窗口)", 
                                    background="#181825")
        
        self.root.after(300, self.update_preview)
    
    def start_server(self):
        title = self.window_var.get().strip()
        if not title:
            messagebox.showwarning("警告", "请先选择要共享的软件窗口！")
            return
        
        try:
            tcp_port = int(self.tcp_port_var.get())
            stream_port = int(self.stream_port_var.get())
            if tcp_port < 1024 or tcp_port > 65535 or stream_port < 1024 or stream_port > 65535:
                raise ValueError
            self.config.tcp_port = tcp_port
            self.config.stream_port = stream_port
        except:
            messagebox.showerror("错误", "端口号必须为1024-65535之间的数字！")
            return
        
        self.config.window_title = title
        self.config.quality = self.quality_var.get()
        self.config.fps = self.fps_var.get()
        self.config.use_win_api = self.win_api_var.get() and self.capture_instance.win_api_available
        self.config.is_running = True
        self.config.connected_clients = 0
        # 初始化stream_clients字典（兼容旧代码）
        self.config.stream_clients = {}
        
        # 启动TCP和Stream服务器
        self.config.tcp_server_thread = threading.Thread(target=self.tcp_server.run, daemon=True)
        # 使用正确的stream_server方法
        self.config.stream_server_thread = threading.Thread(target=self.stream_server.start_servers, daemon=True)
        
        self.config.tcp_server_thread.start()
        self.config.stream_server_thread.start()
        
        # 更新UI
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.window_combo.config(state="disabled")
        
        # 服务线程启动后添加（替换原二维码显示逻辑）：
        access_url = f"http://{self.config.local_ip}:{self.config.tcp_port}"
        self.root.after(300, lambda: self.show_qr_window(access_url))  # 延迟300ms确保服务就绪
        
        # 简短提示
        original_text = self.bottom_status.cget("text")
        self.bottom_status.config(text=f"✅ 服务已启动！TCP: {access_url}, Stream: {self.config.stream_port}", foreground="#a6e3a1")
        self.root.after(3000, lambda: self.bottom_status.config(
            text=f"🟢 服务运行中 | TCP: {access_url}, Stream: {self.config.stream_port}", foreground="#a6e3a1"))
    
    def stop_server(self):
        # 在停止服务逻辑开头添加：
        if hasattr(self, 'qr_win') and self.qr_win.winfo_exists():
            self.qr_win.destroy()
        
        # 改进的停止服务逻辑
        self.config.is_running = False
        
        # 调用stream_server的stop方法
        try:
            self.stream_server.stop()
        except AttributeError:
            # 如果stream_server没有stop方法，则手动关闭
            if hasattr(self.stream_server, 'running'):
                self.stream_server.running = False
            if hasattr(self.stream_server, 'tcp_socket') and self.stream_server.tcp_socket:
                try:
                    self.stream_server.tcp_socket.close()
                except:
                    pass
            if hasattr(self.stream_server, 'udp_socket') and self.stream_server.udp_socket:
                try:
                    self.stream_server.udp_socket.close()
                except:
                    pass
        
        # 清理客户端连接
        if hasattr(self.stream_server, 'clients_tcp'):
            for client_socket in list(self.stream_server.clients_tcp.keys()):
                try:
                    client_socket.close()
                except:
                    pass
            self.stream_server.clients_tcp.clear()
        
        # 等待线程结束
        if hasattr(self.config, 'tcp_server_thread') and self.config.tcp_server_thread and self.config.tcp_server_thread.is_alive():
            try:
                self.config.tcp_server_thread.join(timeout=2.0)  # 2秒超时
            except:
                pass
        
        if hasattr(self.config, 'stream_server_thread') and self.config.stream_server_thread and self.config.stream_server_thread.is_alive():
            try:
                self.config.stream_server_thread.join(timeout=2.0)  # 2秒超时
            except:
                pass
        
        time.sleep(0.3)
        
        # 更新UI
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self.window_combo.config(state="readonly")
        self.preview_label.config(image="", text="服务开启后将显示实时预览\n(当前无活动窗口)", background="#181825")
        
        self.bottom_status.config(text="🛑 服务已停止 | 点击'🚀 开启共享服务'重新启动", foreground="#f38ba8")
    
    def on_closing(self):
        if self.config.is_running:
            if messagebox.askokcancel("确认退出", "服务正在运行，确定退出？\n\n退出后手机将失去访问权限"):
                self.config.is_running = False
                self.stop_server()
                self.cleanup_resources()
                self.root.destroy()
        else:
            self.cleanup_resources()
            self.root.destroy()
    
    def cleanup_resources(self):
        """清理所有资源"""
        import logging
        logger = logging.getLogger(__name__)
        logger.info("正在清理资源...")
        
        # 加锁防止重复清理
        if hasattr(self.config, 'cleanup_lock'):
            with self.config.cleanup_lock:
                # 停止服务
                self.config.is_running = False
                
                # 关闭所有窗口
                try:
                    for widget in self.root.winfo_children():
                        if isinstance(widget, tk.Toplevel):
                            widget.destroy()
                except:
                    pass
                
                # 清理预览图像
                if hasattr(self.preview_label, 'image'):
                    delattr(self.preview_label, 'image')
                
                # 清理二维码窗口
                if hasattr(self, 'qr_win'):
                    try:
                        self.qr_win.destroy()
                    except:
                        pass
                    delattr(self, 'qr_win')
                
                # 关闭所有客户端连接
                if hasattr(self.stream_server, 'clients_tcp'):
                    for client_socket in list(self.stream_server.clients_tcp.keys()):
                        try:
                            client_socket.close()
                        except:
                            pass
                    self.stream_server.clients_tcp.clear()
                
                # 关闭Stream套接字
                if hasattr(self.stream_server, 'tcp_socket') and self.stream_server.tcp_socket:
                    try:
                        self.stream_server.tcp_socket.close()
                    except:
                        pass
                
                if hasattr(self.stream_server, 'udp_socket') and self.stream_server.udp_socket:
                    try:
                        self.stream_server.udp_socket.close()
                    except:
                        pass
                
                # 等待线程结束
                if hasattr(self.config, 'tcp_server_thread') and self.config.tcp_server_thread and self.config.tcp_server_thread.is_alive():
                    try:
                        self.config.tcp_server_thread.join(timeout=3.0)  # 3秒超时
                    except:
                        pass
                
                if hasattr(self.config, 'stream_server_thread') and self.config.stream_server_thread and self.config.stream_server_thread.is_alive():
                    try:
                        self.config.stream_server_thread.join(timeout=3.0)  # 3秒超时
                    except:
                        pass
                
                # 清理配置对象
                self.config.last_frame = None
                logger.info("资源清理完成")
                
                # 记录进程ID供后续检查
                import psutil
                process = psutil.Process()
                logger.info(f"进程 {process.pid} 资源清理完成")
        else:
            # 如果没有cleanup_lock，则直接执行清理
            self.config.is_running = False
            
            # 关闭所有窗口
            try:
                for widget in self.root.winfo_children():
                    if isinstance(widget, tk.Toplevel):
                        widget.destroy()
            except:
                pass
            
            # 清理预览图像
            if hasattr(self.preview_label, 'image'):
                delattr(self.preview_label, 'image')
            
            # 清理二维码窗口
            if hasattr(self, 'qr_win'):
                try:
                    self.qr_win.destroy()
                except:
                    pass
                delattr(self, 'qr_win')
            
            # 关闭所有客户端连接
            if hasattr(self.stream_server, 'clients_tcp'):
                for client_socket in list(self.stream_server.clients_tcp.keys()):
                    try:
                        client_socket.close()
                    except:
                        pass
                self.stream_server.clients_tcp.clear()
            
            # 关闭Stream套接字
            if hasattr(self.stream_server, 'tcp_socket') and self.stream_server.tcp_socket:
                try:
                    self.stream_server.tcp_socket.close()
                except:
                    pass
            
            if hasattr(self.stream_server, 'udp_socket') and self.stream_server.udp_socket:
                try:
                    self.stream_server.udp_socket.close()
                except:
                    pass
            
            # 等待线程结束
            if hasattr(self.config, 'tcp_server_thread') and self.config.tcp_server_thread and self.config.tcp_server_thread.is_alive():
                try:
                    self.config.tcp_server_thread.join(timeout=3.0)  # 3秒超时
                except:
                    pass
            
            if hasattr(self.config, 'stream_server_thread') and self.config.stream_server_thread and self.config.stream_server_thread.is_alive():
                try:
                    self.config.stream_server_thread.join(timeout=3.0)  # 3秒超时
                except:
                    pass
            
            # 清理配置对象
            self.config.last_frame = None
            logger.info("资源清理完成")

# 示例配置类（用于测试）
class Config:
    def __init__(self):
        self.tcp_port = 8080
        self.stream_port = 8081
        self.window_title = ""
        self.quality = 75
        self.fps = 15
        self.use_win_api = True
        self.is_running = False
        self.connected_clients = 0
        self.stream_clients = {}
        self.local_ip = "127.0.0.1"
        self.frame_count = 0
        self.start_time = time.time()
        self.last_frame = None
        self.tcp_server_thread = None
        self.stream_server_thread = None
        import threading
        self.cleanup_lock = threading.Lock()

# 示例TCP服务器类（用于测试）
class TCPServer:
    def run(self):
        print("TCP Server running...")

# 示例流服务器类（用于测试）
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
        self.running = True
    
    def start_servers(self):
        """启动TCP和UDP服务器"""
        print("Stream server started...")
    
    def stop(self):
        """停止服务器"""
        self.running = False
        print("Stream server stopped...")

if __name__ == "__main__":
    root = tk.Tk()
    
    # 创建模拟实例
    config = Config()
    class MockCaptureInstance:
        def __init__(self):
            self.win_api_available = True
    
    capture_instance = MockCaptureInstance()
    tcp_server = TCPServer()
    stream_server = DualprotocolStreamServer(config, capture_instance)
    
    app = ScreenShareGUI(root, config, capture_instance, tcp_server, stream_server)
    root.mainloop()