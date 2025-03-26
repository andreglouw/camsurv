from threading import Thread
import cv2

class VIGIStream:
    def __init__(self, src=0, resolution=(640, 480), name="VIGI Stream"):
        self.stream = cv2.VideoCapture(src)
        self.fps = self.stream.get(cv2.CAP_PROP_FPS)
        self.stream.set(3,resolution[0])
        self.stream.set(4,resolution[1])
        
        (self.grabbed, self.frame) = self.stream.read()

        # initialize the thread name
        self.name = name

        # initialize the variable used to indicate if the thread should
        # be stopped
        self.stopped = False

    def start(self):
        # start the thread to read frames from the video stream
        t = Thread(target=self.update, name=self.name, args=())
        t.daemon = True
        t.start()
        return self

    def update(self):
        # keep looping infinitely until the thread is stopped
        while True:
            # if the thread indicator variable is set, stop the thread
            if self.stopped:
                return

            # otherwise, read the next frame from the stream
            (self.grabbed, self.frame) = self.stream.read()

    def read(self):
        # return the frame most recently read
        return self.frame

    def stop(self):
        # indicate that the thread should be stopped
        self.stopped = True
