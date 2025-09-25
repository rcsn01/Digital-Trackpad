# Development Environment Setup and Installation Guide

## 📋 System Requirements

### Hardware Requirements

```
Minimum Configuration:
├── CPU: Dual-core processor 1.6 GHz or higher
├── RAM: 4GB (8GB recommended)
├── Storage: 2GB available space
├── Network: Wi-Fi or Ethernet connection
└── Display: 1024x768 resolution or higher

Recommended Configuration:
├── CPU: Quad-core processor 2.5 GHz or higher
├── RAM: 8GB (16GB for development)
├── Storage: 10GB available space (SSD recommended)
├── Network: Stable broadband connection
└── Display: 1920x1080 resolution or higher
```

### Software Requirements

#### Operating System Support

```
Windows:
├── Windows 10 (version 1903 or later)
├── Windows 11 (all versions)
├── Windows Server 2019/2022
└── Both x64 and ARM64 architectures

macOS:
├── macOS 10.15 (Catalina) or later
├── Apple Silicon (M1/M2) and Intel processors
└── Latest security updates recommended

Linux:
├── Ubuntu 18.04 LTS or later
├── Debian 10 or later
├── CentOS 8 or later
├── Fedora 32 or later
└── Other modern distributions
```

#### Runtime Environment

```
Python:
├── Version: 3.8 or later (3.11+ recommended)
├── pip package manager
├── virtual environment support
└── pip-tools for dependency management

Node.js:
├── Version: 16.x LTS or later (18.x+ recommended)
├── npm or yarn package manager
├── nvm for version management (optional)
└── Build tools (node-gyp)

Network:
├── Local network access (192.168.x.x)
├── Port 5000 (default) available
├── Firewall configuration may be required
└── Wi-Fi Direct support (optional)
```

---

## 🚀 Development Environment Setup

### Step 1: Install UV Package Manager

UV is a fast Python package manager that significantly improves dependency resolution and installation speed.

#### Windows Installation

```powershell
# Install UV using PowerShell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Verify installation
uv --version

# Add to PATH if needed (usually automatic)
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
```

#### macOS Installation

```bash
# Install UV using Homebrew
brew install uv

# Or install directly
curl -LsSf https://astral.sh/uv/install.sh | sh

# Verify installation
uv --version
```

#### Linux Installation

```bash
# Install UV using the install script
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or using package managers (where available)
# Ubuntu/Debian: apt install uv (if available)
# Fedora: dnf install uv (if available)

# Verify installation
uv --version
```

### Step 2: Clone Project Repository

```bash
# Clone the project to your local machine
git clone https://github.com/yourusername/Digital-Trackpad.git

# Navigate to project directory
cd Digital-Trackpad

# List project contents
ls -la  # Linux/macOS
dir     # Windows
```

### Step 3: Create Virtual Environment

```bash
# Create virtual environment using UV
uv venv

# Activate virtual environment
# Windows:
.venv\Scripts\activate

# macOS/Linux:
source .venv/bin/activate

# Verify activation (should show virtual environment path)
which python
python --version
```

### Step 4: Install Dependencies

```bash
# Install all project dependencies
uv pip install -r requirements.txt

# Or install directly from pyproject.toml if available
uv pip install -e .

# Verify installation
python -c "import flask; print(f'Flask version: {flask.__version__}')"
python -c "import flask_socketio; print(f'Flask-SocketIO version: {flask_socketio.__version__}')"
```

### Step 5: Verify Installation

```bash
# Run basic functionality test
python -c "
import flask
import flask_socketio
import socket
print('✅ All core dependencies installed successfully')
print(f'✅ Flask: {flask.__version__}')
print(f'✅ Flask-SocketIO: {flask_socketio.__version__}')
print(f'✅ Python: {flask.sys.version}')
"
```

---

## 📱 Application Startup

### Method 1: Direct Python Execution

```bash
# Ensure virtual environment is activated
# Navigate to project root directory

# Run the application
python app.py

# Or with specific configuration
python app.py --host=0.0.0.0 --port=5000 --debug
```

### Method 2: Using Environment Variables

```bash
# Set environment variables (Windows)
set FLASK_APP=app.py
set FLASK_ENV=development
set FLASK_DEBUG=1
set SECRET_KEY=your-secret-key-here

# Set environment variables (macOS/Linux)
export FLASK_APP=app.py
export FLASK_ENV=development
export FLASK_DEBUG=1
export SECRET_KEY=your-secret-key-here

# Run Flask application
flask run --host=0.0.0.0 --port=5000
```

### Method 3: Production Deployment

```bash
# Use production-grade WSGI server
pip install gunicorn

# Run with Gunicorn (Unix systems)
gunicorn -w 4 -b 0.0.0.0:5000 app:app

# Or use Waitress (Windows)
pip install waitress
waitress-serve --port=5000 app:app
```

---

## 🌐 Post-Startup Information

### Application Information

```
Default Configuration:
├── Local Access: http://localhost:5000
├── Network Access: http://your-ip:5000
├── Debug Mode: Enabled (development)
├── Auto-reload: Active
└── CORS: Enabled for all origins

Connection Information:
├── Server: Flask development server
├── WebSocket: Flask-SocketIO
├── Real-time: Socket.IO client
└── Static Files: /static directory
```

### Access Methods

#### Local Access

```
# Open browser and navigate to
http://localhost:5000

# Or use IP address
http://127.0.0.1:5000
```

#### Network Access

```bash
# Find your local IP address
# Windows:
ipconfig

# macOS/Linux:
ifconfig  # or 'ip addr'

# Access from other devices
http://YOUR_LOCAL_IP:5000
# Example: http://192.168.1.100:5000
```

#### Mobile Device Access

```
# Connect to same Wi-Fi network
# Open browser on phone/tablet
# Enter computer's IP address
http://192.168.x.x:5000

# Or use QR code generator
# Install: pip install qrcode
# Generate QR code for easy mobile access
```

---

## 🛠️ Development Features

### Core Functionality

```
Touchpad Mode:
├── Multi-touch gesture support
├── Real-time cursor control
├── Click and scroll simulation
├── Customizable sensitivity
└── Touch feedback visualization

Media Control Mode:
├── Play/Pause functionality
├── Volume up/down control
├── Next/Previous track
├── Mute toggle
└── Media player detection

Presentation Mode:
├── Slide navigation (Next/Previous)
├── Laser pointer simulation
├── Screen annotation tools
├── Timer and notes display
└── Presentation mode detection

Application Control:
├── Window management
├── Application switching
├── Custom hotkey support
├── Macro recording
└── Quick launch shortcuts
```

### Advanced Features

```
Multi-Device Support:
├── Connect up to 10 devices simultaneously
├── Device identification and naming
├── Session management
├── Cross-device synchronization
└── Device-specific configurations

Security Features:
├── Local network encryption
├── Session token management
├── CORS protection
├── Rate limiting
└── Input validation

Customization Options:
├── Theme selection (Light/Dark)
├── Gesture sensitivity adjustment
├── Button mapping configuration
├── Custom CSS injection
└── Personalization settings
```

---

## 🧪 Development Testing

### Test Files

```
Available Test Files:
├── basic_test.html          # Basic functionality test
├── performance_test.html    # Performance benchmark
├── mobile_test.html        # Mobile device compatibility
├── stress_test.html        # Load testing
└── integration_test.html   # Full integration test
```

### Running Tests

```bash
# Run basic functionality test
python -m http.server 8080
# Open: http://localhost:8080/basic_test.html

# Run performance test
python performance_test.py

# Run unit tests
python -m pytest tests/

# Run integration tests
python integration_test.py
```

### Manual Testing

```bash
# Test touchpad functionality
# 1. Open http://localhost:5000
# 2. Switch to Touchpad mode
# 3. Test cursor movement
# 4. Test click and scroll

# Test media controls
# 1. Open media player
# 2. Switch to Media mode
# 3. Test play/pause
# 4. Test volume controls

# Test presentation mode
# 1. Open presentation software
# 2. Switch to Presentation mode
# 3. Test slide navigation
```

---

## ⚠️ Common Issues and Solutions

### Installation Issues

#### UV Installation Fails

```bash
# Solution 1: Use alternative installation method
curl -LsSf https://astral.sh/uv/install.sh | sh

# Solution 2: Install via pip (fallback)
pip install uv

# Solution 3: Use traditional pip for dependencies
pip install -r requirements.txt
```

#### Virtual Environment Creation Issues

```bash
# Problem: Permission denied
# Solution: Use --system-site-packages flag
uv venv --system-site-packages

# Problem: Space in path
# Solution: Use short path or move project
# Windows: Move to C:\projects\
# macOS/Linux: Move to /home/user/projects/
```

#### Dependency Installation Issues

```bash
# Problem: Package not found
# Solution: Update pip and try again
uv pip install --upgrade pip
uv pip install -r requirements.txt

# Problem: Compilation errors
# Solution: Install build tools
# Windows: Install Visual Studio Build Tools
# macOS: Install Xcode command line tools
# Linux: Install build-essential package
```

### Runtime Issues

#### Port Already in Use

```bash
# Find process using port 5000
# Windows:
netstat -ano | findstr :5000
taskkill /PID <PID> /F

# macOS/Linux:
lsof -i :5000
kill -9 <PID>

# Or use different port
python app.py --port 5001
```

#### Firewall Blocking

```bash
# Windows Firewall
# 1. Open Windows Defender Firewall
# 2. Click "Allow an app through firewall"
# 3. Add Python and your application

# macOS Firewall
# 1. System Preferences > Security & Privacy
# 2. Click Firewall tab
# 3. Add Python to allowed applications

# Linux (iptables)
sudo iptables -A INPUT -p tcp --dport 5000 -j ACCEPT
```

#### Mobile Device Connection Issues

```
Problem: Cannot connect from mobile device
Solutions:
1. Ensure both devices on same Wi-Fi network
2. Check firewall settings on computer
3. Verify IP address is correct
4. Try disabling mobile data
5. Restart Wi-Fi on both devices
6. Check router AP isolation settings
```

#### WebSocket Connection Issues

```bash
# Check browser console for errors
# Common issues:
# 1. CORS policy - Check ALLOWED_ORIGINS setting
# 2. Mixed content - Use HTTPS or disable browser security
# 3. Firewall blocking WebSocket - Open port for WebSocket

# Debug with browser developer tools
# 1. Open F12 developer tools
# 2. Check Network tab for WebSocket connections
# 3. Check Console tab for JavaScript errors
```

---

## 📁 Project Structure

```
Digital-Trackpad/
├── app.py                    # Main Flask application
├── requirements.txt          # Python dependencies
├── pyproject.toml           # Project configuration
├── templates/               # HTML templates
│   ├── index.html          # Main application interface
│   └── error.html          # Error pages
├── static/                  # Static assets
│   ├── css/                # Stylesheets
│   ├── js/                 # JavaScript files
│   │   └── script.js       # Main application logic
│   └── images/             # Image assets
├── tests/                   # Test files
│   ├── basic_test.html     # Basic functionality tests
│   ├── performance_test.py # Performance benchmarks
│   └── integration_test.py # Integration tests
├── docs/                    # Documentation
│   ├── README.md           # Project documentation
│   └── setup_guide.md      # This file
├── config/                  # Configuration files
│   ├── settings.py         # Application settings
│   └── logging.py          # Logging configuration
└── utils/                   # Utility modules
    ├── network.py          # Network utilities
    └── security.py         # Security functions
```

---

## ⚠️ Important Notes

### Security Considerations

```
Development Environment:
├── Debug mode enabled (never use in production)
├── CORS enabled for all origins (development only)
├── No authentication required (local network)
├── Verbose error messages enabled
└── Auto-reload active for development

Production Deployment:
├── Disable debug mode
├── Configure proper CORS origins
├── Implement authentication
├── Use HTTPS encryption
├── Set up rate limiting
└── Configure proper logging
```

### Performance Optimization

```
Development Optimizations:
├── Use UV for faster dependency management
├── Enable browser caching for static assets
├── Minimize JavaScript and CSS files
├── Optimize image assets
└── Use CDN for external libraries

Production Optimizations:
├── Use production WSGI server
├── Enable gzip compression
├── Set up proper caching headers
├── Use database connection pooling
├── Implement load balancing
└── Monitor performance metrics
```

### Development Best Practices

```
Code Quality:
├── Follow PEP 8 style guidelines
├── Use type hints for functions
├── Write comprehensive docstrings
├── Implement proper error handling
├── Add unit tests for new features
└── Use meaningful variable names

Git Workflow:
├── Use feature branches
├── Write descriptive commit messages
├── Keep commits atomic
├── Review code before merging
├── Tag stable releases
└── Maintain clean commit history
```

---

## 📞 Support and Resources

### Documentation

```
Available Resources:
├── README.md              # Project overview
├── API documentation      # API reference
├── User guide            # User documentation
├── Developer guide       # Development documentation
└── Troubleshooting guide # Common issues
```

### Community Support

```
Support Channels:
├── GitHub Issues         # Bug reports and feature requests
├── Discussion forum    # Community discussions
├── Discord server      # Real-time chat support
├── Stack Overflow      # Technical questions
└── Email support       # Direct support contact
```

### Development Tools

```
Recommended Tools:
├── Visual Studio Code    # Code editor
├── PyCharm              # Python IDE
├── Postman              # API testing
├── Chrome DevTools      # Web debugging
├── Git                  # Version control
└── Docker               # Containerization
```

---

## 🔄 Updates and Maintenance

### Regular Updates

```bash
# Update dependencies
uv pip install --upgrade -r requirements.txt

# Update UV itself
uv self update

# Check for security updates
pip-audit  # Install with: pip install pip-audit

# Update project structure
git pull origin main
```

### Version Management

```bash
# Check current version
git describe --tags

# Create new version
git tag -a v1.0.0 -m "Release version 1.0.0"
git push origin v1.0.0

# Update changelog
# Edit CHANGELOG.md with new features and fixes
```

---

*Guide last updated: September 25, 2025*  
*Compatibility: Digital-Trackpad v1.0.0+*  
*Maintained by: Development Team*