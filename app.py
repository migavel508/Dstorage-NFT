import cv2
import numpy as np
import pyttsx3
from keras.models import load_model
from keras.preprocessing.image import img_to_array

# Load pre-trained emotion recognition model (use FER2013-based CNN model)
emotion_model = load_model('C:/Users/migavel/Downloads/emotion_model.hdf5')

# Initialize Text-to-Speech engine
tts_engine = pyttsx3.init()

# Emotion labels based on FER2013 dataset
emotion_labels = ['Angry', 'Disgust', 'Fear', 'Happy', 'Sad', 'Surprise', 'Neutral']

# Start capturing video from the webcam
cap = cv2.VideoCapture(0)

def detect_emotion(frame):
    # Convert to grayscale for the emotion detection model
    gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    # Use OpenCV's face detection
    face_detector = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    faces = face_detector.detectMultiScale(gray_frame, scaleFactor=1.3, minNeighbors=5)

    for (x, y, w, h) in faces:
        face = gray_frame[y:y+h, x:x+w]
        face = cv2.resize(face, (64, 64))
        face = face.astype('float') / 255.0
        face = img_to_array(face)
        face = np.expand_dims(face, axis=0)

        # Predict emotion
        emotion_prediction = emotion_model.predict(face)[0]
        max_index = np.argmax(emotion_prediction)
        emotion_label = emotion_labels[max_index]
        
        # Speak the emotion out loud
        tts_engine.say(f"You look {emotion_label}")
        tts_engine.runAndWait()

        # Draw a rectangle around the face and the emotion label
        cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 0), 2)
        cv2.putText(frame, emotion_label, (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)
    
    return frame

while cap.isOpened():
    success, frame = cap.read()
    if not success:
        break

    # Detect emotion and speak it
    frame_with_emotion = detect_emotion(frame)

    # Display the video feed
    cv2.imshow('Emotion Detection', frame_with_emotion)

    # Exit loop on 'q' key press
    if cv2.waitKey(5) & 0xFF == ord('q'):
        break

# Release the webcam and close windows
cap.release()
cv2.destroyAllWindows()
