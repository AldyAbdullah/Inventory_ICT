from flask import Flask, render_template, request, redirect, url_for, flash, abort, send_file, make_response
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import os
import pdfkit
from export_utils import generate_excel_report
import qrcode
import io
import base64

app = Flask(__name__)
app.secret_key = 'kunci_rahasia_inventaris_job_tomori_sangat_aman'
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

class Transaksi(db.Model):
    __tablename__ = 'transaksi'
    id = db.Column(db.Integer, primary_key=True)
    barang_id = db.Column(db.Integer, db.ForeignKey('barang_it.id'), nullable=False)
    jenis = db.Column(db.String(10), nullable=False)
    jumlah = db.Column(db.Integer, nullable=False)
    tanggal = db.Column(db.DateTime, default=datetime.utcnow)
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
    search_query = request.args.get('search', '')
    
    # Mengambil seluruh data satu kali untuk efisiensi
    semua_barang = BarangIT.query.all()
    
    if search_query:
        barang_habis_pakai = [
            b for b in semua_barang 
            if search_query.lower() in b.nama_barang.lower() or search_query.lower() in b.kode_barang.lower()
        ]
    else:
        barang_habis_pakai = semua_barang
        
    total_jenis_barang = len(semua_barang)
    total_stok = sum(item.stok for item in semua_barang)
    stok_kritis = sum(1 for item in semua_barang if item.stok <= 5)

    return render_template('index.html', 
                           data=barang_habis_pakai,
                           total_jenis=total_jenis_barang,
                           total_stok=total_stok,
                           stok_kritis=stok_kritis,
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
def tambah():
    kode_scan = request.args.get('kode_scan', '')

    if request.method == 'POST':
        kode_barang = request.form.get('kode_barang')
        nama_barang = request.form.get('nama_barang')
        kategori = request.form.get('kategori')
        stok = int(request.form.get('stok', 0))
        satuan = request.form.get('satuan')

        # 1. Masukkan data barang ke database
        barang_baru = BarangIT(kode_barang=kode_barang, nama_barang=nama_barang, kategori=kategori, stok=stok, satuan=satuan)
        db.session.add(barang_baru)
        db.session.commit() # Commit agar barang_baru mendapatkan ID

        # 2. Catat riwayat stok awal (jika stok yang diinput lebih dari 0)
        if stok > 0:
            transaksi_awal = Transaksi(
                barang_id=barang_baru.id, 
                jenis='Masuk', 
                jumlah=stok, 
                keterangan='Stok Awal (Barang Baru)'
            )
            db.session.add(transaksi_awal)
            db.session.commit()
        
        flash('Barang baru berhasil ditambahkan beserta riwayat stok awalnya.', 'success')
        return redirect(url_for('index'))

    return render_template('tambah.html', kode_scan=kode_scan)
@app.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit(id):
    barang = BarangIT.query.get_or_404(id)
    if request.method == 'POST':
        barang.kode_barang = request.form['kode_barang']
        barang.nama_barang = request.form['nama_barang']
        barang.kategori = request.form['kategori']
        barang.stok = request.form['stok']
        barang.satuan = request.form['satuan']
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('edit.html', barang=barang)

@app.route('/hapus/<int:id>')
@login_required
@admin_required
def hapus(id):
    barang = BarangIT.query.get_or_404(id)
    db.session.delete(barang)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/transaksi/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def catat_transaksi(id):
    barang = BarangIT.query.get_or_404(id)
    if request.method == 'POST':
        jenis = request.form.get('jenis_transaksi')
        jumlah = int(request.form['jumlah'])
        keterangan = request.form['keterangan']

        if jenis == 'Keluar' and jumlah > barang.stok:
            flash(f'Gagal! Jumlah keluar melebihi stok. Sisa stok: {barang.stok}', 'danger')
            return redirect(url_for('catat_transaksi', id=barang.id, jenis='keluar'))

        transaksi_baru = Transaksi(barang_id=barang.id, jenis=jenis, jumlah=jumlah, keterangan=keterangan)
        
        if jenis == 'Masuk':
            barang.stok += jumlah
        elif jenis == 'Keluar':
            barang.stok -= jumlah

        db.session.add(transaksi_baru)
        db.session.commit()
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

@app.route('/riwayat')
@login_required
def riwayat():
    data_riwayat = Transaksi.query.order_by(Transaksi.tanggal.desc()).all()
    return render_template('riwayat.html', riwayat=data_riwayat)

@app.route('/export/excel')
@login_required
def export_excel():
    data_barang = BarangIT.query.all()
    data_transaksi = Transaksi.query.order_by(Transaksi.tanggal.desc()).all()
    output, nama_file = generate_excel_report(data_barang, data_transaksi)
    return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', as_attachment=True, download_name=nama_file)

@app.route('/export/pdf')
@login_required
def export_pdf():
    data_barang = BarangIT.query.all()
    data_transaksi = Transaksi.query.order_by(Transaksi.tanggal.desc()).all()
    tanggal_cetak = datetime.now().strftime('%d %B %Y %H:%M WIB')
    logo_path = os.path.join(app.root_path, 'static', 'img', 'logo-tomori.png').replace('\\', '/')

    rendered_html = render_template('surat_laporan.html', data=data_barang, riwayat=data_transaksi, tanggal_cetak=tanggal_cetak, logo_path=logo_path)

    path_wkhtmltopdf = r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe'
    config = pdfkit.configuration(wkhtmltopdf=path_wkhtmltopdf)
    options = {'page-size': 'A4', 'margin-top': '20mm', 'margin-right': '20mm', 'margin-bottom': '20mm', 'margin-left': '20mm', 'encoding': "UTF-8", 'enable-local-file-access': None}

    pdf = pdfkit.from_string(rendered_html, False, configuration=config, options=options)
    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=Laporan_Inventaris_Tomori_{datetime.now().strftime("%Y%m%d")}.pdf'
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

if __name__ == '__main__':
    # Tambahkan host='0.0.0.0'
    app.run(host='0.0.0.0', port=5000, debug=True)