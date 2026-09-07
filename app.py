from flask import Flask, render_template, request, redirect, url_for, flash, abort, send_file, make_response
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import calendar
import os
import pdfkit
from export_utils import generate_excel_report
import qrcode
import io
import base64
from dotenv import load_dotenv


load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')
app.config['REMEMBER_COOKIE_DURATION'] = timedelta(days=30)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///inventaris_job_tomori.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.role != 'Admin':
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='Viewer')
    nama_lengkap = db.Column(db.String(100), nullable=True)
    jabatan = db.Column(db.String(50), nullable=True)
    departemen = db.Column(db.String(50), nullable=True)

class BarangIT(db.Model):
    __tablename__ = 'barang_it'
    id = db.Column(db.Integer, primary_key=True)
    kode_barang = db.Column(db.String(20), unique=True, nullable=False)
    nama_barang = db.Column(db.String(100), nullable=False)
    kategori = db.Column(db.String(50), nullable=False)
    stok = db.Column(db.Integer, default=0)
    satuan = db.Column(db.String(20), nullable=False)
    is_active = db.Column(db.Boolean, default=True)

class Transaksi(db.Model):
    __tablename__ = 'transaksi'
    id = db.Column(db.Integer, primary_key=True)
    barang_id = db.Column(db.Integer, db.ForeignKey('barang_it.id'), nullable=False)
    jenis = db.Column(db.String(10), nullable=False)
    jumlah = db.Column(db.Integer, nullable=False)
    tanggal = db.Column(db.DateTime, default=lambda: datetime.utcnow() + timedelta(hours=8))    
    keterangan = db.Column(db.String(200))
    barang = db.relationship('BarangIT', backref=db.backref('riwayat_transaksi', lazy=True))

with app.app_context():
    db.create_all()

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        remember = True if request.form.get('remember') else False

        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user, remember=remember)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('index'))
        else:
            flash('Username atau password salah.', 'error')

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    # 1. Metrik Ringkasan (Hanya barang aktif)
    semua_barang = BarangIT.query.filter_by(is_active=True).all()
    total_jenis = len(semua_barang)
    total_stok = sum(item.stok for item in semua_barang)
    stok_kritis = sum(1 for item in semua_barang if item.stok <= 5)
    
    # 2. Persiapan Data Grafik (6 Bulan Terakhir)
    labels = []
    data_masuk = []
    data_keluar = []
    
    semua_transaksi = Transaksi.query.all()
    waktu_sekarang = datetime.utcnow() + timedelta(hours=8)
    
    # Looping mundur dari 5 bulan lalu sampai bulan ini (total 6 bulan)
    for i in range(5, -1, -1):
        bulan_target = (waktu_sekarang.month - i - 1) % 12 + 1
        tahun_target = waktu_sekarang.year + ((waktu_sekarang.month - i - 1) // 12)
        
        # Buat Label (Contoh: "Sep 2026")
        nama_bulan = calendar.month_abbr[bulan_target]
        labels.append(f"{nama_bulan} {tahun_target}")
        
        # Hitung akumulasi masuk & keluar pada bulan tersebut
        total_m = sum(t.jumlah for t in semua_transaksi if t.jenis == 'Masuk' and t.tanggal.month == bulan_target and t.tanggal.year == tahun_target)
        total_k = sum(t.jumlah for t in semua_transaksi if t.jenis == 'Keluar' and t.tanggal.month == bulan_target and t.tanggal.year == tahun_target)
        
        data_masuk.append(total_m)
        data_keluar.append(total_k)

    return render_template('index.html', 
                           total_jenis=total_jenis,
                           total_stok=total_stok,
                           stok_kritis=stok_kritis,
                           labels=labels,
                           data_masuk=data_masuk,
                           data_keluar=data_keluar)

@app.route('/master_barang')
@login_required
def master_barang():
    # Kueri khusus Data Master Barang (Paginasi & Pencarian)
    search_query = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)
    
    query = BarangIT.query.filter_by(is_active=True)
    
    if search_query:
        query = query.filter(
            db.or_(
                BarangIT.nama_barang.ilike(f"%{search_query}%"),
                BarangIT.kode_barang.ilike(f"%{search_query}%")
            )
        )
    
    paginated_data = query.paginate(page=page, per_page=20, error_out=False)
    
    return render_template('master_barang.html', 
                           data=paginated_data,
                           search_query=search_query)

@app.route('/profil', methods=['GET', 'POST'])
@login_required
def profil():
    if request.method == 'POST':
        current_user.nama_lengkap = request.form.get('nama_lengkap')
        current_user.jabatan = request.form.get('jabatan')
        current_user.departemen = request.form.get('departemen')
        
        password_baru = request.form.get('password_baru')
        if password_baru:
            current_user.password = generate_password_hash(password_baru)
            
        db.session.commit()
        flash('Profil berhasil diperbarui.', 'success')
        return redirect(url_for('profil'))
        
    return render_template('profil.html')

@app.route('/tambah', methods=['GET', 'POST'])
@login_required
@admin_required
def tambah():
    kode_scan = request.args.get('kode_scan', '')

    if request.method == 'POST':
        kode_barang = request.form.get('kode_barang').strip()
        nama_barang = request.form.get('nama_barang').strip()
        kategori = request.form.get('kategori')
        satuan = request.form.get('satuan')
        
        try:
            stok = int(request.form.get('stok', 0))
        except ValueError:
            flash('Format stok tidak valid.', 'danger')
            return redirect(url_for('tambah'))

        # Validasi Backend
        if stok < 0:
            flash('Gagal! Stok awal tidak boleh kurang dari 0.', 'danger')
            return redirect(url_for('tambah'))
            
        cek_kode = BarangIT.query.filter_by(kode_barang=kode_barang).first()
        if cek_kode:
            flash(f'Gagal! Kode barang {kode_barang} sudah terdaftar di sistem.', 'danger')
            return redirect(url_for('tambah'))

        barang_baru = BarangIT(kode_barang=kode_barang, nama_barang=nama_barang, kategori=kategori, stok=stok, satuan=satuan)
        db.session.add(barang_baru)
        db.session.commit()

        if stok > 0:
            transaksi_awal = Transaksi(
                barang_id=barang_baru.id, 
                jenis='Masuk', 
                jumlah=stok, 
                keterangan='Stok Awal (Barang Baru)'
            )
            db.session.add(transaksi_awal)
            db.session.commit()
        
        flash('Barang baru berhasil ditambahkan.', 'success')
        return redirect(url_for('index'))

    return render_template('tambah.html', kode_scan=kode_scan)

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit(id):
    barang = BarangIT.query.get_or_404(id)
    if request.method == 'POST':
        try:
            stok_baru = int(request.form['stok'])
        except ValueError:
            flash('Format stok tidak valid.', 'danger')
            return redirect(url_for('edit', id=id))
            
        # Validasi Backend
        if stok_baru < 0:
            flash('Gagal! Nilai stok tidak boleh kurang dari 0.', 'danger')
            return redirect(url_for('edit', id=id))

        barang.kode_barang = request.form['kode_barang'].strip()
        barang.nama_barang = request.form['nama_barang'].strip()
        barang.kategori = request.form['kategori']
        barang.stok = stok_baru
        barang.satuan = request.form['satuan']
        
        db.session.commit()
        flash('Data barang berhasil diperbarui.', 'success')
        return redirect(url_for('index'))
        
    return render_template('edit.html', barang=barang)

@app.route('/hapus/<int:id>')
@login_required
@admin_required
def hapus(id):
    barang = BarangIT.query.get_or_404(id)
    
    # Ubah status menjadi False, BUKAN dihapus permanen
    barang.is_active = False 
    
    db.session.commit()
    flash(f'Barang {barang.nama_barang} berhasil dihapus.', 'success')
    return redirect(url_for('index'))

@app.route('/transaksi/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def catat_transaksi(id):
    barang = BarangIT.query.get_or_404(id)
    if request.method == 'POST':
        jenis = request.form.get('jenis_transaksi')
        keterangan = request.form['keterangan'].strip()
        
        try:
            jumlah = int(request.form['jumlah'])
        except ValueError:
            flash('Format jumlah tidak valid.', 'danger')
            return redirect(url_for('catat_transaksi', id=barang.id))

        # Validasi Backend: Cegah angka 0 atau negatif
        if jumlah <= 0:
            flash('Gagal! Jumlah transaksi harus lebih dari 0.', 'danger')
            return redirect(url_for('catat_transaksi', id=barang.id))

        # Validasi Backend: Cegah stok minus
        if jenis == 'Keluar' and jumlah > barang.stok:
            flash(f'Gagal! Jumlah keluar ({jumlah}) melebihi stok tersedia ({barang.stok}).', 'danger')
            return redirect(url_for('catat_transaksi', id=barang.id))

        transaksi_baru = Transaksi(barang_id=barang.id, jenis=jenis, jumlah=jumlah, keterangan=keterangan)
        
        if jenis == 'Masuk':
            barang.stok += jumlah
        elif jenis == 'Keluar':
            barang.stok -= jumlah

        db.session.add(transaksi_baru)
        db.session.commit()
        flash('Transaksi berhasil dicatat.', 'success')
        return redirect(url_for('index'))
        
    return render_template('form_transaksi.html', barang=barang)

@app.route('/scan_transaksi/<jenis>/<kode>')
@login_required
def scan_transaksi(jenis, kode):
    barang = BarangIT.query.filter_by(kode_barang=kode).first()
    if barang:
        # Teruskan parameter 'jenis' ke URL form transaksi
        return redirect(url_for('catat_transaksi', id=barang.id, jenis=jenis))
    else:
        flash(f'Barcode {kode} belum terdaftar. Silakan lengkapi data.', 'warning')
        return redirect(url_for('tambah', kode_scan=kode))
    
@app.route('/cetak_qr/<kode>')
@login_required
def cetak_qr(kode):
    barang = BarangIT.query.filter_by(kode_barang=kode).first_or_404()
    
    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(kode)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    qr_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')
    
    return render_template('cetak_qr.html', barang=barang, qr_image=qr_base64)

from datetime import datetime

@app.route('/riwayat')
@login_required
def riwayat():
    # 1. Ambil parameter dari URL
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('search', '')
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')

    # 2. Mulai kueri dengan melakukan JOIN antara tabel Transaksi dan BarangIT
    # Asumsi relasi di model Transaksi Anda bernama 'barang' (transaksi.barang)
    query = Transaksi.query.join(BarangIT)

    # 3. Terapkan Filter Pencarian (Nama Barang, Kode, atau Keterangan)
    if search_query:
        query = query.filter(
            db.or_(
                BarangIT.nama_barang.ilike(f"%{search_query}%"),
                BarangIT.kode_barang.ilike(f"%{search_query}%"),
                Transaksi.keterangan.ilike(f"%{search_query}%")
            )
        )

    # 4. Terapkan Filter Rentang Tanggal
    if start_date:
        query = query.filter(Transaksi.tanggal >= datetime.strptime(start_date, '%Y-%m-%d'))
    if end_date:
        # Sesuaikan end_date hingga pukul 23:59:59 agar pencarian inklusif
        end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
        query = query.filter(Transaksi.tanggal <= end_date_obj)

    # 5. Urutkan dari transaksi terbaru dan terapkan paginasi (20 per halaman)
    query = query.order_by(Transaksi.tanggal.desc())
    paginated_data = query.paginate(page=page, per_page=20, error_out=False)

    return render_template('riwayat.html', 
                           data=paginated_data, 
                           search_query=search_query,
                           start_date=start_date,
                           end_date=end_date)

@app.route('/export_riwayat_excel')
@login_required
def export_riwayat_excel():
    # 1. Tangkap parameter dari URL
    search_query = request.args.get('search', '')
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')

    # 2. Filter Kueri Transaksi
    query = Transaksi.query.join(BarangIT)
    if search_query:
        query = query.filter(
            db.or_(
                BarangIT.nama_barang.ilike(f"%{search_query}%"),
                BarangIT.kode_barang.ilike(f"%{search_query}%"),
                Transaksi.keterangan.ilike(f"%{search_query}%")
            )
        )
    if start_date:
        query = query.filter(Transaksi.tanggal >= datetime.strptime(start_date, '%Y-%m-%d'))
    if end_date:
        end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
        query = query.filter(Transaksi.tanggal <= end_date_obj)

    data_transaksi = query.order_by(Transaksi.tanggal.desc()).all()
    
    # Ambil data barang aktif untuk Sheet 1 agar export_utils tidak error
    data_barang = BarangIT.query.filter_by(is_active=True).all()

    # 3. Gunakan fungsi dari export_utils.py
    output, nama_file = generate_excel_report(data_barang, data_transaksi)
    
    return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', as_attachment=True, download_name=nama_file)


@app.route('/export_riwayat_pdf')
@login_required
def export_riwayat_pdf():
    # 1. Tangkap parameter dari URL
    search_query = request.args.get('search', '')
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')

    # 2. Filter Kueri Transaksi
    query = Transaksi.query.join(BarangIT)
    if search_query:
        query = query.filter(
            db.or_(
                BarangIT.nama_barang.ilike(f"%{search_query}%"),
                BarangIT.kode_barang.ilike(f"%{search_query}%"),
                Transaksi.keterangan.ilike(f"%{search_query}%")
            )
        )
    if start_date:
        query = query.filter(Transaksi.tanggal >= datetime.strptime(start_date, '%Y-%m-%d'))
    if end_date:
        end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
        query = query.filter(Transaksi.tanggal <= end_date_obj)

    data_transaksi = query.order_by(Transaksi.tanggal.desc()).all()
    data_barang = BarangIT.query.filter_by(is_active=True).all()

    # 3. Render PDF menggunakan konfigurasi pdfkit bawaan Anda
    tanggal_cetak = (datetime.utcnow() + timedelta(hours=8)).strftime('%d %B %Y %H:%M WITA')
    logo_path = os.path.join(app.root_path, 'static', 'img', 'logo-tomori.png').replace('\\', '/')

    rendered_html = render_template('surat_laporan.html', data=data_barang, riwayat=data_transaksi, tanggal_cetak=tanggal_cetak, logo_path=logo_path)

    path_wkhtmltopdf = os.getenv('WKHTMLTOPDF_PATH')
    config = pdfkit.configuration(wkhtmltopdf=path_wkhtmltopdf)
    options = {
        'page-size': 'A4', 
        'margin-top': '20mm', 
        'margin-right': '20mm', 
        'margin-bottom': '20mm', 
        'margin-left': '20mm', 
        'encoding': "UTF-8", 
        'enable-local-file-access': None
    }

    pdf = pdfkit.from_string(rendered_html, False, configuration=config, options=options)
    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=Laporan_Filter_Transaksi_{datetime.now().strftime("%Y%m%d")}.pdf'
    
    return response

@app.route('/users')
@login_required
@admin_required
def users():
    all_users = User.query.all()
    return render_template('users.html', users=all_users)

@app.route('/tambah_user', methods=['POST'])
@login_required
@admin_required
def tambah_user():
    username = request.form['username']
    password = request.form['password']
    role = request.form['role']
    nama_lengkap = request.form.get('nama_lengkap')
    jabatan = request.form.get('jabatan')
    departemen = request.form.get('departemen')

    user_exists = User.query.filter_by(username=username).first()
    if user_exists:
        flash('Username sudah digunakan.', 'error')
        return redirect(url_for('users'))

    hashed_password = generate_password_hash(password)
    user_baru = User(username=username, password=hashed_password, role=role, nama_lengkap=nama_lengkap, jabatan=jabatan, departemen=departemen)
    db.session.add(user_baru)
    db.session.commit()
    flash('Pengguna berhasil ditambahkan.', 'success')
    return redirect(url_for('users'))

@app.route('/users/hapus/<int:id>')
@login_required
@admin_required
def hapus_user(id):
    if id == current_user.id:
        flash('Tidak dapat menghapus akun yang sedang digunakan.', 'error')
        return redirect(url_for('users'))
        
    user = User.query.get_or_404(id)
    db.session.delete(user)
    db.session.commit()
    flash('Pengguna berhasil dihapus.', 'success')
    return redirect(url_for('users'))

# --- Penanganan Error (Error Handling) ---

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(403)
def access_denied(e):
    return render_template('403.html'), 403

if __name__ == '__main__':
    # Ambil status debug dari .env (default False jika tidak ditemukan)
    is_debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(host='0.0.0.0', port=5000, debug=is_debug)