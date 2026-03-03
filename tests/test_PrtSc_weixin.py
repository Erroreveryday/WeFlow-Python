import win32gui
import win32con
from PIL import ImageGrab
import psutil

def get_window_handle(window_title_keyword):
    """
    根据窗口标题关键词查找目标窗口的句柄
    :param window_title_keyword: 窗口标题包含的关键词（如"微信"）
    :return: 目标窗口句柄，未找到返回0
    """
    hwnd_target = 0
    
    def callback(hwnd, extra):
        nonlocal hwnd_target
        # 获取窗口标题
        try:
            window_title = win32gui.GetWindowText(hwnd)
            # 判断窗口是否可见，且标题包含目标关键词
            if win32gui.IsWindowVisible(hwnd) and window_title_keyword in window_title:
                hwnd_target = hwnd
                return False  # 找到后停止遍历
        except Exception as e:
            # 忽略获取窗口标题时的错误
            pass
        return True
    
    # 使用 try-except 捕获可能的错误
    try:
        # 使用 win32gui.EnumWindows
        win32gui.EnumWindows(callback, None)
    except Exception as e:
        print(f"枚举窗口时出错: {e}")
        # 尝试使用 FindWindow 作为备选方案
        hwnd_target = win32gui.FindWindow(None, window_title_keyword)
        # 如果直接查找失败，尝试使用更通用的方法
        if hwnd_target == 0:
            print("尝试使用备用方法查找窗口...")
            # 尝试使用类名查找微信窗口
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
    
    # 确保窗口在前台（可选，避免窗口被遮挡）
    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)  # 恢复最小化窗口
    win32gui.SetForegroundWindow(hwnd)
    
    # 处理DPI缩放问题
    import ctypes
    user32 = ctypes.windll.user32
    # 获取系统DPI
    dpi = user32.GetDpiForWindow(hwnd)
    # 计算缩放因子
    scale_factor = dpi / 96.0
    print(f"DPI缩放因子: {scale_factor}")
    
    # 获取窗口的位置和尺寸（左、上、右、下）
    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
    print(f"原始窗口位置：左={left}, 上={top}, 右={right}, 下={bottom}")
    
    # 调整坐标以适应DPI缩放
    left = int(left * scale_factor)
    top = int(top * scale_factor)
    right = int(right * scale_factor)
    bottom = int(bottom * scale_factor)
    print(f"调整后窗口位置：左={left}, 上={top}, 右={right}, 下={bottom}")
    
    # 截取指定区域的屏幕
    try:
        # ImageGrab.grab在Windows下支持指定区域，参数为(x1, y1, x2, y2)
        screenshot = ImageGrab.grab(bbox=(left, top, right, bottom))
        return screenshot
    except Exception as e:
        print(f"截图失败：{e}")
        # 尝试使用原始坐标
        try:
            print("尝试使用原始坐标截图...")
            left, top, right, bottom = win32gui.GetWindowRect(hwnd)
            screenshot = ImageGrab.grab(bbox=(left, top, right, bottom))
            return screenshot
        except Exception as e2:
            print(f"原始坐标截图也失败：{e2}")
            return None

if __name__ == "__main__":
    # 目标程序窗口标题关键词（微信的窗口标题会包含"微信"）
    target_app = "微信"
    
    # 1. 查找微信窗口句柄
    hwnd_wechat = get_window_handle(target_app)
    
    # 2. 截取微信窗口
    if hwnd_wechat:
        wechat_screenshot = capture_window(hwnd_wechat)
        if wechat_screenshot:
            # 3. 保存截图（也可以直接显示）
            save_path = "wechat_screenshot.png"
            wechat_screenshot.save(save_path)
            wechat_screenshot.show()  # 打开截图预览
            print(f"截图成功！已保存至：{save_path}")
    else:
        print(f"未找到包含'{target_app}'的窗口，请确认程序已启动且窗口可见！")