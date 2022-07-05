'''
Created on 19 Nov 2021

@author: andre.louw
'''
import cv2
import os
import queue
import time
import threading
q=queue.Queue()

#RTSP_URL = 'rtsp://hack:hack@10.0.0.101:554/av_stream/ch1'
#os.environ['OPENCV_FFMPEG_CAPTURE_OPTIONS'] = 'rtsp_transport;udp'
#cap = cv2.VideoCapture(RTSP_URL, cv2.CAP_FFMPEG)

def Receive():
    print("Start Receive")
    os.environ['OPENCV_FFMPEG_CAPTURE_OPTIONS'] = 'rtsp_transport;udp'
    cap = cv2.VideoCapture("rtsp://rtsp:Th3BetterRTSPPassw0rd@10.0.0.101:554/av_stream/ch1", cv2.CAP_FFMPEG)
    while True:
        ret, frame = cap.read()
        if not ret:
            st = time.time()
            cap = cv2.VideoCapture("rtsp://rtsp:Th3BetterRTSPPassw0rd@10.0.0.101:554/av_stream/ch1", cv2.CAP_FFMPEG)
            print("Time lost: ", time.time()-st)
            continue
        q.put(frame)
    print("Receive thread stopped")
    cap.release()


def Display():
    print("Start Displaying")
    while True:
        if q.empty() != True:
            frame = q.get()
            cv2.imshow("frame1", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    cv2.destroyAllWindows()
    print("Display thread stopped")

if __name__=='__main__':
    p1 = threading.Thread(target=Receive)
    p2 = threading.Thread(target=Display)
    p1.start()
    p2.start()
