import time
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

# Global variables to store the delayed resize task and last window size
resize_task = None
last_window_size = (0, 0)

# Simulate a serial connection (for debug mode)
class FakeSerial:
    def write(self, command):
        print(f"Sending command to Arduino: {command.decode().strip()}")
    def close(self):
        print("Closing fake serial connection")

####################################################

def create_string_vars():
    global spool_motor_min_voltage_var, spool_motor_max_voltage_var
    global cutter_motor_min_voltage_var, cutter_motor_max_voltage_var
    global extra_plastics_motor_min_voltage_var, extra_plastics_motor_max_voltage_var
    global plastics_cooling_motor_min_voltage_var, plastics_cooling_motor_max_voltage_var

    spool_motor_min_voltage_var = tk.StringVar(value="0.00")
    spool_motor_max_voltage_var = tk.StringVar(value="12.00")
    cutter_motor_min_voltage_var = tk.StringVar(value="0.00")
    cutter_motor_max_voltage_var = tk.StringVar(value="12.00")
    extra_plastics_motor_min_voltage_var = tk.StringVar(value="0.00")
    extra_plastics_motor_max_voltage_var = tk.StringVar(value="12.00")
    plastics_cooling_motor_min_voltage_var = tk.StringVar(value="0.00")
    plastics_cooling_motor_max_voltage_var = tk.StringVar(value="12.00")

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

# Function to calculate voltage based on speed percentage and overall speed
def calculate_voltage(item, speed_percent, overall_speed_percent):
    # Base voltage for CD drive motors assumed at 12V maximum
    base_voltage = 12

    # Define dynamic voltage ranges for different motors based on overall speed percent
    # Adjusting the voltage calculation for CD drive motors
    if item in ["Spool Motor", "Cutter Motor", "Extra Plastics Motor", "Plastics Cooling"]:
        # Assuming CD drive motors operate safely at 70% of their rated voltage for longevity
        safe_operation_percentage = 0.7
        min_voltage = base_voltage * (overall_speed_percent / 100) * safe_operation_percentage
        # Assuming no additional increment for CD drive motors as they operate at a fixed voltage
        max_voltage = min_voltage
    else:
        # For other motors, existing logic can remain
        min_voltage = base_voltage * (overall_speed_percent / 100) * 0.5
        max_increment = 0.25
        max_voltage = min_voltage + (base_voltage * max_increment)

    # Ensure max voltage does not exceed base voltage
    max_voltage = min(max_voltage, base_voltage)

    # Calculate the actual voltage within this dynamic range
    voltage = min_voltage + (max_voltage - min_voltage) * (speed_percent / 100)
    return voltage

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

# Function to calculate and update allowed voltage ranges for each motor
def update_allowed_voltage_ranges(*args):
    # Assuming different base voltage requirements for each motor based on their roles
    base_voltages = {
        'Spool Motor': 9.0,  # Example voltage, adjust based on your requirements
        'Cutter Motor': 5.0,  # Example voltage, adjust based on your requirements
        'Extra Plastics Motor': 6.0,  # Example voltage, adjust based on your requirements
        'Plastics Cooling': 4.5  # Example voltage, adjust based on your requirements
    }

    # Assuming a dynamic range based on the percentage of maximum speed
    for motor_name, base_voltage in base_voltages.items():
        # Calculate min and max allowed voltages (for example, 80%-120% of base voltage)
        min_voltage = base_voltage * 0.8
        max_voltage = base_voltage * 1.2

        # Update the labels with the calculated ranges
        allowed_voltage_labels[motor_name].config(text=f"Allowed Voltage: {min_voltage:.2f} - {max_voltage:.2f} V")


# Helper function to create motor controls
def create_motor_controls(motor_name, frame):
     # Declare global variables at the beginning of the function
    global spool_motor_voltage_label, spool_motor_min_voltage_entry, spool_motor_max_voltage_entry
    global cutter_motor_voltage_label, cutter_motor_min_voltage_entry, cutter_motor_max_voltage_entry
    global extra_plastics_motor_voltage_label, extra_plastics_motor_min_voltage_entry, extra_plastics_motor_max_voltage_entry
    global plastics_cooling_motor_voltage_label, plastics_cooling_motor_min_voltage_entry, plastics_cooling_motor_max_voltage_entry


    # Create the variable for the entry before using it
    min_voltage_var = StringVar(value="0")
    max_voltage_var = StringVar(value="12")

    # Label for the motor speed scale
    scale_label = Label(frame, text=f"{motor_name} Speed (%)", bg="#333", fg="white")
    scale_label.grid(row=0, column=0, padx=10, pady=5, sticky='w')

    # Motor speed scale
    scale = Scale(frame, from_=0, to=100, orient='horizontal', bg="#ddd")
    scale.grid(row=0, column=1, padx=10, pady=5, sticky='ew')

    # Create and store the allowed voltage label in the dictionary
    allowed_voltage_labels[motor_name] = Label(frame, text="Allowed Voltage: -- V", bg="#333", fg="white")
    allowed_voltage_labels[motor_name].grid(row=1, column=0, columnspan=4, padx=10, pady=5, sticky='w')

    # Voltage output label
    voltage_output_label = Label(frame, text="Voltage Output: -- V", bg="#333", fg="white")
    voltage_output_label.grid(row=0, column=4, padx=10, pady=5, sticky='w')

    # Min Voltage Entry - Increase padx to move it further away
    min_voltage_entry = Entry(frame, textvariable=min_voltage_var, width=6)
    min_voltage_entry.grid(row=1, column=1, padx=(30, 0), pady=5, sticky='W')  # Increase the left padding

    # Max Voltage Entry - Increase padx to move it further away
    max_voltage_entry = Entry(frame, textvariable=max_voltage_var, width=6)
    max_voltage_entry.grid(row=1, column=2, padx=(5, 20), pady=5, sticky='W')  # Increase the right padding

    if motor_name == "Spool Motor":
        spool_motor_voltage_label = voltage_output_label
        spool_motor_min_voltage_entry = min_voltage_entry
        spool_motor_max_voltage_entry = max_voltage_entry
    elif motor_name == "Cutter Motor":
        cutter_motor_voltage_label = voltage_output_label
        cutter_motor_min_voltage_entry = min_voltage_entry
        cutter_motor_max_voltage_entry = max_voltage_entry
    elif motor_name == "Extra Plastics Motor":
        extra_plastics_motor_voltage_label = voltage_output_label
        extra_plastics_motor_min_voltage_entry = min_voltage_entry
        extra_plastics_motor_max_voltage_entry = max_voltage_entry
    elif motor_name == "Plastics Cooling":
        plastics_cooling_motor_voltage_label = voltage_output_label
        plastics_cooling_motor_min_voltage_entry = min_voltage_entry
        plastics_cooling_motor_max_voltage_entry = max_voltage_entry

    # Update the voltage range globals when entries change
    def on_voltage_change(*args):
        try:
            min_voltage = float(min_voltage_var.get())
            max_voltage = float(max_voltage_var.get())
            # Update the motor voltages and output labels accordingly
            # ... Your existing logic here ...
        except ValueError as e:
            messagebox.showerror("Input Error", "Please enter valid numbers for voltage ranges.")

    # Trace changes to update voltage range
    min_voltage_var.trace_add("write", on_voltage_change)
    max_voltage_var.trace_add("write", on_voltage_change)

    return scale, voltage_output_label, allowed_voltage_labels[motor_name]

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
    # Use the global keyword to modify global variables inside a function
    global spool_frame, cutter_frame, extra_frame, cooling_frame

    # Create the settings window first
    settings_window = Toplevel(root, bg="#333")
    settings_window.title("Algorithm Settings")

    # Ensure that this line comes AFTER the motor control setup functions
    create_voltage_range_interval_labels(settings_window)  # Assuming you are passing the correct argument

    # Explanation label
    explanation_label = Label(settings_window, text="Adjust settings for motor speeds and voltage ranges.", bg="#333", fg="white")
    explanation_label.grid(row=0, column=0, columnspan=4, padx=10, pady=10)

    # Create frames for each set of controls with settings_window as their parent
    spool_frame = ttk.Frame(settings_window, padding="3 3 12 12")
    cutter_frame = ttk.Frame(settings_window, padding="3 3 12 12")
    extra_frame = ttk.Frame(settings_window, padding="3 3 12 12")
    cooling_frame = ttk.Frame(settings_window, padding="3 3 12 12")

    spool_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
    cutter_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
    extra_frame.grid(row=3, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
    cooling_frame.grid(row=4, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

    # Create the controls within each frame
    spool_motor_controls = create_motor_controls("Spool Motor", spool_frame)
    cutter_motor_controls = create_motor_controls("Cutter Motor", cutter_frame)
    extra_plastics_motor_controls = create_motor_controls("Extra Plastics Motor", extra_frame)
    plastics_cooling_motor_controls = create_motor_controls("Plastics Cooling", cooling_frame)

    # To this:
    spool_motor_scale, _, spool_motor_interval_label = create_motor_controls("Spool Motor", spool_frame)
    cutter_motor_scale, _, cutter_motor_interval_label = create_motor_controls("Cutter Motor", cutter_frame)
    extra_plastics_motor_scale, _, extra_plastics_motor_interval_label = create_motor_controls("Extra Plastics Motor", extra_frame)
    plastics_cooling_motor_scale, _, plastics_cooling_motor_interval_label = create_motor_controls("Plastics Cooling", cooling_frame)


    # Place Apply Settings button in the settings window
        # Style the "Apply Settings" button
    apply_button = Button(settings_window, text="Apply Settings", command=apply_settings,
                          bg="#5cb85c", fg="white", relief='flat')  # Match the style of the open settings button
    apply_button.grid(row=5, column=0, columnspan=4, padx=10, pady=10, sticky='ew')

    # Make the settings window resizable
    settings_window.resizable(True, True)

    # Call update_voltage_range_labels_and_vars with proper arguments
    # You need to provide the minimum and maximum voltage values here
    min_voltage = 0.00 # Replace with actual minimum voltage if available
    max_voltage = 12.00 # Replace with actual maximum voltage if available

    # Bind the overall speed variable to adjust the voltage ranges when it changes
    overall_speed_var.trace('w', update_voltage_range_labels_and_vars)

    update_voltage_range_labels_and_vars(min_voltage, max_voltage, settings_window)

    
    settings_window.columnconfigure(0, weight=1)  # This will ensure the frame resizes with the window
    settings_window.rowconfigure(1, weight=1)  # This will allow the frame to expand vertically if needed

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

# Function to connect to the Arduino or simulate connection
def connect_to_arduino(port, baud_rate):
    if DEBUG_MODE:
        print(f"Debug mode: Simulating connection to {port} at {baud_rate} baud")
        return FakeSerial()
    else:
        try:
            return serial.Serial(port, baud_rate)
        except serial.SerialException as e:
            messagebox.showerror("Connection Error", f"Could not connect to {port}: {e}")
            return None

# Function to send a command to the Arduino or simulate it
def send_command(command):
    if arduino:
        arduino.write(f"{command}\n".encode())

# Function to update the GUI with data from the Arduino or simulated data
def update_gui():
    if DEBUG_MODE:
        # Simulate Arduino data for debug purposes
        temp_var.set("Temperature: 200\u00B0C (Debug)")
        fan_speed_var.set("Fan Speed: 50% (Debug)")
        motor_speed_var.set("Motor Speed: 100 steps/s (Debug)")
        power_consumption_var.set("Power Consumption: 100W (Debug)")
    else:
        # Actual serial communication code would go here
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

# Function to update the voltage ranges based on user input
def update_voltage_ranges(*args):
    global spool_motor_voltage_range, cutter_motor_voltage_range
    global extra_plastics_motor_voltage_range, plastics_cooling_motor_voltage_range

    # Update the voltage range for each motor
    spool_motor_voltage_range = (float(spool_motor_min_voltage_entry.get()), float(spool_motor_max_voltage_entry.get()))
    cutter_motor_voltage_range = (float(cutter_motor_min_voltage_entry.get()), float(cutter_motor_max_voltage_entry.get()))
    extra_plastics_motor_voltage_range = (float(extra_plastics_motor_min_voltage_entry.get()), float(extra_plastics_motor_max_voltage_entry.get()))
    plastics_cooling_motor_voltage_range = (float(plastics_cooling_motor_min_voltage_entry.get()), float(plastics_cooling_motor_max_voltage_entry.get()))

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

def setup_trace():
    # Trace changes in the overall speed variable
    overall_speed_var.trace('w', update_voltage_range_labels_and_vars)

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

    # Create frames within the root context
    spool_frame = ttk.Frame(root, padding="3 3 12 12")
    cutter_frame = ttk.Frame(root, padding="3 3 12 12")
    extra_frame = ttk.Frame(root, padding="3 3 12 12")
    cooling_frame = ttk.Frame(root, padding="3 3 12 12")

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
    overall_speed_var.trace('w',  update_allowed_voltage_ranges)  # Trace variable changes

    setup_trace()  # Setup additional traces if necessary

    # GUI elements setup
    overall_speed_scale = Scale(root, from_=0, to=100, variable=overall_speed_var,
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
    create_motor_controls("Cutter Motor", cutter_frame)
    create_motor_controls("Extra Plastics Motor", extra_frame)
    create_motor_controls("Plastics Cooling", cooling_frame)

    # COM port and baud rate setup
    com_port, baud_rate = setup_com_port()

    # Connect to Arduino or simulate connection
    arduino = connect_to_arduino(com_port, baud_rate)

    # Start the GUI update loop
    update_gui()

    # Closing protocol setup
    root.protocol("WM_DELETE_WINDOW", on_closing)

    # Start the Tkinter main loop
    root.mainloop()