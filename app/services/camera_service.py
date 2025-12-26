import cv2
import numpy as np
import threading
import time
import logging
from typing import Optional, Callable, Dict, Any, Generator
from queue import Queue, Empty
import base64
import io
from PIL import Image

logger = logging.getLogger(__name__)


class CameraService:
    
    def __init__(self, camera_index: int = 0, width: int = 640, height: int = 480, fps: int = 60):

        self.camera_index = camera_index
        self.width = width
        self.height = height
        self.fps = fps
        self.cap = None
        self.is_running = False
        self.frame_queue = Queue(maxsize=10)
        self.capture_thread = None
        self.callbacks = []
        
        logger.info(f"CameraService initialized: {width}x{height}@{fps}fps")
    
    def initialize_camera(self) -> bool:

        try:
            self.cap = cv2.VideoCapture(self.camera_index)
            
            if not self.cap.isOpened():
                logger.error(f"Could not open camera {self.camera_index}")
                return False
            
            # Set camera properties
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            self.cap.set(cv2.CAP_PROP_FPS, self.fps)
            
            # Verify settings
            actual_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            actual_fps = int(self.cap.get(cv2.CAP_PROP_FPS))
            
            logger.info(f"Camera initialized: {actual_width}x{actual_height}@{actual_fps}fps")
            
            return True
            
        except Exception as e:
            logger.error(f"Error initializing camera: {str(e)}")
            return False
    
    def start_capture(self) -> bool:
        try:
            if self.is_running:
                logger.warning("Camera capture already running")
                return True
            
            if not self.initialize_camera():
                return False
            
            self.is_running = True
            self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
            self.capture_thread.start()
            
            logger.info("Camera capture started")
            return True
            
        except Exception as e:
            logger.error(f"Error starting camera capture: {str(e)}")
            return False
    
    def stop_capture(self):
        try:
            self.is_running = False
            
            if self.capture_thread and self.capture_thread.is_alive():
                self.capture_thread.join(timeout=2.0)
            
            if self.cap:
                self.cap.release()
                self.cap = None
            
            # Clear frame queue
            while not self.frame_queue.empty():
                try:
                    self.frame_queue.get_nowait()
                except Empty:
                    break
            
            logger.info("Camera capture stopped")
            
        except Exception as e:
            logger.error(f"Error stopping camera capture: {str(e)}")
    
    def _capture_loop(self):
        """Background thread for capturing frames"""
        try:
            while self.is_running and self.cap and self.cap.isOpened():
                ret, frame = self.cap.read()
                
                if not ret:
                    logger.warning("Failed to read frame from camera")
                    time.sleep(0.1)
                    continue
                
                # Resize frame if needed
                if frame.shape[1] != self.width or frame.shape[0] != self.height:
                    frame = cv2.resize(frame, (self.width, self.height))
                
                # Add frame to queue (non-blocking)
                try:
                    self.frame_queue.put_nowait(frame.copy())
                except:
                    # Queue is full, remove oldest frame
                    try:
                        self.frame_queue.get_nowait()
                        self.frame_queue.put_nowait(frame.copy())
                    except Empty:
                        pass
                
                # Call registered callbacks
                for callback in self.callbacks:
                    try:
                        callback(frame.copy())
                    except Exception as e:
                        logger.error(f"Error in camera callback: {str(e)}")
                
                # Control frame rate
                time.sleep(1.0 / self.fps)
                
        except Exception as e:
            logger.error(f"Error in capture loop: {str(e)}")
        finally:
            self.is_running = False
    
    def get_latest_frame(self) -> Optional[np.ndarray]:

        try:
            if not self.is_running:
                return None
            
            # Get latest frame from queue
            frame = None
            while not self.frame_queue.empty():
                try:
                    frame = self.frame_queue.get_nowait()
                except Empty:
                    break
            
            return frame
            
        except Exception as e:
            logger.error(f"Error getting latest frame: {str(e)}")
            return None
    
    def capture_image(self) -> Optional[np.ndarray]:
        """
        Capture a single image
        
        Returns:
            Captured image or None
        """
        try:
            if not self.cap or not self.cap.isOpened():
                if not self.initialize_camera():
                    return None
            
            ret, frame = self.cap.read()
            
            if not ret:
                logger.error("Failed to capture image")
                return None
            
            # Resize if needed
            if frame.shape[1] != self.width or frame.shape[0] != self.height:
                frame = cv2.resize(frame, (self.width, self.height))
            
            return frame
            
        except Exception as e:
            logger.error(f"Error capturing image: {str(e)}")
            return None
    
    def add_callback(self, callback: Callable[[np.ndarray], None]):
        """
        Add callback function for frame processing
        
        Args:
            callback: Function to call with each frame
        """
        self.callbacks.append(callback)
        logger.info(f"Added camera callback: {callback.__name__}")
    
    def remove_callback(self, callback: Callable[[np.ndarray], None]):
        """
        Remove callback function
        
        Args:
            callback: Function to remove
        """
        if callback in self.callbacks:
            self.callbacks.remove(callback)
            logger.info(f"Removed camera callback: {callback.__name__}")
    
    def get_camera_info(self) -> Dict[str, Any]:
        """
        Get camera information
        
        Returns:
            Camera information dictionary
        """
        try:
            if not self.cap or not self.cap.isOpened():
                return {
                    'available': False,
                    'error': 'Camera not initialized'
                }
            
            return {
                'available': True,
                'camera_index': self.camera_index,
                'width': int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                'height': int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                'fps': int(self.cap.get(cv2.CAP_PROP_FPS)),
                'is_running': self.is_running,
                'queue_size': self.frame_queue.qsize()
            }
            
        except Exception as e:
            logger.error(f"Error getting camera info: {str(e)}")
            return {
                'available': False,
                'error': str(e)
            }
    
    def encode_frame_to_base64(self, frame: np.ndarray, quality: int = 90) -> str:
        """
        Encode frame to base64 string
        
        Args:
            frame: Frame to encode
            quality: JPEG quality (1-100)
            
        Returns:
            Base64 encoded frame
        """
        try:
            # Encode frame as JPEG
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
            _, buffer = cv2.imencode('.jpg', frame, encode_param)
            
            # Convert to base64
            frame_bytes = buffer.tobytes()
            base64_string = base64.b64encode(frame_bytes).decode('utf-8')
            
            return f"data:image/jpeg;base64,{base64_string}"
            
        except Exception as e:
            logger.error(f"Error encoding frame to base64: {str(e)}")
            return ""
    
    def decode_base64_to_frame(self, base64_string: str) -> Optional[np.ndarray]:
        """
        Decode base64 string to frame
        
        Args:
            base64_string: Base64 encoded image
            
        Returns:
            Decoded frame or None
        """
        try:
            # Remove data URL prefix if present
            if ',' in base64_string:
                base64_string = base64_string.split(',')[1]
            
            # Decode base64
            image_data = base64.b64decode(base64_string)
            
            # Convert to numpy array
            nparr = np.frombuffer(image_data, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            return frame
            
        except Exception as e:
            logger.error(f"Error decoding base64 to frame: {str(e)}")
            return None
    
    def __enter__(self):
        """Context manager entry"""
        self.start_capture()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.stop_capture()


class VideoStreamGenerator:
    """Generator for video streaming"""
    
    def __init__(self, camera_service: CameraService):
        self.camera_service = camera_service
        self.is_streaming = False
    
    def start_stream(self) -> Generator[bytes, None, None]:
        """
        Start video stream generator
        
        Yields:
            JPEG encoded frames as bytes
        """
        try:
            self.is_streaming = True
            
            while self.is_streaming and self.camera_service.is_running:
                frame = self.camera_service.get_latest_frame()
                
                if frame is None:
                    time.sleep(0.1)
                    continue
                
                # Encode frame as JPEG
                encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 80]
                _, buffer = cv2.imencode('.jpg', frame, encode_param)
                
                yield buffer.tobytes()
                
                time.sleep(1.0 / self.camera_service.fps)
                
        except Exception as e:
            logger.error(f"Error in video stream: {str(e)}")
        finally:
            self.is_streaming = False
    
    def stop_stream(self):
        """Stop video stream"""
        self.is_streaming = False


class CameraManager:
    """High-level camera manager"""
    
    def __init__(self):
        self.camera_service = None
        self.face_detector = None
        self.logger = logging.getLogger(__name__)
    
    def initialize(self, camera_index: int = 0, width: int = 640, height: int = 480, fps: int = 30) -> bool:
        """
        Initialize camera manager
        
        Args:
            camera_index: Camera device index
            width: Video width
            height: Video height
            fps: Frames per second
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.camera_service = CameraService(camera_index, width, height, fps)
            
            if not self.camera_service.initialize_camera():
                return False
            
            self.logger.info("Camera manager initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error initializing camera manager: {str(e)}")
            return False
    
    def start_capture(self) -> bool:
        """Start camera capture"""
        if not self.camera_service:
            self.logger.error("Camera service not initialized")
            return False
        
        return self.camera_service.start_capture()
    
    def stop_capture(self):
        """Stop camera capture"""
        if self.camera_service:
            self.camera_service.stop_capture()
    
    def capture_face_image(self) -> Optional[np.ndarray]:
        """
        Capture image suitable for face recognition
        
        Returns:
            Captured image or None
        """
        try:
            if not self.camera_service:
                return None
            
            frame = self.camera_service.capture_image()
            
            if frame is None:
                return None
            
            # Enhance image for face recognition
            enhanced_frame = self._enhance_for_face_recognition(frame)
            
            return enhanced_frame
            
        except Exception as e:
            self.logger.error(f"Error capturing face image: {str(e)}")
            return None
    
    def _enhance_for_face_recognition(self, frame: np.ndarray) -> np.ndarray:
        """
        Enhance frame for better face recognition
        
        Args:
            frame: Input frame
            
        Returns:
            Enhanced frame
        """
        try:
            # Convert to grayscale for processing
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Apply histogram equalization
            equalized = cv2.equalizeHist(gray)
            
            # Convert back to BGR
            enhanced = cv2.cvtColor(equalized, cv2.COLOR_GRAY2BGR)
            
            return enhanced
            
        except Exception as e:
            self.logger.error(f"Error enhancing frame: {str(e)}")
            return frame
    
    def get_camera_status(self) -> Dict[str, Any]:
        """Get camera status"""
        if not self.camera_service:
            return {'available': False, 'error': 'Not initialized'}
        
        return self.camera_service.get_camera_info()
