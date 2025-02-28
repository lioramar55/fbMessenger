import time
import random
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    ElementClickInterceptedException,
    ElementNotInteractableException,
)
import os
import pickle
from typing import Dict, Optional, Tuple
import json
import sys
import traceback

# UI Element mappings for different languages
UI_ELEMENTS = {
    'en': {
        'message_button': "//*[contains(text(), 'Message')]",
        'message_box': "//div[@role='textbox' and @contenteditable='true' and @spellcheck='true' and @aria-label='Message']",
        'close_chat': "div[aria-label='Close chat']"
    },
    'he': {
        'message_button': "//*[contains(text(), 'הודעה')]",
        'message_box': "//div[@role='textbox' and @contenteditable='true' and @spellcheck='true' and @aria-label='שליחת הודעה']",
        'close_chat': "div[aria-label=\"סגירת הצ'אט\"]"
    }
}

class FacebookMessenger:
    def __init__(self, driver: webdriver.Chrome):
        self.driver = driver
        self.wait = WebDriverWait(driver, 10)
        self.detected_language = 'en'  # Default language
        
    def detect_interface_language(self) -> None:
        """Detect Facebook interface language using both document language attribute and UI element checks."""
        detected_lang = None

        # 1. Try to get the language attribute from the <html> tag
        try:
            lang_attr = self.driver.execute_script("return document.documentElement.lang;")
            if lang_attr:
                if lang_attr.lower().startswith("he"):
                    detected_lang = "he"
                elif lang_attr.lower().startswith("en"):
                    detected_lang = "en"
            print(f"Language attribute detected: {lang_attr}")
        except Exception as e:
            print(f"Error fetching language attribute: {e}")

        # Fallback to English if no language is detected
        if detected_lang is None:
            detected_lang = "en"
        
        self.detected_language = detected_lang
        print(f"Detected interface language: {self.detected_language}")

    def wait_for_element(self, xpath: str, timeout: int = 5) -> Tuple[bool, Optional[webdriver.remote.webelement.WebElement]]:
        """Wait for an element to be present and visible"""
        try:
            # Try presence first
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.XPATH, xpath))
            )
            
            # Then try visibility
            element = WebDriverWait(self.driver, timeout).until(
                EC.visibility_of_element_located((By.XPATH, xpath))
            )
            
            # Additional check for textbox interactability
            if 'message_box' in xpath:
                # Try multiple selectors if the first one fails
                try:
                    element = WebDriverWait(self.driver, timeout).until(
                        EC.element_to_be_clickable((By.XPATH, xpath))
                    )
                except:
                    # Try alternative selectors if the main one fails
                    alternative_selectors = [
                        "//div[@role='textbox' and @contenteditable='true']",
                        "//div[@role='textbox' and @spellcheck='true']",
                        "//div[@contenteditable='true' and @spellcheck='true']",
                        "//div[@aria-label='שליחת הודעה' and @role='textbox']",
                        "//div[@aria-label='Message' and @role='textbox']"
                    ]
                    
                    for alt_xpath in alternative_selectors:
                        try:
                            element = WebDriverWait(self.driver, 2).until(
                                EC.element_to_be_clickable((By.XPATH, alt_xpath))
                            )
                            print(f"Found message box using alternative selector: {alt_xpath}")
                            break
                        except:
                            continue
                
                if element:
                    # Try to focus the element
                    try:
                        self.driver.execute_script("arguments[0].focus();", element)
                        # Also try to scroll it into view
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
                    except:
                        print("⚠️ Could not focus element, but continuing anyway")
                
            return True, element
        except TimeoutException:
            print(f"⚠️ Timeout waiting for element: {xpath}")
            return False, None
        except Exception as e:
            print(f"⚠️ Error waiting for element {xpath}: {str(e)}")
            return False, None

    def close_chat_dialog(self) -> bool:
        """Close the chat dialog using the appropriate close button for the detected language"""
        try:
            print("🔍 Looking for close button...")
            
            close_selector = UI_ELEMENTS[self.detected_language]['close_chat']
            # Convert it to a JSON string (properly escaped for JS)
            selector_json = json.dumps(close_selector)
            
            # Build a self-invoking function as a one-liner
            close_script = (
                "return (function(){ "
                "var selector = " + selector_json + "; "
                "var buttons = document.querySelectorAll(selector); "
                "for (var i = 0; i < buttons.length; i++) { "
                "try { buttons[i].click(); return true; } catch(e) { console.error('Click failed:', e); } "
                "} "
                "return false; "
                "})();"
            )
        

            success = self.driver.execute_script(close_script)
            if success:
                print("✅ Chat popup closed")
                return True
                
            print("⚠️ Could not close chat popup")
            return False
            
        except Exception as e:
            print(f"⚠️ Error closing chat dialog: {str(e)}")
            # Print the actual selectors for debugging
            print(f"Debug - Current selectors:", UI_ELEMENTS[self.detected_language]['close_chat'])
            return False

    def find_and_click_element(self, xpath: str, wait_time: int = 5) -> Optional[webdriver.remote.webelement.WebElement]:
        """Find and click an element with explicit wait and retry logic"""
        success, element = self.wait_for_element(xpath, wait_time)
        if not success or not element:
            return None

        try:
            # Scroll element into view
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
            time.sleep(0.5)  # Small delay after scroll
            
            # Try multiple click methods
            try:
                # Method 1: JavaScript click
                self.driver.execute_script("arguments[0].click();", element)
                return element
            except:
                try:
                    # Method 2: Direct click
                    element.click()
                    return element
                except:
                    try:
                        # Method 3: Action chains
                        from selenium.webdriver.common.action_chains import ActionChains
                        actions = ActionChains(self.driver)
                        actions.move_to_element(element).click().perform()
                        return element
                    except Exception as e:
                        print(f"⚠️ All click methods failed: {str(e)}")
                        return None
                
        except ElementClickInterceptedException:
            print(f"⚠️ Element was intercepted: {xpath}")
            return None
        except ElementNotInteractableException:
            print(f"⚠️ Element not interactable: {xpath}")
            return None
        except Exception as e:
            print(f"⚠️ Error clicking element {xpath}: {str(e)}")
            return None

    def send_message_to_profile(self, profile: str, message: str) -> bool:
        """Send a message to a single profile with proper error handling and waits"""
        try:
            print(f"\n📨 Attempting to message profile: {profile}")
            
            # Navigate to profile
            self.driver.get(profile.strip())
            time.sleep(random.uniform(2, 4))  # Wait for page load
            
            # Detect language if not already detected
            self.detect_interface_language()
            
            print("🔍 Looking for message button...")
            # Click message button
            message_button = self.find_and_click_element(
                UI_ELEMENTS[self.detected_language]['message_button'],
                wait_time=7  # Increased wait time for message button
            )
            if not message_button:
                print("❌ Could not find or click message button")
                return False
            
            print("⌛ Waiting for chat popup...")
            time.sleep(random.uniform(2, 3))  # Increased wait for chat popup
            
            print("🔍 Looking for message box...")
            # Find message box with multiple attempts
            success, message_box = self.wait_for_element(
                UI_ELEMENTS[self.detected_language]['message_box'],
                timeout=7
            )
            
            if not success or not message_box:
                print("❌ Could not find message box")
                return False
                
            try:
                # Clear existing content and set up the message box
                try:
                    # Try to clear using JavaScript first
                    self.driver.execute_script("""
                        arguments[0].innerHTML = '<p><br></p>';
                        arguments[0].click();
                    """, message_box)
                except:
                    try:
                        # Fallback to direct clear
                        message_box.clear()
                    except:
                        print("⚠️ Could not clear message box, continuing anyway")
                
                time.sleep(0.5)
                
                # Try to send message with appropriate newline handling
                message_box.click()
                time.sleep(0.3)
                
                # For each line in the message, use Shift+Enter for newlines
                lines = message.split('\n')
                for i, line in enumerate(lines):
                    message_box.send_keys(line)
                    # Add a line break using Shift+Enter instead of just Enter for all but the last line
                    if i < len(lines) - 1:
                        try:
                            # Use ActionChains for more reliable Shift+Enter
                            from selenium.webdriver.common.action_chains import ActionChains
                            actions = ActionChains(self.driver)
                            actions.key_down(Keys.SHIFT).send_keys(Keys.ENTER).key_up(Keys.SHIFT).perform()
                            time.sleep(0.1)
                        except Exception as e:
                            print(f"Warning: Could not insert newline: {str(e)}")
                            # Fallback to simple send_keys if ActionChains fails
                            try:
                                message_box.send_keys(Keys.SHIFT, Keys.ENTER)
                            except:
                                # If all newline insertion fails, just continue with the next line
                                pass
                
                time.sleep(random.uniform(0.5, 1))  # Small delay before sending
                
                # Try to send the message (this part was working before)
                try:
                    message_box.send_keys(Keys.RETURN)
                except:
                    try:
                        # Fallback to JavaScript event
                        self.driver.execute_script(
                            """
                            arguments[0].dispatchEvent(new KeyboardEvent('keydown', {
                                bubbles: true,
                                cancelable: true,
                                key: 'Enter',
                                code: 'Enter'
                            }));
                            """,
                            message_box
                        )
                    except Exception as e:
                        print(f"❌ Failed to send message: {str(e)}")
                        return False
                
                print("✅ Message typed and sent")
                
            except Exception as e:
                print(f"❌ Error while typing message: {str(e)}")
                return False
            
            # Wait for message to be sent
            time.sleep(random.uniform(2, 3))
            
            # Try to close the chat dialog
            if not self.close_chat_dialog():
                print("⚠️ Warning: Could not close chat popup, but continuing...")
            
            print(f"✅ Successfully messaged {profile}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to message {profile}")
            print(f"Error details: {str(e)}")
            return False

def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)

def read_credentials() -> Tuple[Optional[str], Optional[str]]:
    """Read Facebook credentials from credentials.txt file"""
    try:
        with open("credentials.txt", "r", encoding="utf-8") as f:
            lines = f.readlines()
            
        credentials = {}
        for line in lines:
            line = line.strip()
            if '=' in line:
                key, value = line.split('=', 1)
                credentials[key.strip()] = value.strip()
        
        email = credentials.get('email')
        password = credentials.get('password')
        
        if not email or not password or email == 'your_facebook_email@example.com':
            print("❌ Error: Please update credentials.txt with your Facebook login information")
            print("The file should contain:")
            print("email=your_actual_email@example.com")
            print("password=your_actual_password")
            return None, None
            
        return email, password
    except FileNotFoundError:
        print("❌ Error: credentials.txt file not found!")
        print("Please create a credentials.txt file with your Facebook login information")
        print("The file should contain:")
        print("email=your_email@example.com")
        print("password=your_password")
        return None, None
    except Exception as e:
        print(f"❌ Error reading credentials.txt: {str(e)}")
        return None, None

def main():
    try:
        print("Starting Facebook Group Message Bot...")
        print("Checking required files...")
        
        # Check for required files
        required_files = ["members.csv", "message.txt", "credentials.txt"]
        missing_files = []
        
        for file in required_files:
            if not os.path.exists(file):
                missing_files.append(file)
        
        if missing_files:
            print("\n❌ Error: The following required files are missing:")
            for file in missing_files:
                print(f"- {file}")
            print("\nPlease create these files in the same directory as the executable.")
            input("\nPress Enter to exit...")
            return

        # Load group members CSV
        try:
            df = pd.read_csv("members.csv")
            if "Profile Link" not in df.columns:
                print("❌ Error: members.csv must have a column named 'Profile Link'")
                input("\nPress Enter to exit...")
                return
        except Exception as e:
            print(f"❌ Error reading members.csv: {str(e)}")
            input("\nPress Enter to exit...")
            return

        # Read message from file
        try:
            with open("message.txt", "r", encoding="utf-8") as f:
                MESSAGE = f.read().strip()
            if not MESSAGE:
                print("❌ Error: message.txt file is empty!")
                input("\nPress Enter to exit...")
                return
        except Exception as e:
            print(f"❌ Error reading message.txt: {str(e)}")
            input("\nPress Enter to exit...")
            return

        # Read Facebook Credentials
        EMAIL, PASSWORD = read_credentials()
        if not EMAIL or not PASSWORD:
            input("\nPress Enter to exit...")
            return

        # Load profile links
        profile_links = df["Profile Link"].dropna().tolist()
        
        if not profile_links:
            print("❌ Error: No profile links found in members.csv")
            input("\nPress Enter to exit...")
            return

        print(f"\nFound {len(profile_links)} profiles to message.")
        
        # Setup Chrome WebDriver
        print("\nSetting up Chrome WebDriver...")
        options = webdriver.ChromeOptions()
        options.add_argument("--start-maximized")
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        
        # Initialize FacebookMessenger
        messenger = FacebookMessenger(driver)
        
        try:
            # Login handling
            print("\nNavigating to Facebook...")
            driver.get("https://www.facebook.com")
            time.sleep(3)
            
            cookies_file = "cookies.pkl"
            if os.path.exists(cookies_file):
                print("Found saved login session, attempting to use it...")
                cookies = pickle.load(open(cookies_file, "rb"))
                for cookie in cookies:
                    if 'expiry' in cookie and cookie['expiry'] is None:
                        del cookie['expiry']
                    driver.add_cookie(cookie)
                driver.refresh()
                time.sleep(5)
                if "login" in driver.current_url.lower():
                    print("Previous session expired, proceeding with manual login...")
                    perform_manual_login(driver, EMAIL, PASSWORD)
            else:
                print("No saved login session found, proceeding with manual login...")
                perform_manual_login(driver, EMAIL, PASSWORD)
                # Save cookies after successful login
                pickle.dump(driver.get_cookies(), open(cookies_file, "wb"))
                print("Login session saved for future use!")
            
            # Process profiles
            print("\nStarting to send messages...")
            successful = 0
            failed = 0
            
            for i, profile in enumerate(profile_links, 1):
                print(f"\nProcessing profile {i}/{len(profile_links)}")
                success = messenger.send_message_to_profile(profile, MESSAGE)
                if success:
                    successful += 1
                else:
                    failed += 1
                # Add longer delay between profiles for safety
                delay = random.uniform(15, 30) if success else random.uniform(5, 10)
                print(f"Waiting {delay:.1f} seconds before next profile...")
                time.sleep(delay)
            
            print(f"\n✅ Finished processing all profiles!")
            print(f"Successful: {successful}")
            print(f"Failed: {failed}")
            
        finally:
            print("\nClosing browser...")
            driver.quit()
            
    except Exception as e:
        print(f"\n❌ An unexpected error occurred:")
        print(traceback.format_exc())
    
    input("\nPress Enter to exit...")

def perform_manual_login(driver: webdriver.Chrome, email: str, password: str) -> None:
    """Handle manual login process"""
    try:
        # Make sure we're on the login page
        if "facebook.com" not in driver.current_url:
            driver.get("https://www.facebook.com")
            time.sleep(3)
            
        # Find and fill email field
        email_field = driver.find_element(By.ID, "email")
        email_field.clear()  # Clear any existing text
        email_field.send_keys(email)
        
        # Find and fill password field
        password_field = driver.find_element(By.ID, "pass")
        password_field.clear()  # Clear any existing text
        password_field.send_keys(password)
        
        # Submit the form
        password_field.send_keys(Keys.RETURN)
        
        # Wait for login to process
        time.sleep(10)
        
        # Check for CAPTCHA or 2FA
        if "checkpoint" in driver.current_url.lower() or "encrypted_context" in driver.current_url.lower():
            print("CAPTCHA or Two-Factor Authentication detected.")
            print("Please complete the verification manually in the browser window.")
            input("After completing verification, press Enter to continue...")
            time.sleep(5)
            
        return True
    except Exception as e:
        print(f"Login error: {str(e)}")
        return False

if __name__ == "__main__":
    main()
