import cv2
import numpy as np
import face_recognition
import os
import logging
from typing import List, Tuple, Optional, Dict, Any
from PIL import Image
import io
import base64

logger = logging.getLogger(__name__)


class FaceDetector:
    """Face detection and recognition service"""
    
    def __init__(self, model: str = 'hog', tolerance: float = 0.4):

        self.model = model
        self.tolerance = tolerance
        self.known_face_encodings = []
        self.known_face_names = []
        
        logger.info(f"FaceDetector initialized with model: {model}, tolerance: {tolerance}")
    
    def detect_faces(self, image: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """
        Detect faces in an image
        
        Args:
            image: Input image as numpy array
            
        Returns:
            List of face locations (top, right, bottom, left)
        """
        try:
            # Convert BGR to RGB (OpenCV uses BGR, face_recognition uses RGB)
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # Find face locations
            face_locations = face_recognition.face_locations(
                rgb_image, 
                model=self.model
            )
            
            logger.debug(f"Detected {len(face_locations)} faces")
            return face_locations
            
        except Exception as e:
            logger.error(f"Error detecting faces: {str(e)}")
            return []
    
    def get_face_encodings(self, image: np.ndarray, face_locations: List[Tuple[int, int, int, int]] = None) -> List[np.ndarray]:

        try:
            # Convert BGR to RGB
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # If no face locations provided, detect them
            if face_locations is None:
                face_locations = self.detect_faces(image)
            
            if not face_locations:
                logger.warning("No faces found for encoding")
                return []
            
            # Get face encodings
            face_encodings = face_recognition.face_encodings(
                rgb_image, 
                face_locations
            )
            
            logger.debug(f"Generated {len(face_encodings)} face encodings")
            return face_encodings
            
        except Exception as e:
            logger.error(f"Error getting face encodings: {str(e)}")
            return []
    
    def compare_faces(self, face_encoding: np.ndarray, known_encodings: List[np.ndarray]) -> List[bool]:
        """
        Compare a face encoding with known encodings
        
        Args:
            face_encoding: Face encoding to compare
            known_encodings: List of known face encodings
            
        Returns:
            List of boolean matches
        """
        try:
            if not known_encodings:
                return []
            
            matches = face_recognition.compare_faces(
                known_encodings, 
                face_encoding, 
                tolerance=self.tolerance
            )
            
            return matches
            
        except Exception as e:
            logger.error(f"Error comparing faces: {str(e)}")
            return []
    
    def find_face_distance(self, face_encoding: np.ndarray, known_encodings: List[np.ndarray]) -> List[float]:
        """
        Calculate face distances
        
        Args:
            face_encoding: Face encoding to compare
            known_encodings: List of known face encodings
            
        Returns:
            List of face distances
        """
        try:
            if not known_encodings:
                return []
            
            distances = face_recognition.face_distance(
                known_encodings, 
                face_encoding
            )
            
            return distances.tolist()
            
        except Exception as e:
            logger.error(f"Error calculating face distances: {str(e)}")
            return []
    
    def recognize_face(self, face_encoding: np.ndarray, known_encodings: List[np.ndarray], known_names: List[str]) -> Optional[str]:
        """
        Recognize a face from known encodings
        
        Args:
            face_encoding: Face encoding to recognize
            known_encodings: List of known face encodings
            known_names: List of corresponding names
            
        Returns:
            Name of recognized person or None
        """
        try:
            if not known_encodings or not known_names:
                return None
            
            # Compare faces
            matches = self.compare_faces(face_encoding, known_encodings)
            
            if True in matches:
                # Find the best match
                face_distances = self.find_face_distance(face_encoding, known_encodings)
                best_match_index = np.argmin(face_distances)
                
                if face_distances[best_match_index] < self.tolerance:
                    return known_names[best_match_index]
            
            return None
            
        except Exception as e:
            logger.error(f"Error recognizing face: {str(e)}")
            return None
    
    def draw_face_boxes(self, image: np.ndarray, face_locations: List[Tuple[int, int, int, int]], 
                       names: List[str] = None) -> np.ndarray:
        """
        Draw bounding boxes around detected faces
        
        Args:
            image: Input image
            face_locations: Face locations
            names: Optional names to display
            
        Returns:
            Image with face boxes drawn
        """
        try:
            result_image = image.copy()
            
            for i, (top, right, bottom, left) in enumerate(face_locations):
                # Draw rectangle
                cv2.rectangle(result_image, (left, top), (right, bottom), (0, 255, 0), 2)
                
                # Draw name if provided
                if names and i < len(names):
                    cv2.rectangle(result_image, (left, bottom - 35), (right, bottom), (0, 255, 0), cv2.FILLED)
                    cv2.putText(result_image, names[i], (left + 6, bottom - 6), 
                               cv2.FONT_HERSHEY_DUPLEX, 0.6, (255, 255, 255), 1)
            
            return result_image
            
        except Exception as e:
            logger.error(f"Error drawing face boxes: {str(e)}")
            return image
    
    def process_image(self, image: np.ndarray) -> Dict[str, Any]:
        """
        Process an image and return face detection results
        
        Args:
            image: Input image
            
        Returns:
            Dictionary with detection results
        """
        try:
            # Detect faces
            face_locations = self.detect_faces(image)
            
            if not face_locations:
                return {
                    'faces_found': 0,
                    'face_locations': [],
                    'face_encodings': [],
                    'names': []
                }
            
            # Get face encodings
            face_encodings = self.get_face_encodings(image, face_locations)
            
            # Recognize faces if we have known encodings
            names = []
            if self.known_face_encodings:
                for encoding in face_encodings:
                    name = self.recognize_face(encoding, self.known_face_encodings, self.known_face_names)
                    names.append(name or "Unknown")
            else:
                names = ["Unknown"] * len(face_encodings)
            
            return {
                'faces_found': len(face_locations),
                'face_locations': face_locations,
                'face_encodings': face_encodings,
                'names': names
            }
            
        except Exception as e:
            logger.error(f"Error processing image: {str(e)}")
            return {
                'faces_found': 0,
                'face_locations': [],
                'face_encodings': [],
                'names': [],
                'error': str(e)
            }
    
    def load_known_faces(self, encodings: List[np.ndarray], names: List[str]):
        """
        Load known face encodings and names
        
        Args:
            encodings: List of face encodings
            names: List of corresponding names
        """
        try:
            self.known_face_encodings = encodings
            self.known_face_names = names
            logger.info(f"Loaded {len(encodings)} known faces")
            
        except Exception as e:
            logger.error(f"Error loading known faces: {str(e)}")
    
    def encode_image_from_base64(self, base64_string: str) -> Optional[np.ndarray]:
        """
        Decode base64 image string to numpy array
        
        Args:
            base64_string: Base64 encoded image
            
        Returns:
            Image as numpy array or None
        """
        try:
            # Remove data URL prefix if present
            if ',' in base64_string:
                base64_string = base64_string.split(',')[1]
            
            # Decode base64
            image_data = base64.b64decode(base64_string)
            
            # Convert to PIL Image
            pil_image = Image.open(io.BytesIO(image_data))
            
            # Convert to numpy array
            image_array = np.array(pil_image)
            
            # Convert RGB to BGR for OpenCV
            if len(image_array.shape) == 3:
                image_array = cv2.cvtColor(image_array, cv2.COLOR_RGB2BGR)
            
            return image_array
            
        except Exception as e:
            logger.error(f"Error decoding base64 image: {str(e)}")
            return None
    
    def encode_image_to_base64(self, image: np.ndarray) -> str:
        """
        Encode numpy array image to base64 string
        
        Args:
            image: Image as numpy array
            
        Returns:
            Base64 encoded image string
        """
        try:
            # Convert BGR to RGB
            if len(image.shape) == 3:
                rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            else:
                rgb_image = image
            
            # Convert to PIL Image
            pil_image = Image.fromarray(rgb_image)
            
            # Convert to base64
            buffer = io.BytesIO()
            pil_image.save(buffer, format='JPEG')
            image_bytes = buffer.getvalue()
            
            base64_string = base64.b64encode(image_bytes).decode('utf-8')
            
            return f"data:image/jpeg;base64,{base64_string}"
            
        except Exception as e:
            logger.error(f"Error encoding image to base64: {str(e)}")
            return ""


class FaceRecognitionService:
    """High-level face recognition service"""
    
    def __init__(self):
        self.detector = FaceDetector()
        logger.info("FaceRecognitionService initialized")
    
    def register_face(self, image: np.ndarray, employee_id: str) -> Dict[str, Any]:
        """
        Register a new face for an employee
        
        Args:
            image: Face image
            employee_id: Employee ID
            
        Returns:
            Registration result
        """
        try:
            # Detect faces
            face_locations = self.detector.detect_faces(image)
            
            if not face_locations:
                return {
                    'success': False,
                    'message': 'No face detected in image',
                    'employee_id': employee_id
                }
            
            if len(face_locations) > 1:
                return {
                    'success': False,
                    'message': 'Multiple faces detected. Please use image with single face',
                    'employee_id': employee_id
                }
            
            # Get face encoding
            face_encodings = self.detector.get_face_encodings(image, face_locations)
            
            if not face_encodings:
                return {
                    'success': False,
                    'message': 'Could not generate face encoding',
                    'employee_id': employee_id
                }
            
            return {
                'success': True,
                'message': 'Face registered successfully',
                'employee_id': employee_id,
                'face_encoding': face_encodings[0].tolist(),
                'face_location': face_locations[0]
            }
            
        except Exception as e:
            logger.error(f"Error registering face: {str(e)}")
            return {
                'success': False,
                'message': f'Registration failed: {str(e)}',
                'employee_id': employee_id
            }
    
    def recognize_employee(self, image: np.ndarray, known_encodings: List[np.ndarray], 
                          known_employee_ids: List[str]) -> Dict[str, Any]:
        """
        Recognize employee from image
        
        Args:
            image: Input image
            known_encodings: Known face encodings
            known_employee_ids: Corresponding employee IDs
            
        Returns:
            Recognition result
        """
        try:
            # Process image
            result = self.detector.process_image(image)
            
            if result['faces_found'] == 0:
                return {
                    'success': False,
                    'message': 'No face detected',
                    'employee_id': None
                }
            
            if result['faces_found'] > 1:
                return {
                    'success': False,
                    'message': 'Multiple faces detected',
                    'employee_id': None
                }
            
            # Load known faces for recognition
            self.detector.load_known_faces(known_encodings, known_employee_ids)
            
            # Recognize face
            face_encoding = result['face_encodings'][0]
            employee_id = self.detector.recognize_face(
                face_encoding, 
                known_encodings, 
                known_employee_ids
            )
            
            if employee_id:
                return {
                    'success': True,
                    'message': 'Employee recognized',
                    'employee_id': employee_id,
                    'confidence': 1.0 - min(self.detector.find_face_distance(face_encoding, known_encodings))
                }
            else:
                return {
                    'success': False,
                    'message': 'Employee not recognized',
                    'employee_id': None
                }
                
        except Exception as e:
            logger.error(f"Error recognizing employee: {str(e)}")
            return {
                'success': False,
                'message': f'Recognition failed: {str(e)}',
                'employee_id': None
            }
