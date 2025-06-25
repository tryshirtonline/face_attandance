# Employee Attendance System

## Overview

This is a Flask-based employee attendance management system with face recognition capabilities. The system supports role-based access control with superusers managing the entire system and supervisors managing their assigned teams. Employee attendance is tracked through facial recognition with anti-spoofing measures and geolocation verification.

## System Architecture

### Backend Architecture
- **Framework**: Flask with SQLAlchemy ORM
- **Database**: PostgreSQL (configured via DATABASE_URL environment variable)
- **Authentication**: Flask-Login for session management
- **File Handling**: Werkzeug for secure file uploads

### Frontend Architecture
- **Template Engine**: Jinja2 with Flask
- **CSS Framework**: Bootstrap (dark theme)
- **Icons**: Font Awesome
- **JavaScript**: Vanilla JS for face capture and geolocation

### Face Recognition System
- **Libraries**: face_recognition, OpenCV, MediaPipe
- **Anti-spoofing**: Eye blink detection using MediaPipe Face Mesh
- **Processing**: Real-time face detection and encoding storage

## Key Components

### User Management
- **User Model**: Supports superuser and supervisor roles
- **Authentication**: Username/password login with role-based access control
- **Company Profile**: Configurable company branding and information

### Job Hierarchy
- **JobCategory**: Top-level job classifications created by superusers
- **JobTitle**: Specific positions within categories
- **Assignment**: Supervisors can be assigned to specific categories

### Employee Management
- **Employee Registration**: Face capture during onboarding with validation
- **Supervisor Assignment**: Employees are assigned to supervisors
- **Face Encoding Storage**: Binary face encodings stored in database

### Attendance System
- **Face Recognition**: Real-time face matching for attendance marking
- **Anti-spoofing**: Blink detection to prevent photo attacks
- **Geolocation**: GPS coordinates captured for location verification
- **Time Tracking**: Automatic timestamp recording

### Reporting System
- **Report Generation**: PDF and Excel reports with filtering options
- **Data Export**: Attendance data export capabilities
- **Role-based Access**: Different report views for superusers vs supervisors

### API Integration
- **REST API**: Endpoints for external .NET system integration
- **Employee Data**: JSON endpoints for employee information
- **Attendance Data**: Daily attendance record synchronization

## Data Flow

1. **Employee Registration**:
   - Supervisor captures employee face during registration
   - Face encoding is generated and stored
   - Employee assigned to supervisor and job title

2. **Attendance Marking**:
   - Employee approaches attendance terminal
   - Camera captures face image
   - Blink detection validates liveness
   - Face matching identifies employee
   - Geolocation coordinates recorded
   - Attendance record saved with timestamp

3. **Report Generation**:
   - Users request reports with filters
   - System queries attendance data
   - Reports generated in PDF/Excel format
   - Data formatted based on user role permissions

4. **External API Sync**:
   - .NET system calls daily API endpoints
   - Employee and attendance data synchronized
   - JSON responses with structured data

## External Dependencies

### Python Packages
- **Flask Stack**: flask, flask-sqlalchemy, flask-login
- **Database**: psycopg2-binary for PostgreSQL connectivity
- **Face Recognition**: face_recognition, opencv-python, mediapipe
- **Reports**: reportlab, pandas for document generation
- **HTTP**: gunicorn for production deployment

### JavaScript Libraries
- **Bootstrap**: UI framework and components
- **Font Awesome**: Icon library
- **MediaDevices API**: Camera access for face capture
- **Geolocation API**: GPS coordinate acquisition

### System Dependencies
- **PostgreSQL**: Primary data storage
- **Camera Hardware**: For face capture functionality
- **SSL/TLS**: Secure HTTPS for camera access

## Deployment Strategy

### Development Environment
- **Runtime**: Python 3.11 with Nix package management
- **Server**: Flask development server with debug mode
- **Database**: PostgreSQL with connection pooling

### Production Environment
- **Server**: Gunicorn WSGI server on port 5000
- **Deployment**: Replit autoscale deployment target
- **Process Management**: Parallel workflow execution
- **File Storage**: Local uploads directory for company logos

### Configuration
- **Environment Variables**: DATABASE_URL, SESSION_SECRET
- **File Limits**: 16MB maximum upload size
- **Security**: ProxyFix middleware for proper header handling

## Recent Changes
- June 25, 2025: Successfully migrated from Replit Agent to Replit environment
  - Configured PostgreSQL database with proper environment variables
  - Fixed syntax errors in routes.py for clean application startup
  - Improved face recognition algorithm with multiple similarity metrics
  - Enhanced anti-spoofing with better blink detection patterns
  - Added comprehensive security alerts for unauthorized access attempts
  - Face matching: Improved accuracy using cosine similarity, euclidean distance, and correlation
  - Security notifications: Real-time alerts for spoofing attempts and unauthorized access
  - Application fully operational with enhanced security features

## Changelog
- June 25, 2025: Initial setup and debugging

## User Preferences

Preferred communication style: Simple, everyday language.