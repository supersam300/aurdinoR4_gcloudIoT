// All necessary libraries
#include <Servo.h>
#include <WiFiS3.h>
#include <WiFiSSLClient.h>
#include <ArduinoJson.h>
#include <Base64.h> 
#include "arduino_secrets.h"


const char* server = "webhook-forwarder-431890423803.asia-southeast1.run.app";
const String request_path = "/";


const int trigpin = 7;
const int echopin = 8;
long duration;
Servo myserv;


bool notificationSent = false;



int caldistance() {
  digitalWrite(trigpin, LOW); delayMicroseconds(2);
  digitalWrite(trigpin, HIGH); delayMicroseconds(10);
  digitalWrite(trigpin, LOW);
  duration = pulseIn(echopin, HIGH);
  return duration * 0.034 / 2;
}

void sendToCloudFunction(String payload) {
  WiFiSSLClient client;
  Serial.println("\nConnecting to Cloud Function...");

  if (client.connect(server, 443)) {
    Serial.println("Connected. Sending data...");

    client.println("POST " + request_path + " HTTP/1.1");
    client.println("Host: " + String(server));
    client.println("Authorization: Bearer " + String(SECRET_API_KEY));
    client.println("Content-Type: application/json");
    client.print("Content-Length: ");
    client.println(payload.length());
    client.println("Connection: close");
    client.println();
    client.print(payload);
    client.println();

    Serial.println("Data sent! Payload:");
    Serial.println(payload);
  } else {
    Serial.println("Connection to Cloud Function failed!");
  }
  delay(200);
  client.stop();
}



void setup() {
  Serial.begin(9600);
  pinMode(trigpin, OUTPUT); pinMode(echopin, INPUT);
  myserv.attach(9);

  Serial.print("Connecting to WiFi");
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500); Serial.print(".");
  }
  Serial.println("\nWiFi connected");
}


void loop() {
  for (int angle = 15; angle <= 180; angle++) {
    myserv.write(angle);
    delay(30);

    int distance = caldistance();

    if (distance < 30 && distance > 0 && !notificationSent) {
      Serial.println(" OBJECT DETECTED :3. Preparing Pub/Sub payload OwO");

  
      JsonDocument sensorDataDoc;
      sensorDataDoc["alert"] = "object_detected";
      sensorDataDoc["value"] = distance;
      sensorDataDoc["angle"] = angle;

      String sensorDataString;
      serializeJson(sensorDataDoc, sensorDataString);

      
      int inputLength = sensorDataString.length();
      int encodedLength = Base64.encodedLength(inputLength);
      char base64EncodedData[encodedLength + 1]; 
      Base64.encode(base64EncodedData, (char*)sensorDataString.c_str(), inputLength);

      
      JsonDocument finalPayloadDoc;
      JsonObject message = finalPayloadDoc.createNestedObject("message");
      JsonObject attributes = message.createNestedObject("attributes");
      attributes["thing_id"] = "arduino-radar-1";
      message["data"] = base64EncodedData; 

  
      String finalPayload;
      serializeJson(finalPayloadDoc, finalPayload);


      sendToCloudFunction(finalPayload);

      notificationSent = true;
    }
    else if (distance >= 30 && notificationSent) {
      Serial.println("Object has moved away. Re-arming system.");
      notificationSent = false;
    }
  }
  delay(1000);
}