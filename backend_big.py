# 01/10/2020: M.F. backend_simple，用于配合frontend_big.py的后端，只有显示和读取npy功能

'''
01/02/2019: 海底捞检测项目中，用于展示洗手检测结果的GUI后端
'''

import imutils
import cv2
import numpy as np
import time


class Washer:

    def __init__(self, video_paths):
        # initialization

        self.frameID = 0
        self.washing_time = 0
        self.soaping_time = 0
        self.drying_time = 0
        self.skip_frame = 0

        self.global_frame_to_show = np.zeros((1024, 576, 3))
        self.sink_frame_to_show = np.zeros((500, 285, 3), dtype=np.uint8)
        self.dryer_frame_to_show = np.zeros((500, 285, 3), dtype=np.uint8)

        self.global_cap = cv2.VideoCapture(video_paths[0])
        self.sink_cap = cv2.VideoCapture(video_paths[1])
        self.dryer_cap = cv2.VideoCapture(video_paths[2])



        self.video_end = 0
        # self.pred = np.load('npys/' + video_paths.split('/')[-1].split('.')[0].split('_')[0] + '.npy')
        # print('npys/' + video_paths.split('/')[-1].split('.')[0] + '.npy')
        # self.pred = np.load('npys/GH010379.npy')
        self.pred1 = np.load(video_paths[3] + '/sink.npy')
        self.pred2 = np.load(video_paths[3] + '/dryer.npy')


        # 加上一个简单的计数环节，滤除跳变帧: 3帧连续洗手才开始计时
        self.wash_status = 0
        self.wash_counter = 0

        self.soap_status = 0
        self.soap_counter = 0

        self.dryer_status = 0
        self.dryer_counter = 0

        # checker中一直在循环，以遍历视频的每一帧
    def predict(self, clear_sig, STATE):  # clear_sig用于清除计时器，1时清除self.washing_time, 2时清除self.soaping_time，3清除drying_time
        self.success1, self.global_frame = self.global_cap.read()
        self.success2, self.sink_frame = self.sink_cap.read()
        self.success3, self.dryer_frame = self.dryer_cap.read()
        if clear_sig == 1:
            print('washing time force zero!')
            self.washing_time = 0
        if self.success1 and self.success2 and self.success3:
            self.frameID += 1
            # print('frame ID: ', self.frameID)
            pred1 = self.pred1[self.frameID]  # sink视频的检测结果
            result1 = np.argmax(pred1)  # 0: 负样本，1: 洗手，2: 洗手液，3: 烘干
            pred2 = self.pred2[self.frameID]  # dryer视频的检测结果
            result2 = np.argmax(pred2)

            # 洗手计时逻辑
            if result1 == 1:  # 当前为洗手帧
                if self.wash_counter < 3:  # 状态锁定为”洗手“的条件
                    self.wash_counter += 1
                else:
                    self.wash_status = 1
                    self.wash_counter = 0
                if self.wash_status:
                    self.washing_time += 1 / 30
                else:
                    self.wash_counter += 1
            else:  # 有一帧不是洗手，立马跳出洗手状态
                self.wash_counter = 0
                self.wash_status = 0

            # 打洗手液计时逻辑
            if (result1 == 2) and (STATE == 1) and (pred1[2] > 0.8):  # 当前为打洗手液帧
                if self.soap_counter < 3:  # 状态锁定”打洗手液“的条件
                    self.soap_counter += 1
                else:
                    self.soap_status = 1
                    self.soap_counter = 0
                if self.soap_status:
                    self.soaping_time += 1 / 30
                else:
                    self.soap_counter += 1
            else:  # 有一帧不是打洗手液，立马跳出该状态
                self.soap_counter = 0
                self.soap_status = 0

            # 烘干计时逻辑
            if (result2 == 3) and (STATE == 3) and (pred2[3] > 0.8):  # 当前为烘干帧
                if self.dryer_counter < 3:  # 状态锁定为”烘干“的条件
                    self.dryer_counter += 1
                else:
                    self.dryer_status = 1
                    self.dryer_counter = 0
                if self.dryer_status:
                    self.drying_time += 1 / 30
                else:
                    self.dryer_counter += 1
            else:  # 有一帧不是洗烘干，立马跳出烘干状态
                self.dryer_counter = 0
                self.dryer_status = 0


            self.global_frame_to_show = cv2.resize(self.global_frame, (1024, 576))
            self.sink_frame_to_show = cv2.resize(self.sink_frame, (500, 285))
            self.dryer_frame_to_show = cv2.resize(self.dryer_frame, (500, 285))

        else:
            if self.skip_frame < 20:
                self.skip_frame += 1
            else:
                self.video_end = 1
                self.washing_time = 0
                self.soaping_time = 0
                self.drying_time = 0
                self.global_cap.release()
                self.sink_cap.release()
                self.dryer_cap.release()

        time.sleep(1/240)

        return self.global_frame_to_show, self.sink_frame_to_show, self.dryer_frame_to_show, self.video_end




