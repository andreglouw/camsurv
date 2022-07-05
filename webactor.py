import cv2
import numpy
from frameactor import FrameActor
from flask import Flask, render_template, Response

def index():
    return render_template('index.html')

class WebActor(FrameActor):
        
    def init(self):
        self.app = Flask(__name__)
        self.app.add_url_rule('/', 'index', index)
        self.app.add_url_rule('/video_feed', 'video_feed', self.video_feed)

    def frameToYield(self, frame, movement):
        toYield = FrameActor.frameToYield(self, frame, movement)
        result = None
        if not toYield is None:
            (flag, encodedImage) = cv2.imencode(".jpg", frame)
            if flag:
                result = (b'--frame\r\n'
                          b'Content-Type: image/jpeg\r\n\r\n' + numpy.array(encodedImage).tostring() + b'\r\n')
        return result
            
    def run(self):
        print("Starting WebActor")
        self.app.run("0.0.0.0", debug=True, use_reloader=False)
        print("Actor has shut down...")

    def video_feed(self):
        return Response(self.frames(False), mimetype='multipart/x-mixed-replace; boundary=frame')
