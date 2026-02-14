# utils/window_manager.py
import pygetwindow as gw

class WindowManager:
    """窗口管理类"""
    
    @staticmethod
    def find_target_window(window_title: str):
        """根据标题查找目标窗口"""
        if not window_title:
            return None
        
        # 查找匹配的窗口
        wins = gw.getWindowsWithTitle(window_title)
        if wins:
            return wins[0]
        
        # 如果精确匹配失败，尝试模糊匹配
        all_titles = [t for t in gw.getAllTitles() if t.strip()]
        for title in all_titles:
            if window_title.lower() in title.lower():
                matches = gw.getWindowsWithTitle(title)
                if matches:
                    return matches[0]
        return None