import time
import logging
import pyautogui
import pyperclip
import ctypes
from ctypes import wintypes
import subprocess
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.deepseek import DeepSeekClient

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
        
        self.ai_stream_callbacks = {
            'thinking': None,
            'content': None
        }

    def _get_shortcut(self, key_name, fallback):
        """从配置中获取快捷键，如果不存在则使用默认值"""
        shortcuts = self.config.get('wechat_shortcuts', {})
        return shortcuts.get(key_name, fallback)
    
    def set_ai_stream_callbacks(self, thinking_callback=None, content_callback=None, reasoning_finished_callback=None):
        """
        设置 AI 流式输出的回调函数
        
        Args:
            thinking_callback: 推理内容流式回调函数
            content_callback: 最终内容流式回调函数
            reasoning_finished_callback: 推理完成回调函数
        """
        self.ai_stream_callbacks['thinking'] = thinking_callback
        self.ai_stream_callbacks['content'] = content_callback
        self.ai_stream_callbacks['reasoning_finished'] = reasoning_finished_callback
        print(f"AI 流式回调已设置: thinking={thinking_callback is not None}, content={content_callback is not None}, reasoning_finished={reasoning_finished_callback is not None}")

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

    def execute_test_message(self, session):
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
        8. 输入回复内容（固定文本或 AI 生成）
        """
        try:
            self.logger.info("开始执行测试消息发送流程")
            session_contact_remark = session.get('contact_remark', '')
            
            # 1. 立刻重新检测微信状态
            from weflow.status_checker import check_weixin_status
            status_code, status_description = check_weixin_status()
            self.logger.info(f"当前微信状态: {status_description} (状态码: {status_code})")

            # 2. 根据状态决定是否停止
            if status_code == 0:
                self.logger.error("微信未运行，停止后续所有操作")
                return False

            # 3. 先准备好回复内容（这样后面可以快速执行键盘操作）
            auto_reply_config = self.config.get('auto_reply', {})
            reply_type = auto_reply_config.get('reply_type', 'fixed')
            
            if reply_type == 'fixed':
                test_message = auto_reply_config.get('fixed_text', '这是一条测试消息')
                self.logger.info(f"使用固定文本回复: {test_message}")
            else:
                # 使用 AI 大模型生成回复
                ai_config = auto_reply_config.get('ai_config', {})
                provider = ai_config.get('provider', 'deepseek')
                
                if provider == 'deepseek':
                    self.logger.info("使用 DeepSeek 模型生成回复...")
                    deepseek_config = ai_config.get('deepseek', {})
                    self.logger.info(f"DeepSeek配置: {deepseek_config}")
                    api_key = deepseek_config.get('api_key', '')
                    if not api_key:
                        api_key = self.config.get('ai', {}).get('api_key', '')
                    model = deepseek_config.get('model', 'deepseek-chat')
                    if not model:
                        model = self.config.get('ai', {}).get('model', 'deepseek-chat')
                    default_system_prompt = deepseek_config.get('system_prompt', '你模拟我与对方聊天。')
                    self.logger.info(f"默认系统提示词: {default_system_prompt}")
                    thinking_mode = ai_config.get('thinking_mode', False)
                    temperature = ai_config.get('temperature', 1.3)
                    message_limit = ai_config.get('message_limit', 10)
                    
                    if not api_key:
                        self.logger.error("DeepSeek API Key 未配置，中止回复流程")
                        return False
                    else:
                        port = self.config.get('weflow_api_port', 5031)
                        weflow_base_url = f"http://127.0.0.1:{port}"
                        
                        deepseek_client = DeepSeekClient(
                            api_key=api_key,
                            model=model
                        )
                        
                        thinking_callback = self.ai_stream_callbacks.get('thinking')
                        content_callback = self.ai_stream_callbacks.get('content')
                        reasoning_finished_callback = self.ai_stream_callbacks.get('reasoning_finished')
                        
                        has_stream_callback = thinking_callback or content_callback
                        
                        if has_stream_callback:
                            self.logger.info("使用流式输出模式生成 AI 回复...")
                            test_message = deepseek_client.get_reply_for_session_stream(
                                weflow_base_url=weflow_base_url,
                                session=session,
                                on_thinking_chunk=thinking_callback,
                                on_content_chunk=content_callback,
                                on_reasoning_finished=reasoning_finished_callback,
                                default_system_prompt=default_system_prompt,
                                message_limit=message_limit,
                                thinking_mode=thinking_mode,
                                temperature=temperature
                            )
                        else:
                            test_message = deepseek_client.get_reply_for_session(
                                weflow_base_url=weflow_base_url,
                                session=session,
                                default_system_prompt=default_system_prompt,
                                message_limit=message_limit,
                                thinking_mode=thinking_mode,
                                temperature=temperature
                            )
                        
                        if not test_message:
                            self.logger.error("生成 AI 回复失败，中止回复流程")
                            return False
                else:
                    # 阿里云等其他提供商暂时不实现
                    self.logger.warning(f"未支持的 AI 提供商: {provider}，中止回复流程")
                    return False
            
            # self.logger.info(f"最终回复内容: {test_message}")

            # 4. 获取快捷键配置
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

            # 5. 执行根据状态确定的显示/隐藏次数（仅用于调整微信状态）
            for i in range(toggle_count):
                self.logger.info(f"执行第{i+1}次显示/隐藏微信窗口快捷键")
                if not self.press_shortcut(show_hide_shortcut):
                    self.logger.error(f"执行第{i+1}次显示/隐藏窗口快捷键失败")
                    return False
                time.sleep(0.1)

            # 6. 唤起微信到前台
            if not self._bring_wechat_to_front():
                self.logger.error("唤起微信失败")
                return False

            # 7. 再次检测状态，确认微信已唤起
            status_code, status_description = check_weixin_status()
            self.logger.info(f"唤起后微信状态: {status_description} (状态码: {status_code})")

            if status_code == 0:
                self.logger.error("微信未运行，停止后续所有操作")
                return False

            # 8. 获取其他快捷键配置
            switch_session_shortcut = self._get_shortcut('switch_session', 'Ctrl+2')
            search_shortcut = self._get_shortcut('search', 'Ctrl+F')
            select_shortcut = self._get_shortcut('select', 'Enter')
            paste_shortcut = self._get_shortcut('paste', 'Ctrl+V')
            send_shortcut = self._get_shortcut('send_message', 'Enter')

            self.logger.info(f"快捷键配置: 切换会话={switch_session_shortcut}, 搜索={search_shortcut}, "
                           f"选中={select_shortcut}, 粘贴={paste_shortcut}, 发送={send_shortcut}")

            # 9. 执行后续操作：切换会话
            if not self.press_shortcut(switch_session_shortcut):
                self.logger.error("执行切换会话快捷键失败")
                return False
            time.sleep(0.1)

            # 10. 搜索
            if not self.press_shortcut(search_shortcut):
                self.logger.error("执行搜索快捷键失败")
                return False
            time.sleep(0.1)

            # 11. 输入联系人备注
            if not self.type_text(session_contact_remark):
                self.logger.error("输入联系人备注失败")
                return False
            time.sleep(0.1)

            # 12. 选中搜索结果
            if not self.press_shortcut(select_shortcut):
                self.logger.error("执行选中快捷键失败")
                return False
            time.sleep(0.1)

            # 13. 粘贴准备好的回复消息
            self.logger.info(f"复制消息到剪贴板")
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
            import traceback
            self.logger.error(traceback.format_exc())
            return False