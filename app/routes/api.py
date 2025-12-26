"""API routes"""
from flask import Blueprint, jsonify, request
from flask_login import login_required
from app.models import Employee, Attendance
from datetime import date

bp = Blueprint('api', __name__, url_prefix='/api')


@bp.route('/employees', methods=['GET'])
@login_required
def get_employees():
    """Get all employees"""
    # Filter by department_id nếu có
    department_id = request.args.get('department_id', type=int)
    
    query = Employee.query.filter_by(is_active=True)
    if department_id:
        query = query.filter_by(department_id=department_id)
    
    employees = query.all()
    return jsonify([emp.to_dict() for emp in employees])


@bp.route('/attendance/today', methods=['GET'])
@login_required
def get_today_attendance():
    """Get today's attendance records"""
    today = date.today()
    records = Attendance.query.filter_by(date=today).all()
    return jsonify([record.to_dict() for record in records])


@bp.route('/stats', methods=['GET'])
@login_required
def get_stats():
    """Get system statistics"""
    total_employees = Employee.query.filter_by(is_active=True).count()
    today = date.today()
    today_attendance = Attendance.query.filter_by(date=today).count()
    
    return jsonify({
        'total_employees': total_employees,
        'today_attendance': today_attendance,
        'attendance_rate': round((today_attendance / total_employees * 100) if total_employees > 0 else 0, 2)
    })

