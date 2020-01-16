# 用于电子秤项目中计算origin文件夹下所有图片的三通道均值
import os
import numpy as np
from PIL import Image

# path = 'D:/Dataset/scale_qingdao/origin/'
path = 'C:/Users/Minghao/Desktop/soap/11/'

img_holder = np.zeros((1080, 1920, 3), dtype=np.float32)  # to add up all the image data
img_num = 0  # number of images accumulated

mydata = os.listdir(path)
for j in mydata:
    img_num += 1
    img = Image.open(path + j)
    img_holder += img

print('img_num: ', img_num)
img_holder = np.sum(img_holder, axis=(0,1)) / (1920*1080)
img_mean = img_holder / img_num
print(img_mean)
