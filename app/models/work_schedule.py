"""WorkSchedule model"""
from app import db
from datetime import datetime, time, date


class WorkSchedule(db.Model):
    """Employee work schedule (shift) definition"""

    __tablename__ = 'work_schedules'

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False, index=True)

    # Shift window
    shift_start = db.Column(db.Time, nullable=False)
    shift_end = db.Column(db.Time, nullable=False)

    # Active flags and validity window
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    effective_from = db.Column(db.Date, nullable=True)
    effective_to = db.Column(db.Date, nullable=True)

    # Optional: weekdays mask (0-6 for Mon-Sun), stored as CSV string like "0,1,2,3,4"
    work_days = db.Column(db.String(32), nullable=True)

    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        db.Index('idx_work_schedule_employee_active', 'employee_id', 'is_active'),
    )

    def __repr__(self):
        return f'<WorkSchedule emp={self.employee_id} {self.shift_start}-{self.shift_end}>'

    def is_effective_on(self, on_date: date) -> bool:
        """Check if schedule is effective on a specific date."""
        if self.effective_from and on_date < self.effective_from:
            return False
        if self.effective_to and on_date > self.effective_to:
            return False
        return True

    def is_weekday_allowed(self, weekday: int) -> bool:
        """Check if the given weekday (0=Mon) is allowed by this schedule."""
        if not self.work_days:
            return True
        try:
            allowed = {int(x) for x in self.work_days.split(',') if x != ''}
            return weekday in allowed
        except Exception:
            return True

    def to_dict(self):
        """Serialize to dict for APIs."""
        return {
            'id': self.id,
            'employee_id': self.employee_id,
            'shift_start': self.shift_start.isoformat() if self.shift_start else None,
            'shift_end': self.shift_end.isoformat() if self.shift_end else None,
            'is_active': self.is_active,
            'effective_from': self.effective_from.isoformat() if self.effective_from else None,
            'effective_to': self.effective_to.isoformat() if self.effective_to else None,
            'work_days': self.work_days,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


