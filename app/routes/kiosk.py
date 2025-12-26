"""Attendance kiosk routes"""
from flask import Blueprint, render_template, jsonify, request, current_app
from app import db
from app.models import Employee, Attendance
from datetime import datetime, date
import os
from app.utils.image_utils import ImageProcessor

bp = Blueprint('kiosk', __name__, url_prefix='/kiosk')


@bp.route('/')
def index():
    """Kiosk main page"""
    return render_template('kiosk/index.html')


@bp.route('/attendance')
def attendance_only():
    """Dedicated page for attendance via face recognition only"""
    return render_template('kiosk/attendance.html')


@bp.route('/check-in', methods=['POST'])
def check_in():
    """Handle check-in using employee_code or employee_id"""
    payload = request.get_json(silent=True) or {}
    employee_code = payload.get('employee_code')
    photo_data = payload.get('photo_path')  # Can be base64 or file path

    if not employee_code:
        return jsonify({'status': 'error', 'message': 'employee_code is required'}), 400

    employee = Employee.query.filter_by(employee_code=employee_code, is_active=True).first()

    if not employee:
        return jsonify({'status': 'error', 'message': 'Employee not found'}), 404

    # Check if employee has an active work schedule
    schedule = employee.get_current_schedule()
    if not schedule:
        return jsonify({
            'status': 'error', 
            'message': 'Không thể chấm công. Nhân viên chưa có lịch làm việc đang hoạt động. Vui lòng liên hệ quản trị viên.'
        }), 403

    # Check if schedule is effective on today
    today = date.today()
    if not schedule.is_effective_on(today):
        return jsonify({
            'status': 'error',
            'message': f'Lịch làm việc không có hiệu lực vào ngày {today.strftime("%d/%m/%Y")}. Vui lòng liên hệ quản trị viên.'
        }), 403

    # Check if today is a work day (weekday check: 0=Monday, 6=Sunday)
    weekday = today.weekday()  # 0=Monday, 6=Sunday
    if not schedule.is_weekday_allowed(weekday):
        weekday_names = ['Thứ Hai', 'Thứ Ba', 'Thứ Tư', 'Thứ Năm', 'Thứ Sáu', 'Thứ Bảy', 'Chủ Nhật']
        return jsonify({
            'status': 'error',
            'message': f'Hôm nay là {weekday_names[weekday]}, không phải ngày làm việc theo lịch của bạn. Vui lòng liên hệ quản trị viên.'
        }), 403

    attendance = Attendance.query.filter_by(employee_id=employee.id, date=today).first()
    if not attendance:
        attendance = Attendance(employee_id=employee.id, date=today)
        db.session.add(attendance)

    # If already checked in
    if attendance.check_in_time is not None:
        return jsonify({'status': 'error', 'message': 'Already checked in'}), 409

    attendance.employee = employee
    attendance.check_in()
    
    # Save photo if provided (base64 string)
    if photo_data and photo_data.startswith('data:image'):
        saved_path = _save_attendance_photo(photo_data, employee_code, today, 'check-in')
        if saved_path:
            attendance.check_in_photo = saved_path
    
    db.session.commit()

    return jsonify({'status': 'success', 'message': 'Check-in successful', 'attendance': attendance.to_dict()})


@bp.route('/check-out', methods=['POST'])
def check_out():
    """Handle check-out using employee_code or employee_id"""
    payload = request.get_json(silent=True) or {}
    employee_code = payload.get('employee_code')
    photo_data = payload.get('photo_path')  # Can be base64 or file path

    if not employee_code:
        return jsonify({'status': 'error', 'message': 'employee_code is required'}), 400

    employee = Employee.query.filter_by(employee_code=employee_code, is_active=True).first()

    if not employee:
        return jsonify({'status': 'error', 'message': 'Employee not found'}), 404

    # Check if employee has an active work schedule
    schedule = employee.get_current_schedule()
    if not schedule:
        return jsonify({
            'status': 'error', 
            'message': 'Không thể chấm công. Nhân viên chưa có lịch làm việc đang hoạt động. Vui lòng liên hệ quản trị viên.'
        }), 403

    today = date.today()
    attendance = Attendance.query.filter_by(employee_id=employee.id, date=today).first()

    if not attendance or attendance.check_in_time is None:
        return jsonify({'status': 'error', 'message': 'No check-in found for today'}), 409

    if attendance.check_out_time is not None:
        return jsonify({'status': 'error', 'message': 'Already checked out'}), 409

    attendance.employee = employee
    attendance.check_out()
    
    # Save photo if provided (base64 string)
    if photo_data and photo_data.startswith('data:image'):
        saved_path = _save_attendance_photo(photo_data, employee_code, today, 'check-out')
        if saved_path:
            attendance.check_out_photo = saved_path
    
    db.session.commit()

    return jsonify({'status': 'success', 'message': 'Check-out successful', 'attendance': attendance.to_dict()})


def _save_attendance_photo(photo_data: str, employee_code: str, date_obj: date, photo_type: str) -> str:
    """
    Save attendance photo from base64 to file
    
    Args:
        photo_data: Base64 encoded image string (data:image/...)
        employee_code: Employee code
        date_obj: Date object
        photo_type: 'check-in' or 'check-out'
        
    Returns:
        Relative file path or None if failed
    """
    try:
        # Decode base64 to image
        image = ImageProcessor.decode_from_base64(photo_data)
        if image is None:
            return None
        
        # Get upload directory from config
        upload_dir = current_app.config.get('UPLOAD_PATH', 'app/static/uploads')
        attendance_dir = os.path.join(upload_dir, 'attendance')
        os.makedirs(attendance_dir, exist_ok=True)
        
        # Generate filename: employee_code_date_type_timestamp.jpg
        timestamp = datetime.now().strftime('%H%M%S')
        filename = f"{employee_code}_{date_obj.strftime('%Y%m%d')}_{photo_type}_{timestamp}.jpg"
        file_path = os.path.join(attendance_dir, filename)
        
        # Save image
        if ImageProcessor.save_image(image, file_path, quality=85):
            # Return relative path from static folder
            # Path will be: /static/uploads/attendance/filename.jpg
            relative_path = f"/static/uploads/attendance/{filename}"
            return relative_path
        else:
            return None
            
    except Exception as e:
        current_app.logger.error(f"Error saving attendance photo: {str(e)}")
        return None

