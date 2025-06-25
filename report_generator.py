import pandas as pd
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
        try:
            query = Attendance.query.join(Employee).join(JobTitle).join(JobCategory)
            
            # Apply date filters
            if start_date:
                query = query.filter(Attendance.date >= start_date)
            if end_date:
                query = query.filter(Attendance.date <= end_date)
            
            # Apply role-based filters
            if user_role != 'superuser' and supervisor_id:
                query = query.filter(Employee.supervisor_id == supervisor_id)
            
            # Apply category filter
            if category_id:
                query = query.filter(JobTitle.category_id == category_id)
            
            # Apply job title filter
            if job_title_id:
                query = query.filter(Employee.job_title_id == job_title_id)
            
            # Apply supervisor filter (for superuser)
            if user_role == 'superuser' and supervisor_id:
                query = query.filter(Employee.supervisor_id == supervisor_id)
            
            attendance_records = query.order_by(Attendance.date.desc(), Attendance.time.desc()).all()
            
            data = []
            for record in attendance_records:
                data.append({
                    'Date': record.date.strftime('%Y-%m-%d'),
                    'Time': record.time.strftime('%H:%M:%S'),
                    'Employee Number': record.employee.employee_number,
                    'Employee Name': record.employee.name,
                    'Job Title': record.employee.job_title.name if record.employee.job_title else 'N/A',
                    'Category': record.employee.job_title.category.name if record.employee.job_title else 'N/A',
                    'Supervisor': record.marked_by_supervisor.full_name if record.marked_by_supervisor else 'N/A',
                    'Latitude': record.latitude if record.latitude else 'N/A',
                    'Longitude': record.longitude if record.longitude else 'N/A'
                })
            
            return data
        except Exception as e:
            logging.error(f"Error getting attendance data: {str(e)}")
            return []
    
    def generate_csv_report(self, start_date=None, end_date=None, supervisor_id=None,
                           category_id=None, job_title_id=None, user_role='superuser'):
        """Generate CSV report"""
        try:
            data = self.get_attendance_data(start_date, end_date, supervisor_id, 
                                          category_id, job_title_id, user_role)
            
            if not data:
                return None, "No attendance records found for the selected criteria"
            
            df = pd.DataFrame(data)
            
            # Create CSV string
            csv_buffer = io.StringIO()
            df.to_csv(csv_buffer, index=False)
            csv_content = csv_buffer.getvalue()
            csv_buffer.close()
            
            return csv_content.encode('utf-8'), None
            
        except Exception as e:
            logging.error(f"Error generating CSV report: {str(e)}")
            return None, f"Error generating CSV report: {str(e)}"
    
    def generate_pdf_report(self, start_date=None, end_date=None, supervisor_id=None,
                           category_id=None, job_title_id=None, user_role='superuser'):
        """Generate PDF report"""
        try:
            data = self.get_attendance_data(start_date, end_date, supervisor_id,
                                          category_id, job_title_id, user_role)
            
            if not data:
                return None, "No attendance records found for the selected criteria"
            
            # Create PDF buffer
            pdf_buffer = io.BytesIO()
            doc = SimpleDocTemplate(pdf_buffer, pagesize=A4)
            story = []
            
            # Get company profile
            company = CompanyProfile.query.first()
            company_name = company.name if company else "Company Name"
            
            # Add title
            title = Paragraph(f"{company_name}<br/>Attendance Report", self.title_style)
            story.append(title)
            story.append(Spacer(1, 12))
            
            # Add report parameters
            params = []
            if start_date:
                params.append(f"From: {start_date}")
            if end_date:
                params.append(f"To: {end_date}")
            
            if params:
                param_text = " | ".join(params)
                param_para = Paragraph(param_text, self.styles['Normal'])
                story.append(param_para)
                story.append(Spacer(1, 12))
            
            # Add generation date
            gen_date = Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 
                               self.styles['Normal'])
            story.append(gen_date)
            story.append(Spacer(1, 20))
            
            # Create table data
            table_data = [['Date', 'Time', 'Emp. No.', 'Employee Name', 'Job Title', 'Category']]
            
            for record in data:
                table_data.append([
                    record['Date'],
                    record['Time'],
                    record['Employee Number'],
                    record['Employee Name'][:15] + '...' if len(record['Employee Name']) > 15 else record['Employee Name'],
                    record['Job Title'][:12] + '...' if len(record['Job Title']) > 12 else record['Job Title'],
                    record['Category'][:10] + '...' if len(record['Category']) > 10 else record['Category']
                ])
            
            # Create table
            table = Table(table_data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(table)
            
            # Add summary
            story.append(Spacer(1, 20))
            summary = Paragraph(f"Total Records: {len(data)}", self.styles['Normal'])
            story.append(summary)
            
            # Build PDF
            doc.build(story)
            pdf_content = pdf_buffer.getvalue()
            pdf_buffer.close()
            
            return pdf_content, None
            
        except Exception as e:
            logging.error(f"Error generating PDF report: {str(e)}")
            return None, f"Error generating PDF report: {str(e)}"
    
    def get_attendance_summary(self, start_date=None, end_date=None, supervisor_id=None, user_role='superuser'):
        """Get attendance summary statistics"""
        try:
            data = self.get_attendance_data(start_date, end_date, supervisor_id, user_role=user_role)
            
            if not data:
                return {
                    'total_records': 0,
                    'unique_employees': 0,
                    'categories': 0,
                    'date_range': 'No data'
                }
            
            df = pd.DataFrame(data)
            
            summary = {
                'total_records': len(df),
                'unique_employees': df['Employee Number'].nunique(),
                'categories': df['Category'].nunique(),
                'date_range': f"{df['Date'].min()} to {df['Date'].max()}" if len(df) > 0 else 'No data'
            }
            
            return summary
            
        except Exception as e:
            logging.error(f"Error getting attendance summary: {str(e)}")
            return {
                'total_records': 0,
                'unique_employees': 0,
                'categories': 0,
                'date_range': 'Error'
            }

# Global report generator instance
report_generator = ReportGenerator()
