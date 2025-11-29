#include <Servo.h>
#include <WiFiS3.h>
#include <WiFiSSLClient.h>
#include <ArduinoJson.h>
#include <Base64.h> 
#include "arduino_secrets.h"

const char* server = "webhook-forwarder-431890423803.asia-southeast1.run.app";
const String request_path = "/";
const int trigPins[3] = {2, 4, 6};
const int echoPins[3] = {3, 5, 7};
Servo myserv;

int calDistance(int trigPin, int echoPin) {
  long duration;
  digitalWrite(trigPin, LOW); delayMicroseconds(2);
  digitalWrite(trigPin, HIGH); delayMicroseconds(10);
  digitalWrite(trigPin, LOW);
  duration = pulseIn(echoPin, HIGH, 30000); 
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
  for (int i = 0; i < 3; i++) {
    pinMode(trigPins[i], OUTPUT);
    pinMode(echoPins[i], INPUT);
  }
  myserv.attach(9);
  Serial.print("Connecting to WiFi");
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi connected");
}

void loop() {
  int distances[3];
  String statuses[3];

  for (int i = 0; i < 3; i++) {

    pinMode(trigPins[i], OUTPUT);
    pinMode(echoPins[i], INPUT);
    long duration;
    digitalWrite(trigPins[i], LOW);
    delayMicroseconds(2);
    digitalWrite(trigPins[i], HIGH);
    delayMicroseconds(10);
    digitalWrite(trigPins[i], LOW);
    duration = pulseIn(echoPins[i], HIGH, 30000);
    distances[i] = duration * 0.034 / 2;
    Serial.print("Slot "); Serial.print(i+1); Serial.print(" duration: ");
    Serial.print(duration); Serial.print(", Distance: "); Serial.println(distances[i]);

    if (distances[i] <= 2 && distances[i] > 0) {
      statuses[i] = "occupied";
    } else {
      statuses[i] = "vacant";
    }
    Serial.print(" Status: "); Serial.println(statuses[i]);
  }

  JsonDocument finalPayloadDoc;
  JsonObject message = finalPayloadDoc.createNestedObject("message");
  JsonObject attributes = message.createNestedObject("attributes");
  attributes["thing_id"] = "parking-lot-1";
  JsonArray slots = message.createNestedArray("slots");

  for (int i = 0; i < 3; i++) {
    JsonObject slot = slots.createNestedObject();
    slot["slot_id"] = String("slot") + String(i+1);
    slot["distance_cm"] = distances[i];
    slot["status"] = statuses[i];
  }
  message["timestamp"] = String(millis());

  String sensorDataString;
  serializeJson(finalPayloadDoc, sensorDataString);
  int inputLength = sensorDataString.length();
  int encodedLength = Base64.encodedLength(inputLength);
  char base64EncodedData[encodedLength + 1]; 
  Base64.encode(base64EncodedData, (char*)sensorDataString.c_str(), inputLength);

  JsonDocument payloadDoc;
  JsonObject msg = payloadDoc.createNestedObject("message");
  msg["data"] = base64EncodedData;
  JsonObject attrs = msg.createNestedObject("attributes");
  attrs["thing_id"] = "parking-lot-1";
  String finalPayload;
  serializeJson(payloadDoc, finalPayload);

  sendToCloudFunction(finalPayload);
  delay(1000);
}
