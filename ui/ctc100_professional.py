#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ============================================================
#  Railway CTC100 — Professional TCDD Style Interface
#  Gerçek Endüstriyel CTC Arayüzü (SIEMENS Tarzı)
#  Real-time Track Schematic, Train Animation, Signal Control
# ============================================================

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import serial
import serial.tools.list_ports
import threading
import queue
import json
from datetime import datetime
import math

# ============================================================
# CONSTANTS & COLORS
# ============================================================

# SIEMENS/TCDD Standard Colors
COLOR_BG_DARK = "#0d0f12"
COLOR_TRACK = "#1a1a1a"
COLOR_PANEL_BG = "#1c1f24"
COLOR_PANEL_BORDER = "#3a3f44"
COLOR_TEXT_PRIMARY = "#e0e6ec"
COLOR_TEXT_SECONDARY = "#8a92a0"
COLOR_ACCENT = "#00d4ff"

# Signal Colors (IEC 60087)
COLOR_SIG_STOP = "#ff0000"
COLOR_SIG_APPROACH = "#ffff00"
COLOR_SIG_PROCEED = "#00cc00"
COLOR_SIG_CAUTION = "#ffaa00"

# Track State Colors
COLOR_BLOCK_EMPTY = "#0a1428"
COLOR_BLOCK_OCCUPIED = "#3a0a0a"
COLOR_TRACK_RAIL = "#404040"
COLOR_SWITCH_NORMAL = "#004400"
COLOR_SWITCH_DIVERGE = "#440000"

# Geometry
TRACK_Y_BASE = 200
TRACK_HEIGHT = 80
STATION_SPACING = 150
BLOCK_WIDTH = 140
SIGNAL_RADIUS = 12

# ============================================================
# MAIN CTC APPLICATION
# ============================================================

class CTC100Professional:
    """Railway CTC100 — Professional Control Interface"""

    def __init__(self, root):
        self.root = root
        self.root.title("SIEMENS CTC100 — Railway Centralized Traffic Control")
        self.root.geometry("1920x1080")
        self.root.configure(bg=COLOR_BG_DARK)
        self.root.iconname("CTC100")

        # Serial Communication
        self.ser = None
        self.running = False
        self.rx_thread = None
        self.rx_queue = queue.Queue()

        # Data Model
        self.trains = {}  # {train_id: {'position': block_id, 'speed': 0, 'direction': 1}}
        self.blocks = {}  # {block_id: {'occupied': 0, 'signal': 2, 'name': 'B0'}}
        self.switches = {}  # {switch_id: {'position': 0, 'locked': False, 'name': 'X1'}}
        self.routes = {}  # {route_id: {...}}
        self.active_routes = []
        self.selected_route = None

        # UI State
        self.zoom_level = 1.0
        self.scroll_x = 0
        self.scroll_y = 0
        self.show_grid = True
        self.show_labels = True

        # Initialize Data
        self._init_data()
        self._build_ui()
        self._setup_bindings()
        self.refresh_ports()
        self.update_display()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    # ===== DATA INITIALIZATION =====

    def _init_data(self):
        """Initialize blocks, switches, routes, trains"""

        # Define 5 Platforms (25 blocks total)
        platform_names = ["PLATFORM 1", "PLATFORM 2", "PLATFORM 3", "PLATFORM 4", "PLATFORM 5"]
        for p_idx in range(5):
            for b_idx in range(5):
                block_id = p_idx * 5 + b_idx
                self.blocks[block_id] = {
                    'id': block_id,
                    'name': f'B{block_id}',
                    'platform': platform_names[p_idx],
                    'occupied': 0,
                    'signal': 2,  # 0=STOP, 1=APPROACH, 2=PROCEED
                    'normalized': False,
                    'track_x': 150 + b_idx * BLOCK_WIDTH,
                    'track_y': TRACK_Y_BASE + p_idx * TRACK_HEIGHT
                }

        # Define 7 Switches
        switches_config = [
            (0, 'X1', 150 + 3 * BLOCK_WIDTH, TRACK_Y_BASE + 0.5 * TRACK_HEIGHT),
            (1, 'X2', 150 + 4 * BLOCK_WIDTH, TRACK_Y_BASE + 0.5 * TRACK_HEIGHT),
            (2, 'X3', 150 + 3 * BLOCK_WIDTH, TRACK_Y_BASE + 2.5 * TRACK_HEIGHT),
            (3, 'X4', 150 + 4 * BLOCK_WIDTH, TRACK_Y_BASE + 2.5 * TRACK_HEIGHT),
            (4, 'X5', 150 + 3 * BLOCK_WIDTH, TRACK_Y_BASE + 4 * TRACK_HEIGHT),
            (5, 'X6', 150 + 4 * BLOCK_WIDTH, TRACK_Y_BASE + 4 * TRACK_HEIGHT),
            (6, 'X7', 150 + 3 * BLOCK_WIDTH, TRACK_Y_BASE + 5.5 * TRACK_HEIGHT),
        ]

        for sw_id, name, x, y in switches_config:
            self.switches[sw_id] = {
                'id': sw_id,
                'name': name,
                'position': 0,  # 0=NORMAL, 1=DIVERGING
                'locked': False,
                'track_x': x,
                'track_y': y
            }

        # Define Routes
        self.routes = {
            0: {'id': 0, 'name': 'R0: Entry → Platform 1', 'blocks': [0, 1, 2, 3, 4], 'switches': [], 'state': 'INACTIVE'},
            1: {'id': 1, 'name': 'R1: Entry → Platform 2', 'blocks': [5, 6, 7, 8, 9], 'switches': [], 'state': 'INACTIVE'},
            2: {'id': 2, 'name': 'R2: Platform 1 ↔ Platform 2', 'blocks': [2, 3, 7, 8, 9], 'switches': [0], 'state': 'INACTIVE'},
            3: {'id': 3, 'name': 'R3: Platform 3 ↔ Platform 4', 'blocks': [12, 13, 17, 18, 19], 'switches': [2], 'state': 'INACTIVE'},
            4: {'id': 4, 'name': 'R4: Entry → Platform 5', 'blocks': [20, 21, 22, 23, 24], 'switches': [], 'state': 'INACTIVE'},
        }

        # Test Trains (for simulation)
        self.trains = {
            1: {'id': 1, 'name': 'TN001', 'position': 1, 'target': 4, 'speed': 0, 'state': 'STOPPED'},
            2: {'id': 2, 'name': 'TN002', 'position': 6, 'target': 9, 'speed': 0, 'state': 'STOPPED'},
        }

    # ===== UI BUILDING =====

    def _build_ui(self):
        """Build main interface"""

        # ===== TOP TOOLBAR =====
        toolbar = tk.Frame(self.root, bg=COLOR_PANEL_BG, height=60, relief="sunken", bd=1)
        toolbar.pack(fill="x", side="top")
        toolbar.pack_propagate(False)

        # Logo & Title
        title_frame = tk.Frame(toolbar, bg=COLOR_PANEL_BG)
        title_frame.pack(side="left", padx=12, pady=8)

        tk.Label(title_frame, text="🚂 SIEMENS CTC100", bg=COLOR_PANEL_BG,
                fg=COLOR_ACCENT, font=("Arial", 12, "bold")).pack(side="left")

        tk.Label(title_frame, text="Railway Signalling & Traffic Control",
                bg=COLOR_PANEL_BG, fg=COLOR_TEXT_SECONDARY, font=("Arial", 8)).pack(side="left", padx=(8, 0))

        # Separator
        ttk.Separator(toolbar, orient="vertical").pack(side="left", fill="y", padx=8)

        # Connection Controls
        tk.Label(toolbar, text="PORT:", bg=COLOR_PANEL_BG, fg=COLOR_TEXT_PRIMARY,
                font=("Arial", 9, "bold")).pack(side="left")

        self.port_var = tk.StringVar(value="COM31")
        port_combo = ttk.Combobox(toolbar, textvariable=self.port_var, width=10, state="readonly")
        port_combo.pack(side="left", padx=4)

        tk.Button(toolbar, text="REFRESH", command=self.refresh_ports, bg=COLOR_PANEL_BORDER,
                 fg=COLOR_TEXT_PRIMARY, relief="flat", font=("Arial", 8, "bold")).pack(side="left", padx=2)

        tk.Label(toolbar, text="BAUD:", bg=COLOR_PANEL_BG, fg=COLOR_TEXT_PRIMARY,
                font=("Arial", 9, "bold")).pack(side="left", padx=(12, 0))

        self.baud_var = tk.StringVar(value="9600")
        baud_combo = ttk.Combobox(toolbar, textvariable=self.baud_var, width=8, state="readonly",
                                 values=("9600", "19200", "38400", "57600"))
        baud_combo.pack(side="left", padx=4)

        self.connect_btn = tk.Button(toolbar, text="▶ CONNECT", command=self.connect,
                                     bg="#1a4d1a", fg="#00ff00", relief="raised",
                                     font=("Arial", 9, "bold"), padx=8, pady=4)
        self.connect_btn.pack(side="left", padx=2)

        self.disconnect_btn = tk.Button(toolbar, text="⊠ DISCONNECT", command=self.disconnect,
                                        bg="#4d1a1a", fg="#ff6b6b", relief="raised",
                                        font=("Arial", 9, "bold"), padx=8, pady=4, state="disabled")
        self.disconnect_btn.pack(side="left", padx=2)

        # Status Indicator
        self.status_dot = tk.Label(toolbar, text="●", bg=COLOR_PANEL_BG, fg="#ff3333",
                                  font=("Arial", 16))
        self.status_dot.pack(side="right", padx=12)

        self.status_text = tk.Label(toolbar, text="OFFLINE", bg=COLOR_PANEL_BG,
                                   fg=COLOR_TEXT_SECONDARY, font=("Arial", 9))
        self.status_text.pack(side="right", padx=(0, 4))

        # ===== MAIN LAYOUT =====
        main_frame = tk.Frame(self.root, bg=COLOR_BG_DARK)
        main_frame.pack(fill="both", expand=True)

        # --- LEFT SIDE: Station Schematic ---
        left_frame = tk.Frame(main_frame, bg=COLOR_TRACK, relief="sunken", bd=1)
        left_frame.pack(side="left", fill="both", expand=True, padx=4, pady=4)

        # Schematic Title
        self._label(left_frame, "STATION TRACK SCHEMATIC", 11, "BOLD").pack(anchor="w", padx=8, pady=4)
        self._label(left_frame, "Real-time Block Occupancy & Signal Status", 8).pack(anchor="w", padx=8, pady=(0, 4))

        # Canvas for track schematic
        self.canvas_track = tk.Canvas(
            left_frame, bg=COLOR_TRACK, width=1100, height=700,
            relief="flat", bd=0, highlightthickness=0
        )
        self.canvas_track.pack(fill="both", expand=True, padx=4, pady=4)

        # --- RIGHT SIDE: Control Panel ---
        right_frame = tk.Frame(main_frame, bg=COLOR_PANEL_BG, width=350, relief="sunken", bd=1)
        right_frame.pack(side="right", fill="y", padx=4, pady=4)
        right_frame.pack_propagate(False)

        # Route Management
        self._label(right_frame, "ROUTE MANAGEMENT", 10, "BOLD").pack(anchor="w", padx=8, pady=(8, 4))

        self.route_list = tk.Listbox(right_frame, bg=COLOR_TRACK, fg=COLOR_TEXT_PRIMARY,
                                     font=("Consolas", 9), height=7, relief="sunken", bd=1,
                                     selectmode="SINGLE")
        self.route_list.pack(fill="both", expand=False, padx=8, pady=4)

        for rid, route in self.routes.items():
            self.route_list.insert(tk.END, route['name'])

        self.route_list.bind('<<ListboxSelect>>', lambda e: self.on_route_select())

        tk.Button(right_frame, text="REQUEST ROUTE", command=self.request_route,
                 bg="#003d7a", fg="#87ceeb", relief="raised", font=("Arial", 9, "bold"),
                 padx=6, pady=4).pack(fill="x", padx=8, pady=2)

        tk.Button(right_frame, text="CANCEL ROUTE", command=self.cancel_route,
                 bg="#7a3d00", fg="#ffb347", relief="raised", font=("Arial", 9, "bold"),
                 padx=6, pady=4).pack(fill="x", padx=8, pady=2)

        # Active Routes Display
        self._label(right_frame, "ACTIVE ROUTES", 10, "BOLD").pack(anchor="w", padx=8, pady=(12, 4))

        self.active_routes_text = tk.Label(right_frame, text="No active routes",
                                          bg=COLOR_TRACK, fg=COLOR_SIG_PROCEED,
                                          font=("Consolas", 9), justify="left",
                                          relief="sunken", bd=1, padx=6, pady=6)
        self.active_routes_text.pack(fill="x", padx=8, pady=4)

        # Manual Switch Control
        self._label(right_frame, "MANUAL SWITCH CONTROL", 10, "BOLD").pack(anchor="w", padx=8, pady=(12, 4))

        self.switch_var = tk.StringVar(value="0")
        switch_combo = ttk.Combobox(right_frame, textvariable=self.switch_var,
                                   values=[f"X{i+1}" for i in range(7)],
                                   state="readonly", font=("Arial", 9), width=10)
        switch_combo.pack(fill="x", padx=8, pady=2)

        switch_btn_frame = tk.Frame(right_frame, bg=COLOR_PANEL_BG)
        switch_btn_frame.pack(fill="x", padx=8, pady=2)

        tk.Button(switch_btn_frame, text="NORMAL", command=lambda: self.set_switch(0),
                 bg=COLOR_SWITCH_NORMAL, fg=COLOR_TEXT_PRIMARY, relief="raised",
                 font=("Arial", 9, "bold"), width=15).pack(side="left", padx=1)

        tk.Button(switch_btn_frame, text="DIVERGING", command=lambda: self.set_switch(1),
                 bg=COLOR_SWITCH_DIVERGE, fg=COLOR_TEXT_PRIMARY, relief="raised",
                 font=("Arial", 9, "bold"), width=15).pack(side="left", padx=1)

        # Block Normalization
        self._label(right_frame, "BLOCK NORMALIZATION", 10, "BOLD").pack(anchor="w", padx=8, pady=(12, 4))

        self.norm_check = tk.BooleanVar(value=False)
        tk.Checkbutton(right_frame, text="Enable Normalization", variable=self.norm_check,
                      bg=COLOR_PANEL_BG, fg=COLOR_TEXT_PRIMARY, selectcolor=COLOR_PANEL_BORDER,
                      font=("Arial", 9)).pack(anchor="w", padx=8, pady=2)

        tk.Button(right_frame, text="NORMALIZE ALL", command=self.normalize_blocks,
                 bg="#2d1a5c", fg="#dda0dd", relief="raised", font=("Arial", 9, "bold"),
                 padx=6, pady=4).pack(fill="x", padx=8, pady=2)

        # System Info
        self._label(right_frame, "SYSTEM INFO", 10, "BOLD").pack(anchor="w", padx=8, pady=(12, 4))

        self.info_text = tk.Label(right_frame, text="Waiting for connection...",
                                 bg=COLOR_TRACK, fg=COLOR_TEXT_SECONDARY,
                                 font=("Consolas", 8), justify="left",
                                 relief="sunken", bd=1, padx=6, pady=6)
        self.info_text.pack(fill="both", expand=True, padx=8, pady=4)

        # Emergency Stop
        ttk.Separator(right_frame, orient="horizontal").pack(fill="x", padx=8, pady=8)

        tk.Button(right_frame, text="🚨 EMERGENCY STOP 🚨", command=self.emergency_stop,
                 bg="#ff0000", fg="#ffffff", relief="raised", font=("Arial", 10, "bold"),
                 padx=8, pady=8).pack(fill="x", padx=8, pady=(0, 8))

        # ===== BOTTOM: Event Log =====
        log_frame = tk.Frame(self.root, bg=COLOR_PANEL_BG, relief="sunken", bd=1)
        log_frame.pack(fill="x", side="bottom", padx=4, pady=4)

        self._label(log_frame, "EVENT LOG & DIAGNOSTICS", 10, "BOLD").pack(anchor="w", padx=8, pady=(4, 2))

        self.log_text = scrolledtext.ScrolledText(
            log_frame, bg=COLOR_TRACK, fg="#90ee90",
            insertbackground=COLOR_TEXT_PRIMARY, relief="sunken", bd=0,
            font=("Consolas", 8), height=5, wrap="word"
        )
        self.log_text.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.log_text.config(state="disabled")

        # Configure log tags
        self.log_text.tag_configure("OK", foreground="#00ff00")
        self.log_text.tag_configure("ERROR", foreground="#ff0000")
        self.log_text.tag_configure("WARN", foreground="#ffff00")
        self.log_text.tag_configure("INFO", foreground="#87ceeb")

    def _label(self, parent, text, size=9, style="NORMAL"):
        """Create styled label"""
        fg = COLOR_TEXT_PRIMARY if style == "BOLD" else COLOR_TEXT_SECONDARY
        font_style = ("Arial", size, "bold") if style == "BOLD" else ("Arial", size)
        return tk.Label(parent, text=text, bg=parent.cget("bg"), fg=fg, font=font_style)

    def _setup_bindings(self):
        """Setup keyboard/mouse bindings"""
        self.canvas_track.bind("<Button-1>", self.on_canvas_click)
        self.canvas_track.bind("<MouseWheel>", self.on_mouse_wheel)
        self.canvas_track.bind("<Button-4>", self.on_mouse_wheel)
        self.canvas_track.bind("<Button-5>", self.on_mouse_wheel)

    # ===== TRACK SCHEMATIC RENDERING =====

    def render_schematic(self):
        """Render complete station track schematic"""
        self.canvas_track.delete("all")

        # Draw grid
        if self.show_grid:
            self._draw_grid()

        # Draw platforms
        for p_idx in range(5):
            self._draw_platform(p_idx)

        # Draw trains
        for train_id, train in self.trains.items():
            self._draw_train(train)

    def _draw_grid(self):
        """Draw background grid"""
        for x in range(0, 1100, 50):
            self.canvas_track.create_line(x, 0, x, 700, fill="#1a1a1a", dash=(2, 2))
        for y in range(0, 700, 50):
            self.canvas_track.create_line(0, y, 1100, y, fill="#1a1a1a", dash=(2, 2))

    def _draw_platform(self, p_idx):
        """Draw single platform with tracks and blocks"""
        platform_y = TRACK_Y_BASE + p_idx * TRACK_HEIGHT
        platform_name = f"PLATFORM {p_idx + 1}"

        # Platform name label
        self.canvas_track.create_text(10, platform_y + 15, text=platform_name,
                                     fill=COLOR_TEXT_PRIMARY, font=("Arial", 9, "bold"),
                                     anchor="w")

        # Draw track line
        self.canvas_track.create_rectangle(120, platform_y, 900, platform_y + 20,
                                          fill=COLOR_TRACK_RAIL, outline=COLOR_PANEL_BORDER)

        # Draw blocks
        for b_idx in range(5):
            block_id = p_idx * 5 + b_idx
            block = self.blocks[block_id]

            x = 150 + b_idx * BLOCK_WIDTH
            y = platform_y

            # Block background
            occupied_color = COLOR_BLOCK_OCCUPIED if block['occupied'] else COLOR_BLOCK_EMPTY
            self.canvas_track.create_rectangle(x, y, x + BLOCK_WIDTH - 5, y + 20,
                                              fill=occupied_color, outline=COLOR_PANEL_BORDER, width=2)

            # Block label
            self.canvas_track.create_text(x + BLOCK_WIDTH / 2 - 2, y + 10, text=block['name'],
                                         fill=COLOR_TEXT_PRIMARY, font=("Consolas", 8, "bold"),
                                         anchor="center")

            # Signal lamp (Traffic Light style)
            signal_colors = {
                0: COLOR_SIG_STOP,      # RED - STOP
                1: COLOR_SIG_APPROACH,  # YELLOW - APPROACH
                2: COLOR_SIG_PROCEED    # GREEN - PROCEED
            }
            signal_color = signal_colors.get(block['signal'], COLOR_SIG_STOP)

            self.canvas_track.create_oval(x + BLOCK_WIDTH + 5, y + 4, x + BLOCK_WIDTH + 25, y + 16,
                                         fill=signal_color, outline=COLOR_PANEL_BORDER, width=1)

            # Normalized indicator
            if block['normalized']:
                self.canvas_track.create_text(x + BLOCK_WIDTH / 2 - 2, y - 5,
                                             text="✓ NORM", fill="#00ff00",
                                             font=("Arial", 7, "bold"))

        # Draw switches for this platform pair
        if p_idx < 4:
            switch_ids = [p_idx // 2 * 2, p_idx // 2 * 2 + 1]
            for sw_idx, sw_id in enumerate(switch_ids[:1]):  # Simplified
                x = 850
                y = platform_y + 10
                self._draw_switch(sw_id, x, y)

    def _draw_switch(self, sw_id, x, y):
        """Draw switch/turnout on schematic"""
        switch = self.switches[sw_id]
        position = switch['position']

        # Switch symbol
        color = COLOR_SWITCH_NORMAL if position == 0 else COLOR_SWITCH_DIVERGE
        self.canvas_track.create_polygon(
            x, y, x + 15, y - 8, x + 15, y + 8,
            fill=color, outline=COLOR_PANEL_BORDER, width=1
        )

        # Label
        self.canvas_track.create_text(x - 20, y, text=switch['name'],
                                     fill=COLOR_TEXT_PRIMARY, font=("Arial", 8, "bold"),
                                     anchor="e")

        # Lock indicator
        if switch['locked']:
            self.canvas_track.create_text(x + 20, y - 12, text="🔒",
                                         font=("Arial", 10))

    def _draw_train(self, train):
        """Draw train on schematic"""
        block = self.blocks.get(train['position'])
        if not block:
            return

        x = block['track_x'] + BLOCK_WIDTH / 2
        y = block['track_y'] + 10

        # Train rectangle
        self.canvas_track.create_rectangle(x - 25, y - 12, x + 25, y + 12,
                                          fill="#4d7a99", outline="#87ceeb", width=2)

        # Train number
        self.canvas_track.create_text(x, y, text=train['name'],
                                     fill=COLOR_TEXT_PRIMARY, font=("Consolas", 8, "bold"),
                                     anchor="center")

    # ===== INTERACTION HANDLERS =====

    def on_canvas_click(self, event):
        """Handle canvas click for block selection"""
        if not self.norm_check.get():
            return

        # Simplified: just toggle normalization on clicked area
        self.log(f"Block selected at ({event.x}, {event.y})", "INFO")

    def on_mouse_wheel(self, event):
        """Handle zoom with mouse wheel"""
        if event.num == 5 or event.delta < 0:
            self.zoom_level *= 0.9
        else:
            self.zoom_level *= 1.1

        self.log(f"Zoom: {self.zoom_level:.2f}x", "INFO")

    def on_route_select(self):
        """Handle route selection"""
        sel = self.route_list.curselection()
        if sel:
            self.selected_route = sel[0]
            self.log(f"Route {self.selected_route} selected", "INFO")

    def request_route(self):
        """Request selected route"""
        if self.selected_route is None:
            messagebox.showwarning("CTC100", "Select a route first")
            return

        self.send_command(f"R{self.selected_route}")
        self.log(f"Route {self.selected_route} requested", "OK")

    def cancel_route(self):
        """Cancel active route"""
        if not self.active_routes:
            messagebox.showwarning("CTC100", "No active routes")
            return

        self.send_command(f"CANCEL:{self.active_routes[0]}")

    def set_switch(self, position):
        """Set manual switch"""
        sw_name = self.switch_var.get()
        self.send_command(f"SW{sw_name[-1]}:{position}")

    def normalize_blocks(self):
        """Normalize all blocks"""
        for block in self.blocks.values():
            block['normalized'] = True
        self.log("All blocks normalized", "OK")
        self.send_command("NORMALIZE")

    def emergency_stop(self):
        """Emergency stop"""
        if messagebox.askyesno("🚨 EMERGENCY STOP", "ACTIVATE EMERGENCY STOP?"):
            self.send_command("ESTOP")
            self.log("🚨 EMERGENCY STOP ACTIVATED", "ERROR")
            self.status_dot.config(fg="#ff0000")

    # ===== SERIAL COMMUNICATION =====

    def refresh_ports(self):
        """Refresh serial ports list"""
        ports = [p.device for p in serial.tools.list_ports.comports()]
        if not ports:
            ports = ["COM31"]

    def connect(self):
        """Connect to serial port"""
        if self.running:
            return

        try:
            port = self.port_var.get()
            baud = int(self.baud_var.get())
            self.ser = serial.Serial(port, baud, timeout=0.2)
            self.running = True

            self.connect_btn.config(state="disabled")
            self.disconnect_btn.config(state="normal")
            self.status_dot.config(fg="#00ff00")
            self.status_text.config(text="ONLINE", fg=COLOR_SIG_PROCEED)

            self.log(f"Connected to {port} @ {baud} baud", "OK")

            self.rx_thread = threading.Thread(target=self.read_serial, daemon=True)
            self.rx_thread.start()
        except Exception as e:
            messagebox.showerror("Error", str(e))
            self.log(f"Connection failed: {e}", "ERROR")

    def disconnect(self):
        """Disconnect"""
        self.running = False
        if self.ser:
            self.ser.close()

        self.connect_btn.config(state="normal")
        self.disconnect_btn.config(state="disabled")
        self.status_dot.config(fg="#ff3333")
        self.status_text.config(text="OFFLINE", fg=COLOR_TEXT_SECONDARY)

    def read_serial(self):
        """Read serial in background"""
        buffer = ""
        while self.running and self.ser:
            try:
                data = self.ser.read(256)
                if data:
                    buffer += data.decode("utf-8", errors="replace")
                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        self.rx_queue.put(line.strip())
            except:
                break

    def send_command(self, cmd):
        """Send command to Arduino"""
        if not self.ser or not self.ser.is_open:
            self.log("Not connected!", "ERROR")
            return

        try:
            self.ser.write((cmd + "\n").encode())
            self.log(f"TX: {cmd}", "INFO")
        except Exception as e:
            self.log(f"TX Error: {e}", "ERROR")

    # ===== DISPLAY UPDATE =====

    def update_display(self):
        """Update display (called periodically)"""
        # Process RX queue
        try:
            while True:
                line = self.rx_queue.get_nowait()
                if line.startswith("{"):
                    try:
                        data = json.loads(line)
                        h1 = data.get("h1", [])
                        for i, occ in enumerate(h1[:10]):
                            if i < len(self.blocks):
                                self.blocks[i]['occupied'] = occ
                    except:
                        pass
                else:
                    self.log(line, "INFO")
        except queue.Empty:
            pass

        # Update active routes display
        if self.active_routes:
            routes_text = "\n".join([self.routes[rid]['name'] for rid in self.active_routes[:3]])
        else:
            routes_text = "No active routes"

        self.active_routes_text.config(text=routes_text)

        # Update info text
        occupied_blocks = sum(1 for b in self.blocks.values() if b['occupied'])
        self.info_text.config(text=f"Blocks Occupied: {occupied_blocks}/25\nActive Routes: {len(self.active_routes)}\nStatus: READY")

        # Render track schematic
        self.render_schematic()

        self.root.after(250, self.update_display)

    def log(self, msg, level="INFO"):
        """Log message"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_msg = f"[{timestamp}] [{level:6}] {msg}\n"

        self.log_text.config(state="normal")
        self.log_text.insert("end", log_msg, level)
        self.log_text.see("end")

        lines = int(self.log_text.index("end-1c").split(".")[0])
        if lines > 500:
            self.log_text.delete("1.0", "50.0")

        self.log_text.config(state="disabled")

    def on_close(self):
        """Close application"""
        self.running = False
        if self.ser:
            self.ser.close()
        self.root.destroy()


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    root = tk.Tk()
    app = CTC100Professional(root)
    root.mainloop()
