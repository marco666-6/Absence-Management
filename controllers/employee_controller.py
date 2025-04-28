from flask import render_template, redirect, url_for, flash, request, jsonify, send_file
from app import app, db
from models.employee import Employee
from models.attendance import Attendance
from models.leave import Leave
import qrcode
import io
from PIL import Image
import base64
from datetime import datetime, timedelta
import pytz
from config import Config

# Halaman profil karyawan (diakses melalui token QR)
@app.route('/scan/<token>')
def employee_profile(token):
    employee = Employee.query.filter_by(qr_token=token).first()
    
    if not employee:
        return render_template('shared/404.html'), 404
    
    # Generate QR code untuk ditampilkan
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(f"{request.host_url}scan/{employee.qr_token}")
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Konversi ke base64 untuk ditampilkan
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    qr_code = base64.b64encode(buffered.getvalue()).decode("utf-8")
    
    # Ambil data absensi terbaru
    today = datetime.now(pytz.timezone(Config.TIMEZONE)).date()
    attendance_today = Attendance.query.filter_by(employee_id=employee.id, date=today).first()
    
    # Ambil riwayat absensi
    attendance_history = Attendance.query.filter_by(employee_id=employee.id).order_by(Attendance.date.desc()).limit(10).all()
    
    # Ambil izin/cuti aktif
    active_leaves = Leave.query.filter(
        Leave.employee_id == employee.id,
        Leave.start_date <= today,
        Leave.end_date >= today,
        Leave.status == 'approved'
    ).all()
    
    return render_template('employee/profile.html', 
                          employee=employee, 
                          qr_code=qr_code,
                          attendance_today=attendance_today,
                          attendance_history=attendance_history,
                          active_leaves=active_leaves)

# Download QR Code karyawan
@app.route('/download-qr/<token>')
def download_employee_qr(token):
    employee = Employee.query.filter_by(qr_token=token).first()
    
    if not employee:
        return render_template('shared/404.html'), 404
    
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