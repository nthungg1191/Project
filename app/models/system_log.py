"""System Log model"""
from app import db
from datetime import datetime


class SystemLog(db.Model):
    """System log model for audit trail"""
    
    __tablename__ = 'system_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    action = db.Column(db.String(100), nullable=False, index=True)
    entity_type = db.Column(db.String(50), nullable=True)  # employee, attendance, user, etc.
    entity_id = db.Column(db.Integer, nullable=True)
    details = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(20), default='success', nullable=False)  # success, failure, error
    created_at = db.Column(db.DateTime, default=datetime.now, nullable=False, index=True)
    
    # Composite index for faster queries
    __table_args__ = (
        db.Index('idx_user_action', 'user_id', 'action'),
        db.Index('idx_entity', 'entity_type', 'entity_id'),
    )
    
    def __repr__(self):
        return f'<SystemLog {self.action} by User {self.user_id}>'
    
    @staticmethod
    def log_action(user_id, action, entity_type=None, entity_id=None, 
                   details=None, ip_address=None, user_agent=None, status='success'):
        """Create a new system log entry"""
        log = SystemLog(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
            status=status
        )
        db.session.add(log)
        db.session.commit()
        return log
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'username': self.user.username if self.user else 'System',
            'action': self.action,
            'entity_type': self.entity_type,
            'entity_id': self.entity_id,
            'details': self.details,
            'ip_address': self.ip_address,
            'status': self.status,
            'created_at': self.created_at.isoformat()
        }

