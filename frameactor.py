import threading
import os
import os.path
from datetime import datetime
import cv2

class FrameActor(threading.Thread):
    
    def __init__(self, conf, **kwargs):
        threading.Thread.__init__(self)
        self.setDaemon(True)
        self.event = threading.Condition()
        self.frame_available = False
        self._frame = None
        self.conf = conf
        self.fps = None
        self.avg = None
        self._shutdown = False
        self.init(**kwargs)
        
    def init(self):
        raise RuntimeError('Must be implemented by subclasses.')
    
    def set_frame(self, camera_name, frame):
        self.event.acquire()
        self._frame = (camera_name, frame)
        self.frame_available = True
        self.event.notifyAll()
        self.event.release()
        
    def get_frame(self):
        self.event.acquire()
        while not self.frame_available:
            self.event.wait()
        try:
            self.frame_available = False
            return self._frame
        finally:
            self.event.release()

    def frameToYield(self, frame):
        return frame
    
    def frames(self, detail=True):
        while not self._shutdown:
            (camera_name, frame) =  self.get_frame()
            frame = self.frameToYield(frame)
            if not frame is None:
                if detail:
                    yield (camera_name, frame)
                else:
                    yield frame
            
    def run(self):
        print("Starting actor %s" % type(self).__name__)
        for (camera_name, frame) in self.frames():
            self.handle(camera_name, frame)

    def shutdown(self):
        print("Actor %s shutting down" % type(self).__name__)
        self._shutdown = True        
        
class LocalViewer(FrameActor):
            
    def init(self):
        self.first = True

    def handle(self, camera_name, frame):
        cv2.imshow(camera_name, frame)
        cv2.waitKey(1)
    
class VideoFile(FrameActor):
    
    def init(self, seconds_per_frame):
        self.cameraFiles = {}
        self.fps = 1.0 / float(seconds_per_frame)
        
    def handle(self, camera_name, frame):
        if not camera_name in self.cameraFiles:
            file_name = "./%s.avi" % camera_name
            if os.path.exists(file_name):
                name, ext = os.path.splitext(file_name)
                now = datetime.today()
                timestamp = now.strftime("%Y%m%d_%H%M%S")
                os.rename(file_name, "%s_%s%s" % (name, timestamp, ext))
            fourcc = cv2.VideoWriter_fourcc(*'MJPG')
            (h, w) = frame.shape[:2]
            print("VideoFile capture @ %.1f fps: %d x %d" % (self.fps, w, h))
            video = cv2.VideoWriter(file_name, fourcc, self.fps, (w, h))
            self.cameraFiles[camera_name] = video
        else:
            video = self.cameraFiles[camera_name]
        video.write(frame)        

    def shutdown(self):
        for video in self.cameraFiles.values():
            video.release()
        FrameActor.shutdown(self)
    