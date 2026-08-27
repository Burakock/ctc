// ============================================================
//  BOARD C — MASTER with INTERLOCKING ENGINE
//  Yeni Modüler Yapı (SIL-4 Uyumlu)
// ============================================================

#include <Servo.h>
#include "../shared/common_types.h"
#include "../shared/config.h"
#include "interlocking_engine.h"
#include "route_manager.h"

// Global objeler
InterLockingEngine interlocking;
RouteManager routeManager(&interlocking);

// Servo motorları
Servo servos[6];
const int servoPins[6] = {2, 3, 4, 5, 6, 7};

// Haberleşme buffer'ları
String h1Buffer = "";
String h2Buffer = "";

// Zaman kontrolleri
unsigned long lastHeartbeat = 0;
unsigned long lastPcSend = 0;
unsigned long lastSignalUpdate = 0;
bool heartbeatState = false;

// Sistem durumu
bool systemReady = false;
bool emergencyStopActive = false;

// Blok durumu (Hat1 ve Hat2 için)
bool blockArrayHat1[15];
bool blockArrayHat2[15];

// ============================================================
// SETUP
// ============================================================

void setup() {
  Serial.begin(9600);   // PC (GUI)
  Serial1.begin(9600);  // BOARD A (Hat1)
  Serial2.begin(9600);  // BOARD B (Hat2)

  pinMode(13, OUTPUT);  // Heartbeat LED
  pinMode(28, INPUT_PULLUP);  // Emergency Stop butonu

  delay(100);

  // Servo'ları ayarla
  for (int i = 0; i < 6; i++) {
    servos[i].attach(servoPins[i]);
    servos[i].write(0);  // Başlangıç: Normal
  }

  // İnterlocking Engine'i init et
  interlocking.initialize();

  // 5-peronlu istasyon geometrisini tanımla
  routeManager.defineStationLayout();
  routeManager.printStationInfo();

  systemReady = true;

  Serial.println("\n[BOARD_C] ============================================");
  Serial.println("[BOARD_C] Railway CTC System - BOARD C MASTER");
  Serial.println("[BOARD_C] Modular Interlocking Engine (SIL-4)");
  Serial.println("[BOARD_C] ============================================");
  Serial.println("[BOARD_C] System initialized successfully!");
  Serial.println("[BOARD_C] Waiting for route requests...\n");
}

// ============================================================
// MAIN LOOP
// ============================================================

void loop() {
  // Haberleşme
  readFromBoards();
  readFromPC();

  // Sistem güvenliği
  checkEmergencyStop();

  // İnterlocking hesaplaması
  interlocking.updateBlockOccupancy(0, blockArrayHat1, 15);  // Hat1
  interlocking.updateBlockOccupancy(1, blockArrayHat2, 15);  // Hat2
  interlocking.calculateSignals();

  // Zaman görevleri
  updateHeartbeat();
  if (millis() - lastPcSend > BOARD_UPDATE_INTERVAL) {
    sendToPCJSON();
    lastPcSend = millis();
  }

  delay(10);
}

// ============================================================
// HABERLEŞME: BOARD A ve BOARD B'den Veri Oku
// ============================================================

void readFromBoards() {
  // BOARD A (Hat1) oku
  while (Serial1.available()) {
    char c = Serial1.read();
    if (c == '\n') {
      parseHatData(h1Buffer, blockArrayHat1, 0);
      h1Buffer = "";
    } else {
      h1Buffer += c;
    }
  }

  // BOARD B (Hat2) oku
  while (Serial2.available()) {
    char c = Serial2.read();
    if (c == '\n') {
      parseHatData(h2Buffer, blockArrayHat2, 1);
      h2Buffer = "";
    } else {
      h2Buffer += c;
    }
  }
}

void parseHatData(String data, bool* blocks, int hatId) {
  // Format: "H1:0010000000" veya "H2:0010000000"
  int idx = data.indexOf(':');
  if (idx == -1) return;

  String bits = data.substring(idx + 1);
  for (int i = 0; i < 15 && i < (int)bits.length(); i++) {
    blocks[i] = (bits[i] == '1');
  }
}

// ============================================================
// HABERLEŞME: PC'den Komut Oku
// ============================================================

void readFromPC() {
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();

    // Rota komutu: "R2" → Rota 2'yi aktive et
    if (cmd.startsWith("R") && cmd.length() >= 2) {
      int routeId = cmd.substring(1).toInt();
      ErrorCode err = interlocking.requestRoute(routeId);
      
      if (err == ERR_NONE) {
        Serial.print("[OK] Route ");
        Serial.print(routeId);
        Serial.println(" activated.");
      } else {
        Serial.print("[ERR] Route ");
        Serial.print(routeId);
        Serial.print(" - Error code: ");
        Serial.println(err);
        printErrorMessage(err);
      }
    }

    // Makas komutu: "SW0:1" → Makas 0'ı DIVERGING yap
    else if (cmd.startsWith("SW") && cmd.length() >= 5) {
      int switchId = cmd.charAt(2) - '0';
      int val = cmd.charAt(4) - '0';
      SwitchPosition pos = (val == 1) ? SWITCH_DIVERGING : SWITCH_NORMAL;
      
      ErrorCode err = interlocking.processSwitchCommand(switchId, pos);
      if (err == ERR_NONE) {
        applyServoCommand(switchId, val);
        Serial.print("[OK] Switch ");
        Serial.print(switchId);
        Serial.print(" set to ");
        Serial.println(val == 1 ? "DIVERGING" : "NORMAL");
      } else {
        Serial.print("[ERR] Switch command failed: ");
        Serial.println(err);
      }
    }

    // Rota iptali: "CANCEL:2" → Rota 2'yi iptal et
    else if (cmd.startsWith("CANCEL:")) {
      int routeId = cmd.substring(7).toInt();
      if (interlocking.cancelRoute(routeId)) {
        Serial.print("[OK] Route ");
        Serial.print(routeId);
        Serial.println(" canceled.");
      }
    }

    // Debug komutu: "DEBUG"
    else if (cmd == "DEBUG") {
      interlocking.printDebugInfo();
    }

    // Acil Dur komutu: "ESTOP"
    else if (cmd == "ESTOP") {
      activateEmergencyStop();
    }

    // Durum sorgulama: "STATUS"
    else if (cmd == "STATUS") {
      printSystemStatus();
    }
  }
}

// ============================================================
// SERVO KONTROL
// ============================================================

void applyServoCommand(int switchId, int value) {
  if (switchId < 0 || switchId >= 3) return;

  int angle = (value == 1) ? 90 : 0;
  
  // Her makas için 2 servo var (left + right tongue)
  servos[switchId * 2].write(angle);
  servos[switchId * 2 + 1].write(angle);

  interlocking.updateSwitchPosition(switchId, (SwitchPosition)value);
}

// ============================================================
// ACİL DUR
// ============================================================

void checkEmergencyStop() {
  if (digitalRead(28) == LOW) {  // Buton basıldı
    if (!emergencyStopActive) {
      activateEmergencyStop();
    }
  }
}

void activateEmergencyStop() {
  emergencyStopActive = true;
  interlocking.processEmergencyStop();
  
  // Tüm sinyalleri KIRMIZI yap
  for (int i = 0; i < 6; i++) {
    servos[i].write(0);  // Makasları NORMAL konuma al
  }
  
  Serial.println("\n========== EMERGENCY STOP ACTIVATED ==========");
  Serial.println("[EMERGENCY] All routes canceled!");
  Serial.println("[EMERGENCY] All signals set to RED!");
  Serial.println("[EMERGENCY] All switches moved to NORMAL!");
  Serial.println("=============================================\n");
}

// ============================================================
// HEARTBEAT LED
// ============================================================

void updateHeartbeat() {
  if (millis() - lastHeartbeat > HEARTBEAT_INTERVAL) {
    heartbeatState = !heartbeatState;
    digitalWrite(13, heartbeatState);
    lastHeartbeat = millis();
  }
}

// ============================================================
// PC'YE JSON GÖNDER
// ============================================================

void sendToPCJSON() {
  String json = "{\"h1\":[";
  
  // Hat 1 blokları
  for (int i = 0; i < 15; i++) {
    json += blockArrayHat1[i] ? "1" : "0";
    if (i < 14) json += ",";
  }
  
  json += "],\"h2\":[";
  
  // Hat 2 blokları
  for (int i = 0; i < 15; i++) {
    json += blockArrayHat2[i] ? "1" : "0";
    if (i < 14) json += ",";
  }
  
  json += "],\"sw\":[";
  
  // Makas durumları
  for (int i = 0; i < 3; i++) {
    json += (int)interlocking.getSwitchPosition(i);
    if (i < 2) json += ",";
  }
  
  json += "],\"routes\":[";
  
  // Aktif rotalar
  int activeRoutes[MAX_CONCURRENT_ROUTES];
  int count = interlocking.getActiveRoutes(activeRoutes);
  for (int i = 0; i < count; i++) {
    json += activeRoutes[i];
    if (i < count - 1) json += ",";
  }
  
  json += "]}";
  
  Serial.println(json);
}

// ============================================================
// UTILITY FONKSIYONLAR
// ============================================================

void printErrorMessage(ErrorCode err) {
  switch (err) {
    case ERR_NONE:
      Serial.println("  → No error.");
      break;
    case ERR_ROUTE_NOT_FOUND:
      Serial.println("  → Route not found or invalid.");
      break;
    case ERR_CONFLICT_EXISTS:
      Serial.println("  → Conflict with active route(s).");
      break;
    case ERR_BLOCKS_OCCUPIED:
      Serial.println("  → One or more blocks are occupied.");
      break;
    case ERR_SWITCH_MISMATCH:
      Serial.println("  → Switch position does not match route requirements.");
      break;
    case ERR_INVALID_ROUTE:
      Serial.println("  → Invalid route definition.");
      break;
    case ERR_TIMEOUT:
      Serial.println("  → Operation timeout.");
      break;
    default:
      Serial.println("  → Unknown error.");
  }
}

void printSystemStatus() {
  SystemStatus status = interlocking.getSystemStatus();
  
  Serial.println("\n========== SYSTEM STATUS ==========");
  Serial.print("Timestamp: ");
  Serial.println(status.timestamp);
  Serial.print("Active Routes: ");
  Serial.println(status.activeRouteCount);
  Serial.print("Emergency Stop: ");
  Serial.println(status.emergencyStop ? "YES" : "NO");
  Serial.print("Last Error: ");
  Serial.println(status.errorCode);
  Serial.println("===================================\n");
}
