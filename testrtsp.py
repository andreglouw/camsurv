'''
Created on 17 Nov 2021

@author: andre.louw
'''
import cv2
import os
from datetime import datetime

RTSP_URL = 'rtsp://rtsp:12345678@10.0.0.101:554/av_stream/ch1'

os.environ['OPENCV_FFMPEG_CAPTURE_OPTIONS'] = 'rtsp_transport;udp'
 
cap = cv2.VideoCapture(RTSP_URL, cv2.CAP_FFMPEG)
#cap = cv2.VideoCapture(RTSP_URL)
 
if not cap.isOpened():
    print('Cannot open RTSP stream')
    exit(-1)
 
last_cap = None

while True:
    try:
        grabbed, frame = cap.read()
        if grabbed and not frame is None:
            if last_cap is None or (datetime.now() - last_cap).total_seconds() > 5:
                cv2.imshow('RTSP stream', frame)
                last_cap = datetime.now()
        else:
            print("empty frame")
     
        if cv2.waitKey(1) == 27:
            break
    except Exception as exc:
        print("Caught exception %s" % exc)
 
cap.release()
cv2.destroyAllWindows()