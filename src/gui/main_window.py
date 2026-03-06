import sys
import os
import logging
from datetime import datetime

# 添加src目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTextEdit, QLabel, QStatusBar, QLineEdit, QTableWidget, QTableWidgetItem, QCheckBox, QDialog, QFormLayout, QComboBox, QGroupBox, QRadioButton
from PyQt5.QtCore import QThread, pyqtSignal, Qt, Q_ARG, QCoreApplication, QTimer
from PyQt5.QtGui import QFont, QKeyEvent, QKeySequence
from weflow.status_checker import test_api_health, check_weixin_status
from weflow.message_listener import MessageListenerThread
from weflow.keyboard_automation import KeyboardAutomation
from utils import load_config, save_config


class TestMessageThread(QThread):
    """执行测试消息的后台线程"""
    finished = pyqtSignal(bool, str)
    
    def __init__(self, keyboard_automation, session):
        super().__init__()
        self.keyboard_automation = keyboard_automation
        self.session = session
    
    def run(self):
        try:
            contact_remark = self.session.get('contact_remark', '')
            if not contact_remark:
                self.finished.emit(False, "会话备注为空")
                return
            
            success = self.keyboard_automation.execute_test_message(self.session)
            if success:
                self.finished.emit(True, "测试消息流程执行成功")
            else:
                self.finished.emit(False, "测试消息流程执行失败")
        except Exception as e:
            self.finished.emit(False, f"执行出错: {str(e)}")

# 自定义快捷键输入控件
class ShortcutLineEdit(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setPlaceholderText("点击此处设置快捷键")
        self.original_shortcut = ""
        self.recording = False
        self.current_shortcut_parts = []
        self.setStyleSheet("ShortcutLineEdit { background-color: #f0f0f0; }")
        self.clicked.connect(self.start_recording)
        # 安装全局事件过滤器到应用程序
        app = QApplication.instance()
        if app:
            app.installEventFilter(self)
    
    clicked = pyqtSignal()
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)
    
    def eventFilter(self, obj, event):
        # 在录制状态下，检测鼠标点击事件
        if self.recording and event.type() == event.MouseButtonPress:
            # 获取点击的控件
            clicked_widget = QApplication.widgetAt(event.globalPos())
            # 如果点击的不是当前控件，则停止录制
            if clicked_widget != self and not self.isAncestorOf(clicked_widget):
                logging.info("点击外部区域，停止录制快捷键")
                self.stop_recording(success=False)
                return True
        return super().eventFilter(obj, event)
    
    def start_recording(self):
        if not self.recording:
            self.recording = True
            self.original_shortcut = self.text()
            self.current_shortcut_parts = []
            self.setText("按下快捷键")
            self.setStyleSheet("ShortcutLineEdit { background-color: #fffacd; }")
            self.setFocus()
            self.grabKeyboard()
            print("开始录制快捷键...")
    
    def stop_recording(self, success=True):
        self.recording = False
        self.releaseKeyboard()
        self.current_shortcut_parts = []
        if not success:
            self.setText(self.original_shortcut)
        self.setStyleSheet("ShortcutLineEdit { background-color: #f0f0f0; }")
    
    def update_display(self):
        """实时更新显示当前按下的按键"""
        if self.current_shortcut_parts:
            display_text = "+".join(self.current_shortcut_parts)
            self.setText(display_text)
        else:
            self.setText("按下快捷键")
    
    def keyPressEvent(self, event):
        if not self.recording:
            super().keyPressEvent(event)
            return
        
        key = event.key()
        modifiers = event.modifiers()
        
        # 处理修饰键，实时显示
        if key in [Qt.Key_Control, Qt.Key_Alt, Qt.Key_Shift, Qt.Key_Meta]:
            # 清空之前的按键，重新构建
            self.current_shortcut_parts = []
            if modifiers & Qt.ControlModifier:
                self.current_shortcut_parts.append("Ctrl")
            if modifiers & Qt.AltModifier:
                self.current_shortcut_parts.append("Alt")
            if modifiers & Qt.ShiftModifier:
                self.current_shortcut_parts.append("Shift")
            self.update_display()
            return
        
        # 检查是否至少有一个修饰键
        if not (modifiers & (Qt.ControlModifier | Qt.AltModifier | Qt.ShiftModifier)):
            logging.warning("快捷键必须包含Ctrl、Alt或Shift键")
            self.stop_recording(success=False)
            return
        
        # 构建快捷键字符串
        shortcut_parts = []
        if modifiers & Qt.ControlModifier:
            shortcut_parts.append("Ctrl")
        if modifiers & Qt.AltModifier:
            shortcut_parts.append("Alt")
        if modifiers & Qt.ShiftModifier:
            shortcut_parts.append("Shift")
        
        # 获取按键名称
        key_name = ""
        if key >= Qt.Key_F1 and key <= Qt.Key_F35:
            key_name = f"F{key - Qt.Key_F1 + 1}"
        elif key == Qt.Key_Space:
            key_name = "Space"
        elif key == Qt.Key_Tab:
            key_name = "Tab"
        elif key == Qt.Key_Enter or key == Qt.Key_Return:
            key_name = "Enter"
        elif key == Qt.Key_Escape:
            key_name = "Esc"
        elif key == Qt.Key_Backspace:
            key_name = "Backspace"
        elif key == Qt.Key_Delete:
            key_name = "Delete"
        elif key == Qt.Key_Insert:
            key_name = "Insert"
        elif key == Qt.Key_Home:
            key_name = "Home"
        elif key == Qt.Key_End:
            key_name = "End"
        elif key == Qt.Key_PageUp:
            key_name = "PageUp"
        elif key == Qt.Key_PageDown:
            key_name = "PageDown"
        elif key == Qt.Key_Up:
            key_name = "Up"
        elif key == Qt.Key_Down:
            key_name = "Down"
        elif key == Qt.Key_Left:
            key_name = "Left"
        elif key == Qt.Key_Right:
            key_name = "Right"
        else:
            # 对于字母和数字，直接使用按键文本
            key_text = event.text()
            if key_text and key_text.isprintable() and len(key_text) == 1:
                if key_text.isalpha():
                    key_name = key_text.upper()
                else:
                    key_name = key_text
            else:
                # 使用Qt的按键名称
                key_name = QKeySequence(key).toString()
        
        if not key_name:
            logging.warning("无效的按键")
            self.stop_recording(success=False)
            return
        
        shortcut_parts.append(key_name)
        shortcut_str = "+".join(shortcut_parts)
        
        # 设置新的快捷键
        self.setText(shortcut_str)
        self.stop_recording(success=True)
        print(f"快捷键已设置为: {shortcut_str}")
    
    def keyReleaseEvent(self, event):
        if self.recording:
            key = event.key()
            # 当释放修饰键时，更新显示
            if key in [Qt.Key_Control, Qt.Key_Alt, Qt.Key_Shift, Qt.Key_Meta]:
                modifiers = event.modifiers()
                self.current_shortcut_parts = []
                if modifiers & Qt.ControlModifier:
                    self.current_shortcut_parts.append("Ctrl")
                if modifiers & Qt.AltModifier:
                    self.current_shortcut_parts.append("Alt")
                if modifiers & Qt.ShiftModifier:
                    self.current_shortcut_parts.append("Shift")
                self.update_display()
        super().keyReleaseEvent(event)
    
    def focusOutEvent(self, event):
        if self.recording:
            print("失去焦点，停止录制快捷键")
            self.stop_recording(success=False)
        super().focusOutEvent(event)

# 自定义日志处理器，将日志输出到GUI
class QTextEditLogger(logging.Handler):
    def __init__(self, text_edit):
        super().__init__()
        self.text_edit = text_edit
        self.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    
    def emit(self, record):
        msg = self.format(record)
        # 使用QMetaObject.invokeMethod确保在主线程中执行GUI操作
        from PyQt5.QtCore import QMetaObject, Qt
        # 只调用append方法，不调用ensureCursorVisible()
        QMetaObject.invokeMethod(self.text_edit, "append", Qt.QueuedConnection, 
                                 Q_ARG(str, msg))

# API状态检查线程
class ApiCheckThread(QThread):
    finished = pyqtSignal(bool, str)
    
    def run(self):
        try:
            status, message = test_api_health()
            self.finished.emit(status, message)
        except Exception as e:
            self.finished.emit(False, f"检查API时出错: {str(e)}")

# 微信状态检查线程
class WeixinCheckThread(QThread):
    finished = pyqtSignal(int, str)
    
    def run(self):
        try:
            status_code, status_description = check_weixin_status()
            self.finished.emit(status_code, status_description)
        except Exception as e:
            self.finished.emit(0, f"检查微信时出错: {str(e)}")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config = None
        self.message_listener = None
        self.keyboard_automation = None
        self.is_loading_sessions = False  # 标志：是否正在加载会话
        self.init_ui()
        self.setup_logger()
        self.show()
        
        # 使用定时器延迟加载配置和其他初始化操作
        QTimer.singleShot(100, self.delayed_initialization)
    
    def delayed_initialization(self):
        """延迟初始化：加载配置、加载会话、启动状态检查"""
        print("开始延迟初始化...")
        self.config = load_config()
        
        self.keyboard_automation = KeyboardAutomation(self.config)
        
        # 更新界面控件的值以匹配配置
        self.show_hide_shortcut.setText(self.config.get('wechat_shortcuts', {}).get('show_hide_window', 'Ctrl+Alt+W'))
        self.port_input.setText(str(self.config.get('weflow_api_port', 5031)))
        send_option = self.config.get('wechat_shortcuts', {}).get('send_message', 'Enter')
        if send_option == 'Enter':
            self.send_message_enter.setChecked(True)
        else:
            self.send_message_ctrl_enter.setChecked(True)
        # 加载发送消息后隐藏窗口配置
        hide_after_send = self.config.get('wechat_shortcuts', {}).get('hide_after_send', True)
        self.hide_after_send_checkbox.setChecked(hide_after_send)
        
        # 更新自动回复状态显示
        self.update_auto_reply_status()
        
        self.load_wechat_sessions()
        
        # 初始化状态检查定时器
        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self.auto_check_status)
        # 每5秒检查一次状态
        self.status_timer.start(5000)
        # 立即执行一次检查
        self.auto_check_status()
        
        # 延迟启动消息监听器，减少图形界面唤起时间
        QTimer.singleShot(500, self.start_message_listener)
        
        print("延迟初始化完成")
    
    def start_message_listener(self):
        """启动消息监听器"""
        try:
            self.message_listener = MessageListenerThread(check_interval=1)
            self.message_listener.new_message.connect(self.on_new_message)
            self.message_listener.start()
            logging.info("消息监听器已启动")
        except Exception as e:
            logging.error(f"启动消息监听器失败: {e}")
    
    def on_new_message(self, session: dict, message: dict):
        """处理新消息"""
        contact_remark = session.get('contact_remark', '未知')
        content = message.get('content', '')
        sender = message.get('senderUsername', '')
        create_time = message.get('createTime', 0)
        
        # 判断时间戳是秒级还是毫秒级
        if create_time > 10000000000:  # 毫秒级时间戳（大于 2286 年）
            timestamp = datetime.fromtimestamp(create_time / 1000).strftime('%Y-%m-%d %H:%M:%S')
        else:  # 秒级时间戳
            timestamp = datetime.fromtimestamp(create_time).strftime('%Y-%m-%d %H:%M:%S')
        
        logging.info(f"=== 新消息通知 ===")
        logging.info(f"会话: {contact_remark}")
        logging.info(f"发送者: {sender}")
        logging.info(f"时间: {timestamp}")
        logging.info(f"内容: {content}")
        logging.info(f"==================")
        
        # 检查自动回复配置
        auto_reply_config = self.config.get('auto_reply', {})
        reply_type = auto_reply_config.get('reply_type', 'fixed')
        
        if reply_type == 'fixed':
            fixed_text = auto_reply_config.get('fixed_text', '').strip()
            if not fixed_text:
                logging.warning("自动回复配置为固定文本，但文本内容为空，跳过执行")
                return
        
        # 执行测试消息流程
        self.execute_test_message_flow(session)
    
    def execute_test_message_flow(self, session: dict):
        """执行测试消息流程（在后台线程中执行）"""
        try:
            contact_remark = session.get('contact_remark', '')
            if not contact_remark:
                logging.warning("会话备注为空，无法执行测试消息流程")
                return
            
            if self.keyboard_automation:
                # 使用后台线程执行，避免阻塞UI
                self.test_message_thread = TestMessageThread(self.keyboard_automation, session)
                self.test_message_thread.finished.connect(self.on_test_message_finished)
                self.test_message_thread.start()
                logging.info("已启动后台线程执行测试消息流程")
            else:
                logging.error("键盘自动化对象未初始化")
        except Exception as e:
            logging.error(f"执行测试消息流程时出错: {e}")
    
    def on_test_message_finished(self, success: bool, message: str):
        """测试消息执行完成回调"""
        if success:
            logging.info(message)
            # 获取最新消息ID并更新到监听器，防止重复处理
            if self.message_listener:
                try:
                    from utils import load_config
                    config = load_config()
                    sessions = config.get('wechat_sessions', [])
                    for session in sessions:
                        if session.get('auto_reply', False):
                            talker = session.get('wechat_id', '')
                            if talker:
                                # 获取最新消息
                                import requests
                                port = config.get('weflow_api_port', 5031)
                                response = requests.get(
                                    f"http://127.0.0.1:{port}/api/v1/messages",
                                    params={'talker': talker, 'limit': 1},
                                    timeout=10
                                )
                                if response.status_code == 200:
                                    data = response.json()
                                    if data.get('success') and data.get('messages'):
                                        latest_msg = data['messages'][0]
                                        self.message_listener.update_processed_message(
                                            talker,
                                            latest_msg.get('localId', 0),
                                            latest_msg.get('createTime', 0)
                                        )
                                        logging.info(f"已更新监听器最新消息ID: {latest_msg.get('localId')}")
                except Exception as e:
                    logging.error(f"更新监听器消息记录失败: {e}")
    
    def load_wechat_sessions(self):
        """加载微信会话配置到表格"""
        # 先断开信号连接，避免重复触发
        try:
            self.sessions_table.itemChanged.disconnect(self.on_cell_changed)
        except:
            pass
        
        # 设置加载标志
        self.is_loading_sessions = True
        
        sessions = self.config.get('wechat_sessions', [])
        self.sessions_table.setRowCount(len(sessions))
        
        # 设置表格为可编辑
        self.sessions_table.setEditTriggers(QTableWidget.DoubleClicked | QTableWidget.EditKeyPressed)
        
        for i, session in enumerate(sessions):
            # 微信ID
            wechat_id_item = QTableWidgetItem(session.get('wechat_id', ''))
            self.sessions_table.setItem(i, 0, wechat_id_item)
            # 备注
            remark_item = QTableWidgetItem(session.get('contact_remark', ''))
            self.sessions_table.setItem(i, 1, remark_item)
            # 自动回复 - 居中显示
            auto_reply_widget = QWidget()
            auto_reply_layout = QHBoxLayout(auto_reply_widget)
            auto_reply_layout.setContentsMargins(0, 0, 0, 0)
            auto_reply_checkbox = QCheckBox()
            auto_reply_checkbox.setChecked(session.get('auto_reply', False))
            auto_reply_checkbox.stateChanged.connect(lambda state, row=i: self.update_auto_reply(row, state))
            auto_reply_layout.addWidget(auto_reply_checkbox, 0, Qt.AlignCenter)
            self.sessions_table.setCellWidget(i, 2, auto_reply_widget)
            # 操作按钮 - 仅保留删除按钮
            button_widget = QWidget()
            button_layout = QHBoxLayout(button_widget)
            button_layout.setContentsMargins(2, 2, 2, 2)
            button_layout.setAlignment(Qt.AlignCenter)
            
            # 删除按钮
            delete_button = QPushButton("删除")
            delete_button.setFixedSize(60, 20)
            delete_button.setStyleSheet("QPushButton { padding: 2px; font-size: 9px; color: red; }")
            delete_button.clicked.connect(lambda _, row=i: self.delete_wechat_session(row))
            
            button_layout.addWidget(delete_button)
            self.sessions_table.setCellWidget(i, 3, button_widget)
        
        # 连接单元格变化信号
        self.sessions_table.itemChanged.connect(self.on_cell_changed)
        
        # 为自动回复列和操作列禁用选中效果
        for row in range(self.sessions_table.rowCount()):
            # 为自动回复列（索引2）和操作列（索引3）的单元格设置标志，禁用选中
            for col in [2, 3]:
                item = QTableWidgetItem()
                item.setFlags(item.flags() & ~Qt.ItemIsSelectable)
                self.sessions_table.setItem(row, col, item)
        
        # 清除加载标志
        self.is_loading_sessions = False
    
    def showEvent(self, event):
        """窗口显示事件"""
        super().showEvent(event)
        # 窗口显示后连接屏幕切换信号
        if self.windowHandle():
            self.windowHandle().screenChanged.connect(self.on_screen_changed)
    
    def closeEvent(self, event):
        """窗口关闭事件"""
        # 停止消息监听器（非阻塞）
        if self.message_listener and self.message_listener.isRunning():
            logging.info("正在停止消息监听器...")
            self.message_listener.stop_non_blocking()
            logging.info("消息监听器已停止")
        
        # 停止状态检查定时器
        if hasattr(self, 'status_timer'):
            self.status_timer.stop()
        
        # 立即关闭窗口，不等待线程结束
        event.accept()
        super().closeEvent(event)
    
    def init_ui(self):
        self.setWindowTitle("WeFlow-Python")
        self.setGeometry(100, 100, 800, 600)
        # 设置最小宽度，避免元素拥挤
        self.setMinimumWidth(700)
        
        # 中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout(central_widget)
        
        # 日志输出区域
        log_layout = QVBoxLayout()
        log_label = QLabel("日志输出:")
        self.log_text_edit = QTextEdit()
        self.log_text_edit.setReadOnly(True)
        clear_log_button = QPushButton("清空日志")
        clear_log_button.clicked.connect(self.clear_log)
        
        log_layout.addWidget(log_label)
        log_layout.addWidget(self.log_text_edit)
        log_layout.addWidget(clear_log_button)
        
        # 微信配置区域（左右布局）
        wechat_config_layout = QHBoxLayout()
        
        # 左侧：微信会话配置
        sessions_group = QGroupBox("微信会话配置")
        wechat_sessions_layout = QVBoxLayout()
        
        # 会话表格
        self.sessions_table = QTableWidget()
        self.sessions_table.setColumnCount(4)
        self.sessions_table.setHorizontalHeaderLabels(["微信ID", "联系人备注", "自动回复", "操作"])
        # 调整列宽，操作列只需要足够容纳删除按钮
        self.sessions_table.setColumnWidth(0, 180)  # 微信ID
        self.sessions_table.setColumnWidth(1, 120)  # 联系人备注
        self.sessions_table.setColumnWidth(2, 80)   # 自动回复
        self.sessions_table.setColumnWidth(3, 80)   # 操作（只需要容纳删除按钮）
        # 设置表格水平拉伸策略，确保表格填满控件
        from PyQt5.QtWidgets import QHeaderView
        self.sessions_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.sessions_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.sessions_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)
        self.sessions_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Fixed)
        
        # 操作按钮
        sessions_buttons_layout = QHBoxLayout()
        add_session_button = QPushButton("添加会话")
        add_session_button.clicked.connect(self.add_wechat_session)
        
        sessions_buttons_layout.addWidget(add_session_button)
        
        wechat_sessions_layout.addWidget(self.sessions_table)
        wechat_sessions_layout.addLayout(sessions_buttons_layout)
        sessions_group.setLayout(wechat_sessions_layout)
        
        # 右侧：配置区域
        wechat_shortcuts_layout = QVBoxLayout()
        
        # 微信快捷键配置
        shortcuts_group = QGroupBox("微信快捷键配置")
        shortcuts_content_layout = QVBoxLayout()
        
        # 显示/隐藏微信窗口
        show_hide_layout = QHBoxLayout()
        show_hide_label = QLabel("显示/隐藏微信窗口:")
        self.show_hide_shortcut = ShortcutLineEdit()
        # 使用默认值，稍后会在延迟初始化时更新
        self.show_hide_shortcut.setText('Ctrl+Alt+W')
        self.show_hide_shortcut.textChanged.connect(self.save_shortcuts_config)
        show_hide_layout.addWidget(show_hide_label)
        show_hide_layout.addWidget(self.show_hide_shortcut)
        
        # 发送消息
        send_message_layout = QHBoxLayout()
        send_message_label = QLabel("发送消息:")
        
        # 创建单选按钮组
        self.send_message_enter = QRadioButton("Enter")
        self.send_message_ctrl_enter = QRadioButton("Ctrl+Enter")
        
        # 设置默认值
        self.send_message_enter.setChecked(True)
        
        # 连接信号
        self.send_message_enter.toggled.connect(self.save_shortcuts_config)
        self.send_message_ctrl_enter.toggled.connect(self.save_shortcuts_config)
        
        send_message_layout.addWidget(send_message_label)
        send_message_layout.addWidget(self.send_message_enter)
        send_message_layout.addWidget(self.send_message_ctrl_enter)
        send_message_layout.addStretch()
        
        # 发送消息后隐藏微信窗口
        hide_after_send_layout = QHBoxLayout()
        hide_after_send_label = QLabel("发送消息后隐藏微信窗口:")
        self.hide_after_send_checkbox = QCheckBox()
        self.hide_after_send_checkbox.setChecked(True)  # 默认为启用状态
        self.hide_after_send_checkbox.stateChanged.connect(self.save_shortcuts_config)
        hide_after_send_layout.addWidget(hide_after_send_label)
        hide_after_send_layout.addWidget(self.hide_after_send_checkbox)
        
        # 提示文本
        tip_label = QLabel("注意：需与微信端的设置保持一致\n详见：微信->设置->快捷键")
        tip_label.setStyleSheet("QLabel { font-size: 12px; color: #666; }")
        
        shortcuts_content_layout.addLayout(show_hide_layout)
        shortcuts_content_layout.addLayout(send_message_layout)
        shortcuts_content_layout.addLayout(hide_after_send_layout)
        shortcuts_content_layout.addWidget(tip_label)
        shortcuts_group.setLayout(shortcuts_content_layout)
        
        # API端口号配置
        api_group = QGroupBox("WeFlow API 配置")
        api_content_layout = QVBoxLayout()
        
        config_layout = QHBoxLayout()
        config_label = QLabel("端口号:")
        # 使用默认值，稍后会在延迟初始化时更新
        self.port_input = QLineEdit('5031')
        # 为端口输入框添加输入验证和自动保存
        self.port_input.textChanged.connect(self.save_api_port_config)
        # 设置输入验证器，只允许输入数字
        from PyQt5.QtGui import QIntValidator
        validator = QIntValidator(1024, 65535, self)
        self.port_input.setValidator(validator)
        
        config_layout.addWidget(config_label)
        config_layout.addWidget(self.port_input)
        
        # API状态检查
        api_layout = QHBoxLayout()
        api_label = QLabel("API 状态")
        self.api_status_label = QLabel("未检查")
        self.api_status_label.setStyleSheet("QLabel { border: 1px solid #ccc; padding: 5px; margin: 5px; }")
        
        api_layout.addWidget(api_label)
        api_layout.addWidget(self.api_status_label, 1)  # 添加拉伸因子1
        
        # 微信状态检查
        weixin_layout = QHBoxLayout()
        weixin_label = QLabel("微信状态")
        self.weixin_status_label = QLabel("未检查")
        self.weixin_status_label.setStyleSheet("QLabel { border: 1px solid #ccc; padding: 5px; margin: 5px; }")
        
        weixin_layout.addWidget(weixin_label)
        weixin_layout.addWidget(self.weixin_status_label, 1)  # 添加拉伸因子1
        
        api_content_layout.addLayout(config_layout)
        api_content_layout.addLayout(api_layout)
        api_content_layout.addLayout(weixin_layout)
        api_group.setLayout(api_content_layout)
        
        # 自动回复配置
        auto_reply_group = QGroupBox("自动回复配置")
        auto_reply_layout = QVBoxLayout()
        
        self.auto_reply_config_button = QPushButton("点击配置回复内容")
        self.auto_reply_config_button.clicked.connect(self.open_auto_reply_config)
        auto_reply_layout.addWidget(self.auto_reply_config_button)
        
        # 显示当前自动回复类型
        self.auto_reply_status_label = QLabel("当前配置: 未设置")
        self.auto_reply_status_label.setStyleSheet("QLabel { font-size: 12px; color: #666; }")
        auto_reply_layout.addWidget(self.auto_reply_status_label)
        
        auto_reply_group.setLayout(auto_reply_layout)
        
        # 添加到右侧布局（从上到下：微信快捷键配置、WeFlow API 配置、自动回复配置）
        wechat_shortcuts_layout.addWidget(shortcuts_group)
        wechat_shortcuts_layout.addSpacing(10)
        wechat_shortcuts_layout.addWidget(api_group)
        wechat_shortcuts_layout.addSpacing(10)
        wechat_shortcuts_layout.addWidget(auto_reply_group)
        
        # 添加到左右布局
        wechat_config_layout.addWidget(sessions_group, 2)  # 左边占2份
        wechat_config_layout.addLayout(wechat_shortcuts_layout, 1)  # 右边占1份
        
        # 添加到主布局
        main_layout.addLayout(wechat_config_layout)
        main_layout.addLayout(log_layout)
        
        # 状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪")
    
    def setup_logger(self):
        # 配置日志
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)
        
        # 清除现有处理器
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        
        # 添加GUI日志处理器
        gui_handler = QTextEditLogger(self.log_text_edit)
        logger.addHandler(gui_handler)
        
        # 添加控制台日志处理器
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(console_handler)
    
    def auto_check_status(self):
        """自动检查API和微信状态"""
        # 检查API状态
        self.api_thread = ApiCheckThread()
        self.api_thread.finished.connect(self.on_api_check_finished)
        self.api_thread.start()
        
        # 检查微信状态
        self.weixin_thread = WeixinCheckThread()
        self.weixin_thread.finished.connect(self.on_weixin_check_finished)
        self.weixin_thread.start()
    
    def check_api_status(self):
        self.status_bar.showMessage("正在检查API状态...")
        self.api_thread = ApiCheckThread()
        self.api_thread.finished.connect(self.on_api_check_finished)
        self.api_thread.start()
    
    def on_api_check_finished(self, status, message):
        if status:
            self.api_status_label.setText(f"正常: {message}")
            self.api_status_label.setStyleSheet("QLabel { border: 1px solid #ccc; padding: 5px; margin: 5px; background-color: #d4edda; color: #155724; }")
        else:
            # 只显示基本的异常信息，避免界面变形
            if "ConnectionError" in message or "连接" in message:
                display_message = "API连接失败"
            elif "404" in message:
                display_message = "API路径不存在"
            elif "500" in message:
                display_message = "API服务器错误"
            else:
                display_message = "API状态异常"
            self.api_status_label.setText(f"异常: {display_message}")
            self.api_status_label.setStyleSheet("QLabel { border: 1px solid #ccc; padding: 5px; margin: 5px; background-color: #f8d7da; color: #721c24; }")
        self.status_bar.showMessage("API状态检查完成")
    
    def check_weixin_status(self):
        self.status_bar.showMessage("正在检查微信状态...")
        self.weixin_thread = WeixinCheckThread()
        self.weixin_thread.finished.connect(self.on_weixin_check_finished)
        self.weixin_thread.start()
    
    def on_weixin_check_finished(self, status_code, status_description):
        self.weixin_status_label.setText(status_description)
        
        # 根据状态设置不同的样式
        if status_code == 0:
            # 微信未运行
            self.weixin_status_label.setStyleSheet("QLabel { border: 1px solid #ccc; padding: 5px; margin: 5px; background-color: #f8d7da; color: #721c24; }")
        elif status_code == 1:
            # 微信后台运行
            self.weixin_status_label.setStyleSheet("QLabel { border: 1px solid #ccc; padding: 5px; margin: 5px; background-color: #fff3cd; color: #856404; }")
        elif status_code == 2:
            # 微信窗口打开但被覆盖
            self.weixin_status_label.setStyleSheet("QLabel { border: 1px solid #ccc; padding: 5px; margin: 5px; background-color: #d1ecf1; color: #0c5460; }")
        elif status_code == 3:
            # 微信窗口是当前活动窗口
            self.weixin_status_label.setStyleSheet("QLabel { border: 1px solid #ccc; padding: 5px; margin: 5px; background-color: #d4edda; color: #155724; }")
        
        self.status_bar.showMessage("微信状态检查完成")
    
    def clear_log(self):
        self.log_text_edit.clear()
        logging.info("日志已清空")
    
    def on_screen_changed(self, screen):
        """处理屏幕切换事件"""
        # 当窗口从一个屏幕移动到另一个屏幕时，重新调整布局
        # 这里可以根据需要添加更多的适配逻辑
        logging.info(f"窗口已切换到屏幕: {screen.name() if screen else '未知'}")
        # 重新布局以适应新屏幕的DPI
        self.resize(self.width(), self.height())
        self.updateGeometry()
    
    def save_config(self):
        """保存配置"""
        try:
            # 保存API端口（如果输入有效）
            try:
                port = int(self.port_input.text())
                self.config['weflow_api_port'] = port
                port_saved = True
            except ValueError:
                port_saved = False
                logging.warning("API端口号输入无效，将保持原有配置")
            
            # 保存微信快捷键配置
            if 'wechat_shortcuts' not in self.config:
                self.config['wechat_shortcuts'] = {}
            self.config['wechat_shortcuts']['show_hide_window'] = self.show_hide_shortcut.text()
            # 从单选按钮获取发送消息选项
            send_option = 'Enter' if self.send_message_enter.isChecked() else 'Ctrl+Enter'
            self.config['wechat_shortcuts']['send_message'] = send_option
            # 保存发送消息后隐藏窗口配置
            self.config['wechat_shortcuts']['hide_after_send'] = self.hide_after_send_checkbox.isChecked()
            
            success, message = save_config(self.config)
            
            if success:
                # 更新状态条消息
                if port_saved:
                    self.status_bar.showMessage(f"配置保存成功，API端口号: {port}")
                    logging.info(f"配置保存成功，API端口号: {port}")
                else:
                    self.status_bar.showMessage("快捷键配置保存成功，API端口号输入无效")
                print(f"微信快捷键配置已保存: 显示/隐藏={self.show_hide_shortcut.text()}, 发送消息={send_option}")
            else:
                self.status_bar.showMessage(f"配置保存失败: {message}")
                logging.error(f"配置保存失败: {message}")
        except Exception as e:
            self.status_bar.showMessage(f"配置保存失败: {str(e)}")
            logging.error(f"配置保存失败: {str(e)}")
    
    def save_shortcuts_config(self):
        """保存快捷键配置"""
        try:
            # 保存微信快捷键配置
            if 'wechat_shortcuts' not in self.config:
                self.config['wechat_shortcuts'] = {}
            self.config['wechat_shortcuts']['show_hide_window'] = self.show_hide_shortcut.text()
            # 从单选按钮获取发送消息选项
            send_option = 'Enter' if self.send_message_enter.isChecked() else 'Ctrl+Enter'
            self.config['wechat_shortcuts']['send_message'] = send_option
            # 保存发送消息后隐藏窗口配置
            self.config['wechat_shortcuts']['hide_after_send'] = self.hide_after_send_checkbox.isChecked()
            
            # 确保所有快捷键配置项存在
            default_shortcuts = {
                'show_hide_window': 'Ctrl+Alt+W',
                'send_message': 'Enter',
                'hide_after_send': True,
                'switch_session': 'Ctrl+2',
                'search': 'Ctrl+F',
                'select': 'Enter',
                'paste': 'Ctrl+V'
            }
            for key, default_value in default_shortcuts.items():
                if key not in self.config['wechat_shortcuts']:
                    self.config['wechat_shortcuts'][key] = default_value
            
            success, message = save_config(self.config)
            
            if success:
                print(f"微信快捷键配置已保存: 显示/隐藏={self.show_hide_shortcut.text()}, 发送消息={send_option}")
                # 更新 keyboard_automation 的配置
                if self.keyboard_automation:
                    self.keyboard_automation.config = self.config
            else:
                print(f"快捷键配置保存失败: {message}")
        except Exception as e:
            print(f"保存快捷键配置失败: {str(e)}")
    
    def save_api_port_config(self):
        """保存API端口配置"""
        try:
            port_text = self.port_input.text()
            if port_text:
                port = int(port_text)
                # 验证端口号范围
                if 1024 <= port <= 65535:
                    self.config['weflow_api_port'] = port
                    success, message = save_config(self.config)
                    if success:
                        logging.info(f"API端口配置已保存: {port}")
                        # 重新加载监听器配置，确保使用新的端口
                        if self.message_listener:
                            self.message_listener.reload_config()
                            logging.info("监听器配置已重新加载，使用新的API端口")
                    else:
                        logging.error(f"API端口配置保存失败: {message}")
                else:
                    logging.warning(f"端口号 {port} 超出范围 (1024-65535)")
        except ValueError:
            # 输入不是有效的数字，忽略保存
            pass
    
    def add_wechat_session(self):
        """添加微信会话"""
        # 检查最新的会话配置是否为空
        sessions = self.config.get('wechat_sessions', [])
        if sessions:
            last_session = sessions[-1]
            if not last_session.get('wechat_id', '').strip():
                self.status_bar.showMessage("最新的会话配置为空，不能添加新会话")
                logging.error("最新的会话配置为空，不能添加新会话")
                return
        
        # 创建新会话数据
        new_session = {
            'wechat_id': '',
            'contact_remark': '',
            'auto_reply': False,
            'custom_prompt': False,
            'prompt_settings': {
                '对方身份': '',
                '语气态度': '',
                '其他': ''
            }
        }
        
        # 添加到配置
        if 'wechat_sessions' not in self.config:
            self.config['wechat_sessions'] = []
        self.config['wechat_sessions'].append(new_session)
        
        # 保存配置
        success, message = save_config(self.config)
        if success:
            self.status_bar.showMessage("会话添加成功")
            logging.info("会话添加成功")
            self.load_wechat_sessions()
            # 为新添加的行禁用自动回复列和操作列的选中效果
            row = self.sessions_table.rowCount() - 1
            for col in [2, 3]:
                item = QTableWidgetItem()
                item.setFlags(item.flags() & ~Qt.ItemIsSelectable)
                self.sessions_table.setItem(row, col, item)
            # 重新加载监听器配置
            if self.message_listener:
                self.message_listener.reload_config()
                logging.info("监听器配置已重新加载")
        else:
            self.status_bar.showMessage(f"会话添加失败: {message}")
            logging.error(f"会话添加失败: {message}")
    
    def edit_wechat_session(self, row=None):
        """编辑微信会话"""
        if row is None:
            selected_rows = self.sessions_table.selectionModel().selectedRows()
            if not selected_rows:
                self.status_bar.showMessage("请先选择要编辑的会话")
                return
            row = selected_rows[0].row()
        
        sessions = self.config.get('wechat_sessions', [])
        if 0 <= row < len(sessions):
            dialog = SessionEditDialog(self, sessions[row])
            if dialog.exec_() == QDialog.Accepted:
                session_data = dialog.get_session_data()
                sessions[row] = session_data
                success, message = save_config(self.config)
                if success:
                    self.status_bar.showMessage("会话编辑成功")
                    logging.info("会话编辑成功")
                    self.load_wechat_sessions()
                else:
                    self.status_bar.showMessage(f"会话编辑失败: {message}")
                    logging.error(f"会话编辑失败: {message}")
    
    def on_cell_changed(self, item):
        """处理单元格变化事件"""
        # 如果正在加载会话，不处理
        if self.is_loading_sessions:
            return
        
        row = item.row()
        column = item.column()
        value = item.text()
        
        sessions = self.config.get('wechat_sessions', [])
        if 0 <= row < len(sessions):
            if column == 0:
                # 微信ID数据校验
                if value:
                    if len(value) > 20:
                        self.status_bar.showMessage("微信ID长度不能超过20字符")
                        logging.error("微信ID长度不能超过20字符")
                        # 恢复原来的值
                        original_value = sessions[row].get('wechat_id', '')
                        item.setText(original_value)
                        return
                    if not (value.startswith('wxid_') or value.endswith('@chatroom')):
                        self.status_bar.showMessage("微信ID必须以'wxid_'开头或'@chatroom'结尾")
                        logging.error("微信ID必须以'wxid_'开头或'@chatroom'结尾")
                        # 恢复原来的值
                        original_value = sessions[row].get('wechat_id', '')
                        item.setText(original_value)
                        return
                sessions[row]['wechat_id'] = value
            elif column == 1:
                # 联系人备注长度限制
                if len(value) > 64:
                    self.status_bar.showMessage("联系人备注长度不能超过64字符")
                    logging.error("联系人备注长度不能超过64字符")
                    # 恢复原来的值
                    original_value = sessions[row].get('contact_remark', '')
                    item.setText(original_value)
                    return
                sessions[row]['contact_remark'] = value
            
            success, message = save_config(self.config)
            if success:
                logging.info(f"会话配置已更新")
                # 重新加载监听器配置
                if self.message_listener:
                    self.message_listener.reload_config()
                    logging.info("监听器配置已重新加载")
            else:
                logging.error(f"保存配置失败: {message}")
    
    def update_auto_reply(self, row, state):
        """更新自动回复状态"""
        sessions = self.config.get('wechat_sessions', [])
        if 0 <= row < len(sessions):
            # 实现互斥逻辑：如果当前要开启，则关闭所有其他的
            if state == Qt.Checked:
                for i in range(len(sessions)):
                    if i != row:
                        sessions[i]['auto_reply'] = False
            # 设置当前行的状态
            sessions[row]['auto_reply'] = (state == Qt.Checked)
            # 保存配置
            success, message = save_config(self.config)
            if success:
                logging.info(f"自动回复状态已更新")
                # 重新加载会话列表以更新UI
                self.load_wechat_sessions()
                # 重新加载监听器配置
                if self.message_listener:
                    self.message_listener.reload_config()
                    logging.info("监听器配置已重新加载")
            else:
                logging.error(f"保存配置失败: {message}")
    
    def edit_prompt_settings(self, row):
        """编辑提示词设置"""
        sessions = self.config.get('wechat_sessions', [])
        if 0 <= row < len(sessions):
            dialog = SessionEditDialog(self, sessions[row])
            if dialog.exec_() == QDialog.Accepted:
                session_data = dialog.get_session_data()
                sessions[row] = session_data
                success, message = save_config(self.config)
                if success:
                    self.status_bar.showMessage("提示词设置编辑成功")
                    logging.info("提示词设置编辑成功")
                    self.load_wechat_sessions()
                else:
                    self.status_bar.showMessage(f"提示词设置编辑失败: {message}")
                    logging.error(f"提示词设置编辑失败: {message}")
    
    def delete_wechat_session(self, row=None):
        """删除微信会话"""
        if row is None:
            selected_rows = self.sessions_table.selectionModel().selectedRows()
            if not selected_rows:
                self.status_bar.showMessage("请先选择要删除的会话")
                return
            row = selected_rows[0].row()
        
        sessions = self.config.get('wechat_sessions', [])
        if 0 <= row < len(sessions):
            sessions.pop(row)
            success, message = save_config(self.config)
            if success:
                self.status_bar.showMessage("会话删除成功")
                logging.info("会话删除成功")
                self.load_wechat_sessions()
                # 重新加载监听器配置
                if self.message_listener:
                    self.message_listener.reload_config()
                    logging.info("监听器配置已重新加载")
            else:
                self.status_bar.showMessage(f"会话删除失败: {message}")
                logging.error(f"会话删除失败: {message}")
    
    def open_auto_reply_config(self):
        """打开自动回复配置对话框"""
        # 获取当前自动回复配置
        auto_reply_config = self.config.get('auto_reply', {})
        
        # 打开配置对话框
        dialog = AutoReplyConfigDialog(self, auto_reply_config)
        if dialog.exec_() == QDialog.Accepted:
            # 保存配置
            new_config = dialog.get_auto_reply_config()
            self.config['auto_reply'] = new_config
            
            success, message = save_config(self.config)
            if success:
                self.status_bar.showMessage("自动回复配置保存成功")
                logging.info("自动回复配置保存成功")
                # 更新状态显示
                self.update_auto_reply_status()
                # 重新加载监听器配置
                if self.message_listener:
                    self.message_listener.reload_config()
                    logging.info("监听器配置已重新加载")
            else:
                self.status_bar.showMessage(f"自动回复配置保存失败: {message}")
                logging.error(f"自动回复配置保存失败: {message}")
    
    def update_auto_reply_status(self):
        """更新自动回复状态显示"""
        auto_reply_config = self.config.get('auto_reply', {})
        reply_type = auto_reply_config.get('reply_type', 'fixed')
        
        if reply_type == 'fixed':
            status_text = "当前配置: 回复固定文本"
        else:
            provider = auto_reply_config.get('ai_config', {}).get('provider', 'aliyun')
            if provider == 'aliyun':
                status_text = "当前配置: AI大模型 (阿里云)"
            else:
                status_text = "当前配置: AI大模型 (DeepSeek)"
        
        self.auto_reply_status_label.setText(status_text)

class SessionEditDialog(QDialog):
    """提示词编辑对话框"""
    def __init__(self, parent, session_data=None):
        super().__init__(parent)
        self.session_data = session_data or {
            'wechat_id': '',
            'contact_remark': '',
            'auto_reply': False,
            'custom_prompt': True,
            'prompt_settings': {
                '对方身份': '',
                '语气态度': '',
                '其他': ''
            }
        }
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("编辑提示词")
        self.setGeometry(200, 200, 400, 200)
        
        layout = QVBoxLayout()
        
        # 提示词设置
        form_layout = QFormLayout()
        
        prompt_settings = self.session_data.get('prompt_settings', {})
        self.identity_input = QLineEdit(prompt_settings.get('对方身份', ''))
        form_layout.addRow("对方身份:", self.identity_input)
        
        self.tone_input = QLineEdit(prompt_settings.get('语气态度', ''))
        form_layout.addRow("语气态度:", self.tone_input)
        
        self.other_input = QLineEdit(prompt_settings.get('其他', ''))
        form_layout.addRow("其他:", self.other_input)
        
        layout.addLayout(form_layout)
        
        # 按钮布局
        button_layout = QHBoxLayout()
        save_button = QPushButton("保存")
        save_button.clicked.connect(self.accept)
        cancel_button = QPushButton("取消")
        cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(save_button)
        button_layout.addWidget(cancel_button)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def get_session_data(self):
        """获取会话数据"""
        # 保留原有数据，只更新提示词设置
        session_data = self.session_data.copy()
        session_data['custom_prompt'] = True
        session_data['prompt_settings'] = {
            '对方身份': self.identity_input.text(),
            '语气态度': self.tone_input.text(),
            '其他': self.other_input.text()
        }
        return session_data


class AutoReplyConfigDialog(QDialog):
    """自动回复配置对话框"""
    def __init__(self, parent, auto_reply_config=None):
        super().__init__(parent)
        self.auto_reply_config = auto_reply_config or {
            'reply_type': 'fixed',  # fixed 或 ai
            'fixed_text': '',
            'ai_config': {
                'provider': 'aliyun',  # aliyun 或 deepseek
                'aliyun': {
                    'api_key': '',
                    'model': 'qwen-turbo',
                    'system_prompt': '你模拟我与对方聊天。'
                },
                'deepseek': {
                    'api_key': '',
                    'model': 'deepseek-chat',
                    'system_prompt': '你模拟我与对方聊天。'
                }
            }
        }
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("自动回复配置")
        self.setGeometry(200, 200, 450, 350)
        
        layout = QVBoxLayout()
        
        # 自动回复类型选择
        type_group = QGroupBox("自动回复类型")
        type_layout = QVBoxLayout()
        
        self.fixed_reply_radio = QRadioButton("回复固定文本")
        self.ai_reply_radio = QRadioButton("调用AI大模型")
        
        # 设置默认选项
        if self.auto_reply_config.get('reply_type') == 'ai':
            self.ai_reply_radio.setChecked(True)
        else:
            self.fixed_reply_radio.setChecked(True)
        
        # 连接信号
        self.fixed_reply_radio.toggled.connect(self.on_reply_type_changed)
        self.ai_reply_radio.toggled.connect(self.on_reply_type_changed)
        
        type_layout.addWidget(self.fixed_reply_radio)
        type_layout.addWidget(self.ai_reply_radio)
        type_group.setLayout(type_layout)
        layout.addWidget(type_group)
        
        # 回复固定文本设置
        self.fixed_text_group = QGroupBox("回复固定文本")
        fixed_text_layout = QVBoxLayout()
        
        self.fixed_text_input = QTextEdit(self.auto_reply_config.get('fixed_text', ''))
        self.fixed_text_input.setPlaceholderText("请输入固定回复文本")
        fixed_text_layout.addWidget(self.fixed_text_input)
        
        self.fixed_text_group.setLayout(fixed_text_layout)
        layout.addWidget(self.fixed_text_group)
        
        # AI大模型设置
        self.ai_config_group = QGroupBox("AI大模型配置")
        ai_config_layout = QVBoxLayout()
        
        # AI提供商选择
        provider_layout = QHBoxLayout()
        provider_label = QLabel("AI提供商:")
        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["阿里云", "DeepSeek"])
        
        # 设置默认选项
        provider = self.auto_reply_config.get('ai_config', {}).get('provider', 'aliyun')
        if provider == 'deepseek':
            self.provider_combo.setCurrentIndex(1)
        else:
            self.provider_combo.setCurrentIndex(0)
        
        self.provider_combo.currentIndexChanged.connect(self.on_provider_changed)
        provider_layout.addWidget(provider_label)
        provider_layout.addWidget(self.provider_combo)
        ai_config_layout.addLayout(provider_layout)
        
        # 服务商配置横向布局
        providers_layout = QHBoxLayout()
        
        # 阿里云配置
        self.aliyun_group = QGroupBox("阿里云配置")
        aliyun_layout = QFormLayout()
        
        aliyun_config = self.auto_reply_config.get('ai_config', {}).get('aliyun', {})
        self.aliyun_api_key = QLineEdit(aliyun_config.get('api_key', ''))
        self.aliyun_api_key.setPlaceholderText("请输入阿里云API密钥")
        aliyun_layout.addRow("API密钥:", self.aliyun_api_key)
        
        self.aliyun_model = QComboBox()
        self.aliyun_model.addItems(["qwen-turbo", "qwen-plus", "qwen-max"])
        aliyun_model_value = aliyun_config.get('model', 'qwen-turbo')
        if aliyun_model_value in ["qwen-turbo", "qwen-plus", "qwen-max"]:
            self.aliyun_model.setCurrentText(aliyun_model_value)
        aliyun_layout.addRow("选择模型:", self.aliyun_model)
        
        self.aliyun_system_prompt = QTextEdit(aliyun_config.get('system_prompt', '你模拟我与对方聊天。'))
        self.aliyun_system_prompt.setPlaceholderText("请输入系统提示词")
        self.aliyun_system_prompt.setMinimumHeight(80)
        aliyun_layout.addRow("系统提示词:", self.aliyun_system_prompt)
        
        self.aliyun_group.setLayout(aliyun_layout)
        self.aliyun_group.setMinimumWidth(300)  # 增加最小宽度
        providers_layout.addWidget(self.aliyun_group, 1)  # 添加拉伸因子
        
        # 添加间距
        providers_layout.addSpacing(10)
        
        # DeepSeek配置
        self.deepseek_group = QGroupBox("DeepSeek配置")
        deepseek_layout = QFormLayout()
        
        deepseek_config = self.auto_reply_config.get('ai_config', {}).get('deepseek', {})
        self.deepseek_api_key = QLineEdit(deepseek_config.get('api_key', ''))
        self.deepseek_api_key.setPlaceholderText("请输入DeepSeek API密钥")
        deepseek_layout.addRow("API密钥:", self.deepseek_api_key)
        
        self.deepseek_model = QComboBox()
        self.deepseek_model.addItems(["deepseek-chat", "deepseek-reasoner"])
        deepseek_model_value = deepseek_config.get('model', 'deepseek-chat')
        if deepseek_model_value in ["deepseek-chat", "deepseek-reasoner"]:
            self.deepseek_model.setCurrentText(deepseek_model_value)
        deepseek_layout.addRow("选择模型:", self.deepseek_model)
        
        self.deepseek_system_prompt = QTextEdit(deepseek_config.get('system_prompt', '你模拟我与对方聊天。'))
        self.deepseek_system_prompt.setPlaceholderText("请输入系统提示词")
        self.deepseek_system_prompt.setMinimumHeight(80)
        deepseek_layout.addRow("系统提示词:", self.deepseek_system_prompt)
        
        self.deepseek_group.setLayout(deepseek_layout)
        self.deepseek_group.setMinimumWidth(300)  # 增加最小宽度
        providers_layout.addWidget(self.deepseek_group, 1)  # 添加拉伸因子
        
        ai_config_layout.addLayout(providers_layout)
        
        self.ai_config_group.setLayout(ai_config_layout)
        layout.addWidget(self.ai_config_group)
        
        # 按钮布局
        button_layout = QHBoxLayout()
        save_button = QPushButton("保存")
        save_button.clicked.connect(self.accept)
        cancel_button = QPushButton("取消")
        cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(save_button)
        button_layout.addWidget(cancel_button)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
        
        # 初始状态更新
        self.on_reply_type_changed()
        self.on_provider_changed()
    
    def on_reply_type_changed(self):
        """处理回复类型变化"""
        if self.fixed_reply_radio.isChecked():
            self.fixed_text_group.setEnabled(True)
            self.ai_config_group.setEnabled(False)
        else:
            self.fixed_text_group.setEnabled(False)
            self.ai_config_group.setEnabled(True)
    
    def on_provider_changed(self):
        """处理AI提供商变化"""
        if self.provider_combo.currentIndex() == 0:  # 阿里云
            self.aliyun_group.setEnabled(True)
            self.deepseek_group.setEnabled(False)
        else:  # DeepSeek
            self.aliyun_group.setEnabled(False)
            self.deepseek_group.setEnabled(True)
    
    def get_auto_reply_config(self):
        """获取自动回复配置"""
        config = self.auto_reply_config.copy()
        
        # 保存回复类型
        if self.ai_reply_radio.isChecked():
            config['reply_type'] = 'ai'
        else:
            config['reply_type'] = 'fixed'
        
        # 保存回复固定文本
        config['fixed_text'] = self.fixed_text_input.toPlainText()
        
        # 保存AI配置
        config['ai_config'] = {
            'provider': 'aliyun' if self.provider_combo.currentIndex() == 0 else 'deepseek',
            'aliyun': {
                'api_key': self.aliyun_api_key.text(),
                'model': self.aliyun_model.currentText(),
                'system_prompt': self.aliyun_system_prompt.toPlainText()
            },
            'deepseek': {
                'api_key': self.deepseek_api_key.text(),
                'model': self.deepseek_model.currentText(),
                'system_prompt': self.deepseek_system_prompt.toPlainText()
            }
        }
        
        return config

def main():
    # 启用高DPI缩放支持
    QCoreApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QCoreApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    # 创建应用实例
    app = QApplication(sys.argv)
    
    # 设置全局字体，确保在高DPI下字体清晰
    font = QFont()
    font.setPointSize(10)
    app.setFont(font)
    
    window = MainWindow()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()