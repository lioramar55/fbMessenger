# Facebook Group Messenger Bot

A powerful desktop application that automates sending personalized messages to Facebook profiles from a CSV list. The application features a user-friendly GUI, secure credential management, and robust error handling.

## Features

- **User-friendly GUI**: Easy-to-use interface with message editor, profile list management, and progress tracking
- **Secure Credential Management**: Safely stores Facebook login credentials in a local database
- **Session Management**: Saves login sessions to minimize the need for repeated logins
- **CAPTCHA Handling**: Detects security verifications and guides users through the process
- **Message History**: Tracks message status and prevents duplicate messages
- **Customizable Delays**: Set minimum and maximum wait times between messages to avoid detection
- **Progress Tracking**: Real-time logs and history view of messaging activities

## Getting Started

### For End Users

1. Download the executable from the releases section
2. Create a `members.csv` file with a column named "Profile Link" containing Facebook profile URLs
3. Run the application and follow these steps:
   - Enter your Facebook credentials
   - Type or paste your message in the message editor
   - Select your CSV file using the Browse button
   - Adjust wait times if needed (default: 15-30 seconds)
   - Click Start to begin the messaging process

### Handling Security Verifications

If Facebook requires a security verification (CAPTCHA or 2FA):

1. The application will detect this and show a notification
2. Complete the verification in the browser window that appears
3. Click the "Continue After Verification" button to resume

## For Developers

### Setup

1. Install Python 3.8 or higher
2. Install dependencies:

```bash
pip install -r requirements.txt
```

### Project Structure

- `gui.py`: Main application with GUI implementation
- `main.py`: Core Facebook messaging functionality
- `database.py`: Database management for settings, history, and cookies
- `build.bat`: Script to build the executable

### Building the Executable

```bash
build.bat
```

The executable will be created in the `dist` folder.

## Security Notice

- All credentials are stored locally in an SQLite database
- Cookies are securely stored in the database rather than in files
- Use at your own risk - automated messaging may violate Facebook's terms of service
- Recommended to use with reasonable delays between messages to avoid detection
