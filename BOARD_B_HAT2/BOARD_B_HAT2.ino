// ============================================================
//  BOARD B — HAT2 MERKEZ
//  10 Blok İşgal Sensörü + 10 Blok Sinyali (Kırmızı/Sarı/Yeşil)
//  Master karta (BOARD C) Serial2 (pin 16 TX2 / 17 RX2) üzerinden
//  blok durumunu gönderir.
//  Pin şeması BOARD A ile birebir aynıdır, sadece haberleşme
//  portu ve mesaj öneki (H2:) farklıdır.
// ============================================================

const int BLOK_SAYISI = 10;

const int occPins[BLOK_SAYISI] = {22,23,24,25,26,27,28,29,30,31};

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
  Serial.begin(9600);    // USB debug (opsiyonel)
  Serial2.begin(9600);   // Master'a (BOARD C) haberleşme hattı

  for (int i = 0; i < BLOK_SAYISI; i++) {
    pinMode(occPins[i], INPUT_PULLUP);
    for (int r = 0; r < 3; r++) pinMode(sigPins[i][r], OUTPUT);
  }
}

void readOccupancy() {
  for (int i = 0; i < BLOK_SAYISI; i++) {
    occupied[i] = (digitalRead(occPins[i]) == LOW);
  }
}

void setSignal(int i, int aspect) {
  digitalWrite(sigPins[i][0], aspect == 0);
  digitalWrite(sigPins[i][1], aspect == 1);
  digitalWrite(sigPins[i][2], aspect == 2);
}

void updateSignals() {
  for (int i = 0; i < BLOK_SAYISI; i++) {
    if (occupied[i]) {
      setSignal(i, 0);
    } else {
      bool nextOccupied = (i < BLOK_SAYISI - 1) ? occupied[i + 1] : false;
      setSignal(i, nextOccupied ? 1 : 2);
    }
  }
}

void sendStatus() {
  String msg = "H2:";
  for (int i = 0; i < BLOK_SAYISI; i++) msg += occupied[i] ? "1" : "0";
  Serial2.println(msg);
}

void loop() {
  readOccupancy();
  updateSignals();

  if (millis() - lastSend > 250) {
    sendStatus();
    lastSend = millis();
  }
}
