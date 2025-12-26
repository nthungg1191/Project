"""Service for managing permissions and roles"""
from app import db
from app.models.permission import Permission, Role, RolePermission, UserRole, Permissions
from app.models.user import User
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)


class PermissionService:
    """Service for permission management"""
    
    @staticmethod
    def initialize_permissions():
        """Initialize all permissions in database"""
        permission_data = [
            # Employee permissions
            ('employee.view', 'Xem nhân viên', 'Xem danh sách và thông tin nhân viên', 'employee'),
            ('employee.create', 'Tạo nhân viên', 'Thêm nhân viên mới', 'employee'),
            ('employee.edit', 'Sửa nhân viên', 'Chỉnh sửa thông tin nhân viên', 'employee'),
            ('employee.delete', 'Xóa nhân viên', 'Xóa nhân viên khỏi hệ thống', 'employee'),
            ('employee.manage_face', 'Quản lý khuôn mặt', 'Thêm/sửa/xóa face embeddings', 'employee'),
            
            # Attendance permissions
            ('attendance.view', 'Xem chấm công', 'Xem lịch sử chấm công', 'attendance'),
            ('attendance.create', 'Tạo chấm công', 'Tạo bản ghi chấm công mới', 'attendance'),
            ('attendance.edit', 'Sửa chấm công', 'Chỉnh sửa bản ghi chấm công', 'attendance'),
            ('attendance.delete', 'Xóa chấm công', 'Xóa bản ghi chấm công', 'attendance'),
            ('attendance.manual_check', 'Chấm công thủ công', 'Thực hiện chấm công thủ công', 'attendance'),
            
            # Department permissions
            ('department.view', 'Xem phòng ban', 'Xem danh sách phòng ban', 'department'),
            ('department.create', 'Tạo phòng ban', 'Thêm phòng ban mới', 'department'),
            ('department.edit', 'Sửa phòng ban', 'Chỉnh sửa thông tin phòng ban', 'department'),
            ('department.delete', 'Xóa phòng ban', 'Xóa phòng ban', 'department'),
            
            # Schedule permissions
            ('schedule.view', 'Xem lịch làm việc', 'Xem lịch làm việc nhân viên', 'schedule'),
            ('schedule.create', 'Tạo lịch làm việc', 'Tạo lịch làm việc mới', 'schedule'),
            ('schedule.edit', 'Sửa lịch làm việc', 'Chỉnh sửa lịch làm việc', 'schedule'),
            ('schedule.delete', 'Xóa lịch làm việc', 'Xóa lịch làm việc', 'schedule'),
            
            # Report permissions
            ('report.view', 'Xem báo cáo', 'Xem các báo cáo chấm công', 'report'),
            ('report.export', 'Xuất báo cáo', 'Xuất báo cáo ra file Excel/PDF', 'report'),
            ('report.view_all', 'Xem tất cả báo cáo', 'Xem báo cáo của tất cả phòng ban', 'report'),
            
            # User & Role permissions
            ('user.view', 'Xem người dùng', 'Xem danh sách người dùng', 'user'),
            ('user.create', 'Tạo người dùng', 'Thêm người dùng mới', 'user'),
            ('user.edit', 'Sửa người dùng', 'Chỉnh sửa thông tin người dùng', 'user'),
            ('user.delete', 'Xóa người dùng', 'Xóa người dùng', 'user'),
            ('role.manage', 'Quản lý vai trò', 'Quản lý roles và permissions', 'user'),
            
            # Policy permissions
            ('policy.view', 'Xem chính sách', 'Xem các chính sách chấm công', 'policy'),
            ('policy.create', 'Tạo chính sách', 'Tạo chính sách chấm công mới', 'policy'),
            ('policy.edit', 'Sửa chính sách', 'Chỉnh sửa chính sách chấm công', 'policy'),
            ('policy.delete', 'Xóa chính sách', 'Xóa chính sách chấm công', 'policy'),
            
            # System permissions
            ('system.settings', 'Cài đặt hệ thống', 'Thay đổi cài đặt hệ thống', 'system'),
            ('system.logs', 'Xem nhật ký', 'Xem nhật ký hệ thống', 'system'),
        ]
        
        created = 0
        for name, display_name, description, category in permission_data:
            permission = Permission.query.filter_by(name=name).first()
            if not permission:
                permission = Permission(
                    name=name,
                    display_name=display_name,
                    description=description,
                    category=category
                )
                db.session.add(permission)
                created += 1
        
        db.session.commit()
        logger.info(f"Initialized {created} new permissions")
        return created
    
    @staticmethod
    def initialize_roles():
        """Initialize default roles with permissions"""
        # Admin role - all permissions
        admin_role = Role.query.filter_by(name='admin').first()
        if not admin_role:
            admin_role = Role(
                name='admin',
                display_name='Quản trị viên',
                description='Có tất cả quyền trong hệ thống',
                is_system=True
            )
            db.session.add(admin_role)
            db.session.flush()
        
        # Manager role - most permissions except system settings
        manager_role = Role.query.filter_by(name='manager').first()
        if not manager_role:
            manager_role = Role(
                name='manager',
                display_name='Quản lý',
                description='Quản lý nhân viên, chấm công và báo cáo',
                is_system=True
            )
            db.session.add(manager_role)
            db.session.flush()
        
        # Viewer role - view only
        viewer_role = Role.query.filter_by(name='viewer').first()
        if not viewer_role:
            viewer_role = Role(
                name='viewer',
                display_name='Người xem',
                description='Chỉ xem thông tin, không được chỉnh sửa',
                is_system=True
            )
            db.session.add(viewer_role)
            db.session.flush()
        
        db.session.commit()
        
        # Assign permissions to roles
        all_permissions = Permission.query.all()
        admin_permissions = all_permissions
        
        manager_permissions = [p for p in all_permissions 
                              if not p.name.startswith('system.') and p.name != 'role.manage']
        
        viewer_permissions = [p for p in all_permissions if p.name.endswith('.view')]
        
        # Clear existing role permissions
        RolePermission.query.filter_by(role_id=admin_role.id).delete()
        RolePermission.query.filter_by(role_id=manager_role.id).delete()
        RolePermission.query.filter_by(role_id=viewer_role.id).delete()
        
        # Assign permissions
        for perm in admin_permissions:
            rp = RolePermission(role_id=admin_role.id, permission_id=perm.id)
            db.session.add(rp)
        
        for perm in manager_permissions:
            rp = RolePermission(role_id=manager_role.id, permission_id=perm.id)
            db.session.add(rp)
        
        for perm in viewer_permissions:
            rp = RolePermission(role_id=viewer_role.id, permission_id=perm.id)
            db.session.add(rp)
        
        db.session.commit()
        logger.info("Initialized default roles with permissions")
        
        return {
            'admin': admin_role,
            'manager': manager_role,
            'viewer': viewer_role
        }
    
    @staticmethod
    def assign_role_to_user(user: User, role_name: str):
        """Assign role to user"""
        role = Role.query.filter_by(name=role_name).first()
        if not role:
            raise ValueError(f"Role '{role_name}' not found")
        
        # Check if already assigned
        existing = UserRole.query.filter_by(user_id=user.id, role_id=role.id).first()
        if existing:
            return existing
        
        user_role = UserRole(user_id=user.id, role_id=role.id)
        db.session.add(user_role)
        db.session.commit()
        
        logger.info(f"Assigned role '{role_name}' to user '{user.username}'")
        return user_role
    
    @staticmethod
    def remove_role_from_user(user: User, role_name: str):
        """Remove role from user"""
        role = Role.query.filter_by(name=role_name).first()
        if not role:
            return False
        
        user_role = UserRole.query.filter_by(user_id=user.id, role_id=role.id).first()
        if user_role:
            db.session.delete(user_role)
            db.session.commit()
            logger.info(f"Removed role '{role_name}' from user '{user.username}'")
            return True
        
        return False
    
    @staticmethod
    def create_role(name: str, display_name: str, permission_names: List[str], 
                   description: str = None, is_system: bool = False) -> Role:
        """Create a new role with permissions"""
        role = Role(
            name=name,
            display_name=display_name,
            description=description,
            is_system=is_system
        )
        db.session.add(role)
        db.session.flush()
        
        # Assign permissions
        for perm_name in permission_names:
            permission = Permission.query.filter_by(name=perm_name).first()
            if permission:
                rp = RolePermission(role_id=role.id, permission_id=permission.id)
                db.session.add(rp)
        
        db.session.commit()
        logger.info(f"Created role '{name}' with {len(permission_names)} permissions")
        return role

