'''
Created on 29 Jan 2020

@author: andre.louw
'''
import sys
import threading
import queue
import socket
import time
import select
from datetime import datetime
from camimage.utils import tcp

class ImageSender(threading.Thread):

    def __init__(self, hub_ip='127.0.0.1', hub_port=5555):
        threading.Thread.__init__(self)
        self.setDaemon(True)
        self.hub_ip = hub_ip
        self.hub_port = hub_port
        self.queue = queue.Queue(1)
        
    def send_image(self, data, image):
        try:
            self.queue.put((data, image), block=True, timeout=2.0)
        except queue.Full:
            return
    
    def run(self):
        connected = False
        acked = True
        while True:
            # Connect a client socket to server_socket
            if not connected:
                hub_socket = socket.socket()
                try:
                    hub_socket.connect((self.hub_ip, self.hub_port))
                    acked = True
                    connected = True
                except KeyboardInterrupt:
                    break
                except socket.error:
                    print("No Image Hub found [%s:%d], will retry" % (self.hub_ip, self.hub_port))
                    try:
                        time.sleep(1)
                    except KeyboardInterrupt:
                        break
                except:
                    print("Unexpected Exception [%s]: %s" % (sys.exc_info()[0], sys.exc_info()[1]))
                    break
                if connected:
                    print("Connected to Image Hub")
                    inputs = [hub_socket]
                    outputs = [hub_socket]
                else:
                    continue
            try:
                readable, writable, errored = select.select(inputs, outputs, inputs, 0.1)
                for s in readable:
                    if not acked:
                        acked = tcp.recv_ack(s)
                    if not acked:
                        print("ImageSender: Image Hub disconnected")
                        inputs.remove(s)
                        if s in outputs:
                            outputs.remove(s)
                        s.close()
                        connected = False
                for s in writable:
                    if acked:
                        if not self.queue.empty():
                            data, image = self.queue.get()
                            tcp.send_image(hub_socket, data, image)
                            acked = False
                for s in errored:
                    print("Exception for Image Hub %s" % s.getpeername()[0])
                    inputs.remove(s)
                    if s in outputs:
                        outputs.remove(s)
                    s.close()
            except KeyboardInterrupt:
                break
            except socket.error:
                print("Lost connection with Image Hub")
                break
            #except:
            #    print("Error processing camera frame\n%s: %s" % (sys.exc_info()[0], sys.exc_info()[1]))
            #    time.sleep(0.1)
        print("ImageSender: shutting down...")
        if not hub_socket is None:
            hub_socket.shutdown(socket.SHUT_WR)
            hub_socket.close()

def unique_id(conn):
    return "%s:%s" % (conn.getpeername()[0], conn.getpeername()[1])
    
class CameraState(object):
    
    def __init__(self):
        self.lastActive = datetime.now()
        self.shouldAck = False
        
    def incoming(self):
        self.lastActive = datetime.now()
        self.shouldAck = True
        
    def delay(self):
        return (datetime.now() - self.lastActive).seconds
        
class ImageHub(threading.Thread):

    def __init__(self, hub_ip='0.0.0.0', hub_port=5555):
        threading.Thread.__init__(self)
        self.setDaemon(True)
        self.hub_ip = hub_ip
        self.hub_port = hub_port
        self.queue = queue.Queue(1)
        
    def recv_image(self):
        try:
            return self.queue.get(block=True, timeout=2.0)
        except queue.Empty:
            return None
            
    def send_ack(self, conn):
        tcp.send_ack(conn)

    def run(self):
        hub_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        hub_socket.bind((self.hub_ip, self.hub_port))
        hub_socket.listen(5)
        cam_socks = {}
    
        print("Waiting for Images...")
        inputs = [hub_socket]
        outputs = [hub_socket]
        while inputs:
            try:
                readable, writable, errored = select.select(inputs, outputs, inputs, 0.1)
                for s in readable:
                    if s is hub_socket:
                        camera_socket, client_addr = s.accept()
                        print("ImageHub: camera connected from %s:%s" % (camera_socket.getpeername()[0], camera_socket.getpeername()[1]))
                        inputs.append(camera_socket)
                        cam_socks[unique_id(camera_socket)] = CameraState()
                    else:                        
                        data, image = tcp.recv_image(s)
                        if not image is None:
                            if s not in outputs:
                                outputs.append(s)
                            self.queue.put((data, image))                        
                            cam_socks[unique_id(s)].incoming()
                        else:
                            print("ImageHub: camera disconnected")
                            if s in outputs:
                                outputs.remove(s)
                            inputs.remove(s)
                            del cam_socks[unique_id(s)]
                            s.close()
                for s in writable:
                    if cam_socks[unique_id(s)].shouldAck:
                        self.send_ack(s)
                        cam_socks[unique_id(s)].shouldAck = False
                    else:
                        outputs.remove(s)
                for s in errored:
                    print("Exception for camera %s:%s" % (s.getpeername()[0], s.getpeername()[1]))
                    inputs.remove(s)
                    del cam_socks[unique_id(s)]
                    if s in outputs:
                        outputs.remove(s)
                    s.close()
            except KeyboardInterrupt:
                print("Keyboard interrupt received...")
                break
