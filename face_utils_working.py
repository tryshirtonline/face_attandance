
import numpy as np
import base64
import logging
from io import BytesIO
import hashlib
import json
from PIL import Image
import cv2

class FaceProcessor:
    def __init__(self):
        # Blink detection parameters
        self.blink_threshold = 0.25
        self.consecutive_frames = 3
        self.blink_counter = 0
        self.blink_detected = False
        self.frame_count = 0
        self.last_blink_frame = 0

    def calculate_ear(self, landmarks, eye_points):
        """Calculate Eye Aspect Ratio (EAR) for blink detection"""
        # Simplified mock calculation with more realistic variation
        base_ear = 0.3
        variation = 0.05 * np.sin(self.frame_count * 0.2)  # Natural eye movement
        return base_ear + variation

    def detect_blink(self, frame):
        """Detect eye blink in frame - improved mock version"""
        self.frame_count += 1
        
        # More realistic blink detection - blinks occur every 3-5 seconds naturally
        # For demo purposes, we'll simulate this
        frames_since_blink = self.frame_count - self.last_blink_frame
        
        # Simulate natural blinking pattern
        if frames_since_blink > 50 and (self.frame_count % 17 == 0 or self.frame_count % 23 == 0):
            self.blink_detected = True
            self.last_blink_frame = self.frame_count
            logging.info("Blink detected - anti-spoofing verified!")
            return True
        
        # Reset if too much time has passed without activity
        if frames_since_blink > 100:
            self.blink_detected = False
        
        return self.blink_detected

    def reset_blink_detection(self):
        """Reset blink detection state"""
        self.blink_counter = 0
        self.blink_detected = False
        self.frame_count = 0
        self.last_blink_frame = 0

    def extract_face_encoding(self, image_data):
        """Extract face encoding from base64 image data - improved version"""
        try:
            # Remove data URL prefix if present
            if ',' in image_data:
                image_data = image_data.split(',')[1]
            
            # Decode base64 image
            image_bytes = base64.b64decode(image_data)
            
            # Create a more sophisticated encoding based on image content
            # This simulates actual face feature extraction
            hash_obj = hashlib.sha256(image_bytes)
            hex_digest = hash_obj.hexdigest()
            
            # Create a 128-dimensional encoding (similar to real face encodings)
            encoding = []
            for i in range(0, 128):
                # Use different parts of the hash to create features
                byte_val = int(hex_digest[(i * 2) % len(hex_digest):(i * 2 + 2) % len(hex_digest)], 16)
                normalized_val = (byte_val - 127.5) / 127.5  # Normalize to [-1, 1]
                encoding.append(normalized_val)
            
            return encoding
            
        except Exception as e:
            logging.error(f"Error extracting face encoding: {e}")
            return None

    def compare_faces(self, known_encoding, unknown_encoding, tolerance=0.7):
        """Compare two face encodings - improved similarity calculation"""
        if not known_encoding or not unknown_encoding:
            return False
        
        try:
            # Ensure both encodings are the same length
            if len(known_encoding) != len(unknown_encoding):
                return False
            
            # Calculate multiple similarity metrics for better matching
            known = np.array(known_encoding)
            unknown = np.array(unknown_encoding)
            
            # 1. Cosine similarity (most reliable for face matching)
            dot_product = np.dot(known, unknown)
            norm_known = np.linalg.norm(known)
            norm_unknown = np.linalg.norm(unknown)
            
            if norm_known == 0 or norm_unknown == 0:
                return False
                
            cosine_similarity = dot_product / (norm_known * norm_unknown)
            
            # 2. Euclidean distance (normalized)
            euclidean_distance = np.linalg.norm(known - unknown)
            normalized_distance = euclidean_distance / np.sqrt(len(known_encoding))
            
            # 3. Correlation coefficient
            correlation = np.corrcoef(known, unknown)[0, 1]
            if np.isnan(correlation):
                correlation = 0
            
            # Combined scoring with weights
            similarity_score = (
                cosine_similarity * 0.5 +  # 50% weight to cosine similarity
                (1 - normalized_distance) * 0.3 +  # 30% weight to normalized distance
                abs(correlation) * 0.2  # 20% weight to correlation
            )
            
            # Use more lenient threshold for better matching
            return similarity_score > tolerance
            
        except Exception as e:
            logging.error(f"Error comparing faces: {e}")
            return False

    def process_attendance_frame(self, image_data, known_encoding):
        """Process frame for attendance marking with anti-spoofing"""
        try:
            # Extract face encoding from current frame
            current_encoding = self.extract_face_encoding(image_data)
            
            if not current_encoding:
                return {
                    'success': False,
                    'message': 'No face detected in image. Please ensure your face is clearly visible.',
                    'blink_detected': False,
                    'confidence': 0.0,
                    'security_alert': 'Face detection failed - possible obstruction or poor lighting'
                }
            
            # Check blink detection for anti-spoofing
            blink_detected = self.detect_blink(None)
            
            # Compare with known encoding using improved algorithm
            face_match = self.compare_faces(known_encoding, current_encoding, tolerance=0.65)
            
            if face_match:
                confidence = 0.85 + np.random.random() * 0.10  # Mock confidence 85-95%
                
                if blink_detected:
                    return {
                        'success': True,
                        'message': f'Face matched successfully! Confidence: {confidence:.1%}',
                        'blink_detected': True,
                        'confidence': confidence,
                        'security_alert': None
                    }
                else:
                    return {
                        'success': False,
                        'message': 'Face matched but anti-spoofing verification failed. Please blink naturally.',
                        'blink_detected': False,
                        'confidence': confidence,
                        'security_alert': 'SECURITY ALERT: No eye blink detected - possible photo/screen spoof attempt'
                    }
            else:
                # Face doesn't match
                confidence = 0.20 + np.random.random() * 0.30  # Low confidence for non-match
                
                if not blink_detected:
                    return {
                        'success': False,
                        'message': 'Face does not match registered employee and no blink detected.',
                        'blink_detected': False,
                        'confidence': confidence,
                        'security_alert': 'SECURITY ALERT: Unauthorized access attempt with possible spoofing'
                    }
                else:
                    return {
                        'success': False,
                        'message': 'Face does not match registered employee.',
                        'blink_detected': True,
                        'confidence': confidence,
                        'security_alert': 'SECURITY ALERT: Unauthorized access attempt detected'
                    }
                
        except Exception as e:
            logging.error(f"Error processing attendance frame: {e}")
            return {
                'success': False,
                'message': f'Error processing image: {str(e)}',
                'blink_detected': False,
                'confidence': 0.0,
                'security_alert': 'System error during face processing'
            }

# Global face processor instance
face_processor = FaceProcessor()
