
import sys
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
import numpy as np
from backend_simple import Washer  # 后端处理
import time
import cgitb
cgitb.enable(format='text')  # 显示多线程错误信息

# 全局变量
PAUSE = 0
# VIDEO_NAME = 'C:/Users/Minghao/Desktop/gopro1/TEST1.MP4'

# 将图像处理工作放在一个QObject子类中完成，用于QThread多线程实现
class Worker(QObject):

    call_todo = pyqtSignal(str)  # 用于触发worker的后台运行
    trigger = pyqtSignal()  # 每处理完一帧触发显示
    clear = pyqtSignal()    # 触发清空输入缓存的信号

    def __init__(self):
        super().__init__()
        self.washing_time = 0
        self.frame_to_show = np.zeros((1024, 576, 3), dtype=np.uint8)

    @pyqtSlot(str)  # 使signal-slot的绑定关系与moveToThread的先后顺序无关
    def start(self, video_name):
        print('subthread ID: ', int(QThread.currentThreadId()))  # 打印子线程号
        lil_washer = Washer(video_path=video_name)
        self.frame_to_show = np.zeros((1024, 576, 3), dtype=np.uint8)
        self.washing_time = 0.0  # 洗手总计时间(1/24×帧数，单位为s)
        self.video_end = 0
        # VIDEO_PATH = 'C:/Users/Minghao/Desktop/gopro1/TEST1.MP4'
        while 1:
            # 07/24/2019: 将状态机的flag信号添加到输出列表中:self.machine_state，目的是确保flag=0的时候才能确认付款
            if PAUSE == 1:
                pass
            elif PAUSE == -1:  # actually, stop
                lil_washer.video_cap.release()
                break
            elif PAUSE == 0:
                self.frame_to_show, self.washing_time, self.video_end = lil_washer.predict()
                self.trigger.emit()
                if self.video_end:  # 视频播放到了最后一帧
                    lil_washer.video_end = 0
                    self.video_end = 0
                    # time.sleep(3)
                    self.clear.emit()
                    print('ended phase 1')
                    break


class FrontEnd(QWidget):

    def __init__(self):
        super().__init__()
        self.video_name = 'C:/Users/Minghao/Desktop/gopro/TEST2.MP4'
        self.initUI()


    def initUI(self):
        # 为图像处理建立后台线程
        self.workThread = QThread()
        self.workThread.start()
        self.worker = Worker()  # 例化一个worker对象
        self.worker.moveToThread(self.workThread)
        self.worker.trigger.connect(self.showFrame)  # 每处理完一帧，打印
        self.worker.clear.connect(self.restart)
        # self.worker.clear.connect(self.paintEvent)
        self.worker.call_todo.connect(self.worker.start)

        # 以下是控件及其功能设计
        # 获取显示器分辨率
        self.desktop = QApplication.desktop()
        self.screenRect = self.desktop.screenGeometry()
        self.width = self.screenRect.width()  # 屏幕宽度
        self.height = self.screenRect.height()  # 屏幕高度

        # self.setGeometry(int(self.width/4), int(self.height/4), int(self.width/4*9/16), int(self.height/4*16/9))  # 窗口初始大小为屏幕的1/4
        # self.setMinimumSize(1280, 720)
        self.setGeometry(350, 200, 1200, 700)
        self.setWindowTitle("洗手检测DEMO")
        self.setWindowIcon(QIcon('icons/Hi-logo.png'))

        self.label_show_image = QLabel()  # 显示摄像头画面的控件，DragLabel是继承自QLabel的自定义类，实现了鼠标选区功能
        self.label_show_image.setFixedSize(1024, 576)

        self.label_status = QLabel()  # 显示是否完成洗手
        self.label_status.setFixedSize(360, 50)
        self.label_status.setFont(QFont("Roman times", 18, QFont.Bold))
        self.label_status.setAlignment(Qt.AlignCenter)
        self.label_status.setStyleSheet("border:2px solid blue; border-radius:10px; padding:2px 4px;")
        self.label_status.setText("就绪")
        # self.label_status.setStyleSheet("QPushButton{background-color:#5F9EA0; color: #FFFFFF;"  # 天蓝色背景白色字体
        #                                "border:2px groove gray;border-radius:10px;padding:2px 4px;"  # 圆角按钮
        #                                "border-style: outset;}"  # 平时向外凹陷，按下时向内凹陷
        #                                "QPushButton:pressed{background-color:rgb(176,196,222);border - style: inset;}"
        #                                )

        self.loadVideoButton = QPushButton("选择DEMO")
        # self.loadVideoButton.setText(u"选择视频")
        self.loadVideoButton.clicked.connect(self.loadVideo)
        self.loadVideoButton.setFixedSize(320, 50)
        self.loadVideoButton.setStyleSheet("QPushButton{background-color:#5F9EA0; color: #FFFFFF;"  # 天蓝色背景白色字体
                                           "border:2px groove gray;border-radius:10px;padding:2px 4px;"  # 圆角按钮
                                           "border-style: outset;}"  # 平时向外凹陷，按下时向内凹陷
                                           "QPushButton:pressed{background-color:rgb(176,196,222);border - style: inset;}"
                                           )
        self.loadVideoButton.setFont(QFont("Roman times", 18, QFont.Bold))

        self.startButton = QPushButton("开始检测")
        self.startButton.clicked.connect(self.work)
        self.startButton.setCheckable(True)  # 设为可以按下和弹起的形式
        self.startButton.setFixedSize(320, 50)
        self.startButton.setStyleSheet("QPushButton{background-color:#5F9EA0; color: #FFFFFF;"  # 天蓝色背景白色字体
                                           "border:2px groove gray;border-radius:10px;padding:2px 4px;"  # 圆角按钮
                                           "border-style: outset;}"  # 平时向外凹陷，按下时向内凹陷
                                           "QPushButton:pressed{background-color:rgb(176,196,222);border - style: inset;}"
                                           )
        self.startButton.setFont(QFont("Roman times", 18, QFont.Bold))

        # 进度条和刷新进度条用的计时器
        self.pbar = QProgressBar()
        self.pbar.setRange(0, 1000)
        self.pbar.setFixedSize(1025, 50)
        self.pbar.setTextVisible(False)
        self.pbar.setStyleSheet("QProgressBar{background-color:#FFFFFF; color: #FFFFFF;"  # 天蓝色背景白色字体
                                       "border:2px groove gray;border-radius:10px;padding:2px 4px;}")  # 圆角按钮
        self.timer = QBasicTimer()


        # 控件布局设计：QGridLayout
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.loadVideoButton)
        button_layout.addWidget(self.label_status)
        button_layout.addWidget(self.startButton)

        main_layout = QGridLayout(self)  # 整体使用网格布局
        main_layout.addWidget(self.label_show_image, 0, 0, 9, 16)
        main_layout.addLayout(button_layout, 9, 0, 2, 16)
        # main_layout.addWidget(self.loadVideoButton, 9, 0, 2, 5)
        # main_layout.addWidget(self.label_status, 9, 5, 2, 6)
        # main_layout.addWidget(self.startButton, 9, 11, 2, 5)
        main_layout.addWidget(self.pbar, 11, 0, 2, 16)
        main_layout.setAlignment(Qt.AlignCenter)
        self.setLayout(main_layout)

        self.showFrame()

        # 设置整个窗口的背景颜色为白色而不是默认的灰色
        self.bgColor = QPalette()
        self.bgColor.setColor(self.backgroundRole(), QColor(255, 255, 255))
        self.setPalette(self.bgColor)

    # 重写QObject的timerEvent方法，用于刷新显示进度条
    def timerEvent(self, event):
        if self.worker.washing_time <= 20:
            self.time = self.worker.washing_time * 50
            self.label_status.setText("洗手不足20秒...")
            self.label_status.setStyleSheet("background-color:#FF6347; color: #FFFFFF; border-radius:10px; padding:2px 4px;")

        else:
            self.time = 1000
            self.label_status.setText("洗手已满20秒!")
            self.label_status.setStyleSheet("background-color:#7FFF00; color: #FFFFFF; border-radius:10px; padding:2px 4px;")

        # print(self.time)
        self.pbar.setValue(self.time)



    def loadVideo(self):
         video_name = QFileDialog.getOpenFileName(self, caption="open file dialog", directory="C:/Users/Minghao/Desktop/gopro2")
         self.video_name = video_name[0]

    def keyPressEvent(self, keyEvent):
        global PAUSE
        if keyEvent.key() == Qt.Key_Escape:
            print(keyEvent.key())
            self.close()
        elif keyEvent.key() == Qt.Key_P:  # 按下P键暂停/继续
            PAUSE = PAUSE ^ 1
        elif keyEvent.key() == Qt.Key_Q:  # 按下Q键停止当前视频
            PAUSE = -1

    # 第一个按钮：开始结账/确认付款
    def work(self):
        global PAUSE
        PAUSE = 0
        self.timer.start(100, self)
        self.worker.call_todo.emit(self.video_name)


    def showFrame(self):
        self.label_show_image.setScaledContents(True)
        IMG = self.worker.frame_to_show
        frame_height, frame_width, channel = IMG.shape
        bytesPerline = 3 * frame_width
        img = QImage(IMG.data, frame_width, frame_height, bytesPerline,
                     QImage.Format_RGB888).rgbSwapped()
        # 根据宽高比设置待显示图像的尺寸（使用QImage的scaled方法）
        widget_width = self.label_show_image.width()
        widget_height = self.label_show_image.height()
        frame_ratio = float(frame_width) / float(frame_height)
        widget_ratio = float(widget_width) / float(widget_height)
        if frame_ratio <= widget_ratio:
            adjusted_height = widget_height
            adjusted_width = int(widget_height * frame_ratio)
        else:  # frame_ratio >= widget_ratio
            adjusted_width = widget_width
            adjusted_height = int(widget_width / frame_ratio)
        img = QPixmap.fromImage(img).scaled(adjusted_width, adjusted_height)
        self.label_show_image.setPixmap(img)

    def restart(self):  # 当前视频播放完毕，重播一遍

        print('ended phase 2')
        time.sleep(3)
        self.worker.call_todo.emit(self.video_name)








if __name__ == "__main__":
    print('parent thread ID: ', int(QThread.currentThreadId()))  # 打印主线程ID
    app = QApplication(sys.argv)
    example = FrontEnd()
    example.show()
    sys.exit(app.exec_())
