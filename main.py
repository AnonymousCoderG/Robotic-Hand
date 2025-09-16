# import cv2
# import mediapipe as mp
# import time
# import requests
# import threading
# import queue

# # --- Thread-safe queue to hold commands for the ESP8266 ---
# # The main thread will put commands here, the network thread will get them.
# command_queue = queue.Queue()

# # --- Network Worker Function (will run on a separate thread) ---
# def send_commands_worker(esp_url):
#     """This function runs in the background, sending commands from the queue."""
#     while True:
#         try:
#             # Get a command from the queue. This will wait until a command is available.
#             angles = command_queue.get()

#             # Send the request to the ESP8266
#             requests.get(esp_url, params=angles, timeout=2.0)
#             print(f"Sent: {angles}")

#             # Mark the task as done
#             command_queue.task_done()

#         except requests.exceptions.RequestException as e:
#             print(f"⚠️  Connection error: {e}")
#         except Exception as e:
#             print(f"An error occurred in the network thread: {e}")


# # --- Main Program ---
# if __name__ == "__main__":
#     # --- Get ESP8266 IP address from user ---
#     ESP_IP = input("Enter the IP address of your ESP8266: ")
#     if not ESP_IP:
#         ESP_IP = "192.168.1.79" # Default if you just press Enter
#     ESP_URL = f"http://{ESP_IP}/move"
#     print(f"✅ Sending commands to: {ESP_URL}")

#     # --- Create and start the network worker thread ---
#     # It's a 'daemon' so it will automatically close when the main program exits.
#     network_thread = threading.Thread(target=send_commands_worker, args=(ESP_URL,), daemon=True)
#     network_thread.start()

#     # --- MediaPipe and OpenCV Setup ---
#     mp_draw = mp.solutions.drawing_utils
#     mp_hand = mp.solutions.hands
#     tipIds = [4, 8, 12, 16, 20]

#     video = cv2.VideoCapture(0)

#     last_sent_time = 0
#     SEND_INTERVAL = 0.25 # Send a maximum of 4 commands per second

#     print("🚀 Starting hand tracking...")
#     with mp_hand.Hands(min_detection_confidence=0.5,
#                        min_tracking_confidence=0.5) as hands:
#         while True:
#             ret, image = video.read()
#             if not ret:
#                 break

#             # Process the image to find hands
#             image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
#             results = hands.process(image_rgb)
#             image = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR)

#             lmList = []
#             if results.multi_hand_landmarks:
#                 for hand_landmark in results.multi_hand_landmarks:
#                     for id, lm in enumerate(hand_landmark.landmark):
#                         h, w, c = image.shape
#                         cx, cy = int(lm.x * w), int(lm.y * h)
#                         lmList.append([id, cx, cy])
#                     mp_draw.draw_landmarks(image, hand_landmark, mp_hand.HAND_CONNECTIONS)

#             # Check if enough time has passed to send a new command
#             if len(lmList) != 0 and (time.time() - last_sent_time > SEND_INTERVAL):
#                 fingers = []
#                 # Thumb (x-axis)
#                 if lmList[tipIds[0]][1] > lmList[tipIds[0] - 1][1]:
#                     fingers.append(1)
#                 else:
#                     fingers.append(0)

#                 # Other fingers (y-axis)
#                 for id in range(1, 5):
#                     if lmList[tipIds[id]][2] < lmList[tipIds[id] - 2][2]:
#                         fingers.append(1)
#                     else:
#                         fingers.append(0)
                
#                 # Calculate angles and PUT them into the queue for the network thread
#                 angles = {
#                     "thumb": 90 if fingers[0] == 1 else 0,
#                     "index": 0 if fingers[1] == 1 else 90,
#                     "middle": 0 if fingers[2] == 1 else 180,
#                     "ring": 0 if fingers[3] == 1 else 90,
#                     "pinky": 90 if fingers[4] == 1 else 0
#                 }
#                 command_queue.put(angles)
#                 last_sent_time = time.time()

#             # The video display is now in the main loop and will NEVER be blocked by networking
#             cv2.imshow("Robotic Hand Control", image)
#             if cv2.waitKey(1) & 0xFF == ord('q'):
#                 break

#     video.release()
#     cv2.destroyAllWindows()


#above code is without flask 
import cv2
import mediapipe as mp
import time
import requests
import threading
import queue
from flask import Flask, render_template, Response

# --- Flask App Initialization ---
app = Flask(__name__)

# --- Thread-safe queue to hold commands for the ESP8266 ---
command_queue = queue.Queue()

# --- Global variable for ESP URL (will be set when the app starts) ---
ESP_URL = ""

# --- Network Worker Function (runs on a separate thread) ---
def send_commands_worker():
    """This function runs in the background, sending commands from the queue."""
    print("🚀 Network worker thread started.")
    while True:
        try:
            angles = command_queue.get()
            requests.get(ESP_URL, params=angles, timeout=2.0)
            print(f"Sent: {angles}")
            command_queue.task_done()
        except requests.exceptions.RequestException as e:
            print(f"⚠️  Connection error: {e}")
        except Exception as e:
            print(f"An error occurred in the network thread: {e}")

# --- Video Generation Function ---
def generate_frames():
    """This function captures video, processes it, and yields frames for streaming."""
    video = cv2.VideoCapture(0)
    mp_hand = mp.solutions.hands
    mp_draw = mp.solutions.drawing_utils
    tipIds = [4, 8, 12, 16, 20]

    last_sent_time = 0
    SEND_INTERVAL = 0.25 # Send a maximum of 4 commands per second

    print("🚀 Starting hand tracking for video stream...")
    with mp_hand.Hands(min_detection_confidence=0.5, min_tracking_confidence=0.5) as hands:
        while True:
            success, image = video.read()
            if not success:
                break
            else:
                # Process the image to find hands
                image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                results = hands.process(image_rgb)
                
                lmList = []
                if results.multi_hand_landmarks:
                    for hand_landmark in results.multi_hand_landmarks:
                        for id, lm in enumerate(hand_landmark.landmark):
                            h, w, c = image.shape
                            cx, cy = int(lm.x * w), int(lm.y * h)
                            lmList.append([id, cx, cy])
                        mp_draw.draw_landmarks(image, hand_landmark, mp_hand.HAND_CONNECTIONS)

                # Check if enough time has passed to send a new command
                if len(lmList) != 0 and (time.time() - last_sent_time > SEND_INTERVAL):
                    fingers = []
                    # Thumb (x-axis)
                    if lmList[tipIds[0]][1] > lmList[tipIds[0] - 1][1]: fingers.append(1)
                    else: fingers.append(0)

                    # Other fingers (y-axis)
                    for id in range(1, 5):
                        if lmList[tipIds[id]][2] < lmList[tipIds[id] - 2][2]: fingers.append(1)
                        else: fingers.append(0)
                    
                    # Calculate angles and put them into the queue
                    angles = {
                        "thumb": 90 if fingers[0] == 1 else 0,
                        "index": 0 if fingers[1] == 1 else 90,
                        "middle": 0 if fingers[2] == 1 else 180,
                        "ring": 0 if fingers[3] == 1 else 90,
                        "pinky": 90 if fingers[4] == 1 else 0
                    }
                    command_queue.put(angles)
                    last_sent_time = time.time()

                # Encode the frame in JPEG format
                ret, buffer = cv2.imencode('.jpg', image)
                frame = buffer.tobytes()
                # Yield the frame in the multipart content type
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
    video.release()

# --- Flask Routes ---
@app.route('/')
def index():
    """Video streaming home page."""
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    """Video streaming route. Put this in the src attribute of an img tag."""
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

# --- Main Execution Block ---
if __name__ == '__main__':
    # Get the ESP8266 IP address from the user when starting the server
    ESP_IP = input("Enter the IP address of your ESP8266: ")
    if not ESP_IP:
        ESP_IP = "192.168.1.79" # Default if you just press Enter
    ESP_URL = f"http://{ESP_IP}/move"
    print(f"✅ Commands will be sent to: {ESP_URL}")

    # Start the network worker thread
    network_thread = threading.Thread(target=send_commands_worker, daemon=True)
    network_thread.start()

    # Start the Flask app
    # Use host='0.0.0.0' to make it accessible from other devices on your network
    app.run(host='0.0.0.0', port=5000, debug=False)