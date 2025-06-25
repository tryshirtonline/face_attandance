class FaceCapture {
    constructor(videoId, canvasId, statusId, captureButtonId, hiddenInputId, submitButtonId) {
        this.video = document.getElementById(videoId);
        this.canvas = document.getElementById(canvasId);
        this.status = document.getElementById(statusId);
        this.captureButton = document.getElementById(captureButtonId);
        this.hiddenInput = document.getElementById(hiddenInputId);
        this.submitButton = document.getElementById(submitButtonId);
        
        this.stream = null;
        this.faceDetected = false;
        this.faceCaptured = false;
        
        this.setupEventListeners();
    }
    
    setupEventListeners() {
        if (this.captureButton) {
            this.captureButton.addEventListener('click', () => this.captureFace());
        }
    }
    
    async startCamera() {
        try {
            this.updateStatus('Starting camera...', 'info');
            
            const constraints = {
                video: {
                    width: { ideal: 640 },
                    height: { ideal: 480 },
                    facingMode: 'user'
                }
            };
            
            this.stream = await navigator.mediaDevices.getUserMedia(constraints);
            this.video.srcObject = this.stream;
            
            this.video.addEventListener('loadedmetadata', () => {
                this.updateStatus('Camera ready - Position your face in the frame', 'success');
                this.captureButton.disabled = false;
                this.startFaceDetection();
            });
            
        } catch (error) {
            console.error('Error accessing camera:', error);
            this.updateStatus('Camera access denied. Please allow camera access.', 'danger');
        }
    }
    
    startFaceDetection() {
        // Simple face detection using video dimensions
        // In a real implementation, you might use a library like MediaPipe or face-api.js
        const checkFace = () => {
            if (this.video.videoWidth > 0 && this.video.videoHeight > 0) {
                this.faceDetected = true;
                this.updateStatus('Face detected - Click "Capture Face" when ready', 'success');
            } else {
                this.faceDetected = false;
                this.updateStatus('Looking for face...', 'warning');
            }
            
            if (!this.faceCaptured) {
                setTimeout(checkFace, 1000);
            }
        };
        
        checkFace();
    }
    
    captureFace() {
        if (!this.faceDetected) {
            this.updateStatus('Please position your face in the frame first', 'warning');
            return;
        }
        
        try {
            // Set canvas dimensions to match video
            this.canvas.width = this.video.videoWidth;
            this.canvas.height = this.video.videoHeight;
            
            // Draw current video frame to canvas
            const ctx = this.canvas.getContext('2d');
            ctx.drawImage(this.video, 0, 0);
            
            // Get image data as base64
            const imageData = this.canvas.toDataURL('image/jpeg', 0.8);
            
            // Store in hidden input
            this.hiddenInput.value = imageData;
            
            // Update UI
            this.faceCaptured = true;
            this.updateStatus('Face captured successfully!', 'success');
            this.captureButton.innerHTML = '<i class="fas fa-check me-2"></i>Face Captured';
            this.captureButton.disabled = true;
            this.captureButton.classList.remove('btn-success');
            this.captureButton.classList.add('btn-outline-success');
            
            // Enable submit button
            if (this.submitButton) {
                this.submitButton.disabled = false;
            }
            
            // Show captured image preview (optional)
            this.showPreview(imageData);
            
        } catch (error) {
            console.error('Error capturing face:', error);
            this.updateStatus('Error capturing face. Please try again.', 'danger');
        }
    }
    
    showPreview(imageData) {
        // Create a small preview image
        const preview = document.createElement('img');
        preview.src = imageData;
        preview.style.width = '100px';
        preview.style.height = '75px';
        preview.style.objectFit = 'cover';
        preview.style.border = '2px solid var(--bs-success)';
        preview.style.borderRadius = '4px';
        preview.style.marginTop = '10px';
        
        // Remove existing preview
        const existingPreview = this.captureButton.parentNode.querySelector('.face-preview');
        if (existingPreview) {
            existingPreview.remove();
        }
        
        // Add new preview
        preview.classList.add('face-preview');
        this.captureButton.parentNode.appendChild(preview);
    }
    
    updateStatus(message, type = 'info') {
        this.status.textContent = message;
        this.status.className = 'face-status';
        
        switch (type) {
            case 'success':
                this.status.classList.add('bg-success');
                break;
            case 'warning':
                this.status.classList.add('bg-warning', 'text-dark');
                break;
            case 'danger':
                this.status.classList.add('bg-danger');
                break;
            default:
                this.status.classList.add('bg-info');
        }
    }
    
    stopCamera() {
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
            this.stream = null;
        }
        this.video.srcObject = null;
    }
    
    reset() {
        this.faceCaptured = false;
        this.faceDetected = false;
        this.hiddenInput.value = '';
        
        if (this.submitButton) {
            this.submitButton.disabled = true;
        }
        
        this.captureButton.innerHTML = '<i class="fas fa-camera me-2"></i>Capture Face';
        this.captureButton.disabled = false;
        this.captureButton.classList.remove('btn-outline-success');
        this.captureButton.classList.add('btn-success');
        
        // Remove preview
        const preview = this.captureButton.parentNode.querySelector('.face-preview');
        if (preview) {
            preview.remove();
        }
        
        this.updateStatus('Camera ready - Position your face in the frame', 'info');
        this.startFaceDetection();
    }
}

// Anti-spoofing Face Capture with blink detection
class AntiSpoofFaceCapture extends FaceCapture {
    constructor(videoId, canvasId, statusId, captureButtonId, hiddenInputId, submitButtonId) {
        super(videoId, canvasId, statusId, captureButtonId, hiddenInputId, submitButtonId);
        
        this.blinkDetected = false;
        this.blinkThreshold = 0.25;
        this.consecutiveFrames = 3;
        this.blinkFrameCount = 0;
        this.isCheckingBlink = false;
        
        // Eye aspect ratio calculation points (simplified)
        this.eyePoints = {
            left: [33, 7, 163, 144, 145, 153],
            right: [362, 382, 381, 380, 374, 373]
        };
    }
    
    startFaceDetection() {
        this.isCheckingBlink = true;
        this.checkBlinkDetection();
    }
    
    checkBlinkDetection() {
        if (!this.isCheckingBlink || this.faceCaptured) return;
        
        // Simulate blink detection
        // In a real implementation, this would use MediaPipe or similar
        const randomBlink = Math.random() > 0.95; // 5% chance per check
        
        if (randomBlink && !this.blinkDetected) {
            this.blinkFrameCount++;
            
            if (this.blinkFrameCount >= this.consecutiveFrames) {
                this.blinkDetected = true;
                this.updateStatus('Blink detected! Face recognition ready', 'success');
                this.captureButton.disabled = false;
            }
        } else {
            this.blinkFrameCount = 0;
        }
        
        if (!this.blinkDetected) {
            this.updateStatus('Please blink to confirm you are real', 'warning');
        }
        
        setTimeout(() => this.checkBlinkDetection(), 100);
    }
    
    captureFace() {
        if (!this.blinkDetected) {
            this.updateStatus('Please blink to activate anti-spoofing protection', 'warning');
            return;
        }
        
        super.captureFace();
    }
    
    reset() {
        super.reset();
        this.blinkDetected = false;
        this.blinkFrameCount = 0;
        this.isCheckingBlink = false;
    }
    
    stopCamera() {
        this.isCheckingBlink = false;
        super.stopCamera();
    }
}

// Export for use in other files
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { FaceCapture, AntiSpoofFaceCapture };
}
