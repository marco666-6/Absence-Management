from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename
import os
import uuid
from datetime import datetime, timedelta
import pytz
from app import app, db, role_required
from models.user import User
from models.employee import Employee
from models.attendance import Attendance
from models.leave import Leave
from config import Config

# Dashboard Admin
@app.route('/admin/dashboard')
@login_required
@role_required(['admin'])
def admin_dashboard():
    # Statistik untuk dashboard
    total_employees = Employee.query.filter_by(is_active=True).count()
    total_team_leaders = User.query.filter_by(role='team_leader', is_active=True).count()
    today = datetime.now(pytz.timezone(Config.TIMEZONE)).date()
    present_today = Attendance.query.filter(Attendance.date == today, Attendance.status == 'present').count()
    absent_today = Attendance.query.filter(Attendance.date == today, Attendance.status == 'absent').count()
    late_today = Attendance.query.filter(Attendance.date == today, Attendance.status == 'late').count()
    on_leave_today = Leave.query.filter(Leave.start_date <= today, Leave.end_date >= today, Leave.status == 'approved').count()
    
    return render_template('admin/dashboard.html', 
                           total_employees=total_employees,
                           total_team_leaders=total_team_leaders,
                           present_today=present_today,
                           absent_today=absent_today,
                           late_today=late_today,
                           on_leave_today=on_leave_today)

# Manajemen Team Leader
@app.route('/admin/team-leaders')
@login_required
@role_required(['admin'])
def team_leaders():
    team_leaders = User.query.filter_by(role='team_leader').all()
    return render_template('admin/team_leaders.html', team_leaders=team_leaders)

@app.route('/admin/team-leaders/add', methods=['GET', 'POST'])
@login_required
@role_required(['admin'])
def add_team_leader():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        name = request.form.get('name')
        password = request.form.get('password')
        
        # Validasi data
        existing_user = User.query.filter((User.username == username) | (User.email == email)).first()
        if existing_user:
            flash('Username atau email sudah digunakan', 'danger')
            return redirect(url_for('add_team_leader'))
        
        # Buat user baru
        new_team_leader = User(
            username=username,
            email=email,
            name=name,
            password=generate_password_hash(password),
            role='team_leader',
            is_active=True
        )
        
        db.session.add(new_team_leader)
        db.session.commit()
        
        flash('Team leader berhasil ditambahkan', 'success')
        return redirect(url_for('team_leaders'))
    
    return render_template('admin/add_team_leader.html')

@app.route('/admin/team-leaders/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@role_required(['admin'])
def edit_team_leader(id):
    team_leader = User.query.get_or_404(id)
    
    if request.method == 'POST':
        email = request.form.get('email')
        name = request.form.get('name')
        is_active = 'is_active' in request.form
        
        # Validasi email jika berubah
        if email != team_leader.email:
            existing_email = User.query.filter_by(email=email).first()
            if existing_email:
                flash('Email sudah digunakan', 'danger')
                return redirect(url_for('edit_team_leader', id=id))
        
        # Update data
        team_leader.email = email
        team_leader.name = name
        team_leader.is_active = is_active
        
        # Update password jika diisi
        new_password = request.form.get('password')
        if new_password:
            team_leader.password = generate_password_hash(new_password)
        
        db.session.commit()
        flash('Data team leader berhasil diperbarui', 'success')
        return redirect(url_for('team_leaders'))
    
    return render_template('admin/edit_team_leader.html', team_leader=team_leader)

@app.route('/admin/team-leaders/delete/<int:id>', methods=['POST'])
@login_required
@role_required(['admin'])
def delete_team_leader(id):
    team_leader = User.query.get_or_404(id)
    
    # Cek apakah masih ada karyawan di bawah team leader ini
    employees = Employee.query.filter_by(team_leader_id=id).all()
    if employees:
        flash('Tidak dapat menghapus team leader yang masih memiliki karyawan', 'danger')
        return redirect(url_for('team_leaders'))
    
    db.session.delete(team_leader)
    db.session.commit()
    
    flash('Team leader berhasil dihapus', 'success')
    return redirect(url_for('team_leaders'))

# Manajemen Karyawan
@app.route('/admin/employees')
@login_required
@role_required(['admin'])
def employees():
    employees = Employee.query.all()
    return render_template('admin/employees.html', employees=employees)

@app.route('/admin/employees/add', methods=['GET', 'POST'])
@login_required
@role_required(['admin'])
def add_employee():
    team_leaders = User.query.filter_by(role='team_leader', is_active=True).all()
    
    if request.method == 'POST':
        nik = request.form.get('nik')
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        position = request.form.get('position')
        department = request.form.get('department')
        team_leader_id = request.form.get('team_leader_id')
        
        # Validasi data
        existing_employee = Employee.query.filter((Employee.nik == nik) | (Employee.email == email)).first()
        if existing_employee:
            flash('NIK atau email sudah digunakan', 'danger')
            return redirect(url_for('add_employee'))
        
        # Proses upload foto profil
        profile_pic = None
        if 'profile_pic' in request.files:
            file = request.files['profile_pic']
            if file and file.filename:
                filename = secure_filename(file.filename)
                unique_filename = f"{uuid.uuid4()}_{filename}"
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                file.save(file_path)
                profile_pic = unique_filename
        
        # Buat karyawan baru
        new_employee = Employee(
            nik=nik,
            name=name,
            email=email,
            phone=phone,
            position=position,
            department=department,
            team_leader_id=team_leader_id,
            profile_pic=profile_pic,
            is_active=True
        )
        
        db.session.add(new_employee)
        db.session.commit()
        
        flash('Karyawan berhasil ditambahkan', 'success')
        return redirect(url_for('employees'))
    
    return render_template('admin/add_employee.html', team_leaders=team_leaders)

@app.route('/admin/employees/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@role_required(['admin'])
def edit_employee(id):
    employee = Employee.query.get_or_404(id)
    team_leaders = User.query.filter_by(role='team_leader', is_active=True).all()
    
    if request.method == 'POST':
        nik = request.form.get('nik')
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        position = request.form.get('position')
        department = request.form.get('department')
        team_leader_id = request.form.get('team_leader_id')
        is_active = 'is_active' in request.form
        
        # Validasi NIK dan email jika berubah
        if nik != employee.nik:
            existing_nik = Employee.query.filter_by(nik=nik).first()
            if existing_nik:
                flash('NIK sudah digunakan', 'danger')
                return redirect(url_for('edit_employee', id=id))
        
        if email != employee.email:
            existing_email = Employee.query.filter_by(email=email).first()
            if existing_email:
                flash('Email sudah digunakan', 'danger')
                return redirect(url_for('edit_employee', id=id))
        
        # Proses upload foto profil baru
        if 'profile_pic' in request.files:
            file = request.files['profile_pic']
            if file and file.filename:
                filename = secure_filename(file.filename)
                unique_filename = f"{uuid.uuid4()}_{filename}"
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                file.save(file_path)
                
                # Hapus foto lama jika ada
                if employee.profile_pic:
                    old_file_path = os.path.join(app.config['UPLOAD_FOLDER'], employee.profile_pic)
                    if os.path.exists(old_file_path):
                        os.remove(old_file_path)
                
                employee.profile_pic = unique_filename
        
        # Update data
        employee.nik = nik
        employee.name = name
        employee.email = email
        employee.phone = phone
        employee.position = position
        employee.department = department
        employee.team_leader_id = team_leader_id
        employee.is_active = is_active
        
        db.session.commit()
        flash('Data karyawan berhasil diperbarui', 'success')
        return redirect(url_for('employees'))
    
    return render_template('admin/edit_employee.html', employee=employee, team_leaders=team_leaders)

@app.route('/admin/employees/delete/<int:id>', methods=['POST'])
@login_required
@role_required(['admin'])
def delete_employee(id):
    employee = Employee.query.get_or_404(id)
    
    # Hapus foto profil jika ada
    if employee.profile_pic:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], employee.profile_pic)
        if os.path.exists(file_path):
            os.remove(file_path)
    
    db.session.delete(employee)
    db.session.commit()
    
    flash('Karyawan berhasil dihapus', 'success')
    return redirect(url_for('employees'))

# Laporan Absensi
@app.route('/admin/reports')
@login_required
@role_required(['admin'])
def reports():
    return render_template('admin/reports.html')

@app.route('/admin/reports/attendance', methods=['GET', 'POST'])
@login_required
@role_required(['admin'])
def attendance_report():
    if request.method == 'POST':
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        team_leader_id = request.form.get('team_leader_id')
        department = request.form.get('department')
        
        # Konversi string tanggal ke objek date
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date() if start_date else None
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date() if end_date else None
        
        # Query absensi berdasarkan filter
        query = db.session.query(
            Attendance, Employee
        ).join(
            Employee, Attendance.employee_id == Employee.id
        ).filter(
            Attendance.date >= start_date,
            Attendance.date <= end_date
        )
        
        if team_leader_id:
            query = query.filter(Employee.team_leader_id == team_leader_id)
        
        if department:
            query = query.filter(Employee.department == department)
        
        attendance_data = query.all()
        
        team_leaders = User.query.filter_by(role='team_leader').all()
        departments = db.session.query(Employee.department).distinct().all()
        
        return render_template(
            'admin/attendance_report.html',
            attendance_data=attendance_data,
            team_leaders=team_leaders,
            departments=departments,
            start_date=start_date,
            end_date=end_date
        )
    
    team_leaders = User.query.filter_by(role='team_leader').all()
    departments = db.session.query(Employee.department).distinct().all()
    
    # Default to current month
    today = datetime.now()
    start_date = datetime(today.year, today.month, 1).date()
    end_date = today.date()
    
    return render_template(
        'admin/attendance_report.html',
        team_leaders=team_leaders,
        departments=departments,
        start_date=start_date,
        end_date=end_date
    )

@app.route('/admin/reports/leave', methods=['GET', 'POST'])
@login_required
@role_required(['admin'])
def leave_report():
    if request.method == 'POST':
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        team_leader_id = request.form.get('team_leader_id')
        department = request.form.get('department')
        leave_type = request.form.get('leave_type')
        status = request.form.get('status')
        
        # Konversi string tanggal ke objek date
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date() if start_date else None
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date() if end_date else None
        
        # Query cuti berdasarkan filter
        query = db.session.query(
            Leave, Employee
        ).join(
            Employee, Leave.employee_id == Employee.id
        ).filter(
            (Leave.start_date >= start_date) | (Leave.end_date >= start_date),
            (Leave.start_date <= end_date) | (Leave.end_date <= end_date)
        )
        
        if team_leader_id:
            query = query.filter(Employee.team_leader_id == team_leader_id)
        
        if department:
            query = query.filter(Employee.department == department)
        
        if leave_type:
            query = query.filter(Leave.leave_type == leave_type)
        
        if status:
            query = query.filter(Leave.status == status)
        
        leave_data = query.all()
        
        team_leaders = User.query.filter_by(role='team_leader').all()
        departments = db.session.query(Employee.department).distinct().all()
        
        return render_template(
            'admin/leave_report.html',
            leave_data=leave_data,
            team_leaders=team_leaders,
            departments=departments,
            leave_types=['sakit', 'cuti', 'izin'],
            statuses=['pending', 'approved', 'rejected'],
            start_date=start_date,
            end_date=end_date
        )
    
    team_leaders = User.query.filter_by(role='team_leader').all()
    departments = db.session.query(Employee.department).distinct().all()
    
    # Default to current month
    today = datetime.now()
    start_date = datetime(today.year, today.month, 1).date()
    end_date = today.date()
    
    return render_template(
        'admin/leave_report.html',
        team_leaders=team_leaders,
        departments=departments,
        leave_types=['sakit', 'cuti', 'izin'],
        statuses=['pending', 'approved', 'rejected'],
        start_date=start_date,
        end_date=end_date
    )