'''
08/02/2019：v2.1修正了v2的一个重大bug，将self.items_info = ''这一句从369行移动到463行
            添加1项功能：keyPressEvent每次输入时检查keyList长度是否超过13，若超过说明其他逻辑出错，先清空keyList，
                            为新的输入腾出地方
07/24/2019: v2是v1.3复制过来的，主要为了配合backend的新功能做一些修改，包括：
    v1.3相对于v1.2的主要改变是，能够显示所有已扫码商品;此外还解决了点击"确认付款"之后没有点"是的"
(这种情况下button1会切换为显示"开始结账"的unchecked状态,这是不对的),我的做法是手动通过setChecked
方法将button1固定在checked状态;
07/22/2019：Cashier_v1_1是Cashier_v1的改进，主要是将GUI改成竖排界面
07/18/2019：以cashier_v0.2为模板，结合layout_test2中的GUI设计（控件大小与屏幕分辨率绑定）
'''
import sys
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
import cv2
import numpy as np
import time

from collections import defaultdict


import cgitb
cgitb.enable(format='text')  # 显示多线程错误信息


# 将图像处理工作放在一个QObject子类中完成，用于QThread多线程实现


class FrontEnd(QWidget):

    def __init__(self):
        super().__init__()
        self.pbar = QProgressBar()
        self.pbar.setRange(0, 1000)
        self.pbar.setGeometry(30, 40, 100, 25)
        # self.pbar.setMaximum(0)
        # self.pbar.setMinimum(100)
        self.step = 0
        self.initUI()


    def initUI(self):


        # 以下是控件及其功能设计
        # 获取显示器分辨率
        self.desktop = QApplication.desktop()
        self.screenRect = self.desktop.screenGeometry()
        self.width = self.screenRect.width()  # 屏幕宽度
        self.height = self.screenRect.height()  # 屏幕高度

        # self.setGeometry(int(self.width/4), int(self.height/4), int(self.width/4*9/16), int(self.height/4*16/9))  # 窗口初始大小为屏幕的1/4
        self.setMinimumSize(1280, 720)
        self.setWindowTitle('Ruijie Smart Cashier v1.1')

        self.label_show_image = QLabel()  # 显示摄像头画面的控件，DragLabel是继承自QLabel的自定义类，实现了鼠标选区功能
        self.loadVideoButton = QPushButton("视频输入")
        self.loadVideoButton.setCheckable(True)
        # self.loadVideoButton.setText(u"选择视频")
        # self.loadVideoButton.clicked.connect(self.loadVideo)
        self.loadVideoButton.setFixedSize(155, 40)
        self.loadVideoButton.setStyleSheet("QPushButton{background-color:#5F9EA0; color: #FFFFFF;"  # 天蓝色背景白色字体
                                              "border:2px groove gray;border-radius:10px;padding:2px 4px;"  # 圆角按钮
                                              "border-style: outset;}"  # 平时向外凹陷，按下时向内凹陷
                                              "QPushButton:pressed{background-color:rgb(176,196,222);border - style: inset;}"
                                              )
        self.loadVideoButton.setFont(QFont("Roman times", 18, QFont.Bold))

        self.timer = QBasicTimer()
        self.timer.start(100, self)

        # self.startButton.setFixedSize(155, 40)




        # 控件布局设计：QGridLayout
        main_layout = QGridLayout(self)  # 整体使用网格布局
        main_layout.addWidget(self.label_show_image, 0, 0, 3, 1)
        main_layout.addWidget(self.loadVideoButton, 2, 0, 2, 1)
        main_layout.addWidget(self.pbar, 2, 2, 2, 1)

        main_layout.setAlignment(Qt.AlignCenter)
        self.setLayout(main_layout)

        # 设置整个窗口的背景颜色为白色而不是默认的灰色
        bgColor = QPalette()
        bgColor.setColor(self.backgroundRole(), QColor(255, 255, 255))
        self.setPalette(bgColor)

    def loadVideo(self):
        self.video_name = QFileDialog.getOpenFileName(self, caption="open file dialog", directory="C:/Users/Minghao/Desktop/gopro")
        print(self.video_name[0])

    # 重写QObject的timerEvent方法，用于刷新显示进度条
    def timerEvent(self, event):
        if self.step >= 1000:
            self.step = 0
            return
        time.sleep(0.1)
        self.step = self.step + 1
        self.pbar.setValue(self.step)








if __name__ == "__main__":
    print('parent thread ID: ', int(QThread.currentThreadId()))  # 打印主线程ID
    app = QApplication(sys.argv)
    example = FrontEnd()
    example.show()
    sys.exit(app.exec_())
