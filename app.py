# import cv2
# import mediapipe as mp
# import time
# import requests
# import threading
# import queue
# from flask import Flask, render_template, Response

# # --- Flask App Initialization ---
# app = Flask(__name__)

# # --- Thread-safe queue to hold commands for the ESP8266 ---
# command_queue = queue.Queue()

# # --- Global variable for ESP URL (will be set when the app starts) ---
# ESP_URL = ""

# # --- Network Worker Function (runs on a separate thread) ---
# def send_commands_worker():
#     """This function runs in the background, sending commands from the queue."""
#     print("🚀 Network worker thread started.")
#     while True:
#         try:
#             angles = command_queue.get()
#             requests.get(ESP_URL, params=angles, timeout=2.0)
#             print(f"Sent: {angles}")
#             command_queue.task_done()
#         except requests.exceptions.RequestException as e:
#             print(f"⚠️  Connection error: {e}")
#         except Exception as e:
#             print(f"An error occurred in the network thread: {e}")

# # --- Video Generation Function ---
# def generate_frames():
#     """This function captures video, processes it, and yields frames for streaming."""
#     video = cv2.VideoCapture(0)
#     mp_hand = mp.solutions.hands
#     mp_draw = mp.solutions.drawing_utils
#     tipIds = [4, 8, 12, 16, 20]

#     last_sent_time = 0
#     SEND_INTERVAL = 0.25 # Send a maximum of 4 commands per second

#     print("🚀 Starting hand tracking for video stream...")
#     with mp_hand.Hands(min_detection_confidence=0.5, min_tracking_confidence=0.5) as hands:
#         while True:
#             success, image = video.read()
#             if not success:
#                 break
#             else:
#                 # Process the image to find hands
#                 image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
#                 results = hands.process(image_rgb)
                
#                 lmList = []
#                 if results.multi_hand_landmarks:
#                     for hand_landmark in results.multi_hand_landmarks:
#                         for id, lm in enumerate(hand_landmark.landmark):
#                             h, w, c = image.shape
#                             cx, cy = int(lm.x * w), int(lm.y * h)
#                             lmList.append([id, cx, cy])
#                         mp_draw.draw_landmarks(image, hand_landmark, mp_hand.HAND_CONNECTIONS)

#                 # Check if enough time has passed to send a new command
#                 if len(lmList) != 0 and (time.time() - last_sent_time > SEND_INTERVAL):
#                     fingers = []
#                     # Thumb (x-axis)
#                     if lmList[tipIds[0]][1] > lmList[tipIds[0] - 1][1]: fingers.append(1)
#                     else: fingers.append(0)

#                     # Other fingers (y-axis)
#                     for id in range(1, 5):
#                         if lmList[tipIds[id]][2] < lmList[tipIds[id] - 2][2]: fingers.append(1)
#                         else: fingers.append(0)
                    
#                     # Calculate angles and put them into the queue
#                     angles = {
#                         "thumb": 90 if fingers[0] == 1 else 0,
#                         "index": 0 if fingers[1] == 1 else 90,
#                         "middle": 0 if fingers[2] == 1 else 180,
#                         "ring": 0 if fingers[3] == 1 else 90,
#                         "pinky": 90 if fingers[4] == 1 else 0
#                     }
#                     command_queue.put(angles)
#                     last_sent_time = time.time()

#                 # Encode the frame in JPEG format
#                 ret, buffer = cv2.imencode('.jpg', image)
#                 frame = buffer.tobytes()
#                 # Yield the frame in the multipart content type
#                 yield (b'--frame\r\n'
#                        b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
#     video.release()

# # --- Flask Routes ---
# @app.route('/')
# def index():
#     """Video streaming home page."""
#     return render_template('index.html')

# @app.route('/video_feed')
# def video_feed():
#     """Video streaming route. Put this in the src attribute of an img tag."""
#     return Response(generate_frames(),
#                     mimetype='multipart/x-mixed-replace; boundary=frame')

# # --- Main Execution Block ---
# if __name__ == '__main__':
#     # Get the ESP8266 IP address from the user when starting the server
#     ESP_IP = input("Enter the IP address of your ESP8266: ")
#     if not ESP_IP:
#         ESP_IP = "192.168.1.79" # Default if you just press Enter
#     ESP_URL = f"http://{ESP_IP}/move"
#     print(f"✅ Commands will be sent to: {ESP_URL}")

#     # Start the network worker thread
#     network_thread = threading.Thread(target=send_commands_worker, daemon=True)
#     network_thread.start()

#     # Start the Flask app
#     # Use host='0.0.0.0' to make it accessible from other devices on your network
#     app.run(host='0.0.0.0', port=5000, debug=False)




#above code contains flask for localhost 
# from flask import Flask, render_template, request, jsonify
# import queue
# import threading

# # --- Flask App Initialization ---
# app = Flask(__name__)

# # --- Thread-safe queue to hold ONLY the most recent command ---
# # maxsize=1 means old commands are discarded if a new one arrives.
# # This prevents the hand from acting on stale data.
# command_queue = queue.Queue(maxsize=1)

# # --- Flask Routes ---

# @app.route('/')
# def index():
#     """Serves the main HTML page that contains the JavaScript logic."""
#     return render_template('index.html')

# @app.route('/api/hand_data', methods=['POST'])
# def handle_hand_data():
#     """
#     Receives hand angle data from the browser's JavaScript and puts it in the queue.
#     """
#     angles = request.json
#     if angles:
#         # If the queue is full, remove the old item before adding the new one.
#         if command_queue.full():
#             try:
#                 command_queue.get_nowait()
#             except queue.Empty:
#                 pass  # This is a safe check, though unlikely to be needed
        
#         command_queue.put(angles)
#         print(f"Received from browser: {angles}") # For server-side logging
#         return jsonify({"status": "success", "data": angles})
    
#     return jsonify({"status": "error", "message": "No data received"}), 400

# @app.route('/api/get_command')
# def get_command():
#     """
#     This is the long-polling endpoint for the ESP8266.
#     It waits for a command to appear in the queue and sends it as a response.
#     """
#     try:
#         # Wait up to 10 seconds for a command to appear in the queue.
#         # This holds the HTTP connection open.
#         angles = command_queue.get(timeout=10)
#         print(f"Sending to ESP8266: {angles}") # For server-side logging
#         return jsonify(angles)
#     except queue.Empty:
#         # If no command arrives after 10 seconds, send an empty JSON object.
#         # This tells the ESP8266 to simply try again without error.
#         return jsonify({})

# # --- Main Execution Block ---
# if __name__ == '__main__':
#     # Use host='0.0.0.0' to make the server accessible on your local network
#     # and for Render deployment. The port will be handled by Render.
#     app.run(host='0.0.0.0', port=5000, debug=False)



from flask import Flask, render_template, request, jsonify
import queue
import threading

# --- Flask App Initialization ---
app = Flask(__name__)

# --- Thread-safe queue to hold ONLY the most recent command ---
# maxsize=1 means old commands are discarded if a new one arrives.
# This prevents the hand from acting on stale data.
command_queue = queue.Queue(maxsize=1)

# --- Flask Routes ---

@app.route('/')
def index():
    """Serves the main HTML page that contains the JavaScript logic."""
    return render_template('index.html')

@app.route('/api/hand_data', methods=['POST'])
def handle_hand_data():
    """
    Receives hand angle data from the browser's JavaScript and puts it in the queue.
    """
    angles = request.json
    if angles:
        # If the queue is full, remove the old item before adding the new one.
        if command_queue.full():
            try:
                command_queue.get_nowait()
            except queue.Empty:
                pass  # This is a safe check
        
        command_queue.put(angles)
        print(f"Received from browser: {angles}") # For server-side logging
        return jsonify({"status": "success", "data": angles})
    
    return jsonify({"status": "error", "message": "No data received"}), 400

@app.route('/api/get_command')
def get_command():
    """
    This is the long-polling endpoint for the ESP8266.
    It waits for a command to appear in the queue and sends it as a response.
    """
    try:
        # Wait up to 10 seconds for a command. This holds the HTTP connection open.
        angles = command_queue.get(timeout=10)
        print(f"Sending to ESP8266: {angles}") # For server-side logging
        return jsonify(angles)
    except queue.Empty:
        # If no command arrives, send an empty object.
        # This tells the ESP8266 to simply try again.
        return jsonify({})

# --- Main Execution Block ---
if __name__ == '__main__':
    # Use host='0.0.0.0' for Render deployment.
    app.run(host='0.0.0.0', port=5000, debug=False)