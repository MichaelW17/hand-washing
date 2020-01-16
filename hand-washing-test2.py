# 01/13/2019: M.F. hand-washing-test1.py，使用三合一模型检测含有完整洗手流程（前三步）的视频
# 12/30/2019: use the trained hand-washing detection model to predict on a test video

from keras.models import load_model

from os import listdir
import imghdr
import os, random
import numpy as np
from keras.layers import Dense,Dropout,Flatten,Conv2D,MaxPooling2D,Reshape,Activation
from keras.models import Model
from keras.utils import np_utils

from keras import optimizers, metrics
from efficientnet import EfficientNetB5
from PIL import Image
from keras.callbacks import ModelCheckpoint
import time
import cv2

VIDEO_PATH = 'C:/Users/Minghao/Desktop/showoff/GH010379.MP4'
video_save_path = 'C:/Users/Minghao/Desktop/showoff/GH010379_pred3in1.mp4'
# model = load_model('C:/Users/Minghao/Desktop/Models/soap/0107-2classes-soap-39.h5')
model = load_model('C:/Users/Minghao/Desktop/0113-4classes-merge-25.h5')
# model = load_model('C:/Users/Minghao/Desktop/Models/hand-washing/1231-2classes-wash-29.h5')
x_mean = np.full((456, 456, 3), (82, 79, 77.7), dtype=np.float32)  # soap: (62, 60, 59), others: (84.5, 82.47, 81.05)
video = cv2.VideoCapture(VIDEO_PATH)
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
output_video = cv2.VideoWriter(video_save_path, fourcc, 24.0, (1280, 720))
wait_time = 1
frameID = 0
skip_frame = 0
t0 = time.time()
fps = 0.0
npy_result = np.empty((1, 4))
while 1:
    success, frame = video.read()

    if success:
        frameID += 1
        print('frame ID: ', frameID)
        # frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image = cv2.resize(image, (456, 456), interpolation=cv2.INTER_AREA)
        image = np.expand_dims(image - x_mean, axis=0).astype('float32')
        pred = model.predict(image)
        #         print('pred: ', pred)
        pred = pred[0]
        result = np.argmax(pred)
        if result == 0:
            text = 'Nothing'
            score = pred[result]
            color = (255, 255, 255)
        elif result == 1:
            text = 'Washing'
            score = pred[result]
            color = (0, 0, 255)
        elif result == 2:
            text = 'soaping'
            score = pred[result]
            color = (0, 255, 0)
        elif result == 3:
            text = 'drying'
            score = pred[result]
            color = (255, 0, 0)
        # print('npy_result.shape: ', npy_result.shape, 'pred.shape: ', pred.shape)
        npy_result = np.append(npy_result, np.expand_dims(pred, 0), axis=0)  # np.append(a,b)要求a和b维度相同

        key_value = cv2.waitKey(wait_time)
        frame_to_save = cv2.resize(frame, (1280, 720))
        cv2.putText(frame_to_save, 'status: {} ({:.2f}), {} fps'.format(text, score, fps), (20, 70),
                    cv2.FONT_HERSHEY_SIMPLEX, 2, color, 3)
        cv2.imshow('TEST', frame_to_save)
        output_video.write(frame_to_save)
        wait_time = 0 if key_value == ord('s') else 1
        if key_value == 27:
            break
    else:
        if skip_frame < 20:
            print('pass this frame')
            skip_frame += 1
            continue
        else:
            break
    t1 = time.time()
    fps = round(1/((t1 - t0)/frameID), 1)

np.save(VIDEO_PATH.split('/')[-1].split('.')[0] + '.npy', npy_result)

cv2.destroyAllWindows()
video.release()
output_video.release()