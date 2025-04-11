import os
import sys
import threading
import tkinter as tk
from tkinter import scrolledtext
from subprocess import Popen, PIPE

class BotControlPanel:
    def __init__(self, root):
        self.root = root
        self.root.title("Discord Bot Control Panel")
        self.root.geometry("1024x768")  # Set the window size to 1024x768
        self.bot_process = None
        self.stop_thread = False  # Flag to stop the thread
        self.bot_file = "brain.py"  # Link to the bot file

        # Create a non-editable command log
        self.log_label = tk.Label(root, text="Command Log:", font=("Arial", 12), fg="green")
        self.log_label.place(x=20, y=20)  # Position the label in the top-left corner
        self.log_area = scrolledtext.ScrolledText(root, width=80, height=30, state="disabled", font=("Courier", 10))
        self.log_area.place(x=20, y=50)  # Position the log area below the label

        # Create the "Go Online/Go Offline" button
        self.toggle_button = tk.Button(root, text="Go Online", command=self.toggle_bot, width=20, bg="white", fg="green", font=("Arial", 12))
        self.toggle_button.place(x=824, y=688)  # Position the button in the bottom-right corner

    def toggle_bot(self):
        if self.bot_process is None:
            # Start the bot
            self.stop_thread = False  # Reset the thread stop flag
            try:
                self.log_message("Attempting to start the bot...")
                self.bot_process = Popen([sys.executable, self.bot_file], stdout=PIPE, stderr=PIPE, text=True)
                self.toggle_button.config(text="Go Offline", fg="red")
                threading.Thread(target=self.read_bot_output, daemon=True).start()
                self.log_message(f"Bot process started with PID: {self.bot_process.pid}")
            except FileNotFoundError:
                self.log_message(f"ERROR: Could not find {self.bot_file}. Please ensure the file exists.")
            except Exception as e:
                self.log_message(f"ERROR: Failed to start the bot. Exception: {e}")
        else:
            # Stop the bot
            self.stop_thread = True  # Signal the thread to stop
            if self.bot_process:
                self.log_message(f"Attempting to terminate bot process with PID: {self.bot_process.pid}")
                self.bot_process.terminate()
                self.bot_process = None
                self.log_message("Bot process terminated.")
            self.toggle_button.config(text="Go Online", fg="green")

    def read_bot_output(self):
        """Read the bot's output and display it in the log area."""
        self.log_message("Reading bot output...")
        while not self.stop_thread:
            if self.bot_process:
                # Read stdout
                if self.bot_process.stdout:
                    for line in self.bot_process.stdout:
                        self.log_message(f"STDOUT: {line.strip()}")
                # Read stderr
                if self.bot_process.stderr:
                    for line in self.bot_process.stderr:
                        self.log_message(f"STDERR: {line.strip()}")
            else:
                break  # Exit the loop if the bot process is None
        self.log_message("Stopped reading bot output.")

    def log_message(self, message):
        """Log a message to the command log."""
        self.log_area.config(state="normal")
        self.log_area.insert(tk.END, message + "\n")
        self.log_area.see(tk.END)
        self.log_area.config(state="disabled")
        print(message)  # Also print the message to the terminal for debugging

# Run the control panel
if __name__ == "__main__":
    root = tk.Tk()
    app = BotControlPanel(root)
    root.mainloop()