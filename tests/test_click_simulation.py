import win32gui
import win32con
import pyautogui
from PIL import ImageGrab
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from utils.ocr import rapid_ocr_recognize

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
    
    import ctypes
    user32 = ctypes.windll.user32
    dpi = user32.GetDpiForWindow(hwnd)
    scale_factor = dpi / 96.0
    
    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
    
    print(f"原始窗口位置：左={left}, 上={top}, 右={right}, 下={bottom}")
    print(f"DPI缩放因子: {scale_factor}")
    
    # ImageGrab.grab需要物理屏幕坐标，GetWindowRect返回的是逻辑坐标
    # 直接使用GetWindowRect返回的坐标即可，不需要乘以缩放因子
    try:
        screenshot = ImageGrab.grab(bbox=(left, top, right, bottom))
        return screenshot, (left, top, right, bottom)
    except Exception as e:
        print(f"截图失败：{e}")
        return None, None

def parse_ocr_output(ocr_output):
    """
    解析OCR输出，提取文本、位置和置信度
    :param ocr_output: OCR输出的字符串列表
    :return: 包含文本信息的字典列表
    """
    results = []
    for line in ocr_output:
        parts = line.split('|')
        if len(parts) >= 2:
            text = parts[0]
            coords = parts[1].split(',')
            if len(coords) == 4:
                x1, y1, x2, y2 = map(float, coords)
                score = float(parts[2]) if len(parts) > 2 else 0.0
                results.append({
                    'text': text,
                    'x1': x1,
                    'y1': y1,
                    'x2': x2,
                    'y2': y2,
                    'score': score
                })
    return results

def find_text_position(ocr_results, target_text):
    """
    在OCR结果中查找目标文本的位置
    优先选择左侧，再选择上侧
    :param ocr_results: OCR识别结果列表
    :param target_text: 目标文本
    :return: 目标文本的中心坐标，未找到返回None
    """
    matches = []
    for result in ocr_results:
        if result['text'] == target_text:
            matches.append(result)
    
    if not matches:
        return None
    
    print(f"找到 {len(matches)} 个匹配项：{target_text}")
    for i, match in enumerate(matches):
        print(f"  匹配{i+1}: 位置({match['x1']:.0f},{match['y1']:.0f})~({match['x2']:.0f},{match['y2']:.0f}), 置信度:{match['score']:.2f}")
    
    # 按x1升序排序（优先左侧），然后按y1升序排序（再优先上侧）
    matches.sort(key=lambda x: (x['x1'], x['y1']))
    
    # 选择第一个（最左上方的）
    selected = matches[0]
    center_x = (selected['x1'] + selected['x2']) / 2
    center_y = (selected['y1'] + selected['y2']) / 2
    
    print(f"选择位置: ({center_x:.0f}, {center_y:.0f})")
    return center_x, center_y

def simulate_click(x, y, window_pos=None):
    """
    模拟鼠标点击
    :param x: 相对于截图的x坐标
    :param y: 相对于截图的y坐标
    :param window_pos: 窗口的绝对位置 (left, top, right, bottom)
    """
    if window_pos:
        # 将相对坐标转换为绝对屏幕坐标
        screen_x = window_pos[0] + x
        screen_y = window_pos[1] + y
    else:
        screen_x = x
        screen_y = y
    
    print(f"点击屏幕坐标: ({screen_x:.0f}, {screen_y:.0f})")
    
    # 移动鼠标到目标位置
    pyautogui.moveTo(screen_x, screen_y, duration=0.5)
    # 执行点击
    pyautogui.click(screen_x, screen_y)
    print("点击完成")

def main():
    target_text = "测试"
    target_app = "微信"
    save_path = "wechat_screenshot.png"
    
    print(f"===== 模拟点击测试程序 =====")
    print(f"目标文本: {target_text}")
    print(f"目标窗口: {target_app}")
    print()
    
    # 1. 查找微信窗口句柄
    print("步骤1: 查找微信窗口...")
    hwnd_wechat = get_window_handle(target_app)
    
    if not hwnd_wechat:
        print(f"未找到包含'{target_app}'的窗口，请确认程序已启动且窗口可见！")
        return
    
    print(f"找到窗口句柄: {hwnd_wechat}")
    
    # 2. 截取微信窗口
    print("\n步骤2: 截取微信窗口...")
    wechat_screenshot, window_pos = capture_window(hwnd_wechat)
    
    if not wechat_screenshot:
        print("截图失败！")
        return
    
    wechat_screenshot.save(save_path)
    print(f"截图成功！已保存至：{save_path}")
    print(f"窗口位置: 左={window_pos[0]}, 上={window_pos[1]}, 右={window_pos[2]}, 下={window_pos[3]}")
    
    # 3. OCR识别
    print("\n步骤3: OCR识别...")
    
    # 重定向标准输出以捕获OCR输出
    from io import StringIO
    import sys
    
    old_stdout = sys.stdout
    sys.stdout = captured_output = StringIO()
    
    rapid_ocr_recognize(save_path)
    
    sys.stdout = old_stdout
    ocr_output = captured_output.getvalue().strip().split('\n')
    
    print("OCR识别结果:")
    for line in ocr_output:
        print(f"  {line}")
    
    # 4. 解析OCR结果
    print("\n步骤4: 解析OCR结果...")
    ocr_results = parse_ocr_output(ocr_output)
    print(f"解析出 {len(ocr_results)} 条文本记录")
    
    # 5. 查找目标文本位置
    print(f"\n步骤5: 查找目标文本 '{target_text}'...")
    text_pos = find_text_position(ocr_results, target_text)
    
    if not text_pos:
        print(f"未找到文本 '{target_text}'！")
        return
    
    # 6. 模拟点击
    print(f"\n步骤6: 模拟点击...")
    simulate_click(text_pos[0], text_pos[1], window_pos)
    
    print("\n===== 程序执行完成 =====")

if __name__ == "__main__":
    main()