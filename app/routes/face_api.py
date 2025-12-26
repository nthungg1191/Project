
import base64
import io
import logging
from typing import Optional
from flask import Blueprint, request, jsonify
from app.services.face_detection import FaceDetector
from app.services.face_service import FaceService
from app import db
from app.utils.image_utils import ImageProcessor
import numpy as np
from PIL import Image
import cv2

logger = logging.getLogger(__name__)

# Create blueprint
face_api = Blueprint('face_api', __name__, url_prefix='/api/face')

# Initialize services
face_detector = FaceDetector()

# Legacy /register endpoint removed - use /register-multi instead


@face_api.route('/recognize', methods=['POST'])
def recognize_face():
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'message': 'Không có dữ liệu'
            }), 400
        
        image_data = data.get('image')
        
        if not image_data:
            return jsonify({
                'success': False,
                'message': 'Dữ liệu ảnh là bắt buộc'
            }), 400
        
        # Decode image
        image = _decode_image(image_data)
        if image is None:
            return jsonify({
                'success': False,
                'message': 'Dữ liệu ảnh không hợp lệ'
            }), 400
        
        # Process image for face detection
        result = face_detector.process_image(image)
        
        if result['faces_found'] == 0:
            return jsonify({
                'success': False,
                'message': 'Không có khuôn mặt trong ảnh'
            }), 400
        
        if result['faces_found'] > 1:
            return jsonify({
                'success': False,
                'message': 'Nhiều khuôn mặt được phát hiện. Vui lòng sử dụng ảnh với một khuôn mặt'
            }), 400
        
        # Get face encoding
        face_encoding = result['face_encodings'][0]
        
        # Recognize employee using multi-embedding system
        face_service = FaceService(db.session)
        recognition_result = face_service.recognize_employee_multi(face_encoding, use_multi_embedding=True)
        
        return jsonify(recognition_result), 200
        
    except Exception as e:
        logger.error(f"Lỗi nhận dạng khuôn mặt: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Nhận dạng thất bại: {str(e)}'
        }), 500


@face_api.route('/detect', methods=['POST'])
def detect_faces():
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'message': 'Không có dữ liệu'
            }), 400
        
        image_data = data.get('image')
        
        if not image_data:
            return jsonify({
                'success': False,
                'message': 'Dữ liệu ảnh là bắt buộc'
            }), 400
        
        # Decode image
        image = _decode_image(image_data)
        if image is None:
            return jsonify({
                'success': False,
                'message': 'Dữ liệu ảnh không hợp lệ'
            }), 400
        
        # Detect faces
        result = face_detector.process_image(image)
        
        # Convert face locations to serializable format
        face_locations = []
        for (top, right, bottom, left) in result['face_locations']:
            face_locations.append({
                'top': int(top),
                'right': int(right),
                'bottom': int(bottom),
                'left': int(left)
            })
        
        return jsonify({
            'success': True,
            'faces_found': result['faces_found'],
            'face_locations': face_locations,
            'names': result['names']
        }), 200
        
    except Exception as e:
        logger.error(f"Lỗi phát hiện khuôn mặt: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Phát hiện thất bại: {str(e)}'
        }), 500


# Legacy endpoints removed (not used by frontend):
# - /enroll: Use /register-multi instead
# - /capture: Not used, requires camera_service
# - /encodings: Not used


@face_api.route('/employee/<employee_code>', methods=['GET'])
def get_employee_face(employee_code):
    try:
        face_service = FaceService(db.session)
        encoding = face_service.get_employee_face_encoding(employee_code)
        
        if encoding is None:
            return jsonify({
                'success': False,
                'message': f'Không tìm thấy khuôn mặt cho nhân viên {employee_code}'
            }), 404
        
        return jsonify({
            'success': True,
            'employee_code': employee_code,
            'has_encoding': True
        }), 200
        
    except Exception as e:
        logger.error(f"Lỗi lấy khuôn mặt nhân viên: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Lấy thất bại: {str(e)}'
        }), 500


@face_api.route('/employee/<employee_code>', methods=['DELETE'])
def delete_employee_face(employee_code):
    try:
        face_service = FaceService(db.session)
        result = face_service.delete_employee_face(employee_code)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Lỗi xóa khuôn mặt nhân viên: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Xóa thất bại: {str(e)}'
        }), 500


# Legacy /statistics endpoint removed - using /statistics with get_embedding_statistics() instead

# Backup/restore endpoints removed (not used by frontend):
# - /backup: Not used
# - /restore: Not used


@face_api.route('/register-multi', methods=['POST'])
def register_face_multi():
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'message': 'Không có dữ liệu'
            }), 400
        
        employee_code = data.get('employee_code')
        image_data = data.get('image')
        variant_type = data.get('variant_type', 'default')
        description = data.get('description')
        set_as_primary = data.get('set_as_primary', False)
        
        if not employee_code:
            return jsonify({
                'success': False,
                'message': 'Mã nhân viên là bắt buộc'
            }), 400
        
        if not image_data:
            return jsonify({
                'success': False,
                'message': 'Dữ liệu ảnh là bắt buộc'
            }), 400
        
        # Decode image
        image = _decode_image(image_data)
        if image is None:
            return jsonify({
                'success': False,
                'message': 'Dữ liệu ảnh không hợp lệ'
            }), 400
        
        face_service = FaceService(db.session)
        
        # Detect and encode face
        result_detect = face_detector.process_image(image)
        if result_detect['faces_found'] != 1:
            return jsonify({
                'success': False,
                'message': 'Ảnh phải chứa đúng một khuôn mặt'
            }), 400
        
        face_encoding = result_detect['face_encodings'][0]
        
        result = face_service.add_face_embedding(
            employee_code=employee_code,
            embedding=face_encoding,
            variant_type=variant_type,
            embedding_type='standard',
            description=description,
            set_as_primary=set_as_primary
        )
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"lỗi đăng ký khuôn mặt: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Đăng ký thất bại: {str(e)}'
        }), 500


@face_api.route('/embeddings/<employee_code>', methods=['GET'])
def get_employee_embeddings(employee_code):
    try:
        face_service = FaceService(db.session)
        embeddings = face_service.get_employee_embeddings(employee_code, active_only=True)
        
        embeddings_data = [emb.to_dict() for emb in embeddings]
        
        return jsonify({
            'success': True,
            'employee_code': employee_code,
            'total_embeddings': len(embeddings_data),
            'embeddings': embeddings_data
        }), 200
        
    except Exception as e:
        logger.error(f"Lỗi lấy khuôn mặt nhân viên: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Lấy thất bại: {str(e)}'
        }), 500


@face_api.route('/embedding/<int:embedding_id>', methods=['DELETE'])
def delete_face_embedding(embedding_id):
    try:
        face_service = FaceService(db.session)
        result = face_service.delete_face_embedding(embedding_id)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Lỗi xóa khuôn mặt nhân viên: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Xóa thất bại: {str(e)}'
        }), 500


@face_api.route('/embedding/<int:embedding_id>/primary', methods=['PUT'])
def set_primary_embedding(embedding_id):
    try:
        face_service = FaceService(db.session)
        result = face_service.set_primary_embedding(embedding_id)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Lỗi đặt khuôn mặt chính: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Đặt thất bại: {str(e)}'
        }), 500


@face_api.route('/statistics', methods=['GET'])
def get_embedding_statistics():
    try:
        face_service = FaceService(db.session)
        stats = face_service.get_embedding_statistics()
        
        return jsonify({
            'success': True,
            'statistics': stats
        }), 200
        
    except Exception as e:
        logger.error(f"Lỗi lấy thống kê khuôn mặt: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Lấy thất bại: {str(e)}'
        }), 500


# ========== HELPER FUNCTIONS ==========
# Note: Video registration endpoint and helper functions removed
# System now uses static photo capture (2-3 images) via /register-multi endpoint


def _decode_image(image_data: str) -> Optional[np.ndarray]:

    try:
        # Remove data URL prefix if present
        if ',' in image_data:
            image_data = image_data.split(',')[1]
        
        # Decode base64
        image_bytes = base64.b64decode(image_data)
        
        # Convert to PIL Image
        pil_image = Image.open(io.BytesIO(image_bytes))
        
        # Convert to numpy array
        image_array = np.array(pil_image)
        
        # Convert RGB to BGR for OpenCV
        if len(image_array.shape) == 3:
            image_array = cv2.cvtColor(image_array, cv2.COLOR_RGB2BGR)
        
        return image_array
        
    except Exception as e:
        logger.error(f"Error decoding image: {str(e)}")
        return None
