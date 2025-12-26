"""Face Embedding model for multi-embedding support"""
from app import db
from datetime import datetime
import pickle
import numpy as np
from typing import Optional


class FaceEmbedding(db.Model):
    """Model for storing multiple face embeddings per employee"""
    
    __tablename__ = 'face_embeddings'
    
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False, index=True)
    employee_code = db.Column(db.String(20), nullable=False, index=True)  # Denormalized for faster queries
    
    # Embedding data
    embedding_data = db.Column(db.LargeBinary, nullable=False)  # Stored as binary (pickle)
    embedding_type = db.Column(db.String(50), nullable=True)  # 'standard', 'deepface', etc.
    embedding_shape = db.Column(db.String(50), nullable=True)  # e.g., '(128,)' or '(512,)'
    
    # Metadata
    variant_type = db.Column(db.String(50), nullable=True)  # 'no_glasses', 'with_glasses', 'default', etc.
    description = db.Column(db.String(255), nullable=True)  # User description
    photo_path = db.Column(db.String(255), nullable=True)  # Path to source image
    
    # Quality metrics
    quality_score = db.Column(db.Float, nullable=True)  # Face quality score (0-1)
    is_primary = db.Column(db.Boolean, default=False, nullable=False)  # Primary embedding for this employee
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.now, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    employee = db.relationship('Employee', backref='face_embeddings', lazy='joined')
    
    def __repr__(self):
        return f'<FaceEmbedding {self.id}: {self.employee_code} ({self.variant_type})>'
    
    def set_embedding(self, embedding: np.ndarray):
        """Store embedding as binary"""
        if embedding is not None:
            self.embedding_data = pickle.dumps(embedding)
            self.embedding_shape = str(embedding.shape)
    
    def get_embedding(self) -> Optional[np.ndarray]:
        """Retrieve embedding from binary"""
        if self.embedding_data:
            try:
                embedding = pickle.loads(self.embedding_data)
                if isinstance(embedding, np.ndarray):
                    return embedding
                else:
                    # Convert list to numpy array if needed
                    return np.array(embedding)
            except Exception as e:
                return None
        return None
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'employee_id': self.employee_id,
            'employee_code': self.employee_code,
            'variant_type': self.variant_type,
            'description': self.description,
            'embedding_type': self.embedding_type,
            'embedding_shape': self.embedding_shape,
            'photo_path': self.photo_path,
            'quality_score': self.quality_score,
            'is_primary': self.is_primary,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @staticmethod
    def get_primary_embedding(employee_code: str) -> Optional['FaceEmbedding']:
        """Get primary embedding for an employee"""
        return FaceEmbedding.query.filter_by(
            employee_code=employee_code,
            is_primary=True,
            is_active=True
        ).first()
    
    @staticmethod
    def get_all_embeddings(employee_code: str, active_only: bool = True) -> list:
        """Get all embeddings for an employee"""
        query = FaceEmbedding.query.filter_by(employee_code=employee_code)
        if active_only:
            query = query.filter_by(is_active=True)
        return query.order_by(FaceEmbedding.is_primary.desc(), FaceEmbedding.created_at.desc()).all()
    
    @staticmethod
    def get_embeddings_by_variant(employee_code: str, variant_type: str) -> list:
        """Get embeddings by variant type"""
        return FaceEmbedding.query.filter_by(
            employee_code=employee_code,
            variant_type=variant_type,
            is_active=True
        ).all()

