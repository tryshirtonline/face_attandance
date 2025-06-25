from flask import Blueprint, jsonify
from models import JobTitle

api_job_titles_bp = Blueprint('api_job_titles', __name__, url_prefix='/api')

@api_job_titles_bp.route('/job_titles/<int:category_id>', methods=['GET'])
def get_job_titles_by_category(category_id):
    """Get job titles for a specific category"""
    try:
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
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500