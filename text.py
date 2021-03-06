#move servos accept  angles to move,gotta convert linear distance to it
#gotta compensate for the ~3s delay between processing and realtime image
from __future__ import print_function
import RPi.GPIO as GPIO                                 ## Import GPIO Library.
import time
import serial
import picamera
import numpy as np
from numpy import pi, sin, cos
#from picamera import PiCamera
import cv2
import io
from picamera.array import PiRGBArray
import threading
IM_WIDTH = 320
IM_HEIGHT = 240
camera = picamera.PiCamera()
camera.resolution = (IM_WIDTH,IM_HEIGHT)
camera.framerate = 80
ser = serial.Serial('/dev/ttyACM0',baudrate=9600) 
cv2Net = None
showVideoStream = False


j=0

currentClassDetecting = 'red ball'
netModels = [
    {},
    {
        'modelPath': 'models/mobilenet_ssd_v1_balls/transformed_frozen_inference_graph.pb',
        'configPath': 'models/mobilenet_ssd_v1_balls/ssd_mobilenet_v1_balls_2018_05_20.pbtxt',
        'classNames': {
            0: 'background', 1: 'red ball', 2: 'blue ball'
        }
    }
]


def readser(ser,e,lock):
    print("ser thread start")
    while(True):
        lock.acquire(1)
        line = ser.readline()
        line = str(line)
        lock.release()
        #print("Ser"+line)
        if(line=="STOPGRAB"):
            print("Grabbed")
            e.set()
        

def label_class(img, detection, score, className, boxColor=None):
    rows = img.shape[0]
    cols = img.shape[1]

    if boxColor == None:
        boxColor = (23, 230, 210)
    className = 'target'
    
    xLeft = int(detection[3] * cols)
    yTop = int(detection[4] * rows)
    xRight = int(detection[5] * cols)
    yBottom = int(detection[6] * rows)
    cv2.rectangle(img, (xLeft, yTop), (xRight, yBottom), boxColor, thickness=4)

    label = className + ": " + str(int(round(score * 100))) + '%'
    #print(label)
    labelSize, baseLine = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
    yTop = max(yTop, labelSize[1])
    cv2.rectangle(img, (xLeft, yTop - labelSize[1]), (xLeft + labelSize[0], yTop + baseLine),
        (255, 255, 255), cv2.FILLED)
    cv2.putText(img, label, (xLeft, yTop), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0))
    pass

def detect_all_objects(img, detections, score_threshold, classNames):
    for detection in detections:
        
        class_id = int(detection[1])
        score = float(detection[2])
        if score > 0.3:#score_threshold:
            print(classNames[class_id]+":"+ str(score))
            label_class(img, detection, score, classNames[class_id])
            
    pass

def detect_object(img, detections, score_threshold, classNames, className):
    for detection in detections:
        score = float(detection[2])
        class_id = int(detection[1])
        if className in classNames.values() and className == classNames[class_id] and score > score_threshold:
            label_class(img, detection, score, classNames[class_id])
    pass

def track_object(k,img, detections, score_threshold, classNames, className, tracking_threshold,e,lock):
    for detection in detections:
        score = float(detection[2])
        class_id = int(detection[1])
        if(class_id==-1 or class_id>2):
            class_id=0
        print(class_id)
        print(classNames[class_id])
        if className in classNames.values() and  classNames[class_id] == "red ball" and score > score_threshold:
            
            rows = img.shape[0]
            cols = img.shape[1]
            marginLeft = int(detection[3] * cols) # xLeft
            marginRight = cols - int(detection[5] * cols) # cols - xRight
            xMarginDiff = marginLeft - marginRight
            marginTop = int(detection[4] * rows) # yTop
            marginBottom = rows - int(detection[6] * rows) # rows - yBottom
            yMarginDiff = marginTop - marginBottom
            #print(xMarginDiff,yMarginDiff)
            
            
            
            
            
            if abs(xMarginDiff) < tracking_threshold and abs(yMarginDiff) < tracking_threshold:
                boxColor = (0, 255, 0)
                data=str(xMarginDiff)+str(',')+str(yMarginDiff)+str(',')+str(80)+str(',')+str(10)+str('..')
                print("grab")
                lock.acquire(1)
                ser.write(data.encode())
                lock.release()
                e.wait()
                #time.sleep(0.5)
            else:
                data=str(xMarginDiff)+str(',')+str(yMarginDiff)+str(',')+str(110)+str(',')+str(0)+str('..')
                lock.acquire(1)
                ser.write(data.encode())
                lock.release()
                boxColor = (0, 0, 255)
                #time.sleep(0.5)
            
            print(data)
            label_class(img, detection, score, classNames[class_id], boxColor)
    pass

def run_video_detection(mode, netModel,currentClassDetecting,e,lock):
    scoreThreshold = 0.2
    trackingThreshold = 20
       
    cv2Net = cv2.dnn.readNetFromTensorflow(netModel['modelPath'], netModel['configPath'])
    
    stream = io.BytesIO()
    data  = io.BytesIO()
    k=0
    frame_rate_calc = 1.0
    freq = cv2.getTickFrequency()
    stream = picamera.array.PiRGBArray(camera, size=(320, 240))
    time.sleep(1)
    global showVideoStream
    for i in range(0,1000):
        t1 = cv2.getTickCount()
        camera.capture(stream, format='bgr',use_video_port=True)
        
        # At this point the image is available as stream.array
        img = stream.array
        #print("shot " + str(k))
        k+=1
            #img = cv2.imdecode(dat
        # img = img[:, :, ::-1]
       
        # run detection
     #   print("ping") 
        cv2Net.setInput(cv2.dnn.blobFromImage(img, 1.0/127.5, (300, 300), (127.5, 127.5, 127.5), swapRB=True, crop=False))
        detections = cv2Net.forward()
        #print("pong") 
        #if mode == 1:
         #   detect_all_objects(img, detections[0,0,:,:], scoreThreshold, netModel['classNames'])
        #elif mode == 2:
         #   detect_object(img, detections[0,0,:,:], scoreThreshold, netModel['classNames'], currentClassDetecting)
        #elif mode == 3:
        track_object(k,img, detections[0,0,:,:], scoreThreshold, netModel['classNames'], currentClassDetecting, trackingThreshold,e,lock)
        cv2.putText(img, "FPS: {0:.2f}".format(frame_rate_calc), (20, 20),
                    cv2.FONT_HERSHEY_PLAIN, 1, (255, 255, 0), 2, cv2.LINE_AA)
        cv2.imshow('Real-Time Object Detection', img)
        t2 = cv2.getTickCount()
        time1 = (t2 - t1) / freq
        frame_rate_calc = 1 / time1
        ch = cv2.waitKey(1)
        if ch == 27:
            showVideoStream = False
            break
        
    print('exiting run_video_detection...')
    cv2.destroyAllWindows()
    pass

if __name__ == '__main__':
    
    
    currentClassDetecting = 'red ball'
    showVideoStream = True
    e = threading.Event()
    lock = threading.Lock()
    t1 = threading.Thread(target=readser, args=[ser,e,lock])
    t1.start()
      
    videoStreamThread = threading.Thread(target=run_video_detection, args=[3,netModels[1],currentClassDetecting,e,lock])
    videoStreamThread.start()
    print("thread popped")
        
