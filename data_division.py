import cv2
import os
from shutil import copy

path = 'C:/Users/Minghao/Desktop/soap2/0/'
des = 'C:/Users/Minghao/Desktop/soap2/'
images = os.listdir(path)
print(images[0])

count = 0
for img in images:
    # print(img)
    if count == 20:
        count = 0
    if count < 19:
        copy(path + img, des + 'Train/00/' + img)
    elif count == 19:
        copy(path + img, des + 'Val/00/' + img)

    count = count + 1

