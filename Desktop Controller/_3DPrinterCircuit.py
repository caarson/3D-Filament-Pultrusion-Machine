import time
import sys
import serial
import re
import tkinter as tk
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

# Debounce events
fan_speed_changed = Event()
spool_speed_changed = Event()

BG_COLOR = "#2c2f33"
FG_COLOR = "#ffffff"
ACCENT_COLOR = "#7289da"

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
            time.sleep(2)
        except serial.SerialException as e:
            messagebox.showerror("Serial Error", str(e))
            sys.exit()

    def send_data_to_arduino(self, command):
        if self.arduino and self.arduino.is_open:
            try:
                self.arduino.write((command + '\r\n').encode('utf-8'))
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

    # Start a new thread for sending the command
    Thread(target=send_command_thread, daemon=True).start()

def update_fan_speed(value):
    fan_speed_changed.set()

def update_spool_motor_speed(value):
    spool_speed_changed.set()

def debounce_fan_speed():
    while not stop_threads:
        fan_speed_changed.wait()
        fan_speed_changed.clear()
        time.sleep(0.2)  # Debounce delay
        fan_speed = int(fan_speed_var.get())
        fan_speed_text.set(f"Fan Speed: {fan_speed}%")
        arduino_controller.send_data_to_arduino(f"SET_FAN_PWM:{fan_speed}")

def debounce_spool_speed():
    while not stop_threads:
        spool_speed_changed.wait()
        spool_speed_changed.clear()
        time.sleep(0.2)  # Debounce delay
        spool_speed = int(spool_motor_speed_var.get())
        spool_motor_speed_text.set(f"Spool Motor Speed: {spool_speed}%")
        arduino_controller.send_data_to_arduino(f"SET_WINDER_PWM:{spool_speed}")

def manual_fan_speed():
    update_fan_speed(fan_speed_var.get())

def manual_spool_speed():
    update_spool_motor_speed(spool_motor_speed_var.get())

def on_closing():
    global stop_threads
    stop_threads = True
    arduino_controller.close_connection()
    root.destroy()

# GUI Setup
def create_gui():
    root.title("Filament Machine Control Interface")
    root.geometry("800x600")
    root.configure(bg=BG_COLOR)

    ttk.Label(root, textvariable=temp_var, background=BG_COLOR, foreground=FG_COLOR, font=("Arial", 16)).place(relx=0.5, rely=0.1, anchor=tk.CENTER)
    Entry(root, textvariable=desired_temp_var, width=10).place(relx=0.5, rely=0.15, anchor=tk.CENTER)
    Button(root, text="Set Temperature", command=send_set_temperature).place(relx=0.5, rely=0.2, anchor=tk.CENTER)

    # Fan Speed Controls
    ttk.Label(root, textvariable=fan_speed_text, background=BG_COLOR, foreground=FG_COLOR, font=("Arial", 14)).place(relx=0.5, rely=0.3, anchor=tk.CENTER)
    ttk.Scale(root, from_=0, to=100, orient=tk.HORIZONTAL, variable=fan_speed_var, command=update_fan_speed, length=400).place(relx=0.5, rely=0.35, anchor=tk.CENTER)
    Entry(root, textvariable=fan_speed_var, width=10).place(relx=0.5, rely=0.4, anchor=tk.CENTER)
    Button(root, text="Set Fan Speed", command=manual_fan_speed).place(relx=0.5, rely=0.45, anchor=tk.CENTER)

    # Spool Motor Speed Controls
    ttk.Label(root, textvariable=spool_motor_speed_text, background=BG_COLOR, foreground=FG_COLOR, font=("Arial", 14)).place(relx=0.5, rely=0.55, anchor=tk.CENTER)
    ttk.Scale(root, from_=0, to=100, orient=tk.HORIZONTAL, variable=spool_motor_speed_var, command=update_spool_motor_speed, length=400).place(relx=0.5, rely=0.6, anchor=tk.CENTER)
    Entry(root, textvariable=spool_motor_speed_var, width=10).place(relx=0.5, rely=0.65, anchor=tk.CENTER)
    Button(root, text="Set Spool Speed", command=manual_spool_speed).place(relx=0.5, rely=0.7, anchor=tk.CENTER)

    ttk.Label(root, textvariable=ssr_state_var, background=BG_COLOR, foreground=FG_COLOR, font=("Arial", 16)).place(relx=0.5, rely=0.8, anchor=tk.CENTER)

    root.protocol("WM_DELETE_WINDOW", on_closing)

# Start GUI after COM Port Input
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
