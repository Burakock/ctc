import tkinter as tk
from tkinter import ttk, messagebox
import serial
import serial.tools.list_ports
import threading
import queue
import json
from datetime import datetime


# ============================================================
# CTC HAT KONTROL MERKEZİ - Python / Tkinter
# Proteus COMPIM <-> com0com <-> Python
#
# Önerilen bağlantı:
#   Proteus COMPIM -> COM30
#   Python CTC     -> COM31
#
# COM30/COM31 ters de olabilir; önemli olan iki uygulamanın
# aynı sanal portu açmamasıdır.
# ============================================================

BLOCK_COUNT = 10
DEFAULT_BAUD = 9600


class CTCApp:
    def __init__(self, root):
        self.root = root
        self.root.title("CTC — HAT KONTROL MERKEZİ")
        self.root.geometry("1366x768")
        self.root.minsize(1100, 650)
        self.root.configure(bg="#0a0e13")

        self.ser = None
        self.running = False
        self.rx_thread = None
        self.rx_queue = queue.Queue()

        self.h1 = [0] * BLOCK_COUNT
        self.h2 = [0] * BLOCK_COUNT
        self.switches = [0, 0, 0]
        self.last_heartbeat = None
        self.rx_packets = 0

        self.cells = {"h1": [], "h2": []}
        self.lamps = {"h1": [], "h2": []}
        self.switch_labels = []

        self._build_style()
        self._build_ui()
        self.refresh_ports()
        self.log("BOARD C protokolü: PC->BOARD C = SW0:0 / SW0:1; BOARD C->PC = JSON, otomatik 250 ms.")
        self.log("Önerilen com0com: Proteus COMPIM=COM36, Python CTC=COM35.")
        self.update_clock()
        self.process_rx_queue()
        self.check_heartbeat()

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    # ---------------- COLORS ----------------
    BG = "#0a0e13"
    PANEL = "#10171f"
    PANEL2 = "#141c25"
    BORDER = "#25323d"
    TEXT = "#dce6ee"
    MUTED = "#72818b"
    DIM = "#3f4d57"
    CYAN = "#22b8cf"
    GREEN = "#2ecc71"
    AMBER = "#f0b90b"
    RED = "#ff3b30"
    OCC_BG = "#43130f"

    def _build_style(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "TCombobox",
            fieldbackground=self.PANEL,
            background=self.PANEL,
            foreground=self.TEXT,
            bordercolor=self.BORDER,
            arrowcolor=self.CYAN,
        )

    def _label(self, parent, text, size=10, color=None, bold=False, **kwargs):
        return tk.Label(
            parent,
            text=text,
            bg=kwargs.pop("bg", parent.cget("bg")),
            fg=color or self.TEXT,
            font=("Consolas", size, "bold" if bold else "normal"),
            **kwargs,
        )

    def _button(self, parent, text, command, primary=False, **kwargs):
        bg = self.CYAN if primary else self.PANEL
        fg = "#001318" if primary else self.TEXT
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=bg,
            fg=fg,
            activebackground="#3fd0e6" if primary else self.BORDER,
            activeforeground="#ffffff",
            relief="flat",
            bd=0,
            highlightthickness=1,
            highlightbackground=self.CYAN if primary else self.BORDER,
            font=("Consolas", 10, "bold"),
            padx=14,
            pady=7,
            cursor="hand2",
            **kwargs,
        )

    # ---------------- UI ----------------
    def _build_ui(self):
        # Header
        header = tk.Frame(self.root, bg=self.PANEL, height=70)
        header.pack(fill="x")
        header.pack_propagate(False)

        brand = tk.Frame(header, bg=self.PANEL)
        brand.pack(side="left", padx=24)

        mark = tk.Label(
            brand, text="C", bg=self.CYAN, fg="#001318",
            font=("Arial", 18, "bold"), width=2, height=1
        )
        mark.pack(side="left", padx=(0, 12), pady=17)

        title_box = tk.Frame(brand, bg=self.PANEL)
        title_box.pack(side="left")

        self._label(
            title_box, "CTC — HAT KONTROL MERKEZİ",
            18, "#f2f7fa", True, bg=self.PANEL
        ).pack(anchor="w")
        self._label(
            title_box, "SIEMENS / TCDD TİPİ SİNYALİZASYON İZLEME PANELİ",
            8, self.MUTED, False, bg=self.PANEL
        ).pack(anchor="w")

        clock_box = tk.Frame(header, bg=self.PANEL)
        clock_box.pack(side="right", padx=25)

        self.clock_label = self._label(
            clock_box, "--:--:--", 18, self.CYAN, True, bg=self.PANEL
        )
        self.clock_label.pack(anchor="e")
        self.date_label = self._label(
            clock_box, "—", 8, self.MUTED, False, bg=self.PANEL
        )
        self.date_label.pack(anchor="e")

        # Connection bar
        conn = tk.Frame(self.root, bg=self.PANEL2, height=52)
        conn.pack(fill="x")
        conn.pack_propagate(False)

        self._label(conn, "PORT", 9, self.MUTED, True, bg=self.PANEL2).pack(
            side="left", padx=(24, 6)
        )

        self.port_var = tk.StringVar(value="COM31")
        self.port_combo = ttk.Combobox(
            conn, textvariable=self.port_var, width=9,
            state="readonly", font=("Consolas", 10)
        )
        self.port_combo.pack(side="left", padx=(0, 10), pady=9)

        self._button(conn, "YENİLE", self.refresh_ports).pack(
            side="left", padx=(0, 8)
        )

        self._label(conn, "BAUD", 9, self.MUTED, True, bg=self.PANEL2).pack(
            side="left", padx=(4, 6)
        )
        self.baud_var = tk.StringVar(value=str(DEFAULT_BAUD))
        baud_combo = ttk.Combobox(
            conn, textvariable=self.baud_var,
            values=("9600", "19200", "38400", "57600", "115200"),
            width=8, state="readonly", font=("Consolas", 10)
        )
        baud_combo.pack(side="left", padx=(0, 12), pady=9)

        self.connect_btn = self._button(
            conn, "SERİ PORTA BAĞLAN", self.connect, primary=True
        )
        self.connect_btn.pack(side="left", padx=4)

        self.disconnect_btn = self._button(
            conn, "BAĞLANTIYI KES", self.disconnect
        )
        self.disconnect_btn.pack(side="left", padx=4)
        self.disconnect_btn.config(state="disabled")

        self.link_dot = tk.Label(
            conn, text="●", bg=self.PANEL2, fg=self.DIM,
            font=("Arial", 13)
        )
        self.link_dot.pack(side="left", padx=(20, 5))
        self.link_text = self._label(
            conn, "BAĞLI DEĞİL", 9, self.MUTED, True, bg=self.PANEL2
        )
        self.link_text.pack(side="left")

        self.heart_dot = tk.Label(
            conn, text="●", bg=self.PANEL2, fg=self.DIM,
            font=("Arial", 13)
        )
        self.heart_dot.pack(side="left", padx=(20, 5))
        self._label(
            conn, "MASTER HEARTBEAT", 9, self.MUTED, True, bg=self.PANEL2
        ).pack(side="left")

        self._label(
            conn, "PYTHON / PY SERIAL", 8, self.DIM, True, bg=self.PANEL2
        ).pack(side="right", padx=25)

        # Main
        main = tk.Frame(self.root, bg=self.BG)
        main.pack(fill="both", expand=True, padx=24, pady=18)

        title_row = tk.Frame(main, bg=self.BG)
        title_row.pack(fill="x", pady=(0, 10))
        self._label(
            title_row, "HAT DİYAGRAMI", 16, "#ffffff", True, bg=self.BG
        ).pack(side="left")
        self._label(
            title_row, "CANLI BLOK İŞGAL VE SİNYAL DURUMU", 8,
            self.MUTED, False, bg=self.BG
        ).pack(side="left", padx=10, pady=4)

        board = tk.Frame(
            main, bg=self.PANEL, highlightbackground=self.BORDER,
            highlightthickness=1
        )
        board.pack(fill="x")

        self.create_line(board, "HAT 1", "BOARD A", "h1")

        # Switch strip
        switch_frame = tk.Frame(board, bg=self.PANEL)
        switch_frame.pack(fill="x", padx=35, pady=5)

        for i in range(3):
            box = tk.Frame(switch_frame, bg=self.PANEL)
            box.pack(side="left", expand=True)
            self._label(
                box, f"MAKAS {i+1}", 9, self.TEXT, True, bg=self.PANEL
            ).pack()
            lab = self._label(
                box, "NORMAL", 9, self.MUTED, True, bg=self.PANEL
            )
            lab.pack()
            self.switch_labels.append(lab)

        self.create_line(board, "HAT 2", "BOARD B", "h2")

        legend = tk.Frame(board, bg=self.PANEL)
        legend.pack(fill="x", padx=35, pady=(12, 18))

        for color, text in (
            (self.RED, "KIRMIZI — Blok Dolu"),
            (self.AMBER, "SARI — Yaklaşma"),
            (self.GREEN, "YEŞİL — Hat Açık"),
        ):
            item = tk.Frame(legend, bg=self.PANEL)
            item.pack(side="left", padx=(0, 25))
            tk.Label(item, text="●", bg=self.PANEL, fg=color,
                     font=("Arial", 11)).pack(side="left")
            self._label(item, text, 8, self.MUTED, False,
                        bg=self.PANEL).pack(side="left", padx=5)

        # Bottom area
        bottom = tk.Frame(main, bg=self.BG)
        bottom.pack(fill="both", expand=True, pady=(14, 0))

        left = tk.Frame(bottom, bg=self.PANEL,
                        highlightbackground=self.BORDER, highlightthickness=1)
        left.pack(side="left", fill="both", expand=True)

        self._label(
            left, "OLAY KAYDI", 12, "#ffffff", True, bg=self.PANEL
        ).pack(anchor="w", padx=14, pady=(10, 6))

        self.log_text = tk.Text(
            left, bg="#080b0f", fg="#7fa3ad",
            insertbackground=self.TEXT, relief="flat",
            font=("Consolas", 9), wrap="none"
        )
        self.log_text.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.log_text.configure(state="disabled")

        right = tk.Frame(bottom, bg=self.PANEL, width=250,
                         highlightbackground=self.BORDER, highlightthickness=1)
        right.pack(side="right", fill="y", padx=(14, 0))
        right.pack_propagate(False)

        self._label(
            right, "TEST / KOMUT", 12, "#ffffff", True, bg=self.PANEL
        ).pack(anchor="w", padx=14, pady=(10, 8))

        self._label(
            right, "Makas komutu", 8, self.MUTED, True, bg=self.PANEL
        ).pack(anchor="w", padx=14)

        self.cmd_switch = tk.IntVar(value=1)
        ttk.Combobox(
            right, textvariable=self.cmd_switch,
            values=(1, 2, 3), width=8, state="readonly",
            font=("Consolas", 10)
        ).pack(anchor="w", padx=14, pady=5)

        self.cmd_value = tk.StringVar(value="NORMAL")
        ttk.Combobox(
            right, textvariable=self.cmd_value,
            values=("NORMAL", "TERS"), width=12, state="readonly",
            font=("Consolas", 10)
        ).pack(anchor="w", padx=14, pady=5)

        self._button(
            right, "MAKAS KOMUTU GÖNDER", self.send_switch_command
        ).pack(fill="x", padx=14, pady=8)

        self._button(
            right, "DURUMU OKU / BEKLE", self.request_status
        ).pack(fill="x", padx=14, pady=4)

        self._label(
            right,
            "Gelen veri formatı:\n"
            '{"h1":[0,1,...],\n'
            ' "h2":[0,0,...],\n'
            ' "sw":[0,1,0]}',
            8, self.MUTED, False, bg=self.PANEL, justify="left"
        ).pack(anchor="w", padx=14, pady=15)

        # Status bar
        status = tk.Frame(self.root, bg="#080b0f", height=26)
        status.pack(fill="x", side="bottom")
        status.pack_propagate(False)
        self.status_label = self._label(
            status, "HAZIR — COM30/COM31 com0com çifti bekleniyor",
            8, self.MUTED, False, bg="#080b0f"
        )
        self.status_label.pack(side="left", padx=14)

    def create_line(self, parent, name, board_name, key):
        row = tk.Frame(parent, bg=self.PANEL)
        row.pack(fill="x", padx=35, pady=(16, 0))

        head = tk.Frame(row, bg=self.PANEL)
        head.pack(fill="x")
        self._label(
            head, name, 11, self.CYAN, True, bg=self.PANEL
        ).pack(side="left")
        self._label(
            head, board_name, 7, self.CYAN, True,
            bg="#10252b", padx=8, pady=2
        ).pack(side="left", padx=8)

        track = tk.Frame(row, bg=self.PANEL2, height=70)
        track.pack(fill="x", pady=(8, 4))
        track.pack_propagate(False)

        self.cells[key] = []
        self.lamps[key] = []

        # Rail
        rail = tk.Frame(track, bg=self.BORDER, height=2)
        rail.place(relx=0.01, rely=0.51, relwidth=0.98)

        for i in range(BLOCK_COUNT):
            block = tk.Frame(track, bg=self.PANEL2)
            block.pack(side="left", fill="both", expand=True, padx=3)

            lamp = tk.Label(
                block, text="●", bg=self.PANEL2, fg=self.DIM,
                font=("Arial", 11)
            )
            lamp.pack(pady=(6, 0))
            self.lamps[key].append(lamp)

            cell = tk.Label(
                block, text=f"B{i+1:02d}",
                bg="#2c3944", fg=self.MUTED,
                font=("Consolas", 9, "bold"),
                height=1
            )
            cell.pack(fill="x", pady=(3, 6))
            self.cells[key].append(cell)

    # ---------------- CLOCK ----------------
    def update_clock(self):
        now = datetime.now()
        self.clock_label.config(text=now.strftime("%H:%M:%S"))
        self.date_label.config(
            text=now.strftime("%A, %d %B %Y").upper()
        )
        self.root.after(1000, self.update_clock)

    # ---------------- PORTS ----------------
    def refresh_ports(self):
        ports = [p.device for p in serial.tools.list_ports.comports()]

        # COM30/COM31 varsa öne al
        preferred = [p for p in ("COM30", "COM31") if p in ports]
        others = [p for p in ports if p not in preferred]
        values = preferred + others

        self.port_combo["values"] = values

        if "COM31" in values:
            self.port_var.set("COM31")
        elif values:
            self.port_var.set(values[0])

        self.log(f"Seri portlar tarandı: {', '.join(values) if values else 'port bulunamadı'}")

    # ---------------- SERIAL ----------------
    def connect(self):
        if self.running:
            return

        port_name = self.port_var.get().strip()
        if not port_name:
            messagebox.showwarning("CTC", "Bir seri port seçin.")
            return

        try:
            baud = int(self.baud_var.get())
            self.ser = serial.Serial(
                port=port_name,
                baudrate=baud,
                timeout=0.2,
                write_timeout=0.5
            )
            self.running = True
            self.last_heartbeat = datetime.now()

            self.connect_btn.config(state="disabled")
            self.disconnect_btn.config(state="normal")
            self.port_combo.config(state="disabled")

            self.link_dot.config(fg=self.GREEN)
            self.link_text.config(text="BAĞLI", fg=self.GREEN)
            self.status_label.config(
                text=f"BAĞLI — {port_name} @ {baud} baud",
                fg=self.GREEN
            )

            self.log(f"Seri port açıldı: {port_name} @ {baud} baud")

            self.rx_thread = threading.Thread(
                target=self.read_serial,
                daemon=True
            )
            self.rx_thread.start()

        except Exception as e:
            messagebox.showerror("Seri Port Hatası", str(e))
            self.log(f"HATA: {e}")

    def disconnect(self):
        self.running = False

        try:
            if self.ser and self.ser.is_open:
                self.ser.close()
        except Exception:
            pass

        self.ser = None
        self.connect_btn.config(state="normal")
        self.disconnect_btn.config(state="disabled")
        self.port_combo.config(state="readonly")

        self.link_dot.config(fg=self.DIM)
        self.link_text.config(text="BAĞLI DEĞİL", fg=self.MUTED)
        self.heart_dot.config(fg=self.DIM)
        self.status_label.config(
            text="BAĞLANTI KESİLDİ", fg=self.MUTED
        )
        self.log("Seri bağlantı kesildi.")

    def read_serial(self):
        buffer = ""

        while self.running and self.ser:
            try:
                raw = self.ser.read(256)
                if not raw:
                    continue

                buffer += raw.decode("utf-8", errors="replace")

                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()
                    if line:
                        self.rx_queue.put(line.replace("\\r", "").strip())

            except Exception as e:
                if self.running:
                    self.rx_queue.put("__SERIAL_ERROR__:" + str(e))
                break

    def process_rx_queue(self):
        try:
            while True:
                line = self.rx_queue.get_nowait()

                if line.startswith("__SERIAL_ERROR__:"):
                    self.log("SERİ HATASI: " + line.split(":", 1)[1])
                    self.disconnect()
                    break

                self.handle_line(line)
        except queue.Empty:
            pass

        self.root.after(30, self.process_rx_queue)

    def handle_line(self, line):
        line = line.strip()
        if line.startswith("{"):
            try:
                data = json.loads(line)

                h1 = data.get("h1")
                h2 = data.get("h2")
                sw = data.get("sw")

                if isinstance(h1, list):
                    self.h1 = (h1 + [0] * BLOCK_COUNT)[:BLOCK_COUNT]
                    self.render_line("h1", self.h1)

                if isinstance(h2, list):
                    self.h2 = (h2 + [0] * BLOCK_COUNT)[:BLOCK_COUNT]
                    self.render_line("h2", self.h2)

                if isinstance(sw, list):
                    self.switches = (sw + [0, 0, 0])[:3]
                    self.render_switches()

                self.last_heartbeat = datetime.now()
                self.rx_packets += 1
                self.heart_dot.config(fg=self.GREEN)

                self.log(f"RX JSON #{self.rx_packets}: " + line)

            except json.JSONDecodeError:
                self.log("JSON AYRIŞTIRMA HATASI: " + line)
        else:
            self.log("RX: " + line)

    # ---------------- RENDER ----------------
    def render_line(self, key, arr):
        for i, occupied in enumerate(arr):
            cell = self.cells[key][i]
            lamp = self.lamps[key][i]

            if occupied:
                cell.config(
                    bg=self.OCC_BG,
                    fg="#ffd9d5",
                    highlightbackground=self.RED,
                    highlightthickness=1
                )
            else:
                cell.config(
                    bg="#2c3944",
                    fg=self.MUTED,
                    highlightthickness=0
                )

            if occupied:
                aspect = "red"
            else:
                next_occ = arr[i + 1] if i < BLOCK_COUNT - 1 else 0
                aspect = "yellow" if next_occ else "green"

            lamp.config(fg={
                "red": self.RED,
                "yellow": self.AMBER,
                "green": self.GREEN
            }[aspect])

    def render_switches(self):
        for i, value in enumerate(self.switches):
            self.switch_labels[i].config(
                text="TERS" if value else "NORMAL",
                fg=self.CYAN if value else self.MUTED
            )

    # ---------------- COMMANDS ----------------
    def send_line(self, text):
        if not self.ser or not self.ser.is_open:
            self.log("KOMUT GÖNDERİLEMEDİ: Önce seri porta bağlanın.")
            return False

        try:
            self.ser.write((text.rstrip("\n") + "\n").encode("utf-8"))
            self.log("TX: " + text.rstrip("\n"))
            return True
        except Exception as e:
            self.log("TX HATASI: " + str(e))
            return False

    def send_switch_command(self):
        idx = int(self.cmd_switch.get()) - 1
        value = 1 if self.cmd_value.get() == "TERS" else 0
        self.send_line(f"SW{idx}:{value}")

    def request_status(self):
        # BOARD C firmware'i PC'den JSON istemez.
        # Durum paketini kendisi her 250 ms'de bir gönderir.
        self.log("Durum isteği gönderilmedi; BOARD C JSON'u otomatik olarak 250 ms'de bir gönderir.")

    # ---------------- LOG / HEARTBEAT ----------------
    def log(self, msg):
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        self.log_text.config(state="normal")
        self.log_text.insert("end", f"[{timestamp}] {msg}\n")
        self.log_text.see("end")

        # Son 500 satırı tut
        lines = int(self.log_text.index("end-1c").split(".")[0])
        if lines > 500:
            self.log_text.delete("1.0", "100.0")

        self.log_text.config(state="disabled")

    def check_heartbeat(self):
        if self.running and self.last_heartbeat:
            elapsed = (datetime.now() - self.last_heartbeat).total_seconds()
            if elapsed > 1.5:
                self.heart_dot.config(fg=self.RED)
            else:
                self.heart_dot.config(fg=self.GREEN)

        self.root.after(500, self.check_heartbeat)

    def on_close(self):
        self.running = False
        try:
            if self.ser and self.ser.is_open:
                self.ser.close()
        except Exception:
            pass
        self.root.destroy()


def main():
    root = tk.Tk()
    app = CTCApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
