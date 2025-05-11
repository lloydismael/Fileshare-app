# File Share Application

A simple Flask-based file sharing application with QR code generation capability.

## Version
Current version: v1.5

### Changelog
- v1.5: Added WebRTC P2P file sharing capabilities
  - Implemented WebRTC peer connections
  - Added real-time connection status notifications
  - Enhanced UI with loading indicators
  - Added toast notifications for connection events
  - Improved file sharing security with P2P transfer
- v1.3: Enhanced UI with Azure theme and animations
  - Added modern glass-morphism design
  - Implemented smooth animations
  - Improved button and input styles
  - Added Azure color scheme
  - Enhanced mobile responsiveness

## Features

- File upload functionality
- QR code generation for easy sharing
- Docker support
- Simple and responsive UI

## Quick Start

### Running with Docker

1. Build the Docker image:
```bash
docker build -t fileshare-app .
```

2. Run the container:
```bash
docker run -d -p 5000:5000 -v ./uploads:/app/uploads --name fileshare fileshare-app
```

3. Access the application at http://localhost:5000

### Running Locally

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the application:
```bash
python -m flask run
```

## Environment Variables

- `FLASK_APP`: Set to fileshare.py
- `FLASK_ENV`: Set to production in Docker, development for local development

## License

MIT License
