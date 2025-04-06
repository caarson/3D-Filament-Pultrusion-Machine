import time
import os  # For file path handling
import sys
import serial
import re
import tkinter as tk
from tkinter import *
from tkinter import ttk, messagebox, simpledialog
from threading import Thread, Event

# -------------------------------------------------
# Global UI/Style Settings (Windows 11–inspired)
# -------------------------------------------------
BG_COLOR = "#f3f3f3"       # Light background
FG_COLOR = "#333333"       # Dark gray text
ACCENT_COLOR = "#0078D7"   # Microsoft blue accent
DEFAULT_FONT = ("Segoe UI", 12)
TITLE_FONT = ("Segoe UI", 16)

# -------------------------------------------------
# Global Variables
# -------------------------------------------------
root = tk.Tk()
temperature_var = tk.StringVar(root, value="25")
desired_temp_var = tk.StringVar(root, value="100")
temp_var = tk.StringVar(root, value="Temperature: 0.00°C\nDesired Temperature: 0°C")
fan_speed_var = tk.IntVar(root, value=50)
spool_motor_speed_var = tk.IntVar(root, value=50)
fan_speed_text = tk.StringVar(root, value="Fan Speed: 0%")
spool_motor_speed_text = tk.StringVar(root, value="Spool Motor Speed: 50%")
ssr_state_var = tk.StringVar(root, value="SSR State: OFF")
serial_buffer = ""
last_set_temperature = None
stop_threads = False

# Global List to Store Saved Widths
saved_widths = []
# Global Timer Variables
timer_running = False
remaining_time = 0  # Time in seconds for countdown

SAVE_FILE = "strip_widths.txt"  # File to store the saved widths

# Debounce events
fan_speed_changed = Event()
spool_speed_changed = Event()

# -------------------------------------------------
# Setup ttk Styles for a Modern Look
# -------------------------------------------------
def setup_styles():
    style = ttk.Style()
    style.theme_use('clam')
    # General widget styles
    style.configure("TLabel", background=BG_COLOR, foreground=FG_COLOR, font=DEFAULT_FONT, padding=5)
    style.configure("TButton", font=DEFAULT_FONT, padding=6)
    style.map("TButton",
              background=[('active', ACCENT_COLOR)],
              foreground=[('active', "#ffffff")])
    style.configure("TEntry", font=DEFAULT_FONT, padding=4)
    style.configure("Horizontal.TScale", background=BG_COLOR)
    style.configure("TFrame", background=BG_COLOR)

def donothing():
    pass

# -------------------------------------------------
# Serial Communication
# -------------------------------------------------
class ArduinoController:
    def __init__(self):
        self.arduino = None

    def setup_connection(self):
        com_port = simpledialog.askstring("COM Port", "Enter the COM port (e.g., COM3):")
        if not com_port:
            messagebox.showerror("Connection Error", "No COM port provided. Exiting.")
            sys.exit()

        try:
            self.arduino = serial.Serial(com_port, 9600, timeout=1)
            print(f"Connected to Arduino on {com_port} at 9600 baud")
            time.sleep(2)  # Wait for Arduino to initialize
        except serial.SerialException as e:
            messagebox.showerror("Serial Error", str(e))
            sys.exit()

    def send_data_to_arduino(self, command):
        if self.arduino and self.arduino.is_open:
            try:
                self.arduino.write((command + '\r\n').encode('utf-8'))
                print(f"Sent to Arduino: {command}")
            except Exception as e:
                print(f"Error sending data: {e}")

    def read_data_from_arduino(self):
        global serial_buffer
        try:
            while self.arduino.in_waiting > 0:
                serial_buffer += self.arduino.read().decode('utf-8', errors='ignore')
                if '\n' in serial_buffer:
                    line, serial_buffer = serial_buffer.split('\n', 1)
                    return line.strip()
        except Exception as e:
            print(f"Error reading data: {e}")
        return None

    def close_connection(self):
        if self.arduino:
            self.arduino.close()
            print("Closed serial connection.")

arduino_controller = ArduinoController()

# -------------------------------------------------
# Helper Functions
# -------------------------------------------------
def handle_serial_data(data):
    """
    Expected data format example:
    "Current Temperature: 25.5 C | Set Temperature: 100 C | SSR State: ON"
    """
    try:
        match = re.search(r"Current Temperature:\s*([\d.]+)\s*C.*Set Temperature:\s*([\d.]+)\s*C.*SSR State:\s*(\w+)", data)
        if match:
            current_temp = match.group(1)
            set_temp = match.group(2)
            ssr_state = match.group(3)
            temp_var.set(f"Temperature: {current_temp}°C\nDesired Temperature: {set_temp}°C")
            ssr_state_var.set(f"SSR State: {ssr_state}")
    except Exception as e:
        print(f"Error parsing data: {e}")

def read_serial_data():
    while not stop_threads:
        data = arduino_controller.read_data_from_arduino()
        if data:
            handle_serial_data(data)
        time.sleep(0.1)

def set_filament_preset(filament_type, filament_presets):
    if filament_type in filament_presets:
        preset = filament_presets[filament_type]
        desired_temp_var.set(str(preset["temperature"]))
        fan_speed_var.set(preset["fan_speed"])
        spool_motor_speed_var.set(preset["spool_speed"])
        send_set_temperature()
        manual_fan_speed()
        manual_spool_speed()
        print(f"Preset for {filament_type} loaded: {preset}")

def send_set_temperature():
    def send_command_thread():
        global last_set_temperature
        try:
            temp_value = int(desired_temp_var.get())
            # Allow temperature to be updated even if it's the same value
            if temp_value != last_set_temperature:
                print(f"[DEBUG] Sending SET_TEMP command with value: {temp_value}")
                arduino_controller.send_data_to_arduino(f"SET_TEMP:{temp_value}")
                last_set_temperature = temp_value

                # Wait for acknowledgment (up to 5 seconds)
                start_time = time.time()
                while time.time() - start_time < 5:
                    response = arduino_controller.read_data_from_arduino()
                    if response and f"Set Temperature updated to {temp_value}" in response:
                        print(f"[DEBUG] Received acknowledgment: {response}")
                        last_set_temperature = None  # Reset to allow future updates
                        return
                    time.sleep(0.1)

                print("[WARNING] No acknowledgment received from Arduino.")
                last_set_temperature = None
            else:
                print(f"[DEBUG] Desired temperature {temp_value}°C is already set. No command sent.")

        except ValueError:
            messagebox.showerror("Input Error", "Please enter a valid temperature.")

    Thread(target=send_command_thread, daemon=True).start()

def send_eject_command():
    # Sends the EJECT DEVICE command to the Arduino.
    print("[DEBUG] Sending EJECT DEVICE command.")
    arduino_controller.send_data_to_arduino("EJECT")
    messagebox.showinfo("Eject Device", "EJECT DEVICE command sent to Arduino.")

def update_fan_speed_display(value):
    fan_speed = int(float(value))
    fan_speed_text.set(f"Fan Speed: {fan_speed}%")
    fan_speed_var.set(fan_speed)
    fan_speed_changed.set()

def update_spool_motor_speed_display(value):
    spool_speed = int(float(value))
    spool_motor_speed_text.set(f"Spool Motor Speed: {spool_speed}%")
    spool_motor_speed_var.set(spool_speed)
    spool_speed_changed.set()

def manual_fan_speed():
    slider_value = int(fan_speed_var.get())
    fan_speed_text.set(f"Fan Speed: {slider_value}%")
    pwm_value = int((100 - slider_value) / 100.0 * 254) + 1
    arduino_controller.send_data_to_arduino(f"SET_FAN_PWM:{pwm_value}")

def manual_spool_speed():
    spool_speed = int(spool_motor_speed_var.get())
    spool_motor_speed_text.set(f"Spool Motor Speed: {spool_speed}%")
    winder_pwm = int((100 - spool_speed) / 100.0 * 254) + 1
    arduino_controller.send_data_to_arduino(f"SET_WINDER_PWM:{winder_pwm}")

def load_saved_widths():
    if os.path.exists(SAVE_FILE):
        with open(SAVE_FILE, "r") as file:
            for line in file:
                name, width = line.strip().split(" : ")
                saved_widths.append((name, float(width)))

def save_width_to_file(name, width):
    with open(SAVE_FILE, "a") as file:
        file.write(f"{name} : {width:.2f}\n")

def calculate_strip_width():
    def calculate():
        try:
            thickness = float(thickness_entry.get())
            name = name_entry.get().strip()
            if not name:
                result_label.config(text="Please enter a name for the strip.")
                return

            # Example formula for width estimation
            width = thickness * 2.5
            result_label.config(text=f"Estimated Width: {width:.2f} mm")
            return name, width
        except ValueError:
            result_label.config(text="Please enter a valid thickness.")

    def save_width():
        result = calculate()
        if result:
            name, width = result
            saved_widths.append((name, width))
            save_width_to_file(name, width)
            result_label.config(text=f"Saved: {name} - {width:.2f} mm")

    width_window = tk.Toplevel(root)
    width_window.title("Calculate Strip Width")
    width_window.geometry("400x350")
    width_window.configure(bg=BG_COLOR)

    ttk.Label(width_window, text="Enter Strip Name:").pack(pady=5)
    name_entry = ttk.Entry(width_window)
    name_entry.pack(pady=5)

    ttk.Label(width_window, text="Enter Inner Thickness (mm):").pack(pady=5)
    thickness_entry = ttk.Entry(width_window)
    thickness_entry.pack(pady=5)

    ttk.Button(width_window, text="Calculate", command=calculate).pack(pady=5)
    ttk.Button(width_window, text="Save", command=save_width).pack(pady=5)

    result_label = ttk.Label(width_window, text="")
    result_label.pack(pady=10)

def show_saved_widths():
    save_window = tk.Toplevel(root)
    save_window.title("Saved Widths")
    save_window.geometry("400x300")
    save_window.configure(bg=BG_COLOR)

    ttk.Label(save_window, text="Saved Widths:").pack(pady=10)
    listbox = tk.Listbox(save_window, bg=BG_COLOR, fg=FG_COLOR, bd=0, highlightthickness=0, font=DEFAULT_FONT)
    listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    for name, width in saved_widths:
        listbox.insert(tk.END, f"{name}: {width:.2f} mm")

def add_timer_controls():
    # Placeholder for adding additional timer controls if needed
    pass

def on_closing():
    global stop_threads
    stop_threads = True
    arduino_controller.close_connection()
    root.destroy()

def debounce_fan_speed():
    while not stop_threads:
        fan_speed_changed.wait()
        fan_speed_changed.clear()
        time.sleep(0.2)  # Debounce delay
        slider_value = int(fan_speed_var.get())
        fan_speed_text.set(f"Fan Speed: {slider_value}%")
        # Map slider value (0 slowest, 100 fastest) to PWM value
        pwm_value = int((100 - slider_value) / 100.0 * 254) + 1
        arduino_controller.send_data_to_arduino(f"SET_FAN_PWM:{pwm_value}")

def debounce_spool_speed():
    while not stop_threads:
        spool_speed_changed.wait()
        spool_speed_changed.clear()
        time.sleep(0.2)  # Debounce delay
        spool_speed = int(spool_motor_speed_var.get())
        spool_motor_speed_text.set(f"Spool Motor Speed: {spool_speed}%")
        # Map spool slider value (0 slowest, 100 fastest) to PWM value
        winder_pwm = int((100 - spool_speed) / 100.0 * 254) + 1
        arduino_controller.send_data_to_arduino(f"SET_WINDER_PWM:{winder_pwm}")

# -------------------------------------------------
# Timer Functions
# -------------------------------------------------
def send_shutoff_time(shutoff_seconds):
    try:
        # Use the new command string "SET_SHUTDOWN_TIME:" as expected by the Arduino code.
        command = f"SET_SHUTDOWN_TIME:{shutoff_seconds}"
        arduino_controller.send_data_to_arduino(command)
        print(f"Shutdown timer set for {shutoff_seconds} seconds.")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to set shutdown timer: {e}")

def start_timer():
    global timer_running, remaining_time
    if timer_running:
        messagebox.showinfo("Timer Running", "A timer is already running.")
        return

    try:
        minutes = int(timer_entry.get())
        if minutes <= 0:
            raise ValueError
        remaining_time = minutes * 60
        timer_running = True
        send_shutoff_time(remaining_time)  # Send shutdown time in seconds to Arduino
        update_countdown()
        messagebox.showinfo("Timer Set", f"Turning off after {minutes} minute(s).")
    except ValueError:
        messagebox.showerror("Input Error", "Please enter a valid time in minutes.")

def update_countdown():
    global timer_running, remaining_time

    if remaining_time > 0:
        mins, secs = divmod(remaining_time, 60)
        countdown_label.config(text=f"Time Remaining: {mins:02}:{secs:02}")
        remaining_time -= 1
        root.after(1000, update_countdown)
    else:
        timer_running = False
        countdown_label.config(text="Time Remaining: 00:00")
        turn_off_all()

def turn_off_all():
    desired_temp_var.set("0")
    fan_speed_var.set(0)
    spool_motor_speed_var.set(0)
    temp_var.set("Temperature: --\nDesired Temperature: 0°C")
    fan_speed_text.set("Fan Speed: 0%")
    spool_motor_speed_text.set("Spool Motor Speed: 0%")
    messagebox.showinfo("Timer Finished", "All systems have been turned off.")

# -------------------------------------------------
# Additional Requested Features
# -------------------------------------------------
def set_pp():
    """
    Sets the temperature to 160°C and fan speed to 10%,
    leaving spool speed unchanged.
    """
    desired_temp_var.set("160")
    fan_speed_var.set(10)
    # Send commands
    send_set_temperature()
    manual_fan_speed()

def show_about():
    """Displays the About dialog with version info."""
    messagebox.showinfo("About", "Version 1.3")

# -------------------------------------------------
# GUI Creation
# -------------------------------------------------
def create_gui():
    root.title("Filament Machine Control Interface")
    root.geometry("850x750")
    root.configure(bg=BG_COLOR)

    setup_styles()  # Apply modern styles to ttk widgets

    # ---------------------------
    # Menubar Setup
    # ---------------------------
    menubar = Menu(root, background=BG_COLOR, foreground=FG_COLOR, activebackground=ACCENT_COLOR)
    filemenu = Menu(menubar, tearoff=0)
    filemenu.add_command(label="New", command=donothing)
    filemenu.add_command(label="Open", command=donothing)
    filemenu.add_command(label="Save", command=donothing)
    filemenu.add_command(label="PP", command=set_pp)  # New "PP" option
    filemenu.add_separator()
    filemenu.add_command(label="Exit", command=root.quit)
    menubar.add_cascade(label="File", menu=filemenu)

    helpmenu = Menu(menubar, tearoff=0)
    helpmenu.add_command(label="Set Timer", command=add_timer_controls)
    helpmenu.add_command(label="Strip Width", command=calculate_strip_width)
    helpmenu.add_command(label="Save Widths", command=show_saved_widths)
    helpmenu.add_command(label="About...", command=show_about)  # Updated to show version
    menubar.add_cascade(label="Help", menu=helpmenu)
    root.config(menu=menubar)

    # ---------------------------
    # Top Frame: Temperature
    # ---------------------------
    top_frame = ttk.Frame(root, style="TFrame")
    top_frame.pack(pady=10, fill="x")

    # Temperature Display
    ttk.Label(top_frame, textvariable=temp_var, font=TITLE_FONT).pack(pady=5)

    # Temperature Controls (Entry & Buttons)
    temp_controls_frame = ttk.Frame(top_frame, style="TFrame")
    temp_controls_frame.pack(pady=5)
    ttk.Entry(temp_controls_frame, textvariable=desired_temp_var, width=10).pack(side="left", padx=5)
    ttk.Button(temp_controls_frame, text="Set Temperature", command=send_set_temperature).pack(side="left", padx=5)
    ttk.Button(temp_controls_frame, text="Eject Device", command=send_eject_command).pack(side="left", padx=5)

    # ---------------------------
    # Middle Frame: Fan & Spool
    # ---------------------------
    middle_frame = ttk.Frame(root, style="TFrame")
    middle_frame.pack(pady=10, fill="x")

    # Fan Speed Section
    fan_frame = ttk.Frame(middle_frame, style="TFrame")
    fan_frame.pack(pady=10, fill="x")

    ttk.Label(fan_frame, textvariable=fan_speed_text, font=DEFAULT_FONT).pack()
    ttk.Scale(fan_frame, from_=0, to=100, orient=tk.HORIZONTAL,
              variable=fan_speed_var, command=update_fan_speed_display,
              style="Horizontal.TScale", length=400).pack(pady=5)
    fan_controls_frame = ttk.Frame(fan_frame, style="TFrame")
    fan_controls_frame.pack()
    ttk.Entry(fan_controls_frame, textvariable=fan_speed_var, width=10).pack(side="left", padx=5)
    ttk.Button(fan_controls_frame, text="Set Fan Speed", command=manual_fan_speed).pack(side="left", padx=5)

    # Spool Motor Speed Section
    spool_frame = ttk.Frame(middle_frame, style="TFrame")
    spool_frame.pack(pady=10, fill="x")

    ttk.Label(spool_frame, textvariable=spool_motor_speed_text, font=DEFAULT_FONT).pack()
    ttk.Scale(spool_frame, from_=0, to=100, orient=tk.HORIZONTAL,
              variable=spool_motor_speed_var, command=update_spool_motor_speed_display,
              style="Horizontal.TScale", length=400).pack(pady=5)
    spool_controls_frame = ttk.Frame(spool_frame, style="TFrame")
    spool_controls_frame.pack()
    ttk.Entry(spool_controls_frame, textvariable=spool_motor_speed_var, width=10).pack(side="left", padx=5)
    ttk.Button(spool_controls_frame, text="Set Spool Speed", command=manual_spool_speed).pack(side="left", padx=5)

    # ---------------------------
    # Bottom Frame: SSR & Timer
    # ---------------------------
    bottom_frame = ttk.Frame(root, style="TFrame")
    bottom_frame.pack(pady=10, fill="x")

    # SSR State Display
    ttk.Label(bottom_frame, textvariable=ssr_state_var, font=TITLE_FONT).pack(pady=5)

    # Timer Controls
    timer_frame = ttk.Frame(bottom_frame, style="TFrame")
    timer_frame.pack(pady=5)
    ttk.Label(timer_frame, text="Set Timer (minutes):", font=DEFAULT_FONT).pack(side="left", padx=5)

    global timer_entry
    timer_entry = ttk.Entry(timer_frame, width=10)
    timer_entry.pack(side="left", padx=5)

    ttk.Button(timer_frame, text="Start Timer", command=start_timer).pack(side="left", padx=5)

    # Countdown Label
    global countdown_label
    countdown_label = ttk.Label(root, text="Time Remaining: 00:00", font=DEFAULT_FONT)
    countdown_label.pack(pady=10)

    # Window close event
    root.protocol("WM_DELETE_WINDOW", on_closing)

# -------------------------------------------------
# Main Execution
# -------------------------------------------------
load_saved_widths()
arduino_controller.setup_connection()
create_gui()

# Start serial reading thread
serial_thread = Thread(target=read_serial_data, daemon=True)
serial_thread.start()

# Start debounce threads
fan_thread = Thread(target=debounce_fan_speed, daemon=True)
fan_thread.start()

spool_thread = Thread(target=debounce_spool_speed, daemon=True)
spool_thread.start()

root.mainloop()
