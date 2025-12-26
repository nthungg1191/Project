"""Reports Service - Xử lý logic báo cáo và thống kê"""
from app import db
from app.models import Employee, Attendance, Department, WorkSchedule
from datetime import date, datetime, timedelta
from sqlalchemy import func, and_, or_, extract
from collections import defaultdict
import calendar


class ReportsService:
    """Service for generating attendance reports and statistics"""
    
    @staticmethod
    def get_daily_report(report_date: date = None):
        """Báo cáo theo ngày"""
        if report_date is None:
            report_date = date.today()
        
        # Tổng số nhân viên
        total_employees = Employee.query.filter_by(is_active=True).count()
        
        # Attendance records cho ngày
        attendances = Attendance.query.filter_by(date=report_date).all()
        
        # Thống kê
        present_count = sum(1 for a in attendances if a.status == 'present')
        late_count = sum(1 for a in attendances if a.status == 'late')
        absent_count = total_employees - len(attendances)
        early_leave_count = sum(1 for a in attendances if a.status == 'early_leave')
        
        # Tính tỷ lệ
        attendance_rate = (len(attendances) / total_employees * 100) if total_employees > 0 else 0
        on_time_rate = (present_count / total_employees * 100) if total_employees > 0 else 0
        
        # Tổng giờ làm việc
        total_working_hours = sum(a.working_hours for a in attendances if a.working_hours)
        total_overtime_hours = sum(a.overtime_hours for a in attendances if a.overtime_hours)
        
        return {
            'date': report_date.isoformat(),
            'total_employees': total_employees,
            'checked_in': len(attendances),
            'present': present_count,
            'late': late_count,
            'absent': absent_count,
            'early_leave': early_leave_count,
            'attendance_rate': round(attendance_rate, 2),
            'on_time_rate': round(on_time_rate, 2),
            'total_working_hours': round(total_working_hours, 2),
            'total_overtime_hours': round(total_overtime_hours, 2),
            'attendances': [a.to_dict() for a in attendances]
        }
    
    @staticmethod
    def get_weekly_report(start_date: date = None):
        """Báo cáo theo tuần"""
        if start_date is None:
            # Bắt đầu từ thứ 2 của tuần hiện tại
            today = date.today()
            days_since_monday = today.weekday()
            start_date = today - timedelta(days=days_since_monday)
        
        end_date = start_date + timedelta(days=6)
        
        # Lấy tất cả attendance trong tuần
        attendances = Attendance.query.filter(
            and_(
                Attendance.date >= start_date,
                Attendance.date <= end_date
            )
        ).all()
        
        # Group by date
        daily_stats = defaultdict(lambda: {
            'date': None,
            'present': 0,
            'late': 0,
            'absent': 0,
            'early_leave': 0,
            'total': 0,
            'working_hours': 0
        })
        
        total_employees = Employee.query.filter_by(is_active=True).count()
        
        # Tính toán cho từng ngày
        for day_offset in range(7):
            current_date = start_date + timedelta(days=day_offset)
            day_attendances = [a for a in attendances if a.date == current_date]
            
            daily_stats[current_date] = {
                'date': current_date.isoformat(),
                'present': sum(1 for a in day_attendances if a.status == 'present'),
                'late': sum(1 for a in day_attendances if a.status == 'late'),
                'absent': total_employees - len(day_attendances),
                'early_leave': sum(1 for a in day_attendances if a.status == 'early_leave'),
                'total': len(day_attendances),
                'working_hours': round(sum(a.working_hours for a in day_attendances if a.working_hours), 2)
            }
        
        # Tổng hợp tuần
        week_total_present = sum(s['present'] for s in daily_stats.values())
        week_total_late = sum(s['late'] for s in daily_stats.values())
        week_total_absent = sum(s['absent'] for s in daily_stats.values())
        week_total_hours = sum(s['working_hours'] for s in daily_stats.values())
        
        return {
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'total_employees': total_employees,
            'week_total_present': week_total_present,
            'week_total_late': week_total_late,
            'week_total_absent': week_total_absent,
            'week_total_hours': round(week_total_hours, 2),
            'average_attendance_rate': round((week_total_present / (total_employees * 7) * 100) if total_employees > 0 else 0, 2),
            'daily_stats': list(daily_stats.values())
        }
    
    @staticmethod
    def get_monthly_report(year: int = None, month: int = None):
        """Báo cáo theo tháng"""
        if year is None or month is None:
            today = date.today()
            year = today.year
            month = today.month
        
        start_date = date(year, month, 1)
        # Ngày cuối cùng của tháng
        last_day = calendar.monthrange(year, month)[1]
        end_date = date(year, month, last_day)
        
        # Lấy tất cả attendance trong tháng
        attendances = Attendance.query.filter(
            and_(
                Attendance.date >= start_date,
                Attendance.date <= end_date
            )
        ).all()
        
        total_employees = Employee.query.filter_by(is_active=True).count()
        total_days = (end_date - start_date).days + 1
        
        # Thống kê tổng hợp
        total_present = sum(1 for a in attendances if a.status == 'present')
        total_late = sum(1 for a in attendances if a.status == 'late')
        total_early_leave = sum(1 for a in attendances if a.status == 'early_leave')
        total_working_hours = sum(a.working_hours for a in attendances if a.working_hours)
        total_overtime_hours = sum(a.overtime_hours for a in attendances if a.overtime_hours)
        
        # Tính số ngày vắng mặt
        expected_attendance = total_employees * total_days
        actual_attendance = len(attendances)
        total_absent = expected_attendance - actual_attendance
        
        # Group by date
        daily_stats = defaultdict(lambda: {
            'date': None,
            'present': 0,
            'late': 0,
            'absent': 0,
            'early_leave': 0,
            'total': 0
        })
        
        for day_offset in range(total_days):
            current_date = start_date + timedelta(days=day_offset)
            day_attendances = [a for a in attendances if a.date == current_date]
            
            daily_stats[current_date] = {
                'date': current_date.isoformat(),
                'present': sum(1 for a in day_attendances if a.status == 'present'),
                'late': sum(1 for a in day_attendances if a.status == 'late'),
                'absent': total_employees - len(day_attendances),
                'early_leave': sum(1 for a in day_attendances if a.status == 'early_leave'),
                'total': len(day_attendances)
            }
        
        return {
            'year': year,
            'month': month,
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'total_employees': total_employees,
            'total_days': total_days,
            'total_present': total_present,
            'total_late': total_late,
            'total_absent': total_absent,
            'total_early_leave': total_early_leave,
            'total_working_hours': round(total_working_hours, 2),
            'total_overtime_hours': round(total_overtime_hours, 2),
            'average_attendance_rate': round((actual_attendance / expected_attendance * 100) if expected_attendance > 0 else 0, 2),
            'on_time_rate': round((total_present / expected_attendance * 100) if expected_attendance > 0 else 0, 2),
            'daily_stats': list(daily_stats.values())
        }
    
    @staticmethod
    def get_department_report(report_date: date = None, department_id: int = None):
        """Báo cáo theo phòng ban"""
        if report_date is None:
            report_date = date.today()
        
        # Query employees
        query = Employee.query.filter_by(is_active=True)
        if department_id:
            query = query.filter_by(department_id=department_id)
        
        employees = query.all()
        
        # Lấy attendance
        employee_ids = [e.id for e in employees]
        attendances = Attendance.query.filter(
            and_(
                Attendance.date == report_date,
                Attendance.employee_id.in_(employee_ids)
            )
        ).all()
        
        # Thống kê
        present_count = sum(1 for a in attendances if a.status == 'present')
        late_count = sum(1 for a in attendances if a.status == 'late')
        absent_count = len(employees) - len(attendances)
        
        return {
            'date': report_date.isoformat(),
            'department_id': department_id,
            'total_employees': len(employees),
            'present': present_count,
            'late': late_count,
            'absent': absent_count,
            'attendance_rate': round((len(attendances) / len(employees) * 100) if len(employees) > 0 else 0, 2)
        }
    
    @staticmethod
    def get_employee_attendance_summary(employee_id: int, start_date: date, end_date: date):
        """Tóm tắt chấm công của một nhân viên trong khoảng thời gian"""
        attendances = Attendance.query.filter(
            and_(
                Attendance.employee_id == employee_id,
                Attendance.date >= start_date,
                Attendance.date <= end_date
            )
        ).all()
        
        total_days = (end_date - start_date).days + 1
        present_days = sum(1 for a in attendances if a.status in ['present', 'late'])
        absent_days = total_days - len(attendances)
        late_days = sum(1 for a in attendances if a.status == 'late')
        total_working_hours = sum(a.working_hours for a in attendances if a.working_hours)
        
        return {
            'employee_id': employee_id,
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'total_days': total_days,
            'present_days': present_days,
            'absent_days': absent_days,
            'late_days': late_days,
            'attendance_rate': round((present_days / total_days * 100) if total_days > 0 else 0, 2),
            'total_working_hours': round(total_working_hours, 2),
            'average_hours_per_day': round(total_working_hours / present_days, 2) if present_days > 0 else 0
        }
    
    @staticmethod
    def get_late_employees(report_date: date = None, limit: int = 10):
        """Danh sách nhân viên đi muộn"""
        if report_date is None:
            report_date = date.today()
        
        attendances = Attendance.query.filter(
            and_(
                Attendance.date == report_date,
                Attendance.status == 'late'
            )
        ).order_by(Attendance.check_in_time.asc()).limit(limit).all()
        
        return [a.to_dict() for a in attendances]
    
    @staticmethod
    def get_absent_employees(report_date: date = None):
        """Danh sách nhân viên vắng mặt"""
        if report_date is None:
            report_date = date.today()
        
        # Lấy tất cả nhân viên active
        all_employees = Employee.query.filter_by(is_active=True).all()
        
        # Lấy những người đã chấm công
        checked_in_ids = db.session.query(Attendance.employee_id).filter_by(date=report_date).all()
        checked_in_ids = [id[0] for id in checked_in_ids]
        
        # Những người chưa chấm công
        absent_employees = [e for e in all_employees if e.id not in checked_in_ids]
        
        return [e.to_dict() for e in absent_employees]

