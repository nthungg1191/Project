"""
Test script for face recognition functionality
Tests face detection, encoding, and recognition
"""

import sys
import os
import cv2
import numpy as np
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.face_detection import FaceDetector, FaceRecognitionService
from app.services.camera_service import CameraService, CameraManager
from app.services.face_service import FaceService
from app.utils.image_utils import ImageProcessor
from app import create_app, db

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FaceRecognitionTester:
    """Test face recognition functionality"""
    
    def __init__(self):
        self.app = create_app('testing')
        self.face_detector = FaceDetector()
        self.face_recognition_service = FaceRecognitionService()
        self.camera_manager = CameraManager()
        self.image_processor = ImageProcessor()
        
        logger.info("FaceRecognitionTester initialized")
    
    def test_face_detection(self, image_path: str = None) -> Dict[str, Any]:
        """
        Test face detection functionality
        
        Args:
            image_path: Path to test image (optional)
            
        Returns:
            Test results
        """
        try:
            logger.info("Testing face detection...")
            
            if image_path and os.path.exists(image_path):
                # Test with provided image
                image = cv2.imread(image_path)
                if image is None:
                    return {
                        'success': False,
                        'message': f'Could not load image: {image_path}'
                    }
            else:
                # Test with camera
                if not self.camera_manager.initialize():
                    return {
                        'success': False,
                        'message': 'Could not initialize camera'
                    }
                
                if not self.camera_manager.start_capture():
                    return {
                        'success': False,
                        'message': 'Could not start camera capture'
                    }
                
                # Capture image
                image = self.camera_manager.capture_face_image()
                if image is None:
                    return {
                        'success': False,
                        'message': 'Could not capture image from camera'
                    }
            
            # Detect faces
            result = self.face_detector.process_image(image)
            
            logger.info(f"Face detection result: {result}")
            
            return {
                'success': True,
                'message': 'Face detection test completed',
                'faces_found': result['faces_found'],
                'face_locations': result['face_locations'],
                'has_encodings': len(result['face_encodings']) > 0
            }
            
        except Exception as e:
            logger.error(f"Error in face detection test: {str(e)}")
            return {
                'success': False,
                'message': f'Face detection test failed: {str(e)}'
            }
        finally:
            self.camera_manager.stop_capture()
    
    def test_face_encoding(self, image_path: str = None) -> Dict[str, Any]:
        """
        Test face encoding generation
        
        Args:
            image_path: Path to test image (optional)
            
        Returns:
            Test results
        """
        try:
            logger.info("Testing face encoding...")
            
            if image_path and os.path.exists(image_path):
                image = cv2.imread(image_path)
                if image is None:
                    return {
                        'success': False,
                        'message': f'Could not load image: {image_path}'
                    }
            else:
                if not self.camera_manager.initialize():
                    return {
                        'success': False,
                        'message': 'Could not initialize camera'
                    }
                
                if not self.camera_manager.start_capture():
                    return {
                        'success': False,
                        'message': 'Could not start camera capture'
                    }
                
                image = self.camera_manager.capture_face_image()
                if image is None:
                    return {
                        'success': False,
                        'message': 'Could not capture image from camera'
                    }
            
            # Get face encodings
            face_locations = self.face_detector.detect_faces(image)
            
            if not face_locations:
                return {
                    'success': False,
                    'message': 'No faces detected for encoding'
                }
            
            face_encodings = self.face_detector.get_face_encodings(image, face_locations)
            
            if not face_encodings:
                return {
                    'success': False,
                    'message': 'Could not generate face encodings'
                }
            
            # Validate encoding
            encoding = face_encodings[0]
            is_valid = self._validate_encoding(encoding)
            
            logger.info(f"Face encoding test completed. Valid: {is_valid}")
            
            return {
                'success': True,
                'message': 'Face encoding test completed',
                'encodings_generated': len(face_encodings),
                'encoding_shape': encoding.shape,
                'is_valid': is_valid,
                'encoding_sample': encoding[:5].tolist()  # First 5 values
            }
            
        except Exception as e:
            logger.error(f"Error in face encoding test: {str(e)}")
            return {
                'success': False,
                'message': f'Face encoding test failed: {str(e)}'
            }
        finally:
            self.camera_manager.stop_capture()
    
    def test_face_recognition(self, test_encodings: List[np.ndarray] = None) -> Dict[str, Any]:
        """
        Test face recognition with known encodings
        
        Args:
            test_encodings: List of test face encodings
            
        Returns:
            Test results
        """
        try:
            logger.info("Testing face recognition...")
            
            # Create test encodings if not provided
            if test_encodings is None:
                test_encodings = self._create_test_encodings()
            
            if not test_encodings:
                return {
                    'success': False,
                    'message': 'No test encodings available'
                }
            
            # Test recognition with camera
            if not self.camera_manager.initialize():
                return {
                    'success': False,
                    'message': 'Could not initialize camera'
                }
            
            if not self.camera_manager.start_capture():
                return {
                    'success': False,
                    'message': 'Could not start camera capture'
                }
            
            # Capture image
            image = self.camera_manager.capture_face_image()
            if image is None:
                return {
                    'success': False,
                    'message': 'Could not capture image from camera'
                }
            
            # Process image
            result = self.face_detector.process_image(image)
            
            if result['faces_found'] == 0:
                return {
                    'success': False,
                    'message': 'No face detected for recognition'
                }
            
            # Test recognition
            face_encoding = result['face_encodings'][0]
            test_names = [f"Test_Person_{i}" for i in range(len(test_encodings))]
            
            recognized_name = self.face_detector.recognize_face(
                face_encoding, 
                test_encodings, 
                test_names
            )
            
            # Calculate distances
            distances = self.face_detector.find_face_distance(face_encoding, test_encodings)
            min_distance = min(distances) if distances else float('inf')
            
            logger.info(f"Face recognition test completed. Recognized: {recognized_name}")
            
            return {
                'success': True,
                'message': 'Face recognition test completed',
                'recognized_name': recognized_name,
                'min_distance': min_distance,
                'tolerance': self.face_detector.tolerance,
                'is_match': min_distance < self.face_detector.tolerance
            }
            
        except Exception as e:
            logger.error(f"Error in face recognition test: {str(e)}")
            return {
                'success': False,
                'message': f'Face recognition test failed: {str(e)}'
            }
        finally:
            self.camera_manager.stop_capture()
    
    def test_camera_functionality(self) -> Dict[str, Any]:
        """
        Test camera functionality
        
        Returns:
            Test results
        """
        try:
            logger.info("Testing camera functionality...")
            
            # Initialize camera
            if not self.camera_manager.initialize():
                return {
                    'success': False,
                    'message': 'Could not initialize camera'
                }
            
            # Get camera info
            camera_info = self.camera_manager.get_camera_status()
            
            # Test capture
            if not self.camera_manager.start_capture():
                return {
                    'success': False,
                    'message': 'Could not start camera capture'
                }
            
            # Capture multiple frames
            frames_captured = 0
            for i in range(5):  # Capture 5 frames
                frame = self.camera_manager.capture_face_image()
                if frame is not None:
                    frames_captured += 1
                time.sleep(0.1)  # Small delay between captures
            
            self.camera_manager.stop_capture()
            
            logger.info(f"Camera test completed. Frames captured: {frames_captured}")
            
            return {
                'success': True,
                'message': 'Camera functionality test completed',
                'camera_info': camera_info,
                'frames_captured': frames_captured,
                'capture_success_rate': frames_captured / 5 * 100
            }
            
        except Exception as e:
            logger.error(f"Error in camera test: {str(e)}")
            return {
                'success': False,
                'message': f'Camera test failed: {str(e)}'
            }
        finally:
            self.camera_manager.stop_capture()
    
    def test_database_integration(self) -> Dict[str, Any]:
        """
        Test database integration for face encodings
        
        Returns:
            Test results
        """
        try:
            logger.info("Testing database integration...")
            
            with self.app.app_context():
                # Initialize face service
                face_service = FaceService(db.session)
                
                # Test statistics
                stats = face_service.get_face_statistics()
                
                # Test backup (if we have encodings)
                backup_result = face_service.backup_face_encodings('test_backup.pkl')
                
                logger.info(f"Database integration test completed. Stats: {stats}")
                
                return {
                    'success': True,
                    'message': 'Database integration test completed',
                    'statistics': stats,
                    'backup_success': backup_result['success']
                }
                
        except Exception as e:
            logger.error(f"Error in database integration test: {str(e)}")
            return {
                'success': False,
                'message': f'Database integration test failed: {str(e)}'
            }
    
    def run_all_tests(self) -> Dict[str, Any]:
        """
        Run all face recognition tests
        
        Returns:
            Comprehensive test results
        """
        try:
            logger.info("Running all face recognition tests...")
            
            results = {
                'timestamp': datetime.now().isoformat(),
                'tests': {}
            }
            
            # Test 1: Face Detection
            results['tests']['face_detection'] = self.test_face_detection()
            
            # Test 2: Face Encoding
            results['tests']['face_encoding'] = self.test_face_encoding()
            
            # Test 3: Camera Functionality
            results['tests']['camera'] = self.test_camera_functionality()
            
            # Test 4: Database Integration
            results['tests']['database'] = self.test_database_integration()
            
            # Test 5: Face Recognition (if we have test data)
            results['tests']['face_recognition'] = self.test_face_recognition()
            
            # Calculate overall success
            successful_tests = sum(1 for test in results['tests'].values() if test['success'])
            total_tests = len(results['tests'])
            
            results['overall_success'] = successful_tests == total_tests
            results['success_rate'] = successful_tests / total_tests * 100
            
            logger.info(f"All tests completed. Success rate: {results['success_rate']:.1f}%")
            
            return results
            
        except Exception as e:
            logger.error(f"Error running all tests: {str(e)}")
            return {
                'success': False,
                'message': f'Test suite failed: {str(e)}'
            }
    
    def _validate_encoding(self, encoding: np.ndarray) -> bool:
        """Validate face encoding format"""
        try:
            return (
                isinstance(encoding, np.ndarray) and
                encoding.shape == (128,) and
                not np.any(np.isnan(encoding)) and
                not np.any(np.isinf(encoding))
            )
        except:
            return False
    
    def _create_test_encodings(self) -> List[np.ndarray]:
        """Create test face encodings for testing"""
        try:
            # Create dummy encodings for testing
            test_encodings = []
            for i in range(3):
                # Create random encoding that looks like face_recognition output
                encoding = np.random.rand(128).astype(np.float32)
                test_encodings.append(encoding)
            
            return test_encodings
            
        except Exception as e:
            logger.error(f"Error creating test encodings: {str(e)}")
            return []


def main():
    """Main test function"""
    print("🧪 Face Recognition Test Suite")
    print("=" * 50)
    
    tester = FaceRecognitionTester()
    
    # Run all tests
    results = tester.run_all_tests()
    
    # Print results
    print(f"\n📊 Test Results:")
    print(f"Overall Success: {results.get('overall_success', False)}")
    print(f"Success Rate: {results.get('success_rate', 0):.1f}%")
    
    print(f"\n📋 Individual Tests:")
    for test_name, test_result in results.get('tests', {}).items():
        status = "✅" if test_result['success'] else "❌"
        print(f"  {status} {test_name}: {test_result['message']}")
    
    print(f"\n⏰ Completed at: {results.get('timestamp', 'Unknown')}")
    
    return results


if __name__ == '__main__':
    import time
    main()
