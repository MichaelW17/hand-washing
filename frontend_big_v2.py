# 01/13/2019: M.F. frontend_big.py, not returning washing/soaping/drying time in calling of lil_washer in class Worker
# 01/09/2019: M.F. frontend.py, use to show washing, soaping, drying altogether
import sys, os
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
import numpy as np
from backend_big import Washer  # 后端处理
import time
import cgitb
cgitb.enable(format='text')  # 显示多线程错误信息

# 全局变量
PAUSE = 0
STATE = -1  # 全局状态指示（防止后台计数器在非本状态时累加错误帧）
CLEAR_SIG = 0  # 用于清除lil_washer中的计时器，1时清除washing_time, 2时清除soaping_time，3清除drying_time

class ClearSig:  # 清零信号，写成一个类是为了方便跨线程调用（全局变量也能实现同样的功能），用于在Step2打肥皂之后将Step3冲洗时间置零
    CS = 0
# 将图像处理工作放在一个QObject子类中完成，用于QThread多线程实现
class Worker(QObject):

    call_todo = pyqtSignal(str, str, str, str)  # 用于触发worker的后台运行
    trigger = pyqtSignal()  # 每处理完一帧触发显示
    clear = pyqtSignal()    # 触发清空输入缓存的信号
    reset_CLEAR_SIG = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.global_frame = np.zeros((1024, 576, 3), dtype=np.uint8)
        self.sink_frame = np.zeros((500, 285, 3), dtype=np.uint8)
        self.dryer_frame = np.zeros((500, 285, 3), dtype=np.uint8)

    @pyqtSlot(str, str, str, str)  # 使signal-slot的绑定关系与moveToThread的先后顺序无关
    def start(self, global_path, sink_path, dryer_path, tmp_dir):
        '''
        :param global_path:
        :param sink_path:
        :param dryer_path:
        :param tmp_dir: 当前目录
        :return:
        '''
        print('subthread ID: ', int(QThread.currentThreadId()))  # 打印子线程号
        self.lil_washer = Washer(video_paths=[global_path, sink_path, dryer_path, tmp_dir])
        self.global_frame = np.zeros((1024, 576, 3), dtype=np.uint8)
        self.sink_frame = np.zeros((500, 285, 3), dtype=np.uint8)
        self.dryer_frame = np.zeros((500, 285, 3), dtype=np.uint8)
        self.video_end = 0
        # VIDEO_PATH = 'C:/Users/Minghao/Desktop/gopro1/TEST1.MP4'
        while 1:
            # 07/24/2019: 将状态机的flag信号添加到输出列表中:self.machine_state，目的是确保flag=0的时候才能确认付款
            global PAUSE
            if PAUSE == 1:
                print('a: ', id(PAUSE), '=', PAUSE)
                pass
            elif PAUSE == -1:  # actually, stop
                self.lil_washer.global_cap.release()
                self.lil_washer.sink_cap.release()
                self.lil_washer.dryer_cap.release()
                break
            elif PAUSE == 0:
                global CLEAR_SIG, STATE
                self.global_frame, self.sink_frame, self.dryer_frame, self.video_end = self.lil_washer.predict(CLEAR_SIG, STATE)
                self.trigger.emit()
                self.reset_CLEAR_SIG.emit()  # CLEAR_SIG的1值使用一次（将lil_washer.washing_time置零后）即置零

                if self.video_end:  # 视频播放到了最后一帧
                    self.lil_washer.video_end = 0
                    self.video_end = 0
                    self.frame_to_show = np.zeros((1024, 576, 3), dtype=np.uint8)
                    self.clear.emit()
                    print('ended phase 1')
                    break



class FrontEnd(QWidget):

    def __init__(self):
        super().__init__()
        self.videodir = 'C:/Users/Minghao/Desktop/Hi-gui-videos/'
        self.pass_index, self.fail_index = 0, 0  # 初始化用于索引上述列表的index
        self.initUI()

    def initUI(self):
        global STATE
        STATE = -1
        # 为图像处理建立后台线程
        self.workThread = QThread()
        self.workThread.start()
        self.worker = Worker()  # 例化一个worker对象
        self.worker.moveToThread(self.workThread)
        self.worker.trigger.connect(self.showFrame)  # 每处理完一帧，打印
        self.worker.clear.connect(self.restart)
        self.worker.call_todo.connect(self.worker.start)
        self.worker.reset_CLEAR_SIG.connect(self.reset_clear_sig)

        # 类内计时器初始化
        self.washing_time1 = 0
        self.washing_time2 = 0
        self.soaping_time = 0
        self.drying_time = 0

        # 以下是控件及其功能设计
        # 获取显示器分辨率
        self.desktop = QApplication.desktop()
        self.screenRect = self.desktop.screenGeometry()
        self.width = self.screenRect.width()  # 屏幕宽度
        self.height = self.screenRect.height()  # 屏幕高度

        pbar_w = 250
        pbar_h = 50
        self.setGeometry(60, 140, 1800, 800)
        self.setWindowTitle("洗手检测DEMO")
        self.setWindowIcon(QIcon('icons/Hi-logo.png'))

        self.label_show_global = QLabel()  # 整体画面
        self.label_show_global.setFixedSize(1024, 576)
        self.label_show_global.setScaledContents(True)

        self.label_show_sink = QLabel()  # 洗手池
        self.label_show_sink.setFixedSize(500, 285)
        self.label_show_sink.setScaledContents(True)

        self.label_show_dryer = QLabel()  # 烘干机
        self.label_show_dryer.setFixedSize(500, 285)
        self.label_show_dryer.setScaledContents(True)

        self.pbar1 = QProgressBar()  # 第1步冲水
        self.pbar1.setRange(0, 1000)
        self.pbar1.setFixedSize(pbar_w, pbar_h)
        self.pbar1.setTextVisible(False)
        self.pbar1.setStyleSheet("QProgressBar{background-color:#FFFFFF; color: #FFFFFF;"  # 天蓝色背景白色字体
                                "border:2px groove gray;border-radius:10px;padding:2px 4px;}"  # 圆角按钮
                                 "QProgressBar::chunk{background-color: #FFD700;}")  # 进度初始颜色为黄色

        self.pbar2 = QProgressBar()  # 第2步打洗手液
        self.pbar2.setRange(0, 1000)
        self.pbar2.setFixedSize(pbar_w, pbar_h)
        self.pbar2.setTextVisible(False)
        self.pbar2.setStyleSheet("QProgressBar{background-color:#FFFFFF; color: #FFFFFF;"  # 天蓝色背景白色字体
                                 "border:2px groove gray;border-radius:10px;padding:2px 4px;}"  # 圆角按钮
                                 "QProgressBar::chunk{background-color: #FFD700;}")  # 进度初始颜色为黄色

        self.pbar3 = QProgressBar()  # 第3步冲洗20s
        self.pbar3.setRange(0, 1000)
        self.pbar3.setFixedSize(pbar_w, pbar_h)
        self.pbar3.setTextVisible(False)
        self.pbar3.setStyleSheet("QProgressBar{background-color:#FFFFFF; color: #FFFFFF;"  # 天蓝色背景白色字体
                                 "border:2px groove gray;border-radius:10px;padding:2px 4px;}"  # 圆角按钮
                                 "QProgressBar::chunk{background-color: #FFD700;}")  # 进度初始颜色为黄色

        self.pbar4 = QProgressBar()  # 第4步冲洗烘干
        self.pbar4.setRange(0, 1000)
        self.pbar4.setFixedSize(pbar_w, pbar_h)
        self.pbar4.setTextVisible(False)
        self.pbar4.setStyleSheet("QProgressBar{background-color:#FFFFFF; color: #FFFFFF;"  # 天蓝色背景白色字体
                                 "border:2px groove gray;border-radius:10px;padding:2px 4px;}"  # 圆角按钮
                                 "QProgressBar::chunk{background-color: #FFD700;}")  # 进度初始颜色为黄色

        self.label_pbar1 = QLabel(self)
        self.label_pbar1.setFixedSize(pbar_w, pbar_h)
        self.label_pbar1.setFont(QFont("Arial", 18, QFont.Bold))
        self.label_pbar1.setAlignment(Qt.AlignCenter)
        # self.label_pbar1.setStyleSheet("border:2px solid blue;")
        self.label_pbar1.setText("一次冲洗")

        self.label_pbar2 = QLabel()
        self.label_pbar2.setFixedSize(pbar_w, pbar_h)
        self.label_pbar2.setFont(QFont("Roman times", 18, QFont.Bold))
        self.label_pbar2.setAlignment(Qt.AlignCenter)
        # self.label_pbar2.setStyleSheet("border:2px solid blue;")
        self.label_pbar2.setText("打洗手液")

        self.label_pbar3 = QLabel()
        self.label_pbar3.setFixedSize(pbar_w, pbar_h)
        self.label_pbar3.setFont(QFont("Roman times", 18, QFont.Bold))
        self.label_pbar3.setAlignment(Qt.AlignCenter)
        # self.label_pbar3.setStyleSheet("border:2px solid blue;")
        self.label_pbar3.setText("二次冲洗")

        self.label_pbar4 = QLabel()
        self.label_pbar4.setFixedSize(pbar_w, pbar_h)
        self.label_pbar4.setFont(QFont("Roman times", 18, QFont.Bold))
        self.label_pbar4.setAlignment(Qt.AlignCenter)
        # self.label_pbar4.setStyleSheet("border:2px solid blue;")
        self.label_pbar4.setText("充分烘干")

        self.label_state = QLabel()  # 显示整个流程是否达标
        self.label_state.setFixedSize(2*pbar_w+5, pbar_h)
        self.label_state.setFont(QFont("Roman times", 18, QFont.Bold))
        self.label_state.setAlignment(Qt.AlignCenter)
        self.label_state.setStyleSheet("border:2px solid blue; border-radius:10px; padding:2px 4px;")
        self.label_state.setText("Ready")

        self.button_nextpass = QPushButton("Next Pass")
        self.button_nextpass.clicked.connect(lambda: self.loadVideo(1))
        self.button_nextpass.setFixedSize(pbar_w, pbar_h)
        self.button_nextpass.setStyleSheet("QPushButton{background-color:#5F9EA0; color: #FFFFFF;"  # 天蓝色背景白色字体
                                           "border:2px groove gray;border-radius:10px;padding:2px 4px;"  # 圆角按钮
                                           "border-style: outset;}"  # 平时向外凹陷，按下时向内凹陷
                                           "QPushButton:pressed{background-color:rgb(176,196,222);border - style: inset;}"
                                           )
        self.button_nextpass.setFont(QFont("Roman times", 18, QFont.Bold))

        self.button_nextfail = QPushButton("Next Fail")
        self.button_nextfail.clicked.connect(lambda: self.loadVideo(2))
        self.button_nextfail.setCheckable(True)  # 设为可以按下和弹起的形式
        self.button_nextfail.setFixedSize(pbar_w, pbar_h)
        self.button_nextfail.setStyleSheet("QPushButton{background-color:#5F9EA0; color: #FFFFFF;"  # 天蓝色背景白色字体
                                           "border:2px groove gray;border-radius:10px;padding:2px 4px;"  # 圆角按钮
                                           "border-style: outset;}"  # 平时向外凹陷，按下时向内凹陷
                                           "QPushButton:pressed{background-color:rgb(176,196,222);border - style: inset;}"
                                           )
        self.button_nextfail.setFont(QFont("Roman times", 18, QFont.Bold))

        self.timer = QBasicTimer()

        # 控件布局设计
        video_layout = QVBoxLayout()  # 视频区域布局
        video_layout.addWidget(self.label_show_sink)
        video_layout.addStretch()
        video_layout.addWidget(self.label_show_dryer)
        video_layout.setAlignment(Qt.AlignCenter)

        pbar_layout = QHBoxLayout()  # 进度条区域布局
        pbar_layout.addWidget(self.pbar1)
        pbar_layout.addWidget(self.pbar2)
        pbar_layout.addWidget(self.pbar3)
        pbar_layout.addWidget(self.pbar4)

        label_pbar_layout = QHBoxLayout()
        label_pbar_layout.addWidget(self.label_pbar1)
        label_pbar_layout.addWidget(self.label_pbar2)
        label_pbar_layout.addWidget(self.label_pbar3)
        label_pbar_layout.addWidget(self.label_pbar4)

        button_layout = QVBoxLayout()  # 按钮通知区域布局
        button_sublayout = QHBoxLayout()
        button_layout.addWidget(self.label_state)
        button_sublayout.addWidget(self.button_nextpass)
        button_sublayout.addWidget(self.button_nextfail)
        button_layout.addLayout(button_sublayout)
        button_layout.setAlignment(Qt.AlignCenter)

        main_layout = QGridLayout()  # 整体使用网格布局
        main_layout.addWidget(self.label_show_global, 0, 0, 9, 16)
        main_layout.addLayout(video_layout, 0, 16, 9, 8)
        main_layout.addLayout(label_pbar_layout, 9, 0, 2, 16)
        main_layout.addLayout(pbar_layout, 11, 0, 2, 16)
        main_layout.addLayout(button_layout, 9, 16, 4, 8)

        main_layout.setAlignment(Qt.AlignCenter)
        self.setLayout(main_layout)

        self.showFrame()

        # 设置整个窗口的背景颜色为白色而不是默认的灰色
        self.bgColor = QPalette()
        self.bgColor.setColor(self.backgroundRole(), QColor(255, 255, 255))
        self.setPalette(self.bgColor)

    # 开始后台线程（视频处理）
    def work(self):
        global PAUSE
        PAUSE = 0
        self.timer.start(100, self)
        self.worker.call_todo.emit(self.global_video, self.sink_video, self.dryer_video, self.tmpdir)
        time.sleep(0.1)

    def reset_clear_sig(self):
        global CLEAR_SIG
        CLEAR_SIG = 0
        ClearSig.CS = 0

    # 视频开始时STATE=0代表step1未完成，1代表已完成step1未完成step2...-1代表4个step全部完成，在选择下一段视频前保持-1
    def timerEvent(self, event):
        global STATE, CLEAR_SIG
        if STATE == 0:  # 处于第一步冲洗流程
            if self.worker.lil_washer.washing_time <= 1:  # 这里的2单位是s
                self.washing_time1 = self.worker.lil_washer.washing_time * 1000  # 进度条最大值为1000
                self.label_state.setText("请用清水打湿双手")
                self.label_state.setStyleSheet("background-color:#FFD700; color: #556B2F; border-radius:10px; padding:2px 4px;")
            else:
                self.washing_time1 = 1000
                self.label_state.setText("请打洗手液并充分揉搓")
                STATE = 1  # 进入step2: 打洗手液
                self.pbar1.setStyleSheet("QProgressBar{background-color:#FFFFFF; color: #FFFFFF;"  # 天蓝色背景白色字体
                                         "border:2px groove gray;border-radius:10px;padding:2px 4px;}"  # 圆角按钮
                                         "QProgressBar::chunk{background-color: #7FFF00;}")  # 一个进度条读满则变绿
            self.pbar1.setValue(self.washing_time1)

        elif STATE == 1:  # 处于step2打洗手液流程
            if self.worker.lil_washer.soaping_time <= 0.5:  # 充分出现泡沫1s即可
                self.soaping_time = self.worker.lil_washer.soaping_time * 2000
                self.label_state.setStyleSheet("background-color:#FFD700; color: #556B2F; border-radius:10px; padding:2px 4px;")
            else:  # overll_state=1且soaping_time>2,说明打洗手液完成可以进行step3
                self.soaping_time = 1000
                self.label_state.setText("请用清水冲洗20秒")
                STATE = 2  # 进入step3: 冲洗20s
                # washing_time清零信号
                ClearSig.CS = 1
                CLEAR_SIG = 1
                print('time reseting...')
                # self.worker.lil_washer.washing_time = 0  # step3开始前将washing_time中的step1洗手累积时间置零
                # 【如果可以直接穿透两层控制lil_washer属性的话，worker里就没必要作为返回值多加一层了】直接跨线程写变量，不安全
                self.pbar2.setStyleSheet("QProgressBar{background-color:#FFFFFF; color: #FFFFFF;"  # 天蓝色背景白色字体
                                         "border:2px groove gray;border-radius:10px;padding:2px 4px;}"  # 圆角按钮
                                         "QProgressBar::chunk{background-color: #7FFF00;}")  # 进度初始颜色为黄色
            self.pbar2.setValue(self.soaping_time)

        elif STATE == 2:  # 处于step3冲洗20s流程
            if self.worker.lil_washer.washing_time <= 10:  # 冲洗10s即达标
                self.washing_time2 = self.worker.lil_washer.washing_time * 100
                self.label_state.setStyleSheet("background-color:#FFD700; color: #556B2F; border-radius:10px; padding:2px 4px;")
            else:
                self.washing_time2 = 1000
                self.label_state.setText("请烘干双手")
                STATE = 3  # 进入step3: 冲洗20s
                self.pbar3.setStyleSheet("QProgressBar{background-color:#FFFFFF; color: #FFFFFF;"  # 天蓝色背景白色字体
                                         "border:2px groove gray;border-radius:10px;padding:2px 4px;}"  # 圆角按钮
                                         "QProgressBar::chunk{background-color: #7FFF00;}")  # 进度初始颜色为黄色
            self.pbar3.setValue(self.washing_time2)

        elif STATE == 3:  # 处于step4烘干10s流程
            if self.worker.lil_washer.drying_time <= 10:  # 烘干10s即达标
                self.drying_time = self.worker.lil_washer.drying_time * 100
                self.label_state.setStyleSheet("background-color:#FFD700; color: #556B2F; border-radius:10px; padding:2px 4px;")
            else:
                self.drying_time = 1000
                STATE = -1  # 载入下一段视频之前进入结束状态-1
                self.pbar4.setStyleSheet("QProgressBar{background-color:#FFFFFF; color: #FFFFFF;"  # 天蓝色背景白色字体
                                         "border:2px groove gray;border-radius:10px;padding:2px 4px;}"  # 圆角按钮
                                         "QProgressBar::chunk{background-color: #7FFF00;}")  # 进度初始颜色为黄色
                self.label_state.setText("通过！")
                self.label_state.setStyleSheet("background-color:#7FFF00; color: #556B2F; border-radius:10px; padding:2px 4px;")  # 流程完成，状态框变绿
            self.pbar4.setValue(self.drying_time)

        # else:  # STATE=-1说明程序第一次执行或刚播完一段视频，还未载入新的视频分组
        #     pass

    def loadVideo(self, n):
        global PAUSE, STATE
        PAUSE = -1
        self.pbar1.setValue(0)
        self.pbar1.setStyleSheet("QProgressBar{background-color:#FFFFFF; color: #FFFFFF;"  # 天蓝色背景白色字体
                                 "border:2px groove gray;border-radius:10px;padding:2px 4px;}"  # 圆角按钮
                                 "QProgressBar::chunk{background-color: #FFD700;}")  # 进度初始颜色为黄色
        self.pbar2.setValue(0)
        self.pbar2.setStyleSheet("QProgressBar{background-color:#FFFFFF; color: #FFFFFF;"  # 天蓝色背景白色字体
                                 "border:2px groove gray;border-radius:10px;padding:2px 4px;}"  # 圆角按钮
                                 "QProgressBar::chunk{background-color: #FFD700;}")  # 进度初始颜色为黄色
        self.pbar3.setValue(0)
        self.pbar3.setStyleSheet("QProgressBar{background-color:#FFFFFF; color: #FFFFFF;"  # 天蓝色背景白色字体
                                 "border:2px groove gray;border-radius:10px;padding:2px 4px;}"  # 圆角按钮
                                 "QProgressBar::chunk{background-color: #FFD700;}")  # 进度初始颜色为黄色
        self.pbar4.setValue(0)
        self.pbar4.setStyleSheet("QProgressBar{background-color:#FFFFFF; color: #FFFFFF;"  # 天蓝色背景白色字体
                                 "border:2px groove gray;border-radius:10px;padding:2px 4px;}"  # 圆角按钮
                                 "QProgressBar::chunk{background-color: #FFD700;}")  # 进度初始颜色为黄色

        time.sleep(0.1)
        if n == 1:
            passdirs = os.listdir(self.videodir + 'pass/')
            # passdirs.sort()  # 选择下一组视频时，不再顺序循环，而是随机选择目录下的一组
            pass_count = len(passdirs)
            self.pass_index = np.random.randint(1, pass_count + 1)  # randint左闭右开
            self.tmpdir = self.videodir + 'pass/' + passdirs[self.pass_index]

            self.global_video = self.tmpdir + '/global.mp4'
            self.sink_video = self.tmpdir + '/sink.mp4'
            self.dryer_video = self.tmpdir + '/dryer.mp4'
            # self.pass_index = (self.pass_index + 1) if (self.pass_index < len(passdirs) - 1) else 0  # 循环播放各个文件夹

        if n == 2:
            faildirs = os.listdir(self.videodir + 'fail/')
            # faildirs.sort()
            fail_count = len(faildirs)
            self.fail_index = np.random.randint(1, fail_count + 1)
            self.tmpdir = self.videodir + 'fail/' + faildirs[self.fail_index]

            # self.fail_index = (self.fail_index + 1) if (self.fail_index < len(faildirs) - 1) else 0  # 循环播放各个文件夹
            self.global_video = self.tmpdir + '/global.mp4'
            self.sink_video = self.tmpdir + '/sink.mp4'
            self.dryer_video = self.tmpdir + '/dryer.mp4'

        PAUSE = 0
        STATE = 0  # 每次载入新的视频分组，整体状态归0，等待第一步冲洗完成
        self.work()


    def keyPressEvent(self, keyEvent):
        global PAUSE
        if keyEvent.key() == Qt.Key_Escape:
            print(keyEvent.key())
            self.close()
        elif keyEvent.key() == Qt.Key_P:  # 按下P键暂停/继续
            PAUSE = PAUSE ^ 1  # 异或1->0, 0->1
        elif keyEvent.key() == Qt.Key_Q:  # 按下Q键停止当前视频
            PAUSE = -1

    def showFrame(self):
        GLOBAL_IMG = self.worker.global_frame
        SINK_IMG = self.worker.sink_frame
        DRYER_IMG = self.worker.dryer_frame
        global_height, global_width, channel = GLOBAL_IMG.shape
        sink_height, sink_width, channel = SINK_IMG.shape
        global_img = QImage(GLOBAL_IMG.data, global_width, global_height, 3 * global_width, QImage.Format_RGB888).rgbSwapped()
        sink_img = QImage(SINK_IMG.data, sink_width, sink_height, 3 * sink_width, QImage.Format_RGB888).rgbSwapped()
        dryer_img = QImage(DRYER_IMG.data, sink_width, sink_height, 3 * sink_width, QImage.Format_RGB888).rgbSwapped()
        # 根据宽高比设置待显示图像的尺寸（使用QImage的scaled方法）
        big_width = self.label_show_global.width()
        big_height = self.label_show_global.height()
        big_frame_ratio = float(global_width) / float(global_height)
        big_widget_ratio = float(big_width) / float(big_height)
        if big_frame_ratio <= big_widget_ratio:
            adjusted_height_big = big_height
            adjusted_width_big = int(big_height * big_frame_ratio)
        else:  # frame_ratio >= widget_ratio
            adjusted_width_big = big_width
            adjusted_height_big = int(big_width / big_frame_ratio)
        global_img = QPixmap.fromImage(global_img).scaled(adjusted_width_big, adjusted_height_big)
        self.label_show_global.setPixmap(global_img)

        lil_width = self.label_show_global.width()
        lil_height = self.label_show_global.height()
        lil_frame_ratio = float(sink_width) / float(sink_height)
        lil_widget_ratio = float(lil_width) / float(lil_height)
        if lil_frame_ratio <= lil_widget_ratio:
            adjusted_height_lil = lil_height
            adjusted_width_lil = int(lil_height * lil_frame_ratio)
        else:  # frame_ratio >= widget_ratio
            adjusted_width_lil = lil_width
            adjusted_height_lil = int(lil_width / lil_frame_ratio)
        sink_img = QPixmap.fromImage(sink_img).scaled(adjusted_width_lil, adjusted_height_lil)
        dryer_img = QPixmap.fromImage(dryer_img).scaled(adjusted_width_lil, adjusted_height_lil)

        self.label_show_sink.setPixmap(sink_img)
        self.label_show_dryer.setPixmap(dryer_img)

    def restart(self):  # 当前视频播放完毕，重播一遍
        global STATE
        print('ended phase 2')
        self.showFrame()
        if STATE != -1:
            self.label_state.setText("不通过！")  # 视频结束，如果不通过，状态框变红
            self.label_state.setStyleSheet("background-color:#FF6A6A; color: #FFFFFF; border-radius:10px; padding:2px 4px;")
            if self.washing_time1 < 1000:  # 第一步不成功，第1个进度条和后面3个进度条背景都要变红
                self.pbar1.setStyleSheet("QProgressBar{background-color:#FF6A6A; color: #FFFFFF;"  # 天蓝色背景白色字体
                                         "border:2px groove gray;border-radius:10px;padding:2px 4px;}")  # 进度初始颜色为黄色
                self.pbar2.setStyleSheet("QProgressBar{background-color:#FF6A6A; color: #FFFFFF;"  # 天蓝色背景白色字体
                                         "border:2px groove gray;border-radius:10px;padding:2px 4px;}")  # 进度初始颜色为黄色
                self.pbar3.setStyleSheet("QProgressBar{background-color:#FF6A6A; color: #FFFFFF;"  # 天蓝色背景白色字体
                                         "border:2px groove gray;border-radius:10px;padding:2px 4px;}")  # 进度初始颜色为黄色
                self.pbar4.setStyleSheet("QProgressBar{background-color:#FF6A6A; color: #FFFFFF;"  # 天蓝色背景白色字体
                                         "border:2px groove gray;border-radius:10px;padding:2px 4px;}")  # 进度初始颜色为黄色
            if self.soaping_time < 1000:  # 第一步不成功，第1个进度条和后面3个进度条背景都要变红
                self.pbar2.setStyleSheet("QProgressBar{background-color:#FF6A6A; color: #FFFFFF;"  # 天蓝色背景白色字体
                                         "border:2px groove gray;border-radius:10px;padding:2px 4px;}")  # 进度初始颜色为黄色
                self.pbar3.setStyleSheet("QProgressBar{background-color:#FF6A6A; color: #FFFFFF;"  # 天蓝色背景白色字体
                                         "border:2px groove gray;border-radius:10px;padding:2px 4px;}")  # 进度初始颜色为黄色
                self.pbar4.setStyleSheet("QProgressBar{background-color:#FF6A6A; color: #FFFFFF;"  # 天蓝色背景白色字体
                                         "border:2px groove gray;border-radius:10px;padding:2px 4px;}")  # 进度初始颜色为黄色
            if self.washing_time2 < 1000:  # 第一步不成功，第1个进度条和后面3个进度条背景都要变红
                self.pbar3.setStyleSheet("QProgressBar{background-color:#FF6A6A; color: #FFFFFF;"  # 天蓝色背景白色字体
                                         "border:2px groove gray;border-radius:10px;padding:2px 4px;}")  # 进度初始颜色为黄色
                self.pbar4.setStyleSheet("QProgressBar{background-color:#FF6A6A; color: #FFFFFF;"  # 天蓝色背景白色字体
                                         "border:2px groove gray;border-radius:10px;padding:2px 4px;}")  # 进度初始颜色为黄色
            if self.drying_time < 1000:  # 第一步不成功，第1个进度条和后面3个进度条背景都要变红
                self.pbar4.setStyleSheet("QProgressBar{background-color:#FF6A6A; color: #FFFFFF;"  # 天蓝色背景白色字体
                                         "border:2px groove gray;border-radius:10px;padding:2px 4px;}")  # 进度初始颜色为黄色
        self.repaint()
        time.sleep(2)
        # self.pbar1.setValue(0)
        self.pbar1.setStyleSheet("QProgressBar{background-color:#FFFFFF; color: #FFFFFF;"  # 天蓝色背景白色字体
                                 "border:2px groove gray;border-radius:10px;padding:2px 4px;}"  # 圆角按钮
                                 "QProgressBar::chunk{background-color: #FFD700;}")  # 进度初始颜色为黄色
        # self.pbar2.setValue(0)
        self.pbar2.setStyleSheet("QProgressBar{background-color:#FFFFFF; color: #FFFFFF;"  # 天蓝色背景白色字体
                                 "border:2px groove gray;border-radius:10px;padding:2px 4px;}"  # 圆角按钮
                                 "QProgressBar::chunk{background-color: #FFD700;}")  # 进度初始颜色为黄色
        # self.pbar3.setValue(0)
        self.pbar3.setStyleSheet("QProgressBar{background-color:#FFFFFF; color: #FFFFFF;"  # 天蓝色背景白色字体
                                 "border:2px groove gray;border-radius:10px;padding:2px 4px;}"  # 圆角按钮
                                 "QProgressBar::chunk{background-color: #FFD700;}")  # 进度初始颜色为黄色
        # self.pbar4.setValue(0)
        self.pbar4.setStyleSheet("QProgressBar{background-color:#FFFFFF; color: #FFFFFF;"  # 天蓝色背景白色字体
                                 "border:2px groove gray;border-radius:10px;padding:2px 4px;}"  # 圆角按钮
                                 "QProgressBar::chunk{background-color: #FFD700;}")  # 进度初始颜色为黄色
        # self.label_state.setText("请用清水打湿双手")
        # self.label_state.setStyleSheet("background-color:#FFD700; color: #556B2F; border-radius:10px; padding:2px 4px;")
        STATE = 0
        self.pbar1.setValue(0)
        self.pbar2.setValue(0)
        self.pbar3.setValue(0)
        self.pbar4.setValue(0)
        self.worker.call_todo.emit(self.global_video, self.sink_video, self.dryer_video, self.tmpdir)


if __name__ == "__main__":
    print('parent thread ID: ', int(QThread.currentThreadId()))  # 打印主线程ID
    app = QApplication(sys.argv)
    example = FrontEnd()
    example.show()
    sys.exit(app.exec_())

