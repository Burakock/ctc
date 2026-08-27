// ============================================================
//  BOARD C — MASTER (+ MAKAS, henüz kurulmadıysa bu bölüm pasif kalır)
//  Görevi:
//   - BOARD A'dan (Serial1) Hat1 blok durumlarını almak
//   - BOARD B'den (Serial2) Hat2 blok durumlarını almak
//   - Hepsini birleştirip PC'ye (Serial/USB) JSON olarak yollamak
//   - PC'den gelen makas komutlarını uygulamak (makas kurulunca aktif olur)
// ============================================================

#include <Servo.h>

const int BLOK_SAYISI = 10;
bool h1[BLOK_SAYISI];
bool h2[BLOK_SAYISI];

// ---- MAKAS (henüz kablolamadıysan bu kısım dokunulmadan kalabilir) ----
const int servoPins[6] = {2,3,4,5,6,7};
Servo servos[6];
int swState[3] = {0,0,0};        // 0 = Normal, 1 = Ters
const int swButtons[3] = {22,23,24};
bool makasKurulu = true;        // Makası kurunca bunu true yap

// ---- Haberleşme buffer'ları ----
String h1Buffer = "";
String h2Buffer = "";

unsigned long lastHeartbeat = 0;
bool heartbeatState = false;
unsigned long lastPcSend = 0;

void setup() {
  Serial.begin(9600);   // PC (GUI) buraya bağlanacak
  Serial1.begin(9600);  // BOARD A (Hat1)
  Serial2.begin(9600);  // BOARD B (Hat2)

  pinMode(13, OUTPUT);  // heartbeat LED

  if (makasKurulu) {
    for (int i = 0; i < 3; i++) pinMode(swButtons[i], INPUT_PULLUP);
    for (int i = 0; i < 6; i++) {
      servos[i].attach(servoPins[i]);
      servos[i].write(0); // başlangıç: Normal
    }
  }
}

void parseHat(String data, bool* arr) {
  int idx = data.indexOf(':');
  if (idx == -1) return;
  String bits = data.substring(idx + 1);
  for (int i = 0; i < BLOK_SAYISI && i < (int)bits.length(); i++) {
    arr[i] = (bits[i] == '1');
  }
}

void readFromBoards() {
  while (Serial1.available()) {
    char c = Serial1.read();
    if (c == '\n') { parseHat(h1Buffer, h1); h1Buffer = ""; }
    else h1Buffer += c;
  }
  while (Serial2.available()) {
    char c = Serial2.read();
    if (c == '\n') { parseHat(h2Buffer, h2); h2Buffer = ""; }
    else h2Buffer += c;
  }
}

void handleSwitchButtons() {
  if (!makasKurulu) return;
  for (int i = 0; i < 3; i++) {
    if (digitalRead(swButtons[i]) == LOW) {
      delay(200); // basit debounce
      swState[i] = !swState[i];
      int angle = swState[i] ? 90 : 0;
      servos[i * 2].write(angle);
      servos[i * 2 + 1].write(angle);
    }
  }
}

void applySwitchCommand(int idx, int val) {
  if (idx < 0 || idx > 2) return;
  swState[idx] = val;
  if (makasKurulu) {
    int angle = val ? 90 : 0;
    servos[idx * 2].write(angle);
    servos[idx * 2 + 1].write(angle);
  }
}

void readFromPC() {
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    // Örnek komut: "SW0:1" -> Makas 0'ı Ters konuma al
    if (cmd.startsWith("SW") && cmd.length() >= 5) {
      int idx = cmd.charAt(2) - '0';
      int val = cmd.charAt(4) - '0';
      applySwitchCommand(idx, val);
    }
  }
}

void sendToPC() {
  String json = "{\"h1\":[";
  for (int i = 0; i < BLOK_SAYISI; i++) {
    json += h1[i] ? "1" : "0";
    if (i < BLOK_SAYISI - 1) json += ",";
  }
  json += "],\"h2\":[";
  for (int i = 0; i < BLOK_SAYISI; i++) {
    json += h2[i] ? "1" : "0";
    if (i < BLOK_SAYISI - 1) json += ",";
  }
  json += "],\"sw\":[";
  for (int i = 0; i < 3; i++) {
    json += swState[i];
    if (i < 2) json += ",";
  }
  json += "]}";
  Serial.println(json);
}

void heartbeat() {
  if (millis() - lastHeartbeat > 500) {
    heartbeatState = !heartbeatState;
    digitalWrite(13, heartbeatState);
    lastHeartbeat = millis();
  }
}

void loop() {
  readFromBoards();
  handleSwitchButtons();
  readFromPC();
  heartbeat();

  if (millis() - lastPcSend > 250) {
    sendToPC();
    lastPcSend = millis();
  }
}
