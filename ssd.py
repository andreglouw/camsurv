'''
Created on 29 Jul 2024

@author: andre.louw
'''
import os
import cv2
import numpy as np

CLASSES = ["background", "aeroplane", "bicycle", "bird", "boat",
    "bottle", "bus", "car", "cat", "chair", "cow", "diningtable",
    "dog", "horse", "motorbike", "person", "pottedplant", "sheep",
    "sofa", "train", "tvmonitor"]

class Utils:    
    @staticmethod
    def draw_object(obj, label, color, frame):
        #(confidence, (x1, y1, w, h)) =  obj
        (confidence, obj_rect) =  obj
        print("Found at {}".format(str(obj_rect)))
        x2 = obj_rect.x + obj_rect.w
        y2 = obj_rect.y + obj_rect.h
        cv2.rectangle(frame, (obj_rect.x, obj_rect.y), (x2, y2), color, 2)
        y3 = obj_rect.y - 12
        text = label + " " + str(confidence)+"%"
        cv2.putText(frame, text, (obj_rect.x, y3), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 1, cv2.LINE_AA)
        
    @staticmethod
    def draw_objects(objects, label, color, frame):
        for (i, obj) in enumerate(objects):
            Utils.draw_object(obj, label, color, frame)
            
class CaffeModelLoader:
    @staticmethod
    def load(proto, model):
        net = cv2.dnn.readNetFromCaffe(proto, model)
        return net
 
class FrameProcessor:    
    def __init__(self, size, scale, mean):
        self.size = size
        self.scale = scale
        self.mean = mean
    
    def get_blob(self, frame, dx):
        (h, w, c) = frame.shape
        img = frame[0:h, dx:dx+h]  
        resized = cv2.resize(img, (self.size, self.size), cv2.INTER_AREA)
        blob = cv2.dnn.blobFromImage(resized, self.scale, (self.size, self.size), self.mean)
        return blob
        
    def get_bloblist(self, frame):
        bloblist = []
        (h, w, c) = frame.shape
        dx = 0
        bloblist.append([dx, self.get_blob(frame, dx)])
        dx = w-h
        bloblist.append([dx, self.get_blob(frame, dx)])
        return bloblist
        
class FrameRect:
    @staticmethod
    def perc_diff(this, other):
        this = 0 if this < 0 else this
        other = 0 if other < 0 else other
        diff = abs(this - other)
        return diff if diff == 0 else int((diff / ((this + other) / 2)) * 100)
        
    def __init__(self, x, y, w, h):
        self.x = x
        self.y = y
        self.w = w
        self.h = h

    def __str__(self):
        return f"rect: ({self.x}, {self.y}, {self.w}, {self.h})"
            
    def __eq__(self, other):
        print("Compare {} and {}".format(str(self), str(other)))
        xdiff = FrameRect.perc_diff(self.x, other.x)
        ydiff = FrameRect.perc_diff(self.y, other.y)
        wdiff = FrameRect.perc_diff(self.w, other.w)
        hdiff = FrameRect.perc_diff(self.h, other.h)
        print(f"xdiff: {xdiff}, ydiff: {ydiff}, wdiff: {wdiff}, hdiff: {hdiff}")
        return (xdiff < 10 and ydiff < 10 and wdiff < 10 and hdiff < 10)
    
class SSD:    
    def __init__(self, frame_proc, ssd_net):
        self.proc = frame_proc
        self.net = ssd_net
    
    def detect(self, frame):
        bloblist = self.proc.get_bloblist(frame)
        obj_data = []
        for dx,blob in bloblist:
            self.net.setInput(blob)
            detections = self.net.forward()
            # detected object count
            k = detections.shape[2]
            for i in np.arange(0, k):
                obj = detections[0, 0, i, :]
                obj_data.append([dx,obj])
            
        return obj_data
 
    def get_object(self, frame, data, dx):
        confidence = int(data[2]*100.0)
        (h, w, c) = frame.shape
        r_x = int(data[3]*h)+dx
        r_y = int(data[4]*h)
        r_w = int((data[5]-data[3])*h)
        r_h = int((data[6]-data[4])*h)
        obj_rect = FrameRect(r_x, r_y, r_w, r_h)
        return (confidence, obj_rect)
        
    def get_objects(self, frame, obj_data, classnames, min_confidence, previous_rects=[]):
        objects = []
        class_indexes = [CLASSES.index(classname) for classname in classnames]
        for (i, (dx, data)) in enumerate(obj_data):
            obj_class = int(data[1])
            obj_confidence = data[2]
            if obj_class in class_indexes and obj_confidence >= min_confidence :
                (confidence, obj_rect) = self.get_object(frame, data, dx)
                if not obj_rect in previous_rects:
                    objects.append((confidence, obj_rect))
                
        return objects
