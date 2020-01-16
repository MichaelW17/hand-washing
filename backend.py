'''
01/02/2019: 海底捞检测项目中，用于展示洗手检测结果的GUI后端，在线模型推理
'''

import imutils
import cv2
import numpy as np
from keras.models import load_model
from efficientnet import EfficientNetB5
model = load_model('C:/Users/Minghao/Desktop/Models/hand-washing/1231-2classes-wash-29.h5')
model._make_predict_function()

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

        # checker中一直在循环，以遍历视频的每一帧
    def predict(self):
        self.success, self.frame = self.video_cap.read()
        self.frameID += 1
        if self.success:
            print('frame ID: ', self.frameID)
            frame_rgb = cv2.cvtColor(self.frame, cv2.COLOR_BGR2RGB)
            image = cv2.resize(frame_rgb, (456, 456), interpolation=cv2.INTER_AREA)
            image = np.expand_dims(image - self.x_mean, axis=0).astype('float32')
            pred = model.predict(image)
            if pred[0][0] < pred[0][1]:  # 当前为洗手帧
                self.washing_time += 1/24
                print('washing time: ', self.washing_time)
            self.frame_to_show = cv2.resize(self.frame, (1024, 576))
        else:
            if self.skip_frame < 20:
                self.skip_frame += 1
            else:
                self.video_end = 1
                self.video_cap.release()

        return self.frame_to_show, self.washing_time, self.video_end




