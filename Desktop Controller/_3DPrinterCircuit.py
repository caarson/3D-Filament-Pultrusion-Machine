import time
import serial
import tkinter as tk
from tkinter import Label, Scale, Button, Toplevel, messagebox, Entry, StringVar, Frame, ttk, simpledialog
from PIL import Image, ImageTk
import os
from pathlib import Path

# Get the directory of the script
script_directory = Path(__file__).parent
print("Script directory:", script_directory)

# Assuming the images are in the same directory as the script
logo_image_path = script_directory / "LosAngelesTechnologiesLogo.png"
diagram_image_path = script_directory / "FilamentMaker.drawio (1).png"

# Define DEBUG_MODE
DEBUG_MODE = True  # Set to False in production

# Global variables for allowed voltage labels
allowed_voltage_labels = {}
logo_photo = None
diagram_photo = None
root_images = {}
logo_image_reference = None
diagram_image_reference = None
original_logo_image = Image.open(logo_image_path)
original_diagram_image = Image.open(diagram_image_path)
original_diagram_width, original_diagram_height = original_diagram_image.size

# Global variables for debounce mechanism
last_resize_time = 0
resize_delay = 500  # Delay in milliseconds

# Global dictionary to hold the labels for displaying allowed PWM duty cycles
allowed_percentage_labels = {}

# Global variables for percentage ranges - set these based on your specific requirements
spool_motor_percentage_range = (20, 100)
cutter_motor_percentage_range = (10, 90)
extra_plastics_motor_percentage_range = (15, 85)
plastics_cooling_motor_percentage_range = (25, 95)

# Default PWM duty cycles for each motor type, representing a standard operational point
default_pwm_settings = {
    'Spool Motor': 50,  # Nominal PWM percentage for normal operation
    'Cutter Motor': 30,
    'Extra Plastics Motor': 40,
    'Plastics Cooling': 35
}

# Global variables for scales and labels
motor_max_temp_scale = None
fan_max_temp_scale = None
motor_voltage_label = None
fan_voltage_label = None
spool_motor_voltage_label = None
cutter_motor_voltage_label = None
extra_plastics_motor_voltage_label = None
plastics_cooling_motor_voltage_label = None

# Global variables for percentage entry StringVars
spool_motor_min_percentage_var = None
spool_motor_max_percentage_var = None
cutter_motor_min_percentage_var = None
cutter_motor_max_percentage_var = None
extra_plastics_motor_min_percentage_var = None
extra_plastics_motor_max_percentage_var = None
plastics_cooling_motor_min_percentage_var = None
plastics_cooling_motor_max_percentage_var = None

# Global variables for Entry widgets
spool_motor_min_voltage_entry = None
spool_motor_max_voltage_entry = None
cutter_motor_min_voltage_entry = None
cutter_motor_max_voltage_entry = None
extra_plastics_motor_min_voltage_entry = None
extra_plastics_motor_max_voltage_entry = None
plastics_cooling_motor_min_voltage_entry = None
plastics_cooling_motor_max_voltage_entry = None

# Global variables for voltage ranges - set these based on your specific requirements
spool_motor_voltage_range = (7.68, 15.36)
cutter_motor_voltage_range = (5, 10)
extra_plastics_motor_voltage_range = (6, 12)
plastics_cooling_motor_voltage_range = (4, 8)

# Global variables for scales and labels
motor_max_temp_scale = None
fan_max_temp_scale = None
motor_voltage_label = None
fan_voltage_label = None
spool_motor_voltage_label = None
cutter_motor_voltage_label = None
extra_plastics_motor_voltage_label = None
plastics_cooling_motor_voltage_label = None

# Global variables for interval labels
spool_motor_interval_label = None
cutter_motor_interval_label = None
extra_plastics_motor_interval_label = None
plastics_cooling_motor_interval_label = None

# Global variable for settings window
global settings_window
settings_window = None  # Initialize to None

# Global variables to store the delayed resize task and last window size
resize_task = None
last_window_size = (0, 0)

####################################################

# Simulate a serial connection (for debug mode)
class FakeSerial:
    def write(self, command):
        print(f"Sending command to Arduino (simulated): {command.decode().strip()}")

    def readline(self):
        # Simulate receiving a response from Arduino, modify as necessary
        return b"Simulated response from Arduino\n"

    def close(self):
        print("Closing fake serial connection (simulated)")

    def in_waiting(self):
        # Simulate data waiting to be read
        return 0
    
class ArduinoController:
    def __init__(self, serial_port='COM_PORT', baud_rate=9600):
        self.port = serial_port
        self.baud_rate = baud_rate
        self.arduino = self.connect_to_arduino()

    def connect_to_arduino(self):
        if DEBUG_MODE:
            print(f"Debug mode: Simulating connection to {self.port} at {self.baud_rate} baud")
            return FakeSerial()
        else:
            try:
                arduino = serial.Serial(self.port, self.baud_rate, timeout=1)
                print(f"Connected to Arduino on {self.port} at {self.baud_rate} baud")
                return arduino
            except serial.SerialException as e:
                messagebox.showerror("Connection Error", f"Could not connect to {self.port}: {e}")
                return None

    def send_data_to_arduino(self, command):
        if self.arduino:
            try:
                self.arduino.write((command + '\n').encode('utf-8'))
                print(f"Command sent: {command}")
                
                if self.arduino.in_waiting > 0:
                    response = self.arduino.readline().decode('utf-8').strip()
                    print(f"Arduino response: {response}")
                    return response
                else:
                    print("No response received from Arduino.")
                    return None
            except serial.SerialException as e:
                print(f"Serial communication error: {e}")
                self.arduino.close()
                self.arduino = None
                self.arduino = self.connect_to_arduino()
            except Exception as e:
                print(f"Error sending data to Arduino: {e}")
                self.arduino.close()
                self.arduino = None
        else:
            print("Arduino connection not established.")
            self.arduino = self.connect_to_arduino()

    def fan_on(self):
        self.send_data_to_arduino("FAN_ON")

    def fan_off(self):
        self.send_data_to_arduino("FAN_OFF")

    def set_fan_pwm(self, pwm_value):
        self.send_data_to_arduino(f"SET_FAN_PWM:{pwm_value}")

    def winder_on(self):
        self.send_data_to_arduino("WINDER_ON")

    def winder_off(self):
        self.send_data_to_arduino("WINDER_OFF")

    def set_winder_pwm(self, pwm_value):
        self.send_data_to_arduino(f"SET_WINDER_PWM:{pwm_value}")

    def close_connection(self):
        if self.arduino:
            self.arduino.close()
            print("Closed serial connection.")


####################################################

def update_temperature_label(event=None):
    # Update the temperature label with the value from the entry
    new_temperature = temperature_var.get()  # Get the current value from the entry
    temp_var.set(f"Temperature: {new_temperature}°C")  # Update the label

def create_string_vars():
    global spool_motor_min_percentage_var, spool_motor_max_percentage_var
    global cutter_motor_min_percentage_var, cutter_motor_max_percentage_var
    global extra_plastics_motor_min_percentage_var, extra_plastics_motor_max_percentage_var
    global plastics_cooling_motor_min_percentage_var, plastics_cooling_motor_max_percentage_var

    spool_motor_min_percentage_var = tk.StringVar(value="20")  # Default min percentage
    spool_motor_max_percentage_var = tk.StringVar(value="100")  # Default max percentage
    cutter_motor_min_percentage_var = tk.StringVar(value="10")
    cutter_motor_max_percentage_var = tk.StringVar(value="90")
    extra_plastics_motor_min_percentage_var = tk.StringVar(value="15")
    extra_plastics_motor_max_percentage_var = tk.StringVar(value="85")
    plastics_cooling_motor_min_percentage_var = tk.StringVar(value="25")
    plastics_cooling_motor_max_percentage_var = tk.StringVar(value="95")

def update_voltage_wrapper(*args):
    # Use a global variable or another method to reference your settings_window
    global settings_window
    update_voltage_range_labels_and_vars(settings_window)

# Function to create labels for voltage range intervals
def create_voltage_range_interval_labels(settings_window):
    global spool_motor_interval_label, cutter_motor_interval_label
    global extra_plastics_motor_interval_label, plastics_cooling_motor_interval_label

    # Ensure that the labels are instantiated with StringVar bindings
    spool_motor_interval_label = Label(settings_window, textvariable=spool_motor_min_voltage_var)
    cutter_motor_interval_label = Label(settings_window, textvariable=cutter_motor_min_voltage_var)
    extra_plastics_motor_interval_label = Label(settings_window, textvariable=extra_plastics_motor_min_voltage_var)
    plastics_cooling_motor_interval_label = Label(settings_window, textvariable=plastics_cooling_motor_min_voltage_var)


    # Update these lines to set the maximum voltage to 12V
    spool_motor_max_voltage_var.set("12.00")
    cutter_motor_max_voltage_var.set("12.00")
    extra_plastics_motor_max_voltage_var.set("12.00")
    plastics_cooling_motor_max_voltage_var.set("12.00")

#    # Set maximum voltage to 12V
    max_voltage = 12.00

    # Create interval labels with max voltage of 12V
    spool_motor_interval_label.config(text=f"Allowed Voltage: 0 - {max_voltage} V")
    cutter_motor_interval_label.config(text=f"Allowed Voltage: 0 - {max_voltage} V")
    extra_plastics_motor_interval_label.config(text=f"Allowed Voltage: 0 - {max_voltage} V")
    plastics_cooling_motor_interval_label.config(text=f"Allowed Voltage: 0 - {max_voltage} V")

    # Update the StringVars for the max voltage
    spool_motor_max_voltage_var.set(f"{max_voltage}")
    cutter_motor_max_voltage_var.set(f"{max_voltage}")
    extra_plastics_motor_max_voltage_var.set(f"{max_voltage}")
    plastics_cooling_motor_max_voltage_var.set(f"{max_voltage}")

def update_voltage_range_labels_and_vars(settings_window):
    try:
        print("Updating voltage ranges...")
        min_voltage = calculate_min_voltage(overall_speed_var.get())
        max_voltage = calculate_max_voltage(overall_speed_var.get())

        global voltage_range_text

        # Now we set the complete voltage range text in the StringVars
        voltage_range_text = f"Allowed Voltage: {min_voltage:.2f} - {max_voltage:.2f} V"
        print(f"Setting voltage range to: {voltage_range_text}")  # Print the new voltage range

        spool_motor_min_voltage_var.set(voltage_range_text)
        cutter_motor_min_voltage_var.set(voltage_range_text)
        extra_plastics_motor_min_voltage_var.set(voltage_range_text)
        plastics_cooling_motor_min_voltage_var.set(voltage_range_text)

        

        # Since we are using textvariable in the labels, we don't need to manually update them anymore.
        # However, if the GUI is not refreshing, we can force it to refresh:
        settings_window.update_idletasks()  # Processes pending tasks such as updates
        settings_window.update()  # Force a complete refresh (use cautiously)

    except Exception as e:
        print(f"Error updating voltage ranges: {e}")

def calculate_percentage(item, speed_percent, overall_speed_percent):
    # Simplified to use the speed percent directly as an example
    return speed_percent

# Predictions for intervals for each motor
# Assuming the overall speed is set as a percentage of the maximum
# and the motors' performance scales linearly with voltage
def calculate_intervals_based_on_diagram():
    # Assuming that speed_percent ranges from 0 to 100
    speed_percent = overall_speed_var.get()

    # Prediction logic based on the diagram provided
    # These will need to be adjusted based on actual motor performance and requirements
    spool_interval = (speed_percent * 0.07, speed_percent * 0.12)
    cutter_interval = (speed_percent * 0.05, speed_percent * 0.1)
    extra_plastics_interval = (speed_percent * 0.04, speed_percent * 0.08)
    plastics_cooling_interval = (speed_percent * 0.06, speed_percent * 0.11)

    # Update the global variables for voltage ranges with the predicted intervals
    spool_motor_voltage_range = spool_interval
    cutter_motor_voltage_range = cutter_interval
    extra_plastics_motor_voltage_range = extra_plastics_interval
    plastics_cooling_motor_voltage_range = plastics_cooling_interval

# Function to update voltage output label
def update_voltage_output(scale, label):
    speed_percent = scale.get()
    # Calculate voltage output based on speed percent and some logic
    voltage_output = calculate_voltage_output(speed_percent)  # Implement this function
    label.config(text=f"Voltage Output: {voltage_output} V")

# Function to dynamically update PWM duty cycle settings based on operational conditions
def update_motor_settings(*args):
    overall_speed_percent = overall_speed_var.get()  # Get current overall speed as a percentage

    # Calculate the new PWM duty cycles based on the overall speed
    for motor_name, nominal_duty in default_pwm_settings.items():
        # Example: Adjust the PWM duty by a factor derived from overall speed
        # Here we scale the nominal duty cycle linearly with the overall speed
        adjusted_pwm = nominal_duty * (overall_speed_percent / 100)  # Adjust duty cycle based on speed

        # Update the GUI to show the allowed PWM duty cycle for each motor
        allowed_percentage_labels[motor_name].config(text=f"Recommended Percent: {adjusted_pwm:.2f}%")

# Helper function to create motor controls and initialize labels for PWM display
def create_motor_controls(motor_name, frame):
    global spool_motor_percentage_label, spool_motor_min_percentage_var, spool_motor_max_percentage_var
    global cutter_motor_percentage_label, cutter_motor_min_percentage_var, cutter_motor_max_percentage_var
    global extra_plastics_motor_percentage_label, extra_plastics_motor_min_percentage_var, extra_plastics_motor_max_percentage_var
    global plastics_cooling_motor_percentage_label, plastics_cooling_motor_min_percentage_var, plastics_cooling_motor_max_percentage_var
    global allowed_percentage_labels

    # Create the variable for the entry before using it
    min_percentage_var = StringVar(value="0")
    max_percentage_var = StringVar(value="100")

    # Label for the motor speed scale
    scale_label = Label(frame, text=f"{motor_name} Speed (%)", bg="#333", fg="white")
    scale_label.grid(row=0, column=0, padx=10, pady=5, sticky='w')

    # Motor speed scale
    scale = Scale(frame, from_=0, to=100, orient='horizontal', bg="#ddd")
    scale.grid(row=0, column=1, padx=10, pady=5, sticky='ew')

    # Percentage output label
    percentage_output_label = Label(frame, text="Recommended Percent: -- %", bg="#333", fg="white")
    percentage_output_label.grid(row=1, column=0, columnspan=4, padx=10, pady=5, sticky='w')

    # Store the label in the dictionary for later access
    allowed_percentage_labels[motor_name] = percentage_output_label

    # Min and Max Percentage Entry
    min_percentage_entry = Entry(frame, textvariable=min_percentage_var, width=6)
    min_percentage_entry.grid(row=1, column=1, padx=(30, 0), pady=5, sticky='W')
    max_percentage_entry = Entry(frame, textvariable=max_percentage_var, width=6)
    max_percentage_entry.grid(row=1, column=2, padx=(5, 20), pady=5, sticky='W')

    # Update the percentage range globals when entries change
    min_percentage_var.trace_add("write", lambda *args: on_percentage_change(min_percentage_var, max_percentage_var, percentage_output_label))
    max_percentage_var.trace_add("write", lambda *args: on_percentage_change(min_percentage_var, max_percentage_var, percentage_output_label))

    return scale, percentage_output_label

def initialize_motor_controls():
    global settings_window
    if not settings_window:
        settings_window = Toplevel(root, bg="#333")
        settings_window.title("Motor Settings Initialization")

    spool_frame = ttk.Frame(settings_window, padding="3 3 12 12")
    spool_frame.grid(row=0, column=0)
    create_motor_controls("Spool Motor", spool_frame)

    cutter_frame = ttk.Frame(settings_window, padding="3 3 12 12")
    cutter_frame.grid(row=1, column=0)
    create_motor_controls("Cutter Motor", cutter_frame)

    extra_plastics_frame = ttk.Frame(settings_window, padding="3 3 12 12")
    extra_plastics_frame.grid(row=2, column=0)
    create_motor_controls("Extra Plastics Motor", extra_plastics_frame)

    plastics_cooling_frame = ttk.Frame(settings_window, padding="3 3 12 12")
    plastics_cooling_frame.grid(row=3, column=0)
    create_motor_controls("Plastics Cooling", plastics_cooling_frame)

    # Optionally, hide this window or use it for debugging
    settings_window.withdraw()  # Hide the window after initialization


def on_percentage_change(min_var, max_var, label):
    try:
        min_percentage = float(min_var.get())
        max_percentage = float(max_var.get())
        label.config(text=f"Recommended Percent: {min_percentage} - {max_percentage}%")
    except ValueError:
        messagebox.showerror("Input Error", "Please enter valid numbers for percentage ranges.")

def setup_com_port():
    if DEBUG_MODE:
        print("Debug mode: Using default debug port and baud rate.")
        return "COM_DEBUG", 9600  # Debug COM port and baud rate
    else:
        # Ask for the COM port
        com_port = simpledialog.askstring("COM Port", "Enter the COM port (e.g., COM3):", parent=root)
        if not com_port:
            messagebox.showerror("No COM Port", "No COM port provided. Exiting.")
            root.destroy()
            exit()

        # Ask for the baud rate
        baud_rate = simpledialog.askinteger("Baud Rate", "Enter the baud rate (e.g., 9600):", parent=root)
        if not baud_rate:
            messagebox.showerror("No Baud Rate", "No baud rate provided. Exiting.")
            root.destroy()
            exit()

        return com_port, baud_rate

def open_algorithm_settings():
    global spool_frame, cooling_frame, settings_window

    # Create the settings window
    settings_window = Toplevel(root, bg="#333")
    settings_window.title("Algorithm Settings")

    # Explanation label
    explanation_label = Label(settings_window, text="Adjust settings for motor speeds and voltage ranges.", bg="#333", fg="white")
    explanation_label.grid(row=0, column=0, columnspan=2, padx=10, pady=10)

    # Create frames for spool and cooling motor controls
    spool_frame = ttk.Frame(settings_window, padding="3 3 12 12")
    cooling_frame = ttk.Frame(settings_window, padding="3 3 12 12")

    # Position the frames
    spool_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
    cooling_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

    # Create controls within each frame
    create_motor_controls("Spool Motor", spool_frame)
    create_motor_controls("Plastics Cooling", cooling_frame)

    # Apply settings button
    apply_button = Button(settings_window, text="Apply Settings", command=apply_settings,
                          bg="#5cb85c", fg="white", relief='flat')
    apply_button.grid(row=3, column=0, columnspan=2, padx=10, pady=10, sticky='ew')

    settings_window.resizable(True, True)

def on_closing():
    if DEBUG_MODE:
        print("Closing the application (Debug Mode).")
    else:
        if arduino:
            arduino.close()
            print("Closed serial connection.")
    root.destroy()

# Functions to calculate the min and max voltage
def calculate_min_voltage(overall_speed):
    # Implement your logic to calculate the minimum voltage based on overall speed
    return overall_speed * 0.09  # Example calculation

def calculate_max_voltage(overall_speed):
    # Implement your logic to calculate the maximum voltage based on overall speed
    return overall_speed * 0.15  # Example calculation

# Function to update the GUI with data from the Arduino or simulated data
def update_gui():
    if DEBUG_MODE:
        # Current simulated temperature for debugging
        current_temp = 200  # Example current temperature in degrees Celsius
        target_temp = int(temperature_var.get())  # Get the target temperature from the entry

        # Determine the direction of the arrow
        if current_temp < target_temp:
            arrow = "↑"  # Temperature needs to increase
        elif current_temp > target_temp:
            arrow = "↓"  # Temperature needs to decrease
        else:
            arrow = "—"  # Temperature is at target

        # Update the temperature variable to include the arrow and target
        temp_var.set(f"Temperature: {current_temp}°C {arrow} Target: {target_temp}°C (Debug)")
    else:
        # Actual serial communication code would go here for non-debug mode
        pass

    # Reschedule the update
    root.after(1000, update_gui)


# Function to update motor voltage labels
def update_motor_voltages():
    overall_speed_percent = overall_speed_var.get() / 100.0  # Convert to a fraction

    # Call the adjust_voltage_ranges function to update the labels
    adjust_voltage_ranges()

    # Check if labels are initialized before updating them
    if spool_motor_voltage_label is not None:
        spool_motor_voltage_label.config(text=f"{calculate_voltage('Spool Motor', spool_motor_scale.get(), overall_speed_percent):.2f} V")
    if cutter_motor_voltage_label is not None:
        cutter_motor_voltage_label.config(text=f"{calculate_voltage('Cutter Motor', cutter_motor_scale.get(), overall_speed_percent):.2f} V")
    if extra_plastics_motor_voltage_label is not None:
        extra_plastics_motor_voltage_label.config(text=f"{calculate_voltage('Extra Plastics Motor', extra_plastics_motor_scale.get(), overall_speed_percent):.2f} V")
    if plastics_cooling_motor_voltage_label is not None:
        plastics_cooling_motor_voltage_label.config(text=f"{calculate_voltage('Plastics Cooling', plastics_cooling_motor_scale.get(), overall_speed_percent):.2f} V")

def update_scales_max():
    global spool_motor_scale, cutter_motor_scale
    global extra_plastics_motor_scale, plastics_cooling_motor_scale

    # Ensure the speed scales have been created
    if (spool_motor_scale is not None and cutter_motor_scale is not None and 
        extra_plastics_motor_scale is not None and plastics_cooling_motor_scale is not None):
        overall_speed_percent = overall_speed_var.get()

        # Disable sliders and set to zero if overall speed is zero
        if overall_speed_percent == 0:
            for scale in [spool_motor_scale, cutter_motor_scale, extra_plastics_motor_scale, plastics_cooling_motor_scale]:
                scale.set(0)
                scale.config(state='disabled')
        else:
            for scale in [spool_motor_scale, cutter_motor_scale, extra_plastics_motor_scale, plastics_cooling_motor_scale]:
                scale.config(state='normal')

        # Update the motor voltage labels based on the overall speed
        update_motor_voltages()

def apply_settings():
    # Update the global voltage ranges
    update_voltage_ranges()

    # Print the current voltage ranges to the console
    print("Settings applied with the following voltage ranges:")
    print(f"Spool Motor Voltage Range: {spool_motor_voltage_range}")
    print(f"Cutter Motor Voltage Range: {cutter_motor_voltage_range}")
    print(f"Extra Plastics Motor Voltage Range: {extra_plastics_motor_voltage_range}")
    print(f"Plastics Cooling Motor Voltage Range: {plastics_cooling_motor_voltage_range}")

# Function to update the percentage ranges based on user input
def update_percentage_ranges(*args):
    global spool_motor_percentage_range, cutter_motor_percentage_range
    global extra_plastics_motor_percentage_range, plastics_cooling_motor_percentage_range

    # Update the percentage range for each motor
    spool_motor_percentage_range = (float(spool_motor_min_percentage_entry.get()), float(spool_motor_max_percentage_entry.get()))
    cutter_motor_percentage_range = (float(cutter_motor_min_percentage_entry.get()), float(cutter_motor_max_percentage_entry.get()))
    extra_plastics_motor_percentage_range = (float(extra_plastics_motor_min_percentage_entry.get()), float(extra_plastics_motor_max_percentage_entry.get()))
    plastics_cooling_motor_percentage_range = (float(plastics_cooling_motor_min_percentage_entry.get()), float(plastics_cooling_motor_max_percentage_entry.get()))

# Function to calculate voltage based on speed percentage and overall speed
def calculate_voltage(item, speed_percent, overall_speed_percent):
    # Base voltage remains the same
    base_voltage = 12

    # Define dynamic voltage ranges for different motors based on overall speed percent
    if item == "Spool Motor":
        min_voltage = base_voltage * (overall_speed_percent / 100) * 0.5
        max_increment = 0.25
    elif item == "Cutter Motor":
        min_voltage = base_voltage * (overall_speed_percent / 100) * 0.6
        max_increment = 0.20
    elif item == "Extra Plastics Motor":
        min_voltage = base_voltage * (overall_speed_percent / 100) * 0.4
        max_increment = 0.30
    elif item == "Plastics Cooling":
        min_voltage = base_voltage * (overall_speed_percent / 100) * 0.7
        max_increment = 0.15
    else:
        min_voltage = 0
        max_increment = 0

    # Calculate maximum voltage based on the increment
    max_voltage = min_voltage + (base_voltage * max_increment)

    # Ensure max voltage does not exceed base voltage
    max_voltage = min(max_voltage, base_voltage)

    # Calculate the actual voltage within this dynamic range
    voltage = min_voltage + (max_voltage - min_voltage) * (speed_percent / 100)
    return voltage

# Function to update voltage displays
def update_voltage_displays():
    # Check if the labels have been created before updating them
    if motor_voltage_label is not None and fan_voltage_label is not None:

        motor_voltage = calculate_voltage("Spool Motor", motor_max_temp_scale.get())  # Use the actual motor name
        fan_voltage = calculate_voltage("Fans", fan_max_temp_scale.get())  # Use the actual fan name
        motor_voltage_label.config(text=f"Motor Voltage: {motor_voltage:.2f}V")
        fan_voltage_label.config(text=f"Fan Voltage: {fan_voltage:.2f}V")

# Function to handle image resizing
def resize_image(event=None):
    global diagram_photo, last_resize_time, resize_delay

    current_time = int(time.time() * 1000)
    if (current_time - last_resize_time) < resize_delay:
        root.after(resize_delay - (current_time - last_resize_time), resize_image, event)
        return

    last_resize_time = current_time

    # Get the current size of the main_frame
    new_width = main_frame.winfo_width()
    new_height = main_frame.winfo_height() - 100  # Reserve space for other elements

    # Ensure that we have positive dimensions to avoid ValueError
    if new_width > 0 and new_height > 0:
        aspect_ratio = original_diagram_width / original_diagram_height
        # Calculate the best fit size maintaining the aspect ratio
        if new_width / new_height > aspect_ratio:
            # Window is wider than the image's aspect ratio, so fit to height
            new_width = int(new_height * aspect_ratio)
        else:
            # Window is narrower than the image's aspect ratio, so fit to width
            new_height = int(new_width / aspect_ratio)

        # Resize and update the diagram image
        resized_diagram_image = original_diagram_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        diagram_photo = ImageTk.PhotoImage(resized_diagram_image)
        
        # Update the label with the new image
        diagram_label.config(image=diagram_photo)
        diagram_label.image = diagram_photo  # Keep a reference
    else:
        # If dimensions are not positive, schedule another attempt after some time
        root.after(100, resize_image)

#####################################################

if __name__ == "__main__":
    root = tk.Tk()
    root.title("Los Angeles Technologies - Filament Maker Control Interface")
    root.configure(bg="#333")
    root.minsize(100, 100)  # Set a minimum size for the window

    # Initialize Arduino Controller
    arduino_controller = ArduinoController('COM3', 9600)  # Adjust COM port and baud rate as needed

    # Initialize motor controls at the beginning of the program
    initialize_motor_controls()

    # Create frames for each set of controls with settings_window as their parent
    spool_frame = ttk.Frame(settings_window, padding="3 3 12 12")
    cooling_frame = ttk.Frame(settings_window, padding="3 3 12 12")

    # Now you can create StringVar instances
    spool_motor_min_voltage_var = tk.StringVar(root)
    spool_motor_max_voltage_var = tk.StringVar(root)
    cutter_motor_min_voltage_var = tk.StringVar(root)
    cutter_motor_max_voltage_var = tk.StringVar(root)
    extra_plastics_motor_min_voltage_var = tk.StringVar(root)
    extra_plastics_motor_max_voltage_var = tk.StringVar(root)
    plastics_cooling_motor_min_voltage_var = tk.StringVar(root)
    plastics_cooling_motor_max_voltage_var = tk.StringVar(root)

    # IMAGES
    ###

    # Create the main frame that will contain the watermark and the diagram
    main_frame = ttk.Frame(root, padding="3 3 12 12")
    main_frame.pack(fill='both', expand=True)  # Fill the window with the main frame
    main_frame.grid_columnconfigure(0, weight=1)  # Make the column within main_frame expandable
    main_frame.grid_rowconfigure(1, weight=1)  # Make the row within main_frame expandable

    # Create and place the watermark logo
    watermark_logo_size = (50, 50)  # Desired size for the watermark logo
    watermark_logo_image = original_logo_image.resize(watermark_logo_size, Image.Resampling.LANCZOS)
    watermark_logo_photo = ImageTk.PhotoImage(watermark_logo_image)
    # Add the watermark logo to the main frame
    watermark_logo_label = tk.Label(main_frame, image=watermark_logo_photo, bg="#333")
    watermark_logo_label.grid(row=0, column=0, sticky=tk.W)  # Place it in the top-left corner of main_frame

    # Diagram label setup using grid manager within the main frame
    diagram_label = tk.Label(main_frame, image=diagram_photo)
    diagram_label.grid(row=1, column=0, sticky="nsew")  # Make the diagram expand with the main frame
    resize_image(None)  # Call it once to initialize the correct size

    # Bind the resize event to the resize_image function
    root.bind('<Configure>', resize_image)
    root.after_idle(resize_image)

    ###

    # Call to create StringVars
    create_string_vars()

    # Ensure overall_speed_var is declared at the beginning to be globally accessible
    overall_speed_var = tk.DoubleVar(value=50)

    # Create StringVar for temperature input
    temperature_var = StringVar(value="25")  # Default temperature set to 25 degrees
    temperature_var.trace('w', lambda *args: update_gui())  # Add this line here

    # Frame for temperature entry
    temp_entry_frame = ttk.Frame(root, padding="3 3 12 12")
    temp_entry_frame.pack(fill='x', padx=20, pady=5)
    
    # Label for temperature entry
    temp_label = Label(temp_entry_frame, text="Enter Temperature (°C):", bg="#333", fg="white")
    temp_label.pack(side='left', padx=(10, 2))
    
    # Entry for temperature
    temp_entry = Entry(temp_entry_frame, textvariable=temperature_var, width=10)
    temp_entry.pack(side='left', padx=(2, 10))

    overall_speed_var.trace('w', update_motor_settings)  # Trace variable changes
    
    # GUI elements setup
    overall_speed_scale = Scale(root, from_=0, to 100, variable=overall_speed_var,
                                label="Overall Speed (%)", orient='horizontal', bg="#ddd")
    overall_speed_scale.pack(fill='x', padx=20, pady=10)

    # Data labels
    temp_var = tk.StringVar(value="Temperature: --")
    fan_speed_var = tk.StringVar(value="Fan Speed: --")  # Ensure this is declared at the global scope
    motor_speed_var = tk.StringVar(value="Motor Speed: --")
    power_consumption_var = tk.StringVar(value="Power Consumption: --")
    
    Label(root, textvariable=temp_var, bg="#333", fg="#fff").pack()
    Label(root, textvariable=fan_speed_var, bg="#333", fg="#fff").pack()
    Label(root, textvariable=motor_speed_var, bg="#333", fg="#fff").pack()
    Label(root, textvariable=power_consumption_var, bg="#333", fg="#fff").pack()

    # Control buttons
    settings_button = Button(root, text="Open Settings", command=open_algorithm_settings,
                             bg="#5cb85c", fg="white")
    settings_button.pack(fill='x', padx=20, pady=10)
    calculate_intervals_based_on_diagram()

    # Bottom frame setup
    bottom_frame = tk.Frame(root, bg="#333")
    bottom_frame.pack(side='bottom', fill='x', padx=10, pady=5)

    # Motor controls setup
    create_motor_controls("Spool Motor", spool_frame)
    create_motor_controls("Plastics Cooling", cooling_frame)

    # Start the GUI update loop
    update_gui()

    # Closing protocol setup
    root.protocol("WM_DELETE_WINDOW", on_closing)

    # Start the Tkinter main loop
    root.mainloop()

