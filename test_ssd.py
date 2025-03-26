'''
Created on 30 Jul 2024

@author: andre.louw
'''
import os
import cv2
from ssd import CaffeModelLoader, FrameProcessor, SSD, Utils

im_name = "humanright"
im_dir = "./images"
im_path = os.path.join(im_dir, f"{im_name}.png")
res_dir = "./images/result"
res_path = os.path.join(res_dir, f"{im_name}.png")

proto_file = "./MobileNetSSD_deploy.prototxt"
model_file = "./MobileNetSSD_deploy.caffemodel"
ssd_net = CaffeModelLoader.load(proto_file, model_file)
print("Caffe model loaded from: "+model_file)
 
proc_frame_size = 300
# frame processor for MobileNet
ssd_proc = FrameProcessor(proc_frame_size, 1.0/127.5, 127.5)
person_class = 15
 
ssd = SSD(ssd_proc, ssd_net)
 
image = cv2.imread(im_path)
print("Image read from: "+im_path)
 
obj_data = ssd.detect(image)
persons = ssd.get_objects(image, obj_data, person_class, 0.1)
person_count = len(persons)
print("Person count on the image: "+str(person_count))
Utils.draw_objects(persons, "PERSON", (0, 0, 255), image)
 
cv2.imwrite(res_path, image)
print("Result written to: "+res_path)
