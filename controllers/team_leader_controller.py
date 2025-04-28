from flask import render_template, redirect, url_for, flash, request, jsonify, send_file
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
import uuid
import io
import qrcode
from datetime import datetime, timedelta, date
import pytz
from PIL import Image
import base64
from app import app, db, role_required
from models.user import User
from models.employee import Employee
from models.attendance import Attendance
from models.leave import Leave
from config import Config

# Dashboard Team Leader
@app.route('/team-leader/dashboard')
@login_required
@role_required(['team_leader'])
def team_leader_dashboard():
    # Statistik untuk dashboard
    total_employees = Employee.query.filter_by(team_leader_id=current_user.id, is_active=True).count()
    today = datetime.now(pytz.timezone(Config.TIMEZONE)).date()
    
    # Absensi hari ini
    present_today = db.session.query(Attendance).join(Employee).filter(
        Employee.team_leader_id == current_user.id,
        Attendance.date == today,
        Attendance.status == 'present'
    ).count()
    
    absent_today = db.session.query(Attendance).join(Employee).filter(
        Employee.team_leader_id == current_user.id,
        Attendance.date == today,
        Attendance.status == 'absent'
    ).count()
    
    late_today = db.session.query(Attendance).join(Employee).filter(
        Employee.team_leader_id == current_user.id,
        Attendance.date == today,
        Attendance.status == 'late'
    ).count()
    
    on_leave_today = db.session.query(Leave).join(Employee).filter(
        Employee.team_leader_id == current_user.id,
        Leave.start_date <= today,
        Leave.end_date >= today,
        Leave.status == 'approved'
    ).count()
    
    # Karyawan yang belum absen hari ini
    employees_not_checked_in = db.session.query(Employee).filter(
        Employee.team_leader_id == current_user.id,
        Employee.is_active == True,
        ~Employee.id.in_(
            db.session.query(Attendance.employee_id).filter(
                Attendance.date == today
            )
        )
    ).all()
    
    # Daftar izin yang perlu disetujui
    pending_leaves = db.session.query(Leave, Employee).join(Employee).filter(
        Employee.team_leader_id == current_user.id,
        Leave.status == 'pending'
    ).all()
    
    return render_template('team_leader/dashboard.html', 
                           total_employees=total_employees,
                           present_today=present_today,
                           absent_today=absent_today,
                           late_today=late_today,
                           on_leave_today=on_leave_today,
                           employees_not_checked_in=employees_not_checked_in,
                           pending_leaves=pending_leaves)

# Manajemen Karyawan (Team Leader)
@app.route('/team-leader/employees')
@login_required
@role_required(['team_leader'])
def team_leader_employees():
    employees = Employee.query.filter_by(team_leader_id=current_user.id).all()
    return render_template('team_leader/employees.html', employees=employees)

@app.route('/team-leader/employees/view/<int:id>')
@login_required
@role_required(['team_leader'])
def view_employee(id):
    employee = Employee.query.get_or_404(id)
    
    # Pastikan team leader hanya bisa melihat karyawannya sendiri
    if employee.team_leader_id != current_user.id:
        flash('Anda tidak memiliki akses ke data karyawan ini', 'danger')
        return redirect(url_for('team_leader_employees'))
    
    # Generate QR code untuk karyawan
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(f"{request.host_url}scan/{employee.qr_token}")
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convert to base64 for display
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    qr_code = base64.b64encode(buffered.getvalue()).decode("utf-8")
    
    # Ambil data absensi terbaru
    recent_attendance = Attendance.query.filter_by(employee_id=id).order_by(Attendance.date.desc()).limit(10).all()
    
    # Ambil data izin terbaru
    recent_leaves = Leave.query.filter_by(employee_id=id).order_by(Leave.start_date.desc()).limit(5).all()
    
    return render_template('team_leader/view_employee.html', 
                          employee=employee, 
                          qr_code=qr_code, 
                          recent_attendance=recent_attendance,
                          recent_leaves=recent_leaves)

# QR Code Scanner
@app.route('/team-leader/scan')
@login_required
@role_required(['team_leader'])
def scan_qr():
    return render_template('team_leader/scan_qr.html')

@app.route('/team-leader/process-scan', methods=['POST'])
@login_required
@role_required(['team_leader'])
def process_scan():
    qr_token = request.json.get('qr_token')
    
    if not qr_token:
        return jsonify({'status': 'error', 'message': 'QR token tidak valid'}), 400
    
    # Cari karyawan berdasarkan token
    employee = Employee.query.filter_by(qr_token=qr_token).first()
    
    if not employee:
        return jsonify({'status': 'error', 'message': 'Karyawan tidak ditemukan'}), 404
    
    # Pastikan karyawan adalah anggota tim leader ini
    if employee.team_leader_id != current_user.id:
        return jsonify({'status': 'error', 'message': 'Karyawan bukan anggota tim Anda'}), 403
    
    # Cek apakah karyawan aktif
    if not employee.is_active:
        return jsonify({'status': 'error', 'message': 'Karyawan tidak aktif'}), 403
    
    # Proses absensi
    today = datetime.now(pytz.timezone(Config.TIMEZONE)).date()
    now = datetime.now(pytz.timezone(Config.TIMEZONE))
    
    # Cek apakah sudah ada absensi hari ini
    attendance = Attendance.query.filter_by(employee_id=employee.id, date=today).first()
    
    # Jam kerja standar (untuk menentukan keterlambatan)
    start_time = datetime.strptime('08:00', '%H:%M').time()
    end_time = datetime.strptime('17:00', '%H:%M').time()
    
    if not attendance:
        # Belum ada absensi, tandai sebagai check-in
        status = 'present'
        
        # Cek keterlambatan
        if now.time() > start_time:
            status = 'late'
            
        attendance = Attendance(
            employee_id=employee.id,
            date=today,
            check_in=now,
            status=status,
            created_by=current_user.id
        )
        
        db.session.add(attendance)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': f'Check-in berhasil untuk {employee.name}',
            'action': 'check_in',
            'employee': {
                'id': employee.id,
                'name': employee.name,
                'nik': employee.nik,
                'position': employee.position,
                'department': employee.department
            },
            'timestamp': now.strftime('%H:%M:%S')
        })
    
    elif attendance and attendance.check_in and not attendance.check_out:
        # Sudah check-in tapi belum check-out
        attendance.check_out = now
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': f'Check-out berhasil untuk {employee.name}',
            'action': 'check_out',
            'employee': {
                'id': employee.id,
                'name': employee.name,
                'nik': employee.nik,
                'position': employee.position,
                'department': employee.department
            },
            'timestamp': now.strftime('%H:%M:%S')
        })
    
    else:
        # Sudah check-in dan check-out
        return jsonify({
            'status': 'error',
            'message': f'{employee.name} sudah melakukan check-in dan check-out hari ini'
        }), 400

# Manajemen Absensi
@app.route('/team-leader/attendance')
@login_required
@role_required(['team_leader'])
def attendance():
    today = datetime.now(pytz.timezone(Config.TIMEZONE)).date()
    employees = Employee.query.filter_by(team_leader_id=current_user.id, is_active=True).all()
    
    # Ambil data absensi hari ini
    attendance_data = []
    for employee in employees:
        att = Attendance.query.filter_by(employee_id=employee.id, date=today).first()
        
        # Cek apakah karyawan sedang izin
        leave = Leave.query.filter(
            Leave.employee_id == employee.id,
            Leave.start_date <= today,
            Leave.end_date >= today,
            Leave.status == 'approved'
        ).first()
        
        attendance_data.append({
            'employee': employee,
            'attendance': att,
            'on_leave': leave
        })
    
    return render_template('team_leader/attendance.html', attendance_data=attendance_data, today=today)

@app.route('/team-leader/attendance/manual-entry', methods=['POST'])
@login_required
@role_required(['team_leader'])
def manual_attendance_entry():
    employee_id = request.form.get('employee_id')
    date_str = request.form.get('date')
    check_in_time = request.form.get('check_in_time')
    check_out_time = request.form.get('check_out_time')
    status = request.form.get('status')
    notes = request.form.get('notes')
    
    # Validasi
    employee = Employee.query.get_or_404(employee_id)
    if employee.team_leader_id != current_user.id:
        flash('Anda tidak memiliki akses ke data karyawan ini', 'danger')
        return redirect(url_for('attendance'))
    
    # Parse tanggal dan waktu
    date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
    
    # Cek apakah sudah ada absensi untuk tanggal tersebut
    attendance = Attendance.query.filter_by(employee_id=employee_id, date=date_obj).first()
    
    if attendance:
        # Update absensi yang ada
        if check_in_time:
            check_in_datetime = datetime.strptime(f"{date_str} {check_in_time}", '%Y-%m-%d %H:%M')
            attendance.check_in = check_in_datetime
        
        if check_out_time:
            check_out_datetime = datetime.strptime(f"{date_str} {check_out_time}", '%Y-%m-%d %H:%M')
            attendance.check_out = check_out_datetime
        
        attendance.status = status
        attendance.notes = notes
        
    else:
        # Buat absensi baru
        check_in_datetime = None
        if check_in_time:
            check_in_datetime = datetime.strptime(f"{date_str} {check_in_time}", '%Y-%m-%d %H:%M')
        
        check_out_datetime = None
        if check_out_time:
            check_out_datetime = datetime.strptime(f"{date_str} {check_out_time}", '%Y-%m-%d %H:%M')
        
        attendance = Attendance(
            employee_id=employee_id,
            date=date_obj,
            check_in=check_in_datetime,
            check_out=check_out_datetime,
            status=status,
            notes=notes,
            created_by=current_user.id
        )
        
        db.session.add(attendance)
    
    db.session.commit()
    flash('Data absensi berhasil diperbarui', 'success')
    
    return redirect(url_for('attendance'))

# Manajemen Izin/Cuti
@app.route('/team-leader/leaves')
@login_required
@role_required(['team_leader'])
def leaves():
    # Ambil data izin karyawan
    leaves_data = db.session.query(Leave, Employee).join(Employee).filter(
        Employee.team_leader_id == current_user.id
    ).order_by(Leave.created_at.desc()).all()
    
    return render_template('team_leader/leaves.html', leaves_data=leaves_data)

@app.route('/team-leader/leaves/add', methods=['GET', 'POST'])
@login_required
@role_required(['team_leader'])
def add_leave():
    employees = Employee.query.filter_by(team_leader_id=current_user.id, is_active=True).all()
    
    if request.method == 'POST':
        employee_id = request.form.get('employee_id')
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        leave_type = request.form.get('leave_type')
        reason = request.form.get('reason')
        
        # Validasi
        employee = Employee.query.get_or_404(employee_id)
        if employee.team_leader_id != current_user.id:
            flash('Anda tidak memiliki akses ke data karyawan ini', 'danger')
            return redirect(url_for('leaves'))
        
        # Parse tanggal
        start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        # Validasi tanggal
        if end_date_obj < start_date_obj:
            flash('Tanggal akhir tidak boleh sebelum tanggal mulai', 'danger')
            return redirect(url_for('add_leave'))
        
        # Proses upload attachment jika ada
        attachment = None
        if 'attachment' in request.files:
            file = request.files['attachment']
            if file and file.filename:
                filename = secure_filename(file.filename)
                unique_filename = f"{uuid.uuid4()}_{filename}"
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                file.save(file_path)
                attachment = unique_filename
        
        # Buat cuti baru
        new_leave = Leave(
            employee_id=employee_id,
            start_date=start_date_obj,
            end_date=end_date_obj,
            leave_type=leave_type,
            reason=reason,
            attachment=attachment,
            status='approved',  # Otomatis approve karena diinput oleh team leader
            approved_by=current_user.id
        )
        
        db.session.add(new_leave)
        db.session.commit()
        
        flash('Data izin berhasil ditambahkan', 'success')
        return redirect(url_for('leaves'))
    
    return render_template('team_leader/add_leave.html', employees=employees)

@app.route('/team-leader/leaves/approve/<int:id>', methods=['POST'])
@login_required
@role_required(['team_leader'])
def approve_leave(id):
    leave = Leave.query.get_or_404(id)
    
    # Validasi
    employee = Employee.query.get(leave.employee_id)
    if employee.team_leader_id != current_user.id:
        flash('Anda tidak memiliki akses ke data karyawan ini', 'danger')
        return redirect(url_for('leaves'))
    
    leave.status = 'approved'
    leave.approved_by = current_user.id
    db.session.commit()
    
    flash('Izin berhasil disetujui', 'success')
    return redirect(url_for('leaves'))

@app.route('/team-leader/leaves/reject/<int:id>', methods=['POST'])
@login_required
@role_required(['team_leader'])
def reject_leave(id):
    leave = Leave.query.get_or_404(id)
    
    # Validasi
    employee = Employee.query.get(leave.employee_id)
    if employee.team_leader_id != current_user.id:
        flash('Anda tidak memiliki akses ke data karyawan ini', 'danger')
        return redirect(url_for('leaves'))
    
    leave.status = 'rejected'
    leave.approved_by = current_user.id
    db.session.commit()
    
    flash('Izin berhasil ditolak', 'success')
    return redirect(url_for('leaves'))

# Laporan (Team Leader)
@app.route('/team-leader/reports')
@login_required
@role_required(['team_leader'])
def team_leader_reports():
    return render_template('team_leader/reports.html')

@app.route('/team-leader/reports/attendance', methods=['GET', 'POST'])
@login_required
@role_required(['team_leader'])
def team_leader_attendance_report():
    if request.method == 'POST':
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        employee_id = request.form.get('employee_id')
        
        # Konversi string tanggal ke objek date
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date() if start_date else None
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date() if end_date else None
        
        # Query absensi berdasarkan filter
        query = db.session.query(
            Attendance, Employee
        ).join(
            Employee, Attendance.employee_id == Employee.id
        ).filter(
            Employee.team_leader_id == current_user.id,
            Attendance.date >= start_date,
            Attendance.date <= end_date
        )
        
        if employee_id:
            query = query.filter(Employee.id == employee_id)
        
        attendance_data = query.all()
        
        employees = Employee.query.filter_by(team_leader_id=current_user.id).all()
        
        return render_template(
            'team_leader/attendance_report.html',
            attendance_data=attendance_data,
            employees=employees,
            start_date=start_date,
            end_date=end_date
        )
    
    employees = Employee.query.filter_by(team_leader_id=current_user.id).all()
    
    # Default to current month
    today = datetime.now()
    start_date = datetime(today.year, today.month, 1).date()
    end_date = today.date()
    
    return render_template(
        'team_leader/attendance_report.html',
        employees=employees,
        start_date=start_date,
        end_date=end_date
    )

@app.route('/team-leader/reports/leave', methods=['GET', 'POST'])
@login_required
@role_required(['team_leader'])
def team_leader_leave_report():
    if request.method == 'POST':
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        employee_id = request.form.get('employee_id')
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
            Employee.team_leader_id == current_user.id,
            (Leave.start_date >= start_date) | (Leave.end_date >= start_date),
            (Leave.start_date <= end_date) | (Leave.end_date <= end_date)
        )
        
        if employee_id:
            query = query.filter(Employee.id == employee_id)
        
        if leave_type:
            query = query.filter(Leave.leave_type == leave_type)
        
        if status:
            query = query.filter(Leave.status == status)
        
        leave_data = query.all()
        
        employees = Employee.query.filter_by(team_leader_id=current_user.id).all()
        
        return render_template(
            'team_leader/leave_report.html',
            leave_data=leave_data,
            employees=employees,
            leave_types=['sakit', 'cuti', 'izin'],
            statuses=['pending', 'approved', 'rejected'],
            start_date=start_date,
            end_date=end_date
        )
    
    employees = Employee.query.filter_by(team_leader_id=current_user.id).all()
    
    # Default to current month
    today = datetime.now()
    start_date = datetime(today.year, today.month, 1).date()
    end_date = today.date()
    
    return render_template(
        'team_leader/leave_report.html',
        employees=employees,
        leave_types=['sakit', 'cuti', 'izin'],
        statuses=['pending', 'approved', 'rejected'],
        start_date=start_date,
        end_date=end_date
    )

# Download QR Code
@app.route('/team-leader/download-qr/<int:id>')
@login_required
@role_required(['team_leader'])
def download_qr(id):
    employee = Employee.query.get_or_404(id)
    
    # Pastikan team leader hanya bisa mengakses karyawannya
    if employee.team_leader_id != current_user.id:
        flash('Anda tidak memiliki akses ke data karyawan ini', 'danger')
        return redirect(url_for('team_leader_employees'))
    
    # Generate QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(f"{request.host_url}scan/{employee.qr_token}")
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Simpan ke buffer
    img_io = io.BytesIO()
    img.save(img_io, 'PNG')
    img_io.seek(0)
    
    return send_file(
        img_io,
        mimetype='image/png',
        as_attachment=True,
        download_name=f"QR_Code_{employee.name}.png"
    )