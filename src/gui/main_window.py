import sys
import os
import logging

# 添加src目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTextEdit, QLabel, QStatusBar, QLineEdit
from PyQt5.QtCore import QThread, pyqtSignal, Qt, Q_ARG, QCoreApplication
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
    
    def showEvent(self, event):
        """窗口显示事件"""
        super().showEvent(event)
        # 窗口显示后连接屏幕切换信号
        if self.windowHandle():
            self.windowHandle().screenChanged.connect(self.on_screen_changed)
    
    def init_ui(self):
        self.setWindowTitle("WeFlow 状态监控")
        self.setGeometry(100, 100, 800, 600)
        
        # 中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout(central_widget)
        
        # 配置区域
        config_layout = QHBoxLayout()
        config_label = QLabel("API端口号:")
        self.port_input = QLineEdit(str(self.config.get('weflow_api_port', 5031)))
        save_config_button = QPushButton("保存配置")
        save_config_button.clicked.connect(self.save_config)
        
        config_layout.addWidget(config_label)
        config_layout.addWidget(self.port_input)
        config_layout.addWidget(save_config_button)
        
        # 状态检查区域
        status_layout = QHBoxLayout()
        
        # API状态检查
        api_layout = QVBoxLayout()
        api_label = QLabel("API状态:")
        self.api_status_label = QLabel("未检查")
        self.api_status_label.setStyleSheet("QLabel { border: 1px solid #ccc; padding: 5px; margin: 5px; }")
        api_check_button = QPushButton("检查API状态")
        api_check_button.clicked.connect(self.check_api_status)
        
        api_layout.addWidget(api_label)
        api_layout.addWidget(self.api_status_label)
        api_layout.addWidget(api_check_button)
        
        # 微信状态检查
        weixin_layout = QVBoxLayout()
        weixin_label = QLabel("微信状态:")
        self.weixin_status_label = QLabel("未检查")
        self.weixin_status_label.setStyleSheet("QLabel { border: 1px solid #ccc; padding: 5px; margin: 5px; }")
        weixin_check_button = QPushButton("检查微信状态")
        weixin_check_button.clicked.connect(self.check_weixin_status)
        
        weixin_layout.addWidget(weixin_label)
        weixin_layout.addWidget(self.weixin_status_label)
        weixin_layout.addWidget(weixin_check_button)
        
        status_layout.addLayout(api_layout)
        status_layout.addLayout(weixin_layout)
        
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
        
        # 添加到主布局
        main_layout.addLayout(config_layout)
        main_layout.addLayout(status_layout)
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
            port = int(self.port_input.text())
            
            self.config['weflow_api_port'] = port
            success, message = save_config(self.config)
            
            if success:
                # 更新状态条消息
                self.status_bar.showMessage(message)
                logging.info(f"配置保存成功，API端口号: {port}")
            else:
                self.status_bar.showMessage(f"配置保存失败: {message}")
                logging.error(f"配置保存失败: {message}")
        except ValueError as e:
            self.status_bar.showMessage(f"配置保存失败: {str(e)}")
            logging.error(f"配置保存失败: {str(e)}")

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