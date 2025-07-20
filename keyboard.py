import serial
import time
import pyautogui
import re
import tkinter as tk
from tkinter import ttk, font, messagebox, colorchooser
import threading
from queue import Queue
import json
import os
import ctypes
import sys

DEFAULT_CONFIG = {
    'serial_port': 'COM7',
    'baud_rate': 9600,
    'window_width': 150,
    'window_height': 175,
    'inactivity_timeout': 5,
    'corner_radius': 10,
    'bg_color': '#d8d8d8'
}

GUI_UPDATE_INTERVAL = 100
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.1


def parse_serial_line(line):
    patterns = {
        'selection': re.compile(r"Selected: \[(.)\] \| Mode: (.+)"),
        'confirmed': re.compile(r"Confirmed:\s*(.*)"),
        'esc': re.compile(r"ESC pressed"),
        'backspace': re.compile(r"Backspace"),
        'space': re.compile(r"Space inserted"),
        'enter': re.compile(r"Enter"),
        'mode_change': re.compile(r"Mode switched to:\s*(.+)")
    }

    for type_, pattern in patterns.items():
        if match := pattern.search(line):
            if type_ == 'selection':
                return {'type': type_, 'char': match.group(1), 'mode': match.group(2)}
            elif type_ == 'confirmed':
                return {'type': type_, 'char': match.group(1) or ' '}
            elif type_ == 'mode_change':
                return {'type': type_, 'mode': match.group(1)}
            return {'type': type_}

    return {'type': 'unknown', 'raw': line}


def restart_application():
    python = sys.executable
    os.execl(python, python, *sys.argv)


class SerialMonitorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Keyboard Controller")

        self.config = self.load_config()
        self.serial_queue = Queue()
        self.last_activity_time = time.time()
        self.sleeping = False
        self.running = True

        self.setup_fonts()
        self.create_widgets()
        self.setup_window()
        self.start_serial_thread()

        self.root.after(GUI_UPDATE_INTERVAL, self.check_inactivity)
        self.root.after(100, self.check_serial_ready)

    def check_serial_ready(self):
        if not hasattr(self, 'connected') or not self.connected:
            self.show_connection_dialog("Connection failed. Check port/settings and Restart.")

    def show_connection_dialog(self, message):
        if getattr(self, 'connection_dialog', None) and self.connection_dialog.winfo_exists():
            return

        self.connection_dialog = tk.Toplevel(self.root)
        self.connection_dialog.title("Connection Error")
        self.connection_dialog.attributes("-topmost", True)
        tk.Label(self.connection_dialog, text=message, wraplength=300).pack(padx=10, pady=10)
        tk.Button(self.connection_dialog, text="Restart", command=self.restart_app).pack(pady=5)
        self.connection_dialog.protocol("WM_DELETE_WINDOW", lambda: None)

    def restart_app(self):
        if self.connection_dialog.winfo_exists():
            self.connection_dialog.destroy()
        self.on_close()
        restart_application()

    def load_config(self):
        try:
            with open("keyboard_config.json", 'r') as f:
                return json.load(f)
        except:
            return DEFAULT_CONFIG.copy()

    def save_config(self):
        with open("keyboard_config.json", 'w') as f:
            json.dump(self.config, f, indent=4)

    def start_serial_thread(self):
        def serial_loop():
            try:
                with serial.Serial(self.config['serial_port'], self.config['baud_rate'], timeout=1) as ser:
                    self.connected = True
                    if getattr(self, 'connection_dialog', None):
                        self.connection_dialog.destroy()
                    self.update_status(f"Connected to {self.config['serial_port']}")

                    while self.running:
                        if ser.in_waiting > 0:
                            line = ser.readline().decode('utf-8', errors='ignore').strip()
                            if line:
                                self.serial_queue.put(parse_serial_line(line))
                                self.root.event_generate("<<SerialData>>", when="tail")
                        time.sleep(0.01)
            except Exception as e:
                error_msg = f"Serial error: {e}"
                self.serial_queue.put({'type': 'error', 'message': error_msg})
                self.root.after(100, lambda msg=error_msg: self.show_connection_dialog(msg))


        threading.Thread(target=serial_loop, daemon=True).start()

    def process_serial_data(self):
        while not self.serial_queue.empty():
            data = self.serial_queue.get()
            if self.sleeping:
                self.wake_window()
                continue
            self.handle_arduino_input(data)
            self.last_activity_time = time.time()

    def setup_window(self):
        self.root.attributes("-topmost", True)
        self.root.attributes("-toolwindow", True)
        self.root.overrideredirect(True)
        self.root.geometry(f"{self.config['window_width']}x{self.config['window_height']}")
        self.root.configure(bg=self.config.get('bg_color', '#444'))
        self.enable_window_dragging()
        self.apply_corner_radius()

    def enable_window_dragging(self):
        self.root.bind("<Button-1>", self.start_drag)
        self.root.bind("<B1-Motion>", self.perform_drag)

    def start_drag(self, event):
        self.drag_start_x = event.x
        self.drag_start_y = event.y

    def perform_drag(self, event):
        x = self.root.winfo_x() + (event.x - self.drag_start_x)
        y = self.root.winfo_y() + (event.y - self.drag_start_y)
        self.root.geometry(f"+{x}+{y}")
        self.last_activity_time = time.time()

    def apply_corner_radius(self):
        r = self.config.get('corner_radius', 10)
        w, h = self.config['window_width'], self.config['window_height']
        hrgn = ctypes.windll.gdi32.CreateRoundRectRgn(0, 0, w, h, r * 2, r * 2)
        hwnd = self.root.winfo_id()
        ctypes.windll.user32.SetWindowRgn(hwnd, hrgn, True)

    def check_inactivity(self):
        if time.time() - self.last_activity_time > self.config['inactivity_timeout'] and not self.sleeping:
            self.minimize_window()
        self.root.after(GUI_UPDATE_INTERVAL, self.check_inactivity)

    def minimize_window(self):
        self.root.withdraw()
        self.sleeping = True
        self.update_status("Sleeping...")

    def wake_window(self):
        self.root.deiconify()
        self.sleeping = False
        self.update_status("Awake")
        self.root.after(200, lambda: self.update_status("Ready"))

    def setup_fonts(self):
        self.big_font = font.Font(family='Arial', size=12, weight='bold')
        self.medium_font = font.Font(family='Arial', size=8)
        self.small_font = font.Font(family='Arial', size=7)

    def create_widgets(self):
        bg_color = self.config.get('bg_color', '#444')
        text_color = "#000" if sum(int(bg_color[i:i+2], 16) for i in (1, 3, 5)) / 3 > 127 else "#fff"

        style = ttk.Style()
        style.configure("Dark.TFrame", background=bg_color)
        style.configure("Dark.TLabel", background=bg_color, foreground=text_color)
        style.configure("Dark.TButton", background=bg_color)

        frame = ttk.Frame(self.root, padding="2", style="Dark.TFrame")
        frame.pack(fill=tk.BOTH, expand=True)

        top_frame = ttk.Frame(frame, style="Dark.TFrame")
        top_frame.pack(fill=tk.X)

        ttk.Button(top_frame, text="⚙", width=3, command=self.open_settings, style="Dark.TButton").pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(top_frame, text="X", width=3, command=self.on_close, style="Dark.TButton").pack(side=tk.RIGHT, padx=5, pady=5)

        char_frame = ttk.Frame(frame, style="Dark.TFrame")
        char_frame.pack()

        ttk.Label(char_frame, text="Selected:", font=self.medium_font, style="Dark.TLabel").pack(side=tk.LEFT)
        self.char_display = ttk.Label(char_frame, text=" ", font=self.big_font, style="Dark.TLabel")
        self.char_display.pack(side=tk.LEFT, padx=5)

        ttk.Label(frame, text="Mode:", font=self.medium_font, style="Dark.TLabel").pack()
        self.mode_display = ttk.Label(frame, text="Unknown", font=self.medium_font, style="Dark.TLabel")
        self.mode_display.pack(pady=1)

        ttk.Label(frame, text="Last Sent:", font=self.medium_font, style="Dark.TLabel").pack()
        self.confirmed_display = ttk.Label(frame, text=" ", font=self.medium_font, style="Dark.TLabel")
        self.confirmed_display.pack(pady=1)

        self.status_bar = ttk.Label(frame, text="Initializing...", relief=tk.SUNKEN, font=self.small_font, style="Dark.TLabel")
        self.status_bar.pack(fill=tk.X, pady=(2, 0))

    def open_settings(self):
        if getattr(self, 'settings_window', None) and self.settings_window.winfo_exists():
            self.settings_window.lift()
            return

        self.settings_window = tk.Toplevel(self.root)
        self.settings_window.title("Settings")
        self.settings_window.attributes("-topmost", True)
        self.settings_window.protocol("WM_DELETE_WINDOW", self.on_settings_close)

        settings = [
            ("COM Port:", 'serial_port', 0),
            ("Baud Rate:", 'baud_rate', 1),
            ("Window Width:", 'window_width', 2),
            ("Window Height:", 'window_height', 3),
            ("Inactivity Timeout (s):", 'inactivity_timeout', 4),
            ("Corner Radius:", 'corner_radius', 5),
            ("Background Color:", 'bg_color', 6)
        ]

        for label, key, row in settings:
            ttk.Label(self.settings_window, text=label).grid(row=row, column=0, padx=5, pady=2, sticky=tk.W)
            entry = ttk.Entry(self.settings_window)
            entry.grid(row=row, column=1, padx=5, pady=2)
            entry.insert(0, str(self.config[key]))
            setattr(self, f"{key}_entry", entry)

            if key == 'bg_color':
                color_btn = ttk.Button(self.settings_window, text="Pick...", command=self.choose_color)
                color_btn.grid(row=row, column=2, padx=2, pady=2)

        save_btn = ttk.Button(self.settings_window, text="Save Settings", command=self.save_settings)
        save_btn.grid(row=7, column=0, columnspan=3, pady=5)

    def choose_color(self):
        color = colorchooser.askcolor(initialcolor=self.bg_color_entry.get())[1]
        if color:
            self.bg_color_entry.delete(0, tk.END)
            self.bg_color_entry.insert(0, color)

    def save_settings(self):
        try:
            new_config = {
                'serial_port': self.serial_port_entry.get(),
                'baud_rate': int(self.baud_rate_entry.get()),
                'window_width': int(self.window_width_entry.get()),
                'window_height': int(self.window_height_entry.get()),
                'inactivity_timeout': int(self.inactivity_timeout_entry.get()),
                'corner_radius': int(self.corner_radius_entry.get()),
                'bg_color': self.bg_color_entry.get()
            }

            if new_config['window_width'] < 100 or new_config['window_height'] < 100:
                raise ValueError("Window dimensions must be at least 100x100")
            if new_config['inactivity_timeout'] < 1:
                raise ValueError("Timeout must be at least 1 second")
            if new_config['corner_radius'] < 0:
                raise ValueError("Corner radius must be non-negative")

            self.config = new_config
            self.save_config()
            self.settings_window.destroy()

            if messagebox.askyesno("Restart Required", "Settings saved. Restart app now?"):
                self.on_close()
                restart_application()

        except ValueError as e:
            messagebox.showerror("Error", f"Invalid setting: {str(e)}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings: {str(e)}")

    def on_settings_close(self):
        self.settings_window.destroy()

    def handle_arduino_input(self, data):
        try:
            if data['type'] == 'selection':
                self.update_display(char=data['char'], mode=data['mode'])
            elif data['type'] == 'confirmed':
                pyautogui.write(data['char'])
                self.update_display(confirmed=data['char'])
            elif data['type'] == 'esc':
                pyautogui.press('esc')
                self.update_display(confirmed='ESC')
            elif data['type'] == 'backspace':
                pyautogui.press('backspace')
                self.update_display(confirmed='BACKSPACE')
            elif data['type'] == 'space':
                pyautogui.write(' ')
                self.update_display(confirmed='SPACE')
            elif data['type'] == 'enter':
                pyautogui.press('enter')
                self.update_display(confirmed='ENTER')
            elif data['type'] == 'mode_change':
                self.update_display(mode=data['mode'])
                self.update_status(f"Mode: {data['mode']}")
            elif data['type'] == 'error':
                self.update_status(data['message'])
        except Exception as e:
            self.update_status(f"Input error: {str(e)}")

    def update_display(self, char=None, mode=None, confirmed=None):
        if char is not None:
            self.char_display.config(text=char)
        if mode is not None:
            self.mode_display.config(text=mode)
        if confirmed is not None:
            self.confirmed_display.config(text=confirmed)

    def update_status(self, message):
        self.status_bar.config(text=message)

    def on_close(self):
        self.running = False
        self.root.destroy()


def main():
    root = tk.Tk()
    app = SerialMonitorApp(root)
    root.bind("<<SerialData>>", lambda e: app.process_serial_data())
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()


if __name__ == "__main__":
    main()