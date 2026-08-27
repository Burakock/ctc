// ============================================================
//  INTERLOCKING ENGINE IMPLEMENTATION
//  Rota Kilitleme, Çakışma Tespiti, Sinyal Hesaplama
// ============================================================

#include "interlocking_engine.h"

// ---- YAPICI ----
InterLockingEngine::InterLockingEngine() : activeRouteCount(0), isInitialized(false) {
  // İnit sıfırla
  for (int i = 0; i < MAX_BLOCKS; i++) {
    blocks[i].id = i;
    blocks[i].occupancy = BLOCK_EMPTY;
    blocks[i].signal = SIGNAL_RED;
    blocks[i].parentRoute = -1;
    snprintf(blocks[i].name, 16, "B%d", i);
  }
  
  for (int i = 0; i < MAX_SWITCHES; i++) {
    switches[i].id = i;
    switches[i].position = SWITCH_NORMAL;
    switches[i].isLocked = false;
    switches[i].lockedByRoute = -1;
    switches[i].lastMoveTime = 0;
    snprintf(switches[i].name, 16, "X%d", i + 1);
  }
  
  for (int i = 0; i < MAX_ROUTES; i++) {
    routes[i].id = i;
    routes[i].state = ROUTE_INACTIVE;
    routes[i].isValid = false;
    routes[i].blockCount = 0;
  }
  
  memset(activeRoutes, -1, sizeof(activeRoutes));
}

// ---- İNİTYALİZASYON ----
void InterLockingEngine::initialize() {
  // Tüm rotaları doğrula
  for (int i = 0; i < MAX_ROUTES; i++) {
    if (routes[i].isValid) {
      validateRouteDefinition(i);
    }
  }
  
  // Çakışma matrisini oluştur
  buildConflictMatrix();
  
  isInitialized = true;
  Serial.println("[ILE] InterLockingEngine initialized successfully!");
}

// ---- ROTA TANITIMI ----
bool InterLockingEngine::defineRoute(int routeId, const char* routeName,
                                      int blocks[], int blockCount,
                                      int switchReqs[]) {
  // Geçerlik kontrol
  if (routeId < 0 || routeId >= MAX_ROUTES) {
    Serial.println("[ERR] Route ID out of range!");
    return false;
  }
  
  if (blockCount <= 0 || blockCount > 20) {
    Serial.println("[ERR] Invalid block count!");
    return false;
  }
  
  // Rota tanımla
  routes[routeId].id = routeId;
  strncpy(routes[routeId].name, routeName, 31);
  routes[routeId].blockCount = blockCount;
  routes[routeId].state = ROUTE_INACTIVE;
  
  // Blokları kopyala
  for (int i = 0; i < blockCount; i++) {
    routes[routeId].blocks[i] = blocks[i];
  }
  
  // Makas gereksinimlerini kopyala
  for (int i = 0; i < MAX_SWITCHES; i++) {
    routes[routeId].switchRequirements[i] = switchReqs[i];
  }
  
  routes[routeId].isValid = true;
  
  Serial.print("[ILE] Route defined: ");
  Serial.print(routeId);
  Serial.print(" - ");
  Serial.println(routeName);
  
  return true;
}

// ---- ROTA İSTEĞİ (ANA MANTIK) ----
ErrorCode InterLockingEngine::requestRoute(int routeId) {
  // Rota geçerli mi?
  if (routeId < 0 || routeId >= MAX_ROUTES || !routes[routeId].isValid) {
    return ERR_ROUTE_NOT_FOUND;
  }
  
  Route& route = routes[routeId];
  
  // Adım 1: Tüm bloklar boş mu?
  for (int i = 0; i < route.blockCount; i++) {
    int blockId = route.blocks[i];
    if (blocks[blockId].occupancy == BLOCK_OCCUPIED) {
      Serial.print("[ERR] Block occupied: B");
      Serial.println(blockId);
      return ERR_BLOCKS_OCCUPIED;
    }
  }
  
  // Adım 2: Makas konumları uyumlu mu?
  for (int i = 0; i < MAX_SWITCHES; i++) {
    int req = route.switchRequirements[i];
    if (req != -1) {  // -1 = önemli değil
      if (switches[i].position != (SwitchPosition)req) {
        Serial.print("[WAR] Switch mismatch: X");
        Serial.print(i + 1);
        Serial.print(" needs ");
        Serial.println(req);
        return ERR_SWITCH_MISMATCH;
      }
    }
  }
  
  // Adım 3: Çakışan aktif rotalar var mı?
  for (int i = 0; i < activeRouteCount; i++) {
    int activeId = activeRoutes[i];
    if (activeId != -1 && hasConflict(routeId, activeId)) {
      Serial.print("[ERR] Conflict with active route: R");
      Serial.println(activeId);
      return ERR_CONFLICT_EXISTS;
    }
  }
  
  // Adım 4: Rota uygun, LE'yi kitle
  lockRoute(routeId);
  
  // Adım 5: Rotayı aktif listesine ekle
  for (int i = 0; i < MAX_CONCURRENT_ROUTES; i++) {
    if (activeRoutes[i] == -1) {
      activeRoutes[i] = routeId;
      activeRouteCount++;
      break;
    }
  }
  
  route.state = ROUTE_ACTIVE;
  route.activatedAt = millis();
  
  Serial.print("[OK] Route activated: R");
  Serial.println(routeId);
  
  return ERR_NONE;
}

// ---- ROTA İPTALİ ----
bool InterLockingEngine::cancelRoute(int routeId) {
  if (routeId < 0 || routeId >= MAX_ROUTES) return false;
  
  Route& route = routes[routeId];
  
  // Rotayı pasif yap
  route.state = ROUTE_INACTIVE;
  
  // Makasları unlock et
  unlockRoute(routeId);
  
  // Aktif listeden kaldır
  for (int i = 0; i < MAX_CONCURRENT_ROUTES; i++) {
    if (activeRoutes[i] == routeId) {
      activeRoutes[i] = -1;
      activeRouteCount--;
    }
  }
  
  Serial.print("[OK] Route canceled: R");
  Serial.println(routeId);
  
  return true;
}

// ---- ROTA DURUMU SORGU ----
RouteState InterLockingEngine::getRouteState(int routeId) {
  if (routeId < 0 || routeId >= MAX_ROUTES) return ROUTE_INACTIVE;
  return routes[routeId].state;
}

// ---- İç Fonksiyon: Rota Kilitle ----
void InterLockingEngine::lockRoute(int routeId) {
  Route& route = routes[routeId];
  
  // Rotada yer alan makasları kilitle
  for (int i = 0; i < MAX_SWITCHES; i++) {
    if (route.switchRequirements[i] != -1) {
      switches[i].isLocked = true;
      switches[i].lockedByRoute = routeId;
    }
  }
  
  // Rotada yer alan blokları işaretle
  for (int i = 0; i < route.blockCount; i++) {
    blocks[route.blocks[i]].parentRoute = routeId;
  }
}

// ---- İç Fonksiyon: Rota Kilidini Aç ----
void InterLockingEngine::unlockRoute(int routeId) {
  Route& route = routes[routeId];
  
  // Makasları unlock et
  for (int i = 0; i < MAX_SWITCHES; i++) {
    if (switches[i].lockedByRoute == routeId) {
      switches[i].isLocked = false;
      switches[i].lockedByRoute = -1;
    }
  }
  
  // Blok işaretlemesini temizle
  for (int i = 0; i < route.blockCount; i++) {
    if (blocks[route.blocks[i]].parentRoute == routeId) {
      blocks[route.blocks[i]].parentRoute = -1;
    }
  }
}

// ---- ÇAKIŞMA MATRISI OLUŞTUR ----
void InterLockingEngine::buildConflictMatrix() {
  for (int r1 = 0; r1 < MAX_ROUTES; r1++) {
    if (!routes[r1].isValid) continue;
    
    for (int r2 = r1 + 1; r2 < MAX_ROUTES; r2++) {
      if (!routes[r2].isValid) continue;
      
      bool conflict = hasBlockConflict(r1, r2) || hasSwitchConflict(r1, r2);
      
      conflictMatrix[r1][r2].route1 = r1;
      conflictMatrix[r1][r2].route2 = r2;
      conflictMatrix[r1][r2].exists = conflict;
      
      if (conflict) {
        snprintf(conflictMatrix[r1][r2].reason, 64,
                 "R%d and R%d share blocks/switches", r1, r2);
      }
    }
  }
  
  Serial.println("[ILE] Conflict matrix built.");
}

// ---- İç Fonksiyon: Blok Çakışması Kontrolü ----
bool InterLockingEngine::hasBlockConflict(int route1, int route2) {
  Route& r1 = routes[route1];
  Route& r2 = routes[route2];
  
  for (int i = 0; i < r1.blockCount; i++) {
    for (int j = 0; j < r2.blockCount; j++) {
      if (r1.blocks[i] == r2.blocks[j]) {
        return true;  // Aynı blok
      }
    }
  }
  
  return false;
}

// ---- İç Fonksiyon: Makas Çakışması Kontrolü ----
bool InterLockingEngine::hasSwitchConflict(int route1, int route2) {
  Route& r1 = routes[route1];
  Route& r2 = routes[route2];
  
  for (int i = 0; i < MAX_SWITCHES; i++) {
    int req1 = r1.switchRequirements[i];
    int req2 = r2.switchRequirements[i];
    
    if (req1 != -1 && req2 != -1) {
      if (req1 != req2) {
        return true;  // Makas aynı yerde ama farklı konum isteniyor
      }
    }
  }
  
  return false;
}

// ---- ÇAKIŞMA SORGU ----
bool InterLockingEngine::hasConflict(int route1, int route2) {
  if (route1 < 0 || route1 >= MAX_ROUTES ||
      route2 < 0 || route2 >= MAX_ROUTES) {
    return false;
  }
  
  if (route1 > route2) {
    int temp = route1;
    route1 = temp;
    route2 = route1;
  }
  
  if (route1 == route2) return false;
  
  return conflictMatrix[route1][route2].exists;
}

// ---- ÇAKIŞAN ROTALAR LISTELE ----
int InterLockingEngine::getConflictingRoutes(int routeId, int conflicts[]) {
  int count = 0;
  
  for (int i = 0; i < MAX_ROUTES; i++) {
    if (i != routeId && hasConflict(routeId, i)) {
      conflicts[count++] = i;
    }
  }
  
  return count;
}

// ---- BLOK İŞGAL GÜNCELLE ----
void InterLockingEngine::updateBlockOccupancy(int hatId, bool blocks[], int blockCount) {
  int startIdx = hatId * BLOCKS_PER_HAT;
  
  for (int i = 0; i < blockCount; i++) {
    int blockId = startIdx + i;
    if (blockId < MAX_BLOCKS) {
      blocks[blockId].occupancy = blocks[i] ? BLOCK_OCCUPIED : BLOCK_EMPTY;
    }
  }
}

// ---- MAKAS KONUMU GÜNCELLE ----
void InterLockingEngine::updateSwitchPosition(int switchId, SwitchPosition position) {
  if (switchId < 0 || switchId >= MAX_SWITCHES) return;
  
  switches[switchId].position = position;
  switches[switchId].lastMoveTime = millis();
}

// ---- BLOK İŞGAL SORGU ----
BlockState InterLockingEngine::getBlockOccupancy(int blockId) {
  if (blockId < 0 || blockId >= MAX_BLOCKS) return BLOCK_EMPTY;
  return blocks[blockId].occupancy;
}

// ---- MAKAS KONUMU SORGU ----
SwitchPosition InterLockingEngine::getSwitchPosition(int switchId) {
  if (switchId < 0 || switchId >= MAX_SWITCHES) return SWITCH_NORMAL;
  return switches[switchId].position;
}

// ---- SİNYAL HESAPLAMA ----
void InterLockingEngine::calculateSignals() {
  for (int i = 0; i < MAX_BLOCKS; i++) {
    Block& block = blocks[i];
    
    // Eğer blok işgal ise → KIRMIZı
    if (block.occupancy == BLOCK_OCCUPIED) {
      block.signal = SIGNAL_RED;
      continue;
    }
    
    // Eğer blok aktif bir rotanın parçası değilse → KIRMIZı (güvenlik)
    if (block.parentRoute == -1) {
      block.signal = SIGNAL_RED;
      continue;
    }
    
    // Blok boş ve rotanın parçası
    // Bir sonraki blok işgal mi?
    int nextBlockId = -1;
    Route& parentRoute = routes[block.parentRoute];
    for (int j = 0; j < parentRoute.blockCount - 1; j++) {
      if (parentRoute.blocks[j] == i) {
        nextBlockId = parentRoute.blocks[j + 1];
        break;
      }
    }
    
    if (nextBlockId != -1 && blocks[nextBlockId].occupancy == BLOCK_OCCUPIED) {
      block.signal = SIGNAL_YELLOW;  // Yaklaşma
    } else {
      block.signal = SIGNAL_GREEN;   // Açık
    }
  }
}

// ---- SİNYAL SORGU ----
SignalAspect InterLockingEngine::getSignal(int blockId) {
  if (blockId < 0 || blockId >= MAX_BLOCKS) return SIGNAL_RED;
  return blocks[blockId].signal;
}

// ---- MAKAS KOMUTU İŞLE ----
ErrorCode InterLockingEngine::processSwitchCommand(int switchId, SwitchPosition position) {
  if (switchId < 0 || switchId >= MAX_SWITCHES) {
    return ERR_INVALID_ROUTE;
  }
  
  Switch& sw = switches[switchId];
  
  // Makas kilitli mi?
  if (sw.isLocked) {
    Serial.print("[ERR] Switch locked by route: ");
    Serial.println(sw.lockedByRoute);
    return ERR_CONFLICT_EXISTS;
  }
  
  // Komut uygula
  sw.position = position;
  sw.lastMoveTime = millis();
  
  // İlgili rotaları iptal et (makasın konumu değiştiğinden)
  for (int i = 0; i < activeRouteCount; i++) {
    int routeId = activeRoutes[i];
    if (routeId != -1) {
      if (routes[routeId].switchRequirements[switchId] != -1) {
        cancelRoute(routeId);
      }
    }
  }
  
  return ERR_NONE;
}

// ---- ACİL DUR ----
void InterLockingEngine::processEmergencyStop() {
  // Tüm rotaları iptal et
  for (int i = 0; i < MAX_ROUTES; i++) {
    if (routes[i].state != ROUTE_INACTIVE) {
      cancelRoute(i);
    }
  }
  
  // Tüm sinyalleri KIRMIZI yap
  for (int i = 0; i < MAX_BLOCKS; i++) {
    blocks[i].signal = SIGNAL_RED;
  }
  
  Serial.println("[EMERGENCY] Emergency stop activated!");
}

// ---- SISTEM DURUMU SORGU ----
SystemStatus InterLockingEngine::getSystemStatus() {
  sysStatus.timestamp = millis();
  sysStatus.activeRouteCount = activeRouteCount;
  sysStatus.emergencyStop = false;
  sysStatus.errorCode = ERR_NONE;
  
  return sysStatus;
}

// ---- AKTİF ROTALAR LISTELE ----
int InterLockingEngine::getActiveRoutes(int routes[]) {
  int count = 0;
  for (int i = 0; i < MAX_CONCURRENT_ROUTES; i++) {
    if (activeRoutes[i] != -1) {
      routes[count++] = activeRoutes[i];
    }
  }
  return count;
}

// ---- DEBUG İNFO YAZDIR ----
void InterLockingEngine::printDebugInfo() {
  Serial.println("\n========== INTERLOCKING ENGINE DEBUG ==========");
  
  Serial.print("Active Routes: ");
  Serial.println(activeRouteCount);
  for (int i = 0; i < activeRouteCount; i++) {
    Serial.print("  R");
    Serial.println(activeRoutes[i]);
  }
  
  Serial.println("Locked Switches:");
  for (int i = 0; i < MAX_SWITCHES; i++) {
    if (switches[i].isLocked) {
      Serial.print("  X");
      Serial.print(i + 1);
      Serial.print(" (locked by R");
      Serial.print(switches[i].lockedByRoute);
      Serial.println(")");
    }
  }
  
  Serial.println("============================================\n");
}
