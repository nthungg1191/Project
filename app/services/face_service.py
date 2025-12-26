import numpy as np
import json
import logging
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from app.models.employee import Employee
from app.models.face_embedding import FaceEmbedding
from app.models.user import User
from app.services.face_detection import FaceDetector
import pickle
import os
from datetime import datetime

logger = logging.getLogger(__name__)


class FaceService:
    """Service for managing face encodings in database"""
    
    def __init__(self, db_session: Session):
        """
        Initialize face service
        
        Args:
            db_session: Database session
        """
        self.db = db_session
        self.face_detector = FaceDetector()
        logger.info("FaceService initialized")
    
    def register_employee_face(self, employee_code: str, face_encoding: np.ndarray, 
                             image_path: str = None) -> Dict[str, Any]:
        """
        Register face encoding for an employee
        
        Args:
            employee_code: Employee code
            face_encoding: Face encoding array
            image_path: Optional path to face image
            
        Returns:
            Registration result
        """
        try:
            # Check if employee exists
            employee = self.db.query(Employee).filter(Employee.employee_code == employee_code).first()
            if not employee:
                return {
                    'success': False,
                    'message': f'Employee {employee_code} not found',
                    'employee_code': employee_code
                }
            
            # Store encoding as binary using pickle via model helper
            employee.set_face_encoding(face_encoding)
            if image_path:
                employee.photo_path = image_path
            
            self.db.commit()
            
            logger.info(f"Face registered for employee {employee_code}")
            
            return {
                'success': True,
                'message': 'Face registered successfully',
                'employee_code': employee_code
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error registering face for employee {employee_code}: {str(e)}")
            return {
                'success': False,
                'message': f'Registration failed: {str(e)}',
                'employee_code': employee_code
            }
    
    def get_employee_face_encoding(self, employee_code: str) -> Optional[np.ndarray]:
        """
        Get face encoding for an employee
        
        Args:
            employee_code: Employee code
            
        Returns:
            Face encoding array or None
        """
        try:
            employee = self.db.query(Employee).filter(Employee.employee_code == employee_code).first()
            
            if not employee or not employee.face_encoding:
                return None
            
            # Decode from binary pickle via model helper
            return employee.get_face_encoding()
            
        except Exception as e:
            logger.error(f"Error getting face encoding for employee {employee_code}: {str(e)}")
            return None
    
    def get_all_face_encodings(self) -> Tuple[List[np.ndarray], List[str]]:
        """
        Get all face encodings and corresponding employee IDs
        
        Returns:
            Tuple of (encodings, employee_ids)
        """
        try:
            employees = self.db.query(Employee).filter(
                Employee.face_encoding.isnot(None),
                Employee.is_active == True
            ).all()
            
            encodings = []
            employee_ids = []
            
            for employee in employees:
                try:
                    encoding = employee.get_face_encoding()
                    if isinstance(encoding, np.ndarray):
                        encodings.append(encoding)
                        employee_ids.append(employee.employee_code)
                    else:
                        raise ValueError('Decoded encoding is not ndarray')
                except Exception as e:
                    logger.warning(f"Invalid face encoding for employee {employee.employee_code}: {str(e)}")
                    continue
            
            logger.info(f"Retrieved {len(encodings)} face encodings for employees: {employee_ids}")
            return encodings, employee_ids
            
        except Exception as e:
            logger.error(f"Error getting all face encodings: {str(e)}")
            return [], []
    
    def recognize_employee(self, face_encoding: np.ndarray) -> Dict[str, Any]:
        """
        Recognize employee from face encoding
        
        Args:
            face_encoding: Face encoding to match
            
        Returns:
            Recognition result
        """
        try:
            # Get all known encodings
            known_encodings, known_employee_ids = self.get_all_face_encodings()
            
            if not known_encodings:
                return {
                    'success': False,
                    'message': 'No registered faces found',
                    'employee_code': None,
                    'confidence': 0.0
                }
            
            # Find best match
            distances = self.face_detector.find_face_distance(face_encoding, known_encodings)
            
            if not distances:
                return {
                    'success': False,
                    'message': 'Could not calculate face distances',
                    'employee_code': None,
                    'confidence': 0.0
                }
            
            # Find minimum distance
            min_distance = min(distances)
            best_match_index = distances.index(min_distance)
            
            # Check if match is within tolerance
            # Use stricter threshold: require distance < tolerance AND confidence > 0.6
            # This prevents false matches when only one face encoding exists
            if min_distance < self.face_detector.tolerance:
                confidence = 1.0 - min_distance
                
                # Additional check: confidence must be high enough (at least 60%)
                # This ensures we only match when the face is actually similar
                if confidence >= 0.6:
                    employee_code = known_employee_ids[best_match_index]
                    
                    logger.info(f"Employee recognized: {employee_code} (confidence: {confidence:.3f}, distance: {min_distance:.3f})")
                    
                    return {
                        'success': True,
                        'message': 'Employee recognized',
                        'employee_code': employee_code,
                        'confidence': confidence,
                        'distance': min_distance
                    }
                else:
                    logger.warning(f"Match found but confidence too low: {confidence:.3f} < 0.6 (distance: {min_distance:.3f})")
                    return {
                        'success': False,
                        'message': f'Face detected but confidence too low ({confidence:.1%}). Please register your face.',
                        'employee_code': None,
                        'confidence': confidence,
                        'distance': min_distance
                    }
            else:
                logger.info(f"No match found. Min distance: {min_distance:.3f} (tolerance: {self.face_detector.tolerance})")
                return {
                    'success': False,
                    'message': 'No matching face found. Please register your face.',
                    'employee_code': None,
                    'confidence': 0.0,
                    'distance': min_distance
                }
                
        except Exception as e:
            logger.error(f"Error recognizing employee: {str(e)}")
            return {
                'success': False,
                'message': f'Recognition failed: {str(e)}',
                'employee_code': None,
                'confidence': 0.0
            }
    
    def update_employee_face(self, employee_code: str, face_encoding: np.ndarray, 
                           image_path: str = None) -> Dict[str, Any]:
        """
        Update face encoding for an employee
        
        Args:
            employee_code: Employee code
            face_encoding: New face encoding
            image_path: Optional new image path
            
        Returns:
            Update result
        """
        try:
            employee = self.db.query(Employee).filter(Employee.employee_code == employee_code).first()
            
            if not employee:
                return {
                    'success': False,
                    'message': f'Employee {employee_code} not found',
                    'employee_code': employee_code
                }
            
            # Update face encoding as binary
            employee.set_face_encoding(face_encoding)
            if image_path:
                employee.photo_path = image_path
            
            self.db.commit()
            
            logger.info(f"Face updated for employee {employee_code}")
            
            return {
                'success': True,
                'message': 'Face updated successfully',
                'employee_code': employee_code
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating face for employee {employee_code}: {str(e)}")
            return {
                'success': False,
                'message': f'Update failed: {str(e)}',
                'employee_code': employee_code
            }
    
    def delete_employee_face(self, employee_code: str) -> Dict[str, Any]:
        """
        Delete face encoding for an employee
        
        Args:
            employee_code: Employee code
            
        Returns:
            Deletion result
        """
        try:
            employee = self.db.query(Employee).filter(Employee.employee_code == employee_code).first()
            
            if not employee:
                return {
                    'success': False,
                    'message': f'Employee {employee_code} not found',
                    'employee_code': employee_code
                }
            
            # Verify face encoding exists before deletion
            had_encoding = employee.face_encoding is not None
            
            # Clear face data - explicitly set to None to ensure deletion
            employee.face_encoding = None
            employee.photo_path = None
            
            # Force commit to ensure database is updated
            self.db.commit()
            
            # Verify deletion succeeded
            self.db.refresh(employee)
            if employee.face_encoding is not None:
                logger.error(f"Face encoding still exists after deletion for {employee_code}")
                return {
                    'success': False,
                    'message': 'Face encoding deletion failed - encoding still exists',
                    'employee_code': employee_code
                }
            
            logger.info(f"Face deleted for employee {employee_code} (had encoding: {had_encoding})")
            
            return {
                'success': True,
                'message': 'Face deleted successfully',
                'employee_code': employee_code
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error deleting face for employee {employee_code}: {str(e)}")
            return {
                'success': False,
                'message': f'Deletion failed: {str(e)}',
                'employee_code': employee_code
            }
    
    def get_face_statistics(self) -> Dict[str, Any]:
        """
        Get face registration statistics
        
        Returns:
            Statistics dictionary
        """
        try:
            total_employees = self.db.query(Employee).count()
            employees_with_faces = self.db.query(Employee).filter(
                Employee.face_encoding.isnot(None)
            ).count()
            
            return {
                'total_employees': total_employees,
                'employees_with_faces': employees_with_faces,
                'registration_rate': (employees_with_faces / total_employees * 100) if total_employees > 0 else 0,
                'recent_registrations': 0
            }
            
        except Exception as e:
            logger.error(f"Error getting face statistics: {str(e)}")
            return {
                'total_employees': 0,
                'employees_with_faces': 0,
                'registration_rate': 0,
                'recent_registrations': 0
            }
    
    def backup_face_encodings(self, backup_path: str) -> Dict[str, Any]:
        """
        Backup all face encodings to file
        
        Args:
            backup_path: Path to backup file
            
        Returns:
            Backup result
        """
        try:
            encodings, employee_ids = self.get_all_face_encodings()
            
            backup_data = {
                'timestamp': datetime.utcnow().isoformat(),
                'total_encodings': len(encodings),
                'encodings': [encoding.tolist() for encoding in encodings],
                'employee_ids': employee_ids
            }
            
            # Create backup directory if it doesn't exist
            os.makedirs(os.path.dirname(backup_path), exist_ok=True)
            
            # Save backup
            with open(backup_path, 'wb') as f:
                pickle.dump(backup_data, f)
            
            logger.info(f"Face encodings backed up to {backup_path}")
            
            return {
                'success': True,
                'message': 'Backup created successfully',
                'backup_path': backup_path,
                'total_encodings': len(encodings)
            }
            
        except Exception as e:
            logger.error(f"Error backing up face encodings: {str(e)}")
            return {
                'success': False,
                'message': f'Backup failed: {str(e)}',
                'backup_path': backup_path
            }
    
    def restore_face_encodings(self, backup_path: str) -> Dict[str, Any]:
        """
        Restore face encodings from backup file
        
        Args:
            backup_path: Path to backup file
            
        Returns:
            Restore result
        """
        try:
            if not os.path.exists(backup_path):
                return {
                    'success': False,
                    'message': f'Backup file not found: {backup_path}',
                    'backup_path': backup_path
                }
            
            # Load backup data
            with open(backup_path, 'rb') as f:
                backup_data = pickle.load(f)
            
            encodings = [np.array(encoding) for encoding in backup_data['encodings']]
            employee_ids = backup_data['employee_ids']
            
            # Restore encodings
            restored_count = 0
            for encoding, employee_id in zip(encodings, employee_ids):
                result = self.register_employee_face(employee_id, encoding)
                if result['success']:
                    restored_count += 1
            
            logger.info(f"Restored {restored_count} face encodings from {backup_path}")
            
            return {
                'success': True,
                'message': f'Restored {restored_count} face encodings',
                'backup_path': backup_path,
                'restored_count': restored_count,
                'total_in_backup': len(encodings)
            }
            
        except Exception as e:
            logger.error(f"Error restoring face encodings: {str(e)}")
            return {
                'success': False,
                'message': f'Restore failed: {str(e)}',
                'backup_path': backup_path
            }
    
    def validate_face_encoding(self, face_encoding: np.ndarray) -> bool:
        """
        Validate face encoding format
        
        Args:
            face_encoding: Face encoding to validate
            
        Returns:
            True if valid, False otherwise
        """
        try:
            # Check if it's a numpy array
            if not isinstance(face_encoding, np.ndarray):
                return False
            
            # Check shape (should be 1D with 128 elements for face_recognition)
            if face_encoding.shape != (128,):
                return False
            
            # Check for NaN or infinite values
            if np.any(np.isnan(face_encoding)) or np.any(np.isinf(face_encoding)):
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating face encoding: {str(e)}")
            return False
    
    # ========== MULTI-EMBEDDING METHODS ==========
    
    def add_face_embedding(self, employee_code: str, embedding: np.ndarray,
                          variant_type: str = 'default', 
                          embedding_type: str = 'standard',
                          description: str = None,
                          photo_path: str = None,
                          quality_score: float = None,
                          set_as_primary: bool = False) -> Dict[str, Any]:
        """
        Add a new face embedding for an employee (multi-embedding support)
        
        Args:
            employee_code: Employee code
            embedding: Face embedding array
            variant_type: Variant type ('no_glasses', 'with_glasses', 'default', etc.)
            embedding_type: Type of embedding ('standard', 'deepface', etc.)
            description: Optional description
            photo_path: Optional path to source image
            quality_score: Optional quality score (0-1)
            set_as_primary: Whether to set this as primary embedding
            
        Returns:
            Registration result
        """
        try:
            # Check if employee exists
            employee = self.db.query(Employee).filter(Employee.employee_code == employee_code).first()
            if not employee:
                return {
                    'success': False,
                    'message': f'Employee {employee_code} not found',
                    'employee_code': employee_code
                }
            
            # If set_as_primary, unset other primary embeddings
            if set_as_primary:
                self.db.query(FaceEmbedding).filter_by(
                    employee_code=employee_code,
                    is_primary=True
                ).update({'is_primary': False})
            
            # Create new embedding record
            face_embedding = FaceEmbedding(
                employee_id=employee.id,
                employee_code=employee_code,
                variant_type=variant_type,
                embedding_type=embedding_type,
                description=description,
                photo_path=photo_path,
                quality_score=quality_score,
                is_primary=set_as_primary or (not self.has_any_embeddings(employee_code)),
                is_active=True
            )
            face_embedding.set_embedding(embedding)
            
            self.db.add(face_embedding)
            self.db.commit()
            
            logger.info(f"Face embedding added for employee {employee_code} (variant: {variant_type})")
            
            return {
                'success': True,
                'message': 'Face embedding added successfully',
                'employee_code': employee_code,
                'embedding_id': face_embedding.id,
                'variant_type': variant_type,
                'is_primary': face_embedding.is_primary
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error adding face embedding for employee {employee_code}: {str(e)}")
            return {
                'success': False,
                'message': f'Failed to add embedding: {str(e)}',
                'employee_code': employee_code
            }
    
    def get_employee_embeddings(self, employee_code: str, active_only: bool = True) -> List[FaceEmbedding]:
        """
        Get all embeddings for an employee
        
        Args:
            employee_code: Employee code
            active_only: Only return active embeddings
            
        Returns:
            List of FaceEmbedding objects
        """
        try:
            return FaceEmbedding.get_all_embeddings(employee_code, active_only=active_only)
        except Exception as e:
            logger.error(f"Error getting embeddings for employee {employee_code}: {str(e)}")
            return []
    
    def get_employee_embeddings_dict(self, employee_code: str, active_only: bool = True) -> Dict[str, np.ndarray]:
        """
        Get all embeddings for an employee as dictionary {variant_type: embedding}
        
        Args:
            employee_code: Employee code
            active_only: Only return active embeddings
            
        Returns:
            Dictionary of {variant_type: embedding}
        """
        try:
            embeddings = self.get_employee_embeddings(employee_code, active_only)
            result = {}
            for emb in embeddings:
                embedding_data = emb.get_embedding()
                if embedding_data is not None:
                    variant = emb.variant_type or 'default'
                    result[variant] = embedding_data
            return result
        except Exception as e:
            logger.error(f"Error getting embeddings dict for employee {employee_code}: {str(e)}")
            return {}
    
    def get_all_face_embeddings_multi(
        self, 
        embedding_type: str = None, 
        embedding_dim: int = None
    ) -> Tuple[List[np.ndarray], List[str]]:
        """
        Get all face embeddings from multi-embedding table (for recognition)
        Returns all active embeddings from all employees
        
        Returns:
            Tuple of (embeddings, employee_codes)
        """
        try:
            query = self.db.query(FaceEmbedding).filter(
                FaceEmbedding.is_active == True
            )
            
            if embedding_type:
                query = query.filter(FaceEmbedding.embedding_type == embedding_type)
            
            embeddings_list = query.all()
            
            encodings = []
            employee_codes = []
            
            for emb in embeddings_list:
                embedding = emb.get_embedding()
                if embedding is None:
                    continue
                
                if embedding_dim and embedding.size != embedding_dim:
                    logger.debug(
                        "Skip embedding %s due to dimension mismatch (expected %s, got %s)",
                        emb.id,
                        embedding_dim,
                        embedding.size
                    )
                    continue
                
                encodings.append(embedding)
                employee_codes.append(emb.employee_code)
            
            logger.info(f"Retrieved {len(encodings)} face embeddings from multi-embedding table")
            return encodings, employee_codes
            
        except Exception as e:
            logger.error(f"Error getting all face embeddings: {str(e)}")
            return [], []
    
    def recognize_employee_multi(self, face_encoding: np.ndarray, use_multi_embedding: bool = True) -> Dict[str, Any]:
        """
        Recognize employee using multi-embedding system
        Compares against all embeddings and returns best match
        
        Args:
            face_encoding: Face encoding to match
            use_multi_embedding: Use multi-embedding table (True) or legacy (False)
            
        Returns:
            Recognition result
        """
        try:
            if use_multi_embedding:
                # Get all embeddings from multi-embedding table
                known_encodings, known_employee_codes = self.get_all_face_embeddings_multi()
            else:
                # Fallback to legacy method
                known_encodings, known_employee_codes = self.get_all_face_encodings()
            
            if not known_encodings:
                return {
                    'success': False,
                    'message': 'No registered faces found',
                    'employee_code': None,
                    'confidence': 0.0
                }
            
            # Find best match across all embeddings
            distances = self.face_detector.find_face_distance(face_encoding, known_encodings)
            
            if not distances:
                return {
                    'success': False,
                    'message': 'Could not calculate face distances',
                    'employee_code': None,
                    'confidence': 0.0
                }
            
            # Find minimum distance
            min_distance = min(distances)
            best_match_index = distances.index(min_distance)
            best_employee_code = known_employee_codes[best_match_index]
            
            # Check if match is within tolerance
            if min_distance < self.face_detector.tolerance:
                confidence = 1.0 - min_distance
                
                if confidence >= 0.6:
                    logger.info(f"Employee recognized: {best_employee_code} (confidence: {confidence:.3f}, distance: {min_distance:.3f})")
                    
                    return {
                        'success': True,
                        'message': 'Employee recognized',
                        'employee_code': best_employee_code,
                        'confidence': confidence,
                        'distance': min_distance,
                        'method': 'multi_embedding' if use_multi_embedding else 'legacy'
                    }
                else:
                    logger.warning(f"Match found but confidence too low: {confidence:.3f} < 0.6")
                    return {
                        'success': False,
                        'message': f'Face detected but confidence too low ({confidence:.1%}). Please register your face.',
                        'employee_code': None,
                        'confidence': confidence,
                        'distance': min_distance
                    }
            else:
                logger.info(f"No match found. Min distance: {min_distance:.3f}")
                return {
                    'success': False,
                    'message': 'No matching face found. Please register your face.',
                    'employee_code': None,
                    'confidence': 0.0,
                    'distance': min_distance
                }
                
        except Exception as e:
            logger.error(f"Error recognizing employee: {str(e)}")
            return {
                'success': False,
                'message': f'Recognition failed: {str(e)}',
                'employee_code': None,
                'confidence': 0.0
            }
    
    def delete_face_embedding(self, embedding_id: int) -> Dict[str, Any]:
        """
        Delete a specific face embedding
        
        Args:
            embedding_id: ID of embedding to delete
            
        Returns:
            Deletion result
        """
        try:
            embedding = self.db.query(FaceEmbedding).filter_by(id=embedding_id).first()
            
            if not embedding:
                return {
                    'success': False,
                    'message': f'Embedding {embedding_id} not found',
                    'embedding_id': embedding_id
                }
            
            employee_code = embedding.employee_code
            self.db.delete(embedding)
            self.db.commit()
            
            logger.info(f"Face embedding {embedding_id} deleted for employee {employee_code}")
            
            return {
                'success': True,
                'message': 'Face embedding deleted successfully',
                'embedding_id': embedding_id,
                'employee_code': employee_code
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error deleting face embedding {embedding_id}: {str(e)}")
            return {
                'success': False,
                'message': f'Deletion failed: {str(e)}',
                'embedding_id': embedding_id
            }
    
    def delete_all_employee_embeddings(self, employee_code: str) -> Dict[str, Any]:
        """
        Delete all embeddings for an employee
        
        Args:
            employee_code: Employee code
            
        Returns:
            Deletion result
        """
        try:
            count = self.db.query(FaceEmbedding).filter_by(employee_code=employee_code).delete()
            self.db.commit()
            
            logger.info(f"Deleted {count} embeddings for employee {employee_code}")
            
            return {
                'success': True,
                'message': f'Deleted {count} embeddings',
                'employee_code': employee_code,
                'deleted_count': count
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error deleting all embeddings for employee {employee_code}: {str(e)}")
            return {
                'success': False,
                'message': f'Deletion failed: {str(e)}',
                'employee_code': employee_code
            }
    
    def set_primary_embedding(self, embedding_id: int) -> Dict[str, Any]:
        """
        Set an embedding as primary for an employee
        
        Args:
            embedding_id: ID of embedding to set as primary
            
        Returns:
            Result
        """
        try:
            embedding = self.db.query(FaceEmbedding).filter_by(id=embedding_id).first()
            
            if not embedding:
                return {
                    'success': False,
                    'message': f'Embedding {embedding_id} not found',
                    'embedding_id': embedding_id
                }
            
            # Unset other primary embeddings for this employee
            self.db.query(FaceEmbedding).filter_by(
                employee_code=embedding.employee_code,
                is_primary=True
            ).update({'is_primary': False})
            
            # Set this one as primary
            embedding.is_primary = True
            self.db.commit()
            
            logger.info(f"Set embedding {embedding_id} as primary for employee {embedding.employee_code}")
            
            return {
                'success': True,
                'message': 'Primary embedding set successfully',
                'embedding_id': embedding_id,
                'employee_code': embedding.employee_code
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error setting primary embedding {embedding_id}: {str(e)}")
            return {
                'success': False,
                'message': f'Failed to set primary: {str(e)}',
                'embedding_id': embedding_id
            }
    
    def has_any_embeddings(self, employee_code: str) -> bool:
        """
        Check if employee has any embeddings
        
        Args:
            employee_code: Employee code
            
        Returns:
            True if has embeddings, False otherwise
        """
        try:
            count = self.db.query(FaceEmbedding).filter_by(
                employee_code=employee_code,
                is_active=True
            ).count()
            return count > 0
        except Exception as e:
            logger.error(f"Error checking embeddings for employee {employee_code}: {str(e)}")
            return False
    
    def get_embedding_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about embeddings
        
        Returns:
            Statistics dictionary
        """
        try:
            total_embeddings = self.db.query(FaceEmbedding).filter_by(is_active=True).count()
            total_employees_with_embeddings = self.db.query(FaceEmbedding.employee_code).filter_by(
                is_active=True
            ).distinct().count()
            
            # Count by variant type
            variant_counts = {}
            variants = self.db.query(FaceEmbedding.variant_type).filter_by(is_active=True).all()
            for (variant,) in variants:
                variant = variant or 'default'
                variant_counts[variant] = variant_counts.get(variant, 0) + 1
            
            return {
                'total_embeddings': total_embeddings,
                'total_employees_with_embeddings': total_employees_with_embeddings,
                'variant_counts': variant_counts,
                'average_embeddings_per_employee': total_embeddings / total_employees_with_embeddings if total_employees_with_embeddings > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Error getting embedding statistics: {str(e)}")
            return {
                'total_embeddings': 0,
                'total_employees_with_embeddings': 0,
                'variant_counts': {},
                'average_embeddings_per_employee': 0
            }
