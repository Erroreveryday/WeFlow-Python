import sys
import os
import logging

# 添加src目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTextEdit, QLabel, QStatusBar, QLineEdit, QTableWidget, QTableWidgetItem, QCheckBox, QDialog, QFormLayout, QComboBox, QGroupBox
from PyQt5.QtCore import QThread, pyqtSignal, Qt, Q_ARG, QCoreApplication, QTimer
from PyQt5.QtGui import QFont
from weflow.status_checker import test_api_health, check_weixin_status
from utils import load_config, save_config

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
        # 加载配置
        self.config = load_config()
        self.init_ui()
        self.setup_logger()
        self.load_wechat_sessions()
        
        # 初始化状态检查定时器
        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self.auto_check_status)
        # 每5秒检查一次状态
        self.status_timer.start(5000)
        # 立即执行一次检查
        self.auto_check_status()
    
    def load_wechat_sessions(self):
        """加载微信会话配置到表格"""
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
    
    def showEvent(self, event):
        """窗口显示事件"""
        super().showEvent(event)
        # 窗口显示后连接屏幕切换信号
        if self.windowHandle():
            self.windowHandle().screenChanged.connect(self.on_screen_changed)
    
    def init_ui(self):
        self.setWindowTitle("WeFlow 状态监控")
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
        self.show_hide_shortcut = QLineEdit(self.config.get('wechat_shortcuts', {}).get('show_hide_window', 'Ctrl+Alt+W'))
        self.show_hide_shortcut.textChanged.connect(self.save_shortcuts_config)
        show_hide_layout.addWidget(show_hide_label)
        show_hide_layout.addWidget(self.show_hide_shortcut)
        
        # 发送消息
        send_message_layout = QHBoxLayout()
        send_message_label = QLabel("发送消息:")
        self.send_message_shortcut = QComboBox()
        self.send_message_shortcut.addItems(["Enter", "Ctrl+Enter"])
        # 设置默认值
        send_option = self.config.get('wechat_shortcuts', {}).get('send_message', 'Enter')
        self.send_message_shortcut.setCurrentText(send_option)
        self.send_message_shortcut.currentTextChanged.connect(self.save_shortcuts_config)
        send_message_layout.addWidget(send_message_label)
        send_message_layout.addWidget(self.send_message_shortcut)
        
        # 提示文本
        tip_label = QLabel("快捷键需与微信设置相同")
        tip_label.setStyleSheet("QLabel { font-size: 10px; color: #666; }")
        
        shortcuts_content_layout.addLayout(show_hide_layout)
        shortcuts_content_layout.addLayout(send_message_layout)
        shortcuts_content_layout.addWidget(tip_label)
        shortcuts_group.setLayout(shortcuts_content_layout)
        
        # API端口号配置
        api_group = QGroupBox("WeFlow API 配置")
        api_content_layout = QVBoxLayout()
        
        config_layout = QHBoxLayout()
        config_label = QLabel("端口号:")
        self.port_input = QLineEdit(str(self.config.get('weflow_api_port', 5031)))
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
        
        # 添加到右侧布局（从上到下：微信快捷键配置、API端口号配置+API状态、微信状态）
        wechat_shortcuts_layout.addWidget(shortcuts_group)
        wechat_shortcuts_layout.addSpacing(10)
        wechat_shortcuts_layout.addWidget(api_group)
        
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
            self.config['wechat_shortcuts']['send_message'] = self.send_message_shortcut.currentText()
            
            success, message = save_config(self.config)
            
            if success:
                # 更新状态条消息
                if port_saved:
                    self.status_bar.showMessage(f"配置保存成功，API端口号: {port}")
                    logging.info(f"配置保存成功，API端口号: {port}")
                else:
                    self.status_bar.showMessage("快捷键配置保存成功，API端口号输入无效")
                logging.info(f"微信快捷键配置已保存: 显示/隐藏={self.show_hide_shortcut.text()}, 发送消息={self.send_message_shortcut.currentText()}")
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
            self.config['wechat_shortcuts']['send_message'] = self.send_message_shortcut.currentText()
            
            success, message = save_config(self.config)
            
            if success:
                logging.info(f"微信快捷键配置已保存: 显示/隐藏={self.show_hide_shortcut.text()}, 发送消息={self.send_message_shortcut.currentText()}")
            else:
                logging.error(f"快捷键配置保存失败: {message}")
        except Exception as e:
            logging.error(f"保存快捷键配置失败: {str(e)}")
    
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
            else:
                self.status_bar.showMessage(f"会话删除失败: {message}")
                logging.error(f"会话删除失败: {message}")

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
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()