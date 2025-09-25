# Universal PC Remote - User Guide

## 🎯 Project Overview

This is a web-based PC remote control application that allows you to remotely control your Windows computer through your phone or tablet.

## ✨ Main Features

### 1. Trackpad Control
- **Mouse Movement**: Swipe on the touch area to control the mouse cursor
- **Left Click**: Single finger tap
- **Right Click**: Two-finger tap
- **Scrolling**: Two-finger swipe

### 2. Media Control
- Play/Pause ⏯️
- Previous/Next ⏮️⏭️
- Volume Adjustment 🔊🔉
- Mute 🔇

### 3. Presentation Control
- Previous/Next Page ⬅️➡️
- Start Presentation ▶️
- End Presentation ⏹️

### 4. Application Control
- Open Chrome 🌐
- Open Notepad 📝
- Open Calculator 🧮
- Open File Explorer 📁

### 5. System Control
- System Sleep 😴
- Shutdown 🔄
- Restart 🔄
- Show Desktop 🖥️
- Switch Window 🔄
- Lock Computer 🔒

### 6. Keyboard Input
- Text input
- Shortcut key sending

### 7. Custom Buttons (New Feature) 🎛️
- Create personalized shortcut buttons
- Support multiple control types
- Save and load configurations

## 🚀 Quick Start

### Installation Requirements
- Python 3.7+
- Windows operating system

### Installation Steps
1. Install Python dependencies:
```bash
pip install flask flask-socketio pyautogui
```

2. Run the application:
```bash
python app.py
```

3. Open browser and navigate to:
```
http://localhost:5000
```

### Network Access
If you want to access from other devices:
```
http://[Your IP Address]:5000
```

## 📱 Usage Instructions

### Basic Operation
1. **Connect to Server**: Ensure your phone and computer are on the same network
2. **Select Control Mode**: Click the mode buttons at the top to switch between different functions
3. **Use Control Features**: Use the corresponding control buttons according to the selected mode

### Custom Button Settings
1. Click the "Custom Button Settings" button on the main page
2. Choose preset templates or create new buttons
3. Set button name, icon, and function
4. Save configuration and return to main page to use

## 🔧 Technical Architecture

### Backend
- **Flask**: Web framework
- **Flask-SocketIO**: Real-time bidirectional communication
- **PyAutoGUI**: System control automation

### Frontend
- **HTML5/CSS3**: Responsive interface
- **JavaScript**: Interactive logic
- **Socket.IO**: Real-time communication

### Supported Browsers
- Chrome/Chromium
- Firefox
- Safari
- Edge

## ⚠️ Security Tips

1. **Network Security**: Only use in trusted network environments
2. **Firewall**: Ensure firewall allows required ports
3. **Permissions**: Some features may require administrator privileges

## 🐛 Troubleshooting

### Connection Issues
- Check firewall settings
- Confirm IP address is correct
- Ensure port 5000 is not occupied

### Function Issues
- Check if Python dependencies are fully installed
- Confirm Windows permission settings
- Check console error messages

## 📞 Support

For issues, please check console error messages or view application logs.

## 📝 Version History

- v1.0.0: Basic functionality completed
  - Trackpad control
  - Media control
  - Presentation control
  - Application control
  - System control
  - Keyboard input
  - Custom button feature

---

**Enjoy your Universal PC Remote experience!** 🎉