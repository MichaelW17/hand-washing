'''
01/02/2019: 海底捞检测项目中，用于展示洗手检测结果的GUI后端
'''

import imutils
import cv2
import numpy as np
import time


class Washer:

    def __init__(self, video_path):
        # initialization
        self.video_cap = cv2.VideoCapture(video_path)
        self.frameID = 0
        self.washing_time = 0
        self.skip_frame = 0
        self.frame_to_show = np.zeros((1024, 576, 3))
        self.success, self.frame = self.video_cap.read()
        self.x_mean = np.full((456, 456, 3), (84.5, 82.47, 81.05), dtype=np.float32)
        self.video_end = 0
        self.pred = np.load('npys/' + video_path.split('/')[-1].split('.')[0].split('_')[0] + '.npy')
        print('npys/' + video_path.split('/')[-1].split('.')[0] + '.npy')

        # 加上一个简单的计数环节，滤除跳变帧: 3帧连续洗手才开始计时
        self.true_result = 0
        self.true_counter = 0
        self.false_result = 0
        self.false_counter = 0  # 连续没有洗手的帧计数


        # checker中一直在循环，以遍历视频的每一帧
    def predict(self):
        self.success, self.frame = self.video_cap.read()
        if self.success:
            self.frameID += 1
            # print('frame ID: ', self.frameID)
            pred = self.pred[self.frameID]

            if pred[0] < pred[1]:  # 当前为洗手帧
                if self.true_counter < 3:  # 状态切换为”洗手“的条件
                    self.true_counter += 1
                else:
                    self.true_result = 1
                    self.true_counter = 0
                if self.true_result:
                    self.washing_time += 1/24
                else:
                    self.true_counter += 1
            else:
                self.true_counter = 0
                self.true_result = 0


            self.frame_to_show = cv2.resize(self.frame, (1024, 576))
        else:
            if self.skip_frame < 20:
                self.skip_frame += 1
            else:
                self.video_end = 1
                self.video_cap.release()

        time.sleep(1/240)

        return self.frame_to_show, self.washing_time, self.video_end




