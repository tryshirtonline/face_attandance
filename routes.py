import os
from datetime import datetime, date, timedelta
from flask import render_template, request, redirect, url_for, flash, send_file, jsonify
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash
from sqlalchemy import and_, or_, desc
from sqlalchemy.exc import IntegrityError

from app import app, db
from auth import auth_bp, role_required, superuser_required
from api import api_bp

from models import (User, CompanyProfile, JobCategory, JobTitle, Supervisor, 
                   Employee, Attendance, supervisor_categories)
from face_utils_working import face_processor
from report_generator_simple import report_generator
import logging
import io

# Register blueprints
app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(api_bp)


# Allowed file extensions for logo upload
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('auth.login'))

@app.route('/dashboard')
@login_required
def dashboard():
    try:
        # Get user-specific data
        if current_user.role == 'superuser':
            # Superuser dashboard
            total_employees = Employee.query.filter_by(is_active=True).count()
            total_supervisors = Supervisor.query.count()
            total_categories = JobCategory.query.count()
            today_attendance = Attendance.query.filter_by(date=date.today()).count()

            # Recent attendance records
            recent_attendance = Attendance.query.join(Employee).order_by(
                desc(Attendance.datetime)
            ).limit(10).all()

            context = {
                'user_role': 'superuser',
                'total_employees': total_employees,
                'total_supervisors': total_supervisors,
                'total_categories': total_categories,
                'today_attendance': today_attendance,
                'recent_attendance': recent_attendance
            }

        else:  # supervisor
            supervisor = current_user.supervisor_profile
            if not supervisor:
                flash('Supervisor profile not found. Please contact administrator.', 'error')
                return redirect(url_for('auth.logout'))

            # Get all employees accessible to this supervisor
            allowed_category_ids = [cat.id for cat in supervisor.allowed_categories]

            my_employees = Employee.query.join(JobTitle).join(JobCategory).filter(
                and_(
                    Employee.is_active == True,
                    or_(
                        Employee.supervisor_id == supervisor.id,  # Directly assigned employees
                        JobCategory.id.in_(allowed_category_ids)  # Employees in allowed categories
                    )
                )
            ).count()

            # Today's attendance for accessible employees
            today_attendance = Attendance.query.join(Employee).join(JobTitle).join(JobCategory).filter(
                and_(
                    Attendance.date == date.today(),
                    or_(
                        Employee.supervisor_id == supervisor.id,
                        JobCategory.id.in_(allowed_category_ids)
                    )
                )
            ).count()

            # Recent attendance for accessible employees
            recent_attendance = Attendance.query.join(Employee).join(JobTitle).join(JobCategory).filter(
                or_(
                    Employee.supervisor_id == supervisor.id,
                    JobCategory.id.in_(allowed_category_ids)
                )
            ).order_by(desc(Attendance.datetime)).limit(10).all()

            context = {
                'user_role': 'supervisor',
                'my_employees': my_employees,
                'today_attendance': today_attendance,
                'recent_attendance': recent_attendance
            }

        return render_template('dashboard.html', **context)

    except Exception as e:
        logging.error(f"Dashboard error: {str(e)}")
        flash('An error occurred while loading the dashboard.', 'error')
        return render_template('dashboard.html', user_role=current_user.role)

@app.route('/categories')
@login_required
def categories():
    if current_user.role == 'superuser':
        categories = JobCategory.query.order_by(JobCategory.name).all()
    else:
        supervisor = current_user.supervisor_profile
        categories = supervisor.allowed_categories if supervisor else []

    return render_template('categories.html', categories=categories)

@app.route('/categories/add', methods=['GET', 'POST'])
@superuser_required
def add_category():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()

        if not name:
            flash('Category name is required.', 'error')
            return render_template('categories.html')

        # Check if category already exists
        existing = JobCategory.query.filter_by(name=name).first()
        if existing:
            flash('Category with this name already exists.', 'error')
            return redirect(url_for('categories'))

        try:
            category = JobCategory(name=name, created_by_id=current_user.id)
            db.session.add(category)
            db.session.commit()
            flash(f'Category "{name}" added successfully.', 'success')
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error adding category: {str(e)}")
            flash('Error adding category.', 'error')

        return redirect(url_for('categories'))

    return redirect(url_for('categories'))

@app.route('/categories/<int:category_id>/job-titles')
@login_required
def job_titles(category_id):
    category = JobCategory.query.get_or_404(category_id)

    # Check access permissions
    if current_user.role != 'superuser':
        supervisor = current_user.supervisor_profile
        if not supervisor or category not in supervisor.allowed_categories:
            flash('Access denied.', 'error')
            return redirect(url_for('categories'))

    job_titles = JobTitle.query.filter_by(category_id=category_id).order_by(JobTitle.name).all()
    return render_template('job_titles.html', category=category, job_titles=job_titles)

@app.route('/categories/<int:category_id>/job-titles/add', methods=['POST'])
@login_required
def add_job_title(category_id):
    category = JobCategory.query.get_or_404(category_id)

    # Check permissions
    if current_user.role != 'superuser':
        supervisor = current_user.supervisor_profile
        if not supervisor or category not in supervisor.allowed_categories:
            flash('Access denied.', 'error')
            return redirect(url_for('categories'))

    name = request.form.get('name', '').strip()

    if not name:
        flash('Job title name is required.', 'error')
        return redirect(url_for('job_titles', category_id=category_id))

    # Check if job title already exists in this category
    existing = JobTitle.query.filter_by(name=name, category_id=category_id).first()
    if existing:
        flash('Job title with this name already exists in this category.', 'error')
        return redirect(url_for('job_titles', category_id=category_id))

    try:
        job_title = JobTitle(name=name, category_id=category_id)
        db.session.add(job_title)
        db.session.commit()
        flash(f'Job title "{name}" added successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error adding job title: {str(e)}")
        flash('Error adding job title.', 'error')

    return redirect(url_for('job_titles', category_id=category_id))

@app.route('/employees')
@login_required
def employees():
    if current_user.role == 'superuser':
        employees = Employee.query.filter_by(is_active=True).order_by(Employee.name).all()
        # Pass additional data for superuser employee management
        categories = JobCategory.query.order_by(JobCategory.name).all()
        supervisors = Supervisor.query.order_by(Supervisor.full_name).all()
        return render_template('employees.html', 
                             employees=employees, 
                             JobCategory=JobCategory,
                             Supervisor=Supervisor,
                             categories=categories,
                             supervisors=supervisors)
    else:
        supervisor = current_user.supervisor_profile
        if supervisor:
            # Get all employees whose job categories are assigned to this supervisor
            # OR employees directly assigned to this supervisor
            allowed_category_ids = [cat.id for cat in supervisor.allowed_categories]

            employees = Employee.query.join(JobTitle).join(JobCategory).filter(
                and_(
                    Employee.is_active == True,
                    or_(
                        Employee.supervisor_id == supervisor.id,  # Directly assigned employees
                        JobCategory.id.in_(allowed_category_ids)  # Employees in allowed categories
                    )
                )
            ).order_by(Employee.name).all()
        else:
            employees = []

        return render_template('employees.html', employees=employees)

@app.route('/employees/register', methods=['GET', 'POST'])
@login_required
def register_employee():
    if request.method == 'POST':
        try:
            # Get form data
            employee_number = request.form.get('employee_number', '').strip()
            name = request.form.get('name', '').strip()
            job_title_id = request.form.get('job_title_id')
            address = request.form.get('address', '').strip()
            contact_number = request.form.get('contact_number', '').strip()
            email = request.form.get('email', '').strip()
            face_image_data = request.form.get('face_image_data')

            # Validation
            if not all([employee_number, name, job_title_id, face_image_data]):
                flash('All required fields must be filled and face must be captured.', 'error')
                return redirect(url_for('register_employee'))

            # Check if employee number already exists
            existing = Employee.query.filter_by(employee_number=employee_number).first()
            if existing:
                flash('Employee number already exists.', 'error')
                return redirect(url_for('register_employee'))

            # Extract face encoding
            face_encoding = face_processor.extract_face_encoding(face_image_data)
            if face_encoding is None:
                flash('Face registration failed: No face detected in image', 'error')
                return redirect(url_for('register_employee'))

            # Get supervisor for current user (only if supervisor is creating the employee)
            supervisor = current_user.supervisor_profile if current_user.role == 'supervisor' else None

            # Create employee
            employee = Employee(
                employee_number=employee_number,
                name=name,
                job_title_id=int(job_title_id),
                address=address,
                contact_number=contact_number,
                email=email if email else None,
                supervisor_id=supervisor.id if supervisor else None  # Only set if created by supervisor
            )

            # Set face encoding
            employee.set_face_encoding(face_encoding)

            db.session.add(employee)
            db.session.commit()

            flash(f'Employee "{name}" registered successfully.', 'success')
            return redirect(url_for('employees'))

        except Exception as e:
            db.session.rollback()
            logging.error(f"Error registering employee: {str(e)}")
            flash('Error registering employee.', 'error')
            return redirect(url_for('register_employee'))

    # GET request - show registration form
    if current_user.role == 'superuser':
        categories = JobCategory.query.order_by(JobCategory.name).all()
    else:
        supervisor = current_user.supervisor_profile
        categories = supervisor.allowed_categories if supervisor else []

    return render_template('employee_register.html', categories=categories)

@app.route('/attendance/mark')
@login_required
def mark_attendance():
    # Only supervisors can mark attendance
    if current_user.role != 'supervisor':
        flash('Only supervisors can mark attendance.', 'error')
        return redirect(url_for('dashboard'))

    supervisor = current_user.supervisor_profile
    if not supervisor:
        flash('Supervisor profile not found.', 'error')
        return redirect(url_for('dashboard'))

    # Get all employees whose job categories are assigned to this supervisor
    # OR employees directly assigned to this supervisor
    allowed_category_ids = [cat.id for cat in supervisor.allowed_categories]

    employees = Employee.query.join(JobTitle).join(JobCategory).filter(
        and_(
            Employee.is_active == True,
            or_(
                Employee.supervisor_id == supervisor.id,  # Directly assigned employees
                JobCategory.id.in_(allowed_category_ids)  # Employees in allowed categories
            )
        )
    ).all()

    if not employees:
        flash('No employees assigned to you. Please contact administrator.', 'info')
        return redirect(url_for('dashboard'))

    return render_template('attendance_mark.html', employees=employees)

@app.route('/attendance/process', methods=['POST'])
@login_required
def process_attendance():
    try:
        if current_user.role != 'supervisor':
            return jsonify({'success': False, 'message': 'Access denied'})

        supervisor = current_user.supervisor_profile
        if not supervisor:
            return jsonify({'success': False, 'message': 'Supervisor profile not found'})

        # Get form data
        employee_id = request.form.get('employee_id')
        face_image_data = request.form.get('face_image_data')
        latitude = request.form.get('latitude')
        longitude = request.form.get('longitude')

        if not all([employee_id, face_image_data]):
            return jsonify({'success': False, 'message': 'Missing required data'})

        # Get employee - check if supervisor has access to this employee
        employee = Employee.query.get(int(employee_id))

        if not employee or not employee.is_active:
            return jsonify({'success': False, 'message': 'Employee not found'})

        # Check if supervisor has access to this employee
        allowed_category_ids = [cat.id for cat in supervisor.allowed_categories]
        has_access = (
            employee.supervisor_id == supervisor.id or  # Directly assigned
            (employee.job_title and employee.job_title.category_id in allowed_category_ids)  # In allowed category
        )

        if not has_access:
            return jsonify({'success': False, 'message': 'Access denied to this employee'})

        # Check if attendance already marked today
        today_attendance = Attendance.query.filter_by(
            employee_id=employee.id, date=date.today()
        ).first()

        if today_attendance:
            return jsonify({
                'success': False, 
                'message': f'Attendance already marked for {employee.name} today at {today_attendance.time.strftime("%H:%M")}'
            })

        # Get stored face encoding
        known_encoding = employee.get_face_encoding()
        if known_encoding is None:
            return jsonify({'success': False, 'message': 'No face data found for this employee'})

        # Process face recognition with anti-spoofing
        result = face_processor.process_attendance_frame(face_image_data, known_encoding)

        # Log security alerts
        if result.get('security_alert'):
            logging.warning(f"Security Alert for employee {employee.name}: {result['security_alert']}")

        if not result['success']:
            # Include security alert in response if present
            response = {
                'success': False, 
                'message': result['message'],
                'confidence': result.get('confidence', 0.0)
            }
            if result.get('security_alert'):
                response['security_alert'] = result['security_alert']
            return jsonify(response)

        if not result['blink_detected']:
            return jsonify({
                'success': False, 
                'message': 'Please blink to confirm you are a real person',
                'security_alert': 'Anti-spoofing verification required'
            })

        # Create attendance record
        attendance = Attendance(
            employee_id=employee.id,
            date=date.today(),
            time=datetime.now().time(),
            datetime=datetime.now(),
            latitude=float(latitude) if latitude else None,
            longitude=float(longitude) if longitude else None,
            marked_by_id=supervisor.id
        )

        db.session.add(attendance)
        db.session.commit()

        # Reset blink detection for next use
        face_processor.reset_blink_detection()

        return jsonify({
            'success': True, 
            'message': f'Attendance marked successfully for {employee.name}',
            'confidence': f'{result["confidence"]:.2f}'
        })

    except Exception as e:
        db.session.rollback()
        logging.error(f"Error processing attendance: {str(e)}")
        return jsonify({'success': False, 'message': 'Error processing attendance'})

@app.route('/reports')
@login_required
def reports():
    # Get filter options
    if current_user.role == 'superuser':
        categories = JobCategory.query.order_by(JobCategory.name).all()
        supervisors = Supervisor.query.order_by(Supervisor.full_name).all()
    else:
        supervisor = current_user.supervisor_profile
        categories = supervisor.allowed_categories if supervisor else []
        supervisors = []

    return render_template('reports.html', categories=categories, supervisors=supervisors)

@app.route('/reports/generate', methods=['POST'])
@login_required
def generate_report():
    try:
        # Get form data
        report_type = request.form.get('report_type', 'csv')
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')
        supervisor_id = request.form.get('supervisor_id')
        category_id = request.form.get('category_id')
        job_title_id = request.form.get('job_title_id')

        # Parse dates
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date() if start_date_str else None
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else None

        # Convert empty strings to None
        supervisor_id = int(supervisor_id) if supervisor_id else None
        category_id = int(category_id) if category_id else None
        job_title_id = int(job_title_id) if job_title_id else None

        # For supervisors, override supervisor_id with their own ID
        if current_user.role == 'supervisor':
            supervisor_id = current_user.supervisor_profile.id if current_user.supervisor_profile else None

        if report_type == 'csv':
            content, error = report_generator.generate_csv_report(
                start_date, end_date, supervisor_id, category_id, job_title_id, current_user.role
            )

            if error:
                flash(error, 'error')
                return redirect(url_for('reports'))

            # Create filename
            filename = f"attendance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

            return send_file(
                io.BytesIO(content),
                as_attachment=True,
                download_name=filename,
                mimetype='text/csv'
            )

        elif report_type == 'pdf':
            content, error = report_generator.generate_pdf_report(
                start_date, end_date, supervisor_id, category_id, job_title_id, current_user.role
            )

            if error:
                flash(error, 'error')
                return redirect(url_for('reports'))

            # Create filename
            filename = f"attendance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

            return send_file(
                io.BytesIO(content),
                as_attachment=True,
                download_name=filename,
                mimetype='application/pdf'
            )

        else:
            flash('Invalid report type.', 'error')
            return redirect(url_for('reports'))

    except Exception as e:
        logging.error(f"Error generating report: {str(e)}")
        flash('Error generating report.', 'error')
        return redirect(url_for('reports'))

@app.route('/admin')
@superuser_required
def admin_panel():
    # Get company profile
    company = CompanyProfile.query.first()
    if not company:
        company = CompanyProfile()
        db.session.add(company)
        db.session.commit()

    # Get supervisors
    supervisors = Supervisor.query.order_by(Supervisor.full_name).all()
    categories = JobCategory.query.order_by(JobCategory.name).all()

    return render_template('admin_panel.html', 
                         company=company, 
                         supervisors=supervisors, 
                         categories=categories,
                         Employee=Employee)

@app.route('/admin/company-profile', methods=['POST'])
@superuser_required
def update_company_profile():
    try:
        company = CompanyProfile.query.first()
        if not company:
            company = CompanyProfile()
            db.session.add(company)

        # Update company details
        company.name = request.form.get('name', '').strip()
        company.about = request.form.get('about', '').strip()

        # Handle logo upload
        if 'logo' in request.files:
            file = request.files['logo']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                # Add timestamp to avoid conflicts
                filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"

                # Create uploads directory if it doesn't exist
                upload_dir = os.path.join(app.root_path, app.config['UPLOAD_FOLDER'])
                os.makedirs(upload_dir, exist_ok=True)

                file_path = os.path.join(upload_dir, filename)
                file.save(file_path)
                company.logo_filename = filename

        db.session.commit()
        flash('Company profile updated successfully.', 'success')

    except Exception as e:
        db.session.rollback()
        logging.error(f"Error updating company profile: {str(e)}")
        flash('Error updating company profile.', 'error')

    return redirect(url_for('admin_panel'))

@app.route('/admin/supervisors/add', methods=['POST'])
@superuser_required
def add_supervisor():
    try:
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        full_name = request.form.get('full_name', '').strip()
        password = request.form.get('password', '').strip()

        if not all([username, email, full_name, password]):
            flash('All fields are required.', 'error')
            return redirect(url_for('admin_panel'))

        # Check if username or email already exists
        existing_user = User.query.filter(
            or_(User.username == username, User.email == email)
        ).first()

        if existing_user:
            flash('Username or email already exists.', 'error')
            return redirect(url_for('admin_panel'))

        # Create user
        user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password),
            role='supervisor',
            full_name=full_name
        )

        db.session.add(user)
        db.session.flush()  # To get the user ID

        # Create supervisor profile
        supervisor = Supervisor(
            user_id=user.id,
            full_name=full_name
        )

        db.session.add(supervisor)
        db.session.commit()

        flash(f'Supervisor "{full_name}" added successfully.', 'success')

    except Exception as e:
        db.session.rollback()
        logging.error(f"Error adding supervisor: {str(e)}")
        flash('Error adding supervisor.', 'error')

    return redirect(url_for('admin_panel'))

@app.route('/admin/supervisors/edit', methods=['POST'])
@superuser_required
def edit_supervisor():
    try:
        supervisor_id = request.form.get('supervisor_id')
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        full_name = request.form.get('full_name', '').strip()
        password = request.form.get('password', '').strip()
        is_active = bool(request.form.get('is_active'))

        if not supervisor_id or not all([username, email, full_name]):
            flash('All required fields must be filled.', 'error')
            return redirect(url_for('admin_panel'))

        supervisor = Supervisor.query.get_or_404(int(supervisor_id))
        user = supervisor.user

        # Check if username or email already exists (excluding current user)
        existing_user = User.query.filter(
            and_(
                or_(User.username == username, User.email == email),
                User.id != user.id
            )
        ).first()

        if existing_user:
            flash('Username or email already exists.', 'error')
            return redirect(url_for('admin_panel'))

        # Update user details
        user.username = username
        user.email = email
        user.full_name = full_name
        user.is_active = is_active

        # Update password if provided
        if password:
            if len(password) < 6:
                flash('Password must be at least 6 characters long.', 'error')
                return redirect(url_for('admin_panel'))
            user.password_hash = generate_password_hash(password)

        # Update supervisor profile
        supervisor.full_name = full_name

        db.session.commit()
        flash(f'Supervisor "{full_name}" updated successfully.', 'success')

    except Exception as e:
        db.session.rollback()
        logging.error(f"Error editing supervisor: {str(e)}")
        flash('Error updating supervisor.', 'error')

    return redirect(url_for('admin_panel'))

@app.route('/admin/supervisors/<int:supervisor_id>/toggle-status', methods=['POST'])
@superuser_required
def toggle_supervisor_status(supervisor_id):
    try:
        supervisor = Supervisor.query.get_or_404(supervisor_id)
        data = request.get_json()
        new_status = data.get('is_active', True)

        supervisor.user.is_active = new_status
        db.session.commit()

        status_text = 'activated' if new_status else 'deactivated'
        return jsonify({
            'success': True,
            'message': f'Supervisor {supervisor.full_name} {status_text} successfully.'
        })

    except Exception as e:
        db.session.rollback()
        logging.error(f"Error toggling supervisor status: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/supervisors/delete', methods=['POST'])
@superuser_required
def delete_supervisor():
    try:
        supervisor_id = request.form.get('supervisor_id')

        if not supervisor_id:
            flash('Supervisor ID is required.', 'error')
            return redirect(url_for('admin_panel'))

        supervisor = Supervisor.query.get_or_404(int(supervisor_id))
        supervisor_name = supervisor.full_name

        # Check if supervisor has employees
        employee_count = Employee.query.filter_by(supervisor_id=supervisor.id, is_active=True).count()
        if employee_count > 0:
            flash(f'Cannot delete supervisor "{supervisor_name}". They have {employee_count} active employees assigned. Please reassign or deactivate employees first.', 'error')
            return redirect(url_for('admin_panel'))

        # Remove category assignments
        supervisor.allowed_categories.clear()

        # Delete supervisor and associated user
        user = supervisor.user
        db.session.delete(supervisor)
        db.session.delete(user)
        db.session.commit()

        flash(f'Supervisor "{supervisor_name}" deleted successfully.', 'success')

    except Exception as e:
        db.session.rollback()
        logging.error(f"Error deleting supervisor: {str(e)}")
        flash('Error deleting supervisor.', 'error')

    return redirect(url_for('admin_panel'))

@app.route('/admin/supervisor-categories', methods=['POST'])
@superuser_required
def assign_supervisor_categories():
    try:
        supervisor_id = request.form.get('supervisor_id')
        category_ids = request.form.getlist('category_ids')

        if not supervisor_id:
            flash('Please select a supervisor.', 'error')
            return redirect(url_for('admin_panel'))

        supervisor = Supervisor.query.get_or_404(int(supervisor_id))

        # Clear existing assignments
        supervisor.allowed_categories.clear()

        # Add new assignments
        if category_ids:
            categories = JobCategory.query.filter(JobCategory.id.in_(category_ids)).all()
            supervisor.allowed_categories.extend(categories)

        db.session.commit()
        flash(f'Categories assigned to {supervisor.full_name} successfully.', 'success')

    except Exception as e:
        db.session.rollback()
        logging.error(f"Error assigning categories: {str(e)}")
        flash('Error assigning categories.', 'error')

    return redirect(url_for('admin_panel'))

@app.route('/admin/employees/add', methods=['POST'])
@superuser_required
def admin_add_employee():
    try:
        employee_number = request.form.get('employee_number', '').strip()
        name = request.form.get('name', '').strip()
        job_title_id = request.form.get('job_title_id')
        address = request.form.get('address', '').strip()
        contact_number = request.form.get('contact_number', '').strip()
        email = request.form.get('email', '').strip()
        supervisor_id = request.form.get('supervisor_id')
        face_data = request.form.get('face_data')

        # Validation
        if not all([employee_number, name, job_title_id, contact_number]):
            flash('Employee number, name, job title, and contact number are required.', 'error')
            return redirect(url_for('employees'))

        if not face_data:
            flash('Face capture is required for employee registration.', 'error')
            return redirect(url_for('employees'))

        # Check if employee number already exists
        existing = Employee.query.filter_by(employee_number=employee_number).first()
        if existing:
            flash('Employee number already exists.', 'error')
            return redirect(url_for('employees'))

        # Process face encoding
        face_encoding = None
        if face_data:
            try:
                from face_utils_working import face_processor
                face_encoding = face_processor.extract_face_encoding(face_data)
                if not face_encoding:
                    flash('Failed to process face data. Please ensure face is clearly visible and try capturing again.', 'error')
                    return redirect(url_for('employees'))
                logging.info(f"Successfully processed face encoding for employee: {name}")
            except Exception as e:
                logging.error(f"Error processing face encoding: {str(e)}")
                flash('Error processing face data. Please try again.', 'error')
                return redirect(url_for('employees'))

        # Create employee
        employee = Employee(
            employee_number=employee_number,
            name=name,
            job_title_id=int(job_title_id),
            address=address if address else None,
            contact_number=contact_number,
            email=email if email else None,
            supervisor_id=int(supervisor_id) if supervisor_id else None
        )

        # Set face encoding
        if face_encoding:
            employee.set_face_encoding(face_encoding)

        db.session.add(employee)
        db.session.commit()

        flash(f'Employee "{name}" added successfully with face registration.', 'success')

    except Exception as e:
        db.session.rollback()
        logging.error(f"Error adding employee: {str(e)}")
        flash('Error adding employee.', 'error')

    return redirect(url_for('employees'))

@app.route('/admin/employees/edit', methods=['POST'])
@superuser_required
def admin_edit_employee():
    try:
        employee_id = request.form.get('employee_id')
        employee_number = request.form.get('employee_number', '').strip()
        name = request.form.get('name', '').strip()
        job_title_id = request.form.get('job_title_id')
        address = request.form.get('address', '').strip()
        contact_number = request.form.get('contact_number', '').strip()
        email = request.form.get('email', '').strip()
        supervisor_id = request.form.get('supervisor_id')

        if not employee_id or not all([employee_number, name, job_title_id, contact_number]):
            flash('All required fields must be filled.', 'error')
            return redirect(url_for('admin_panel'))

        employee = Employee.query.get_or_404(int(employee_id))

        # Check if employee number already exists (excluding current employee)
        existing = Employee.query.filter(
            and_(
                Employee.employee_number == employee_number,
                Employee.id != employee.id
            )
        ).first()

        if existing:
            flash('Employee number already exists.', 'error')
            return redirect(url_for('admin_panel'))

        # Update employee details
        employee.employee_number = employee_number
        employee.name = name
        employee.job_title_id = int(job_title_id)
        employee.address = address if address else None
        employee.contact_number = contact_number
        employee.email = email if email else None
        employee.supervisor_id = int(supervisor_id) if supervisor_id else None

        db.session.commit()
        flash(f'Employee "{name}" updated successfully.', 'success')

    except Exception as e:
        db.session.rollback()
        logging.error(f"Error editing employee: {str(e)}")
        flash('Error updating employee.', 'error')

    return redirect(url_for('admin_panel'))

@app.route('/admin/employees/delete', methods=['POST'])
@superuser_required
def admin_delete_employee():
    try:
        employee_id = request.form.get('employee_id')

        if not employee_id:
            flash('Employee ID is required.', 'error')
            return redirect(url_for('admin_panel'))

        employee = Employee.query.get_or_404(int(employee_id))
        employee_name = employee.name

        # Delete attendance records first
        Attendance.query.filter_by(employee_id=employee.id).delete()

        # Delete employee
        db.session.delete(employee)
        db.session.commit()

        flash(f'Employee "{employee_name}" deleted successfully.', 'success')

    except Exception as e:
        db.session.rollback()
        logging.error(f"Error deleting employee: {str(e)}")
        flash('Error deleting employee.', 'error')

    return redirect(url_for('admin_panel'))

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500

# Context processor to make company info available in all templates
@app.context_processor
def inject_company_info():
    company = CompanyProfile.query.first()
    return dict(company=company, current_year=datetime.now().year)