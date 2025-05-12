# Changelog

All notable changes to the Fileshare App project will be documented in this file.

## [Version 2.0] - 2025-05-12

### Added
- Implemented WebRTC data channel support for P2P file sharing
- Added direct peer-to-peer file transfer capability
- Introduced chunk-based file transfer system
- Added file transfer progress tracking
- Implemented WebRTC signaling system
- Added support for multiple simultaneous transfers

### Fixed
- Improved connection stability with ICE candidate handling
- Enhanced peer connection management
- Fixed user joining issues with better state management

### Changed
- Updated connection system to prioritize WebRTC
- Enhanced room management with better user tracking
- Improved logging system for better debugging
- Added transfer mode selection (WebRTC/Socket fallback)

## [Version 1.9] - 2025-05-12

### Added
- Implemented proper eventlet server initialization
- Added robust WebSocket connection handling
- Optimized application startup sequence

### Fixed
- Fixed WebSocket connection issues in Docker environment
- Corrected eventlet monkey patching timing
- Resolved server startup configuration issues

### Changed
- Updated Docker container to use eventlet server directly
- Modified server startup sequence for better stability
- Streamlined logging configuration

## [Version 1.8] - 2025-05-12

### Added
- Improved room joining flow with proper connection request handling
- Added better WebSocket connection management
- Implemented proper event logging
- Added connection state tracking and feedback

### Fixed
- Fixed UI alignment issues with boxes and containers
- Fixed QR code centering in containers
- Improved error handling and user feedback
- Fixed WebRTC connection issues

### Changed
- Updated WebSocket configuration for better stability
- Improved status message clarity
- Enhanced connection request/response flow

## [Version 1.7] - 2025-05-12

### Added
- Connection request prompt for room joining
- Accept/Decline functionality for room hosts
- Improved WebRTC connection handling

### Fixed
- Fixed connection state management
- Improved error handling
- Fixed UI layout issues

### Changed
- Updated room joining workflow
- Enhanced user feedback system

## [Version 1.6] - 2025-05-11

### Added
- Implemented peer-to-peer file sharing
- Added WebRTC data channel support
- Real-time file transfer progress

### Fixed
- Fixed room connection issues
- Improved error handling for file transfers
- Fixed UI responsiveness

### Changed
- Updated WebRTC implementation
- Enhanced file transfer security

## [Version 1.4] - 2025-05-10

### Added
- QR code generation for room sharing
- Room management system
- Real-time connection status

### Fixed
- Fixed room creation issues
- Improved QR code reliability
- Enhanced room security

### Changed
- Updated room sharing mechanism
- Improved room state management

## [Version 1.2] - 2025-05-09

### Added
- Basic room creation functionality
- File upload support
- QR code for file sharing

### Fixed
- Fixed file upload issues
- Improved error handling
- Enhanced security measures

### Changed
- Updated file handling system
- Improved upload success feedback
