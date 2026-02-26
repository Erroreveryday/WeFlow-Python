import os
import time
import logging
import pyautogui
import subprocess
import win32gui
import win32con
import psutil

class KeyboardAutomation:
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        # 设置 pyautogui 的延迟，确保操作有足够时间响应
        pyautogui.PAUSE = 0.5
    
    def is_wechat_running(self):
        """检测是否有微信进程在运行（排除新启动的登录实例）"""
        for proc in psutil.process_iter(['name', 'pid']):
            if proc.info['name'] == 'WeiXin.exe' or proc.info['name'] == 'Weixin.exe':
                # 简单判断：微信进程内存占用>50MB 大概率是已登录的主进程（登录实例内存<50MB）
                try:
                    mem = proc.memory_info().rss / 1024 / 1024  # 转换为MB
                    if mem > 50:  # 降低阈值，50MB以上认为是已登录的主进程
                        return True, proc.info['pid']
                except:
                    continue
        return False, None

    def get_wechat_main_window_handle(self):
        """获取已登录的微信主窗口句柄（通过窗口标题和类名匹配）"""
        wechat_handle = None
        
        # 枚举所有窗口，筛选微信主窗口
        def callback(handle, extra):
            nonlocal wechat_handle
            try:
                class_name = win32gui.GetClassName(handle)
                window_title = win32gui.GetWindowText(handle)
                # 检查是否是微信窗口：标题包含"微信"且类名不是记事本或浏览器
                if "微信" in window_title and class_name not in ["Notepad", "Chrome_WidgetWin_1"]:
                    # 只要标题包含"微信"且窗口可见，就认为是主窗口
                    if win32gui.IsWindowVisible(handle):
                        wechat_handle = handle
            except:
                pass
            return True
        
        win32gui.EnumWindows(callback, None)
        return wechat_handle

    def open_wechat(self):
        """唤起微信程序"""
        try:
            # 1. 先检测是否有已登录的微信进程
            is_running, pid = self.is_wechat_running()
            if not is_running:
                # 如果微信没有运行，尝试启动微信
                open_command = self.config.get('WeChat', 'open_wechat', fallback='start wechat')
                self.logger.info(f"微信未运行，执行命令启动微信: {open_command}")
                
                # 使用 subprocess 执行命令并捕获输出
                result = subprocess.run(open_command, shell=True, capture_output=True, text=True)
                
                # 检查是否有错误输出
                if result.stderr and ("系统找不到文件" in result.stderr or "Windows 找不到文件" in result.stderr):
                    self.logger.error(f"系统找不到微信程序: {result.stderr}")
                    return False
                
                # 检查返回码
                if result.returncode != 0:
                    self.logger.error(f"执行命令失败，返回码: {result.returncode}")
                    return False
                
                # 等待微信启动
                time.sleep(5)
                
                # 执行一次隐藏/显示窗口的快捷键
                toggle_shortcut = self.config.get('WeChat', 'toggle_window_shortcut', fallback='ctrl+alt+w')
                self.press_shortcut(toggle_shortcut)
                
                # 再次检查是否识别到微信
                time.sleep(1)
                is_running, pid = self.is_wechat_running()
                if not is_running:
                    self.logger.error("启动微信后执行隐藏/显示快捷键仍未识别到微信程序！")
                    return False
                
                return True
            else:
                # 如果微信已运行，激活微信窗口
                self.logger.info("微信已运行，尝试激活窗口")
                
                # 2. 定位微信主窗口句柄
                handle = self.get_wechat_main_window_handle()
                if not handle:
                    # 微信可能在后台任务栏角标里，尝试执行显示/隐藏窗口快捷键
                    self.logger.info("未找到微信主窗口，尝试执行显示/隐藏窗口快捷键...")
                    toggle_shortcut = self.config.get('WeChat', 'toggle_window_shortcut', fallback='ctrl+alt+w')
                    self.press_shortcut(toggle_shortcut)
                    time.sleep(1)
                    # 再次尝试获取主窗口句柄
                    handle = self.get_wechat_main_window_handle()
                    if not handle:
                        self.logger.error("执行显示/隐藏窗口快捷键后仍未找到微信主窗口！")
                        return False
                
                # 3. 激活窗口（处理最小化/后台状态）
                # 先判断窗口是否最小化，若是则还原
                if win32gui.IsIconic(handle):
                    win32gui.ShowWindow(handle, win32con.SW_RESTORE)
                # 将窗口置顶并激活
                win32gui.SetForegroundWindow(handle)
                # 确保窗口激活（加短暂延迟）
                time.sleep(0.5)
                
                # 再次检查是否识别到微信
                handle = self.get_wechat_main_window_handle()
                if not handle:
                    # 再执行一次隐藏/显示窗口的快捷键
                    toggle_shortcut = self.config.get('WeChat', 'toggle_window_shortcut', fallback='ctrl+alt+w')
                    self.press_shortcut(toggle_shortcut)
                    time.sleep(0.5)
                    handle = self.get_wechat_main_window_handle()
                    if not handle:
                        self.logger.error("执行显示/隐藏窗口快捷键后未识别到微信程序！")
                        return False
                
                self.logger.info("已成功激活已登录的微信窗口！")
                return True
        except Exception as e:
            self.logger.error(f"唤起微信失败: {e}")
            return False
    
    def press_shortcut(self, shortcut):
        """按下快捷键组合"""
        try:
            # 解析快捷键，如 "ctrl+v" 分解为 ["ctrl", "v"]
            keys = shortcut.split('+')
            self.logger.info(f"按下快捷键: {shortcut}")
            
            # 按下组合键
            with pyautogui.hold(keys[:-1]):
                pyautogui.press(keys[-1])
            
            # 等待操作响应
            time.sleep(1)
            return True
        except Exception as e:
            self.logger.error(f"执行快捷键失败: {e}")
            return False
    
    def type_text(self, text):
        """输入文本（使用粘贴方式）"""
        try:
            self.logger.info(f"输入文本: {text}")
            # 使用粘贴方式输入文本
            pyperclip.copy(text)
            # 使用粘贴快捷键
            self.press_shortcut('ctrl+v')
            # 等待输入完成
            time.sleep(0.5)
            return True
        except Exception as e:
            self.logger.error(f"输入文本失败: {e}")
            return False
    
    def send_message(self, message, target_session):
        """完整的发送消息流程"""
        try:
            self.logger.info("开始执行微信消息发送流程")
            
            # 1. 唤起微信
            if not self.open_wechat():
                return False
            
            # 2. 搜索会话
            search_shortcut = self.config.get('WeChat', 'search_shortcut', fallback='ctrl+f')
            if not self.press_shortcut(search_shortcut):
                return False
            
            # 3. 输入会话名称（使用粘贴方式）
            if not self.type_text(target_session):
                return False
            
            # 4. 选中搜索结果
            select_shortcut = self.config.get('WeChat', 'select_shortcut', fallback='enter')
            if not self.press_shortcut(select_shortcut):
                return False
            
            # 5. 快速执行两次隐藏/显示窗口的快捷键
            toggle_shortcut = self.config.get('WeChat', 'toggle_window_shortcut', fallback='ctrl+alt+w')
            for i in range(2):
                if not self.press_shortcut(toggle_shortcut):
                    return False
                time.sleep(0.5)
            
            # 6. 粘贴消息
            # 先复制消息到剪贴板
            self.logger.info(f"复制消息到剪贴板: {message}")
            pyperclip.copy(message)
            # 等待剪贴板更新
            time.sleep(0.2)
            paste_shortcut = self.config.get('WeChat', 'paste_shortcut', fallback='ctrl+v')
            if not self.press_shortcut(paste_shortcut):
                return False
            
            # 7. 发送消息
            send_shortcut = self.config.get('WeChat', 'send_shortcut', fallback='ctrl+enter')
            if not self.press_shortcut(send_shortcut):
                return False
            
            self.logger.info("微信消息发送流程执行完成")
            return True
        except Exception as e:
            self.logger.error(f"发送消息失败: {e}")
            return False

# 导入 pyperclip 用于剪贴板操作
import pyperclip