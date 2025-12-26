"""Permission decorators and utilities"""
from functools import wraps
from flask import abort, current_app
from flask_login import current_user


def permission_required(permission_name: str):
    """
    Decorator to require specific permission
    
    Usage:
        @bp.route('/employees')
        @login_required
        @permission_required('employee.view')
        def list_employees():
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            
            if not current_user.has_permission(permission_name):
                current_app.logger.warning(
                    f"User {current_user.username} attempted to access {f.__name__} "
                    f"without permission {permission_name}"
                )
                abort(403)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def any_permission_required(*permission_names: str):
    """
    Decorator to require any of the specified permissions
    
    Usage:
        @any_permission_required('employee.view', 'employee.edit')
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            
            if not current_user.has_any_permission(*permission_names):
                current_app.logger.warning(
                    f"User {current_user.username} attempted to access {f.__name__} "
                    f"without any of permissions: {permission_names}"
                )
                abort(403)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def all_permissions_required(*permission_names: str):
    """
    Decorator to require all of the specified permissions
    
    Usage:
        @all_permissions_required('employee.view', 'employee.edit')
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            
            if not current_user.has_all_permissions(*permission_names):
                current_app.logger.warning(
                    f"User {current_user.username} attempted to access {f.__name__} "
                    f"without all permissions: {permission_names}"
                )
                abort(403)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def role_required(*roles: str):
    """
    Decorator to require specific role(s) (legacy support)
    
    Usage:
        @role_required('admin', 'manager')
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            
            if current_user.role not in roles:
                current_app.logger.warning(
                    f"User {current_user.username} attempted to access {f.__name__} "
                    f"without required role. Has: {current_user.role}, Required: {roles}"
                )
                abort(403)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

