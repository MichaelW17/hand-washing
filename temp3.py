import cv2

cap = cv2.VideoCapture('C:/Users/Minghao/Desktop/showoff0114/1/global.MP4')


skip_counter = 0
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
output_video = cv2.VideoWriter('C:/Users/Minghao/Desktop/showoff0114/1/global1.MP4', fourcc, 30.0, (1280, 720))
while 1:
    success, frame = cap.read()
    if success:
        frame = cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
        cv2.imshow(' ', frame)
        output_video.write(frame)
        keyv = cv2.waitKey(1)

        if keyv == 27:
            break
    elif skip_counter < 20:
        skip_counter += 1
        pass
    else:
        break

cv2.destroyAllWindows()
cap.release()
output_video.release()