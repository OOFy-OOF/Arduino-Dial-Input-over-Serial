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
from ctypes import wintypes
import sys
import subprocess

# ======================
# CONFIGURABLE SETTINGS
# ======================

# Serial communication
DEFAULT_CONFIG = {
    'serial_port': 'COM7',
    'baud_rate': 9600,
    'window_width': 150,
    'window_height': 175,
    'inactivity_timeout': 5,  # seconds
    'corner_radius': 10,
    'bg_color': '#d8d8d8'  # Default background color
}

# GUI settings
GUI_UPDATE_INTERVAL = 100  # milliseconds

# PyAutoGUI settings
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.1

# ======================
# HELPER FUNCTIONS
# ======================

def parse_serial_line(line):
    """Parse a line of serial input from Arduino"""
    patterns = {
        'selection': re.compile(r"Selected: \[(.)\] \| Mode: (.+)"),
        'confirmed': re.compile(r"Confirmed:\s*(.*)"),
        'esc': re.compile(r"ESC pressed"),
        'backspace': re.compile(r"Backspace"),
        'space': re.compile(r"Space inserted"),
        'mode_change': re.compile(r"Mode switched to:\s*(.+)")
    }
    
    for type_, pattern in patterns.items():
        match = pattern.search(line)
        if match:
            if type_ == 'selection':
                return {'type': type_, 'char': match.group(1), 'mode': match.group(2)}
            elif type_ == 'confirmed':
                return {'type': type_, 'char': match.group(1) or ' '}
            elif type_ == 'mode_change':
                return {'type': type_, 'mode': match.group(1)}
            else:
                return {'type': type_}
    
    return {'type': 'unknown', 'raw': line}

def restart_application():
    """Restart the current application"""
    python = sys.executable
    os.execl(python, python, *sys.argv)

# ======================
# MAIN APPLICATION CLASS
# ======================

class SerialMonitorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Keyboard Controller")
        
        # Initialize application state
        self.config = self.load_config()
        self.current_char = " "
        self.current_mode = "Unknown"
        self.confirmed_char = " "
        self.serial_queue = Queue()
        self.last_activity_time = time.time()
        self.sleeping = False
        self.serial_thread = None
        self.running = True
        self.connected = False  # Track connection status
        
        # Setup UI
        self.setup_fonts()
        self.create_widgets()
        self.setup_window()
        
        # Start operations
        self.start_serial_thread()
        self.root.after(GUI_UPDATE_INTERVAL, self.check_inactivity)
        self.root.after(100, self.check_initial_connection)  # Check initial connection

    def check_initial_connection(self):
        """Check if we have initial connection"""
        if not self.connected and not hasattr(self, 'connection_dialog'):
            self.show_connection_dialog("Initial connection failed. Please check your device and port settings, then click Restart.")

    def show_connection_dialog(self, message):
        """Show connection error dialog with restart button"""
        if hasattr(self, 'connection_dialog') and self.connection_dialog.winfo_exists():
            return
            
        self.connection_dialog = tk.Toplevel(self.root)
        self.connection_dialog.title("Connection Error")
        self.connection_dialog.attributes("-topmost", True)
        
        tk.Label(self.connection_dialog, text=message, wraplength=300).pack(padx=10, pady=10)
        
        def restart_app():
            self.connection_dialog.destroy()
            self.on_close()
            restart_application()
            
        tk.Button(self.connection_dialog, text="Restart", command=restart_app).pack(pady=5)
        self.connection_dialog.protocol("WM_DELETE_WINDOW", lambda: None)  # Prevent closing

    def get_text_color(self, bg_color):
        """Determine whether to use black or white text based on background color brightness"""
        if bg_color.startswith('#'):
            bg_color = bg_color[1:]
        
        # Convert hex to RGB components
        r = int(bg_color[0:2], 16)
        g = int(bg_color[2:4], 16)
        b = int(bg_color[4:6], 16)
        
        # Calculate brightness using the HSP color model
        brightness = (0.299 * r + 0.587 * g + 0.114 * b)
        
        # Use white text for dark backgrounds, black for light
        return "#000000" if brightness > 127 else "#ffffff"

    # ======================
    # CONFIGURATION METHODS
    # ======================

    def load_config(self):
        """Load configuration from file or create default"""
        config_path = "keyboard_config.json"
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    return json.load(f)
            except:
                return DEFAULT_CONFIG.copy()
        return DEFAULT_CONFIG.copy()

    def save_config(self):
        """Save current configuration to file"""
        with open("keyboard_config.json", 'w') as f:
            json.dump(self.config, f, indent=4)

    # ======================
    # SERIAL COMMUNICATION
    # ======================

    def start_serial_thread(self):
        """Start the serial communication thread"""
        self.serial_thread = threading.Thread(
            target=self.serial_loop,
            daemon=True
        )
        self.serial_thread.start()

    def serial_loop(self):
        """Main serial communication loop"""
        try:
            with serial.Serial(
                self.config['serial_port'], 
                self.config['baud_rate'], 
                timeout=1
            ) as ser:
                self.connected = True
                if hasattr(self, 'connection_dialog'):
                    self.connection_dialog.destroy()
                self.update_status(f"Connected to {self.config['serial_port']}")
                
                while self.running:
                    if ser.in_waiting > 0:
                        line = ser.readline().decode('utf-8', errors='ignore').strip()
                        if line:
                            data = parse_serial_line(line)
                            self.serial_queue.put(data)
                            self.root.event_generate("<<SerialData>>", when="tail")
                    
                    time.sleep(0.01)
                
        except serial.SerialException as e:
            self.connected = False
            self.serial_queue.put({'type': 'error', 'message': f"Serial error: {e}"})
            self.root.after(100, lambda: self.show_connection_dialog(
                f"Disconnected from {self.config['serial_port']}. Please check your connection and click Restart."
            ))
        except Exception as e:
            self.connected = False
            self.serial_queue.put({'type': 'error', 'message': f"Unexpected error: {e}"})
            self.root.after(100, lambda: self.show_connection_dialog(
                f"Unexpected error occurred: {str(e)}. Please click Restart."
            ))
        finally:
            self.update_status("Serial connection closed")

    def process_serial_data(self):
        """Process messages from the serial queue"""
        while not self.serial_queue.empty():
            data = self.serial_queue.get()
            
            if self.sleeping:
                self.wake_window()
                continue
            
            self.handle_arduino_input(data)
            self.last_activity_time = time.time()

    def restart_serial(self):
        """Restart serial connection with new settings"""
        self.running = False
        if self.serial_thread and self.serial_thread.is_alive():
            self.serial_thread.join(timeout=1)
        
        self.running = True
        self.start_serial_thread()
        self.update_status(f"Reconnected to {self.config['serial_port']}")

    # ======================
    # WINDOW MANAGEMENT
    # ======================

    def setup_window(self):
        """Configure window settings"""
        self.root.attributes("-topmost", True)
        self.root.attributes("-toolwindow", True)
        self.root.overrideredirect(True)
        self.root.geometry(f"{self.config['window_width']}x{self.config['window_height']}")
        self.enable_window_dragging()
        
        # Apply corner radius during window setup
        self.apply_corner_radius()

    def enable_window_dragging(self):
        """Enable dragging functionality for the window"""
        self.root.bind("<Button-1>", self.start_drag)
        self.root.bind("<B1-Motion>", self.perform_drag)

    def start_drag(self, event):
        """Record the starting position of the drag"""
        self.drag_start_x = event.x
        self.drag_start_y = event.y
        self.last_activity_time = time.time()

    def perform_drag(self, event):
        """Update the window position during the drag"""
        x = self.root.winfo_x() + (event.x - self.drag_start_x)
        y = self.root.winfo_y() + (event.y - self.drag_start_y)
        self.root.geometry(f"+{x}+{y}")
        self.last_activity_time = time.time()

    def apply_corner_radius(self):
        """Apply rounded corners to the window"""
        corner_radius = self.config.get('corner_radius', 20)
        width = self.config['window_width']
        height = self.config['window_height']

        hrgn = ctypes.windll.gdi32.CreateRoundRectRgn(
            0, 0, width, height, corner_radius * 2, corner_radius * 2
        )
        hwnd = self.root.winfo_id()  # Use root window handle directly
        ctypes.windll.user32.SetWindowRgn(hwnd, hrgn, True)

    def minimize_window(self):
        """Minimize the window"""
        self.root.withdraw()
        self.sleeping = True
        self.update_status("Sleeping...")

    def wake_window(self):
        """Restore the window"""
        if not self.sleeping:
            return
        
        self.root.deiconify()
        self.sleeping = False
        self.last_activity_time = time.time()
        self.update_status("Awake")
        self.root.after(200, lambda: self.update_status("Ready"))

    def check_inactivity(self):
        """Check for inactivity and minimize if needed"""
        if (time.time() - self.last_activity_time > self.config['inactivity_timeout'] and 
            not self.sleeping and 
            not getattr(self, 'settings_window', None)):
            self.minimize_window()
        self.root.after(GUI_UPDATE_INTERVAL, self.check_inactivity)

    # ======================
    # UI METHODS
    # ======================

    def setup_fonts(self):
        """Configure dynamic fonts"""
        self.big_font = font.Font(family='Arial', size=12, weight='bold')
        self.medium_font = font.Font(family='Arial', size=8)
        self.small_font = font.Font(family='Arial', size=7)

    def create_widgets(self):
        """Create and layout all GUI elements"""
        # Set background color from config
        bg_color = self.config.get('bg_color', '#444444')
        text_color = self.get_text_color(bg_color)
        
        self.root.configure(bg=bg_color)
        style = ttk.Style()
        style.configure("Dark.TFrame", background=bg_color)
        style.configure("Dark.TLabel", background=bg_color, foreground=text_color)
        style.configure("Dark.TButton", background=bg_color)

        # Main frame
        main_frame = ttk.Frame(self.root, padding="2", style="Dark.TFrame")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Close button
        close_btn = ttk.Button(main_frame, text="X", width=3, command=self.on_close, style="Dark.TButton")
        close_btn.pack(side=tk.TOP, anchor=tk.NE, padx=5, pady=5)

        # Character selection row
        char_frame = ttk.Frame(main_frame, style="Dark.TFrame")
        char_frame.pack()
        
        self.settings_btn = ttk.Button(char_frame, text="⚙", width=3, command=self.open_settings, style="Dark.TButton")
        self.settings_btn.pack(side=tk.LEFT, padx=(0, 5))

        ttk.Label(char_frame, text="Selected:", font=self.medium_font, background=bg_color, foreground=text_color).pack(side=tk.LEFT)
        self.char_display = ttk.Label(char_frame, text=" ", font=self.big_font, background=bg_color, foreground=text_color)
        self.char_display.pack(side=tk.LEFT, padx=5)

        # Mode display
        ttk.Label(main_frame, text="Mode:", font=self.medium_font, background=bg_color, foreground=text_color).pack()
        self.mode_display = ttk.Label(main_frame, text="Unknown", font=self.medium_font, background=bg_color, foreground=text_color)
        self.mode_display.pack(pady=1)

        # Confirmed character
        ttk.Label(main_frame, text="Last Sent:", font=self.medium_font, background=bg_color, foreground=text_color).pack()
        self.confirmed_display = ttk.Label(main_frame, text=" ", font=self.medium_font, background=bg_color, foreground=text_color)
        self.confirmed_display.pack(pady=1)

        # Status bar
        self.status_bar = ttk.Label(main_frame, text="Initializing...", relief=tk.SUNKEN, font=self.small_font, background=bg_color, foreground=text_color)
        self.status_bar.pack(fill=tk.X, pady=(2, 0))

        # Apply initial background color
        self.update_background_color()

    def open_settings(self):
        """Open the settings window"""
        if hasattr(self, 'settings_window') and self.settings_window.winfo_exists():
            self.settings_window.lift()
            return

        self.settings_window = tk.Toplevel(self.root)
        self.settings_window.title("Settings")
        self.settings_window.attributes("-topmost", True)
        self.settings_window.protocol("WM_DELETE_WINDOW", self.on_settings_close)

        # COM Port
        ttk.Label(self.settings_window, text="COM Port:").grid(row=0, column=0, padx=5, pady=2, sticky=tk.W)
        self.com_port_entry = ttk.Entry(self.settings_window)
        self.com_port_entry.grid(row=0, column=1, padx=5, pady=2)
        self.com_port_entry.insert(0, self.config['serial_port'])

        # Baud Rate
        ttk.Label(self.settings_window, text="Baud Rate:").grid(row=1, column=0, padx=5, pady=2, sticky=tk.W)
        self.baud_rate_entry = ttk.Entry(self.settings_window)
        self.baud_rate_entry.grid(row=1, column=1, padx=5, pady=2)
        self.baud_rate_entry.insert(0, str(self.config['baud_rate']))

        # Window Width
        ttk.Label(self.settings_window, text="Window Width:").grid(row=2, column=0, padx=5, pady=2, sticky=tk.W)
        self.width_entry = ttk.Entry(self.settings_window)
        self.width_entry.grid(row=2, column=1, padx=5, pady=2)
        self.width_entry.insert(0, str(self.config['window_width']))

        # Window Height
        ttk.Label(self.settings_window, text="Window Height:").grid(row=3, column=0, padx=5, pady=2, sticky=tk.W)
        self.height_entry = ttk.Entry(self.settings_window)
        self.height_entry.grid(row=3, column=1, padx=5, pady=2)
        self.height_entry.insert(0, str(self.config['window_height']))

        # Inactivity Timeout
        ttk.Label(self.settings_window, text="Inactivity Timeout (s):").grid(row=4, column=0, padx=5, pady=2, sticky=tk.W)
        self.timeout_entry = ttk.Entry(self.settings_window)
        self.timeout_entry.grid(row=4, column=1, padx=5, pady=2)
        self.timeout_entry.insert(0, str(self.config['inactivity_timeout']))

        # Corner Radius
        ttk.Label(self.settings_window, text="Corner Radius:").grid(row=5, column=0, padx=5, pady=2, sticky=tk.W)
        self.corner_radius_entry = ttk.Entry(self.settings_window)
        self.corner_radius_entry.grid(row=5, column=1, padx=5, pady=2)
        self.corner_radius_entry.insert(0, str(self.config.get('corner_radius', 20)))

        # Background Color
        ttk.Label(self.settings_window, text="Background Color:").grid(row=6, column=0, padx=5, pady=2, sticky=tk.W)
        self.bg_color_entry = ttk.Entry(self.settings_window)
        self.bg_color_entry.grid(row=6, column=1, padx=5, pady=2)
        self.bg_color_entry.insert(0, self.config.get('bg_color', '#444444'))

        def choose_color():
            color = colorchooser.askcolor(initialcolor=self.bg_color_entry.get())[1]
            if color:
                self.bg_color_entry.delete(0, tk.END)
                self.bg_color_entry.insert(0, color)

        color_btn = ttk.Button(self.settings_window, text="Pick...", command=choose_color)
        color_btn.grid(row=6, column=2, padx=2, pady=2)

        # Save Button
        save_btn = ttk.Button(self.settings_window, text="Save Settings", command=self.save_settings)
        save_btn.grid(row=7, column=0, columnspan=3, pady=5)

    def save_settings(self):
        """Save settings from the settings window"""
        try:
            new_config = {
                'serial_port': self.com_port_entry.get(),
                'baud_rate': int(self.baud_rate_entry.get()),
                'window_width': int(self.width_entry.get()),
                'window_height': int(self.height_entry.get()),
                'inactivity_timeout': int(self.timeout_entry.get()),
                'corner_radius': int(self.corner_radius_entry.get()),
                'bg_color': self.bg_color_entry.get()
            }
            
            if new_config['window_width'] < 100 or new_config['window_height'] < 100:
                raise ValueError("Window dimensions must be at least 100x100")
            if new_config['inactivity_timeout'] < 1:
                raise ValueError("Timeout must be at least 1 second")
            if new_config['corner_radius'] < 0:
                raise ValueError("Corner radius must be non-negative")
            
            old_color = self.config.get('bg_color', '#444444')
            new_color = new_config.get('bg_color', '#444444')
            
            self.config = new_config
            self.save_config()
            self.root.geometry(f"{self.config['window_width']}x{self.config['window_height']}")
            self.apply_corner_radius()
            self.update_background_color()
            
            # Check if color changed
            if old_color.lower() != new_color.lower():
                # Show restart dialog with restart button
                self.settings_window.destroy()
                result = messagebox.askyesno(
                    "Restart Required",
                    "Settings saved successfully.\nThe application needs to restart to apply color changes.\nRestart now?",
                    icon='question'
                )
                if result:
                    self.on_close()
                    restart_application()
            else:
                # No color change, just recreate widgets
                self.create_widgets()
                self.settings_window.destroy()
                messagebox.showinfo("Success", "Settings saved successfully")
            
        except ValueError as e:
            messagebox.showerror("Error", f"Invalid setting: {str(e)}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings: {str(e)}")

    # ======================
    # EVENT HANDLERS
    # ======================

    def handle_arduino_input(self, data):
        """Handle input from Arduino"""
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
            elif data['type'] == 'mode_change':
                self.update_display(mode=data['mode'])
                self.update_status(f"Mode: {data['mode']}")
            elif data['type'] == 'error':
                self.update_status(data['message'])
        except Exception as e:
            self.update_status(f"Input error: {str(e)}")

    def update_display(self, char=None, mode=None, confirmed=None):
        """Update the display elements"""
        if char is not None:
            self.current_char = char
            self.char_display.config(text=char)

        if mode is not None:
            self.current_mode = mode
            self.mode_display.config(text=mode)

        if confirmed is not None:
            self.confirmed_char = confirmed
            self.confirmed_display.config(text=confirmed)

    def update_status(self, message):
        """Update the status bar"""
        self.status_bar.config(text=message)

    def update_background_color(self):
        """Update the background color of the window and widgets"""
        color = self.config.get('bg_color', '#444444')
        text_color = self.get_text_color(color)
        
        self.root.configure(bg=color)
        style = ttk.Style()
        style.configure("Dark.TFrame", background=color)
        style.configure("Dark.TLabel", background=color, foreground=text_color)
        style.configure("Dark.TButton", background=color)
        
        # Update all label backgrounds if they exist
        if hasattr(self, 'char_display'):
            self.char_display.config(background=color, foreground=text_color)
        if hasattr(self, 'mode_display'):
            self.mode_display.config(background=color, foreground=text_color)
        if hasattr(self, 'confirmed_display'):
            self.confirmed_display.config(background=color, foreground=text_color)
        if hasattr(self, 'status_bar'):
            self.status_bar.config(background=color, foreground=text_color)

    def on_settings_close(self):
        """Handle settings window close"""
        self.settings_window.destroy()

    def on_close(self):
        """Clean up on window close"""
        self.running = False
        if self.serial_thread and self.serial_thread.is_alive():
            self.serial_thread.join(timeout=1)
        self.root.destroy()

# ======================
# MAIN ENTRY POINT
# ======================

def main():
    root = tk.Tk()
    app = SerialMonitorApp(root)
    root.bind("<<SerialData>>", lambda e: app.process_serial_data())
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()

if __name__ == "__main__":
    main()