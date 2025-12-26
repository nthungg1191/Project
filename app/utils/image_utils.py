"""
Image processing utilities
Helper functions for image manipulation and enhancement
"""

import cv2
import numpy as np
import base64
import io
import logging
from typing import Tuple, Optional, List, Dict, Any
from PIL import Image, ImageEnhance
import os

logger = logging.getLogger(__name__)


class ImageProcessor:
    """Image processing utilities"""
    
    @staticmethod
    def resize_image(image: np.ndarray, width: int, height: int, 
                    maintain_aspect_ratio: bool = True) -> np.ndarray:
        """
        Resize image to specified dimensions
        
        Args:
            image: Input image
            width: Target width
            height: Target height
            maintain_aspect_ratio: Whether to maintain aspect ratio
            
        Returns:
            Resized image
        """
        try:
            if maintain_aspect_ratio:
                h, w = image.shape[:2]
                aspect_ratio = w / h
                
                if width / height > aspect_ratio:
                    new_width = int(height * aspect_ratio)
                    new_height = height
                else:
                    new_width = width
                    new_height = int(width / aspect_ratio)
                
                resized = cv2.resize(image, (new_width, new_height))
                
                # Create canvas with target size
                canvas = np.zeros((height, width, 3), dtype=np.uint8)
                
                # Center the resized image
                y_offset = (height - new_height) // 2
                x_offset = (width - new_width) // 2
                
                canvas[y_offset:y_offset+new_height, x_offset:x_offset+new_width] = resized
                
                return canvas
            else:
                return cv2.resize(image, (width, height))
                
        except Exception as e:
            logger.error(f"Error resizing image: {str(e)}")
            return image
    
    @staticmethod
    def enhance_for_face_recognition(image: np.ndarray) -> np.ndarray:
        """
        Enhance image for better face recognition
        
        Args:
            image: Input image
            
        Returns:
            Enhanced image
        """
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Apply histogram equalization
            equalized = cv2.equalizeHist(gray)
            
            # Apply Gaussian blur to reduce noise
            blurred = cv2.GaussianBlur(equalized, (3, 3), 0)
            
            # Apply sharpening
            kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
            sharpened = cv2.filter2D(blurred, -1, kernel)
            
            # Convert back to BGR
            enhanced = cv2.cvtColor(sharpened, cv2.COLOR_GRAY2BGR)
            
            return enhanced
            
        except Exception as e:
            logger.error(f"Error enhancing image: {str(e)}")
            return image
    
    @staticmethod
    def adjust_brightness_contrast(image: np.ndarray, brightness: float = 0, 
                                 contrast: float = 1.0) -> np.ndarray:
        """
        Adjust brightness and contrast of image
        
        Args:
            image: Input image
            brightness: Brightness adjustment (-100 to 100)
            contrast: Contrast adjustment (0.0 to 3.0)
            
        Returns:
            Adjusted image
        """
        try:
            # Convert to float
            img_float = image.astype(np.float32)
            
            # Apply brightness
            img_float = img_float + brightness
            
            # Apply contrast
            img_float = img_float * contrast
            
            # Clip values to valid range
            img_float = np.clip(img_float, 0, 255)
            
            return img_float.astype(np.uint8)
            
        except Exception as e:
            logger.error(f"Error adjusting brightness/contrast: {str(e)}")
            return image
    
    @staticmethod
    def detect_face_quality(image: np.ndarray, face_location: Tuple[int, int, int, int]) -> Dict[str, Any]:
        """
        Detect face quality metrics
        
        Args:
            image: Input image
            face_location: Face location (top, right, bottom, left)
            
        Returns:
            Quality metrics dictionary
        """
        try:
            top, right, bottom, left = face_location
            
            # Extract face region
            face_region = image[top:bottom, left:right]
            
            if face_region.size == 0:
                return {
                    'quality_score': 0,
                    'is_blurry': True,
                    'is_dark': True,
                    'is_small': True,
                    'brightness': 0,
                    'contrast': 0
                }
            
            # Convert to grayscale
            gray_face = cv2.cvtColor(face_region, cv2.COLOR_BGR2GRAY)
            
            # Calculate brightness
            brightness = np.mean(gray_face)
            
            # Calculate contrast (standard deviation)
            contrast = np.std(gray_face)
            
            # Detect blur using Laplacian variance
            laplacian_var = cv2.Laplacian(gray_face, cv2.CV_64F).var()
            
            # Calculate face size
            face_area = (bottom - top) * (right - left)
            image_area = image.shape[0] * image.shape[1]
            face_ratio = face_area / image_area
            
            # Quality assessment
            is_blurry = laplacian_var < 100
            is_dark = brightness < 50
            is_small = face_ratio < 0.01  # Less than 1% of image
            
            # Calculate quality score (0-100)
            quality_score = 0
            
            if not is_blurry:
                quality_score += 30
            if not is_dark:
                quality_score += 30
            if not is_small:
                quality_score += 20
            
            # Brightness score
            if 50 <= brightness <= 200:
                quality_score += 10
            elif 30 <= brightness < 50 or 200 < brightness <= 250:
                quality_score += 5
            
            # Contrast score
            if contrast > 30:
                quality_score += 10
            elif contrast > 20:
                quality_score += 5
            
            return {
                'quality_score': min(quality_score, 100),
                'is_blurry': is_blurry,
                'is_dark': is_dark,
                'is_small': is_small,
                'brightness': float(brightness),
                'contrast': float(contrast),
                'laplacian_variance': float(laplacian_var),
                'face_ratio': float(face_ratio)
            }
            
        except Exception as e:
            logger.error(f"Error detecting face quality: {str(e)}")
            return {
                'quality_score': 0,
                'is_blurry': True,
                'is_dark': True,
                'is_small': True,
                'brightness': 0,
                'contrast': 0
            }
    
    @staticmethod
    def crop_face(image: np.ndarray, face_location: Tuple[int, int, int, int], 
                  padding: int = 20) -> np.ndarray:
        """
        Crop face region from image
        
        Args:
            image: Input image
            face_location: Face location (top, right, bottom, left)
            padding: Padding around face
            
        Returns:
            Cropped face image
        """
        try:
            top, right, bottom, left = face_location
            
            # Add padding
            h, w = image.shape[:2]
            top = max(0, top - padding)
            bottom = min(h, bottom + padding)
            left = max(0, left - padding)
            right = min(w, right + padding)
            
            return image[top:bottom, left:right]
            
        except Exception as e:
            logger.error(f"Error cropping face: {str(e)}")
            return image
    
    @staticmethod
    def encode_to_base64(image: np.ndarray, quality: int = 90) -> str:
        """
        Encode image to base64 string
        
        Args:
            image: Input image
            quality: JPEG quality (1-100)
            
        Returns:
            Base64 encoded image string
        """
        try:
            # Encode as JPEG
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
            _, buffer = cv2.imencode('.jpg', image, encode_param)
            
            # Convert to base64
            image_bytes = buffer.tobytes()
            base64_string = base64.b64encode(image_bytes).decode('utf-8')
            
            return f"data:image/jpeg;base64,{base64_string}"
            
        except Exception as e:
            logger.error(f"Error encoding image to base64: {str(e)}")
            return ""
    
    @staticmethod
    def decode_from_base64(base64_string: str) -> Optional[np.ndarray]:
        """
        Decode base64 string to image
        
        Args:
            base64_string: Base64 encoded image string
            
        Returns:
            Decoded image or None
        """
        try:
            # Remove data URL prefix if present
            if ',' in base64_string:
                base64_string = base64_string.split(',')[1]
            
            # Decode base64
            image_bytes = base64.b64decode(base64_string)
            
            # Convert to numpy array
            nparr = np.frombuffer(image_bytes, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            return image
            
        except Exception as e:
            logger.error(f"Error decoding base64 image: {str(e)}")
            return None
    
    @staticmethod
    def save_image(image: np.ndarray, file_path: str, quality: int = 90) -> bool:
        """
        Save image to file
        
        Args:
            image: Input image
            file_path: Output file path
            quality: JPEG quality (1-100)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # Determine file extension
            ext = os.path.splitext(file_path)[1].lower()
            
            if ext in ['.jpg', '.jpeg']:
                encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
                cv2.imwrite(file_path, image, encode_param)
            elif ext == '.png':
                cv2.imwrite(file_path, image)
            else:
                # Default to JPEG
                encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
                cv2.imwrite(file_path, image, encode_param)
            
            return True
            
        except Exception as e:
            logger.error(f"Error saving image: {str(e)}")
            return False
    
    @staticmethod
    def load_image(file_path: str) -> Optional[np.ndarray]:
        """
        Load image from file
        
        Args:
            file_path: Image file path
            
        Returns:
            Loaded image or None
        """
        try:
            if not os.path.exists(file_path):
                logger.warning(f"Image file not found: {file_path}")
                return None
            
            image = cv2.imread(file_path)
            
            if image is None:
                logger.error(f"Could not load image: {file_path}")
                return None
            
            return image
            
        except Exception as e:
            logger.error(f"Error loading image: {str(e)}")
            return None
    
    @staticmethod
    def create_face_thumbnail(image: np.ndarray, face_location: Tuple[int, int, int, int], 
                             size: Tuple[int, int] = (150, 150)) -> np.ndarray:
        """
        Create thumbnail of face
        
        Args:
            image: Input image
            face_location: Face location
            size: Thumbnail size (width, height)
            
        Returns:
            Face thumbnail
        """
        try:
            # Crop face
            face_crop = ImageProcessor.crop_face(image, face_location)
            
            # Resize to thumbnail size
            thumbnail = ImageProcessor.resize_image(face_crop, size[0], size[1])
            
            return thumbnail
            
        except Exception as e:
            logger.error(f"Error creating face thumbnail: {str(e)}")
            return image
    
    @staticmethod
    def batch_process_images(image_paths: List[str], output_dir: str, 
                           processor_func: callable) -> List[Dict[str, Any]]:
        """
        Batch process multiple images
        
        Args:
            image_paths: List of image file paths
            output_dir: Output directory
            processor_func: Processing function
            
        Returns:
            List of processing results
        """
        try:
            results = []
            
            for image_path in image_paths:
                try:
                    # Load image
                    image = ImageProcessor.load_image(image_path)
                    
                    if image is None:
                        results.append({
                            'input_path': image_path,
                            'success': False,
                            'error': 'Could not load image'
                        })
                        continue
                    
                    # Process image
                    processed_image = processor_func(image)
                    
                    # Generate output path
                    filename = os.path.basename(image_path)
                    name, ext = os.path.splitext(filename)
                    output_path = os.path.join(output_dir, f"{name}_processed{ext}")
                    
                    # Save processed image
                    success = ImageProcessor.save_image(processed_image, output_path)
                    
                    results.append({
                        'input_path': image_path,
                        'output_path': output_path,
                        'success': success
                    })
                    
                except Exception as e:
                    results.append({
                        'input_path': image_path,
                        'success': False,
                        'error': str(e)
                    })
            
            return results
            
        except Exception as e:
            logger.error(f"Error in batch processing: {str(e)}")
            return []
