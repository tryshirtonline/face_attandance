"""
Simplified report generator without pandas dependency
"""
import io
import os
from datetime import datetime, timedelta
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from models import Attendance, Employee, JobCategory, JobTitle, Supervisor, CompanyProfile
from sqlalchemy import and_, or_
import logging

class ReportGenerator:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=16,
            spaceAfter=30,
            alignment=1  # Center alignment
        )
        
    def get_attendance_data(self, start_date=None, end_date=None, supervisor_id=None, 
                          category_id=None, job_title_id=None, user_role='superuser'):
        """Get filtered attendance data"""
        from app import db
        
        # Base query
        query = db.session.query(
            Attendance.date,
            Attendance.time,
            Employee.name,
            Employee.employee_number,
            JobTitle.name.label('job_title'),
            JobCategory.name.label('category'),
            Supervisor.full_name.label('supervisor_name')
        ).join(Employee).join(JobTitle).join(JobCategory).join(Supervisor)
        
        # Apply filters based on user role
        if user_role == 'supervisor' and supervisor_id:
            query = query.filter(Employee.supervisor_id == supervisor_id)
        
        # Date range filter
        if start_date:
            query = query.filter(Attendance.date >= start_date)
        if end_date:
            query = query.filter(Attendance.date <= end_date)
            
        # Additional filters
        if category_id:
            query = query.filter(JobTitle.category_id == category_id)
        if job_title_id:
            query = query.filter(Employee.job_title_id == job_title_id)
            
        return query.all()
    
    def generate_csv_report(self, start_date=None, end_date=None, supervisor_id=None,
                           category_id=None, job_title_id=None, user_role='superuser'):
        """Generate CSV report"""
        data = self.get_attendance_data(start_date, end_date, supervisor_id, 
                                      category_id, job_title_id, user_role)
        
        # Create CSV content
        csv_content = "Date,Time,Employee Name,Employee Number,Job Title,Category,Supervisor\n"
        
        for record in data:
            csv_content += f"{record.date},{record.time},{record.name},{record.employee_number},"
            csv_content += f"{record.job_title},{record.category},{record.supervisor_name}\n"
        
        # Create in-memory file
        output = io.StringIO()
        output.write(csv_content)
        output.seek(0)
        
        return output
    
    def generate_pdf_report(self, start_date=None, end_date=None, supervisor_id=None,
                           category_id=None, job_title_id=None, user_role='superuser'):
        """Generate PDF report"""
        data = self.get_attendance_data(start_date, end_date, supervisor_id, 
                                      category_id, job_title_id, user_role)
        
        # Create in-memory file
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        elements = []
        
        # Get company info
        from app import db
        company = db.session.query(CompanyProfile).first()
        company_name = company.name if company else "Company Name"
        
        # Title
        title = Paragraph(f"Attendance Report - {company_name}", self.title_style)
        elements.append(title)
        elements.append(Spacer(1, 12))
        
        # Date range info
        if start_date or end_date:
            date_info = f"Period: {start_date or 'Beginning'} to {end_date or 'Present'}"
            elements.append(Paragraph(date_info, self.styles['Normal']))
            elements.append(Spacer(1, 12))
        
        # Create table data
        table_data = [['Date', 'Time', 'Employee', 'Number', 'Job Title', 'Category', 'Supervisor']]
        
        for record in data:
            table_data.append([
                str(record.date),
                str(record.time),
                record.name,
                record.employee_number,
                record.job_title,
                record.category,
                record.supervisor_name
            ])
        
        # Create table
        if len(table_data) > 1:
            table = Table(table_data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            elements.append(table)
        else:
            elements.append(Paragraph("No attendance records found for the specified criteria.", self.styles['Normal']))
        
        # Build PDF
        doc.build(elements)
        buffer.seek(0)
        
        return buffer
    
    def get_attendance_summary(self, start_date=None, end_date=None, supervisor_id=None, user_role='superuser'):
        """Get attendance summary statistics"""
        from app import db
        
        # Base query for unique attendance records
        query = db.session.query(Attendance).join(Employee)
        
        if user_role == 'supervisor' and supervisor_id:
            query = query.filter(Employee.supervisor_id == supervisor_id)
        
        if start_date:
            query = query.filter(Attendance.date >= start_date)
        if end_date:
            query = query.filter(Attendance.date <= end_date)
        
        total_records = query.count()
        
        # Get unique employees count
        unique_employees = query.with_entities(Attendance.employee_id).distinct().count()
        
        return {
            'total_records': total_records,
            'unique_employees': unique_employees,
            'period_start': start_date,
            'period_end': end_date
        }

# Create global instance
report_generator = ReportGenerator()