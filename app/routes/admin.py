"""Admin dashboard routes"""
from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from sqlalchemy.orm import subqueryload
from app import db
from app.models import Employee, Attendance, Department, WorkSchedule
from datetime import date, datetime, time

bp = Blueprint('admin', __name__, url_prefix='/admin')


@bp.route('/')
@bp.route('/dashboard')
@login_required
def dashboard():
    """Admin dashboard"""
    from app.services.reports_service import ReportsService
    from app.services.notification_service import NotificationService
    
    # Get statistics
    total_employees = Employee.query.filter_by(is_active=True).count()
    today = date.today()
    
    # Get today's report
    today_report = ReportsService.get_daily_report(today)
    
    # Get weekly report
    weekly_report = ReportsService.get_weekly_report()
    
    # Get late employees
    late_employees = ReportsService.get_late_employees(today, limit=5)
    
    # Get absent employees
    absent_employees = ReportsService.get_absent_employees(today)
    
    # Get dashboard alerts
    alerts = NotificationService.get_dashboard_alerts()
    
    return render_template('admin/dashboard.html',
                         total_employees=total_employees,
                         today_report=today_report,
                         weekly_report=weekly_report,
                         late_employees=late_employees,
                         absent_employees=absent_employees,
                         alerts=alerts)


@bp.route('/employees')
@login_required
def employees():
    """Employee management page"""
    employees = Employee.query.options(
        subqueryload(Employee.face_embeddings)
    ).order_by(Employee.created_at.desc()).all()
    departments = Department.query.filter_by(is_active=True).order_by(Department.name).all()
    return render_template('admin/employees.html', 
                         employees=employees,
                         departments=departments)


# Employee CRUD
@bp.route('/employees/new', methods=['GET', 'POST'])
@login_required
def employee_new():
    if request.method == 'POST':
        employee_code = request.form.get('employee_code', '').strip()
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip() or None
        phone = request.form.get('phone', '').strip() or None
        
        # NEW: Dùng department_id thay vì department string
        department_id = request.form.get('department_id')
        if department_id:
            try:
                department_id = int(department_id)
            except (ValueError, TypeError):
                department_id = None
        else:
            department_id = None
        
        position = request.form.get('position', '').strip() or None
        hire_date_str = request.form.get('hire_date', '').strip()
        hire_date = datetime.strptime(hire_date_str, '%Y-%m-%d').date() if hire_date_str else None
        notes = request.form.get('notes', '').strip() or None
        is_active = request.form.get('is_active') == 'on'

        emp = Employee(
            employee_code=employee_code,
            name=name,
            email=email,
            phone=phone,
            department_id=department_id,  # NEW: Dùng FK
            position=position,
            hire_date=hire_date,
            notes=notes,
            is_active=is_active
        )
        
        # Sync department string cho backward compatibility
        if department_id:
            dept = Department.query.get(department_id)
            if dept:
                emp.department = dept.name
        
        db.session.add(emp)
        db.session.commit()
        flash('Employee created successfully', 'success')
        return redirect(url_for('admin.employees'))
    
    # GET: Show form
    departments = Department.query.filter_by(is_active=True).order_by(Department.name).all()
    return render_template('admin/employee_form.html', 
                         employee=None,
                         departments=departments)


@bp.route('/employees/<int:employee_id>/edit', methods=['GET', 'POST'])
@login_required
def employee_edit(employee_id: int):
    emp = Employee.query.get_or_404(employee_id)
    if request.method == 'POST':
        emp.employee_code = request.form.get('employee_code', emp.employee_code).strip()
        emp.name = request.form.get('name', emp.name).strip()
        emp.email = request.form.get('email') or None
        emp.phone = request.form.get('phone') or None
        
        # NEW: Dùng department_id thay vì department string
        department_id = request.form.get('department_id')
        if department_id:
            try:
                emp.department_id = int(department_id)
                # Sync department string
                dept = Department.query.get(emp.department_id)
                if dept:
                    emp.department = dept.name
            except (ValueError, TypeError):
                emp.department_id = None
                emp.department = None
        else:
            emp.department_id = None
            emp.department = None
        
        emp.position = request.form.get('position') or None
        hire_date_str = request.form.get('hire_date', '')
        emp.hire_date = datetime.strptime(hire_date_str, '%Y-%m-%d').date() if hire_date_str else None
        emp.notes = request.form.get('notes') or None
        emp.is_active = request.form.get('is_active') == 'on'
        db.session.commit()
        flash('Employee updated successfully', 'success')
        return redirect(url_for('admin.employees'))
    
    # GET: Show form
    departments = Department.query.filter_by(is_active=True).order_by(Department.name).all()
    return render_template('admin/employee_form.html', 
                         employee=emp,
                         departments=departments)


@bp.route('/employees/<int:employee_id>/delete', methods=['POST'])
@login_required
def employee_delete(employee_id: int):
    emp = Employee.query.get_or_404(employee_id)
    db.session.delete(emp)
    db.session.commit()
    return redirect(url_for('admin.employees'))


# ========== WORK SCHEDULE MANAGEMENT ==========

@bp.route('/schedules')
@login_required
def schedules():
    """Work schedule management page"""
    # Get filter parameters
    employee_id_filter = request.args.get('employee_id', type=int)
    is_active_filter = request.args.get('is_active')
    
    # Build query
    query = WorkSchedule.query
    
    if employee_id_filter:
        query = query.filter_by(employee_id=employee_id_filter)
    
    if is_active_filter is not None:
        is_active = is_active_filter.lower() == 'true'
        query = query.filter_by(is_active=is_active)
    
    # Order by employee name, then effective_from
    schedules = query.join(Employee).order_by(
        Employee.name,
        WorkSchedule.effective_from.desc().nullslast(),
        WorkSchedule.created_at.desc()
    ).all()
    
    # Get all employees for filter dropdown
    employees = Employee.query.filter_by(is_active=True).order_by(Employee.name).all()
    
    # Statistics
    total_schedules = WorkSchedule.query.count()
    active_schedules = WorkSchedule.query.filter_by(is_active=True).count()
    inactive_schedules = total_schedules - active_schedules
    
    return render_template('admin/schedules.html',
                         schedules=schedules,
                         employees=employees,
                         total_schedules=total_schedules,
                         active_schedules=active_schedules,
                         inactive_schedules=inactive_schedules)


@bp.route('/schedules/new', methods=['GET', 'POST'])
@login_required
def schedule_new():
    """Create new work schedule"""
    if request.method == 'POST':
        employee_id = request.form.get('employee_id')
        if not employee_id:
            flash('Vui lòng chọn nhân viên', 'danger')
            employees = Employee.query.filter_by(is_active=True).order_by(Employee.name).all()
            return render_template('admin/schedule_form.html', 
                                 schedule=None,
                                 employees=employees)
        
        try:
            employee_id = int(employee_id)
        except (ValueError, TypeError):
            flash('Mã nhân viên không hợp lệ', 'danger')
            employees = Employee.query.filter_by(is_active=True).order_by(Employee.name).all()
            return render_template('admin/schedule_form.html', 
                                 schedule=None,
                                 employees=employees)
        
        # Get shift times
        shift_start_str = request.form.get('shift_start', '').strip()
        shift_end_str = request.form.get('shift_end', '').strip()
        
        if not shift_start_str or not shift_end_str:
            flash('Vui lòng nhập giờ bắt đầu và giờ kết thúc ca làm việc', 'danger')
            employees = Employee.query.filter_by(is_active=True).order_by(Employee.name).all()
            return render_template('admin/schedule_form.html', 
                                 schedule=None,
                                 employees=employees)
        
        try:
            shift_start = datetime.strptime(shift_start_str, '%H:%M').time()
            shift_end = datetime.strptime(shift_end_str, '%H:%M').time()
        except ValueError:
            flash('Định dạng giờ không hợp lệ. Vui lòng sử dụng định dạng HH:MM', 'danger')
            employees = Employee.query.filter_by(is_active=True).order_by(Employee.name).all()
            return render_template('admin/schedule_form.html', 
                                 schedule=None,
                                 employees=employees)
        
        # Get effective dates
        effective_from_str = request.form.get('effective_from', '').strip()
        effective_from = None
        if effective_from_str:
            try:
                effective_from = datetime.strptime(effective_from_str, '%Y-%m-%d').date()
            except ValueError:
                pass
        
        effective_to_str = request.form.get('effective_to', '').strip()
        effective_to = None
        if effective_to_str:
            try:
                effective_to = datetime.strptime(effective_to_str, '%Y-%m-%d').date()
            except ValueError:
                pass
        
        # Validate date range
        if effective_from and effective_to and effective_from > effective_to:
            flash('Ngày bắt đầu không thể sau ngày kết thúc', 'danger')
            employees = Employee.query.filter_by(is_active=True).order_by(Employee.name).all()
            return render_template('admin/schedule_form.html', 
                                 schedule=None,
                                 employees=employees)
        
        # Get work days (weekdays)
        work_days_list = request.form.getlist('work_days')
        work_days = ','.join(sorted(work_days_list)) if work_days_list else None
        
        # Get is_active
        is_active = request.form.get('is_active') == 'on'
        
        # Get notes
        notes = request.form.get('notes', '').strip() or None
        
        # If this is set as active, deactivate other active schedules for this employee
        # (Simple approach: deactivate all other active schedules for this employee)
        if is_active:
            existing_active = WorkSchedule.query.filter_by(
                employee_id=employee_id,
                is_active=True
            ).all()
            
            for existing in existing_active:
                existing.is_active = False
        
        # Create work schedule
        schedule = WorkSchedule(
            employee_id=employee_id,
            shift_start=shift_start,
            shift_end=shift_end,
            effective_from=effective_from,
            effective_to=effective_to,
            work_days=work_days,
            is_active=is_active,
            notes=notes
        )
        
        db.session.add(schedule)
        db.session.commit()
        
        flash('Tạo lịch làm việc thành công', 'success')
        return redirect(url_for('admin.schedules'))
    
    # GET request
    employees = Employee.query.filter_by(is_active=True).order_by(Employee.name).all()
    return render_template('admin/schedule_form.html', 
                         schedule=None,
                         employees=employees)


@bp.route('/schedules/<int:schedule_id>/edit', methods=['GET', 'POST'])
@login_required
def schedule_edit(schedule_id: int):
    """Edit work schedule"""
    schedule = WorkSchedule.query.get_or_404(schedule_id)
    
    if request.method == 'POST':
        employee_id = request.form.get('employee_id')
        if not employee_id:
            flash('Vui lòng chọn nhân viên', 'danger')
            employees = Employee.query.filter_by(is_active=True).order_by(Employee.name).all()
            return render_template('admin/schedule_form.html', 
                                 schedule=schedule,
                                 employees=employees)
        
        try:
            employee_id = int(employee_id)
        except (ValueError, TypeError):
            flash('Mã nhân viên không hợp lệ', 'danger')
            employees = Employee.query.filter_by(is_active=True).order_by(Employee.name).all()
            return render_template('admin/schedule_form.html', 
                                 schedule=schedule,
                                 employees=employees)
        
        # Get shift times
        shift_start_str = request.form.get('shift_start', '').strip()
        shift_end_str = request.form.get('shift_end', '').strip()
        
        if not shift_start_str or not shift_end_str:
            flash('Vui lòng nhập giờ bắt đầu và giờ kết thúc ca làm việc', 'danger')
            employees = Employee.query.filter_by(is_active=True).order_by(Employee.name).all()
            return render_template('admin/schedule_form.html', 
                                 schedule=schedule,
                                 employees=employees)
        
        try:
            shift_start = datetime.strptime(shift_start_str, '%H:%M').time()
            shift_end = datetime.strptime(shift_end_str, '%H:%M').time()
        except ValueError:
            flash('Định dạng giờ không hợp lệ. Vui lòng sử dụng định dạng HH:MM', 'danger')
            employees = Employee.query.filter_by(is_active=True).order_by(Employee.name).all()
            return render_template('admin/schedule_form.html', 
                                 schedule=schedule,
                                 employees=employees)
        
        # Get effective dates
        effective_from_str = request.form.get('effective_from', '').strip()
        effective_from = None
        if effective_from_str:
            try:
                effective_from = datetime.strptime(effective_from_str, '%Y-%m-%d').date()
            except ValueError:
                pass
        
        effective_to_str = request.form.get('effective_to', '').strip()
        effective_to = None
        if effective_to_str:
            try:
                effective_to = datetime.strptime(effective_to_str, '%Y-%m-%d').date()
            except ValueError:
                pass
        
        # Validate date range
        if effective_from and effective_to and effective_from > effective_to:
            flash('Ngày bắt đầu không thể sau ngày kết thúc', 'danger')
            employees = Employee.query.filter_by(is_active=True).order_by(Employee.name).all()
            return render_template('admin/schedule_form.html', 
                                 schedule=schedule,
                                 employees=employees)
        
        # Get work days
        work_days_list = request.form.getlist('work_days')
        work_days = ','.join(sorted(work_days_list)) if work_days_list else None
        
        # Get is_active
        is_active = request.form.get('is_active') == 'on'
        
        # Get notes
        notes = request.form.get('notes', '').strip() or None
        
        # If this is set as active, deactivate other active schedules for this employee
        # (Simple approach: deactivate all other active schedules for this employee, excluding current)
        if is_active:
            existing_active = WorkSchedule.query.filter(
                WorkSchedule.employee_id == employee_id,
                WorkSchedule.is_active == True,
                WorkSchedule.id != schedule_id
            ).all()
            
            for existing in existing_active:
                existing.is_active = False
        
        # Update schedule
        schedule.employee_id = employee_id
        schedule.shift_start = shift_start
        schedule.shift_end = shift_end
        schedule.effective_from = effective_from
        schedule.effective_to = effective_to
        schedule.work_days = work_days
        schedule.is_active = is_active
        schedule.notes = notes
        
        db.session.commit()
        
        flash('Cập nhật lịch làm việc thành công', 'success')
        return redirect(url_for('admin.schedules'))
    
    # GET request
    employees = Employee.query.filter_by(is_active=True).order_by(Employee.name).all()
    return render_template('admin/schedule_form.html', 
                         schedule=schedule,
                         employees=employees)


@bp.route('/schedules/<int:schedule_id>/delete', methods=['POST'])
@login_required
def schedule_delete(schedule_id: int):
    """Delete work schedule"""
    schedule = WorkSchedule.query.get_or_404(schedule_id)
    employee_name = schedule.employee.name
    
    db.session.delete(schedule)
    db.session.commit()
    
    flash(f'Đã xóa lịch làm việc của {employee_name}', 'success')
    return redirect(url_for('admin.schedules'))


@bp.route('/attendance')
@login_required
def attendance():
    """Attendance records page"""
    today = date.today()
    
    # Get filter parameters
    filter_date = request.args.get('date')
    if filter_date:
        try:
            filter_date = datetime.strptime(filter_date, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            filter_date = today
    else:
        filter_date = today
    
    status_filter = request.args.get('status')
    employee_id_filter = request.args.get('employee_id', type=int)
    
    # Build query
    query = Attendance.query.filter_by(date=filter_date)
    
    if status_filter:
        query = query.filter_by(status=status_filter)
    
    if employee_id_filter:
        query = query.filter_by(employee_id=employee_id_filter)
    
    # Order by check-in time (most recent first)
    records = query.order_by(Attendance.check_in_time.desc().nulls_last()).all()
    
    # Get all employees for filter dropdown
    employees = Employee.query.filter_by(is_active=True).order_by(Employee.name).all()
    
    return render_template('admin/attendance.html', 
                         records=records,
                         employees=employees,
                         today=filter_date)


@bp.route('/attendance/new', methods=['GET', 'POST'])
@login_required
def attendance_new():
    """Create new attendance record"""
    if request.method == 'POST':
        employee_id = request.form.get('employee_id')
        if not employee_id:
            flash('Vui lòng chọn nhân viên', 'danger')
            employees = Employee.query.filter_by(is_active=True).order_by(Employee.name).all()
            return render_template('admin/attendance_form.html', 
                                 employees=employees,
                                 today=date.today())
        
        try:
            employee_id = int(employee_id)
        except (ValueError, TypeError):
            flash('Mã nhân viên không hợp lệ', 'danger')
            employees = Employee.query.filter_by(is_active=True).order_by(Employee.name).all()
            return render_template('admin/attendance_form.html', 
                                 employees=employees,
                                 today=date.today())
        
        # Get date
        date_str = request.form.get('date', '').strip()
        if not date_str:
            flash('Vui lòng chọn ngày', 'danger')
            employees = Employee.query.filter_by(is_active=True).order_by(Employee.name).all()
            return render_template('admin/attendance_form.html', 
                                 employees=employees,
                                 today=date.today())
        
        try:
            record_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Ngày không hợp lệ', 'danger')
            employees = Employee.query.filter_by(is_active=True).order_by(Employee.name).all()
            return render_template('admin/attendance_form.html', 
                                 employees=employees,
                                 today=date.today())
        
        # Check if attendance record already exists
        existing = Attendance.query.filter_by(
            employee_id=employee_id,
            date=record_date
        ).first()
        
        if existing:
            flash('Bản ghi chấm công cho nhân viên này trong ngày này đã tồn tại. Vui lòng sửa bản ghi hiện có.', 'warning')
            return redirect(url_for('admin.attendance_edit', attendance_id=existing.id))
        
        # Get check-in time
        check_in_str = request.form.get('check_in_time', '').strip()
        check_in_time = None
        if check_in_str:
            try:
                check_in_time = datetime.strptime(check_in_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                pass
        
        # Get check-out time
        check_out_str = request.form.get('check_out_time', '').strip()
        check_out_time = None
        if check_out_str:
            try:
                check_out_time = datetime.strptime(check_out_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                pass
        
        # Get status
        status = request.form.get('status', 'present').strip()
        
        # Get working hours
        working_hours = request.form.get('working_hours', '').strip()
        try:
            working_hours = float(working_hours) if working_hours else None
        except ValueError:
            working_hours = None
        
        # Get overtime hours
        overtime_hours = request.form.get('overtime_hours', '').strip()
        try:
            overtime_hours = float(overtime_hours) if overtime_hours else None
        except ValueError:
            overtime_hours = None
        
        # Get notes
        notes = request.form.get('notes', '').strip() or None
        
        # Create attendance record
        attendance = Attendance(
            employee_id=employee_id,
            date=record_date,
            check_in_time=check_in_time,
            check_out_time=check_out_time,
            status=status,
            working_hours=working_hours or 0.0,
            overtime_hours=overtime_hours or 0.0,
            notes=notes
        )
        
        # Auto-calculate if times are provided
        if check_in_time and check_out_time:
            attendance.calculate_working_hours()
            attendance.update_status()
        
        db.session.add(attendance)
        db.session.commit()
        
        flash('Tạo bản ghi chấm công thành công', 'success')
        return redirect(url_for('admin.attendance'))
    
    # GET request
    employees = Employee.query.filter_by(is_active=True).order_by(Employee.name).all()
    return render_template('admin/attendance_form.html', 
                         employees=employees,
                         today=date.today())


@bp.route('/attendance/<int:attendance_id>/edit', methods=['GET', 'POST'])
@login_required
def attendance_edit(attendance_id: int):
    """Edit attendance record"""
    attendance = Attendance.query.get_or_404(attendance_id)
    
    if request.method == 'POST':
        # Get employee_id
        employee_id = request.form.get('employee_id')
        if not employee_id:
            flash('Vui lòng chọn nhân viên', 'danger')
            employees = Employee.query.filter_by(is_active=True).order_by(Employee.name).all()
            return render_template('admin/attendance_form.html', 
                                 attendance=attendance,
                                 employees=employees,
                                 today=date.today())
        
        try:
            employee_id = int(employee_id)
        except (ValueError, TypeError):
            flash('Mã nhân viên không hợp lệ', 'danger')
            employees = Employee.query.filter_by(is_active=True).order_by(Employee.name).all()
            return render_template('admin/attendance_form.html', 
                                 attendance=attendance,
                                 employees=employees,
                                 today=date.today())
        
        # Get date
        date_str = request.form.get('date', '').strip()
        if not date_str:
            flash('Vui lòng chọn ngày', 'danger')
            employees = Employee.query.filter_by(is_active=True).order_by(Employee.name).all()
            return render_template('admin/attendance_form.html', 
                                 attendance=attendance,
                                 employees=employees,
                                 today=date.today())
        
        try:
            record_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Ngày không hợp lệ', 'danger')
            employees = Employee.query.filter_by(is_active=True).order_by(Employee.name).all()
            return render_template('admin/attendance_form.html', 
                                 attendance=attendance,
                                 employees=employees,
                                 today=date.today())
        
        # Check if another record exists with same employee and date
        existing = Attendance.query.filter(
            Attendance.employee_id == employee_id,
            Attendance.date == record_date,
            Attendance.id != attendance_id
        ).first()
        
        if existing:
            flash('Bản ghi chấm công cho nhân viên này trong ngày này đã tồn tại', 'warning')
            employees = Employee.query.filter_by(is_active=True).order_by(Employee.name).all()
            return render_template('admin/attendance_form.html', 
                                 attendance=attendance,
                                 employees=employees,
                                 today=date.today())
        
        # Get check-in time
        check_in_str = request.form.get('check_in_time', '').strip()
        check_in_time = None
        if check_in_str:
            try:
                check_in_time = datetime.strptime(check_in_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                pass
        
        # Get check-out time
        check_out_str = request.form.get('check_out_time', '').strip()
        check_out_time = None
        if check_out_str:
            try:
                check_out_time = datetime.strptime(check_out_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                pass
        
        # Get status
        status = request.form.get('status', 'present').strip()
        
        # Get working hours
        working_hours = request.form.get('working_hours', '').strip()
        try:
            working_hours = float(working_hours) if working_hours else None
        except ValueError:
            working_hours = None
        
        # Get overtime hours
        overtime_hours = request.form.get('overtime_hours', '').strip()
        try:
            overtime_hours = float(overtime_hours) if overtime_hours else None
        except ValueError:
            overtime_hours = None
        
        # Get notes
        notes = request.form.get('notes', '').strip() or None
        
        # Update attendance record
        attendance.employee_id = employee_id
        attendance.date = record_date
        attendance.check_in_time = check_in_time
        attendance.check_out_time = check_out_time
        attendance.status = status
        attendance.notes = notes
        
        # Auto-calculate if times are provided
        if check_in_time and check_out_time:
            attendance.calculate_working_hours()
            attendance.update_status()
        else:
            attendance.working_hours = working_hours or 0.0
            attendance.overtime_hours = overtime_hours or 0.0
        
        db.session.commit()
        
        flash('Cập nhật bản ghi chấm công thành công', 'success')
        return redirect(url_for('admin.attendance'))
    
    # GET request
    employees = Employee.query.filter_by(is_active=True).order_by(Employee.name).all()
    return render_template('admin/attendance_form.html', 
                         attendance=attendance,
                         employees=employees,
                         today=date.today())


@bp.route('/attendance/<int:attendance_id>/delete', methods=['POST'])
@login_required
def attendance_delete(attendance_id: int):
    """Delete attendance record"""
    attendance = Attendance.query.get_or_404(attendance_id)
    db.session.delete(attendance)
    db.session.commit()
    flash('Xóa bản ghi chấm công thành công', 'success')
    return redirect(url_for('admin.attendance'))


@bp.route('/reports')
@login_required
def reports():
    """Reports page"""
    report_type = request.args.get('type', 'daily')
    report_date = request.args.get('date')
    year = request.args.get('year', type=int)
    month = request.args.get('month', type=int)
    
    from app.services.reports_service import ReportsService
    
    report_data = None
    if report_type == 'daily':
        if report_date:
            report_date = datetime.strptime(report_date, '%Y-%m-%d').date()
        else:
            report_date = date.today()
        report_data = ReportsService.get_daily_report(report_date)
    elif report_type == 'weekly':
        if report_date:
            start_date = datetime.strptime(report_date, '%Y-%m-%d').date()
        else:
            start_date = None
        report_data = ReportsService.get_weekly_report(start_date)
    elif report_type == 'monthly':
        report_data = ReportsService.get_monthly_report(year, month)
    
    return render_template('admin/reports.html',
                         report_type=report_type,
                         report_data=report_data)


@bp.route('/reports/export')
@login_required
def export_report():
    """Export report to Excel"""
    from flask import send_file
    from app.services.reports_service import ReportsService
    from app.services.export_service import ExportService
    import io
    
    report_type = request.args.get('type', 'daily')
    report_date = request.args.get('date')
    year = request.args.get('year', type=int)
    month = request.args.get('month', type=int)
    
    # Get report data
    report_data = None
    if report_type == 'daily':
        if report_date:
            report_date = datetime.strptime(report_date, '%Y-%m-%d').date()
        else:
            report_date = date.today()
        report_data = ReportsService.get_daily_report(report_date)
    elif report_type == 'weekly':
        if report_date:
            start_date = datetime.strptime(report_date, '%Y-%m-%d').date()
        else:
            start_date = None
        report_data = ReportsService.get_weekly_report(start_date)
    elif report_type == 'monthly':
        report_data = ReportsService.get_monthly_report(year, month)
    
    # Export to Excel
    excel_file = ExportService.export_to_excel(report_data, report_type)
    
    # Generate filename
    if report_type == 'daily':
        filename = f'bao_cao_ngay_{report_data["date"]}.xlsx'
    elif report_type == 'weekly':
        filename = f'bao_cao_tuan_{report_data["start_date"]}_to_{report_data["end_date"]}.xlsx'
    else:
        filename = f'bao_cao_thang_{year}_{month:02d}.xlsx'
    
    return send_file(
        excel_file,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename
    )


## (Policies removed per rollback to pre-scheduling baseline)

