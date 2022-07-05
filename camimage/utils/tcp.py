import sys
import struct
import cv2
import json
import numpy as np

def recvall(conn, count=4096):
    buf = b''
    while count:
        newbuf = conn.recv(count)
        if not newbuf: return buf
        buf += newbuf
        count -= len(newbuf)
    return buf

def read_image(conn):
    try:
        length = struct.unpack('<L', recvall(conn, struct.calcsize('<L')))[0]
    except:
        return False, None
    decimg = recvall(conn, length)
    #data = np.fromstring(stringData, dtype=np.uint8)
    #decimg = cv2.imdecode(data, cv2.IMREAD_COLOR)
    return True, decimg

def send_image_old(conn, img, scale=1.0, encode_param=[int(cv2.IMWRITE_JPEG_QUALITY),90]):
    if scale < 1:
        img = cv2.resize(img, None, fx=scale, fy=scale)
    stringData = cv2.imencode('.jpg', img, encode_param)[1].tostring()
    #result, imgencode = cv2.imencode('.jpg', img, encode_param)
    #data = np.array(imgencode)
    #stringData = data.tostring()
    conn.send(struct.pack('<L', len(stringData)))
    conn.send(stringData)

def read_detail(conn):
    try:
        length = struct.unpack('<L', recvall(conn, struct.calcsize('<L')))[0]
    except:
        return False, None
    stringData = recvall(conn, length)
    detail = json.loads(stringData.decode())
    if "image" in detail:
        image = recvall(conn, detail["image"])
        detail["image"] = image
    return True, detail

def send_detail(conn, **kwargs):
    image = None
    if "image" in kwargs:
        image = kwargs["image"]
        kwargs["image"] = len(image)
    stringData = json.dumps(kwargs)
    conn.send(struct.pack('<L', len(stringData)))
    conn.send(stringData.encode())
    if image != None:
        conn.send(image)

def send_image(conn, data, frame):
    detail = {"data":data, "image":cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY),90])[1].tostring()}
    send_detail(conn, **detail)

def recv_image(conn):
    flag, detail = read_detail(conn)
    if flag:
        image = None 
        if "image" in detail:
            data = np.fromstring(detail["image"], dtype=np.uint8)
            image = cv2.imdecode(data, cv2.IMREAD_COLOR)
            del detail["image"]
        return detail["data"], image
    return None, None

def send_ack(conn):
    detail = {"ack":True}
    send_detail(conn, **detail)

def recv_ack(conn):
    flag, detail = read_detail(conn)
    if flag and "ack" in detail:
        return detail["ack"]
    return False
