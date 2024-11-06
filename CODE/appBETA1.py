from flask import Flask, render_template, request, redirect
import cv2
import numpy as np
import pickle
import pandas as pd
from ultralytics import YOLO
import socketio
import threading
import sys

app = Flask(__name__)

# Initialize YOLO model
model = YOLO('yolov8s.pt')

# Load parking slot annotations
with open("parkingslotpolylines", "rb") as f:
    data = pickle.load(f)
    polylines, slot_names = data['polylines'], data['slot_names']

# Initialize socketio
sio = socketio.Server()
app.wsgi_app = socketio.WSGIApp(sio, app.wsgi_app)

# Default OTPs
user_otp = "00000"
admin_otp = "12345"

# Initialize counters
used_slots = 0
free_slots = len(polylines)

# Load class labels from coco.txt
with open("coco.txt", "r") as f:
    class_list = f.read().split("\n")

# Flag variable for stopping car_detection thread
stop_car_detection = False

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login/user', methods=['POST'])
def user_login():
    entered_otp = request.form['user_otp']
    if entered_otp == user_otp:
        return redirect('/slotmap')
    else:
        return "Incorrect OTP for user. Please try again."

@app.route('/login/admin', methods=['POST'])
def admin_login():
    entered_otp = request.form['admin_otp']
    if entered_otp == admin_otp:
        return redirect('/adminpanel')
    else:
        return "Incorrect OTP for admin. Please try again."

@app.route('/slotmap')
def slotmap():
    return render_template('slotmap.html', used_slots=used_slots, free_slots=free_slots)

@app.route('/adminpanel')
def adminpanel():
    return render_template('adminpanel.html')

@sio.on('connect')
def connect(sid, environ):
    print('Connected to server')

def car_detection():
    global used_slots, free_slots, stop_car_detection
    cap = cv2.VideoCapture('cam_feed.mp4')
    count = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            continue

        count += 1
        if count % 3 != 0:
            continue

        frame = cv2.resize(frame, (1020, 500))
        frame_copy = frame.copy()
        results = model.predict(frame)
        a = results[0].boxes.data
        px = pd.DataFrame(a).astype("float")
        list1 = []

        for index, row in px.iterrows():
            x1 = int(row[0])
            y1 = int(row[1])
            x2 = int(row[2])
            y2 = int(row[3])
            d = int(row[5])

            c = class_list[d]
            cx = int(x1 + x2) // 2
            cy = int(y1 + y2) // 2
            if 'car' in c:
                list1.append([cx, cy])

        counter1 = []
        list2 = []

        for i, polyline in enumerate(polylines):
            list2.append(i)
            for i1 in list1:
                cx1 = i1[0]
                cy1 = i1[1]
                result = cv2.pointPolygonTest(polyline, ((cx1, cy1)), False)
                if result >= 0:
                    counter1.append(cx1)

        used_slots = len(counter1)
        free_slots = len(list2) - used_slots

        sio.emit('parking_status_update', {'used_slots': used_slots, 'free_slots': free_slots})

        # Check if the app is being terminated
        if stop_car_detection:
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == '__main__':
    # Start car detection in a separate thread
    car_detection_thread = threading.Thread(target=car_detection)
    car_detection_thread.start()

    try:
        # Run the Flask app
        app.run(debug=True)
    finally:
        # Set the flag to stop car_detection thread when Flask app is terminated
        stop_car_detection = True
        # Wait for the car_detection thread to finish
        car_detection_thread.join()
