import base64
import cv2
import cvzone
import numpy as np
import pickle
import pandas as pd
from flask import Flask, render_template, request, redirect
import socketio
import threading
from ultralytics import YOLO

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

# Default admin credentials
admin_credentials = {"root": "MPD"}

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
    return redirect('/slotmap')

@app.route('/login/admin', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        admin_id = request.form['admin_id']
        admin_password = request.form['admin_password']
        if admin_id in admin_credentials and admin_credentials[admin_id] == admin_password:
            return redirect('/adminpanel')
        else:
            return "Incorrect admin ID or password. Please try again."
    else:
        return render_template('admin_login.html')

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
        occupied_slots = []  # List to store occupied slot names

        for i, polyline in enumerate(polylines):
            slot_name = slot_names[i]  # Get the slot name
            cv2.polylines(frame,[polyline], True, (0, 255, 0), 2)
            cvzone.putTextRect(frame, f'{slot_names[i]}', tuple(polyline[0]), 1, 1)
            for i1 in list1:
                cx1 = i1[0]
                cy1 = i1[1]

                result = cv2.pointPolygonTest(polyline, ((cx1, cy1)), False)
                if result >= 0:
                    cv2.circle(frame,(cx1, cy1), 5, (255, 0, 0), -1)
                    cv2.polylines(frame,[polyline], True,(0, 0, 255), 2)
                    counter1.append(cx1)
                    occupied_slots.append(slot_name)  # Add the occupied slot name

        used_slots = len(counter1)
        free_slots = len(polylines) - used_slots

        cvzone.putTextRect(frame, f'PARKED CAR COUNT:{used_slots}',(20,30),2,2)
        cvzone.putTextRect(frame, f'FREE SLOTS:{free_slots}',(20,100),2,2)

        #cv2.imshow('FRAME', frame)
        key = cv2.waitKey(1000) & 0xFF

        # Convert frame to base64 encoded JPEG image
        _, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = base64.b64encode(buffer).decode('utf-8')

        # Send the frame data to the client
        sio.emit('cam_feed', {'frame_bytes': frame_bytes})

        # Send the occupied slot names to the client
        sio.emit('parking_status_update', {
            'used_slots': used_slots,
            'free_slots': free_slots,
            'occupied_slots': occupied_slots  # Include occupied slot names in the update
        })

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
