from flask import render_template, request, redirect, url_for, flash, send_file
from flask_login import login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from sqlalchemy import func
import calendar
import qrcode
import io
import base64
from sqlalchemy import or_

from main import app, admin_required
from models import db, User, Lokasi, Inventory, Consumable, Transaksi
from export_utils import generate_excel_report

# ---------------------------------------------------------
# 1. RUTE AUTENTIKASI & PENGGUNA
# ---------------------------------------------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        # Mengubah query pencarian menggunakan payroll
        user = User.query.filter_by(payroll=request.form['payroll']).first()
        if user and check_password_hash(user.password, request.form['password']):
            login_user(user, remember=bool(request.form.get('remember')))
            return redirect(request.args.get('next') or url_for('index'))
        # Flash message disesuaikan bahasanya
        flash('No. Payroll atau password salah.', 'error')
    return render_template('auth/login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/profil', methods=['GET', 'POST'])
@login_required
def profil():
    if request.method == 'POST':
        nama_depan = request.form.get('nama_depan', '').strip()
        nama_belakang = request.form.get('nama_belakang', '').strip()
        jabatan = request.form.get('jabatan', '').strip()
        password_baru = request.form.get('password_baru')

        if nama_belakang:
            nama_lengkap = f"{nama_depan} {nama_belakang}"
        else:
            nama_lengkap = nama_depan

        current_user.nama_lengkap = nama_lengkap
        current_user.jabatan = jabatan
        
        if password_baru:
            from werkzeug.security import generate_password_hash
            current_user.password = generate_password_hash(password_baru)
            
        db.session.commit()
        flash('Profil berhasil diperbarui.', 'success')
        return redirect(url_for('profil'))
        
    return render_template('auth/profil.html')

@app.route('/users')
@login_required
@admin_required
def users():
    return render_template('auth/users.html', users=User.query.all())

@app.route('/tambah_user', methods=['POST'])
@login_required
@admin_required
def tambah_user():
    payroll = request.form.get('payroll')
    nama_lengkap = request.form.get('nama_lengkap')
    jabatan = request.form.get('jabatan')
    password = request.form.get('password')
    role = request.form.get('role')

    if User.query.filter_by(payroll=payroll).first():
        flash('Nomor Payroll sudah terdaftar!', 'danger')
        return redirect(url_for('users'))

    from werkzeug.security import generate_password_hash
    hashed_pw = generate_password_hash(password)
    
    new_user = User(
        payroll=payroll, nama_lengkap=nama_lengkap, 
        jabatan=jabatan, password=hashed_pw, role=role
    )
    db.session.add(new_user)
    db.session.commit()
    flash('Pengguna berhasil ditambahkan.', 'success')
    return redirect(url_for('users'))

@app.route('/edit_user/<int:id>', methods=['POST'])
@login_required
@admin_required
def edit_user(id):
    user = User.query.get_or_404(id)
    user.nama_lengkap = request.form.get('nama_lengkap')
    user.jabatan = request.form.get('jabatan')
    user.role = request.form.get('role')
    
    password_baru = request.form.get('password')
    if password_baru:
        from werkzeug.security import generate_password_hash
        user.password = generate_password_hash(password_baru)
        
    db.session.commit()
    flash('Data pengguna berhasil diperbarui.', 'success')
    return redirect(url_for('users'))

@app.route('/users/hapus/<int:id>')
@login_required
@admin_required
def hapus_user(id):
    if id == current_user.id:
        flash('Tidak dapat menghapus akun yang sedang digunakan.', 'error')
        return redirect(url_for('users'))
    db.session.delete(User.query.get_or_404(id))
    db.session.commit()
    flash('Pengguna berhasil dihapus.', 'success')
    return redirect(url_for('users'))

# ---------------------------------------------------------
# 2. RUTE DASHBOARD
# ---------------------------------------------------------
@app.route('/')
@login_required
def index():
    # 1. Hitung Nilai untuk Kartu Ringkasan
    total_inventory = Inventory.query.filter_by(is_active=True).count()
    total_consumable = Consumable.query.filter_by(is_active=True).count()
    # Menganggap stok kritis adalah jika stok <= 5
    stok_kritis = Consumable.query.filter(Consumable.is_active==True, Consumable.stok <= 5).count()

    # 2. Persiapkan Array untuk Data Grafik
    labels = []
    inv_masuk = []
    inv_keluar = []
    cons_masuk = []
    cons_keluar = []

    sekarang = datetime.now()
    
    # Looping untuk 6 bulan terakhir (dari 5 bulan lalu sampai bulan ini)
    for i in range(5, -1, -1):
        # Hitung kalkulasi bulan dan tahun mundur
        m = sekarang.month - i
        y = sekarang.year
        while m <= 0:
            m += 12
            y -= 1
            
        # Format label bulan (Cth: Sep 2026)
        bulan_nama = datetime(y, m, 1).strftime('%b %Y')
        labels.append(bulan_nama)
        
        # Cari tanggal awal dan akhir untuk bulan tersebut
        start_date = datetime(y, m, 1)
        _, last_day = calendar.monthrange(y, m)
        end_date = datetime(y, m, last_day, 23, 59, 59)
        
        # --- QUERY INVENTORY ---
        # Untuk Inventory, kita menghitung JUMLAH BARIS transaksi (count)
        inv_m = Transaksi.query.filter(
            Transaksi.inventory_id != None,
            Transaksi.jenis == 'Masuk',
            Transaksi.tanggal >= start_date,
            Transaksi.tanggal <= end_date
        ).count()
        
        inv_k = Transaksi.query.filter(
            Transaksi.inventory_id != None,
            Transaksi.jenis.in_(['Keluar', 'Mutasi']),
            Transaksi.tanggal >= start_date,
            Transaksi.tanggal <= end_date
        ).count()
        
        # --- QUERY CONSUMABLE ---
        # Untuk Consumable, kita menjumlahkan TOTAL QTY (sum jumlah), bukan sekadar hitung baris
        cons_m_query = db.session.query(func.sum(Transaksi.jumlah)).filter(
            Transaksi.consumable_id != None,
            Transaksi.jenis == 'Masuk',
            Transaksi.tanggal >= start_date,
            Transaksi.tanggal <= end_date
        ).scalar()
        
        cons_k_query = db.session.query(func.sum(Transaksi.jumlah)).filter(
            Transaksi.consumable_id != None,
            Transaksi.jenis == 'Keluar',
            Transaksi.tanggal >= start_date,
            Transaksi.tanggal <= end_date
        ).scalar()
        
        # Masukkan ke dalam array grafik
        inv_masuk.append(inv_m)
        inv_keluar.append(inv_k)
        cons_masuk.append(int(cons_m_query or 0))
        cons_keluar.append(int(cons_k_query or 0))

    # Kirimkan semua variabel ke template HTML
    return render_template(
        'index.html',
        total_inventory=total_inventory,
        total_consumable=total_consumable,
        stok_kritis=stok_kritis,
        labels=labels,
        inv_masuk=inv_masuk,
        inv_keluar=inv_keluar,
        cons_masuk=cons_masuk,
        cons_keluar=cons_keluar
    )
# ---------------------------------------------------------
# 3. RUTE MASTER LOKASI
# ---------------------------------------------------------
@app.route('/lokasi')
@login_required
@admin_required
def master_lokasi():
    data_lokasi = Lokasi.query.order_by(Lokasi.main_lokasi.asc(), Lokasi.nama_lokasi.asc()).all()
    return render_template('lokasi/master.html', data=data_lokasi)

@app.route('/tambah_lokasi', methods=['GET', 'POST'])
@login_required
@admin_required
def tambah_lokasi():
    if request.method == 'POST':
        main_lokasi = request.form.get('main_lokasi', '').strip()
        nama_lokasi = request.form.get('nama_lokasi', '').strip() 
        
        cek_lokasi = Lokasi.query.filter(Lokasi.main_lokasi.ilike(main_lokasi), Lokasi.nama_lokasi.ilike(nama_lokasi)).first()
        if cek_lokasi:
            flash(f'Gagal! Sub Lokasi "{nama_lokasi}" sudah ada di dalam Main Lokasi "{main_lokasi}".', 'danger')
            return redirect(url_for('tambah_lokasi'))
            
        lokasi_baru = Lokasi(main_lokasi=main_lokasi, nama_lokasi=nama_lokasi)
        db.session.add(lokasi_baru)
        db.session.commit()
        flash('Titik lokasi baru berhasil ditambahkan.', 'success')
        return redirect(url_for('master_lokasi'))
        
    main_lokasi_list = [m[0] for m in db.session.query(Lokasi.main_lokasi).distinct().all()]
    return render_template('lokasi/tambah.html', main_lokasi_list=main_lokasi_list)

@app.route('/hapus_lokasi/<int:id>')
@login_required
@admin_required
def hapus_lokasi(id):
    lokasi = Lokasi.query.get_or_404(id)
    if lokasi.inventories or lokasi.consumables:
        flash(f'Gagal! Sub Lokasi "{lokasi.nama_lokasi}" masih berisi aset.', 'danger')
    else:
        db.session.delete(lokasi)
        db.session.commit()
        flash('Lokasi berhasil dihapus.', 'success')
    return redirect(url_for('master_lokasi'))

# ---------------------------------------------------------
# 4. RUTE RIWAYAT, EXPORT & CETAK QR
# ---------------------------------------------------------
@app.route('/cetak_qr/<kode>')
@login_required
def cetak_qr(kode):
    barang = Inventory.query.filter_by(kode_barang=kode).first() or Consumable.query.filter_by(kode_barang=kode).first_or_404()
    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(kode)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return render_template('transaksi/cetak_qr.html', barang=barang, qr_image=base64.b64encode(buf.getvalue()).decode('utf-8'))

@app.route('/riwayat_inventory')
@login_required
def riwayat_inventory():
    search = request.args.get('search', '').strip()
    start_date = request.args.get('start_date', '').strip()
    end_date = request.args.get('end_date', '').strip()
    page = request.args.get('page', 1, type=int)

    # PASTIKAN BARIS INI MENGANDUNG filter(Transaksi.jenis != 'Edit')
    query = Transaksi.query.filter(Transaksi.inventory_id != None, Transaksi.jenis != 'Edit')

    if search:
        query = query.join(Inventory).filter(or_(
            Inventory.nama_barang.ilike(f"%{search}%"),
            Inventory.serial_number.ilike(f"%{search}%"),
            Inventory.kode_barang.ilike(f"%{search}%")
        ))

    if start_date:
        query = query.filter(Transaksi.tanggal >= f"{start_date} 00:00:00")
    if end_date:
        query = query.filter(Transaksi.tanggal <= f"{end_date} 23:59:59")

    data = query.order_by(Transaksi.tanggal.desc()).paginate(page=page, per_page=15, error_out=False)
    return render_template('inventory/riwayat.html', data=data)

@app.route('/riwayat_consumable')
@login_required
def riwayat_consumable():
    search = request.args.get('search', '')
    start_date, end_date = request.args.get('start_date', ''), request.args.get('end_date', '')
    
    # Ambil hanya transaksi yang memiliki consumable_id
    query = Transaksi.query.join(Consumable).filter(Transaksi.consumable_id != None)
    
    if search:
        query = query.filter(db.or_(Consumable.nama_barang.ilike(f"%{search}%"), Consumable.kode_barang.ilike(f"%{search}%"), Transaksi.keterangan.ilike(f"%{search}%")))
    if start_date:
        query = query.filter(Transaksi.tanggal >= datetime.strptime(start_date, '%Y-%m-%d'))
    if end_date:
        query = query.filter(Transaksi.tanggal <= datetime.strptime(end_date, '%Y-%m-%d').replace(hour=23, minute=59, second=59))
        
    data = query.order_by(Transaksi.tanggal.desc()).paginate(page=request.args.get('page', 1, type=int), per_page=20, error_out=False)
    return render_template('consumable/riwayat.html', data=data, search_query=search, start_date=start_date, end_date=end_date)

@app.route('/export_riwayat_excel')
@login_required
def export_riwayat_excel():
    data_transaksi = Transaksi.query.order_by(Transaksi.tanggal.desc()).all()
    output, nama_file = generate_excel_report(Inventory.query.all(), Consumable.query.all(), data_transaksi)
    return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', as_attachment=True, download_name=nama_file)

# ---------------------------------------------------------
# 5. ERROR HANDLERS
# ---------------------------------------------------------
@app.errorhandler(404)
def page_not_found(e): 
    return render_template('errors/404.html'), 404

@app.errorhandler(403)
def access_denied(e): 
    return render_template('errors/403.html'), 403