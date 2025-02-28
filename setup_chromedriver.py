import os
import sys
import json
import urllib.request
import zipfile
import subprocess
import re
from packaging import version

def get_chrome_version():
    """Get the installed Chrome version."""
    try:
        # For Windows
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Google\Chrome\BLBeacon")
        chrome_version = winreg.QueryValueEx(key, "version")[0]
        return chrome_version
    except Exception as e:
        print(f"Error getting Chrome version: {e}")
        return None

def get_chromedriver_version(chrome_version):
    """Get the appropriate ChromeDriver version for the installed Chrome."""
    try:
        # Get major version
        major_version = chrome_version.split('.')[0]
        
        # Get ChromeDriver versions list
        url = "https://googlechromelabs.github.io/chrome-for-testing/known-good-versions-with-downloads.json"
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read())
        
        # Find matching version
        matching_version = None
        for version_data in data['versions']:
            if version_data['version'].startswith(f"{major_version}."):
                matching_version = version_data
                break
                
        if matching_version:
            return matching_version
        return None
    except Exception as e:
        print(f"Error getting ChromeDriver version: {e}")
        return None

def download_chromedriver(version_data):
    """Download and extract ChromeDriver."""
    try:
        # Find Windows download URL
        download_url = None
        for download in version_data['downloads'].get('chromedriver', []):
            if download['platform'] == 'win64':
                download_url = download['url']
                break
        
        if not download_url:
            print("Could not find ChromeDriver download URL")
            return False
            
        print(f"Downloading ChromeDriver version {version_data['version']}...")
        
        # Download the zip file
        zip_path = "chromedriver_win64.zip"
        urllib.request.urlretrieve(download_url, zip_path)
        
        # Extract the zip file
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall()
            
        # Move chromedriver.exe to current directory
        os.rename(os.path.join("chromedriver-win64", "chromedriver.exe"), "chromedriver.exe")
        
        # Clean up
        os.remove(zip_path)
        import shutil
        shutil.rmtree("chromedriver-win64")
        
        print("ChromeDriver downloaded and extracted successfully!")
        return True
    except Exception as e:
        print(f"Error downloading ChromeDriver: {e}")
        return False

def main():
    print("Setting up ChromeDriver...")
    
    # Get Chrome version
    chrome_version = get_chrome_version()
    if not chrome_version:
        print("Could not detect Chrome version. Please make sure Google Chrome is installed.")
        return False
    
    print(f"Detected Chrome version: {chrome_version}")
    
    # Get matching ChromeDriver version
    version_data = get_chromedriver_version(chrome_version)
    if not version_data:
        print("Could not find matching ChromeDriver version.")
        return False
    
    # Download and extract ChromeDriver
    success = download_chromedriver(version_data)
    
    if success:
        print("\nSetup completed successfully!")
        print("You can now run the Facebook Messenger Bot.")
    else:
        print("\nSetup failed. Please try again or download ChromeDriver manually.")
    
    return success

if __name__ == "__main__":
    main() 