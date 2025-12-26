
import os
from flask import redirect, url_for
from app import create_app, db
from app.models import User, Employee, Attendance, SystemLog

# Get configuration from environment
config_name = os.getenv('FLASK_ENV', 'development')
app = create_app(config_name)


@app.route('/')
def index():
    """Redirect to kiosk page"""
    return redirect(url_for('auth.login'))

@app.shell_context_processor
def make_shell_context():
    """Make database models available in Flask shell"""
    return {
        'db': db,
        'User': User,
        'Employee': Employee,
        'Attendance': Attendance,
        'SystemLog': SystemLog
    }


@app.cli.command()
def init_db():
    """Initialize the database"""
    db.create_all()
    print('✅ Database tables created successfully!')


@app.cli.command()
def drop_db():
    """Drop all database tables"""
    if input('Are you sure you want to drop all tables? (yes/no): ').lower() == 'yes':
        db.drop_all()
        print('✅ All tables dropped!')
    else:
        print('❌ Operation cancelled')


@app.cli.command()
def seed_db():
    """Seed database with initial data"""
    from werkzeug.security import generate_password_hash
    from datetime import date, time
    
    print('🌱 Seeding database...')
    
    # Create admin user
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin = User(
            username='admin',
            email='admin@attendance.com',
            role='admin',
            is_active=True
        )
        admin.set_password('admin123')
        db.session.add(admin)
        print('✅ Created admin user (username: admin, password: admin123)')
    
    # Create sample employees
    sample_employees = [
        {
            'employee_code': 'EMP001',
            'name': 'Nguyễn Văn A',
            'email': 'nguyenvana@company.com',
            'phone': '0901234567',
            'department': 'Sản xuất',
            'position': 'Công nhân',
            'hire_date': date(2024, 1, 15)
        },
        {
            'employee_code': 'EMP002',
            'name': 'Trần Thị B',
            'email': 'tranthib@company.com',
            'phone': '0902345678',
            'department': 'Sản xuất',
            'position': 'Công nhân',
            'hire_date': date(2024, 2, 1)
        },
        {
            'employee_code': 'EMP003',
            'name': 'Lê Văn C',
            'email': 'levanc@company.com',
            'phone': '0903456789',
            'department': 'Kỹ thuật',
            'position': 'Kỹ thuật viên',
            'hire_date': date(2024, 1, 20)
        }
    ]
    
    db.session.commit()
    print('🎉 Database seeded successfully!')


if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=5555,
        debug=True
    )

