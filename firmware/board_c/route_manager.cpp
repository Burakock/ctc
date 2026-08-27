// ============================================================
//  ROUTE MANAGER IMPLEMENTATION
//  5-Peronlu İstasyon Rota Tanımları
// ============================================================

#include "route_manager.h"

RouteManager::RouteManager(InterLockingEngine* ile) : engine(ile), definedRoutes(0) {}

void RouteManager::defineStationLayout() {
  /*
     HAT YAPISI (5-PERONLU İSTASYON):
     
     PERON 1: [B0]─[B1]─[X1]─[B2]─[B3]─[X2]─[B4]
     PERON 2: [B5]─[B6]─[X1]─[B7]─[B8]─[X2]─[B9]
     PERON 3: [B10]─[B11]─[X3]─[B12]─[B13]─[X4]─[B14]
     PERON 4: [B15]─[B16]─[X3]─[B17]─[B18]─[X4]─[B19]
     PERON 5: [B20]─[B21]─[X5]─[B22]─[B23]─[X6]─[B24]
     
     DEPO: [B25]─[B26]─[X7]─[B27]─[B28]
     
     X1, X2, X3, X4, X5, X6, X7 = Makaslar (7 makas)
  */

  Serial.println("\n=== ROUTE MANAGER: 5-Platform Station Layout ===\n");

  // ============================================================
  // GRUP 1: PERON 1 ROTASI (Girişten Peron 1'e)
  // ============================================================
  {
    int blocks[] = {0, 1, 2, 3, 4, -1};
    int switches[] = {-1, -1, -1, -1, -1, -1, -1};
    
    engine->defineRoute(0, "R00_ENTRY_TO_PLATFORM_1", blocks, 5, switches);
    definedRoutes++;
  }

  // ============================================================
  // GRUP 2: PERON 2 ROTASI (Girişten Peron 2'e)
  // ============================================================
  {
    int blocks[] = {5, 6, 7, 8, 9, -1};
    int switches[] = {-1, -1, -1, -1, -1, -1, -1};
    
    engine->defineRoute(1, "R01_ENTRY_TO_PLATFORM_2", blocks, 5, switches);
    definedRoutes++;
  }

  // ============================================================
  // GRUP 3: PERON 1 → PERON 2 GEÇİŞ (X1 DIVERGING)
  // ============================================================
  {
    int blocks[] = {2, 3, 7, 8, 9, -1};
    int switches[] = {1, -1, -1, -1, -1, -1, -1};  // X1 = DIVERGING(1)
    
    engine->defineRoute(2, "R02_P1_TO_P2_VIA_X1", blocks, 5, switches);
    definedRoutes++;
  }

  // ============================================================
  // GRUP 4: PERON 2 → PERON 1 GEÇİŞ (X1 NORMAL)
  // ============================================================
  {
    int blocks[] = {7, 8, 2, 3, 4, -1};
    int switches[] = {0, -1, -1, -1, -1, -1, -1};  // X1 = NORMAL(0)
    
    engine->defineRoute(3, "R03_P2_TO_P1_VIA_X1", blocks, 5, switches);
    definedRoutes++;
  }

  // ============================================================
  // GRUP 5: PERON 1 → PERON 2 GEÇİŞ (X2 DIVERGING)
  // ============================================================
  {
    int blocks[] = {3, 4, 9, -1};
    int switches[] = {-1, 1, -1, -1, -1, -1, -1};  // X2 = DIVERGING(1)
    
    engine->defineRoute(4, "R04_P1_TO_P2_VIA_X2", blocks, 3, switches);
    definedRoutes++;
  }

  // ============================================================
  // GRUP 6: PERON 2 → PERON 1 GEÇİŞ (X2 NORMAL)
  // ============================================================
  {
    int blocks[] = {8, 9, 4, -1};
    int switches[] = {-1, 0, -1, -1, -1, -1, -1};  // X2 = NORMAL(0)
    
    engine->defineRoute(5, "R05_P2_TO_P1_VIA_X2", blocks, 3, switches);
    definedRoutes++;
  }

  // ============================================================
  // GRUP 7: PERON 3 ROTASI
  // ============================================================
  {
    int blocks[] = {10, 11, 12, 13, 14, -1};
    int switches[] = {-1, -1, -1, -1, -1, -1, -1};
    
    engine->defineRoute(6, "R06_ENTRY_TO_PLATFORM_3", blocks, 5, switches);
    definedRoutes++;
  }

  // ============================================================
  // GRUP 8: PERON 4 ROTASI
  // ============================================================
  {
    int blocks[] = {15, 16, 17, 18, 19, -1};
    int switches[] = {-1, -1, -1, -1, -1, -1, -1};
    
    engine->defineRoute(7, "R07_ENTRY_TO_PLATFORM_4", blocks, 5, switches);
    definedRoutes++;
  }

  // ============================================================
  // GRUP 9: PERON 3 → PERON 4 GEÇİŞ (X3 DIVERGING)
  // ============================================================
  {
    int blocks[] = {12, 13, 17, 18, 19, -1};
    int switches[] = {-1, -1, 1, -1, -1, -1, -1};  // X3 = DIVERGING(1)
    
    engine->defineRoute(8, "R08_P3_TO_P4_VIA_X3", blocks, 5, switches);
    definedRoutes++;
  }

  // ============================================================
  // GRUP 10: PERON 4 → PERON 3 GEÇİŞ (X3 NORMAL)
  // ============================================================
  {
    int blocks[] = {17, 18, 12, 13, 14, -1};
    int switches[] = {-1, -1, 0, -1, -1, -1, -1};  // X3 = NORMAL(0)
    
    engine->defineRoute(9, "R09_P4_TO_P3_VIA_X3", blocks, 5, switches);
    definedRoutes++;
  }

  // ============================================================
  // GRUP 11: PERON 3 → PERON 4 GEÇİŞ (X4 DIVERGING)
  // ============================================================
  {
    int blocks[] = {13, 14, 19, -1};
    int switches[] = {-1, -1, -1, 1, -1, -1, -1};  // X4 = DIVERGING(1)
    
    engine->defineRoute(10, "R10_P3_TO_P4_VIA_X4", blocks, 3, switches);
    definedRoutes++;
  }

  // ============================================================
  // GRUP 12: PERON 4 → PERON 3 GEÇİŞ (X4 NORMAL)
  // ============================================================
  {
    int blocks[] = {18, 19, 14, -1};
    int switches[] = {-1, -1, -1, 0, -1, -1, -1};  // X4 = NORMAL(0)
    
    engine->defineRoute(11, "R11_P4_TO_P3_VIA_X4", blocks, 3, switches);
    definedRoutes++;
  }

  // ============================================================
  // GRUP 13: PERON 5 ROTASI
  // ============================================================
  {
    int blocks[] = {20, 21, 22, 23, 24, -1};
    int switches[] = {-1, -1, -1, -1, -1, -1, -1};
    
    engine->defineRoute(12, "R12_ENTRY_TO_PLATFORM_5", blocks, 5, switches);
    definedRoutes++;
  }

  // ============================================================
  // GRUP 14: PERON 5 → DEPO GEÇİŞİ
  // ============================================================
  {
    int blocks[] = {22, 23, 24, 27, 28, -1};
    int switches[] = {-1, -1, -1, -1, 1, -1, 0};  // X5=DIVERGING(1), X7=NORMAL(0)
    
    engine->defineRoute(13, "R13_P5_TO_DEPOT", blocks, 5, switches);
    definedRoutes++;
  }

  // ============================================================
  // GRUP 15: DEPO → PERON 5 GEÇİŞİ
  // ============================================================
  {
    int blocks[] = {25, 26, 23, 24, -1};
    int switches[] = {-1, -1, -1, -1, -1, 0, 1};  // X6=NORMAL(0), X7=DIVERGING(1)
    
    engine->defineRoute(14, "R14_DEPOT_TO_P5", blocks, 4, switches);
    definedRoutes++;
  }

  // ============================================================
  // GRUP 16: DEPO GİRİŞİ
  // ============================================================
  {
    int blocks[] = {25, 26, 27, 28, -1};
    int switches[] = {-1, -1, -1, -1, -1, -1, -1};
    
    engine->defineRoute(15, "R15_ENTRY_TO_DEPOT", blocks, 4, switches);
    definedRoutes++;
  }

  // ============================================================
  // GRUP 17: BYPASS ROTASI (P1→P3 Doğrudan)
  // ============================================================
  {
    int blocks[] = {3, 4, 9, 14, 12, -1};
    int switches[] = {-1, 1, -1, 1, -1, -1, -1};  // X2=DIV, X4=DIV
    
    engine->defineRoute(16, "R16_P1_TO_P3_BYPASS", blocks, 5, switches);
    definedRoutes++;
  }

  // Çakışma matrisini oluştur
  engine->buildConflictMatrix();

  Serial.print("[RM] ");
  Serial.print(definedRoutes);
  Serial.println(" routes defined.");
  Serial.println("Station layout initialized for 5-platform operation.\n");
}

void RouteManager::printStationInfo() {
  Serial.println("\n========== 5-PLATFORM STATION LAYOUT ==========");
  Serial.println("\nPLATFORM 1: [B0]─[B1]─[X1]─[B2]─[B3]─[X2]─[B4]");
  Serial.println("PLATFORM 2: [B5]─[B6]─[X1]─[B7]─[B8]─[X2]─[B9]");
  Serial.println("PLATFORM 3: [B10]─[B11]─[X3]─[B12]─[B13]─[X4]─[B14]");
  Serial.println("PLATFORM 4: [B15]─[B16]─[X3]─[B17]─[B18]─[X4]─[B19]");
  Serial.println("PLATFORM 5: [B20]─[B21]─[X5]─[B22]─[B23]─[X6]─[B24]");
  Serial.println("DEPOT:      [B25]─[B26]─[X7]─[B27]─[B28]");
  
  Serial.println("\nSWITCHES (7 makaslar):");
  Serial.println("  X1: Platform 1-2 Left  | X2: Platform 1-2 Right");
  Serial.println("  X3: Platform 3-4 Left  | X4: Platform 3-4 Right");
  Serial.println("  X5: Platform 5 Entry   | X6: Platform 5 Exit");
  Serial.println("  X7: Depot Crossover");
  
  Serial.print("\nTotal Routes Defined: ");
  Serial.println(definedRoutes);
  
  Serial.println("\nROUTE GROUPS:");
  Serial.println("  R00-R01: Platform Entries");
  Serial.println("  R02-R05: Platform 1-2 Transfers");
  Serial.println("  R06-R11: Platform 3-4 Operations");
  Serial.println("  R12-R15: Platform 5 & Depot");
  Serial.println("  R16: Bypass Route");
  
  Serial.println("============================================\n");
}
