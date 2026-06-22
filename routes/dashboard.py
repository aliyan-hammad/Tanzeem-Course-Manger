from datetime import datetime, date
from flask import Blueprint, render_template, request
from flask_login import login_required, current_user
from extensions import db
from models import User, Course, Student, FeeCollection, Expense, AuditLog, ApprovalRequest

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@login_required
def index():
    selected_course_id = request.args.get('course_id')
    current_year = date.today().year
    current_month = date.today().month
    today_date = date.today()
    
    if current_user.role == 'Coordinator':
        assigned_courses = Course.query.filter_by(coordinator_id=current_user.id).all()
        assigned_course_ids = [c.id for c in assigned_courses]
        
        if not assigned_course_ids:
            return render_template('dashboard.html', 
                                   total_active_students=0, hand_cash=0.0, in_account=0.0,
                                   total_fees=0.0, total_expenses=0.0, net_balance=0.0,
                                   latest_fees=[], latest_expenses=[], courses=[],
                                   today_collections=0.0, monthly_collections=0.0,
                                   expenses_added=0.0, pending_requests_count=0)
            
        total_active_students = Student.query.filter(Student.course_id.in_(assigned_course_ids), Student.status=='Active').count()
        
        hand_cash = db.session.query(db.func.sum(FeeCollection.amount_paid)).join(Student).filter(
            Student.course_id.in_(assigned_course_ids), FeeCollection.payment_method=='Cash', FeeCollection.is_deleted==False
        ).scalar() or 0.0
        
        in_account = db.session.query(db.func.sum(FeeCollection.amount_paid)).join(Student).filter(
            Student.course_id.in_(assigned_course_ids), FeeCollection.payment_method=='Online', FeeCollection.is_deleted==False
        ).scalar() or 0.0
        
        total_fees = hand_cash + in_account
        
        total_expenses = db.session.query(db.func.sum(Expense.amount)).filter(
            Expense.course_id.in_(assigned_course_ids), Expense.is_deleted==False
        ).scalar() or 0.0
        
        net_balance = total_fees - total_expenses
        
        latest_fees = FeeCollection.query.join(Student).filter(
            Student.course_id.in_(assigned_course_ids), FeeCollection.is_deleted==False
        ).order_by(FeeCollection.date_collected.desc()).limit(5).all()
        
        latest_expenses = Expense.query.filter(
            Expense.course_id.in_(assigned_course_ids), Expense.is_deleted==False
        ).order_by(Expense.expense_date.desc()).limit(5).all()

        # Coordinator specific metrics:
        coord_fees = FeeCollection.query.join(Student).filter(
            Student.course_id.in_(assigned_course_ids), FeeCollection.is_deleted==False
        ).all()
        today_collections = sum([f.amount_paid for f in coord_fees if f.date_collected.date() == today_date])
        monthly_collections = sum([f.amount_paid for f in coord_fees if f.date_collected.year == current_year and f.date_collected.month == current_month])
        
        coord_expenses = Expense.query.filter(
            Expense.course_id.in_(assigned_course_ids), Expense.is_deleted==False
        ).all()
        expenses_added = sum([e.amount for e in coord_expenses])

        pending_requests_count = ApprovalRequest.query.filter_by(
            requested_by_id=current_user.id, status='Pending'
        ).count()
        
        return render_template('dashboard.html', 
                               total_active_students=total_active_students,
                               hand_cash=hand_cash,
                               in_account=in_account,
                               total_fees=total_fees,
                               total_expenses=total_expenses,
                               net_balance=net_balance,
                               latest_fees=latest_fees,
                               latest_expenses=latest_expenses,
                               courses=assigned_courses,
                               selected_course_id=None,
                               today_collections=today_collections,
                               monthly_collections=monthly_collections,
                               expenses_added=expenses_added,
                               pending_requests_count=pending_requests_count)
                               
    else:  # Admin Role
        all_courses = Course.query.filter_by(status='Active').all()
        
        if selected_course_id and selected_course_id.isdigit():
            c_id = int(selected_course_id)
            total_active_students = Student.query.filter_by(course_id=c_id, status='Active').count()
            
            hand_cash = db.session.query(db.func.sum(FeeCollection.amount_paid)).join(Student).filter(
                Student.course_id==c_id, FeeCollection.payment_method=='Cash', FeeCollection.is_deleted==False
            ).scalar() or 0.0
            
            in_account = db.session.query(db.func.sum(FeeCollection.amount_paid)).join(Student).filter(
                Student.course_id==c_id, FeeCollection.payment_method=='Online', FeeCollection.is_deleted==False
            ).scalar() or 0.0
            
            total_fees = hand_cash + in_account
            
            total_expenses = db.session.query(db.func.sum(Expense.amount)).filter_by(course_id=c_id, is_deleted=False).scalar() or 0.0
            net_balance = total_fees - total_expenses
            
            latest_fees = FeeCollection.query.join(Student).filter(
                Student.course_id==c_id, FeeCollection.is_deleted==False
            ).order_by(FeeCollection.date_collected.desc()).limit(5).all()
            
            latest_expenses = Expense.query.filter_by(course_id=c_id, is_deleted=False).order_by(Expense.expense_date.desc()).limit(5).all()
        else:
            total_active_students = Student.query.filter_by(status='Active').count()
            hand_cash = db.session.query(db.func.sum(FeeCollection.amount_paid)).filter_by(payment_method='Cash', is_deleted=False).scalar() or 0.0
            in_account = db.session.query(db.func.sum(FeeCollection.amount_paid)).filter_by(payment_method='Online', is_deleted=False).scalar() or 0.0
            total_fees = hand_cash + in_account
            total_expenses = db.session.query(db.func.sum(Expense.amount)).filter_by(is_deleted=False).scalar() or 0.0
            net_balance = total_fees - total_expenses
            
            latest_fees = FeeCollection.query.filter_by(is_deleted=False).order_by(FeeCollection.date_collected.desc()).limit(5).all()
            latest_expenses = Expense.query.filter_by(is_deleted=False).order_by(Expense.expense_date.desc()).limit(5).all()
            
        # Admin specific metrics:
        pending_edit_requests = ApprovalRequest.query.filter_by(request_type='Edit', status='Pending').count()
        pending_delete_requests = ApprovalRequest.query.filter_by(request_type='Delete', status='Pending').count()
        recent_activities = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(10).all()
        
        # Monthly charts data (For current calendar year)
        months_list = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        monthly_collections = [0.0] * 12
        monthly_expenses = [0.0] * 12
        
        if selected_course_id and selected_course_id.isdigit():
            c_id = int(selected_course_id)
            fees_year = FeeCollection.query.join(Student).filter(Student.course_id==c_id, FeeCollection.is_deleted==False).all()
            exps_year = Expense.query.filter_by(course_id=c_id, is_deleted=False).all()
        else:
            fees_year = FeeCollection.query.filter_by(is_deleted=False).all()
            exps_year = Expense.query.filter_by(is_deleted=False).all()
            
        for f in fees_year:
            if f.date_collected and f.date_collected.year == current_year:
                monthly_collections[f.date_collected.month - 1] += f.amount_paid
                
        for e in exps_year:
            if e.expense_date and e.expense_date.year == current_year:
                monthly_expenses[e.expense_date.month - 1] += e.amount
                
        return render_template('dashboard.html', 
                               total_active_students=total_active_students,
                               hand_cash=hand_cash,
                               in_account=in_account,
                               total_fees=total_fees,
                               total_expenses=total_expenses,
                               net_balance=net_balance,
                               latest_fees=latest_fees,
                               latest_expenses=latest_expenses,
                               courses=all_courses,
                               selected_course_id=selected_course_id,
                               pending_edit_requests=pending_edit_requests,
                               pending_delete_requests=pending_delete_requests,
                               recent_activities=recent_activities,
                               months_list=months_list,
                               monthly_collections=monthly_collections,
                               monthly_expenses=monthly_expenses)
