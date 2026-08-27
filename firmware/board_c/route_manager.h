// ============================================================
//  ROUTE MANAGER — 5-Peronlu İstasyon Rota Tanımları
//  Siemens/TCDD CTC Standartlarına Uygun
// ============================================================

#ifndef ROUTE_MANAGER_H
#define ROUTE_MANAGER_H

#include "../shared/common_types.h"
#include "../shared/config.h"
#include "interlocking_engine.h"

class RouteManager {
  private:
    InterLockingEngine* engine;
    int definedRoutes;
    
  public:
    RouteManager(InterLockingEngine* ile);
    
    /**
     * defineStationLayout: 5-peronlu istasyon geometrisini tanımla
     * Tüm rotaları otomatik olarak oluşturur
     */
    void defineStationLayout();
    
    /**
     * printStationInfo: İstasyon bilgilerini yazdır
     */
    void printStationInfo();
};

#endif // ROUTE_MANAGER_H
