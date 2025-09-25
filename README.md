# Phone Trackpad - Web-based Mouse Control

Transform your phone into a wireless trackpad for your PC! This web application allows you to control your computer's mouse cursor and perform clicks using your phone's touchscreen.

## Features

- **Mouse Movement**: Use one finger to move the cursor
- **Two-Finger Scrolling**: Natural scrolling with two fingers
- **Click Controls**: Left, right, and middle click buttons
- **Adjustable Sensitivity**: Customize cursor and scroll sensitivity
- **Drag Mode**: Enable dragging functionality
- **Mobile Optimized**: Responsive design for phone screens
- **LAN Access**: Access from any device on your local network

## Setup Instructions

### 1. Install Python Dependencies

First, make sure you have Python 3.7+ installed on your PC. Then install the required packages:

```bash
pip install -r requirements.txt
```

### 2. Run the Server

Start the Flask server:

```bash
python app.py
```

The server will start and display your local IP address. You'll see output like:

```
Starting trackpad server...
Access from your phone at: http://192.168.1.100:51273
Or access locally at: http://localhost:51273
Screen size detected: 1920x1080
```

## Multi-monitor support

The server now supports multiple monitors on Windows by using the system's virtual
screen bounds. This means the cursor should be able to move across all connected
displays (including monitors positioned to the left of the primary) instead of
being clamped to the primary monitor.

Notes and testing:
- On Windows the server queries the virtual screen using the Win32
	GetSystemMetrics API so no additional configuration is required.
- On other platforms the server currently falls back to the primary monitor
	dimensions reported by PyAutoGUI.
- To test: run the server, open the trackpad page on your phone or another
	device, and move the pointer toward the edges of your setup. The cursor
	should travel onto other monitors if your OS reports them in the virtual
	screen area.

If you find the cursor still cannot move across monitors, please confirm your
OS exposes the extended desktop as a single virtual screen (common on Windows)
and share the output of the server startup message which prints the detected
virtual screen bounds.

### 3. Connect Your Phone

1. Make sure your phone is connected to the same Wi-Fi network as your PC
2. Open your phone's web browser
3. Navigate to the IP address shown in the terminal (e.g., `http://192.168.1.100:5000`)
4. Add the page to your home screen for easy access

## How to Use

### Basic Controls
- **Move Cursor**: Drag one finger on the trackpad area
- **Left Click**: Tap once on the trackpad area
- **Right Click**: Use the "Right Click" button
- **Middle Click**: Use the "Middle Click" button
- **Scroll**: Use two fingers and drag up/down or left/right

### Advanced Features
- **Drag Mode**: Toggle the "Drag Mode" button to enable click-and-drag functionality
- **Sensitivity**: Adjust cursor movement sensitivity with the slider
- **Scroll Sensitivity**: Adjust scrolling speed with the slider

### Visual Feedback
- Status indicator shows current action (Ready, Moving cursor, Scrolling, etc.)
- Touch feedback circles appear where you tap
- Active buttons are highlighted

## Troubleshooting

### Connection Issues
- Ensure both devices are on the same Wi-Fi network
- Check Windows Firewall settings - you may need to allow Python through the firewall
- Try accessing `http://localhost:5000` directly on your PC to test the server

### Performance Issues
- Reduce sensitivity if cursor movement is too fast
- Close other applications to improve responsiveness
- Ensure good Wi-Fi signal strength

### PyAutoGUI Issues
- PyAutoGUI has a fail-safe feature - move your mouse to the top-left corner to stop all actions
- On some systems, you may need to run the script as administrator
- Make sure your screen is not locked when using the trackpad

## Security Note

This application runs a web server accessible on your local network. Only use on trusted networks. The server runs in debug mode by default for development - disable debug mode in production environments.

## Customization

You can modify the following in `app.py`:
- `sensitivity` variable to change default mouse sensitivity
- Port number (default: 5000)
- PyAutogui settings and delays

The web interface can be customized by editing the HTML, CSS, and JavaScript files in the `templates` and `static` directories.

## System Requirements

- Python 3.7+
- Windows, macOS, or Linux
- Wi-Fi network
- Modern web browser on phone (Chrome, Safari, Firefox, etc.)

## License

This project is open source and available under the MIT License.