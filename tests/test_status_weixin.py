import psutil
import os
import ctypes
from ctypes import wintypes

# 定义Windows API常量
GW_OWNER = 4
GW_HWNDNEXT = 2
SW_HIDE = 0
SW_SHOWNORMAL = 1
SW_SHOWMINIMIZED = 2
SW_SHOWMAXIMIZED = 3

# 定义结构体
class WINDOWPLACEMENT(ctypes.Structure):
    _fields_ = [
        ('length', wintypes.UINT),
        ('flags', wintypes.UINT),
        ('showCmd', wintypes.UINT),
        ('ptMinPosition', wintypes.POINT),
        ('ptMaxPosition', wintypes.POINT),
        ('rcNormalPosition', wintypes.RECT),
    ]

# 定义Windows API函数
user32 = ctypes.WinDLL('user32', use_last_error=True)
user32.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
user32.FindWindowW.restype = wintypes.HWND
user32.GetWindowPlacement.argtypes = [wintypes.HWND, ctypes.POINTER(WINDOWPLACEMENT)]
user32.GetWindowPlacement.restype = wintypes.BOOL
user32.GetForegroundWindow.argtypes = []
user32.GetForegroundWindow.restype = wintypes.HWND
user32.IsWindowVisible.argtypes = [wintypes.HWND]
user32.IsWindowVisible.restype = wintypes.BOOL

def is_weixin_running():
    """
    检测微信（Weixin.exe）是否正在运行
    考虑前台和后台运行的情况
    """
    for proc in psutil.process_iter(['pid', 'name', 'status']):
        try:
            if proc.info['name'] == 'Weixin.exe':
                print(f"微信进程已找到，PID: {proc.info['pid']}, 状态: {proc.info['status']}")
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    print("未找到微信进程")
    return False

def get_weixin_window_status():
    """
    获取微信窗口的状态
    返回值：
    - 0: 微信未运行
    - 1: 微信后台运行（托盘状态，无界面）
    - 2: 微信窗口打开但被其他窗口覆盖
    - 3: 微信窗口是当前活动窗口
    """
    # 首先检查微信是否运行
    if not is_weixin_running():
        return 0
    
    # 查找微信窗口 - 尝试多种类名
    class_names = ['WeChatMainWndForPC', 'WeChatMainWND', 'WeChat']
    hwnd = None
    
    for class_name in class_names:
        hwnd = user32.FindWindowW(class_name, None)
        if hwnd:
            break
    
    if not hwnd:
        # 尝试通过标题查找
        hwnd = user32.FindWindowW(None, '微信')
        if not hwnd:
            return 1
    
    # 检查窗口是否可见
    is_visible = user32.IsWindowVisible(hwnd)
    
    # 检查窗口的显示状态
    placement = WINDOWPLACEMENT()
    placement.length = ctypes.sizeof(WINDOWPLACEMENT)
    user32.GetWindowPlacement(hwnd, ctypes.byref(placement))
    
    # 检查窗口是否被最小化、隐藏或不可见
    if not is_visible or placement.showCmd == SW_HIDE or placement.showCmd == SW_SHOWMINIMIZED:
        return 1
    
    # 检查是否是活动窗口
    foreground_hwnd = user32.GetForegroundWindow()
    if hwnd == foreground_hwnd:
        return 3
    else:
        return 2

def get_status_description(status_code):
    """
    根据状态码获取状态描述
    """
    status_map = {
        0: "微信未运行",
        1: "微信后台运行（托盘状态，无界面）",
        2: "微信窗口打开但被其他窗口覆盖",
        3: "微信窗口是当前活动窗口"
    }
    return status_map.get(status_code, "未知状态")

if __name__ == "__main__":
    print("开始检测微信运行状态...")
    status_code = get_weixin_window_status()
    status_description = get_status_description(status_code)
    print(f"检测结果: {status_description}")
