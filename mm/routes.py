"""Montessori Materials routes - admin and public student pages."""

from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from datetime import datetime
import logging
import uuid
from db import db
from models import MUser, MontessoriPackage, MUserPackage, UserTable

logger = logging.getLogger(__name__)

mm_bp = Blueprint("mm", __name__)


def verify_admin():
    """Check if current user is admin."""
    if not current_user.is_authenticated or current_user.user_role != "admin":
        return False
    return True


def generate_token():
    """Generate unique token for student."""
    return str(uuid.uuid4())[:12].upper()


# ==================== PUBLIC STUDENT VIEW ==================== #

@mm_bp.route('/view/<token>')
def student_packages(token):
    """Display packages for student via token - no login required."""
    muser = MUser.query.filter_by(token=token).first()
    
    if not muser:
        flash("Invalid or expired access link", "danger")
        return redirect(url_for("lms.login"))
    
    # Get packages assigned to this student
    packages = db.session.query(
        MontessoriPackage.id,
        MontessoriPackage.subject,
        MontessoriPackage.topic,
        MontessoriPackage.work,
        MontessoriPackage.link,
        MUserPackage.assigned_date,
        MUserPackage.click_count,
        MUserPackage.last_accessed
    ).join(
        MUserPackage,
        MUserPackage.package_id == MontessoriPackage.id
    ).filter(
        MUserPackage.muser_id == muser.id,
        MontessoriPackage.is_deleted == False
    ).order_by(
        MUserPackage.assigned_date.desc()
    ).all()
    
    package_list = []
    for pkg_id, subject, topic, work, link, assigned_date, click_count, last_accessed in packages:
        package_list.append({
            'id': pkg_id,
            'subject': subject,
            'topic': topic,
            'work': work,
            'link': link,
            'assigned_date': assigned_date,
            'click_count': click_count or 0,
            'last_accessed': last_accessed
        })
    
    return render_template(
        'montessori_student.html',
        student_name=muser.name,
        packages=package_list,
        token=token
    )


@mm_bp.route('/track/<token>/<int:package_id>', methods=['POST'])
def track_package_click(token, package_id):
    """Track when student clicks on a package."""
    muser = MUser.query.filter_by(token=token).first()
    
    if not muser:
        return {'ok': False, 'error': 'Invalid token'}, 403
    
    user_package = MUserPackage.query.filter_by(
        muser_id=muser.id,
        package_id=package_id
    ).first()
    
    if user_package:
        user_package.click_count = (user_package.click_count or 0) + 1
        user_package.last_accessed = datetime.now()
        db.session.commit()
    
    return {'ok': True, 'click_count': user_package.click_count if user_package else 0}


# ==================== ADMIN: MANAGE STUDENTS ==================== #

@mm_bp.route('/montessori_admin', methods=['GET', 'POST'])
@login_required
def admin_students():
    """Admin page: manage Montessori students."""
    if not verify_admin():
        flash("Admin access required", "danger")
        return redirect(url_for("lms.login"))
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add':
            name = request.form.get('name', '').strip()
            if not name:
                flash("Student name required", "danger")
            else:
                token = generate_token()
                new_student = MUser(name=name, token=token)
                db.session.add(new_student)
                db.session.commit()
                flash(f"Student '{name}' added successfully!", "success")
        
        elif action == 'delete':
            student_id = request.form.get('student_id')
            student = MUser.query.get(student_id)
            if student:
                # Delete related package assignments first
                MUserPackage.query.filter_by(muser_id=student.id).delete()
                db.session.delete(student)
                db.session.commit()
                flash(f"Student '{student.name}' deleted", "success")
    
    students = MUser.query.order_by(MUser.name).all()
    
    # Build full links for each student
    students_with_links = []
    for student in students:
        full_link = url_for('mm.student_packages', token=student.token, _external=True)
        students_with_links.append({
            'id': student.id,
            'name': student.name,
            'token': student.token,
            'link': full_link,
            'created_at': student.created_at
        })
    
    return render_template('montessori_admin_students.html', students=students_with_links)


# ==================== ADMIN: ASSIGN WORK TO STUDENT ==================== #

@mm_bp.route('/montessori_admin/assign/<int:student_id>', methods=['GET', 'POST'])
@login_required
def assign_work(student_id):
    """Admin page: assign packages to a student."""
    if not verify_admin():
        flash("Admin access required", "danger")
        return redirect(url_for("lms.login"))
    
    student = MUser.query.get_or_404(student_id)
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'assign':
            package_id = int(request.form.get('package_id'))
            
            # Check if already assigned
            existing = MUserPackage.query.filter_by(
                muser_id=student.id,
                package_id=package_id
            ).first()
            
            if existing:
                return jsonify({'ok': False, 'error': 'Already assigned'}), 400
            
            assignment = MUserPackage(
                muser_id=student.id,
                package_id=package_id,
                assigned_date=datetime.now()
            )
            db.session.add(assignment)
            db.session.commit()
            return jsonify({'ok': True, 'message': 'Assigned successfully'})
        
        elif action == 'remove':
            assignment_id = int(request.form.get('assignment_id'))
            assignment = MUserPackage.query.get(assignment_id)
            
            if assignment and assignment.muser_id == student.id:
                db.session.delete(assignment)
                db.session.commit()
                return jsonify({'ok': True, 'message': 'Removed successfully'})
            
            return jsonify({'ok': False, 'error': 'Assignment not found'}), 404
    
    # Get assigned packages
    assigned = db.session.query(
        MUserPackage.id,
        MontessoriPackage.id,
        MontessoriPackage.subject,
        MontessoriPackage.topic,
        MontessoriPackage.work,
        MUserPackage.assigned_date
    ).join(
        MontessoriPackage,
        MUserPackage.package_id == MontessoriPackage.id
    ).filter(
        MUserPackage.muser_id == student.id
    ).order_by(MUserPackage.assigned_date.desc()).all()
    
    # Get available packages (not assigned and not deleted)
    assigned_ids = [pkg[1] for pkg in assigned]
    available = MontessoriPackage.query.filter(
        MontessoriPackage.is_deleted == False,
        ~MontessoriPackage.id.in_(assigned_ids) if assigned_ids else True
    ).order_by(MontessoriPackage.subject, MontessoriPackage.topic).all()
    
    return render_template(
        'montessori_assign_work.html',
        student=student,
        assigned=assigned,
        available=available
    )


@mm_bp.route('/montessori_admin/assign/<int:student_id>/assigned-items', methods=['GET'])
@login_required
def get_assigned_items(student_id):
    """Get assigned items as JSON for AJAX refresh."""
    if not verify_admin():
        return jsonify({'ok': False, 'error': 'Unauthorized'}), 403
    
    student = MUser.query.get_or_404(student_id)
    
    # Get assigned packages
    assigned = db.session.query(
        MUserPackage.id,
        MontessoriPackage.id,
        MontessoriPackage.subject,
        MontessoriPackage.topic,
        MontessoriPackage.work,
        MUserPackage.assigned_date
    ).join(
        MontessoriPackage,
        MUserPackage.package_id == MontessoriPackage.id
    ).filter(
        MUserPackage.muser_id == student.id
    ).order_by(MUserPackage.assigned_date.desc()).all()
    
    items = []
    for assignment_id, pkg_id, subject, topic, work, assigned_date in assigned:
        items.append({
            'assignment_id': assignment_id,
            'package_id': pkg_id,
            'subject': subject,
            'topic': topic,
            'work': work,
            'assigned_date': assigned_date.isoformat() if assigned_date else ''
        })
    
    return jsonify({'ok': True, 'items': items, 'count': len(items)})


# ==================== ADMIN: MANAGE PACKAGES ==================== #

@mm_bp.route('/montessori_admin/packages', methods=['GET', 'POST'])
@login_required
def admin_packages():
    """Admin page: manage Montessori packages."""
    if not verify_admin():
        flash("Admin access required", "danger")
        return redirect(url_for("lms.login"))
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add_package':
            subject = request.form.get('subject', '').strip()
            topic = request.form.get('topic', '').strip()
            work = request.form.get('work', '').strip()
            link = request.form.get('link', '').strip()
            
            if not subject or not topic or not work or not link:
                flash("Subject, topic, work, and link are required", "danger")
            else:
                new_package = MontessoriPackage(
                    subject=subject,
                    topic=topic,
                    work=work,
                    link=link
                )
                db.session.add(new_package)
                db.session.commit()
                flash(f"Package '{subject} - {topic} - {work}' added", "success")
        
        elif action == 'delete_package':
            package_id = request.form.get('package_id')
            package = MontessoriPackage.query.get(package_id)
            if package:
                package.is_deleted = True
                db.session.commit()
                flash(f"Package '{package.subject} - {package.topic}' deleted", "success")
        
        elif action == 'assign_package':
            student_id = request.form.get('student_id')
            package_id = request.form.get('package_id')
            
            # Check if already assigned
            existing = MUserPackage.query.filter_by(
                muser_id=student_id,
                package_id=package_id
            ).first()
            
            if existing:
                flash("Package already assigned to this student", "warning")
            else:
                assignment = MUserPackage(
                    muser_id=student_id,
                    package_id=package_id,
                    assigned_date=datetime.now()
                )
                db.session.add(assignment)
                db.session.commit()
                flash("Package assigned successfully", "success")
        
        elif action == 'remove_assignment':
            assignment_id = request.form.get('assignment_id')
            assignment = MUserPackage.query.get(assignment_id)
            if assignment:
                db.session.delete(assignment)
                db.session.commit()
                flash("Package removed from student", "success")
    
    packages = MontessoriPackage.query.filter_by(is_deleted=False).order_by(
        MontessoriPackage.created_at.desc()
    ).all()
    
    students = MUser.query.order_by(MUser.name).all()
    
    # Get all assignments with tracking data
    assignments = db.session.query(
        MUserPackage.id,
        MUser.name,
        MontessoriPackage.title,
        MUserPackage.assigned_date,
        MUserPackage.click_count,
        MUserPackage.last_accessed
    ).join(
        MUser, MUserPackage.muser_id == MUser.id
    ).join(
        MontessoriPackage, MUserPackage.package_id == MontessoriPackage.id
    ).order_by(
        MUserPackage.assigned_date.desc()
    ).all()
    
    return render_template(
        'montessori_admin_packages.html',
        packages=packages,
        students=students,
        assignments=assignments
    )
