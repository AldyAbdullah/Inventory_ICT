from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required
from main import app, admin_required
from models import db, Karyawan
import openpyxl

@app.route('/karyawan', methods=['GET', 'POST'])
@login_required
@admin_required
def master_karyawan():
    if request.method == 'POST':
        # Logika Tambah Manual
        payroll = request.form.get('payroll').strip()
        nama = request.form.get('nama').strip()
        status = request.form.get('status').strip()
        
        if Karyawan.query.filter_by(payroll=payroll).first():
            flash(f'Gagal: Karyawan dengan Payroll {payroll} sudah terdaftar!', 'danger')
        else:
            db.session.add(Karyawan(payroll=payroll, nama=nama, status=status))
            db.session.commit()
            flash('Data Karyawan berhasil ditambahkan.', 'success')
        return redirect(url_for('master_karyawan'))
        
    # Logika GET (Tampilkan Tabel & Pencarian)
    search = request.args.get('search', '')
    query = Karyawan.query
    if search:
        query = query.filter(db.or_(Karyawan.nama.ilike(f"%{search}%"), Karyawan.payroll.ilike(f"%{search}%")))
        
    data_karyawan = query.order_by(Karyawan.nama.asc()).all()
    return render_template('karyawan/master.html', data=data_karyawan, search_query=search)

@app.route('/import_karyawan', methods=['POST'])
@login_required
@admin_required
def import_karyawan():
    file = request.files.get('file_excel')
    if not file or file.filename == '':
        flash('Gagal: Tidak ada file Excel yang dipilih.', 'danger')
        return redirect(url_for('master_karyawan'))
        
    if file and file.filename.endswith(('.xlsx', '.xls')):
        try:
            wb = openpyxl.load_workbook(file)
            ws = wb.active
            
            jumlah_sukses = 0
            jumlah_skip = 0
            
            # Membaca mulai dari baris ke-2 (Baris 1 diasumsikan sebagai Header)
            for row in ws.iter_rows(min_row=2, values_only=True):
                # Validasi jika baris kosong
                if not row[0] or not row[1]: 
                    continue
                    
                payroll = str(row[0]).strip()
                nama = str(row[1]).strip()
                # Jika kolom status kosong di excel, default 'Aktif'
                status = str(row[2]).strip() if len(row) > 2 and row[2] else 'Aktif'
                
                if Karyawan.query.filter_by(payroll=payroll).first():
                    jumlah_skip += 1
                else:
                    db.session.add(Karyawan(payroll=payroll, nama=nama, status=status))
                    jumlah_sukses += 1
                    
            db.session.commit()
            flash(f'Import Selesai! {jumlah_sukses} data ditambahkan. {jumlah_skip} data dilewati (duplikat).', 'success')
        except Exception as e:
            flash(f'Terjadi kesalahan sistem saat membaca file: {str(e)}', 'danger')
    else:
        flash('Gagal: Format file harus Excel (.xlsx)', 'danger')
        
    return redirect(url_for('master_karyawan'))