import win32gui
import win32con
from PIL import ImageGrab
import ctypes

def get_window_handle(window_title_keyword):
    """
    根据窗口标题关键词查找目标窗口的句柄
    :param window_title_keyword: 窗口标题包含的关键词（如"微信"）
    :return: 目标窗口句柄，未找到返回0
    """
    hwnd_target = 0
    
    def callback(hwnd, extra):
        nonlocal hwnd_target
        try:
            window_title = win32gui.GetWindowText(hwnd)
            if win32gui.IsWindowVisible(hwnd) and window_title_keyword in window_title:
                hwnd_target = hwnd
                return False
        except Exception as e:
            pass
        return True
    
    try:
        win32gui.EnumWindows(callback, None)
    except Exception as e:
        print(f"枚举窗口时出错: {e}")
        hwnd_target = win32gui.FindWindow(None, window_title_keyword)
        if hwnd_target == 0:
            print("尝试使用备用方法查找窗口...")
            hwnd_target = win32gui.FindWindow("WeChatMainWndForPC", None)
    
    return hwnd_target

def capture_window(hwnd):
    """
    根据窗口句柄截取该窗口的界面
    :param hwnd: 窗口句柄
    :return: 截取的PIL图像对象，失败返回None
    """
    if hwnd == 0:
        print("未找到目标窗口！")
        return None
    
    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
    win32gui.SetForegroundWindow(hwnd)
    
    user32 = ctypes.windll.user32
    dpi = user32.GetDpiForWindow(hwnd)
    scale_factor = dpi / 96.0
    print(f"DPI缩放因子: {scale_factor}")
    
    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
    print(f"原始窗口位置：左={left}, 上={top}, 右={right}, 下={bottom}")
    
    left = int(left * scale_factor)
    top = int(top * scale_factor)
    right = int(right * scale_factor)
    bottom = int(bottom * scale_factor)
    print(f"调整后窗口位置：左={left}, 上={top}, 右={right}, 下={bottom}")
    
    try:
        screenshot = ImageGrab.grab(bbox=(left, top, right, bottom))
        return screenshot
    except Exception as e:
        print(f"截图失败：{e}")
        try:
            print("尝试使用原始坐标截图...")
            left, top, right, bottom = win32gui.GetWindowRect(hwnd)
            screenshot = ImageGrab.grab(bbox=(left, top, right, bottom))
            return screenshot
        except Exception as e2:
            print(f"原始坐标截图也失败：{e2}")
            return None

def capture_window_by_title(window_title_keyword):
    """
    根据窗口标题关键词直接截取窗口（组合函数）
    :param window_title_keyword: 窗口标题包含的关键词
    :return: 截取的PIL图像对象，失败返回None
    """
    hwnd = get_window_handle(window_title_keyword)
    return capture_window(hwnd)
