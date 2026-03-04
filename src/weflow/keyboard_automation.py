import time
import logging
import pyautogui
import pyperclip
import ctypes
from ctypes import wintypes
import subprocess

class KeyboardAutomation:
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        pyautogui.PAUSE = 0.1
        
        self.user32 = ctypes.WinDLL('user32', use_last_error=True)
        self.user32.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
        self.user32.FindWindowW.restype = wintypes.HWND
        self.user32.SetForegroundWindow.argtypes = [wintypes.HWND]
        self.user32.SetForegroundWindow.restype = wintypes.BOOL
        self.user32.IsWindowVisible.argtypes = [wintypes.HWND]
        self.user32.IsWindowVisible.restype = wintypes.BOOL
        self.user32.IsIconic.argtypes = [wintypes.HWND]
        self.user32.IsIconic.restype = wintypes.BOOL

    def _get_shortcut(self, key_name, fallback):
        """从配置中获取快捷键，如果不存在则使用默认值"""
        shortcuts = self.config.get('wechat_shortcuts', {})
        return shortcuts.get(key_name, fallback)

    def _get_wechat_window_handle(self):
        """获取微信窗口句柄"""
        class_names = ['WeChatMainWndForPC', 'WeChatMainWND', 'WeChat']
        hwnd = None
        
        for class_name in class_names:
            hwnd = self.user32.FindWindowW(class_name, None)
            if hwnd:
                break
        
        if not hwnd:
            hwnd = self.user32.FindWindowW(None, '微信')
        
        return hwnd

    def _activate_wechat_window(self):
        """激活微信窗口"""
        try:
            hwnd = self._get_wechat_window_handle()
            if not hwnd:
                self.logger.warning("未找到微信窗口句柄")
                return False
            
            # 如果窗口最小化，则还原
            if self.user32.IsIconic(hwnd):
                self.user32.ShowWindow(hwnd, 9)  # SW_RESTORE = 9
            
            # 将窗口置顶并激活
            self.user32.SetForegroundWindow(hwnd)
            time.sleep(0.1)
            
            self.logger.info("已激活微信窗口")
            return True
        except Exception as e:
            self.logger.error(f"激活微信窗口失败: {e}")
            return False

    def press_shortcut(self, shortcut):
        """按下快捷键组合"""
        try:
            keys = shortcut.lower().split('+')
            self.logger.info(f"按下快捷键: {shortcut}")

            # 处理单个按键的情况（如 Enter）
            if len(keys) == 1:
                pyautogui.press(keys[0])
            else:
                with pyautogui.hold(keys[:-1]):
                    pyautogui.press(keys[-1])

            time.sleep(0.1)
            return True
        except Exception as e:
            self.logger.error(f"执行快捷键失败: {e}")
            return False

    def type_text(self, text):
        """输入文本（使用粘贴方式）"""
        try:
            self.logger.info(f"输入文本: {text}")
            pyperclip.copy(text)
            time.sleep(0.05)
            self.press_shortcut('ctrl+v')
            return True
        except Exception as e:
            self.logger.error(f"输入文本失败: {e}")
            return False

    def _bring_wechat_to_front(self):
        """唤起微信到前台（只激活窗口，不执行显示/隐藏快捷键）"""
        try:
            self.logger.info("开始唤起微信...")
            
            # 直接使用窗口句柄激活微信
            self._activate_wechat_window()
            time.sleep(0.1)
            
            return True
        except Exception as e:
            self.logger.error(f"唤起微信失败: {e}")
            return False

    def execute_test_message(self, session_contact_remark):
        """
        执行测试消息发送流程

        流程：
        1. 监听到新消息时，立刻重新检测微信状态
        2. 根据微信状态执行对应次数的显示/隐藏窗口快捷键：
           - 微信后台运行(状态1): 执行1次
           - 微信窗口已打开(状态2): 执行1次
           - 微信窗口是当前活动窗口(状态3): 执行0次
           - 微信未运行(状态0): 停止后续所有操作
        3. 唤起微信到前台
        4. 快捷键 Ctrl+2 (切换会话)
        5. 快捷键 Ctrl+F (搜索)
        6. 粘贴所选会话的联系人备注
        7. 快捷键 Enter (选中搜索结果)
        8. 输入测试文本"这是一条测试消息"
        """
        try:
            self.logger.info("开始执行测试消息发送流程")

            # 1. 立刻重新检测微信状态
            from weflow.status_checker import check_weixin_status
            status_code, status_description = check_weixin_status()
            self.logger.info(f"当前微信状态: {status_description} (状态码: {status_code})")

            # 2. 根据状态决定是否停止
            if status_code == 0:
                self.logger.error("微信未运行，停止后续所有操作")
                return False

            # 3. 获取快捷键配置
            show_hide_shortcut = self._get_shortcut('show_hide_window', 'Ctrl+Alt+W')
            
            # 根据状态决定显示/隐藏快捷键的执行次数
            # 状态1（后台运行）和状态2（窗口已打开）: 执行1次
            # 状态3（当前活动窗口）: 执行0次
            toggle_count = 0
            if status_code == 1:
                toggle_count = 1
            elif status_code == 2:
                toggle_count = 1
            elif status_code == 3:
                toggle_count = 0

            self.logger.info(f"根据微信状态 {status_description}，将执行 {toggle_count} 次显示/隐藏微信窗口快捷键")

            # 4. 执行根据状态确定的显示/隐藏次数（仅用于调整微信状态）
            for i in range(toggle_count):
                self.logger.info(f"执行第{i+1}次显示/隐藏微信窗口快捷键")
                if not self.press_shortcut(show_hide_shortcut):
                    self.logger.error(f"执行第{i+1}次显示/隐藏窗口快捷键失败")
                    return False
                time.sleep(0.1)

            # 5. 唤起微信到前台
            if not self._bring_wechat_to_front():
                self.logger.error("唤起微信失败")
                return False

            # 6. 再次检测状态，确认微信已唤起
            status_code, status_description = check_weixin_status()
            self.logger.info(f"唤起后微信状态: {status_description} (状态码: {status_code})")

            if status_code == 0:
                self.logger.error("微信未运行，停止后续所有操作")
                return False

            # 7. 获取其他快捷键配置
            switch_session_shortcut = self._get_shortcut('switch_session', 'Ctrl+2')
            search_shortcut = self._get_shortcut('search', 'Ctrl+F')
            select_shortcut = self._get_shortcut('select', 'Enter')
            paste_shortcut = self._get_shortcut('paste', 'Ctrl+V')
            send_shortcut = self._get_shortcut('send_message', 'Enter')

            self.logger.info(f"快捷键配置: 切换会话={switch_session_shortcut}, 搜索={search_shortcut}, "
                           f"选中={select_shortcut}, 粘贴={paste_shortcut}, 发送={send_shortcut}")

            # 8. 执行后续操作：切换会话
            if not self.press_shortcut(switch_session_shortcut):
                self.logger.error("执行切换会话快捷键失败")
                return False
            time.sleep(0.1)

            # 9. 搜索
            if not self.press_shortcut(search_shortcut):
                self.logger.error("执行搜索快捷键失败")
                return False
            time.sleep(0.1)

            # 10. 输入联系人备注
            if not self.type_text(session_contact_remark):
                self.logger.error("输入联系人备注失败")
                return False
            time.sleep(0.1)

            # 11. 选中搜索结果
            if not self.press_shortcut(select_shortcut):
                self.logger.error("执行选中快捷键失败")
                return False
            time.sleep(0.1)



            # 13. 粘贴测试消息
            test_message = "这是一条测试消息"
            self.logger.info(f"复制消息到剪贴板: {test_message}")
            pyperclip.copy(test_message)
            time.sleep(0.05)

            if not self.press_shortcut(paste_shortcut):
                self.logger.error("执行粘贴快捷键失败")
                return False
            time.sleep(0.1)

            # 14. 发送消息
            if not self.press_shortcut(send_shortcut):
                self.logger.error("执行发送快捷键失败")
                return False

            # 15. 发送消息后隐藏窗口（如果配置启用）
            hide_after_send = self.config.get('wechat_shortcuts', {}).get('hide_after_send', True)
            if hide_after_send:
                self.logger.info("配置已启用发送消息后隐藏窗口，执行显示/隐藏微信窗口快捷键")
                show_hide_shortcut = self._get_shortcut('show_hide_window', 'Ctrl+Alt+W')
                if not self.press_shortcut(show_hide_shortcut):
                    self.logger.error("执行显示/隐藏窗口快捷键失败")
                    # 不返回失败，因为消息已经发送成功

            self.logger.info("测试消息发送流程执行完成")
            return True
        except Exception as e:
            self.logger.error(f"执行测试消息失败: {e}")
            return False