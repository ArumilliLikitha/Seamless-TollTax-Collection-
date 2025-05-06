import numpy as np
import cv2
import LPR as lpr
cap = cv2.VideoCapture(8080)
while True:
    ret, frame = cap.read()
    if not ret:
        break
    plate_img = lpr.recognize_license_plate(frame)
    cv2.imshow('frame', plate_img)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break
cap.release()
cv2.destroyAllWindows()
