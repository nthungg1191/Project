"""Department model"""
from app import db
from datetime import datetime


class Department(db.Model):
    """Department model for organizational units"""
    
    __tablename__ = 'departments'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    code = db.Column(db.String(20), unique=True, nullable=True, index=True)
    description = db.Column(db.Text, nullable=True)
    
    # Manager reference (self-referential)
    manager_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=True)
    
    # Location and contact info
    location = db.Column(db.String(255), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    
    # Hierarchy (parent department)
    parent_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=True)
    
    # Display and status
    display_order = db.Column(db.Integer, default=0, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False, index=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.now, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    notes = db.Column(db.Text, nullable=True)
    
    # Relationships
    employees = db.relationship(
        'Employee',
        foreign_keys='Employee.department_id',
        backref='department_obj',
        lazy='dynamic',
        cascade='all, delete-orphan'
    )
    
    parent = db.relationship(
        'Department',
        remote_side=[id],
        backref='sub_departments',
        foreign_keys=[parent_id]
    )
    
    manager = db.relationship(
        'Employee',
        foreign_keys=[manager_id],
        backref='managed_departments',
        lazy='select'
    )
    
    def __repr__(self):
        return f'<Department {self.code or self.name}: {self.name}>'
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'code': self.code,
            'description': self.description,
            'manager_id': self.manager_id,
            'location': self.location,
            'phone': self.phone,
            'email': self.email,
            'parent_id': self.parent_id,
            'display_order': self.display_order,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

