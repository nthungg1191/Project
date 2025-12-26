"""Attendance model"""
from app import db
from datetime import datetime, timedelta


class Attendance(db.Model):
    """Attendance model for check-in/check-out records"""
    
    __tablename__ = 'attendance'
    
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False, index=True)
    date = db.Column(db.Date, nullable=False, index=True)
    check_in_time = db.Column(db.DateTime, nullable=True)
    check_out_time = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), default='present', nullable=False)  # present, absent, late, early_leave
    working_hours = db.Column(db.Float, default=0.0)  # Hours worked
    overtime_hours = db.Column(db.Float, default=0.0)  # Overtime hours
    notes = db.Column(db.Text, nullable=True)
    check_in_photo = db.Column(db.String(255), nullable=True)
    check_out_photo = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Composite index for faster queries
    __table_args__ = (
        db.Index('idx_employee_date', 'employee_id', 'date'),
    )
    
    def __repr__(self):
        return f'<Attendance {self.employee_id} on {self.date}>'
    
    def check_in(self, timestamp=None):
        """Record check-in time"""
        if timestamp is None:
            timestamp = datetime.now()
        self.check_in_time = timestamp
        self.date = timestamp.date()
        self.update_status()
    
    def check_out(self, timestamp=None):
        """Record check-out time"""
        if timestamp is None:
            timestamp = datetime.now()
        self.check_out_time = timestamp
        self.calculate_working_hours()
        self.update_status()
    
    def calculate_working_hours(self):
        """Calculate total working hours"""
        if self.check_in_time and self.check_out_time:
            delta = self.check_out_time - self.check_in_time
            self.working_hours = round(delta.total_seconds() / 3600, 2)
            
            # Calculate overtime (assuming 8-hour workday)
            if self.working_hours > 8:
                self.overtime_hours = round(self.working_hours - 8, 2)
    
    def update_status(self):
        """Update attendance status based on check-in/out times"""
        if not self.check_in_time:
            self.status = 'absent'
            return
        
        # Get employee's work schedule
        schedule = self.employee.get_current_schedule()
        if not schedule:
            self.status = 'present'
            return
        
        # Check if late
        scheduled_start = datetime.combine(self.date, schedule.shift_start)
        late_threshold = scheduled_start + timedelta(minutes=15)  # 15 minutes grace period
        
        if self.check_in_time > late_threshold:
            self.status = 'late'
        elif self.check_out_time:
            # Check if early leave
            scheduled_end = datetime.combine(self.date, schedule.shift_end)
            early_threshold = scheduled_end - timedelta(minutes=15)
            
            if self.check_out_time < early_threshold:
                self.status = 'early_leave'
            else:
                self.status = 'present'
        else:
            self.status = 'present'
    
    def is_complete(self):
        """Check if both check-in and check-out are recorded"""
        return self.check_in_time is not None and self.check_out_time is not None
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'employee_id': self.employee_id,
            'employee_name': self.employee.name if self.employee else None,
            'employee_code': self.employee.employee_code if self.employee else None,
            'date': self.date.isoformat(),
            'check_in_time': self.check_in_time.isoformat() if self.check_in_time else None,
            'check_out_time': self.check_out_time.isoformat() if self.check_out_time else None,
            'status': self.status,
            'working_hours': self.working_hours,
            'overtime_hours': self.overtime_hours,
            'notes': self.notes,
            'is_complete': self.is_complete()
        }

