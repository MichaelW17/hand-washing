import cv2

import os
import time


cv2.namedWindow(' ', 256)

cap = cv2.VideoCapture(1)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

count = 0
while 1:

    ret, img = cap.read()

    WAITKEY= cv2.waitKey(1)
    if WAITKEY == ord('s'):
        cv2.imwrite('C:/Users/Minghao/Desktop/calib/'+str(time.time())+'.jpg', img)
        cv2.waitKey(1500)
        count = count + 1
        print(count)
    if WAITKEY == 27:
        cap.release()
        break
    cv2.resizeWindow(" ", 1280, 720)
    cv2.imshow(' ', img)
