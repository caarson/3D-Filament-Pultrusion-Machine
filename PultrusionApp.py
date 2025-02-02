import time
import os  # For file path handling
import sys
import serial
import re
import tkinter as tk
from tkinter import *
from tkinter import Label, Button, Entry, StringVar, ttk, messagebox, simpledialog
from threading import Thread, Event

# Global Variables
root = tk.Tk()
temperature_var = StringVar(root, value="25")
desired_temp_var = StringVar(root, value="100")
temp_var = StringVar(root, value="Temperature: --\nDesired Temperature: --")
fan_speed_var = tk.IntVar(root, value=50)
spool_motor_speed_var = tk.IntVar(root, value=50)
fan_speed_text = StringVar(root, value="Fan Speed: 50%")
spool_motor_speed_text = StringVar(root, value="Spool Motor Speed: 50%")
ssr_state_var = StringVar(root, value="SSR State: OFF")
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

BG_COLOR = "#2c2f33"
FG_COLOR = "#ffffff"
ACCENT_COLOR = "#7289da"

def donothing():  # test command
    pass

# Serial Communication
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

# Helper Functions
def handle_serial_data(data):
    try:
        # Example data format: "Current Temperature: 25.5 C | Set Temperature: 100 C | SSR State: ON"
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

def setup_menu():
    # Menu setup
    menubar = Menu(root)
    filemenu = Menu(menubar, tearoff=0)
    filemenu.add_command(label="New", command=donothing)
    filemenu.add_command(label="Open", command=donothing)
    filemenu.add_command(label="Save", command=donothing)
    filemenu.add_separator()
    filemenu.add_command(label="Exit", command=root.quit)
    menubar.add_cascade(label="File", menu=filemenu)

    helpmenu = Menu(menubar, tearoff=0)
    helpmenu.add_command(label="Set Timer", command=add_timer_controls)
    helpmenu.add_command(label="Strip Width", command=calculate_strip_width)
    helpmenu.add_command(label="Save Widths", command=show_saved_widths)
    helpmenu.add_command(label="About...", command=donothing)
    menubar.add_cascade(label="Help", menu=helpmenu)

    # Filament Presets
    filament_presets = {
        "PLA": {"temperature": 190, "fan_speed": 60, "spool_speed": 70},
        "ABS": {"temperature": 230, "fan_speed": 75, "spool_speed": 80},
        "PETG": {"temperature": 250, "fan_speed": 50, "spool_speed": 60},
        "Nylon": {"temperature": 260, "fan_speed": 70, "spool_speed": 65}
    }

    return filament_presets, menubar

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

                # Wait for acknowledgment without blocking the main thread
                start_time = time.time()
                while time.time() - start_time < 5:  # Wait up to 5 seconds for acknowledgment
                    response = arduino_controller.read_data_from_arduino()
                    if response and f"Set Temperature updated to {temp_value}" in response:
                        print(f"[DEBUG] Received acknowledgment: {response}")
                        last_set_temperature = None  # Reset to allow future updates
                        return
                    time.sleep(0.1)

                # If no acknowledgment, reset last_set_temperature to None
                print("[WARNING] No acknowledgment received from Arduino.")
                last_set_temperature = None

            else:
                print(f"[DEBUG] Desired temperature {temp_value}°C is already set. No command sent.")

        except ValueError:
            messagebox.showerror("Input Error", "Please enter a valid temperature.")

    Thread(target=send_command_thread, daemon=True).start()

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

def load_saved_widths():
    if os.path.exists(SAVE_FILE):
        with open(SAVE_FILE, "r") as file:
            for line in file:
                name, width = line.strip().split(" : ")
                saved_widths.append((name, float(width)))

def save_width_to_file(name, width):
    with open(SAVE_FILE, "a") as file:
        file.write(f"{name} : {width:.2f}\n")

def add_timer_controls():
    # This function can be used to add additional timer controls if needed
    pass  # Placeholder for future extensions

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
    
    ttk.Label(width_window, text="Enter Strip Name:", background=BG_COLOR, foreground=FG_COLOR).pack(pady=5)
    name_entry = ttk.Entry(width_window)
    name_entry.pack(pady=5)
    
    ttk.Label(width_window, text="Enter Inner Thickness (mm):", background=BG_COLOR, foreground=FG_COLOR).pack(pady=5)
    thickness_entry = ttk.Entry(width_window)
    thickness_entry.pack(pady=5)
    
    ttk.Button(width_window, text="Calculate", command=calculate).pack(pady=5)
    ttk.Button(width_window, text="Save", command=save_width).pack(pady=5)
    
    result_label = ttk.Label(width_window, text="", background=BG_COLOR, foreground=FG_COLOR)
    result_label.pack(pady=10)

def show_saved_widths():
    save_window = tk.Toplevel(root)
    save_window.title("Saved Widths")
    save_window.geometry("400x300")
    save_window.configure(bg=BG_COLOR)
    
    ttk.Label(save_window, text="Saved Widths:", background=BG_COLOR, foreground=FG_COLOR).pack(pady=10)
    listbox = tk.Listbox(save_window, bg=BG_COLOR, fg=FG_COLOR)
    listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    for name, width in saved_widths:
        listbox.insert(tk.END, f"{name}: {width:.2f} mm")

def debounce_fan_speed():
    while not stop_threads:
        fan_speed_changed.wait()
        fan_speed_changed.clear()
        time.sleep(0.2)  # Debounce delay
        slider_value = int(fan_speed_var.get())
        fan_speed_text.set(f"Fan Speed: {slider_value}%")
        # Map slider value (0 slowest, 100 fastest) to PWM value: 100 -> 1 (fastest), 0 -> 255 (slowest)
        pwm_value = int((100 - slider_value) / 100.0 * 254) + 1
        arduino_controller.send_data_to_arduino(f"SET_FAN_PWM:{pwm_value}")

def debounce_spool_speed():
    while not stop_threads:
        spool_speed_changed.wait()
        spool_speed_changed.clear()
        time.sleep(0.2)  # Debounce delay
        spool_speed = int(spool_motor_speed_var.get())
        spool_motor_speed_text.set(f"Spool Motor Speed: {spool_speed}%")
        # Map spool slider value (0 slowest, 100 fastest) to PWM value: 100 -> 1 (fastest), 0 -> 255 (slowest)
        winder_pwm = int((100 - spool_speed) / 100.0 * 254) + 1
        arduino_controller.send_data_to_arduino(f"SET_WINDER_PWM:{winder_pwm}")

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

def on_closing():
    global stop_threads
    stop_threads = True
    arduino_controller.close_connection()
    root.destroy()

def create_gui():
    root.title("Filament Machine Control Interface")
    root.geometry("800x700")
    root.configure(bg=BG_COLOR)

    filament_presets, menubar = setup_menu()
    root.config(menu=menubar)

    ttk.Label(root, textvariable=temp_var, background=BG_COLOR, foreground=FG_COLOR, font=("Arial", 16)).place(relx=0.5, rely=0.05, anchor=tk.CENTER)
    ttk.Entry(root, textvariable=desired_temp_var, width=10).place(relx=0.5, rely=0.1, anchor=tk.CENTER)
    ttk.Button(root, text="Set Temperature", command=send_set_temperature).place(relx=0.5, rely=0.15, anchor=tk.CENTER)

    # Fan Speed Controls
    ttk.Label(root, textvariable=fan_speed_text, background=BG_COLOR, foreground=FG_COLOR, font=("Arial", 14)).place(relx=0.5, rely=0.25, anchor=tk.CENTER)
    ttk.Scale(root, from_=0, to=100, orient=tk.HORIZONTAL, variable=fan_speed_var, command=update_fan_speed_display, length=400).place(relx=0.5, rely=0.3, anchor=tk.CENTER)
    ttk.Entry(root, textvariable=fan_speed_var, width=10).place(relx=0.5, rely=0.35, anchor=tk.CENTER)
    ttk.Button(root, text="Set Fan Speed", command=manual_fan_speed).place(relx=0.5, rely=0.4, anchor=tk.CENTER)

    # Spool Motor Speed Controls
    ttk.Label(root, textvariable=spool_motor_speed_text, background=BG_COLOR, foreground=FG_COLOR, font=("Arial", 14)).place(relx=0.5, rely=0.45, anchor=tk.CENTER)
    ttk.Scale(root, from_=0, to=100, orient=tk.HORIZONTAL, variable=spool_motor_speed_var, command=update_spool_motor_speed_display, length=400).place(relx=0.5, rely=0.5, anchor=tk.CENTER)
    ttk.Entry(root, textvariable=spool_motor_speed_var, width=10).place(relx=0.5, rely=0.55, anchor=tk.CENTER)
    ttk.Button(root, text="Set Spool Speed", command=manual_spool_speed).place(relx=0.5, rely=0.6, anchor=tk.CENTER)

    # SSR State Display
    ttk.Label(root, textvariable=ssr_state_var, background=BG_COLOR, foreground=FG_COLOR, font=("Arial", 16)).place(relx=0.5, rely=0.65, anchor=tk.CENTER)

    # Timer Components (Set Timer in Minutes)
    ttk.Label(root, text="Set Timer (minutes):", background=BG_COLOR, foreground=FG_COLOR, font=("Arial", 14)).place(relx=0.3, rely=0.75, anchor=tk.CENTER)
    global timer_entry
    timer_entry = ttk.Entry(root, width=10)
    timer_entry.place(relx=0.5, rely=0.75, anchor=tk.CENTER)
    ttk.Button(root, text="Start Timer", command=start_timer).place(relx=0.7, rely=0.75, anchor=tk.CENTER)

    global countdown_label
    countdown_label = ttk.Label(root, text="Time Remaining: 00:00", background=BG_COLOR, foreground=FG_COLOR, font=("Arial", 14))
    countdown_label.place(relx=0.5, rely=0.8, anchor=tk.CENTER)

    root.protocol("WM_DELETE_WINDOW", on_closing)

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

# Start GUI after COM Port Input
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
