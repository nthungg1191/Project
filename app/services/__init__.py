"""Services package"""

from app.services.face_detection import FaceDetector
from app.services.face_service import FaceService

__all__ = [
    'FaceDetector',
    'FaceService'
]

# Note: FaceRecognitionService and CameraService removed from exports
# They are only used in test files, not in production code
