# utils/screen_capture.py
import cv2
import numpy as np
from PIL import Image
import mss
import logging
from .window_manager import WindowManager

logger = logging.getLogger(__name__)

class ScreenCapture:
    """屏幕捕获类"""
    
    def __init__(self, config):
        self.config = config
        self.win_api_available = self._check_win_api_availability()
        
    def _check_win_api_availability(self) -> bool:
        """检查Windows API是否可用"""
        try:
            import win32gui
            import win32ui
            import win32con
            return True
        except ImportError:
            logger.warning("警告: 未安装pywin32库，无法调用WindowsAPI相关功能，使用默认模式进行屏幕捕获")
            return False
    
    def capture_window_content(self):
        """智能窗口内容捕获"""
        win = WindowManager.find_target_window(self.config.window_title)
        if not win:
            return None, None
        
        if self.config.use_win_api and self.win_api_available:
            # 尝试使用Windows API
            hwnd = win._hWnd  # 获取窗口句柄
            result = self.capture_window_hwnd(hwnd)
            if result is not None:
                return result, win
    
        # 回退到普通模式
        result = self.capture_window_regular(win)
        if result is not None:
            return result, win
    
        return None, None
    
    def capture_window_hwnd(self, hwnd):
        """使用Windows API直接捕获窗口句柄内容（绕过遮挡问题）"""
        if not self.win_api_available:
            return None
            
        try:
            import win32gui
            import win32ui
            import win32con
            
            # 获取窗口位置和大小
            rect = win32gui.GetWindowRect(hwnd)
            x, y, w, h = rect[0], rect[1], rect[2]-rect[0], rect[3]-rect[1]
            
            if w <= 10 or h <= 10:
                return None
                
            # 创建设备上下文
            hwndDC = win32gui.GetWindowDC(hwnd)
            mfcDC = win32ui.CreateDCFromHandle(hwndDC)
            saveDC = mfcDC.CreateCompatibleDC()
            
            # 创建位图
            saveBitMap = win32ui.CreateBitmap()
            saveBitMap.CreateCompatibleBitmap(mfcDC, w, h)
            saveDC.SelectObject(saveBitMap)
            
            # 从窗口复制内容
            result = saveDC.BitBlt((0, 0), (w, h), mfcDC, (0, 0), win32con.SRCCOPY)
            
            # 转换为numpy数组
            bmpinfo = saveBitMap.GetInfo()
            bmpstr = saveBitMap.GetBitmapBits(True)
            im = Image.frombuffer('RGB', (bmpinfo['bmWidth'], bmpinfo['bmHeight']), bmpstr, 'raw', 'BGRX', 0, 1)
            
            # 转换为OpenCV格式
            img = np.array(im)
            if len(img.shape) == 3:
                img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
            
            # 清理
            win32gui.DeleteObject(saveBitMap.GetHandle())
            saveDC.DeleteDC()
            mfcDC.DeleteDC()
            win32gui.ReleaseDC(hwnd, hwndDC)
            
            return img
        except Exception as e:
            logger.error(f"Windows API捕获失败: {e}")
            return None

    def capture_window_regular(self, win):
        """普通屏幕捕获模式"""
        try:
            with mss.mss() as sct:
                monitor = {
                    "top": int(max(0, win.top)),
                    "left": int(max(0, win.left)),
                    "width": int(win.width),
                    "height": int(win.height)
                }
                if monitor["width"] <= 10 or monitor["height"] <= 10:
                    return None
                    
                screenshot = sct.grab(monitor)
                frame = np.array(screenshot)
                if frame.shape[2] == 4:
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
                return frame
        except Exception as e:
            logger.error(f"常规捕获失败: {e}")
            return None