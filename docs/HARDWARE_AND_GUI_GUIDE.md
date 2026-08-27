# Railway CTC System — Proje Rehberi

## 1. Mevcut Sistem Analizi

### 1.1 Elektrik Yapısı (Şu Anki)
```
10 BLOK × 2 HAT × 3 SINYAL (R/Y/G) = 60 SINYAL LED

HAT 1: B0-B1-B2-B3-B4-B5-B6-B7-B8-B9 (10 blok)
       ├─ B0: D32(R), D33(Y), D34(G)
       ├─ B1: D35(R), D36(Y), D37(G)
       ├─ B2: D38(R), D39(Y), D40(G)
       ├─ B3: D41(R), D42(Y), D43(G)
       ├─ B4: D44(R), D45(Y), D46(G)
       ├─ B5: D47(R), D48(Y), D49(G)
       ├─ B6: D50(R), D51(Y), D52(G)
       ├─ B7: D53(R), A0(Y), A1(G)
       ├─ B8: A2(R), A3(Y), A4(G)
       └─ B9: A5(R), A6(Y), A7(G)

HAT 2: B10-B11-B12-B13-B14-B15-B16-B17-B18-B19 (10 blok)
       [Aynı şema, BOARD B üzerinde]

BOARD A (Hat1): Serial1 (TX:18, RX:19) + D22-D31 (işgal) + D32-A7 (sinyaller)
BOARD B (Hat2): Serial2 (TX:16, RX:17) + D22-D31 (işgal) + D32-A7 (sinyaller)
```

### 1.2 Problem
Perona uyarlanmış değil — sadece 2 hat 10 blok. Peron gösterim ve yönetimi yok.

---

## 2. Peron Mimarisi (5-Peronlu İstasyon)

### 2.1 Fiziksel Düzen
```
PERON 1:
  [GİRİŞ] → [B0]─[B1]─[X1 Makas]─[B2]─[B3]─[X2 Makas]─[B4] → [ÇIKIŞ]
                   ↑ Sinyaller: R/Y/G LED'ler

PERON 2:
  [GİRİŞ] → [B5]─[B6]─[X1 Makas]─[B7]─[B8]─[X2 Makas]─[B9] → [ÇIKIŞ]

PERON 3:
  [GİRİŞ] → [B10]─[B11]─[X3 Makas]─[B12]─[B13]─[X4 Makas]─[B14] → [ÇIKIŞ]

PERON 4:
  [GİRİŞ] → [B15]─[B16]─[X3 Makas]─[B17]─[B18]─[X4 Makas]─[B19] → [ÇIKIŞ]

PERON 5:
  [GİRİŞ] → [B20]─[B21]─[X5 Makas]─[B22]─[B23]─[X6 Makas]─[B24] → [ÇIKIŞ]

DEPO (İsteğe bağlı):
  [GİRİŞ] → [D0]─[D1]─[X7 Makas]─[D2]─[D3] → [ÇIKIŞ]

TOPLAM: 25 blok (5 peron × 5 blok) + 4 depo = 29 blok
         7 makas (X1-X7)
         29 × 3 = 87 sinyal LED
```

### 2.2 Blok Haritası (Hardware Pin Ataması)

#### HAT 1 (BOARD A):

| Peron | Blok | Index | İşgal Pin | Sinyal Pinleri (R,Y,G) |
|-------|------|-------|-----------|------------------------|
| P1 | B0 | 0 | D22 | D32, D33, D34 |
| P1 | B1 | 1 | D23 | D35, D36, D37 |
| P1 | B2 | 2 | D24 | D38, D39, D40 |
| P1 | B3 | 3 | D25 | D41, D42, D43 |
| P1 | B4 | 4 | D26 | D44, D45, D46 |
| P2 | B5 | 5 | D27 | D47, D48, D49 |
| P2 | B6 | 6 | D28 | D50, D51, D52 |
| P2 | B7 | 7 | D29 | D53, A0, A1 |
| P2 | B8 | 8 | D30 | A2, A3, A4 |
| P2 | B9 | 9 | D31 | A5, A6, A7 |

#### HAT 2 (BOARD B):
```
Aynı pin şeması:
- İşgal: D22-D31
- Sinyaller: D32-D53, A0-A7
```

#### BOARD C - Makas Kontrolü:
```
Servo Pinleri:
  X1 Sol (Servo 0):   D2   → Peron 1-2 geçişi (left)
  X1 Sağ (Servo 1):   D3   → Peron 1-2 geçişi (right)
  X3 Sol (Servo 2):   D4   → Peron 3-4 geçişi (left)
  X3 Sağ (Servo 3):   D5   → Peron 3-4 geçişi (right)
  X5 (Servo 4):       D6   → Peron 5 girişi
  X7 (Servo 5):       D7   → Depo geçişi

Kontrol Pinleri:
  Heartbeat LED:      D13
  Acil Dur Butonu:    D28 (INPUT_PULLUP)
```

---

## 3. Proteus Simülasyon Şeması

### 3.1 BOARD A Kablolama (Proteus)

```
Arduino MEGA Pin | Bileşen | Proteus Simülasyonu
─────────────────┼────────────┼────────────────────
D22-D31 (10 pin) │ Blok Sensörleri │ SWITCH × 10
D32-D53 (22 pin) │ Sinyal LED'ler │ LED × 22
A0-A7 (8 pin)    │ Sinyal LED'ler │ LED × 8
D18 (TX1)        │ Master'a        │ → BOARD C RX1 (D19)
D19 (RX1)        │ Master'den      │ ← BOARD C TX1 (D18)
GND              │ Ortak toprak    │ ← BOARD C, BOARD B

BOARD B: Tıpatıp aynı (Serial2 ile bağlı)
```

### 3.2 Simülasyon Bağlantı Diyagramı

```
                      ┌──────────────┐
                      │   PROTEUS    │
                      └──────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
    ┌───────┐           ┌───────┐           ┌───────┐
    │BOARD A│           │BOARD C│           │BOARD B│
    │(HAT1) │           (MASTER)            │(HAT2) │
    └───────┘           └───────┘           └───────┘
        │               │   │   │               │
        │ Serial1       │   │   │               │ Serial2
        │ TX18/RX19     │   │   │               │ TX16/RX17
        └───────────────┤   │   ├───────────────┘
                        │   │   │
                        │  USB  │
                        │   │   │
                        └───┼───┘
                            │
                       [Python GUI]
                       COM30/COM31
```

---

## 4. Peron Fiziği ve Blok Yerleşimi

### 4.1 Peron 1 Detaylı Yerleşim

```
                    PERON 1 — Platform View
                    
    [GİRİŞ HATTI]
           │
    ┌──────┴──────┐
    │    B0       │ 5m uzunluk
    ├─────────────┤ 
    │    B1       │ X1 (Makas - Peron 2'ye geçiş)
    ├─────────────┤
    │    B2       │ 5m uzunluk
    ├─────────────┤
    │    B3       │ X2 (Makas - Peron 2'ye geçiş)
    ├─────────────┤
    │    B4       │ 5m uzunluk
    ├─────────────┤
           │
    [ÇIKIŞ HATTI]


Her blok = 5 meter
Peron 1 Sinyaller:
  ┌────────────────────────────────────────────┐
  │ B0  │ B1  │ B2  │ B3  │ B4                 │
  │ ◯   │ ◯   │ ◯   │ ◯   │ ◯  ← LED'ler     │
  └────────────────────────────────────────────┘
   R/Y/G R/Y/G R/Y/G R/Y/G R/Y/G
  D32-34 D35-37 D38-40 D41-43 D44-46
```

### 4.2 5 Peronun Tamamı (Üst Görünüş)

```
┌─────────────────────────────────────────────────────────────────┐
│  PERON 1: [B0]─[B1]─X1─[B2]─[B3]─X2─[B4]                      │
├─────────────────────────────────────────────────────────────────┤
│  PERON 2: [B5]─[B6]─X1─[B7]─[B8]─X2─[B9]                      │
├─────────────────────────────────────────────────────────────────┤
│  PERON 3: [B10]─[B11]─X3─[B12]─[B13]─X4─[B14]                 │
├─────────────────────────────────────────────────────────────────┤
│  PERON 4: [B15]─[B16]─X3─[B17]─[B18]─X4─[B19]                 │
├─────────────────────────────────────────────────────────────────┤
│  PERON 5: [B20]─[B21]─X5─[B22]─[B23]─X6─[B24]                 │
├─────────────────────────────────────────────────────────────────┤
│  DEPO:    [D0]─[D1]─X7─[D2]─[D3]                               │
└─────────────────────────────────────────────────────────────────┘
           ↑       ↑ Makaslar (Servo Motorlu)
        Sinyaller
```

---

## 5. Pin Atama Tablosu (Tamamı)

### 5.1 BOARD A (Hat1) — Arduino Mega #1

```
HABERLEŞME:
  TX1 (D18) ← BOARD C RX1 (D19)
  RX1 (D19) ← BOARD C TX1 (D18)
  GND ← Ortak GND (BOARD B, BOARD C)

BLOK İŞGAL SENSÖRLERI (INPUT_PULLUP):
  D22 ← B0 işgal sensörü
  D23 ← B1 işgal sensörü
  D24 ← B2 işgal sensörü
  D25 ← B3 işgal sensörü
  D26 ← B4 işgal sensörü
  D27 ← B5 işgal sensörü
  D28 ← B6 işgal sensörü
  D29 ← B7 işgal sensörü
  D30 ← B8 işgal sensörü
  D31 ← B9 işgal sensörü

SINYAL LED'LERİ (OUTPUT, 220Ω rezistor + LED + GND):
  PERON 1:
    B0: D32(R), D33(Y), D34(G)
    B1: D35(R), D36(Y), D37(G)
    B2: D38(R), D39(Y), D40(G)
    B3: D41(R), D42(Y), D43(G)
    B4: D44(R), D45(Y), D46(G)
  
  PERON 2:
    B5: D47(R), D48(Y), D49(G)
    B6: D50(R), D51(Y), D52(G)
    B7: D53(R), A0(Y), A1(G)
    B8: A2(R), A3(Y), A4(G)
    B9: A5(R), A6(Y), A7(G)
```

### 5.2 BOARD B (Hat2) — Arduino Mega #2

**Tıpatıp BOARD A ile aynı pin şeması**
```
Tek fark: Serial2 (TX16/RX17) kullanıyor.
```

### 5.3 BOARD C (Master) — Arduino Mega #3

```
HABERLEŞME:
  Serial  (D0/D1)  → USB (PC ile haberleşme)
  Serial1 (D18/D19) ← BOARD A
  Serial2 (D16/D17) ← BOARD B

SERVO MOTORLAR (6 adet, 5V harici güç):
  D2 ← Servo 0 (X1 Sol)
  D3 ← Servo 1 (X1 Sağ)
  D4 ← Servo 2 (X3 Sol)
  D5 ← Servo 3 (X3 Sağ)
  D6 ← Servo 4 (X5)
  D7 ← Servo 5 (X7)

KONTROLDİSPOZİTİFLER:
  D13 ← Heartbeat LED (sistem canlı mı?)
  D28 ← Acil Dur Butonu (INPUT_PULLUP)

GÜÇ:
  5V → Servo motorların güç (harici PSU)
  GND ← Ortak toprak (BOARD A, BOARD B, Servo GND)
```

---

## 6. Proteus Simülasyon Yapısı (Detaylı)

### 6.1 BOARD A Simülasyonu

```
Proteus Bileşenleri:
  1. Arduino MEGA 2560 (U1)
  
  2. Blok Sensörleri (10 adet)
     S1-S10: SPST Switch (Basit Anahtar)
     ├─ S1: Pin D22 ↔ GND
     ├─ S2: Pin D23 ↔ GND
     ├─ S3: Pin D24 ↔ GND
     ├─ S4: Pin D25 ↔ GND
     ├─ S5: Pin D26 ↔ GND
     ├─ S6: Pin D27 ↔ GND
     ├─ S7: Pin D28 ↔ GND
     ├─ S8: Pin D29 ↔ GND
     ├─ S9: Pin D30 ↔ GND
     └─ S10: Pin D31 ↔ GND
  
  3. Sinyal LED'leri (30 adet)
     LED1-LED30: 3mm LED (Kırmızı/Sarı/Yeşil)
     Her LED: Pin → 220Ω Rezistor → LED → GND
     
  4. Seri Haberleşme (Master'a)
     TX1 (D18) ←→ BOARD C RX1 (D19)
     RX1 (D19) ←→ BOARD C TX1 (D18)
     GND ↔ Ortak GND

Simülasyon Ayarları:
  Baud Rate: 9600 bps
  Stop Bits: 1
  Parity: None
```

### 6.2 BOARD C Simülasyonu

```
Proteus Bileşenleri:
  1. Arduino MEGA 2560 (U2)
  
  2. Servo Motorlar (6 adet)
     ├─ SG90_1 (D2): Peron 1-2 Sol Geçiş
     ├─ SG90_2 (D3): Peron 1-2 Sağ Geçiş
     ├─ SG90_3 (D4): Peron 3-4 Sol Geçiş
     ├─ SG90_4 (D5): Peron 3-4 Sağ Geçiş
     ├─ SG90_5 (D6): Peron 5 Girişi
     └─ SG90_6 (D7): Depo Geçişi
  
  3. Heartbeat LED
     LED: D13 → 220Ω Rezistor → LED → GND
  
  4. Acil Dur Butonu
     S_ESTOP: D28 ↔ GND (INPUT_PULLUP)
  
  5. COMPIM (Virtual COM Port)
     USB Simülasyonu:
     D0 (RX) → COMPIM RX
     D1 (TX) → COMPIM TX
     GND ↔ COMPIM GND
  
  6. Serial Haberleşme (BOARD A & B)
     Serial1: D18 (TX) ↔ BOARD A RX, D19 (RX) ↔ BOARD A TX
     Serial2: D16 (TX) ↔ BOARD B RX, D17 (RX) ↔ BOARD B TX

Güç:
  5V Harici PSU → Servo'lar (6 × ~150mA = 900mA min)
  Arduino 5V ↔ Servo GND (referans toprağı)
```

### 6.3 Proteus Devresi Konnektörleri

```
BOARD A ↔ BOARD C:
  BOARD_A D18 (TX1) → BOARD_C D19 (RX1)
  BOARD_A D19 (RX1) → BOARD_C D18 (TX1)
  BOARD_A GND → BOARD_C GND

BOARD B ↔ BOARD C:
  BOARD_B D16 (TX2) → BOARD_C D17 (RX2)
  BOARD_B D17 (RX2) → BOARD_C D16 (TX2)
  BOARD_B GND → BOARD_C GND

BOARD C ↔ PC (com0com):
  Proteus COMPIM Port → COM30 (sanal)
  Python GUI → COM31 (sanal)
```

---

## 7. Kablo Listesi (Gerçek Kurulum)

### 7.1 Blok Sensörleri (20 Adet)
```
Hat1 (BOARD A):
  - 10 × SPST Anahtar (Normalde Açık)
  - Her biri: GND - Anahtar - Arduino Pin

Hat2 (BOARD B):
  - 10 × SPST Anahtar
```

### 7.2 Sinyal LED'leri (60 Adet)
```
Her biri:
  Arduino Pin → 220Ω Rezistor → LED Anot → LED Katot → GND

Malzeme:
  - 60 × 3mm LED (20× Kırmızı, 20× Sarı, 20× Yeşil)
  - 60 × 220Ω Rezistor (1/4W)
  - Jumper kablolar

Örgütleme:
  Her peron için plastic kutu / modül
  Peron 1: 15 LED (B0-B4)
  Peron 2: 15 LED (B5-B9)
  Peron 3: 15 LED (B10-B14)
  Peron 4: 15 LED (B15-B19)
  Peron 5: 15 LED (B20-B24)
```

### 7.3 Servo Motorlar (6 Adet)
```
Her Servo:
  - Sinyal: Arduino Pin (Jumper)
  - 5V: Harici PSU
  - GND: Ortak GND

Bağlantı:
  Harici 5V PSU → Servo Kırmızı (+)
  Harici GND → Servo Kahverengi (-)
  Arduino Pin → Servo Turuncu (Sinyal)
  
NOT: Arduino 5V pini 6 servo'yu besleyemez! 
     Minimum 1A harici güç kaynağı gerekli.
```

### 7.4 Seri Haberleşme Kabloları
```
BOARD A ↔ BOARD C:
  - TX1 (D18) ↔ RX1 Jumper
  - RX1 (D19) ↔ TX1 Jumper
  - GND ↔ GND

BOARD B ↔ BOARD C:
  - TX2 (D16) ↔ RX2 Jumper
  - RX2 (D17) ↔ TX2 Jumper
  - GND ↔ GND

BOARD C ↔ PC:
  - USB Kablo (Proteus simülasyonunda com0com)
```

---

## 8. Firmware Güncelleştirme Checklist

### 8.1 BOARD A ve BOARD B

```cpp
// Henüz değişiklik yok — mevcut kod çalışır
// Sadece blok sayısını doğrula:
const int BLOK_SAYISI = 10;  // ✓ Correct

// Testler:
✓ D22-D31 sensörleri çalışıyor mu?
✓ D32-A7 LED'leri yanıyor mu?
✓ Serial1/Serial2 haberleşmesi stabli mi?
```

### 8.2 BOARD C

```cpp
// İnterlocking Engine + RouteManager ile güncellendi
// Testler:
✓ Yeni modüler yapı compile ediyor mu?
✓ Rota tanımları (17 rota) düzgün mi?
✓ Servo hareketi hızlı ve güvenilir mi?
✓ Çakışma tespiti çalışıyor mu?
✓ Python GUI ile JSON haberleşmesi durağan mı?
```

---

## 9. Python GUI Yenileme Planı

### 9.1 Sorunlar (Mevcut)
- ❌ Sadece 2 hat 10 blok gösteriliyor
- ❌ Peron bilgisi yok
- ❌ Rota seçimi imkânsız (manual makas kontrolü)
- ❌ Görsel olarak veri yoğun (tren simülasyonu yok)
- ❌ Log çıktısı sınırlı
- ❌ Sistem sağlığı göstergesi eksik

### 9.2 Çözüm: Yeni GUI Mimarisi

```
┌──────────────────────────────────────────────────────────────┐
│         Railway CTC — 5-Peronlu İstasyon Kontrol Paneli     │
├──────────────────────────────────────────────────────────────┤
│ [BAĞLAN] [PORT: COM31▼] [BAUD: 9600▼] [YENİLE] │ ●BAĞLI     │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌────────────────────────────────────────────────────────┐  │
│  │         İSTASYON GÖRÜNÜŞÜ (Üst Görünüş)               │  │
│  │                                                        │  │
│  │ PERON 1: [●][●][X1][●][●][X2][●]                   │  │
│  │ PERON 2: [◯][◯][X1][◯][◯][X2][◯]                   │  │
│  │ PERON 3: [●][◯][X3][◯][◯][X4][◯]                   │  │
│  │ PERON 4: [◯][◯][X3][●][◯][X4][◯]                   │  │
│  │ PERON 5: [◯][◯][X5][◯][◯][X6][◯]                   │  │
│  │                                                        │  │
│  │ ● = OCCUPIED (Kırmızı Sinyal)                        │  │
│  │ ◯ = EMPTY (Yeşil Sinyal)                             │  │
│  │ ◑ = APPROACH (Sarı Sinyal)                           │  │
│  │ X = Makas (Normal/Diverging göstergesi)              │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                               │
│  ┌──────────────────┬───────────────────────────────────┐   │
│  │ KONTROL PANELI   │  OLAY KAYDI & İZLEME             │   │
│  ├──────────────────┼───────────────────────────────────┤   │
│  │ Rota Seçimi:     │ [00:15:23] Route 2 activated     │   │
│  │ [R0: P1→Entry]   │ [00:15:25] Block B2 occupied     │   │
│  │ [R2: P1→P2]      │ [00:15:28] Switch X1 diverging   │   │
│  │ [R6: P3→Entry]   │ [00:15:30] Route 6 requested     │   │
│  │ [R13: P5→Depot]  │ [00:15:32] Conflict detected!    │   │
│  │                  │ [00:15:35] Route 6 rejected      │   │
│  │ Aktif Rotalar:   │                                   │   │
│  │ ✓ R2 (actv 5s)   │                                   │   │
│  │                  │                                   │   │
│  │ Sistem Durumu:   │                                   │   │
│  │ ●Heartbeat OK    │                                   │   │
│  │ ●BOARD_A con     │                                   │   │
│  │ ●BOARD_B con     │                                   │   │
│  │                  │                                   │   │
│  │ [MANUEL MAKAS]   │                                   │   │
│  │ X1: NORMAL ◆     │                                   │   │
│  │ X3: DIVERGING ◆  │                                   │   │
│  │                  │                                   │   │
│  │ [ESTOP]          │                                   │   │
│  └──────────────────┴───────────────────────────────────┘   │
│                                                               │
│  Status: 3 active routes | 1 conflict pending | System OK   │
└──────────────────────────────────────────────────────────────┘
```

### 9.3 GUI Özellikleri

**A) İstasyon Görünüşü Bölümü**
```python
# Her peron için dinamik grid
class PlatformView:
  - Blok göstergesi (● işgal, ◯ boş, ◑ yaklaşma)
  - Makas durumu (X1, X3, X5 göstergesi)
  - Renk kodlaması (Kırmızı/Sarı/Yeşil)
  - Real-time güncelleme (250ms)
```

**B) Rota Kontrol Paneli**
```python
class RouteController:
  - Dropdown: 17 rota seçimi
  - Buton: "Rota Başlat" (yeşil)
  - Buton: "Rota İptal" (kırmızı)
  - Aktif Rotalar listesi (durum + süre)
  - Hata göstergesi (çakışma uyarısı)
```

**C) Manuel Makas Kontrolü**
```python
class SwitchManualControl:
  - Her makas için slider (Normal ◄─►Diverging)
  - Durumu göster (kilitleme uyarısı)
  - Timeout indicator
```

**D) Sistem İzleme**
```python
class SystemMonitor:
  - Heartbeat indicator (yanıp sönüyor)
  - BOARD A/B/C bağlantı durumu
  - Seri hata sayısı
  - Sistem sağlığı (%)
```

**E) Olay Kaydı**
```python
class EventLogger:
  - Timestamp + Event
  - Yazılı log (500 satır tutma)
  - Renk kodlu mesajlar ([OK], [ERR], [WAR])
  - Export butonu
```

### 9.4 Yeni Python Kodunun Yapısı

```
ctc_gui_v3.py
├── class CTCMainWindow
│   ├── __init__()
│   ├── build_ui()
│   ├── setup_styles()
│   └── on_close()
│
├── class PlatformGrid
│   ├── create_platform_row()
│   ├── update_blocks()
│   ├── update_signals()
│   └── animate_train()
│
├── class RouteController
│   ├── load_routes()
│   ├── request_route()
│   ├── cancel_route()
│   ├── update_active_routes()
│   └── check_conflicts()
│
├── class SwitchPanel
│   ├── create_switch_slider()
│   ├── apply_switch_command()
│   └── show_lock_warning()
│
├── class SystemMonitor
│   ├── update_heartbeat()
│   ├── check_board_status()
│   ├── update_health_gauge()
│   └── log_event()
│
├── class SerialHandler (threading)
│   ├── connect()
│   ├── disconnect()
│   ├── read_json()
│   ├── send_command()
│   └── error_recovery()
│
└── class EventLogger
    ├── log()
    ├── filter_by_type()
    └── export_log()
```

---

## 10. Kurulum Adımları (Özet)

### Adım 1: Hardware Montajı
```
1. BOARD A montajı:
   - 10 sensör → D22-D31
   - 30 LED → D32-A7 (220Ω + LED)
   
2. BOARD B (BOARD A ile aynı)
   
3. BOARD C servo montajı:
   - 6 servo → D2-D7
   - 5V harici PSU bağlantısı
   - Heartbeat LED → D13
   - Acil Dur butonu → D28
   
4. Seri haberleşme kablolama:
   - A-C: TX1/RX1
   - B-C: TX2/RX2
   - Ortak GND
```

### Adım 2: Proteus Simülasyonu
```
1. Yeni Proteus projesi:
   - 3 Arduino MEGA
   - 20 sensör switch
   - 60 LED + 220Ω rezistor
   - 6 Servo motor
   - 1 COMPIM (USB)
   
2. Bağlantılar (yukarıdaki devre diyagramı)

3. Arduino IDE'de compile ve hex üret:
   - BOARD_A_HAT1.ino
   - BOARD_B_HAT2.ino
   - BOARD_C_MASTER.ino
   
4. Proteus'ta Arduino'lara hex yükle
   
5. Simülasyonu çalıştır (250ms)
```

### Adım 3: Python GUI
```
1. Yeni GUI kodu yazılır
   
2. com0com kurulur (Windows):
   - COM30 ↔ COM31 (sanal port çifti)
   
3. Proteus COMPIM:
   - Port: COM30
   
4. Python GUI:
   - Port: COM31
   
5. Test: com0com bridge çalışıyor mı?
```

### Adım 4: End-to-End Test
```
1. Simülasyon başla
   
2. GUI'de "Rota 2" seç (P1→P2)
   
3. BOARD C acil dur komutu
   
4. Log çıktısını kontrol et
```

---

## 11. Sonraki Adımlar (Öneriler)

✅ **Tamamlanmış:**
- İnterlocking Engine (Rota kilitleme)
- 5-Peronlu geometri
- 17 rota tanımı
- Pin atama

⚠️ **Devam Etmesi Gerek:**
1. ✏️ Yeni Python GUI kodunu yaz
2. 🔌 Proteus simülasyonunu konfigure et
3. 🧪 Hardware test et (gerçek ortamda)
4. 📝 Logging ve monitoring ekle
5. 🚨 Emergency Stop logic validate et

---
