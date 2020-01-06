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

from backend import Dealer  # 后端处理
from LUT import look_up_table
from collections import defaultdict


import cgitb
cgitb.enable(format='text')  # 显示多线程错误信息
# 定义全局变量，用于前后端之间必要的通信

global IMG, CORNERS
IMG = np.ones([480, 640, 3], dtype=np.uint8)
CORNERS = [0, 0, 0, 0]


# 用于显示商品价格信息的QLabel，实现背景图片自动调整大小
class BackgroundLabel(QLabel):
    '''
    自定义类，为了实现背景自动调整大小，重写paintEvent方法
    '''
    def __init__(self):
        super().__init__()

    def paintEvent(self, event):
        painter = QPainter(self)
        # 设置背景图片，平铺到整个窗口，随着窗口改变而改变
        painter.drawPixmap(self.rect(), QPixmap('./icons/info.jpg'))  # self.rect()获取当前控件大小
        QLabel.paintEvent(self, event)


# 用于显示视频流的QLabel，继承的目的是为了实现鼠标事件
class DragLabel(QLabel):
    '''
    自定义类，继承自QLabel，主要为了实现鼠标点击选取区域的功能
    '''
    def __init__(self):
        super().__init__()
        self.mouse_pressed = False
        self.start_point = [0, 0]
        self.end_point = [0, 0]

    def mousePressEvent(self, e):  # e.button() == Qt.LeftButton  鼠标左键点击事件
        #print('mousePressEvent(%d,%d)\n' % (e.pos().x(), e.pos().y()))
        self.mouse_pressed = True
        self.start_point = [e.pos().x(), e.pos().y()]  # 点击起始位置
        self.end_point = [e.pos().x(), e.pos().y()]  # 先初始化鼠标当前的位置变量（占位）
        # 得到的点击位置要缩放到视频图像的像素坐标系中（控件小，视频大，所谓的pos在二者上其实不是一个位置）
        x_pos = int(e.pos().x() * 1080 / 640)
        y_pos = int(e.pos().y() * 810 / 480)  # 不同的相机，如果不是4：3的画幅，这里的810要改
        CORNERS[0:2] = [x_pos, y_pos]  # 鼠标按下的位置
        CORNERS[2:4] = [x_pos, y_pos]  # 鼠标松开的位置（初始化占位）
        # self.update()

    def mouseMoveEvent(self, e):  # 鼠标左键按下并拖动
        # print('mouse move:(%d,%d)\n' % (e.pos().x(), e.pos().y()))
        if self.mouse_pressed:  # 鼠标按下并移动期间不断更新当前位置
            self.end_point = [e.pos().x(), e.pos().y()]
            print('x, y: ', e.pos().x(), e.pos().y())
        # self.update()

    def mouseReleaseEvent(self, e):  # 鼠标松开
        #print('mouseReleaseEvent(%d,%d)\n' % (e.pos().x(), e.pos().y()))
        self.end_point = [e.pos().x(), e.pos().y()]
        # 得到的点击位置要缩放到视频图像的像素坐标系中（控件小，视频大，所谓的pos在二者上其实不是一个位置）
        width = self.rect().width()
        height = self.rect().height()
        x_pos = int(e.pos().x() * 1080 / width)  # 1215 = 810/2*3
        # x_pos = int(x_pos * 0.94)  # 控件比例3：2，画面比例4：3，所以x坐标还要线性变换一下（y坐标不需要）
        y_pos = int(e.pos().y() * 810 / height)  # 不同的相机，如果不是4：3的画幅，这里的810要改
        CORNERS[2:4] = [x_pos, y_pos]  # 记录鼠标松开的位置
        self.mouse_pressed = False
        # self.update()

    def paintEvent(self, event):  # 重写paintEvent，实现在显示的图像上画框
        QLabel.paintEvent(self, event)  # 避免原来的绘图（视频图像）被接下来的内容覆盖
        # 画出鼠标选取的区域
        if self.mouse_pressed:
            painter = QPainter(self)
            pen = QPen(Qt.red, 2, Qt.SolidLine)
            painter.setPen(pen)  # 设置线条颜色、粗细和形式
            x = self.start_point[0]
            y = self.start_point[1]
            w = self.end_point[0] - self.start_point[0]
            h = self.end_point[1] - self.start_point[1]
            painter.drawRect(QRect(x, y, w, h))  # 画一个矩形框


# 将图像处理工作放在一个QObject子类中完成，用于QThread多线程实现
class Worker(QObject):

    call_todo = pyqtSignal()  # 用于触发worker的后台运行
    trigger = pyqtSignal()  # 每处理完一帧触发显示
    clear = pyqtSignal()    # 触发清空输入缓存的信号

    def __init__(self):
        super().__init__()
        self.a_checks = 0  # alpha means money
        self.b_checks = 0  # beta means no money
        self.digits = []   # 向后台传递的扫码器输入，每次最多一个码（12或13位）
        self.clear_signal = 0
        self.show_border = 0  # 用于指示worker是否显示扫码/离开区域边界和flag等信息
        # 用于设置main area和exit area的参数
        self.set_main = 0
        self.set_exit = 0
        self.lock = 1  # backend的状态机不是时时刻刻都运行，而是每点击一次“开始结账”才开始运行（lock=0），确认付款后lock=1
        self.machine_state = 0

    @pyqtSlot()  # 这个装饰器的作用是，让signal-slot的绑定关系与moveToThread的先后顺序无关
    def start(self):
        print('subthread ID: ', int(QThread.currentThreadId()))  # 打印子线程号
        lil_dealer = Dealer()
        while True:
            global IMG, CORNERS
            # 07/24/2019: 将状态机的flag信号添加到输出列表中:self.machine_state，目的是确保flag=0的时候才能确认付款
            IMG, self.a_checks, self.b_checks, self.clear_signal, self.machine_state = \
                lil_dealer.deal(self.digits, self.show_border, self.set_main, self.set_exit, CORNERS, self.lock)
            self.trigger.emit()
            if self.clear_signal:
                self.clear.emit()


class Cashier(QWidget):

    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.keyList = []  # 记录键盘输入
        self.finished_signal = 0  # 一次输入结束（回车）后置1，准备清除keyList
        self.ready_for_input = 0  # 接收键盘输入存入keyList，设置这个信号的原因是防止同一商品多次扫码
        self.price_sum = 0  # 已扫码商品的总金额
        self.start_up = 1  # 标记是否为首次启动，为0时表示不是首次启动，而是开始新一轮结账流程
        self.scanned_items = []
        self.previous_beta_checks = 0  # 代表之前的所有顾客的失败次数之和

        self.workThread = QThread()  # 为图像处理建立一个线程
        self.workThread.start()
        self.worker = Worker()  # 例化一个worker对象
        self.worker.moveToThread(self.workThread)

        # 以下是控件及其功能设计
        # 获取显示器分辨率
        self.desktop = QApplication.desktop()
        self.screenRect = self.desktop.screenGeometry()
        self.width = self.screenRect.width()  # 屏幕宽度
        self.height = self.screenRect.height()  # 屏幕高度

        # self.setGeometry(int(self.width/4), int(self.height/4), int(self.width/4*9/16), int(self.height/4*16/9))  # 窗口初始大小为屏幕的1/4
        self.setMinimumSize(768, 1366)
        self.setWindowTitle('Ruijie Smart Cashier v1.1')

        self.label_show_camera = DragLabel()  # 显示摄像头画面的控件，DragLabel是继承自QLabel的自定义类，实现了鼠标选区功能
        self.label_show_item = QLabel()  # 显示商品快照snapshot的控件
        self.label_item_info = BackgroundLabel()  # 显示商品价格信息的控件
        self.top_placeholder = QLabel()  # 顶端和底端的空白占位符
        self.bottom_placeholder = QLabel()  # 顶端和底端的空白占位符
        self.button1 = QPushButton("开始结账")
        button2 = QPushButton("显示边界")
        self.button_setMainArea = QPushButton("扫码区域")
        self.button_setExitArea = QPushButton("打包区域")
        itemsCount = QLabel("商品总数:")  # 显示已扫码商品总数和扫码失败次数的控件
        itemsCount.setObjectName('display_label')
        itemsCount.setFixedSize(150, 30)
        self.counts = QLabel("0")  # 显示已扫商品总数
        self.counts.setObjectName('display_label')
        self.counts.setFixedSize(150, 30)
        betaCheck = QLabel("漏扫商品:")
        betaCheck.setObjectName('display_label')
        betaCheck.setFixedSize(150, 30)
        self.betas = QLabel("0")  # 显示假装扫码次数
        self.betas.setObjectName('display_label')
        self.betas.setFixedSize(150, 30)

        # 显示摄像头画面的控件
        # self.label_show_camera.setMinimumWidth(self.rect().width())
        # self.label_show_camera.setMinimumHeight(int(self.rect().height() / 9 * 8))
        welcome_img = cv2.imread('./icons/welcome.jpg', -1)  # 初始化为欢迎页面（静态图片）
        frame_height, frame_width, channel = welcome_img.shape
        bytesPerline = 3 * frame_width
        welcome_img = QImage(welcome_img.data, frame_width, frame_height, bytesPerline, QImage.Format_RGB888).rgbSwapped()
        # 根据视频和控件的宽高比，调整视频尺寸，保证视频处于画面中间且不发生比例变形
        self.label_show_camera.setAlignment(Qt.AlignCenter)  # 保证显示的图像在控件中间
        widget_width = self.label_show_camera.width()
        widget_height = self.label_show_camera.height()
        frame_ratio = float(frame_width) / float(frame_height)
        widget_ratio = float(widget_width) / float(widget_height)

        self.label_show_camera.setScaledContents(True)
        self.label_show_camera.setFixedSize(640, 480)
        welcome_img = QPixmap.fromImage(welcome_img).scaled(640, 480, Qt.KeepAspectRatio)
        self.label_show_camera.setPixmap(welcome_img)

        # 显示商品快照snapshot的控件
        self.label_show_item.setScaledContents(True)
        ready_img = cv2.imread('./icons/ready.jpg', -1)  # 初始化为欢迎页面
        print('self.label_show_item.width()', self.label_show_item.width())
        print('self.label_show_item.height()', self.label_show_item.height())
        height, width, channel = ready_img.shape
        bytesPerline = 3 * width
        ready_img = QImage(ready_img.data, width, height, bytesPerline, QImage.Format_RGB888).rgbSwapped()
        self.ready_img = QPixmap.fromImage(ready_img).scaled(315, 315)
        self.label_show_item.setPixmap(self.ready_img)
        self.label_show_item.setFixedSize(315, 315)


        # 显示商品价格信息的控件
        self.label_item_info.setStyleSheet(
            "QLabel{color:rgb(0,0,0,250);font-size:20px;font-weight:bold;font-family:Roman times;}"
            "QLabel:hover{color:rgb(255,0,0,255);}")
        self.label_item_info.setAlignment(Qt.AlignTop)
        self.label_item_info.setScaledContents(True)
        self.label_item_info.setFixedSize(315, 315)
        self.label_item_info.setText('\n\n\n\n  使用提示：请将商品放在待扫区,\n  依次扫码后放置在打包区域')

        # 显示已扫码商品总数和扫码失败次数的控件
        # itemsCount.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        itemsCount.setFixedSize(155, 40)
        itemsCount.setStyleSheet("border:2px solid red;")
        itemsCount.setAlignment(Qt.AlignCenter)
        itemsCount.setFont(QFont("Roman times", 18, QFont.Bold))
        self.counts.setAlignment(Qt.AlignCenter)
        self.counts.setStyleSheet("border:2px solid red;")
        self.counts.setFixedSize(155, 40)
        self.counts.setFont(QFont("Roman times", 18, QFont.Bold))

        betaCheck.setAlignment(Qt.AlignCenter)
        betaCheck.setFixedSize(155, 40)
        betaCheck.setStyleSheet("border:2px solid red;")
        betaCheck.setFont(QFont("Roman times", 18, QFont.Bold))
        self.betas.setAlignment(Qt.AlignCenter)
        self.betas.setFixedSize(155, 40)
        self.betas.setStyleSheet("border:2px solid red;")
        self.betas.setFont(QFont("Roman times", 18, QFont.Bold))
        #
        # self.setStyleSheet('''
        #     QLabel#display_label{
        #         border:2px solid red;
        #         font-family:Times;
        #         font-size:18;
        #         font-weight:700;
        #         text-align:center;
        #     }
        # ''')

        # 配置页面下方的按钮
        self.button1.setCheckable(True)  # 设为可以按下和弹起的形式，按下显示“确认付款”，弹起显示“开始结账”
        self.button1.clicked.connect(self.work)
        self.button1.setFixedSize(155, 40)
        button2.setCheckable(True)  # 设为可以按下和弹起的形式
        button2.clicked[bool].connect(self.showBorder)
        button2.setFixedSize(155, 40)

        # 设置按钮样式
        self.button1.setFont(QFont("Roman times", 18, QFont.Bold))
        self.button1.setStyleSheet("QPushButton{background-color:#87CEEB; color: #FFFFFF;"  # 天蓝色背景白色字体
                              "border:2px groove gray;border-radius:10px;padding:2px 4px;"  # 圆角按钮
                              "border-style: outset;}"  # 平时向外凹陷，按下时向内凹陷
                              "QPushButton:pressed{background-color:rgb(85, 170, 255);border - style: inset;}"
                              )
        button2.setFont(QFont("Roman times", 18, QFont.Bold))
        button2.setStyleSheet("QPushButton{background-color:#87CEEB; color: #FFFFFF;"  # 天蓝色背景白色字体
                              "border:2px groove gray;border-radius:10px;padding:2px 4px;"  # 圆角按钮
                              "border-style: outset;}"  # 平时向外凹陷，按下时向内凹陷
                              "QPushButton:pressed{background-color:rgb(85, 170, 255);border - style: inset;}"
                              )
        # 设置扫码区域的按钮
        # self.button_setMainArea.setMinimumHeight(int(self.rect().height() / 9))
        self.button_setMainArea.setStyleSheet("QPushButton{background-color:#87CEEB; color: #FFFFFF;"  # 天蓝色背景白色字体
                                              "border:2px groove gray;border-radius:10px;padding:2px 4px;"  # 圆角按钮
                                              "border-style: outset;}"  # 平时向外凹陷，按下时向内凹陷
                                              "QPushButton:pressed{background-color:rgb(85, 170, 255);border - style: inset;}"
                                              )
        self.button_setMainArea.setFont(QFont("Roman times", 18, QFont.Bold))
        self.button_setMainArea.setCheckable(True)
        self.button_setMainArea.setFixedSize(155, 40)
        self.button_setMainArea.clicked.connect(self.setMainArea)
        # 设置打包区域的按钮
        # self.button_setExitArea.setMinimumHeight(int(self.rect().height() / 9))
        self.button_setExitArea.setStyleSheet("QPushButton{background-color:#87CEEB; color: #FFFFFF;"  # 天蓝色背景白色字体
                                              "border:2px groove gray;border-radius:10px;padding:2px 4px;"  # 圆角按钮
                                              "border-style: outset;}"  # 平时向外凹陷，按下时向内凹陷
                                              "QPushButton:pressed{background-color:rgb(85, 170, 255);border - style: inset;}"
                                              )
        self.button_setExitArea.setFont(QFont("Roman times", 18, QFont.Bold))
        self.button_setExitArea.setCheckable(True)
        self.button_setExitArea.setFixedSize(155, 40)
        self.button_setExitArea.clicked.connect(self.setExitArea)


        # 底部提示扫码后放在打包区的控件
        self.bottom_placeholder.setStyleSheet(
            "QLabel{color:rgb(0,0,0,250);font-size:24px;font-weight:bold;font-family:Roman times;}"
            "QLabel:hover{color:rgb(255,0,0,255);}")
        self.bottom_placeholder.setAlignment(Qt.AlignCenter)
        self.bottom_placeholder.setFixedSize(640, 160)

        # 控件布局设计：QGridLayout
        main_layout = QGridLayout(self)  # 整体使用网格布局

        main_layout.addWidget(self.label_show_item, 0, 0, 18, 18)
        main_layout.addWidget(self.label_item_info, 0, 18, 18, 18)
        main_layout.addWidget(self.button1, 18, 0, 5, 9)
        main_layout.addWidget(button2, 18, 9, 5, 9)
        main_layout.addWidget(self.button_setMainArea, 18, 18, 5, 9)
        main_layout.addWidget(self.button_setExitArea, 18, 27, 5, 9)
        main_layout.addWidget(itemsCount, 23, 0, 5, 9)
        main_layout.addWidget(self.counts, 23, 9, 5, 9)
        main_layout.addWidget(betaCheck, 23, 18, 5, 9)
        main_layout.addWidget(self.betas, 23, 27, 5, 9)
        main_layout.addWidget(self.label_show_camera, 28, 0, 27, 36)
        main_layout.addWidget(self.bottom_placeholder, 55, 0, 9, 36)

        main_layout.setAlignment(Qt.AlignCenter)
        self.setLayout(main_layout)

        # 设置整个窗口的背景颜色为白色而不是默认的灰色
        bgColor = QPalette()
        bgColor.setColor(self.backgroundRole(), QColor(255, 255, 255))
        self.setPalette(bgColor)

    def keyPressEvent(self, keyEvent):
        if keyEvent.key() == Qt.Key_Escape:
            print(keyEvent.key())
            self.close()
        elif self.ready_for_input:  # 只允许输入"数字"和"回车"
            if keyEvent.key() == Qt.Key_Return:
                stringer = ''.join(self.keyList)
                self.scanned_items.append(stringer)  # 记录已经扫到的条形码，用于最后付款时统一显示
                #print(stringer)
                # 检索条形码，若存在对应图片则显示
                self.bottom_placeholder.setText('请将商品放在右侧打包区域，否则无法继续!')
                item_imgfile = look_up_table[stringer][0]
                if item_imgfile:
                    item = cv2.imread(item_imgfile, -1)
                    item = cv2.cvtColor(item, cv2.COLOR_BGR2RGB)
                    bytesPerline = 3 * item.shape[1]
                    item_img = QImage(item.data, item.shape[1], item.shape[0], bytesPerline, QImage.Format_RGB888)  # 存入格式为R, G, B 对应 0,1,2
                    item_img = QPixmap.fromImage(item_img).scaled(self.label_show_item.rect().width(), self.label_show_item.rect().height())
                    self.label_show_item.setPixmap(item_img)  # 显示商品图片
                    self.label_show_item.setScaledContents(True)  # 图片自适应控件大小

                    # 累计当前顾客的所有已扫商,显示在self.label_item_info上
                    scanned_item_counts = defaultdict(int)
                    for item in self.scanned_items:
                        print('item: ', item)
                        scanned_item_counts[item] += 1
                    self.items_info = ''  # 用于显示的临时变量？
                    for item in scanned_item_counts:
                        self.items_info += '\n  ' + look_up_table[item][1] + ' x ' + str(scanned_item_counts[item])
                    print('items_info: ', self.items_info)
                    self.label_item_info.setText(self.items_info)

                    # self.label_item_info.setText('\n  '+look_up_table[stringer][1])  # 显示商品信息
                self.counts.setText(str(int(self.counts.text()) + 1))  # 已扫商品计数加1
                self.finished_signal = 1  # 表示一次扫码结束，可以清空。
                self.ready_for_input = 0  # 接收到一个回车信号，说明一个码输入结束，如果没有清空就又输入一个码，会导致结果错误（两个码连在一起了），所以要等清空再置为1
            else:  # 若输入的是数字,后期可以进一步增加约束，限制只能输入数字
                # print(chr(keyEvent.key()))  # 显示键盘输入
                # 判断是否已经存储了一个码,如果当前keyList的长度超过了13,再往里输入就一定会出错,
                # 这种情况下,即keyList长度超过13还运行到了这里想要继续输入,说明是其他某个地方逻辑出错,
                # 那么这里就进行一次硬校正,强行将之前keyList已经存储的一个条形码的(13位)数字清空,为新的输入腾出地方
                if len(self.keyList) > 13:
                    self.keyList.clear()
                self.keyList.append(chr(keyEvent.key()))
                self.worker.digits = ''.join(self.keyList)


    # 第一个按钮：开始结账/确认付款
    def work(self, pressed):
        if self.button1.isChecked():  # button1按键按下
            # print('in pressed checked? ', self.button1.isChecked())
            self.button1.setText('确认付款')
            self.worker.lock = 0  # 解锁backend状态机的锁
            if self.start_up == 1:  # 开机后首次点击"开始结账"
                self.ready_for_input = 1  # 解开扫码器输入的锁（其实扫码器一直在输入，只是有没有存起来预备处理）
                # 切换显示画面为“请稍候…”
                wait = cv2.imread('./icons/plzwait.jpg', -1)
                height, width, channel = wait.shape
                bytesPerline = 3 * width
                wait = QImage(wait.data, width, height, bytesPerline, QImage.Format_RGB888).rgbSwapped()

                widget_width = self.label_show_camera.width()
                widget_height = self.label_show_camera.height()
                wait = QPixmap.fromImage(wait).scaled(widget_width, widget_height)
                self.label_show_camera.setPixmap(wait)
                # 实现业务线程的信号和槽机制
                self.worker.call_todo.connect(self.worker.start)
                self.worker.call_todo.emit()
                self.worker.trigger.connect(self.showFrame)  # 每处理完一帧，打印
                self.worker.clear.connect(self.clearScannedDigits)
                self.start_up = 0
            elif not len(self.items_info):  # 一次完整的付款（注意不是扫码）流程后点击“开始结账” 【这里的len永远是0啊！】
                # 如果没有扫码商品记录,运行到这里说明不是点击"确认付款"后反悔的(执行了该方法的最后一个else)
                # 而是开始了一次新的扫码过程(不是开机后首次)
                self.ready_for_input = 1  # 解开扫码器输入的锁（其实扫码器一直在输入，只是有没有存起来预备处理）
                print('here: ', self.ready_for_input)
                self.label_item_info.setText('\n  请将选购的商品放在左侧待扫区')
                self.label_show_item.setPixmap(self.ready_img)
        else:  # button1按键弹起
            # 首先要判断状态机是否在状态0，即所有已商品是否已经放在了打包区，如果扫了码没放在打包区则不允许结账
            # ready_for_input == 0说明刚刚成功扫了一个码
            if (self.worker.machine_state != 0) & (self.ready_for_input == 0):
                # 给一个警告框
                pay_warner = QMessageBox()
                pay_warner.setWindowTitle("现在无法付款")
                pay_warner.setIcon(QMessageBox.Warning)
                pay_warner.setText("请将所有商品放在打包区域以继续付款！ Flag："+str(self.worker.machine_state))
                pay_warner.addButton(QMessageBox.Ok)
                pay_warner.exec()
                # 按键重新按下，继续扫码流程，重新执行一遍work函数, 但既不是self.start_up == 1也不是not len(self.items_info)，
                # 而是len(self.items_info) != 0的一条隐含分支（本方法最下面的一条含setChecked的else分支同样会重新执行self.work到这条隐含分支），
                # 这条隐含分支就是，不改变self.ready_for_input的状态，这样已经扫了码但还没有完成一次完整扫码流程的话就不允许中途再输入，
                # 而完成扫码流程点击确认付款又取消想继续扫码的ready_for_input=1的状态也不会变；其他各种控件状态也都维持不变
                self.button1.setChecked(True)  # 这一步非常关键，将按键重新按下(checked)
                self.work(True)
            else:  # 状态机状态为0的时候可以放心付款（如果有误触发使状态机的flag=1就没法付款了，所以，这么做可能有隐患）
                self.button1.setText('开始结账')
                messageBox = QMessageBox()
                messageBox.setWindowTitle('确认付款')
                if int(self.betas.text()) == 0:
                    messageBox.setText('已完成所有商品扫码，确认付款吗？')
                else:
                    messageBox.setText('请检查您在打包区域的商品是否为'+self.counts.text() +
                                       '件' + '，确认付款吗？')
                messageBox.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
                buttonY = messageBox.button(QMessageBox.Yes)
                buttonY.setText('是的')
                buttonN = messageBox.button(QMessageBox.No)
                buttonN.setText('没有')
                messageBox.exec_()
                if messageBox.clickedButton() == buttonY:
                    # 按下"确认付款"时先把状态机和键盘输入锁上再说
                    self.worker.lock = 1  # 先把状态机锁上
                    self.ready_for_input = 0  # 把扫码器也锁上，避免非结账期间的乱扫
                    # 汇总结算信息
                    items_info = '\n  应付总额： [' + str(self.price_sum) + ']元'  # 显示商品价格详情
                    scanned_item_counts = defaultdict(int)
                    for item in self.scanned_items:
                        print('item: ', item)
                        scanned_item_counts[item] += 1
                    for item in scanned_item_counts:
                        items_info += '\n  ' + look_up_table[item][1] + ' x ' + str(scanned_item_counts[item])
                    self.label_item_info.setText(items_info)  # 显示汇总的结算信息
                    self.label_show_item.setPixmap(self.ready_img)  # 商品小图也置为默认图
                    self.scanned_items = []
                    self.price_sum = 0  # 这就算结束一次购物了，默认付款成功，开始重新计算扫码商品总金额
                    self.counts.setText('0')  # 把已扫商品计数和漏扫商品计数都置为0
                    self.betas.setText('0')   # 把已扫商品计数和漏扫商品计数都置为0
                    self.previous_beta_checks = self.worker.b_checks
                    self.items_info = ''

                else:  # 点击了“确认付款”，却反悔了不想付款还要继续扫码
                    # (对话框弹出期间一旦扫码, 会捕捉到最后的回车,相当于选择了"没有",继续进行扫码)
                    self.button1.setChecked(True)  # 这一步非常关键，将按键重新按下(checked)
                    self.work(True)  # 然后重新执行一遍work函数,这也很重要，这样才能再次执行work的第一个if分支

    def showFrame(self):
        self.label_show_camera.setScaledContents(False)
        global IMG
        frame_height, frame_width, channel = IMG.shape
        bytesPerline = 3 * frame_width
        img = QImage(IMG.data, frame_width, frame_height, bytesPerline,
                     QImage.Format_RGB888).rgbSwapped()
        # 根据宽高比设置待显示图像的尺寸（使用QImage的scaled方法）
        widget_width = self.label_show_camera.width()
        widget_height = self.label_show_camera.height()
        frame_ratio = float(frame_width) / float(frame_height)
        widget_ratio = float(widget_width) / float(widget_height)
        if frame_ratio <= widget_ratio:
            adjusted_height = widget_height
            adjusted_width = int(widget_height * frame_ratio)
        else:  # frame_ratio >= widget_ratio
            adjusted_width = widget_width
            adjusted_height = int(widget_width / frame_ratio)
        img = QPixmap.fromImage(img).scaled(adjusted_width, adjusted_height)
        self.label_show_camera.setPixmap(img)


    def showBorder(self, pressed):
        if pressed:
            self.worker.show_border = 1
        else:
            self.worker.show_border = 0

    def setMainArea(self, pressed):
        global CORNERS
        if pressed:
            self.worker.set_main = 1
            CORNERS = [0, 0, 0, 0]
            self.button_setMainArea.setText('完成设置')
        else:
            self.worker.set_main = 0
            self.button_setMainArea.setText('扫码区域')

    def setExitArea(self, pressed):
        global CORNERS
        if pressed:
            self.worker.set_exit = 1
            CORNERS = [0, 0, 0, 0]
            self.button_setExitArea.setText('完成设置')
        else:
            self.worker.set_exit = 0
            self.button_setExitArea.setText('打包区域')

    def clearScannedDigits(self):  # 状态机完成一次扫码流程
        # 如果本次扫码失败,弹出对话框进行提示
        if self.worker.b_checks - self.previous_beta_checks > int(self.betas.text()):
            retry_img = cv2.imread('./icons/retry.jpg', -1)  # 显示“重刷”页面
            h, w, c = retry_img.shape
            retry_img = QImage(retry_img.data, w, h, 3*w, QImage.Format_RGB888).rgbSwapped()
            self.label_show_item.setPixmap(QPixmap.fromImage(retry_img))
            # 弹出警告对话框
            miss_warner = QMessageBox()
            miss_warner.setWindowTitle("警告:视频监控中")
            miss_warner.setIcon(QMessageBox.Warning)
            miss_warner.setText("扫码未成功,请重新扫码")
            miss_warner.addButton(QMessageBox.Ok)
            miss_warner.exec()
        # print('失败次数: ', self.worker.b_checks, self.previous_beta_checks)
        self.betas.setText(str(self.worker.b_checks - self.previous_beta_checks))
        # 如果本次成功扫到了一个条形码
        if self.finished_signal:
            stringer = ''.join(self.keyList)
            self.price_sum += look_up_table[stringer][2]  # 累加已扫码商品的总金额
            # self.scanned_items.append(stringer)  # 记录已经扫到的条形码，用于最后付款时统一显示
            # 执行清空操作和信号复位
            self.worker.digits = []
            self.keyList = []
            self.finished_signal = 0
            self.ready_for_input = 1
            self.bottom_placeholder.clear()


if __name__ == "__main__":
    print('parent thread ID: ', int(QThread.currentThreadId()))  # 打印主线程ID
    app = QApplication(sys.argv)
    example = Cashier()
    example.show()
    print('self.rect().width()', example.rect().width())
    print('self.rect().height()', example.rect().height())
    print('self.label_show_item.width()', example.label_show_item.width())
    print('self.label_show_item.height()', example.label_show_item.height())
    print('self.label_item_info.width()', example.label_item_info.width())
    print('self.label_item_info.height()', example.label_item_info.height())
    print('self.label_show_camera.width()', example.label_show_camera.width())
    print('self.label_show_camera.height()', example.label_show_camera.height())
    sys.exit(app.exec_())
