"""User model for authentication"""
from app import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime,timezone


class User(UserMixin, db.Model):
    """User model for system authentication"""
    
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='admin', nullable=False)  # admin, manager, viewer
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    last_login = db.Column(db.DateTime, nullable=True)
    failed_login_attempts = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.now, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    logs = db.relationship('SystemLog', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<User {self.username}>'
    
    def set_password(self, password):
        """Hash and set password"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check if password matches"""
        return check_password_hash(self.password_hash, password)
    
    def update_last_login(self):
        """Update last login timestamp"""
        self.last_login = datetime.now(timezone.utc)
        self.failed_login_attempts = 0
        db.session.commit()
    
    def increment_failed_login(self):
        """Increment failed login attempts"""
        self.failed_login_attempts += 1
        db.session.commit()
    
    def reset_failed_login(self):
        """Reset failed login attempts"""
        self.failed_login_attempts = 0
        db.session.commit()
    
    def has_role(self, role):
        """Check if user has specific role"""
        return self.role == role
    
    def is_admin(self):
        """Check if user is admin"""
        return self.role == 'admin'
    
    def get_roles(self):
        """Get all roles for this user (from UserRole)"""
        from app.models.permission import UserRole, Role
        user_roles = UserRole.query.filter_by(user_id=self.id).all()
        return [ur.role for ur in user_roles]
    
    def has_permission(self, permission_name: str) -> bool:
        """
        Check if user has specific permission
        
        Priority:
        1. Check permission-based roles (UserRole)
        2. Fallback to legacy role-based (self.role)
        """
        from app.models.permission import UserRole, Role, Permissions
        
        # Check permission-based roles
        user_roles = UserRole.query.filter_by(user_id=self.id).all()
        for ur in user_roles:
            if ur.role.has_permission(permission_name):
                return True
        
        # Fallback to legacy role-based check
        if self.role == 'admin':
            return True  # Admin has all permissions
        elif self.role == 'manager':
            # Manager has most permissions except system settings
            return permission_name not in [Permissions.SYSTEM_SETTINGS, Permissions.ROLE_MANAGE]
        elif self.role == 'viewer':
            # Viewer only has view permissions
            return permission_name.endswith('.view')
        
        return False
    
    def has_any_permission(self, *permission_names: str) -> bool:
        """Check if user has any of the specified permissions"""
        return any(self.has_permission(p) for p in permission_names)
    
    def has_all_permissions(self, *permission_names: str) -> bool:
        """Check if user has all of the specified permissions"""
        return all(self.has_permission(p) for p in permission_names)
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'is_active': self.is_active,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'created_at': self.created_at.isoformat()
        }


@login_manager.user_loader
def load_user(user_id):
    """Load user by ID for Flask-Login"""
    return User.query.get(int(user_id))

