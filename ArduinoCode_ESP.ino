#include <WiFi.h>
#include <HTTPClient.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

// OLED settings
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
#define OLED_RESET    -1
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);

// WiFi Credentials
const char* ssid = "sweety";
const char* password = "123456789";

// SMS API Details
const char* apiKey = "1UZlACpEYvvN";
const char* baseURL = "https://www.circuitdigest.cloud/send_sms";
const char* mobileNumber = "917893097464";
const char* tollPlazaName = "Tumkur Toll Booth";

// Template IDs
const char* billTemplateID1 = "101";
const char* billTemplateID2 = "101";
const char* alertTemplateID1 = "115";
const char* alertTemplateID2 = "115";

// Variables
String receivedPlate = "";
String receivedRFID = "";
unsigned long lastDataTime = 0;
bool waitingForMatch = false;

void setup() {
  Serial.begin(115200);
  Serial2.begin(9600, SERIAL_8N1, 16, 17);

  WiFi.begin(ssid, password);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nConnected to WiFi!");

  if (!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    Serial.println("❌ OLED init failed");
    while (true);
  }

  display.clearDisplay();
  display.setTextSize(1);
  display.setTextColor(WHITE);
  display.setCursor(0, 0);
  display.println("System Ready");
  display.display();
}

void loop() {
  checkSerialFromUno();
  checkTimeout();
}

void checkSerialFromUno() {
  while (Serial2.available()) {
    String data = Serial2.readStringUntil('\n');
    data.trim();
    Serial.println(">> From UNO: " + data);

    if (data.startsWith("Scanned RFID UID:")) {
      receivedRFID = data.substring(String("Scanned RFID UID:").length());
      receivedRFID.trim();
      lastDataTime = millis();
      waitingForMatch = true;
      showRFIDInfo(receivedRFID);

    } else if (data.startsWith("NUM:") || data.startsWith("Received Number Plate:")) {
      int idx = data.indexOf(":");
      receivedPlate = data.substring(idx + 1);
      receivedPlate.trim();
      lastDataTime = millis();
      waitingForMatch = true;

    } else if (data == "match_ok") {
      Serial.println("✅ Match OK from UNO. Sending Bill SMS...");
      sendBillSMS(receivedPlate, receivedRFID);
      resetInputs();

    } else if (data == "only_number_plate") {
      Serial.println("⚠ Only Number Plate detected. Sending Alert SMS...");
      sendAlertSMS(receivedPlate, receivedRFID);
      resetInputs();

    } else if (data == "only_rfid") {
      Serial.println("⚠ Only RFID detected. Sending Alert SMS...");
      sendAlertSMS(receivedPlate, receivedRFID);
      resetInputs();
    }
  }
}

void checkTimeout() {
  if (waitingForMatch && millis() - lastDataTime > 5000) {
    Serial.println("⏳ Timeout: RFID/Plate mismatch");
    sendAlertSMS(receivedPlate, receivedRFID);
    resetInputs();
  }
}

void resetInputs() {
  receivedPlate = "";
  receivedRFID = "";
  waitingForMatch = false;
  clearOLED();
}

void showRFIDInfo(String rfid) {
  display.clearDisplay();
  display.setCursor(0, 0);
  display.println("RFID Detected");

  if (rfid == "23109920") {
    display.println("Name: prabhat");
    display.println("Number: 8509972970");
    display.println("Plate: DL1CAC7637");
  } else if (rfid == "85865BAE") {
    display.println("Name: balu");
    display.println("Number: 9502866471");
    display.println("Plate: ML05Z7777");
  } else {
    display.println("Unknown RFID");
  }

  display.display();
}

void clearOLED() {
  display.clearDisplay();
  display.setCursor(0, 0);
  display.display();
}

void sendBillSMS(String plate, String rfid) {
  plate.trim();
  plate.toUpperCase();
  rfid.trim();

  if (rfid == "85865BAE" && plate == "ML05Z7777") {
    Serial.println(plate + " with RFID " + rfid + " detected. Toll tax paid successfully National Highways Authority of India.");
    sendSMS(plate, rfid, billTemplateID1);

  } else if (rfid == "23109920" && plate == "DL1CAC7637") {
    Serial.println(plate + " with RFID " + rfid + " detected. Toll tax paid successfully National Highways Authority of India.");
    sendSMS(plate, rfid, billTemplateID2);

  } else {
    Serial.println("❌ Mismatch in plate and RFID. No billing SMS sent.");
    Serial.print("Plate received: [");
    Serial.print(plate);
    Serial.println("]");
    Serial.print("RFID received: [");
    Serial.print(rfid);
    Serial.println("]");
  }
}

void sendAlertSMS(String plate, String rfid) {
  Serial.println("🚨 Alert Triggered: Mismatch or missing data.");
  Serial.println("Plate: " + plate);
  Serial.println("RFID: " + rfid);

  if (rfid == "85865BAE") {
    sendSMS(plate, rfid, alertTemplateID1);
  } else if (rfid == "23109920") {
    sendSMS(plate, rfid, alertTemplateID2);
  } else {
    sendSMS(plate, rfid, alertTemplateID2); // default alert
  }
}

void sendSMS(String plate, String rfid, const char* templateID) {
  HTTPClient http;
  String url = String(baseURL) + "?ID=" + templateID;

  http.begin(url);
  http.addHeader("Content-Type", "application/json");
  http.addHeader("Authorization", apiKey);

  String var1 = (String(templateID).startsWith("10")) ? "Toll Confirmed" : "Alert Triggered";
  String var2 = "Plate:" + plate + " RFID:" + rfid;

  if (var1.length() > 30) var1 = var1.substring(0, 30);
  if (var2.length() > 30) var2 = var2.substring(0, 30);

  String payload = "{\"mobiles\":\"" + String(mobileNumber) +
                   "\",\"var1\":\"" + var1 +
                   "\",\"var2\":\"" + var2 + "\"}";

  Serial.println("Payload being sent:");
  Serial.println(payload);

  int httpCode = http.POST(payload);
  if (httpCode == 200) {
    Serial.println("✅ SMS sent successfully.");
  } else {
    Serial.print("❌ SMS failed. Code: ");
    Serial.println(httpCode);
    Serial.println(http.getString());
  }

  http.end();
}