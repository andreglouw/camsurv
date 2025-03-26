import sys
import argparse
import json
import time
import datetime
from camimage import camimage
import cv2
from vigistream import VIGIStream
from imutils.video import VideoStream, FPS

class Camera(object):
    
    def __init__(self, conf):
        self.conf = conf
        self.sender = camimage.ImageSender(hub_ip=conf["server_ip"], hub_port=conf["server_port"])
        self.sender.start()
        self.stream = self.build()
        self.fps = self.stream.fps
        print(f"FPS: {self.fps}")
        self.stream.start()
        time.sleep(conf["camera_warmup_time"])
    
    def build(self):
        return VIGIStream(src=conf["source"], resolution=conf["resolution"])
    
    def run(self):
        while True:
            try:
                frame = self.stream.read()
                if not frame is None:
                    self.sender.send_image({"camera_name":self.conf["camera_name"], "fps": self.fps}, frame)
            except:
                print("Camera shutting down...")
                break
        self.stream.stop()
            
class PiCamera(Camera):

    def build(self):
        return VideoStream(src=self.conf["source"], usePiCamera=True, resolution=self.conf["resolution"], framerate=self.conf["framerate"])
            
if __name__ == "__main__":
    # construct the argument parser and parse the arguments
    ap = argparse.ArgumentParser()
    ap.add_argument("-c", "--conf", default="camera.json", help="path to the JSON configuration file")
    args = vars(ap.parse_args())
    
    conf = json.load(open(args["conf"]))
    if conf["picamera"]:
        pub = PiCamera(conf)
    else:
        pub = Camera(conf)
    pub.run()
                
        