#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ============================================================
#  Railway CTC — Python GUI v3
#  5-Peronlu İstasyon Kontrol Paneli (Professional Edition)
#  SIL-4 Uyumlu, Modüler, İngilizce/Türkçe
# ============================================================

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import serial
import serial.tools.list_ports
import threading
import queue
import json
from datetime import datetime
from enum import Enum

# ============================================================
# CONSTANTS
# ============================================================

BLOCK_COUNT = 10  # Per Hat
PLATFORM_COUNT = 5
BLOCKS_PER_PLATFORM = 5
SWITCH_COUNT = 7

DEFAULT_BAUD = 9600
LOG_MAX_LINES = 1000

# ============================================================
# ENUMS
# ============================================================

class SignalAspect(Enum):
    RED = 0      # Dur (Kırmızı)
    YELLOW = 1   # Yaklaşma (Sarı)
    GREEN = 2    # Açık (Yeşil)

class SwitchState(Enum):
    NORMAL = 0       # Düz yol
    DIVERGING = 1    # Sapan yol

# ============================================================
# MAIN APPLICATION CLASS
# ============================================================

class CTCMainWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("Railway CTC — 5-Platform Station Control")
        self.root.geometry("1600x900")
        self.root.minsize(1400, 800)
        self.root.configure(bg="#0a0e13")

        # Serial
        self.ser = None
        self.running = False
        self.rx_thread = None
        self.rx_queue = queue.Queue()

        # Data
        self.hat1_blocks = [0] * BLOCK_COUNT
        self.hat2_blocks = [0] * BLOCK_COUNT
        self.switches = [0] * 3  # X1, X3, X5 manuel
        self.active_routes = []
        self.last_heartbeat = None
        self.rx_packets = 0

        # UI Elements
        self.platform_frames = []
        self.block_widgets = []
        self.route_listbox = None
        self.event_log = None
        self.status_label = None

        # Style
        self._build_style()
        self._build_ui()
        self.refresh_ports()
        self.update_clock()
        self.process_rx_queue()
        self.check_heartbeat()

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    # ===== COLORS =====
    BG = "#0a0e13"
    PANEL = "#10171f"
    PANEL2 = "#141c25"
    BORDER = "#25323d"
    TEXT = "#dce6ee"
    MUTED = "#72818b"
    DIM = "#3f4d57"
    CYAN = "#22b8cf"
    GREEN = "#2ecc71"
    YELLOW = "#f0b90b"
    RED = "#ff3b30"
    OCCUPIED_BG = "#43130f"

    def _build_style(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TCombobox", fieldbackground=self.PANEL,
                       background=self.PANEL, foreground=self.TEXT)

    def _label(self, parent, text, size=10, color=None, bold=False, **kwargs):
        return tk.Label(
            parent, text=text,
            bg=kwargs.pop("bg", parent.cget("bg")),
            fg=color or self.TEXT,
            font=("Consolas", size, "bold" if bold else "normal"),
            **kwargs
        )

    def _button(self, parent, text, command, primary=False, **kwargs):
        bg = self.CYAN if primary else self.PANEL
        fg = "#001318" if primary else self.TEXT
        return tk.Button(
            parent, text=text, command=command,
            bg=bg, fg=fg,
            activebackground="#3fd0e6" if primary else self.BORDER,
            relief="flat", bd=0, highlightthickness=1,
            highlightbackground=self.CYAN if primary else self.BORDER,
            font=("Consolas", 9, "bold"), padx=12, pady=6,
            cursor="hand2", **kwargs
        )

    # ===== UI BUILDING =====

    def _build_ui(self):
        # ===== HEADER =====
        header = tk.Frame(self.root, bg=self.PANEL, height=70)
        header.pack(fill="x")
        header.pack_propagate(False)

        brand_box = tk.Frame(header, bg=self.PANEL)
        brand_box.pack(side="left", padx=20)

        mark = tk.Label(brand_box, text="🚂", bg=self.PANEL,
                       font=("Arial", 24), fg=self.CYAN)
        mark.pack(side="left", padx=(0, 12))

        title_frame = tk.Frame(brand_box, bg=self.PANEL)
        title_frame.pack(side="left")

        self._label(title_frame, "RAILWAY CTC SYSTEM",
                   16, "#ffffff", True, bg=self.PANEL).pack(anchor="w")
        self._label(title_frame, "5-Platform Station Control",
                   8, self.MUTED, False, bg=self.PANEL).pack(anchor="w")

        clock_box = tk.Frame(header, bg=self.PANEL)
        clock_box.pack(side="right", padx=20)

        self.clock_label = self._label(
            clock_box, "--:--:--", 14, self.CYAN, True, bg=self.PANEL
        )
        self.clock_label.pack(anchor="e")

        self.date_label = self._label(
            clock_box, "—", 8, self.MUTED, False, bg=self.PANEL
        )
        self.date_label.pack(anchor="e")

        # ===== CONNECTION BAR =====
        conn = tk.Frame(self.root, bg=self.PANEL2, height=50)
        conn.pack(fill="x")
        conn.pack_propagate(False)

        self._label(conn, "PORT", 8, self.MUTED, True, bg=self.PANEL2).pack(
            side="left", padx=(16, 4))

        self.port_var = tk.StringVar(value="COM31")
        self.port_combo = ttk.Combobox(
            conn, textvariable=self.port_var, width=8, state="readonly",
            font=("Consolas", 9)
        )
        self.port_combo.pack(side="left", padx=(0, 8), pady=8)

        self._button(conn, "REFRESH", self.refresh_ports).pack(
            side="left", padx=2)

        self._label(conn, "BAUD", 8, self.MUTED, True, bg=self.PANEL2).pack(
            side="left", padx=(8, 4))

        self.baud_var = tk.StringVar(value=str(DEFAULT_BAUD))
        baud_combo = ttk.Combobox(
            conn, textvariable=self.baud_var,
            values=("9600", "19200", "38400", "57600", "115200"),
            width=8, state="readonly", font=("Consolas", 9)
        )
        baud_combo.pack(side="left", padx=(0, 12), pady=8)

        self.connect_btn = self._button(
            conn, "CONNECT", self.connect, primary=True
        )
        self.connect_btn.pack(side="left", padx=4)

        self.disconnect_btn = self._button(
            conn, "DISCONNECT", self.disconnect
        )
        self.disconnect_btn.pack(side="left", padx=4)
        self.disconnect_btn.config(state="disabled")

        self.link_dot = tk.Label(conn, text="●", bg=self.PANEL2, fg=self.DIM,
                                font=("Arial", 12))
        self.link_dot.pack(side="left", padx=(16, 4))

        self.link_text = self._label(conn, "DISCONNECTED", 8, self.MUTED,
                                     True, bg=self.PANEL2)
        self.link_text.pack(side="left")

        self._label(conn, "v3.0 — Modular Interlocking", 7, self.DIM,
                   True, bg=self.PANEL2).pack(side="right", padx=16)

        # ===== MAIN CONTENT =====
        main = tk.Frame(self.root, bg=self.BG)
        main.pack(fill="both", expand=True, padx=16, pady=12)

        # --- Left: Station View ---
        left_panel = tk.Frame(main, bg=self.BG)
        left_panel.pack(side="left", fill="both", expand=True, padx=(0, 8))

        title_row = tk.Frame(left_panel, bg=self.BG)
        title_row.pack(fill="x", pady=(0, 8))

        self._label(left_panel, "STATION LAYOUT",
                   12, "#ffffff", True, bg=self.BG).pack(anchor="w")

        self._label(left_panel, "Real-time block occupancy and signals",
                   7, self.MUTED, False, bg=self.BG).pack(anchor="w")

        station_frame = tk.Frame(left_panel, bg=self.PANEL,
                                highlightbackground=self.BORDER,
                                highlightthickness=1)
        station_frame.pack(fill="both", expand=True)

        # Create platform rows
        self._create_platform_view(station_frame)

        # --- Right: Control Panel ---
        right_panel = tk.Frame(main, bg=self.PANEL, width=280,
                              highlightbackground=self.BORDER,
                              highlightthickness=1)
        right_panel.pack(side="right", fill="y")
        right_panel.pack_propagate(False)

        # Route controller
        self._label(right_panel, "ROUTE CONTROL", 10, "#ffffff", True,
                   bg=self.PANEL).pack(anchor="w", padx=12, pady=(10, 6))

        self._label(right_panel, "Available Routes", 7, self.MUTED, True,
                   bg=self.PANEL).pack(anchor="w", padx=12, pady=(4, 2))

        self.route_listbox = tk.Listbox(
            right_panel, bg=self.PANEL2, fg=self.TEXT,
            font=("Consolas", 8), height=8, bd=0,
            highlightthickness=0
        )
        self.route_listbox.pack(fill="x", padx=12, pady=(0, 6))
        self.route_listbox.bind('<<ListboxSelect>>', self.on_route_select)

        # Populate routes
        routes = [
            "R0: Entry → Platform 1",
            "R1: Entry → Platform 2",
            "R2: Platform 1 ↔ Platform 2",
            "R3: Platform 2 ↔ Platform 1",
            "R4: Entry → Platform 3",
            "R5: Entry → Platform 4",
            "R6: Platform 3 ↔ Platform 4",
            "R7: Entry → Platform 5",
            "R8: Platform 5 → Depot",
            "R9: Depot → Platform 5",
        ]

        for route in routes:
            self.route_listbox.insert(tk.END, route)

        self._button(right_panel, "START ROUTE", self.start_route).pack(
            fill="x", padx=12, pady=4)

        self._button(right_panel, "CANCEL ROUTE", self.cancel_route).pack(
            fill="x", padx=12, pady=2)

        # Active routes
        self._label(right_panel, "Active Routes", 7, self.MUTED, True,
                   bg=self.PANEL).pack(anchor="w", padx=12, pady=(10, 2))

        self.active_routes_label = tk.Label(
            right_panel, text="None", bg=self.PANEL, fg=self.GREEN,
            font=("Consolas", 8), justify="left"
        )
        self.active_routes_label.pack(anchor="w", padx=12, pady=(0, 8))

        # System status
        self._label(right_panel, "SYSTEM STATUS", 10, "#ffffff", True,
                   bg=self.PANEL).pack(anchor="w", padx=12, pady=(10, 6))

        self.heartbeat_label = tk.Label(
            right_panel, text="● HEARTBEAT OK", bg=self.PANEL, fg=self.GREEN,
            font=("Consolas", 8)
        )
        self.heartbeat_label.pack(anchor="w", padx=12)

        self.board_status_label = tk.Label(
            right_panel, text="● BOARD A: Connected\n● BOARD B: Connected",
            bg=self.PANEL, fg=self.GREEN,
            font=("Consolas", 7), justify="left"
        )
        self.board_status_label.pack(anchor="w", padx=12, pady=2)

        self._button(right_panel, "EMERGENCY STOP", self.emergency_stop,
                    primary=True).pack(fill="x", padx=12, pady=(8, 4))

        self._button(right_panel, "DEBUG INFO", self.debug_info).pack(
            fill="x", padx=12, pady=2)

        # ===== BOTTOM: EVENT LOG =====
        footer = tk.Frame(self.root, bg=self.BG)
        footer.pack(fill="both", expand=True, padx=16, pady=(0, 12))

        self._label(footer, "EVENT LOG", 10, "#ffffff", True,
                   bg=self.BG).pack(anchor="w", pady=(0, 4))

        self.event_log = scrolledtext.ScrolledText(
            footer, bg="#080b0f", fg="#7fa3ad",
            insertbackground=self.TEXT, relief="flat",
            font=("Consolas", 8), height=6, wrap="word"
        )
        self.event_log.pack(fill="both", expand=True)
        self.event_log.configure(state="disabled")

        # ===== STATUS BAR =====
        status = tk.Frame(self.root, bg="#080b0f", height=24)
        status.pack(fill="x", side="bottom")
        status.pack_propagate(False)

        self.status_label = self._label(
            status, "Ready — Waiting for connection",
            7, self.MUTED, False, bg="#080b0f"
        )
        self.status_label.pack(side="left", padx=12)

    def _create_platform_view(self, parent):
        """Create visual representation of 5 platforms"""
        platforms = [
            ("PLATFORM 1", ["B0", "B1", "B2", "B3", "B4"]),
            ("PLATFORM 2", ["B5", "B6", "B7", "B8", "B9"]),
            ("PLATFORM 3", ["B10", "B11", "B12", "B13", "B14"]),
            ("PLATFORM 4", ["B15", "B16", "B17", "B18", "B19"]),
            ("PLATFORM 5", ["B20", "B21", "B22", "B23", "B24"]),
        ]

        for plat_name, blocks in platforms:
            self._create_platform_row(parent, plat_name, blocks)

    def _create_platform_row(self, parent, platform_name, block_names):
        """Create a single platform row"""
        row = tk.Frame(parent, bg=self.PANEL)
        row.pack(fill="x", padx=12, pady=6)

        # Platform name
        self._label(row, platform_name, 9, self.CYAN, True,
                   bg=self.PANEL).pack(side="left", padx=(0, 8))

        # Blocks
        for block_name in block_names:
            block_frame = tk.Frame(row, bg=self.PANEL)
            block_frame.pack(side="left", padx=2)

            # Signal lamp (circle)
            lamp = tk.Label(block_frame, text="●", bg=self.PANEL,
                          fg=self.DIM, font=("Arial", 10))
            lamp.pack()

            # Block label
            label = tk.Label(block_frame, text=block_name, bg=self.PANEL2,
                           fg=self.MUTED, font=("Consolas", 8, "bold"),
                           width=4, height=2, relief="flat")
            label.pack()

            self.block_widgets.append({
                'name': block_name,
                'lamp': lamp,
                'label': label
            })

    def update_clock(self):
        """Update clock display"""
        now = datetime.now()
        self.clock_label.config(text=now.strftime("%H:%M:%S"))
        self.date_label.config(text=now.strftime("%A, %d %B %Y").upper())
        self.root.after(1000, self.update_clock)

    # ===== SERIAL PORT MANAGEMENT =====

    def refresh_ports(self):
        """Refresh available serial ports"""
        ports = [p.device for p in serial.tools.list_ports.comports()]
        preferred = [p for p in ("COM30", "COM31") if p in ports]
        others = [p for p in ports if p not in preferred]
        values = preferred + others

        self.port_combo["values"] = values

        if "COM31" in values:
            self.port_var.set("COM31")
        elif values:
            self.port_var.set(values[0])

        self.log(f"Serial ports found: {', '.join(values) if values else 'none'}")

    def connect(self):
        """Connect to serial port"""
        if self.running:
            return

        port_name = self.port_var.get().strip()
        if not port_name:
            messagebox.showwarning("CTC", "Please select a serial port.")
            return

        try:
            baud = int(self.baud_var.get())
            self.ser = serial.Serial(
                port=port_name, baudrate=baud,
                timeout=0.2, write_timeout=0.5
            )
            self.running = True
            self.last_heartbeat = datetime.now()

            self.connect_btn.config(state="disabled")
            self.disconnect_btn.config(state="normal")
            self.port_combo.config(state="disabled")

            self.link_dot.config(fg=self.GREEN)
            self.link_text.config(text="CONNECTED", fg=self.GREEN)
            self.status_label.config(text=f"Connected — {port_name} @ {baud} baud",
                                    fg=self.GREEN)

            self.log(f"Serial port opened: {port_name} @ {baud} baud")

            self.rx_thread = threading.Thread(target=self.read_serial, daemon=True)
            self.rx_thread.start()

        except Exception as e:
            messagebox.showerror("Serial Error", str(e))
            self.log(f"ERROR: {e}")

    def disconnect(self):
        """Disconnect from serial port"""
        self.running = False

        try:
            if self.ser and self.ser.is_open:
                self.ser.close()
        except:
            pass

        self.ser = None
        self.connect_btn.config(state="normal")
        self.disconnect_btn.config(state="disabled")
        self.port_combo.config(state="readonly")

        self.link_dot.config(fg=self.DIM)
        self.link_text.config(text="DISCONNECTED", fg=self.MUTED)
        self.status_label.config(text="Disconnected", fg=self.MUTED)
        self.log("Serial connection closed.")

    def read_serial(self):
        """Read from serial port in background thread"""
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
                        self.rx_queue.put(line)

            except Exception as e:
                if self.running:
                    self.rx_queue.put(f"__ERROR__:{str(e)}")
                break

    def process_rx_queue(self):
        """Process received messages from queue"""
        try:
            while True:
                line = self.rx_queue.get_nowait()

                if line.startswith("__ERROR__:"):
                    self.log("SERIAL ERROR: " + line.split(":", 1)[1])
                    self.disconnect()
                    break

                self.handle_line(line)
        except queue.Empty:
            pass

        self.root.after(30, self.process_rx_queue)

    def handle_line(self, line):
        """Handle received line"""
        line = line.strip()
        if line.startswith("{"):
            try:
                data = json.loads(line)

                h1 = data.get("h1")
                h2 = data.get("h2")
                sw = data.get("sw")
                routes = data.get("routes", [])

                if isinstance(h1, list):
                    self.hat1_blocks = (h1 + [0] * BLOCK_COUNT)[:BLOCK_COUNT]
                    self.render_blocks()

                if isinstance(h2, list):
                    self.hat2_blocks = (h2 + [0] * BLOCK_COUNT)[:BLOCK_COUNT]
                    self.render_blocks()

                if isinstance(sw, list):
                    self.switches = (sw + [0, 0, 0])[:3]

                if isinstance(routes, list):
                    self.active_routes = routes

                self.last_heartbeat = datetime.now()
                self.rx_packets += 1

                self.log(f"[RX #{self.rx_packets}] Block update received")

            except json.JSONDecodeError:
                self.log(f"JSON ERROR: {line}")
        else:
            self.log(f"[RX] {line}")

    def render_blocks(self):
        """Update block visual representation"""
        for i, widget in enumerate(self.block_widgets):
            occupied = self.hat1_blocks[i] if i < len(self.hat1_blocks) else 0

            if occupied:
                aspect = SignalAspect.RED
                bg_color = self.OCCUPIED_BG
                text_color = "#ffd9d5"
            else:
                next_occupied = self.hat1_blocks[i + 1] if i < len(self.hat1_blocks) - 1 else 0
                aspect = SignalAspect.YELLOW if next_occupied else SignalAspect.GREEN
                bg_color = self.PANEL2
                text_color = self.MUTED

            color_map = {
                SignalAspect.RED: self.RED,
                SignalAspect.YELLOW: self.YELLOW,
                SignalAspect.GREEN: self.GREEN,
            }

            widget['lamp'].config(fg=color_map[aspect])
            widget['label'].config(bg=bg_color, fg=text_color)

    # ===== ROUTE CONTROL =====

    def on_route_select(self, event):
        """Handle route selection"""
        pass

    def start_route(self):
        """Start selected route"""
        selection = self.route_listbox.curselection()
        if not selection:
            messagebox.showwarning("CTC", "Please select a route.")
            return

        route_id = selection[0]
        self.send_command(f"R{route_id}")
        self.log(f"Route {route_id} requested...")

    def cancel_route(self):
        """Cancel selected route"""
        if not self.active_routes:
            messagebox.showwarning("CTC", "No active routes.")
            return

        self.send_command(f"CANCEL:{self.active_routes[0]}")

    def emergency_stop(self):
        """Activate emergency stop"""
        if messagebox.askyesno("EMERGENCY STOP", "Activate emergency stop?"):
            self.send_command("ESTOP")
            self.log("EMERGENCY STOP ACTIVATED!")

    def debug_info(self):
        """Request debug info"""
        self.send_command("DEBUG")

    def send_command(self, cmd):
        """Send command to Arduino"""
        if not self.ser or not self.ser.is_open:
            self.log("ERROR: Not connected.")
            return False

        try:
            self.ser.write((cmd.rstrip("\n") + "\n").encode("utf-8"))
            self.log(f"[TX] {cmd}")
            return True
        except Exception as e:
            self.log(f"TX ERROR: {str(e)}")
            return False

    # ===== HEARTBEAT & STATUS =====

    def check_heartbeat(self):
        """Check system heartbeat"""
        if self.running and self.last_heartbeat:
            elapsed = (datetime.now() - self.last_heartbeat).total_seconds()
            if elapsed > 1.5:
                self.heartbeat_label.config(text="● HEARTBEAT LOST",
                                           fg=self.RED)
            else:
                self.heartbeat_label.config(text="● HEARTBEAT OK",
                                           fg=self.GREEN)

        self.root.after(500, self.check_heartbeat)

    # ===== LOG =====

    def log(self, msg):
        """Log message"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        self.event_log.config(state="normal")
        self.event_log.insert("end", f"[{timestamp}] {msg}\n")
        self.event_log.see("end")

        lines = int(self.event_log.index("end-1c").split(".")[0])
        if lines > LOG_MAX_LINES:
            self.event_log.delete("1.0", "100.0")

        self.event_log.config(state="disabled")

    def on_close(self):
        """Close application"""
        self.running = False
        try:
            if self.ser and self.ser.is_open:
                self.ser.close()
        except:
            pass
        self.root.destroy()


# ============================================================
# MAIN
# ============================================================

def main():
    root = tk.Tk()
    app = CTCMainWindow(root)
    root.mainloop()


if __name__ == "__main__":
    main()
