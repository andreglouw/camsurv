'''
Created on 17 Nov 2021

@author: andre.louw
'''
import os
import cv2
import time
from datetime import datetime
from ssd import CaffeModelLoader, FrameProcessor, SSD, Utils

RTSP_URL = 'rtsp://admin:@L0uW2048@192.168.1.130/stream1'
res_dir = "./images/result"

proto_file = "./MobileNetSSD_deploy.prototxt"
model_file = "./MobileNetSSD_deploy.caffemodel"
ssd_net = CaffeModelLoader.load(proto_file, model_file)
print("Caffe model loaded from: "+model_file)
 
CONSIDER = ["person", "car"]

proc_frame_size = 300
# frame processor for MobileNet
ssd_proc = FrameProcessor(proc_frame_size, 1.0/127.5, 127.5)
person_class = 15
 
ssd = SSD(ssd_proc, ssd_net)
 
cap = cv2.VideoCapture(RTSP_URL)
 
if not cap.isOpened():
    print('Cannot open RTSP stream')
    exit(-1)

last_movement = None
previous_objects = []

while True:
    try:
        grabbed, frame = cap.read()
        if grabbed and not frame is None:
            if last_movement is None or (int(time.time()) - last_movement) > 1:
                obj_data = ssd.detect(frame)
                detected = ssd.get_objects(frame, obj_data, CONSIDER, 0.1, previous_objects)
                previous_objects = [obj_rect for (confidence, obj_rect) in detected]
                person_count = len(detected)
                if person_count > 0:
                    fname = datetime.strftime(datetime.now(), "%Y%m%d%H%M%S")
                    print("Count {} objects on the image {}".format(person_count, fname))
                    last_movement = int(time.time())
                    Utils.draw_objects(detected, "PERSON", (0, 0, 255), frame)
                    res_path = os.path.join(res_dir, f"{fname}.jpg")
                    cv2.imwrite(res_path, frame)
        else:
            print("empty frame")     
    except (KeyboardInterrupt) as exc:
        break
 
cap.release()
cv2.destroyAllWindows()