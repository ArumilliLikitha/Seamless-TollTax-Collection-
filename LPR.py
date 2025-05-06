import cv2
import imutils
import numpy as np
import pytesseract
import serial
import time
import serial.tools.list_ports

def recognize_license_plate(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.bilateralFilter(gray, 11, 17, 17)
    edged = cv2.Canny(gray, 30, 200)
    plate_text = ""
    try:
        cnts = cv2.findContours(edged.copy(), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        cnts = imutils.grab_contours(cnts)
        cnts = sorted(cnts, key=cv2.contourArea, reverse=True)[:10]
        screenCnt = None
        for c in cnts:
            peri = cv2.arcLength(c, True)
            approx = cv2.approxPolyDP(c, 0.018 * peri, True)
            if len(approx) == 4:
                screenCnt = approx
                break
        if screenCnt is not None:
            mask = np.zeros(gray.shape, np.uint8)
            new_image = cv2.drawContours(mask, [screenCnt], 0, 255, -1)
            new_image = cv2.bitwise_and(frame, frame, mask=mask)
            (x, y) = np.where(mask == 255)
            (topx, topy) = (np.min(x), np.min(y))
            (bottomx, bottomy) = (np.max(x), np.max(y))
            cropped_img = gray[topx:bottomx + 1, topy:bottomy + 1]
            plate_text = pytesseract.image_to_string(cropped_img, config="-c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
            plate_text = plate_text.strip()
    except Exception as e:
        print("Error:", e)
    return plate_text

# Find Arduino Uno port
def find_arduino_port():
    ports = serial.tools.list_ports.comports()
    for port, desc, hwid in sorted(ports):
        if 'arduino' in desc.lower():
            return port
    return None

arduino_port = find_arduino_port()
if arduino_port is None:
    print("Arduino Uno not found.")
    exit()

# Open serial port to communicate with Arduino Uno
ser = serial.Serial(arduino_port, 9600)

cap = cv2.VideoCapture(8080)

# Set the desired resolution
width = 640
height = 480
cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

while True:
    ret, frame = cap.read()
    if not ret:
        break
    # Resize the frame
    frame = cv2.resize(frame, (width, height))
    text = recognize_license_plate(frame)
    if text:
        print("Recognized License Plate:", text)
        # Print last four characters with '*' mark
        last_four_characters = text[-4:] + "*"
        print("Last four characters:", last_four_characters)
        
        # Send last four characters to Arduino Uno
        ser.write(last_four_characters.encode())
        time.sleep(1)  # Wait for 1 second for the Arduino to process the data
    
    cv2.imshow("License Plate Recognition", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
