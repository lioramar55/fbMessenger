import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading
import queue
import json
from database import MessageDatabase
from main import FacebookMessenger, perform_manual_login
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType
import pandas as pd
import os
import time
import random
import pickle
from ttkthemes import ThemedTk  # For better styling

class FacebookMessengerAdapter:
    """Adapter class to integrate FacebookMessenger with our database and GUI"""
    def __init__(self, db, logger_callback=None, captcha_callback=None):
        self.db = db
        self.driver = None
        self.messenger = None
        self.logger = logger_callback or (lambda msg: print(msg))
        self.captcha_callback = captcha_callback
        self.login_paused = False
        
    def set_add_friend_option(self, should_add: bool):
        """Pass the add friend option to the messenger instance"""
        if self.messenger:
            self.messenger.should_add_friend = should_add
        
    def initialize(self):
        """Initialize the WebDriver and FacebookMessenger"""
        self.logger("Setting up Chrome WebDriver...")
        options = webdriver.ChromeOptions()
        options.add_argument("--start-maximized")
        
        try:
            # Try using webdriver-manager with explicit Chrome version
            from selenium.webdriver.chrome.service import Service
            from webdriver_manager.chrome import ChromeDriverManager
            from webdriver_manager.core.os_manager import ChromeType
            
            # Get current Chrome version and download matching driver
            service = Service(ChromeDriverManager(chrome_type=ChromeType.GOOGLE).install())
            self.driver = webdriver.Chrome(service=service, options=options)
        except Exception as e:
            self.logger(f"Error with automatic ChromeDriver: {str(e)}")
            
            # Fallback to manually specified ChromeDriver
            try:
                import os
                # Look for chromedriver in the current directory or use absolute path
                driver_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chromedriver.exe")
                
                if not os.path.exists(driver_path):
                    self.logger(f"ChromeDriver not found at: {driver_path}")
                    self.logger("Please download the appropriate ChromeDriver from: https://chromedriver.chromium.org/downloads")
                    self.logger("Make sure to match it with your Chrome browser version")
                    raise FileNotFoundError(f"ChromeDriver not found at: {driver_path}")
                
                service = Service(executable_path=driver_path)
                self.driver = webdriver.Chrome(service=service, options=options)
            except Exception as inner_e:
                self.logger(f"Failed to initialize ChromeDriver: {str(inner_e)}")
                raise
        
        self.messenger = FacebookMessenger(self.driver)
        return self.driver, self.messenger
        
    def login_to_facebook(self, email, password):
        """Handle Facebook login with cookie management"""
        if not self.driver or not self.messenger:
            self.initialize()
            
        self.logger("Navigating to Facebook...")
        self.driver.get("https://www.facebook.com")
        time.sleep(3)
        
        # Try to load cookies from database
        saved_cookies = self.db.get_cookies("facebook.com")
        login_required = True
        
        if saved_cookies:
            self.logger("Found saved login session, attempting to use it...")
            try:
                for cookie in saved_cookies:
                    if 'expiry' in cookie and cookie['expiry'] is None:
                        del cookie['expiry']
                    self.driver.add_cookie(cookie)
                self.driver.refresh()
                time.sleep(5)
                
                # Check if we're still on the login page
                if "login" not in self.driver.current_url.lower() and "authentication" not in self.driver.current_url.lower():
                    self.logger("Successfully logged in using saved session!")
                    login_required = False
                else:
                    self.logger("Previous session expired, proceeding with manual login...")
            except Exception as e:
                self.logger(f"Error loading cookies: {str(e)}")
        else:
            self.logger("No saved login session found, proceeding with manual login...")
        
        # Perform manual login if needed
        if login_required:
            self.logger("Performing manual login...")
            # Make sure we're on the login page
            self.driver.get("https://www.facebook.com")
            time.sleep(3)
            
            # Modified login process to handle captcha with GUI
            login_result = self.custom_login(email, password)
            if not login_result:
                self.logger("Login process failed or was interrupted.")
                return False
            
            # Check if login was successful
            if "login" in self.driver.current_url.lower() or "authentication" in self.driver.current_url.lower():
                self.logger("Login failed. Please check your credentials.")
                return False
                
            # Save cookies to database after successful login
            try:
                cookies = self.driver.get_cookies()
                if self.db.save_cookies("facebook.com", cookies):
                    self.logger("Login session saved for future use!")
            except Exception as e:
                self.logger(f"Error saving cookies: {str(e)}")
        
        # Verify we're logged in by checking for common elements or URLs
        try:
            self.logger("Verifying login status...")
            time.sleep(2)
            
            # Multiple checks for login status
            logged_in = False
            
            # Check 1: URL check
            if "login" not in self.driver.current_url.lower() and "authentication" not in self.driver.current_url.lower():
                logged_in = True
            
            # Check 2: Try to find common elements that indicate we're logged in
            if not logged_in:
                try:
                    elements_to_check = [
                        "//input[@placeholder='Search Facebook']",
                        "//a[@aria-label='Home']",
                        "//div[@aria-label='Your profile']",
                        "//div[@aria-label='Menu']",
                        "//div[@aria-label='Messenger']"
                    ]
                    
                    for xpath in elements_to_check:
                        try:
                            if self.driver.find_elements(By.XPATH, xpath):
                                logged_in = True
                                break
                        except:
                            continue
                except:
                    pass
            
            # Check 3: Check if we can access the news feed
            if not logged_in:
                try:
                    self.driver.get("https://www.facebook.com/")
                    time.sleep(2)
                    if "login" not in self.driver.current_url.lower():
                        logged_in = True
                except:
                    pass
                
            if logged_in:
                self.logger("Login verification successful!")
                return True
            else:
                self.logger("Warning: Login verification failed. Proceeding anyway since initial login was successful.")
                return True  # Return True anyway if we got past the initial login checks
                
        except Exception as e:
            self.logger(f"Error verifying login: {str(e)}")
            self.logger("Proceeding anyway since initial login was successful.")
            return True  # Return True anyway if we got past the initial login checks
    
    def custom_login(self, email, password):
        """Custom login process with captcha handling"""
        try:
            # Find and fill email field
            email_field = self.driver.find_element(By.ID, "email")
            email_field.clear()
            email_field.send_keys(email)
            
            # Find and fill password field
            password_field = self.driver.find_element(By.ID, "pass")
            password_field.clear()
            password_field.send_keys(password)
            
            # Submit the form
            password_field.send_keys(Keys.RETURN)
            
            # Wait for login to process
            time.sleep(5)
            
            # Check for security challenges
            if ("checkpoint" in self.driver.current_url.lower() or 
                "security" in self.driver.current_url.lower() or
                "captcha" in self.driver.page_source.lower() or
                "verification" in self.driver.page_source.lower()):
                
                captcha_detected = True
                self.logger("Security verification required")
                
                # Set login as paused and notify GUI
                self.login_paused = True
                if self.captcha_callback:
                    self.captcha_callback(True)
                
                # Wait until resumed by GUI
                wait_count = 0
                max_wait = 300  # 5 minute timeout
                while self.login_paused and wait_count < max_wait:
                    time.sleep(1)
                    wait_count += 1
                
                if wait_count >= max_wait:
                    self.logger("Timeout waiting for verification")
                    if self.captcha_callback:
                        self.captcha_callback(False)
                    return False
            
            return True
        except Exception as e:
            self.logger(f"Login error: {str(e)}")
            return False
    
    def resume_after_captcha(self):
        """Resume login process after captcha is solved"""
        self.login_paused = False
        self.logger("Continuing after verification...")
        if self.captcha_callback:
            self.captcha_callback(False)
    
    def send_message(self, profile, message):
        """Send a message to a profile and record the result"""
        if not self.driver or not self.messenger:
            raise ValueError("FacebookMessenger not initialized")
            
        # Verify we're logged in before attempting to send message
        if "login" in self.driver.current_url.lower() or "authentication" in self.driver.current_url.lower():
            self.logger("Error: Not logged in. Cannot send message.")
            return False
            
        success = self.messenger.send_message_to_profile(profile, message)
        
        # Record status
        status = "success" if success else "failed"
        self.db.save_message_status(profile, status)
        
        return success
        
    def close(self):
        """Close the WebDriver"""
        if self.driver:
            self.driver.quit()
            self.driver = None
            self.messenger = None

class MessengerBotGUI:
    def __init__(self):
        self.root = ThemedTk(theme="arc")  # Use a modern theme
        self.root.title("Facebook Group Messenger Bot")
        self.root.geometry("900x700")  # Slightly larger window
        
        # Configure style
        style = ttk.Style()
        style.configure("Custom.TButton", padding=5)
        style.configure("Success.TButton", background="green", padding=5)
        style.configure("Warning.TButton", background="red", padding=5)
        
        self.db = MessageDatabase()
        self.is_running = False
        self.fb_adapter = FacebookMessengerAdapter(
            self.db, 
            logger_callback=self.log,
            captcha_callback=self.handle_captcha
        )
        self.message_queue = queue.Queue()
        self.captcha_frame = None
        self.control_frame = None
        self.stats_frame = None  # New frame for statistics
        
        self.create_gui()
        self.load_saved_settings()
        
    def create_gui(self):
        # Create notebook for tabs
        notebook = ttk.Notebook(self.root)
        notebook.pack(expand=True, fill='both', padx=10, pady=10)  # Increased padding
        
        # Main tab
        main_frame = ttk.Frame(notebook)
        notebook.add(main_frame, text='Main')
        
        # Credentials frame with improved styling
        cred_frame = ttk.LabelFrame(main_frame, text="Facebook Credentials", padding=10)
        cred_frame.pack(fill='x', padx=10, pady=5)
        
        # Grid configuration for better alignment
        cred_frame.grid_columnconfigure(1, weight=1)
        
        ttk.Label(cred_frame, text="Email:").grid(row=0, column=0, padx=10, pady=5, sticky='e')
        self.email_var = tk.StringVar()
        ttk.Entry(cred_frame, textvariable=self.email_var, width=40).grid(row=0, column=1, padx=10, pady=5, sticky='ew')
        
        ttk.Label(cred_frame, text="Password:").grid(row=1, column=0, padx=10, pady=5, sticky='e')
        self.password_var = tk.StringVar()
        ttk.Entry(cred_frame, textvariable=self.password_var, show="*", width=40).grid(row=1, column=1, padx=10, pady=5, sticky='ew')
        
        # Message frame with better spacing
        msg_frame = ttk.LabelFrame(main_frame, text="Message", padding=10)
        msg_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Add friend checkbox
        self.add_friend_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(msg_frame, text="Add friend when messaging", variable=self.add_friend_var).pack(anchor='w', padx=5, pady=2)
        
        self.message_text = scrolledtext.ScrolledText(msg_frame, height=5, font=('Segoe UI', 10))
        self.message_text.pack(fill='both', expand=True, padx=5, pady=5)
        
        # CSV file frame with improved layout
        csv_frame = ttk.LabelFrame(main_frame, text="Profile List (CSV)", padding=10)
        csv_frame.pack(fill='x', padx=10, pady=5)
        
        self.csv_path_var = tk.StringVar()
        ttk.Entry(csv_frame, textvariable=self.csv_path_var, state='readonly').pack(side='left', fill='x', expand=True, padx=5, pady=5)
        ttk.Button(csv_frame, text="Browse", command=self.browse_csv, style="Custom.TButton").pack(side='right', padx=5, pady=5)
        
        # Wait time frame with better organization
        wait_frame = ttk.LabelFrame(main_frame, text="Wait Time Between Profiles (seconds)", padding=10)
        wait_frame.pack(fill='x', padx=10, pady=5)
        
        # Grid configuration for wait times
        wait_frame.grid_columnconfigure(1, weight=1)
        wait_frame.grid_columnconfigure(3, weight=1)
        
        ttk.Label(wait_frame, text="Min:").grid(row=0, column=0, padx=10, pady=5)
        self.min_wait_var = tk.StringVar(value="15")
        ttk.Entry(wait_frame, textvariable=self.min_wait_var, width=5).grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(wait_frame, text="Max:").grid(row=0, column=2, padx=10, pady=5)
        self.max_wait_var = tk.StringVar(value="30")
        ttk.Entry(wait_frame, textvariable=self.max_wait_var, width=5).grid(row=0, column=3, padx=5, pady=5)
        
        # Stats frame - New addition
        self.stats_frame = ttk.LabelFrame(main_frame, text="Statistics", padding=10)
        self.stats_frame.pack(fill='x', padx=10, pady=5)
        
        # Progress bar and stats
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(self.stats_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill='x', padx=5, pady=5)
        
        # Stats grid
        stats_grid = ttk.Frame(self.stats_frame)
        stats_grid.pack(fill='x', padx=5)
        
        # Statistics variables
        self.total_var = tk.StringVar(value="Total: 0")
        self.success_var = tk.StringVar(value="Success: 0")
        self.failed_var = tk.StringVar(value="Failed: 0")
        self.skipped_var = tk.StringVar(value="Skipped: 0")
        
        ttk.Label(stats_grid, textvariable=self.total_var).grid(row=0, column=0, padx=10)
        ttk.Label(stats_grid, textvariable=self.success_var).grid(row=0, column=1, padx=10)
        ttk.Label(stats_grid, textvariable=self.failed_var).grid(row=0, column=2, padx=10)
        ttk.Label(stats_grid, textvariable=self.skipped_var).grid(row=0, column=3, padx=10)
        
        # Control frame with improved styling
        self.control_frame = ttk.Frame(main_frame)
        self.control_frame.pack(fill='x', padx=10, pady=5)
        
        # Left side controls
        left_controls = ttk.Frame(self.control_frame)
        left_controls.pack(side='left')
        
        self.start_button = ttk.Button(left_controls, text="Start", command=self.toggle_bot, style="Success.TButton")
        self.start_button.pack(side='left', padx=5)
        
        ttk.Button(left_controls, text="Restart Fresh", command=self.restart_bot, style="Custom.TButton").pack(side='left', padx=5)
        
        # Right side controls
        ttk.Button(self.control_frame, text="Clear History", command=self.clear_history, style="Warning.TButton").pack(side='right', padx=5)
        
        # Captcha frame - create it here but don't pack it yet
        self.captcha_frame = ttk.LabelFrame(main_frame, text="Security Verification", relief="raised", borderwidth=2)
        
        captcha_label = ttk.Label(
            self.captcha_frame, 
            text="Complete the verification in the browser window",
            foreground="red",
            font=("Arial", 10, "bold")
        )
        captcha_label.pack(pady=5)
        
        self.resume_button = ttk.Button(
            self.captcha_frame, 
            text="Continue After Verification", 
            command=self.resume_after_captcha
        )
        self.resume_button.pack(pady=5)
        
        # History tab
        history_frame = ttk.Frame(notebook)
        notebook.add(history_frame, text='History')
        
        # Create treeview for history
        columns = ('Profile', 'Status', 'Date')
        self.history_tree = ttk.Treeview(history_frame, columns=columns, show='headings')
        
        # Configure column widths and headings
        self.history_tree.heading('Profile', text='Profile')
        self.history_tree.heading('Status', text='Status')
        self.history_tree.heading('Date', text='Date')
        
        self.history_tree.column('Profile', width=300)
        self.history_tree.column('Status', width=100)
        self.history_tree.column('Date', width=150)
        
        self.history_tree.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Add scrollbar to history
        scrollbar = ttk.Scrollbar(history_frame, orient='vertical', command=self.history_tree.yview)
        scrollbar.pack(side='right', fill='y')
        self.history_tree.configure(yscrollcommand=scrollbar.set)
        
        # Logs tab - NEW
        logs_frame = ttk.Frame(notebook)
        notebook.add(logs_frame, text='Logs')
        
        # Create scrolled text for logs
        self.progress_text = scrolledtext.ScrolledText(
            logs_frame,
            height=10,
            font=('Segoe UI', 10),
            wrap=tk.WORD,  # Enable word wrapping
            undo=True,  # Enable undo/redo
        )
        # Make text widget read-only but selectable
        self.progress_text.bind("<Key>", lambda e: "break")  # Disable typing
        self.progress_text.bind("<Control-c>", lambda e: "continue")  # Allow copy
        self.progress_text.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Add right-click menu for copy
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="Copy", command=self.copy_selected_text)
        self.progress_text.bind("<Button-3>", self.show_context_menu)
        
        # Update history display
        self.update_history_display()
    
    def handle_captcha(self, show):
        """Show or hide the captcha frame"""
        if show:
            self.log("⚠️ CAPTCHA detected! Complete it in the browser, then click 'Continue'")
            
            # Remove the captcha frame if it's already showing
            self.captcha_frame.pack_forget()
            
            # Show the captcha frame between control_frame and progress_frame
            self.captcha_frame.pack(after=self.control_frame, fill='x', padx=5, pady=5)
            
            # Bring window to front to alert user
            self.root.lift()
            self.root.attributes('-topmost', True)
            self.root.after_idle(self.root.attributes, '-topmost', False)
        else:
            self.captcha_frame.pack_forget()
    
    def resume_after_captcha(self):
        """Resume the bot after captcha is solved"""
        self.log("✅ Continuing after verification...")
        self.fb_adapter.resume_after_captcha()
        self.captcha_frame.pack_forget()
        
        # Force update the GUI to ensure changes are visible
        self.root.update_idletasks()
    
    def load_saved_settings(self):
        """Load saved settings from database"""
        email = self.db.get_setting('email', '')
        password = self.db.get_setting('password', '')
        message = self.db.get_setting('message', '')
        csv_path = self.db.get_setting('csv_path', '')
        min_wait = self.db.get_setting('min_wait', '15')
        max_wait = self.db.get_setting('max_wait', '30')
        add_friend = self.db.get_setting('add_friend', 'False')
        
        self.email_var.set(email)
        self.password_var.set(password)
        self.message_text.insert('1.0', message)
        self.csv_path_var.set(csv_path)
        self.min_wait_var.set(min_wait)
        self.max_wait_var.set(max_wait)
        self.add_friend_var.set(add_friend.lower() == 'true')
    
    def save_settings(self):
        """Save current settings to database"""
        self.db.save_setting('email', self.email_var.get())
        self.db.save_setting('password', self.password_var.get())
        self.db.save_setting('message', self.message_text.get('1.0', 'end-1c'))
        self.db.save_setting('csv_path', self.csv_path_var.get())
        self.db.save_setting('min_wait', self.min_wait_var.get())
        self.db.save_setting('max_wait', self.max_wait_var.get())
        self.db.save_setting('add_friend', str(self.add_friend_var.get()))
    
    def browse_csv(self):
        """Open file dialog to select CSV file"""
        filename = filedialog.askopenfilename(
            title="Select CSV file",
            filetypes=(("CSV files", "*.csv"), ("All files", "*.*"))
        )
        if filename:
            self.csv_path_var.set(filename)
            self.save_settings()
    
    def update_history_display(self):
        """Update the history treeview with latest data"""
        # Clear existing items
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
        
        # Get history from database and populate treeview
        history = self.db.get_message_history()
        for record in history:
            profile_url, status, sent_at = record
            self.history_tree.insert('', 'end', values=(profile_url, status, sent_at))
    
    def clear_history(self):
        """Clear message history after confirmation"""
        if messagebox.askyesno("Clear History", "Are you sure you want to clear all message history?"):
            self.db.clear_history()
            self.update_history_display()
            # Clear log panel
            self.clear_log()
            self.log("Message history cleared")
    
    def clear_log(self):
        """Clear the log panel"""
        self.progress_text.delete('1.0', 'end')
    
    def log(self, message):
        """Add message to progress log"""
        self.progress_text.insert('end', f"{message}\n")
        self.progress_text.see('end')
    
    def toggle_bot(self):
        """Start or stop the bot"""
        if not self.is_running:
            # Validate inputs
            if not all([self.email_var.get(), self.password_var.get(), 
                       self.message_text.get('1.0', 'end-1c').strip(), 
                       self.csv_path_var.get()]):
                messagebox.showerror("Error", "Please fill in all fields")
                return
            
            # Save current settings
            self.save_settings()
            
            # Start the bot
            self.is_running = True
            self.start_button.configure(text="Stop")
            threading.Thread(target=self.run_bot, daemon=True).start()
        else:
            # Stop the bot
            self.is_running = False
            self.start_button.configure(text="Start")
            self.log("Stopping bot...")
    
    def restart_bot(self):
        """Restart the bot from the beginning after clearing history"""
        if self.is_running:
            messagebox.showerror("Error", "Please stop the bot first")
            return
            
        if messagebox.askyesno("Restart Bot", "This will clear all message history and start fresh. Continue?"):
            self.db.clear_history()
            self.update_history_display()
            # Clear log panel
            self.clear_log()
            self.log("History cleared, starting fresh...")
            self.toggle_bot()
    
    def update_stats(self, total, successful, failed, skipped):
        """Update statistics display"""
        self.total_var.set(f"Total: {total}")
        self.success_var.set(f"Success: {successful}")
        self.failed_var.set(f"Failed: {failed}")
        self.skipped_var.set(f"Skipped: {skipped}")
        
        # Update progress bar
        if total > 0:
            progress = ((successful + failed + skipped) / total) * 100
            self.progress_var.set(progress)
        else:
            self.progress_var.set(0)
        
        # Force update
        self.root.update_idletasks()
    
    def run_bot(self):
        """Run the bot in a separate thread"""
        try:
            # Reset statistics
            self.update_stats(0, 0, 0, 0)
            
            # Get wait times
            try:
                min_wait = float(self.min_wait_var.get())
                max_wait = float(self.max_wait_var.get())
                if min_wait < 0 or max_wait < min_wait:
                    raise ValueError
            except ValueError:
                self.log("Invalid wait times, using defaults (15-30 seconds)")
                min_wait = 15
                max_wait = 30
            
            # Initialize FacebookMessenger
            self.fb_adapter.initialize()
            
            # Set add friend option
            self.fb_adapter.set_add_friend_option(self.add_friend_var.get())
            
            # Login to Facebook
            login_success = self.fb_adapter.login_to_facebook(
                self.email_var.get(),
                self.password_var.get()
            )
            
            if not login_success:
                self.log("❌ Login failed. Please check your credentials and try again.")
                raise Exception("Login failed")
            
            self.log("✅ Successfully logged in to Facebook!")
            
            # Load CSV
            self.log("Loading profile list from CSV...")
            df = pd.read_csv(self.csv_path_var.get())
            if "Profile Link" not in df.columns:
                raise ValueError("CSV must have a 'Profile Link' column")
            
            profile_links = df["Profile Link"].dropna().tolist()
            message = self.message_text.get('1.0', 'end-1c').strip()
            
            # Process profiles
            total = len(profile_links)
            successful = 0
            failed = 0
            skipped = 0
            
            self.log(f"Found {total} profiles to message")
            self.update_stats(total, successful, failed, skipped)
            
            for i, profile in enumerate(profile_links, 1):
                if not self.is_running:
                    break
                
                # Skip if already messaged successfully
                if self.db.has_messaged_profile(profile):
                    self.log(f"Skipping {profile} (already messaged)")
                    skipped += 1
                    self.update_stats(total, successful, failed, skipped)
                    continue
                
                self.log(f"\nProcessing profile {i}/{total}: {profile}")
                success = self.fb_adapter.send_message(profile, message)
                
                if success:
                    successful += 1
                    self.log(f"✅ Successfully messaged {profile}")
                else:
                    failed += 1
                    self.log(f"❌ Failed to message {profile}")
                
                # Update statistics and history display
                self.update_stats(total, successful, failed, skipped)
                self.root.after(0, self.update_history_display)
                
                # Add delay between profiles
                if self.is_running and i < total:
                    delay = random.uniform(min_wait, max_wait)
                    self.log(f"Waiting {delay:.1f} seconds before next profile...")
                    time.sleep(delay)
            
            self.log(f"\nFinished!")
            
        except Exception as e:
            self.log(f"Error: {str(e)}")
            import traceback
            self.log(traceback.format_exc())
        finally:
            self.fb_adapter.close()
            self.is_running = False
            self.root.after(0, lambda: self.start_button.configure(text="Start"))
    
    def run(self):
        """Start the GUI application"""
        self.root.mainloop()

    def copy_selected_text(self):
        """Copy selected text to clipboard"""
        try:
            selected_text = self.progress_text.get("sel.first", "sel.last")
            self.root.clipboard_clear()
            self.root.clipboard_append(selected_text)
        except tk.TclError:  # No selection
            pass
            
    def show_context_menu(self, event):
        """Show the context menu on right click"""
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()

if __name__ == "__main__":
    app = MessengerBotGUI()
    app.run() 