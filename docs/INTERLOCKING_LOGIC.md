# Railway CTC — İnterlocking Mantığı (SIL-4 Uyumlu)

## 1. Genel Tanımlar

### 1.1 Route (Rota)
Bir **rota**, trenin başlangıç bloğundan hedef bloğuna gitmesi için gereken:
- Blok dizisi
- Makas pozisyonları (hangisi NORMAL, hangisi TERS)
- Sinyaller (kilit durumu)

**Örnek:**
```
Rota R1: Blok1 → Blok2 → Blok3 (makasız)
  - Blok1 sinyal: YEŞİL
  - Blok2 sinyal: YEŞİL
  - Blok3 sinyal: KIRMIZI (hedefe yaklaşma)

Rota R2: Blok1 → Makas1(TERS) → Hat2'ye → Blok5
  - Blok1 sinyal: YEŞİL
  - Makas1 pozisyonu: TERS (0° → 90°)
  - Hat2 blokları: YEŞİL
  - Blok5 sinyal: KIRMIZI
```

### 1.2 Route Locking (Rota Kilitleme)
Bir rota **kilitlendiğinde**:
1. Rotada yer alan tüm **makaslar sabit pozisyona kilitlenir** (değiştirilemez)
2. Rotada yer alan tüm **blokların işgal durumu izlenir**
3. Rota kullanımdayken **başka hiçbir rota bu bloklara erişemez**

### 1.3 Conflict Detection (Çakışma Tespiti)
İki rotanın **çakışması** = aynı blok veya makasın her iki rotada da kullanılması.

**Örnek çakışma:**
```
Rota R1: Blok1 → Blok2 → Blok3 (Makas1 NORMAL)
Rota R2: Blok2 → Blok4 (Makas1 TERS) ← ÇAKIŞMA!
  - Blok2 her iki rotada var
  - Makas1 farklı pozisyonda isteniyor
  → R2 başlatılamaz eğer R1 aktif ise
```

### 1.4 Switch-Signal Interlocking (Makas-Sinyal Uyum)
Makasın konumu değişirse:
1. Makası kullanan tüm aktif rotalar **IPTAL** edilir
2. Etkilenen blokların sinyalleri **KIRMIZIya** alınır (Dur)
3. Makas stabilize olduktan sonra (servo seyreltildikten sonra) yeni komutlar kabul edilir

### 1.5 Approach Locking (Yaklaşma Kilitleme)
Tren bir bloktan çıkmaya yaklaşırken (işgali release etmeye):
1. O blok sırasındaki makaslar **kilitlenir** (değiştirilmez)
2. Tren bloğu tamamıyla terk edene kadar kilitleme devam eder
3. Amaç: Tren transit sırasında makas konumunun aniden değişmemesi

---

## 2. Sistem Mimarisi

### 2.1 Veri Yapıları

```cpp
// Blok Durumu
enum BlockState {
  EMPTY = 0,      // Boş
  OCCUPIED = 1    // Dolu
};

// Makas Konumu
enum SwitchPosition {
  NORMAL = 0,     // Düz yol (0°)
  DIVERGING = 1   // Sapan yol (90°)
};

// Rota Durumu
enum RouteState {
  INACTIVE = 0,      // Pasif
  REQUESTED = 1,     // İstenmiş, onay bekleniyor
  ACTIVE = 2,        // Aktif (kilitleri var)
  LOCKED_BY_TRAIN = 3 // Tren işgalinde, makaslar kilitli
};

// Rota Tanımı
struct Route {
  int id;                           // Rota ID (0-99)
  String name;                      // Rota adı (R1, R2, vb)
  int blocks[20];                   // Blok indeksleri (-1 = bitiş)
  int blockCount;                   // Kaç blok?
  
  // Makas gereksinmeleri: [makasIdx] = istenen pozisyon
  int switchRequirements[3];        // -1 = önemli değil, 0 = NORMAL, 1 = DIVERGING
  
  RouteState state;                 // Rota durumu
  unsigned long activatedAt;        // Aktif hale getirilme zamanı
};

// Çakışma Tablosu
struct Conflict {
  int route1;    // Rota 1 ID
  int route2;    // Rota 2 ID
  bool conflictExists; // true = çakışma var
};
```

### 2.2 İnterlocking Motor (Merkez)

```cpp
class InterLockingEngine {
  private:
    Route routes[MAX_ROUTES];           // Tüm rotalar
    int activeRoutes[MAX_ROUTES];       // Şu an aktif rotalar
    Conflict conflictTable[MAX_ROUTES][MAX_ROUTES]; // Çakışma matrisi
    
    // Blok ve Makas durumu (BOARD A/B/C'den okunur)
    bool blockOccupancy[20];            // Blok işgali
    int switchPosition[3];              // Makas konumları
    
  public:
    // Rota tanımı
    void defineRoute(int routeId, int blocks[], int blockCount, 
                     int switchReqs[3]);
    
    // Çakışma tablosu oluştur
    void buildConflictTable();
    
    // Rota isteği
    bool requestRoute(int routeId);     // true = başarılı, false = çakışma/hata
    
    // Rota iptali
    void cancelRoute(int routeId);
    
    // Çakışma kontrol
    bool hasConflict(int route1, int route2);
    
    // Blok durumu güncelle
    void updateBlockOccupancy(bool blocks[]);
    
    // Makas durumu güncelle
    void updateSwitchPosition(int switches[]);
    
    // Sinyalleri hesapla ve BOARD A/B'ye gönder
    void calculateAndSendSignals();
};
```

---

## 3. Algoritma: Rota İsteği Akışı

```
requestRoute(R1):
  1. R1'in tüm blokları bos mu? Kontrol et
     - Hayır → HATA, return false
  
  2. R1'in makas gereksinimleri şu anki pozisyonla uyumlu mu?
     - Hayır → HATA (makas konumu değiştirme komutu gönder, return false)
  
  3. Çakışma tablosunda R1 ile çakışan rotalar var mı?
     → Aktif olanlar var mı?
     - Evet → HATA, return false (çakışan rota aktif)
     - Hayır → Devam
  
  4. R1'i ACTIVE yap
  
  5. R1'deki makasları LOCK yap (değiştirilmez)
  
  6. R1'deki bloklara ait sinyalleri YEŞIL yap
  
  7. return true (başarılı)

cancelRoute(R1):
  1. R1'i INACTIVE yap
  2. R1'deki makasları UNLOCK yap
  3. R1'deki blokların sinyallerini güncelle
  4. Başka aktif rotaları kontrol et, varsa onların sinyallerini güncelle
```

---

## 4. Sinyal Hesaplama Kuralı (TCDD/SIEMENS)

```cpp
for each block:
  if (block OCCUPIED) {
    signal = RED       // Blok dolu → DUR
  } else if (block is in ACTIVE route) {
    if (nextBlock OCCUPIED or nextBlock is route's last) {
      signal = YELLOW  // Yaklaşma
    } else {
      signal = GREEN   // Açık
    }
  } else {
    signal = RED       // Route dışı → DUR (güvenlik)
  }
```

---

## 5. 5-Peronlu İstasyon Geometrisi (Örnek Tanımı)

```
┌─────────────────────────────────────────────────────────────┐
│                    PERON 1                                  │
├─────────────────────────────────────────────────────────────┤
│  [B1]─[B2]─[X1]─[B3]─[B4]─[X2]─[B5]                        │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                    PERON 2                                  │
├─────────────────────────────────────────────────────────────┤
│  [B6]─[B7]─[X1]─[B8]─[B9]─[X2]─[B10]                       │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                    PERON 3                                  │
├─────────────────────────────────────────────────────────────┤
│  [B11]─[B12]─[X3]─[B13]─[B14]─[X4]─[B15]                   │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                    PERON 4                                  │
├─────────────────────────────────────────────────────────────┤
│  [B16]─[B17]─[X3]─[B18]─[B19]─[X4]─[B20]                   │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                    PERON 5                                  │
├─────────────────────────────────────────────────────────────┤
│  [B21]─[B22]─[X5]─[B23]─[B24]─[X6]─[B25]                   │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                  DEPO HATTI (İsteğe bağlı)                  │
├─────────────────────────────────────────────────────────────┤
│  [D1]─[D2]─[X7]─[D3]─[D4]                                   │
└─────────────────────────────────────────────────────────────┘

X1, X2, X3, X4, X5, X6, X7 = Makaslar (crossover points)
B1-B25 = Bloklar (25 blok total — 5 peron × 5 blok/peron)
D1-D4 = Depo hattı blokları
```

**Örnek Rotalar:**
```
R1: B1 → B2 → B3 → B4 → B5 (Peron 1'de duş)
R2: B1 → B2 → X1(NORMAL) → B6 → B7 (Peron 1'den Peron 2'ye geçiş)
R3: B6 → B7 → X1(DIVERGING) → B1 → B2 (Peron 2'den Peron 1'ye)
...
```

---

## 6. SIL-4 Uyum Notları

- **Redundancy:** Her blok işgali iki bağımsız sensör (future)
- **Timeout:** Makasların hareketinde timeout (güvenlik timeout)
- **Watchdog:** BOARD C'nin düzgün çalışıp çalışmadığını izlemek (Heartbeat)
- **Testing:** Tüm rota çakışmaları önceden test edilmeli
- **Logging:** Tüm rota değişiklikleri kaydedilmeli

---

