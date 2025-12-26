"""Permission model for fine-grained access control"""
from app import db
from datetime import datetime
from typing import List, Set


class Permission(db.Model):
    """Permission definition"""
    
    __tablename__ = 'permissions'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False, index=True)  # e.g., "employee.view"
    display_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(50), nullable=True)  # e.g., "employee", "attendance", "report"
    
    created_at = db.Column(db.DateTime, default=datetime.now, nullable=False)
    
    # Relationships
    role_permissions = db.relationship('RolePermission', back_populates='permission', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Permission {self.name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'display_name': self.display_name,
            'description': self.description,
            'category': self.category
        }


class Role(db.Model):
    """Role definition with permissions"""
    
    __tablename__ = 'roles'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False, index=True)  # e.g., "admin", "manager", "viewer"
    display_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    is_system = db.Column(db.Boolean, default=False, nullable=False)  # System roles cannot be deleted
    
    created_at = db.Column(db.DateTime, default=datetime.now, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    role_permissions = db.relationship('RolePermission', back_populates='role', cascade='all, delete-orphan')
    user_roles = db.relationship('UserRole', back_populates='role', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Role {self.name}>'
    
    def get_permissions(self) -> List[Permission]:
        """Get all permissions for this role"""
        return [rp.permission for rp in self.role_permissions]
    
    def has_permission(self, permission_name: str) -> bool:
        """Check if role has specific permission"""
        return any(rp.permission.name == permission_name for rp in self.role_permissions)
    
    def add_permission(self, permission: Permission):
        """Add permission to role"""
        if not self.has_permission(permission.name):
            rp = RolePermission(role_id=self.id, permission_id=permission.id)
            db.session.add(rp)
    
    def remove_permission(self, permission: Permission):
        """Remove permission from role"""
        rp = RolePermission.query.filter_by(role_id=self.id, permission_id=permission.id).first()
        if rp:
            db.session.delete(rp)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'display_name': self.display_name,
            'description': self.description,
            'is_system': self.is_system,
            'permissions': [p.to_dict() for p in self.get_permissions()]
        }


class RolePermission(db.Model):
    """Many-to-many relationship between Role and Permission"""
    
    __tablename__ = 'role_permissions'
    
    id = db.Column(db.Integer, primary_key=True)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False, index=True)
    permission_id = db.Column(db.Integer, db.ForeignKey('permissions.id'), nullable=False, index=True)
    
    created_at = db.Column(db.DateTime, default=datetime.now, nullable=False)
    
    # Relationships
    role = db.relationship('Role', back_populates='role_permissions')
    permission = db.relationship('Permission', back_populates='role_permissions')
    
    __table_args__ = (
        db.UniqueConstraint('role_id', 'permission_id', name='uq_role_permission'),
    )
    
    def __repr__(self):
        return f'<RolePermission role={self.role_id} permission={self.permission_id}>'


class UserRole(db.Model):
    """Many-to-many relationship between User and Role (for multi-role support)"""
    
    __tablename__ = 'user_roles'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False, index=True)
    
    created_at = db.Column(db.DateTime, default=datetime.now, nullable=False)
    
    # Relationships
    user = db.relationship('User', backref='user_roles_assoc')
    role = db.relationship('Role', back_populates='user_roles')
    
    __table_args__ = (
        db.UniqueConstraint('user_id', 'role_id', name='uq_user_role'),
    )
    
    def __repr__(self):
        return f'<UserRole user={self.user_id} role={self.role_id}>'


# Permission constants
class Permissions:
    """Permission name constants"""
    # Employee permissions
    EMPLOYEE_VIEW = 'employee.view'
    EMPLOYEE_CREATE = 'employee.create'
    EMPLOYEE_EDIT = 'employee.edit'
    EMPLOYEE_DELETE = 'employee.delete'
    EMPLOYEE_MANAGE_FACE = 'employee.manage_face'
    
    # Attendance permissions
    ATTENDANCE_VIEW = 'attendance.view'
    ATTENDANCE_CREATE = 'attendance.create'
    ATTENDANCE_EDIT = 'attendance.edit'
    ATTENDANCE_DELETE = 'attendance.delete'
    ATTENDANCE_MANUAL_CHECK = 'attendance.manual_check'
    
    # Department permissions
    DEPARTMENT_VIEW = 'department.view'
    DEPARTMENT_CREATE = 'department.create'
    DEPARTMENT_EDIT = 'department.edit'
    DEPARTMENT_DELETE = 'department.delete'
    
    # Schedule permissions
    SCHEDULE_VIEW = 'schedule.view'
    SCHEDULE_CREATE = 'schedule.create'
    SCHEDULE_EDIT = 'schedule.edit'
    SCHEDULE_DELETE = 'schedule.delete'
    
    # Report permissions
    REPORT_VIEW = 'report.view'
    REPORT_EXPORT = 'report.export'
    REPORT_VIEW_ALL = 'report.view_all'  # View reports for all departments
    
    # User & Role permissions
    USER_VIEW = 'user.view'
    USER_CREATE = 'user.create'
    USER_EDIT = 'user.edit'
    USER_DELETE = 'user.delete'
    ROLE_MANAGE = 'role.manage'
    
    # Policy permissions
    POLICY_VIEW = 'policy.view'
    POLICY_CREATE = 'policy.create'
    POLICY_EDIT = 'policy.edit'
    POLICY_DELETE = 'policy.delete'
    
    # System permissions
    SYSTEM_SETTINGS = 'system.settings'
    SYSTEM_LOGS = 'system.logs'
    
    @classmethod
    def get_all(cls) -> List[str]:
        """Get all permission names"""
        return [
            cls.EMPLOYEE_VIEW, cls.EMPLOYEE_CREATE, cls.EMPLOYEE_EDIT, cls.EMPLOYEE_DELETE, cls.EMPLOYEE_MANAGE_FACE,
            cls.ATTENDANCE_VIEW, cls.ATTENDANCE_CREATE, cls.ATTENDANCE_EDIT, cls.ATTENDANCE_DELETE, cls.ATTENDANCE_MANUAL_CHECK,
            cls.DEPARTMENT_VIEW, cls.DEPARTMENT_CREATE, cls.DEPARTMENT_EDIT, cls.DEPARTMENT_DELETE,
            cls.SCHEDULE_VIEW, cls.SCHEDULE_CREATE, cls.SCHEDULE_EDIT, cls.SCHEDULE_DELETE,
            cls.REPORT_VIEW, cls.REPORT_EXPORT, cls.REPORT_VIEW_ALL,
            cls.USER_VIEW, cls.USER_CREATE, cls.USER_EDIT, cls.USER_DELETE, cls.ROLE_MANAGE,
            cls.POLICY_VIEW, cls.POLICY_CREATE, cls.POLICY_EDIT, cls.POLICY_DELETE,
            cls.SYSTEM_SETTINGS, cls.SYSTEM_LOGS
        ]

