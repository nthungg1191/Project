
import os
import sys
from app import create_app, db
from app.models import User, Employee, Attendance, WorkSchedule, SystemLog

def init_database():
    """Initialize database with tables"""
    print('🔧 Initializing database...')
    
    # Create Flask app
    app = create_app('development')
    
    with app.app_context():
        # Create all tables
        db.create_all()
        print('✅ Database tables created successfully!')
        
        # List all tables
        print('\n📋 Created tables:')
        for table in db.metadata.sorted_tables:
            print(f'  - {table.name}')
        
        print('\n✨ Database initialization complete!')
        print('\n📝 Next steps:')
        print('  1. Run: python run.py seed_db  (to add sample data)')
        print('  2. Run: python run.py  (to start the application)')


if __name__ == '__main__':
    init_database()

