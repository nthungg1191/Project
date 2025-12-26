"""Employee model"""
from app import db
from datetime import datetime
import pickle


class Employee(db.Model):
    """Employee model for workers"""
    
    __tablename__ = 'employees'
    
    id = db.Column(db.Integer, primary_key=True)
    employee_code = db.Column(db.String(20), unique=True, nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    
    # ========== DEPARTMENT: Migration từ String sang FK ==========
    # NEW: Foreign Key (primary)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=True, index=True)
    
    # OLD: String (deprecated - giữ để backward compatibility)
    department = db.Column(db.String(50), nullable=True)  # DEPRECATED: Dùng department_id
    
    # ========== POSITION: Giữ String (đơn giản) ==========
    position = db.Column(db.String(50), nullable=True)
    
    face_encoding = db.Column(db.LargeBinary, nullable=True)  # Legacy single encoding
    photo_path = db.Column(db.String(255), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    hire_date = db.Column(db.Date, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    attendances = db.relationship('Attendance', backref='employee', lazy='dynamic', cascade='all, delete-orphan')
    work_schedules = db.relationship('WorkSchedule', backref='employee', lazy='dynamic', cascade='all, delete-orphan')
    
    @property
    def has_active_face_embeddings(self) -> bool:
        """Return True if employee has any active face embeddings."""
        embeddings = getattr(self, 'face_embeddings', None)
        if not embeddings:
            return False
        try:
            return any(getattr(embedding, 'is_active', False) for embedding in embeddings)
        except TypeError:
            return False

    def __repr__(self):
        return f'<Employee {self.employee_code}: {self.name}>'
    
    # ========== DEPARTMENT HELPER METHODS ==========
    
    def get_department_name(self):
        """Lấy tên phòng ban (ưu tiên department_obj, fallback về department string)"""
        if self.department_obj:
            return self.department_obj.name
        return self.department  # Backward compatibility
    
    def get_department_code(self):
        """Lấy mã phòng ban"""
        if self.department_obj:
            return self.department_obj.code
        return None
    
    def set_department_by_name(self, department_name):
        """Set department bằng tên (helper method)"""
        if department_name:
            from app.models.department import Department
            dept = Department.query.filter_by(name=department_name).first()
            if dept:
                self.department_id = dept.id
                self.department = dept.name  # Sync cho backward compatibility
            else:
                # Fallback: giữ string nếu không tìm thấy
                self.department = department_name
                self.department_id = None
        else:
            self.department_id = None
            self.department = None
    
    def set_face_encoding(self, encoding):
        """Store face encoding as binary"""
        if encoding is not None:
            self.face_encoding = pickle.dumps(encoding)
    
    def get_face_encoding(self):
        """Retrieve face encoding from binary"""
        if self.face_encoding:
            return pickle.loads(self.face_encoding)
        return None
    
    def get_current_schedule(self):
        """Get current active work schedule"""
        return self.work_schedules.filter_by(is_active=True).first()
    
    def get_today_attendance(self):
        """Get today's attendance record"""
        from datetime import date
        today = date.today()
        return self.attendances.filter_by(date=today).first()
    
    def has_checked_in_today(self):
        """Check if employee has checked in today"""
        attendance = self.get_today_attendance()
        return attendance is not None and attendance.check_in_time is not None
    
    def has_checked_out_today(self):
        """Check if employee has checked out today"""
        attendance = self.get_today_attendance()
        return attendance is not None and attendance.check_out_time is not None
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'employee_code': self.employee_code,
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            # Department: ưu tiên department_obj
            'department_id': self.department_id,
            'department': self.get_department_name(),  # Tên phòng ban
            'department_code': self.get_department_code(),  # Mã phòng ban
            'position': self.position,
            'is_active': self.is_active,
            'hire_date': self.hire_date.isoformat() if self.hire_date else None,
            'has_face_encoding': self.face_encoding is not None,
            'has_face_embeddings': self.has_active_face_embeddings,
            'photo_path': self.photo_path,
            'created_at': self.created_at.isoformat()
        }

