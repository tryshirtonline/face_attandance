"""
Simplified face utilities for basic functionality without complex dependencies
"""
import base64
import io
import json

class FaceProcessor:
    def __init__(self):
        self.blink_counter = 0
        self.consecutive_frames = 0
        self.blink_detected = False
        
    def calculate_ear(self, landmarks, eye_points):
        """Placeholder for Eye Aspect Ratio calculation"""
        return 0.3  # Mock value
    
    def detect_blink(self, frame):
        """Mock blink detection - returns True periodically"""
        self.consecutive_frames += 1
        if self.consecutive_frames > 10:  # Simulate blink every 10 frames
            self.consecutive_frames = 0
            self.blink_detected = True
            return True
        return False
    
    def reset_blink_detection(self):
        """Reset blink detection state"""
        self.blink_counter = 0
        self.consecutive_frames = 0
        self.blink_detected = False
    
    def extract_face_encoding(self, image_data):
        """Extract face encoding from base64 image data - simplified version"""
        try:
            # Remove data URL prefix if present
            if ',' in image_data:
                image_data = image_data.split(',')[1]
            
            # Decode base64 image
            image_bytes = base64.b64decode(image_data)
            
            # Create a simple hash-based encoding for demo purposes
            # In production, this would use actual face recognition
            import hashlib
            hash_obj = hashlib.md5(image_bytes)
            encoding = [float(int(hash_obj.hexdigest()[i:i+2], 16)) / 255.0 for i in range(0, 32, 2)]
            
            return encoding
        except Exception as e:
            print(f"Error extracting face encoding: {e}")
            return None
    
    def compare_faces(self, known_encoding, unknown_encoding, tolerance=0.6):
        """Compare two face encodings - simplified version"""
        if not known_encoding or not unknown_encoding:
            return False
        
        # Simple comparison based on encoding similarity
        if len(known_encoding) != len(unknown_encoding):
            return False
        
        # Calculate simple distance
        distance = sum(abs(a - b) for a, b in zip(known_encoding, unknown_encoding)) / len(known_encoding)
        return distance < tolerance
    
    def process_attendance_frame(self, image_data, known_encoding):
        """Process frame for attendance marking with anti-spoofing"""
        try:
            # Extract face encoding from current frame
            current_encoding = self.extract_face_encoding(image_data)
            
            if not current_encoding:
                return {
                    'success': False,
                    'message': 'No face detected in image',
                    'blink_detected': False
                }
            
            # Check if blink was detected (anti-spoofing)
            blink_detected = self.detect_blink(None)  # Mock blink detection
            
            # Compare with known encoding
            match = self.compare_faces(known_encoding, current_encoding)
            
            if match and blink_detected:
                return {
                    'success': True,
                    'message': 'Face matched and liveness verified',
                    'blink_detected': True,
                    'face_match': True
                }
            elif match:
                return {
                    'success': False,
                    'message': 'Face matched but liveness verification failed',
                    'blink_detected': False,
                    'face_match': True
                }
            else:
                return {
                    'success': False,
                    'message': 'Face not recognized',
                    'blink_detected': blink_detected,
                    'face_match': False
                }
                
        except Exception as e:
            return {
                'success': False,
                'message': f'Error processing frame: {str(e)}',
                'blink_detected': False
            }

# Create global instance
face_processor = FaceProcessor()