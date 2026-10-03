from flask import render_template, request, redirect, url_for, flash
from flask_login import login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from sqlalchemy import func, or_
import calendar

from main import app, admin_required
from models import db, User, MainLokasi, SubLokasi, Inventory, Consumable, Transaksi, KategoriBarang, SatuanBarang

@app.context_processor
def inject_datetime():
    return {'dt': datetime}

# ---------------------------------------------------------
# 1. RUTE AUTENTIKASI & PENGGUNA
# ---------------------------------------------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        user = User.query.filter_by(payroll=request.form['payroll']).first()
        if user and check_password_hash(user.password, request.form['password']):
            login_user(user, remember=bool(request.form.get('remember')))
            return redirect(request.args.get('next') or url_for('index'))
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
    total_inventory = Inventory.query.filter_by(is_active=True).count()
    total_consumable = Consumable.query.filter_by(is_active=True).count()
    stok_kritis = Consumable.query.filter(Consumable.is_active==True, Consumable.stok <= 5).count()

    labels = []
    inv_masuk = []
    inv_keluar = []
    cons_masuk = []
    cons_keluar = []

    sekarang = datetime.now()
    
    for i in range(5, -1, -1):
        m = sekarang.month - i
        y = sekarang.year
        while m <= 0:
            m += 12
            y -= 1
            
        bulan_nama = datetime(y, m, 1).strftime('%b %Y')
        labels.append(bulan_nama)
        
        start_date = datetime(y, m, 1)
        _, last_day = calendar.monthrange(y, m)
        end_date = datetime(y, m, last_day, 23, 59, 59)
        
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
        
        inv_masuk.append(inv_m)
        inv_keluar.append(inv_k)
        cons_masuk.append(int(cons_m_query or 0))
        cons_keluar.append(int(cons_k_query or 0))

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
    main_lokasi_list = MainLokasi.query.order_by(MainLokasi.nama_main.asc()).all()
    sub_lokasi_list = SubLokasi.query.join(MainLokasi).order_by(MainLokasi.nama_main.asc(), SubLokasi.nama_sub.asc()).all()
    
    return render_template('lokasi/master.html', main_lokasi_list=main_lokasi_list, sub_lokasi_list=sub_lokasi_list)

@app.route('/tambah_lokasi', methods=['GET'])
@login_required
@admin_required
def tambah_lokasi():
    main_lokasi_list = MainLokasi.query.order_by(MainLokasi.nama_main.asc()).all()
    return render_template('lokasi/tambah.html', main_lokasi_list=main_lokasi_list)

@app.route('/tambah_main_lokasi', methods=['POST'])
@login_required
@admin_required
def tambah_main_lokasi():
    nama_main = request.form.get('nama_main', '').strip()
    keterangan = request.form.get('keterangan', '').strip()
    
    if MainLokasi.query.filter(MainLokasi.nama_main.ilike(nama_main)).first():
        flash(f'Gagal! Main Lokasi "{nama_main}" sudah ada.', 'danger')
    else:
        db.session.add(MainLokasi(nama_main=nama_main, keterangan=keterangan))
        db.session.commit()
        flash(f'Main Lokasi "{nama_main}" berhasil ditambahkan.', 'success')
        
    return redirect(url_for('master_lokasi'))

@app.route('/tambah_sub_lokasi', methods=['POST'])
@login_required
@admin_required
def tambah_sub_lokasi():
    main_lokasi_id = request.form.get('main_lokasi_id')
    nama_sub = request.form.get('nama_sub', '').strip()
    keterangan = request.form.get('keterangan', '').strip()
    
    if not main_lokasi_id:
        flash('Pilih Main Lokasi terlebih dahulu.', 'danger')
        return redirect(url_for('master_lokasi'))
        
    cek = SubLokasi.query.filter_by(main_lokasi_id=main_lokasi_id).filter(SubLokasi.nama_sub.ilike(nama_sub)).first()
    if cek:
        flash(f'Gagal! Sub Lokasi "{nama_sub}" sudah ada di area ini.', 'danger')
    else:
        db.session.add(SubLokasi(main_lokasi_id=main_lokasi_id, nama_sub=nama_sub, keterangan=keterangan))
        db.session.commit()
        flash(f'Sub Lokasi "{nama_sub}" berhasil ditambahkan.', 'success')
        
    return redirect(url_for('master_lokasi'))

@app.route('/edit_main_lokasi/<int:id>', methods=['POST'])
@login_required
@admin_required
def edit_main_lokasi(id):
    main_loc = MainLokasi.query.get_or_404(id)
    nama_main_baru = request.form.get('nama_main', '').strip()
    keterangan_baru = request.form.get('keterangan', '').strip()
    
    cek = MainLokasi.query.filter(MainLokasi.id != id, MainLokasi.nama_main.ilike(nama_main_baru)).first()
    if cek:
        flash(f'Gagal! Main Lokasi "{nama_main_baru}" sudah terdaftar.', 'danger')
    else:
        main_loc.nama_main = nama_main_baru
        main_loc.keterangan = keterangan_baru
        db.session.commit()
        flash('Data Main Lokasi berhasil diperbarui.', 'success')
        
    return redirect(url_for('master_lokasi'))

@app.route('/edit_sub_lokasi/<int:id>', methods=['POST'])
@login_required
@admin_required
def edit_sub_lokasi(id):
    sub_loc = SubLokasi.query.get_or_404(id)
    main_lokasi_id = request.form.get('main_lokasi_id')
    nama_sub_baru = request.form.get('nama_sub', '').strip()
    keterangan_baru = request.form.get('keterangan', '').strip()
    
    cek = SubLokasi.query.filter(SubLokasi.id != id, SubLokasi.main_lokasi_id == main_lokasi_id, SubLokasi.nama_sub.ilike(nama_sub_baru)).first()
    if cek:
        flash(f'Gagal! Sub Lokasi "{nama_sub_baru}" sudah ada di area tersebut.', 'danger')
    else:
        sub_loc.main_lokasi_id = main_lokasi_id
        sub_loc.nama_sub = nama_sub_baru
        sub_loc.keterangan = keterangan_baru
        db.session.commit()
        flash('Data Sub Lokasi berhasil diperbarui.', 'success')
        
    return redirect(url_for('master_lokasi'))

# ---------------------------------------------------------
# 4. RUTE MASTER KATEGORI & SATUAN BARANG
# ---------------------------------------------------------
@app.route('/master_kategori_satuan', methods=['GET', 'POST'])
@login_required
@admin_required
def master_kategori_satuan():
    if request.method == 'POST':
        nama_kategori = request.form.get('nama_kategori', '').strip()
        jenis = request.form.get('jenis', '').strip()
        nama_satuan = request.form.get('satuan', '').strip() if jenis == 'Consumable' else ''

        if not nama_kategori and not nama_satuan:
            flash('Gagal! Harap isi minimal Nama Kategori atau Nama Satuan.', 'danger')
            return redirect(url_for('master_kategori_satuan'))

        pesan = []
        
        if nama_kategori:
            if KategoriBarang.query.filter_by(nama_kategori=nama_kategori, jenis=jenis).first():
                pesan.append(f'Kategori "{nama_kategori}" sudah ada')
            else:
                db.session.add(KategoriBarang(nama_kategori=nama_kategori, jenis=jenis))
                pesan.append(f'Kategori "{nama_kategori}" ditambahkan')

        if nama_satuan:
            if SatuanBarang.query.filter_by(nama_satuan=nama_satuan).first():
                pesan.append(f'Satuan "{nama_satuan}" sudah ada')
            else:
                db.session.add(SatuanBarang(nama_satuan=nama_satuan))
                pesan.append(f'Satuan "{nama_satuan}" ditambahkan')

        db.session.commit()
        flash(" | ".join(pesan) + ".", 'success')
        return redirect(url_for('master_kategori_satuan'))

    kat_inventory = KategoriBarang.query.filter_by(jenis='Inventory').order_by(KategoriBarang.nama_kategori.asc()).all()
    kat_consumable = KategoriBarang.query.filter_by(jenis='Consumable').order_by(KategoriBarang.nama_kategori.asc()).all()
    data_satuan = SatuanBarang.query.order_by(SatuanBarang.nama_satuan.asc()).all()

    return render_template('kategori/master.html', 
                           kat_inventory=kat_inventory, 
                           kat_consumable=kat_consumable, 
                           data_satuan=data_satuan)

@app.route('/hapus_kategori/<int:id>', methods=['GET'])
@login_required
@admin_required
def hapus_kategori(id):
    kategori = KategoriBarang.query.get_or_404(id)
    if (kategori.jenis == 'Inventory' and kategori.inventories) or (kategori.jenis == 'Consumable' and kategori.consumables):
        flash('Gagal! Kategori ini masih digunakan oleh aset aktif.', 'danger')
    else:
        db.session.delete(kategori)
        db.session.commit()
        flash('Kategori berhasil dihapus.', 'success')
    return redirect(url_for('master_kategori_satuan'))

@app.route('/hapus_satuan/<int:id>', methods=['GET'])
@login_required
@admin_required
def hapus_satuan(id):
    satuan = SatuanBarang.query.get_or_404(id)
    if satuan.consumables:
        flash('Gagal! Satuan ini masih digunakan oleh data Consumable.', 'danger')
    else:
        db.session.delete(satuan)
        db.session.commit()
        flash('Satuan berhasil dihapus.', 'success')
    return redirect(url_for('master_kategori_satuan'))

# ---------------------------------------------------------
# 5. RUTE TAMPILAN RIWAYAT
# ---------------------------------------------------------
@app.route('/riwayat_inventory')
@login_required
def riwayat_inventory():
    search = request.args.get('search', '').strip()
    start_date = request.args.get('start_date', '').strip()
    end_date = request.args.get('end_date', '').strip()
    page = request.args.get('page', 1, type=int)

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

# ==========================================
# PERBAIKAN: RIWAYAT CONSUMABLE (REVERSE STOCK CALCULATION)
# ==========================================
@app.route('/riwayat_consumable')
@login_required
def riwayat_consumable():
    search = request.args.get('search', '').strip().lower()
    start_date = request.args.get('start_date', '').strip()
    end_date = request.args.get('end_date', '').strip()
    
    # Ambil SEMUA transaksi untuk menghitung mundur dari stok saat ini (Desc = Terbaru ke Terlama)
    # Filter pencarian ditunda ke level list (Python) agar urutan hitungan stok valid
    semua_trx = Transaksi.query.filter(Transaksi.consumable_id != None).order_by(Transaksi.id.desc()).all()
    
    stok_tracker = {}
    processed_data = []
    
    for trx in semua_trx:
        c_id = trx.consumable_id
        
        # Di transaksi terbaru yang dibaca pertama kali, ambil stok aktual di DB
        if c_id not in stok_tracker:
            stok_tracker[c_id] = trx.consumable.stok if trx.consumable else 0
            
        stok_sesudah = stok_tracker[c_id]
        
        # Hitung mundur (reverse engineering) ke stok sebelumnya
        if trx.jenis == 'Masuk':
            stok_sebelum = stok_sesudah - trx.jumlah
        elif trx.jenis == 'Keluar':
            stok_sebelum = stok_sesudah + trx.jumlah
        else:
            stok_sebelum = stok_sesudah # Edit/Mutasi
            
        # Simpan state untuk mundur ke iterasi transaksi yang lebih lampau
        stok_tracker[c_id] = stok_sebelum
        
        trx.stok_sebelum = stok_sebelum
        trx.stok_sekarang = stok_sesudah
        
        # -----------------------------
        # Logika Filter Search & Date
        # -----------------------------
        tampil = True
        
        if search:
            nm = (trx.consumable.nama_barang or '').lower() if trx.consumable else ''
            kd = (trx.consumable.kode_barang or '').lower() if trx.consumable else ''
            kt = (trx.keterangan or '').lower()
            if search not in nm and search not in kd and search not in kt:
                tampil = False
                
        if start_date and trx.tanggal:
            if trx.tanggal.strftime('%Y-%m-%d') < start_date:
                tampil = False
        if end_date and trx.tanggal:
            if trx.tanggal.strftime('%Y-%m-%d') > end_date:
                tampil = False
                
        if tampil:
            processed_data.append(trx)
            
    # Data di HTML akan terurut dari yang terbaru secara otomatis, tidak perlu di-reverse
    return render_template('consumable/riwayat.html', data=processed_data)

# ---------------------------------------------------------
# 6. ERROR HANDLERS
# ---------------------------------------------------------
@app.errorhandler(404)
def page_not_found(e): 
    return render_template('errors/404.html'), 404

@app.errorhandler(403)
def access_denied(e): 
    return render_template('errors/403.html'), 403