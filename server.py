import sys
import argparse
import json
from camimage import camimage
import numpy
import cv2
import threading
import time
import importlib
import ssd
from datetime import datetime

# initialize the list of class labels MobileNet SSD was trained to
# detect, then generate a set of bounding box colors for each class
CLASSES = ["background", "aeroplane", "bicycle", "bird", "boat",
    "bottle", "bus", "car", "cat", "chair", "cow", "diningtable",
    "dog", "horse", "motorbike", "person", "pottedplant", "sheep",
    "sofa", "train", "tvmonitor"]
CONSIDER = set(["person", "car"])
COLORS = numpy.random.uniform(0, 255, size=(len(CLASSES), 3))

config = None

class FPS:
    def __init__(self):
        self._start = None
        self._end = None
        self._numFrames = 0

    def start(self):
        self._start = datetime.now()
        return self

    def stop(self):
        self._end = datetime.now()

    def update(self):
        self._numFrames += 1

    def elapsed(self):
        return ((self._end if not self._end is None else datetime.now()) - self._start).total_seconds()

    def fps(self):
        return self._numFrames / self.elapsed()
    
class CameraSource(object):
    
    def __init__(self, camera_name):
        self.fps = FPS()
        self.fps.start()
        self.camera_name = camera_name
        self.comms = datetime.now()
        self.movement = False
        self.record_movement = config["record_new_seconds"]
        self.motion_frames = 0
        self._active = True
        self.last_render = None

    def update(self):
        self.fps.update()
        self._active = True
        self.comms = datetime.now()
        
    def render(self, frame, movement):
        self.update()
        result = None
        if movement:
            # increment the motion counter
            self.motion_frames += 1
            if self.movement:
                # ongoing movement, record after interval and set new interval
                pause_frames = self.record_movement * self.fps.fps()
                if self.motion_frames > pause_frames:
                    self.movement = False
                    self.motion_frames = 0
                    self.record_movement = config["record_update_seconds"]
                    result = frame
            # check to see if the number of frames with consistent motion is high enough
            if self.motion_frames >= config["min_motion_frames"]:
                self.movement = True
                self.motion_frames = 0
                result = frame
        else:
            if self.movement:
                self.motion_frames += 1
                pause_frames = config["record_new_seconds"] * self.fps.fps()
                if self.motion_frames > pause_frames:
                    self.record_movement = config["record_new_seconds"]
                    self.movement = False
                    self.motion_frames = 0
                    result = frame
            else:
                result = frame
#             elif self.last_render is None or (datetime.now() - self.last_render).total_seconds() > 5:
#                 print("No movement for 5 seconds, render frame")
#                 self.last_render = datetime.now()
#                 result = frame
        if not result is None:
            timestamp = datetime.now()
            cv2.putText(frame, timestamp.strftime("%A %d %B %Y %I:%M:%S%p"), (10, frame.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 255), 1)
        return result
        
    @property
    def active(self):
        if not self._active or (datetime.now() - self.comms).seconds > config["active_check_seconds"]:
            self._active = False
        return self._active
    
class FrameServer(object):
    
    def __init__(self):
        self.imageHub = camimage.ImageHub(hub_port=config["server_port"])
        self.imageHub.start()
        self.net = cv2.dnn.readNetFromCaffe(config["prototxt"], config["model"])
        self.camera_sources = {}
        self.frame_available = False
        self.empty_frame = None
        self.lastActiveCheck = datetime.now()
        self._actors = []
        self.shutdown = False

    def set_frame(self, camera_name, fps, frame, movement):
        for actor in self._actors:
            if not movement and actor.movement_only:
                continue
            actor.set_frame(camera_name, fps, frame)
        
    def run(self):
        for detail in config["actors"]:
            modname, klassName = detail["class_name"].split(".")
            module = importlib.import_module(modname)
            print("Building actor %s" % klassName)
            actor = getattr(module, klassName)(config, **detail["args"])
            self._actors.append(actor)
            actor.start()
        while not self.shutdown:
            try:
                result = self.imageHub.recv_image()
                if not result is None:
                    (camdetail, frame) = result
                    camera_name = camdetail["camera_name"]
                    if not camera_name in self.camera_sources:
                        print("Register camera %s" % (camera_name))
                        camera_source = CameraSource(camera_name)
                        self.camera_sources[camera_name] = camera_source
                    else:
                        camera_source = self.camera_sources[camera_name]
                        if self.empty_frame is None:
                            (h, w) = frame.shape[:2]
                            self.empty_frame = cv2.resize(cv2.imread("./nopicture.png"), (w, h), cv2.INTER_AREA)
                        frame, movement = self.analyze(frame)
                        if not camera_source.render(frame, movement) is None:
                            self.set_frame(camera_name, camdetail["fps"], frame, movement)
                if (datetime.now() - self.lastActiveCheck).seconds > config["active_check_seconds"]:
                    for camera_source in list(self.camera_sources.values()):
                        if not camera_source.active:
                            print("Unregistering camera %s" % camera_source.camera_name)
                            self.camera_sources.pop(camera_source.camera_name)
                            self.set_frame(camera_source.camera_name, 0, self.empty_frame) 
                    self.lastActiveCheck = datetime.now()                        
            except (KeyboardInterrupt, SystemExit):
                self.shutdown = True
            #except:
            #    print("Error processing camera \n%s: %s" % (sys.exc_info()[0], sys.exc_info()[1]))
            #    self.shutdown = True
        print("Frame server shutting down")
        for actor in self._actors:
            actor.shutdown()
    
    def analyze(self, frame):
        movement = False
        # grab the frame dimensions and construct a blob
        (h, w) = frame.shape[:2]
        resized = cv2.resize(frame, (300, 300), cv2.INTER_AREA)
        blob = cv2.dnn.blobFromImage(resized, 0.007843, (300, 300), 127.5)    
        # pass the blob through the network and obtain the detections and predictions
        self.net.setInput(blob)
        detections = self.net.forward()
        # reset the object count for each object in the CONSIDER set
        objCount = {obj: 0 for obj in CONSIDER}    
        # loop over the detections
        for i in numpy.arange(0, detections.shape[2]):
            # extract the confidence (i.e., probability) associated with the prediction
            confidence = detections[0, 0, i, 2]    
            # filter out weak detections by ensuring the confidence is greater than the minimum confidence
            if confidence > config["confidence"]:
                # extract the index of the class label from the detections
                idx = int(detections[0, 0, i, 1])    
                # check to see if the predicted class is in the set of classes that need to be considered
                if CLASSES[idx] in CONSIDER:
                    # increment the count of the particular object detected in the frame
                    objCount[CLASSES[idx]] += 1    
                    # compute the (x, y)-coordinates of the bounding box for the object
                    box = detections[0, 0, i, 3:7] * numpy.array([w, h, w, h])
                    (startX, startY, endX, endY) = box.astype("int")    
                    # draw the bounding box around the detected object on the frame
                    cv2.rectangle(frame, (startX, startY), (endX, endY), COLORS[idx], 2)
                    # display the prediction
                    label = "{}: {:.2f}%".format(CLASSES[idx], confidence * 100)
                    y = startY - 15 if startY - 15 > 15 else startY + 15
                    cv2.putText(frame, label, (startX, y), cv2.FONT_HERSHEY_SIMPLEX, 0.4, COLORS[idx], 2)                   
                    movement = True
        return frame, movement
        
    def detect(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)
        if self.avg is None:
            self.avg = gray.copy().astype("float")
            return frame, False
        movement = False
        cv2.accumulateWeighted(gray, self.avg, config["weighting_alpha"])
        frameDelta = cv2.absdiff(gray, cv2.convertScaleAbs(self.avg))        

        # threshold the delta image, dilate the thresholded image to fill in holes, then find contours on thresholded image
        thresh = cv2.threshold(frameDelta, config["delta_thresh"], 255, cv2.THRESH_BINARY)[1]
        thresh = cv2.erode(thresh, None, iterations = 2)
        thresh = cv2.dilate(thresh, None, iterations = 2)
        contours, hierarchy = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
        # loop over the contours
        if contours is None or len(contours) == 0:
            return frame, False
        (minX, minY) = (numpy.inf, numpy.inf)
        (maxX, maxY) = (-numpy.inf, -numpy.inf)
        
        for contour in contours:
            # compute the bounding box of the contour and use it to
            # update the minimum and maximum bounding box regions
            (x, y, w, h) = cv2.boundingRect(contour)
            (minX, minY) = (min(minX, x), min(minY, y))
            (maxX, maxY) = (max(maxX, x + w), max(maxY, y + h))                

        area_perc = ((maxX - minX) * (maxY - minY)) / 100.0
        if area_perc >= config["movement_sensitivity"]:
            print("Movement, recognize shape?")
            frame, movement = self.recognize(frame)
            if movement:
                timestamp = datetime.now()
                cv2.putText(frame, timestamp.strftime("%A %d %B %Y %I:%M:%S%p"), (10, frame.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 255), 1)
                #cv2.rectangle(frame, (minX, minY), (maxX, maxY), (0, 255, 0), 2)
        return frame, movement
        
if __name__ == "__main__":
    # construct the argument parser and parse the arguments
    ap = argparse.ArgumentParser()
    ap.add_argument("-c", "--conf", default="server.json", 
        help="path to the JSON configuration file")
    args = vars(ap.parse_args())
    
    config = json.load(open(args["conf"]))

    instance = FrameServer()
    instance.run()
