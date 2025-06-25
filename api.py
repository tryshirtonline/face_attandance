from flask import Blueprint, jsonify, request
from datetime import datetime, date
from models import Employee, Attendance, JobTitle, JobCategory, Supervisor
from app import db
import logging

api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.route('/employees', methods=['GET'])
def get_employees():
    """Get list of all employees for .NET integration"""
    try:
        employees = Employee.query.filter_by(is_active=True).all()

        employee_list = []
        for emp in employees:
            employee_data = {
                'id': emp.id,
                'employee_number': emp.employee_number,
                'name': emp.name,
                'job_title': emp.job_title.name if emp.job_title else None,
                'category': emp.job_title.category.name if emp.job_title else None,
                'contact_number': emp.contact_number,
                'email': emp.email,
                'supervisor': emp.supervisor.full_name if emp.supervisor else None,
                'created_at': emp.created_at.isoformat() if emp.created_at else None
            }
            employee_list.append(employee_data)

        return jsonify({
            'success': True,
            'employees': employee_list,
            'total': len(employee_list)
        })

    except Exception as e:
        logging.error(f"Error getting employees: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/attendance/daily', methods=['GET'])
def get_daily_attendance():
    """Get attendance records for a specific date"""
    try:
        # Get date from query parameter, default to today
        date_str = request.args.get('date', date.today().isoformat())

        try:
            attendance_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({
                'success': False,
                'error': 'Invalid date format. Use YYYY-MM-DD'
            }), 400

        # Query attendance records for the date
        attendance_records = Attendance.query.filter_by(date=attendance_date).all()

        attendance_list = []
        for record in attendance_records:
            attendance_data = {
                'id': record.id,
                'employee_id': record.employee.employee_number,
                'employee_name': record.employee.name,
                'date': record.date.isoformat(),
                'time': record.time.strftime('%H:%M:%S'),
                'datetime': record.datetime.isoformat() if record.datetime else None,
                'latitude': record.latitude,
                'longitude': record.longitude,
                'job_title': record.employee.job_title.name if record.employee.job_title else None,
                'category': record.employee.job_title.category.name if record.employee.job_title else None,
                'supervisor': record.marked_by_supervisor.full_name if record.marked_by_supervisor else None
            }
            attendance_list.append(attendance_data)

        return jsonify({
            'success': True,
            'date': date_str,
            'attendance': attendance_list,
            'total': len(attendance_list)
        })

    except Exception as e:
        logging.error(f"Error getting daily attendance: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/job_titles/<int:category_id>', methods=['GET'])
def get_job_titles_by_category(category_id):
    """Get job titles for a specific category"""
    try:
        from models import JobTitle
        job_titles = JobTitle.query.filter_by(category_id=category_id).order_by(JobTitle.name).all()
        
        titles_list = []
        for title in job_titles:
            titles_list.append({
                'id': title.id,
                'name': title.name
            })
        
        return jsonify({
            'success': True,
            'job_titles': titles_list
        })
        
    except Exception as e:
        logging.error(f"Error getting job titles: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/attendance/range', methods=['GET'])
def get_attendance_range():
    """Get attendance records for a date range"""
    try:
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')

        if not start_date_str or not end_date_str:
            return jsonify({
                'success': False,
                'error': 'Both start_date and end_date are required'
            }), 400

        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({
                'success': False,
                'error': 'Invalid date format. Use YYYY-MM-DD'
            }), 400

        # Query attendance records for the date range
        attendance_records = Attendance.query.filter(
            Attendance.date >= start_date,
            Attendance.date <= end_date
        ).order_by(Attendance.date.desc(), Attendance.time.desc()).all()

        attendance_list = []
        for record in attendance_records:
            attendance_data = {
                'id': record.id,
                'employee_id': record.employee.employee_number,
                'employee_name': record.employee.name,
                'date': record.date.isoformat(),
                'time': record.time.strftime('%H:%M:%S'),
                'datetime': record.datetime.isoformat() if record.datetime else None,
                'latitude': record.latitude,
                'longitude': record.longitude,
                'job_title': record.employee.job_title.name if record.employee.job_title else None,
                'category': record.employee.job_title.category.name if record.employee.job_title else None,
                'supervisor': record.marked_by_supervisor.full_name if record.marked_by_supervisor else None
            }
            attendance_list.append(attendance_data)

        return jsonify({
            'success': True,
            'start_date': start_date_str,
            'end_date': end_date_str,
            'attendance': attendance_list,
            'total': len(attendance_list)
        })

    except Exception as e:
        logging.error(f"Error getting attendance range: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/sync-to-dotnet', methods=['POST'])
def sync_to_dotnet():
    """Endpoint for .NET system to receive attendance data"""
    try:
        # Get date from request, default to today
        request_data = request.get_json() or {}
        date_str = request_data.get('date', date.today().isoformat())

        try:
            attendance_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({
                'success': False,
                'error': 'Invalid date format. Use YYYY-MM-DD'
            }), 400

        # Get attendance records for the date
        attendance_records = Attendance.query.filter_by(date=attendance_date).all()

        sync_data = []
        for record in attendance_records:
            sync_record = {
                'employee_id': record.employee.employee_number,
                'name': record.employee.name,
                'date': record.date.isoformat(),
                'time': record.time.strftime('%H:%M:%S'),
                'latitude': record.latitude,
                'longitude': record.longitude,
                'job_title': record.employee.job_title.name if record.employee.job_title else None,
                'category': record.employee.job_title.category.name if record.employee.job_title else None
            }
            sync_data.append(sync_record)

        # Log sync attempt
        logging.info(f"Syncing {len(sync_data)} attendance records for {date_str} to .NET system")

        return jsonify({
            'success': True,
            'date': date_str,
            'records_synced': len(sync_data),
            'data': sync_data
        })

    except Exception as e:
        logging.error(f"Error syncing to .NET: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/statistics', methods=['GET'])
def get_statistics():
    """Get system statistics"""
    try:
        stats = {
            'total_employees': Employee.query.filter_by(is_active=True).count(),
            'total_supervisors': Supervisor.query.count(),
            'total_categories': JobCategory.query.count(),
            'total_job_titles': JobTitle.query.count(),
            'today_attendance': Attendance.query.filter_by(date=date.today()).count(),
            'total_attendance_records': Attendance.query.count()
        }

        return jsonify({
            'success': True,
            'statistics': stats
        })

    except Exception as e:
        logging.error(f"Error getting statistics: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

from flask_login import login_required, current_user  # Import necessary modules

@api_bp.route('/categories/<int:category_id>/job-titles')
@login_required
def get_job_titles(category_id):
    """Get job titles for a specific category"""
    try:
        # Check if user has access to this category
        category = JobCategory.query.get_or_404(category_id)

        if current_user.role != 'superuser':
            supervisor = current_user.supervisor_profile
            if not supervisor or category not in supervisor.allowed_categories:
                return jsonify({'error': 'Access denied'}), 403

        # Get job titles for this category
        job_titles = JobTitle.query.filter_by(category_id=category_id).order_by(JobTitle.name).all()

        return jsonify({
            'job_titles': [
                {
                    'id': jt.id,
                    'name': jt.name
                }
                for jt in job_titles
            ]
        })

    except Exception as e:
        logging.error(f"Error getting job titles: {str(e)}")
        return jsonify({'error': 'Failed to load job titles'}), 500

@api_bp.route('/supervisors/<int:supervisor_id>/categories')
@login_required
def get_supervisor_categories(supervisor_id):
    """Get categories assigned to a supervisor"""
    try:
        # Only superusers can access this
        if current_user.role != 'superuser':
            return jsonify({'error': 'Access denied'}), 403

        supervisor = Supervisor.query.get_or_404(supervisor_id)

        category_ids = [category.id for category in supervisor.allowed_categories]

        return jsonify({
            'success': True,
            'category_ids': category_ids
        })

    except Exception as e:
        logging.error(f"Error getting supervisor categories: {str(e)}")
        return jsonify({'error': 'Failed to load supervisor categories'}), 500

@api_bp.route('/employees/<int:employee_id>')
@login_required
def get_employee_details(employee_id):
    try:
        if current_user.role != 'superuser':
            return jsonify({'success': False, 'error': 'Access denied'}), 403

        employee = Employee.query.get_or_404(employee_id)

        employee_data = {
            'id': employee.id,
            'employee_number': employee.employee_number,
            'name': employee.name,
            'contact_number': employee.contact_number,
            'email': employee.email,
            'address': employee.address,
            'job_title': employee.job_title.name if employee.job_title else None,
            'category': employee.job_title.category.name if employee.job_title and employee.job_title.category else None,
            'supervisor': employee.supervisor.full_name if employee.supervisor else None,
            'face_registered': employee.face_encoding is not None
        }

        return jsonify({'success': True, 'employee': employee_data})

    except Exception as e:
        logging.error(f"Error getting employee details: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to load employee details'}), 500

@api_bp.route('/job-titles/<int:job_title_id>/category')
@login_required
def get_job_title_category(job_title_id):
    try:
        job_title = JobTitle.query.get_or_404(job_title_id)
        return jsonify({
            'success': True, 
            'category_id': job_title.category_id,
            'category_name': job_title.category.name
        })

    except Exception as e:
        logging.error(f"Error getting job title category: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to load category'}), 500

# Register the blueprint in routes.py