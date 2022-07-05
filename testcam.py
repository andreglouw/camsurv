'''
Created on 24 Jan 2020

@author: andre.louw
'''
import cv2
import imutils

def main():
    cv2.namedWindow('images')
    cap = cv2.VideoCapture(0)
#     fourccs = cv2.VideoWriter_fourcc(*'XVID')
#     out = cv2.VideoWriter('sample.avi', fourccs, 20.0, (640,480))
    avg = None
    while (True):
        ret, frame = cap.read()
#        out.write(frame)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        #gray = cv2.GaussianBlur(gray, (21, 21), 0)
        if avg is None:
            avg = gray.copy().astype("float")
        cv2.imshow('images',gray)
        cv2.accumulateWeighted(gray, avg, 0.05)
        frameDelta = cv2.absdiff(gray, cv2.convertScaleAbs(avg))        
        thresh = cv2.threshold(frameDelta, 30, 255, cv2.THRESH_BINARY)[1]
        thresh = cv2.dilate(thresh, None, iterations = 2)
        contours, hierarchy = cv2.findContours(thresh.copy(), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        if contours is None:
            continue
        for cnt in contours:
            if cv2.contourArea(cnt) < 3000:
                continue
    
            # compute the bounding box for the contour, draw it on the frame,
            # and update the text
            (x, y, w, h) = cv2.boundingRect(cnt)
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.imshow('rects',frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
#            out.release()
            cv2.destroyAllWindows()
            break
    
if __name__ == '__main__':
    main()