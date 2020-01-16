# 将视频切割为图片
import numpy as np
import cv2

video_path_name = 'C:/Users/Minghao/Desktop/soap2/GH010367.MP4'
video_name = video_path_name.split('/')[-1].split('.')[0]
output_path = 'C:/Users/Minghao/Desktop/soap2/0/'
cap = cv2.VideoCapture(video_path_name)
ret, frame = cap.read()
frameID = 0
skip_frame = 0
while 1:
    ret, frame = cap.read()
    if ret:
        frameID += 1
        print('frame ID: ', frameID)
        image = frame
        cv2.imwrite(output_path + video_name + '-' + str(frameID).zfill(4) + '.jpg', image)
        # cv2.imshow(' ', image)
        key_value = cv2.waitKey(1)
        if key_value == 27:
            break
    else:
        # key_value = cv2.waitKey(0)
        if skip_frame < 50:
            print('pass this frame')
            skip_frame += 1
            continue
        else:
            break

cap.release()
cv2.destroyAllWindows()