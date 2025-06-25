class GeoLocation {
    constructor(statusElementId) {
        this.statusElement = document.getElementById(statusElementId);
        this.latitude = null;
        this.longitude = null;
        this.accuracy = null;
        this.timestamp = null;
        
        this.options = {
            enableHighAccuracy: true,
            timeout: 10000,
            maximumAge: 300000 // 5 minutes
        };
    }
    
    async getCurrentLocation() {
        return new Promise((resolve, reject) => {
            if (!navigator.geolocation) {
                this.updateStatus('Geolocation is not supported by this browser', 'error');
                reject(new Error('Geolocation not supported'));
                return;
            }
            
            this.updateStatus('Getting your location...', 'info');
            
            navigator.geolocation.getCurrentPosition(
                (position) => {
                    this.latitude = position.coords.latitude;
                    this.longitude = position.coords.longitude;
                    this.accuracy = position.coords.accuracy;
                    this.timestamp = position.timestamp;
                    
                    this.updateStatus(
                        `Location acquired (±${Math.round(this.accuracy)}m accuracy)`, 
                        'success'
                    );
                    
                    resolve({
                        latitude: this.latitude,
                        longitude: this.longitude,
                        accuracy: this.accuracy,
                        timestamp: this.timestamp
                    });
                },
                (error) => {
                    this.handleLocationError(error);
                    reject(error);
                },
                this.options
            );
        });
    }
    
    watchLocation() {
        if (!navigator.geolocation) {
            this.updateStatus('Geolocation is not supported by this browser', 'error');
            return null;
        }
        
        return navigator.geolocation.watchPosition(
            (position) => {
                this.latitude = position.coords.latitude;
                this.longitude = position.coords.longitude;
                this.accuracy = position.coords.accuracy;
                this.timestamp = position.timestamp;
                
                this.updateStatus(
                    `Location updated (±${Math.round(this.accuracy)}m accuracy)`, 
                    'success'
                );
            },
            (error) => {
                this.handleLocationError(error);
            },
            this.options
        );
    }
    
    handleLocationError(error) {
        let message = 'Unknown location error';
        let type = 'error';
        
        switch (error.code) {
            case error.PERMISSION_DENIED:
                message = 'Location access denied by user';
                type = 'warning';
                break;
            case error.POSITION_UNAVAILABLE:
                message = 'Location information unavailable';
                type = 'warning';
                break;
            case error.TIMEOUT:
                message = 'Location request timed out';
                type = 'warning';
                break;
            default:
                message = `Location error: ${error.message}`;
                break;
        }
        
        this.updateStatus(message, type);
    }
    
    updateStatus(message, type = 'info') {
        if (!this.statusElement) return;
        
        const icon = this.getIconForType(type);
        this.statusElement.innerHTML = `${icon} ${message}`;
        
        // Remove existing classes
        this.statusElement.classList.remove('text-success', 'text-warning', 'text-danger', 'text-info');
        
        // Add appropriate class
        switch (type) {
            case 'success':
                this.statusElement.classList.add('text-success');
                break;
            case 'warning':
                this.statusElement.classList.add('text-warning');
                break;
            case 'error':
                this.statusElement.classList.add('text-danger');
                break;
            default:
                this.statusElement.classList.add('text-info');
        }
    }
    
    getIconForType(type) {
        switch (type) {
            case 'success':
                return '<i class="fas fa-check-circle"></i>';
            case 'warning':
                return '<i class="fas fa-exclamation-triangle"></i>';
            case 'error':
                return '<i class="fas fa-times-circle"></i>';
            default:
                return '<i class="fas fa-map-marker-alt"></i>';
        }
    }
    
    getLocationString() {
        if (this.latitude && this.longitude) {
            return `${this.latitude.toFixed(6)}, ${this.longitude.toFixed(6)}`;
        }
        return 'Location not available';
    }
    
    getAccuracyString() {
        if (this.accuracy) {
            return `±${Math.round(this.accuracy)}m`;
        }
        return 'Unknown accuracy';
    }
    
    getTimestampString() {
        if (this.timestamp) {
            return new Date(this.timestamp).toLocaleString();
        }
        return 'Unknown time';
    }
    
    async getAddressFromCoordinates() {
        if (!this.latitude || !this.longitude) {
            throw new Error('No coordinates available');
        }
        
        try {
            // Using a reverse geocoding service (example with OpenStreetMap Nominatim)
            const response = await fetch(
                `https://nominatim.openstreetmap.org/reverse?format=json&lat=${this.latitude}&lon=${this.longitude}&zoom=18&addressdetails=1`
            );
            
            if (!response.ok) {
                throw new Error('Geocoding service unavailable');
            }
            
            const data = await response.json();
            return data.display_name || 'Address not found';
            
        } catch (error) {
            console.error('Error getting address:', error);
            return 'Address lookup failed';
        }
    }
    
    calculateDistance(lat2, lon2) {
        if (!this.latitude || !this.longitude) {
            return null;
        }
        
        const R = 6371; // Earth's radius in kilometers
        const dLat = this.toRadians(lat2 - this.latitude);
        const dLon = this.toRadians(lon2 - this.longitude);
        
        const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
                  Math.cos(this.toRadians(this.latitude)) * Math.cos(this.toRadians(lat2)) *
                  Math.sin(dLon / 2) * Math.sin(dLon / 2);
        
        const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
        const distance = R * c;
        
        return distance * 1000; // Return distance in meters
    }
    
    toRadians(degrees) {
        return degrees * (Math.PI / 180);
    }
    
    isWithinRadius(centerLat, centerLon, radiusMeters) {
        const distance = this.calculateDistance(centerLat, centerLon);
        return distance !== null && distance <= radiusMeters;
    }
    
    startTracking() {
        return this.watchLocation();
    }
    
    stopTracking(watchId) {
        if (watchId && navigator.geolocation) {
            navigator.geolocation.clearWatch(watchId);
        }
    }
    
    exportData() {
        return {
            latitude: this.latitude,
            longitude: this.longitude,
            accuracy: this.accuracy,
            timestamp: this.timestamp,
            locationString: this.getLocationString(),
            accuracyString: this.getAccuracyString(),
            timestampString: this.getTimestampString()
        };
    }
}

// GPS Attendance Helper
class GPSAttendance {
    constructor(allowedLocations = [], radiusMeters = 100) {
        this.geoLocation = new GeoLocation('gpsStatus');
        this.allowedLocations = allowedLocations; // Array of {lat, lon, name} objects
        this.radiusMeters = radiusMeters;
        this.isLocationValid = false;
    }
    
    async checkLocationValidity() {
        try {
            const location = await this.geoLocation.getCurrentLocation();
            
            if (this.allowedLocations.length === 0) {
                // If no specific locations are set, any location is valid
                this.isLocationValid = true;
                return { valid: true, message: 'Location captured successfully' };
            }
            
            // Check if current location is within any allowed location
            for (const allowedLocation of this.allowedLocations) {
                const distance = this.geoLocation.calculateDistance(
                    allowedLocation.lat, 
                    allowedLocation.lon
                );
                
                if (distance <= this.radiusMeters) {
                    this.isLocationValid = true;
                    return { 
                        valid: true, 
                        message: `Location verified: ${allowedLocation.name}`,
                        location: allowedLocation
                    };
                }
            }
            
            this.isLocationValid = false;
            return { 
                valid: false, 
                message: 'You are not at an authorized location for attendance'
            };
            
        } catch (error) {
            this.isLocationValid = false;
            return { 
                valid: false, 
                message: 'Unable to verify location. Please enable GPS and try again.'
            };
        }
    }
    
    getLocationData() {
        return this.geoLocation.exportData();
    }
    
    async getLocationWithAddress() {
        const locationData = this.getLocationData();
        
        try {
            const address = await this.geoLocation.getAddressFromCoordinates();
            locationData.address = address;
        } catch (error) {
            locationData.address = 'Address not available';
        }
        
        return locationData;
    }
}

// Export for use in other files
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { GeoLocation, GPSAttendance };
}
