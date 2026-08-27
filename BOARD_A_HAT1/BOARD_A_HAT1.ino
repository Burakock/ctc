// ============================================================
//  BOARD A — HAT1 MERKEZ
//  10 Blok İşgal Sensörü + 10 Blok Sinyali (Kırmızı/Sarı/Yeşil)
//  Master karta (BOARD C) Serial1 (pin 18 TX1 / 19 RX1) üzerinden
//  blok durumunu gönderir.
// ============================================================

const int BLOK_SAYISI = 10;

// İşgal sensör pinleri (D22-D31) — INPUT_PULLUP, anahtar kapanınca LOW = DOLU
const int occPins[BLOK_SAYISI] = {22,23,24,25,26,27,28,29,30,31};

// Sinyal LED pinleri [blok][Kırmızı,Sarı,Yeşil]
const int sigPins[BLOK_SAYISI][3] = {
  {32,33,34},
  {35,36,37},
  {38,39,40},
  {41,42,43},
  {44,45,46},
  {47,48,49},
  {50,51,52},
  {53,A0,A1},
  {A2,A3,A4},
  {A5,A6,A7}
};

bool occupied[BLOK_SAYISI];
unsigned long lastSend = 0;

void setup() {
  Serial.begin(9600);    // USB üzerinden debug (opsiyonel, PC'ye bağlamana gerek yok)
  Serial1.begin(9600);   // Master'a (BOARD C) haberleşme hattı

  for (int i = 0; i < BLOK_SAYISI; i++) {
    pinMode(occPins[i], INPUT_PULLUP);
    for (int r = 0; r < 3; r++) pinMode(sigPins[i][r], OUTPUT);
  }
}

void readOccupancy() {
  for (int i = 0; i < BLOK_SAYISI; i++) {
    occupied[i] = (digitalRead(occPins[i]) == LOW); // LOW = blok dolu
  }
}

// aspect: 0 = kırmızı, 1 = sarı, 2 = yeşil
void setSignal(int i, int aspect) {
  digitalWrite(sigPins[i][0], aspect == 0);
  digitalWrite(sigPins[i][1], aspect == 1);
  digitalWrite(sigPins[i][2], aspect == 2);
}

void updateSignals() {
  for (int i = 0; i < BLOK_SAYISI; i++) {
    if (occupied[i]) {
      setSignal(i, 0); // blok dolu -> kırmızı
    } else {
      // bir sonraki blok (trenin gideceği yön: B1 -> B10) dolu mu?
      bool nextOccupied = (i < BLOK_SAYISI - 1) ? occupied[i + 1] : false;
      setSignal(i, nextOccupied ? 1 : 2); // sarı (yaklaşma) ya da yeşil
    }
  }
}

void sendStatus() {
  // Format: "H1:0010000000"  (1=dolu, 0=boş, sırayla Blok1..Blok10)
  String msg = "H1:";
  for (int i = 0; i < BLOK_SAYISI; i++) msg += occupied[i] ? "1" : "0";
  Serial1.println(msg);
}

void loop() {
  readOccupancy();
  updateSignals();

  if (millis() - lastSend > 250) {
    sendStatus();
    lastSend = millis();
  }
}
