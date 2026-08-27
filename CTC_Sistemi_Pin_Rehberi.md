# TCDD / SIEMENS Mantığında CTC Sistemi — Proteus Pin Bağlantı Rehberi

## 1. Genel Mimari (Önce Büyük Resim)

Sen istedin:
- 2 hatlı (Hat 1 / Hat 2) çift yol
- En az 10 blok, her blokta sinyal
- En az 3 makas (crossover), Hat1 → Hat2 geçişi

Bunu **3 adet Arduino Mega 2560** ile kuracağız:

| Kart Adı | Görevi |
|---|---|
| **BOARD A — HAT1-MERKEZ** | Hat 1 üzerindeki 10 bloğun işgal sensörü + sinyal LED'leri |
| **BOARD B — HAT2-MERKEZ** | Hat 2 üzerindeki 10 bloğun işgal sensörü + sinyal LED'leri |
| **BOARD C — MASTER/MAKAS** | 3 makasın (6 adet uç makine/servo) kontrolü + Board A ve Board B'den gelen bilgileri toplayıp PC'deki Siemens tarzı CTC yazılımına aktarma |

**Neden tek Mega yetmiyor?** 20 blok × 3 renkli LED (Kırmızı/Sarı/Yeşil) = 60 çıkış + 20 işgal girişi + 6 servo + buton = ~90 pin gerekiyor. Mega'da kullanılabilir pin sayısı ~70. Shift register (74HC595) kullanmadan, direkt kablo ile öğretmek istediğin için işi 3 karta bölüyoruz.

**Kartlar birbiriyle nasıl konuşacak?** Mega'nın 4 tane donanımsal seri portu var (Serial, Serial1, Serial2, Serial3). Bunu kullanacağız — I2C veya ekstra kütüphane gerekmiyor, sadece `Serial.println()` / `Serial.read()` mantığı.

```
PC (Siemens tarzı CTC ekranı)
      │  USB (Serial - pin 0/1)
      ▼
BOARD C (MASTER + MAKAS)
   │ Serial1 (pin18 TX / pin19 RX)     │ Serial2 (pin16 TX / pin17 RX)
   ▼                                    ▼
BOARD A (HAT1)                     BOARD B (HAT2)
```

---

## 2. Hat Düzeni (Blok ve Makas Yerleşimi)

```
HAT1:  [B1]-[B2]-[B3]-X-[B4]-[B5]-[B6]-X-[B7]-[B8]-[B9]-X-[B10]
                       |               |               |
                    MAKAS1          MAKAS2          MAKAS3
                       |               |               |
HAT2:  [B1]-[B2]-[B3]-X-[B4]-[B5]-[B6]-X-[B7]-[B8]-[B9]-X-[B10]
```

Her makas noktasında **2 adet uç makine (servo)** var: biri Hat1 tarafındaki dil, biri Hat2 tarafındaki dil. İkisi birlikte hareket ederse tren Hat1'den Hat2'ye (veya tersi) geçebilir. Toplam: 3 makas × 2 servo = **6 servo motor**.

---

## 3. BOARD A — HAT1-MERKEZ (Arduino Mega #1)

### 3.1 Haberleşme (dokunma, ayrılmış)
| Pin | Bağlantı |
|---|---|
| 0 (RX0) / 1 (TX0) | USB — sadece debug için, boş bırak |
| 18 (TX1) / 19 (RX1) | BOARD C'nin Serial1 girişine (çapraz: A'nın TX1 → C'nin RX1, A'nın RX1 → C'nin TX1) |
| GND | BOARD C'nin GND'siyle ORTAK GND — bu şart, seri haberleşme referans toprağı paylaşmalı |

### 3.2 Blok İşgal Sensörleri (Track Circuit Simülasyonu)

Proteus'ta gerçek tren tekerleği olmadığı için her bloğu bir **SPST anahtar (switch)** ile simüle ediyoruz: anahtar kapanınca "blok dolu" (tren var), açıkken "blok boş" sayılır.

Kablolama mantığı (her biri için aynı): Arduino pinini `INPUT_PULLUP` moduna al → anahtarın bir ucunu pine, diğer ucunu GND'ye bağla. Anahtar kapanınca pin LOW okunur = **İŞGAL**, açıkken HIGH = **BOŞ**.

| Blok No | Pin | Proteus Bileşeni |
|---|---|---|
| Blok 1 | D22 | SWITCH (SPST) → GND |
| Blok 2 | D23 | SWITCH (SPST) → GND |
| Blok 3 | D24 | SWITCH (SPST) → GND |
| Blok 4 | D25 | SWITCH (SPST) → GND |
| Blok 5 | D26 | SWITCH (SPST) → GND |
| Blok 6 | D27 | SWITCH (SPST) → GND |
| Blok 7 | D28 | SWITCH (SPST) → GND |
| Blok 8 | D29 | SWITCH (SPST) → GND |
| Blok 9 | D30 | SWITCH (SPST) → GND |
| Blok 10 | D31 | SWITCH (SPST) → GND |

### 3.3 Blok Sinyalleri (Her blok = Kırmızı/Sarı/Yeşil LED)

Kablolama mantığı (her LED için aynı): Arduino pini → 220-330 Ω direnç → LED anot → LED katot → GND. Pin HIGH = LED yanar.

| Blok | Kırmızı (R) | Sarı (Y) | Yeşil (G) |
|---|---|---|---|
| Blok 1 | D32 | D33 | D34 |
| Blok 2 | D35 | D36 | D37 |
| Blok 3 | D38 | D39 | D40 |
| Blok 4 | D41 | D42 | D43 |
| Blok 5 | D44 | D45 | D46 |
| Blok 6 | D47 | D48 | D49 |
| Blok 7 | D50 | D51 | D52 |
| Blok 8 | D53 | A0 (D54) | A1 (D55) |
| Blok 9 | A2 (D56) | A3 (D57) | A4 (D58) |
| Blok 10 | A5 (D59) | A6 (D60) | A7 (D61) |

**Sinyal mantığı (Siemens/TCDD blok sinyalizasyonu):**
- Blok BOŞ ve bir sonraki blok da BOŞ → **YEŞİL**
- Blok BOŞ ama bir sonraki blok DOLU → **SARI** (yaklaşma/dikkat)
- Blok DOLU → **KIRMIZI** (dur)

> Board A üzerinde kullanılan toplam pin: 22-31 (giriş) + 32-53, A0-A7 (çıkış) + 18/19 (haberleşme). Board B ile birebir aynı şemayı kur, tek fark Serial2'ye bağlanması.

---

## 4. BOARD B — HAT2-MERKEZ (Arduino Mega #2)

Board A ile **tıpatıp aynı pin şeması**. Tek fark haberleşme:

| Pin | Bağlantı |
|---|---|
| 16 (TX2) / 17 (RX2) | BOARD C'nin Serial2'sine çapraz bağlan |

Blok işgal girişleri: D22–D31 (Hat2 Blok1–10)
Sinyal LED'leri: D32–D53 + A0–A7 (yukarıdaki Board A tablosuyla birebir aynı sırada)

---

## 5. BOARD C — MASTER + MAKAS (Arduino Mega #3)

Bu kart hem PC'deki CTC yazılımıyla konuşur hem de fiziksel makasları (servo) sürer.

### 5.1 Haberleşme
| Pin | Bağlantı |
|---|---|
| 0 (RX0) / 1 (TX0) — USB | PC'ye. Proteus'ta bunu **COMPIM** bileşeniyle sanal COM portuna bağlayıp gerçek CTC yazılımınla (Processing/C#/Python ne yazacaksan) haberleştirirsin |
| 18 (TX1) / 19 (RX1) | BOARD A'ya çapraz bağlı |
| 16 (TX2) / 17 (RX2) | BOARD B'ye çapraz bağlı |

### 5.2 Makas Servo Motorları (3 Makas × 2 Servo = 6 adet)

Kablolama: Servonun **turuncu/sarı (sinyal)** kablosu Arduino pinine, **kırmızı (VCC)** ayrı bir **5V harici güç kaynağına** (Arduino'nun 5V pini 6 servoyu kaldıramaz, akım yetmez), **kahverengi/siyah (GND)** hem harici kaynağın GND'sine hem Arduino GND'sine (ortak toprak şart).

| Makas | Servo | Pin |
|---|---|---|
| Makas 1 — Hat1 tarafı dili | Servo1 | D2 |
| Makas 1 — Hat2 tarafı dili | Servo2 | D3 |
| Makas 2 — Hat1 tarafı dili | Servo3 | D4 |
| Makas 2 — Hat2 tarafı dili | Servo4 | D5 |
| Makas 3 — Hat1 tarafı dili | Servo5 | D6 |
| Makas 3 — Hat2 tarafı dili | Servo6 | D7 |

Servo açıları: **NORMAL (düz yol) = 0°**, **TERS (sapan yol) = 90°** gibi iki sabit pozisyon kullan (Servo.write(0) / Servo.write(90)).

### 5.3 Makas Kumanda Butonları (yerinde manuel test için)

Her makas için bir buton — CTC yazılımı çalışmadan önce Proteus'ta tek başına test etmek için faydalı. Kablolama: `INPUT_PULLUP`, bir ucu pine, diğer ucu GND'ye (aynı switch mantığı).

| Makas | Pin |
|---|---|
| Makas 1 kumanda | D22 |
| Makas 2 kumanda | D23 |
| Makas 3 kumanda | D24 |

### 5.4 Makas Pozisyon Geri Bildirimi (opsiyonel ama gerçekçi olması için önerilir)

Gerçek TCDD/Siemens sisteminde her makasın "Normal'de kilitli mi / Ters'te kilitli mi" bilgisini veren 2 adet limit switch'i vardır. İstersen ekle:

| Makas | Normal Limit Switch | Ters Limit Switch |
|---|---|---|
| Makas 1 | D30 | D31 |
| Makas 2 | D32 | D33 |
| Makas 3 | D34 | D35 |

### 5.5 Diğer
| Pin | Görev |
|---|---|
| D13 (dahili LED) | Master "canlı/heartbeat" göstergesi — her saniye yanıp söner, sistemin çöküp çökmediğini gösterir |
| D28 | Acil Dur (Emergency Stop) butonu — basılınca tüm hatta kırmızı sinyal komutu yollanır |

---

## 6. Kurulum Sırası (Adım Adım, Sıfırdan)

1. **Board A'yı kur:** Önce 10 anahtarı (D22-D31) bağla, sonra 30 LED'i (D32-D53, A0-A7) direnç + LED şeklinde bağla. Kod yükle, tek başına test et (anahtara bas, ilgili blok kırmızıya dönmeli).
2. **Board B'yi** Board A ile birebir aynı şekilde kur.
3. **Board C'yi kur:** Önce 6 servoyu bağla (harici 5V güç kaynağı unutma), sonra 3 makas butonunu, sonra (istersen) limit switch'leri.
4. **Üç kartı birbirine bağla:** A'nın 18/19'u ↔ C'nin 18/19'u (çapraz), B'nin 16/17'si ↔ C'nin 16/17'si (çapraz). **Üç kartın GND'lerini tek noktada birleştir.**
5. **PC bağlantısı:** Board C'nin USB'sini (D0/D1) Proteus'ta COMPIM üzerinden sanal COM portuna bağla, CTC yazılımını o porta bağla.
6. Her kartı ayrı ayrı test ettikten sonra hepsini birlikte çalıştır.

---

## 7. Malzeme Listesi (Özet)

- 3 × Arduino Mega 2560
- 60 × LED (20 blok × 3 renk — kırmızı/sarı/yeşil)
- 60 × 220-330 Ω direnç
- 20 × SPST switch (blok işgal simülasyonu)
- 6 × Servo motor (SG90 veya benzeri, Proteus'ta "SERVO" bileşeni)
- 3 × buton (makas kumanda)
- 6 × limit switch (opsiyonel, makas pozisyon geri bildirimi)
- 1 × harici 5V güç kaynağı (servo besleme için, min 2A)
- Çapraz seri bağlantı kabloları (TX↔RX)

Bu şemayla en az 10 blok, en az 3 makas ve tam Siemens/TCDD mantığında blok sinyalizasyonu (Kırmızı-Sarı-Yeşil) şartlarının hepsi karşılanıyor.
