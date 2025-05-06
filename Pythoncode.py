import cv2
import pytesseract
import serial
import numpy as np
import time

# Set the Tesseract OCR path
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def extract_number_plate(frame):
    # Convert to grayscale
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # Apply Gaussian Blur to remove noise
    gray = cv2.GaussianBlur(gray, (5, 5), 0)

    # Edge detection using Canny
    edges = cv2.Canny(gray, 50, 150)

    # Find contours
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Sort contours by area and keep the largest ones
    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:10]

    number_plate = None
    for contour in contours:
        # Approximate the contour
        approx = cv2.approxPolyDP(contour, 0.02 * cv2.arcLength(contour, True), True)

        # If the contour has 4 corners, assume it's a number plate
        if len(approx) == 4:
            x, y, w, h = cv2.boundingRect(approx)
            number_plate = gray[y:y+h, x:x+w]  # Crop the plate region
            
            # Draw rectangle around detected plate for debugging
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            break

    if number_plate is None:
        print("No number plate detected!")
        return ""

    # Resize for better OCR accuracy
    number_plate = cv2.resize(number_plate, (number_plate.shape[1] * 2, number_plate.shape[0] * 2))

    # Apply Adaptive Threshold
    number_plate = cv2.adaptiveThreshold(number_plate, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)

    # Save processed image for debugging
    cv2.imwrite("detected_plate.jpg", number_plate)
    cv2.imshow("Detected Plate Region", number_plate)  # Show the detected plate for debugging

    # OCR Config: Use "--psm 6" for structured text
    custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'

    # Extract text using Tesseract
    text = pytesseract.image_to_string(number_plate, config=custom_config)

    return text.strip()

# Initialize serial communication (Handle errors)
try:
    arduino = serial.Serial('COM3', 9600, timeout=1)
    time.sleep(2)
    print("Connected to Arduino.")
except serial.SerialException:
    print("Error: Could not open serial port. Check the connection.")
    arduino = None

# Open webcam
cap = cv2.VideoCapture(1)
if not cap.isOpened():
    print("Error: Could not access the webcam.")
    exit()
while True:
    ret, frame = cap.read()
    if not ret:
        print("Error: Could not read from the webcam.")
        break

    cv2.imshow("Webcam Feed", frame)

    if cv2.waitKey(1) & 0xFF == ord('c'):  # Press 'c' to capture
        print("Processing Image...")
        number_plate = extract_number_plate(frame)
        print("Extracted Number Plate:", number_plate)

        # Send extracted number to Arduino (only if connected)
        if number_plate and arduino:
            arduino.write((number_plate + "\n").encode())

        # Display extracted number plate in a separate window
        display_frame = 255 * np.ones((200, 400, 3), dtype=np.uint8)
        cv2.putText(display_frame, number_plate, (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
        cv2.imshow("Detected Number Plate", display_frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):  # Press 'q' to quit
        break

cap.release()
cv2.destroyAllWindows()