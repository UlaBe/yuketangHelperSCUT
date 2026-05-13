import sys
import threading
from pathlib import Path

from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QApplication,
    QDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from app.ui import Ui_MainWindow
import webbrowser
from app.videoHelper import StopRequested, start as start_video_helper


# 定义要传递的参数
csrftoken = ""
sessionid = ""
university_id = ""


def resource_path(relative_path):
    """Return a path that works both in source and PyInstaller bundles."""
    base_path = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    return str(base_path / relative_path)


def app_icon():
    return QIcon(resource_path("icon.png"))


class HelpMessageBox(QMessageBox):
    def __init__(self, parent=None):
        super().__init__(parent)

        # 设置消息框标题和图标
        self.setWindowTitle("帮助")
        self.setWindowIcon(app_icon())
        self.setIcon(QMessageBox.Information)

        # 创建 QLabel 用于显示帮助信息
        self.label = QLabel()
        self.label.setText(
            "\n\n浏览器登录上雨课堂，然后按 F12 --> 选 Application --> 找到雨课堂的 cookies，"
            "寻找 csrftoken、sessionid、\n\nuniversity_id 字段\n\n"
            "如果出现报错可以尝试关闭代理\n\n"            
            "反馈问题邮箱 nuozanxinye921.gmail.com\n\n"
            "项目源码/使用教程："
        )

        # 创建 QTextEdit 用于显示项目源码链接（可复制）
        self.text_edit = QTextEdit()
        self.text_edit.setPlainText("https://github.com/Cat1007/yuketangHelperSCUTLite")
        self.text_edit.setReadOnly(True)  # 设置为只读
        self.text_edit.setFixedHeight(30)  # 设置固定高度

        self.label_url = QLabel()
        self.label_url.setText('<a href="https://www.example.com">点击打开链接</a>')
        self.label.setOpenExternalLinks(True)

        # 将 QLabel 和 QTextEdit 添加到 QMessageBox
        layout = self.layout()
        layout.addWidget(self.label, 0, 0)
        layout.addWidget(self.text_edit, 1, 0)
        # layout.addWidget(self.label_url, 1, 0)

class VideoHelperThread(QThread):
    output_signal = pyqtSignal(str)
    input_requested = pyqtSignal(str)  # 新增信号：请求输入
    finished_signal = pyqtSignal()

    def __init__(self, csrftoken, sessionid, university_id):
        super().__init__()
        self.csrftoken = csrftoken
        self.sessionid = sessionid
        self.university_id = university_id
        self._is_running = True
        self._input_event = threading.Event()
        self._input_value = None

    def run(self):
        try:
            start_video_helper(
                self.csrftoken,
                self.sessionid,
                self.university_id,
                log_callback=self.output_signal.emit,
                input_callback=self.request_input,
                stop_callback=self.should_stop,
            )
        except StopRequested:
            self.output_signal.emit("任务已停止")
        except Exception as e:
            self.output_signal.emit(f"运行时发生错误: {str(e)}")
        finally:
            self.finished_signal.emit()

    def should_stop(self):
        return not self._is_running

    def request_input(self, prompt):
        self._input_value = None
        self._input_event.clear()
        self.input_requested.emit(prompt)
        while self._is_running:
            if self._input_event.wait(0.1):
                if self._input_value is None:
                    raise StopRequested("任务已停止")
                return self._input_value
        raise StopRequested("任务已停止")

    def send_user_input(self, user_input):
        """向工作线程发送用户输入"""
        self._input_value = user_input
        self._input_event.set()

    def stop(self):
        """请求停止工作线程"""
        self._is_running = False
        self._input_event.set()

class InputDialog(QDialog):
    """自定义非阻塞输入对话框"""
    input_signal = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("输入课程编号")
        self.setWindowIcon(app_icon())
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        self.setModal(False)

        layout = QVBoxLayout()

        self.label = QLabel("请输入课程编号:")
        layout.addWidget(self.label)

        self.input_field = QLineEdit(self)
        self.input_field.returnPressed.connect(self.submit_input)
        layout.addWidget(self.input_field)

        self.submit_button = QPushButton("提交", self)
        self.submit_button.clicked.connect(self.submit_input)
        layout.addWidget(self.submit_button)

        self.setLayout(layout)

    def open_for_prompt(self, prompt):
        self.label.setText(prompt)
        self.input_field.clear()
        self.adjustSize()
        self.show()
        self.raise_()
        self.activateWindow()
        self.input_field.setFocus()

    def submit_input(self):
        user_input = self.input_field.text().strip()
        self.input_signal.emit(user_input)  # 发射信号，将输入发送到主窗口
        self.close()

class mywindow(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super(mywindow, self).__init__()
        self.setupUi(self)
        self.setWindowIcon(app_icon())

        self.start.clicked.connect(self.startprocess)
        self.stop.clicked.connect(self.stopprocess)
        self.help.clicked.connect(self.show_help)
        self.go_web.clicked.connect(self.open_website)
        self.sub_thread = None
        self.input_dialog = InputDialog(self)  # 创建自定义的输入对话框
        self.input_dialog.input_signal.connect(self.send_input_to_worker)
        self.stop.setEnabled(False)

        self.auto_scroll = True
        self.textBrowser.verticalScrollBar().valueChanged.connect(self.check_scroll_position)

    def startprocess(self):
        global csrftoken, sessionid, university_id
        csrftoken = self.csrftoken_input.toPlainText().strip()
        sessionid = self.sessionid_input.toPlainText().strip()
        university_id = self.university_id_input.toPlainText().strip()

        # 检查参数是否为空
        if not csrftoken or not sessionid or not university_id:
            QMessageBox.critical(self, "错误", "参数不能为空！")
            return
        if self.sub_thread and self.sub_thread.isRunning():
            QMessageBox.information(self, "提示", "任务正在运行中")
            return

        # 创建并启动线程
        self.sub_thread = VideoHelperThread(csrftoken, sessionid, university_id)
        self.sub_thread.output_signal.connect(self.update_text_browser)
        self.sub_thread.input_requested.connect(self.handle_input_request)  # 连接输入请求信号
        self.sub_thread.finished_signal.connect(self.handle_task_finished)
        self.start.setEnabled(False)
        self.stop.setEnabled(True)
        self.sub_thread.start()

    def stopprocess(self):
        if self.sub_thread:
            self.sub_thread.stop()
            self.textBrowser.append("正在停止任务...")

    def update_text_browser(self, text):
        self.textBrowser.append(text)
        if self.auto_scroll:
            QTimer.singleShot(0, self.textBrowser.ensureCursorVisible)  # 延时执行确保滚动

    def handle_input_request(self, prompt):
        """处理输入请求（弹出自定义的输入框并确保主线程不被阻塞）"""
        self.update_text_browser("请选择要刷的课程编号")
        self.input_dialog.open_for_prompt(prompt)  # 弹出自定义输入框

    def send_input_to_worker(self, user_input):
        """向工作线程发送用户输入"""
        if self.sub_thread:
            self.sub_thread.send_user_input(user_input)

        self.auto_scroll = True

    def handle_task_finished(self):
        self.start.setEnabled(True)
        self.stop.setEnabled(False)
        self.sub_thread = None

    def show_help(self):
        # reply = QMessageBox.about(self, "帮助", "浏览器登录上雨课堂，然后按F12-->选Application-->找到雨课堂的cookies，寻找csrftoken、sessionid、university_id字段\n\n如果出现报错可以尝试关闭代理\n\n项目源码：https://github.com/Cat1007/yuketangHelperSCUTLite")
        # print(reply)

        # 创建自定义的帮助消息框
        help_box = HelpMessageBox(self)
        reply = help_box.exec_()  # 显示消息框并获取返回值
        print(reply)  # 打印返回值（例如 QMessageBox.Ok）

    def check_scroll_position(self, value):
        """检查滚动条位置"""
        scrollbar = self.textBrowser.verticalScrollBar()
        self.auto_scroll = (value >= scrollbar.maximum() - 5)

    def open_website(self):
        # 打开指定URL
        url = "https://scut.yuketang.cn/pro/courselist"
        webbrowser.open(url)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = mywindow()
    window.show()
    sys.exit(app.exec_())
