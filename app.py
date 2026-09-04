from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from flask import abort
from flask import send_file
from export_utils import generate_excel_report
import pdfkit
from flask import make_response
from datetime import timedelta

app = Flask(__name__)
app.secret_key = 'kunci_rahasia_inventaris_job_tomori_sangat_aman'
app.config['REMEMBER_COOKIE_DURATION'] = timedelta(days=30)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///inventaris_job_tomori.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Konfigurasi Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' # Halaman tujuan jika user belum login

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.role != 'Admin':
            abort(403) # Mengembalikan error 403 Forbidden jika bukan Admin
        return f(*args, **kwargs)
    return decorated_function

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Model Tabel User
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='Viewer')
    
    # Tambahan kolom profil
    nama_lengkap = db.Column(db.String(100), nullable=True)
    jabatan = db.Column(db.String(50), nullable=True)
    departemen = db.Column(db.String(50), nullable=True)

class BarangIT(db.Model):
    __tablename__ = 'barang_it' # Deklarasi nama tabel secara eksplisit
    id = db.Column(db.Integer, primary_key=True)
    kode_barang = db.Column(db.String(20), unique=True, nullable=False)
    nama_barang = db.Column(db.String(100), nullable=False)
    kategori = db.Column(db.String(50), nullable=False)
    stok = db.Column(db.Integer, default=0)
    satuan = db.Column(db.String(20), nullable=False)

# Tambahkan Model Transaksi
class Transaksi(db.Model):
    __tablename__ = 'transaksi'
    id = db.Column(db.Integer, primary_key=True)
    barang_id = db.Column(db.Integer, db.ForeignKey('barang_it.id'), nullable=False)
    jenis = db.Column(db.String(10), nullable=False) # 'Masuk' atau 'Keluar'
    jumlah = db.Column(db.Integer, nullable=False)
    tanggal = db.Column(db.DateTime, default=datetime.utcnow)
    keterangan = db.Column(db.String(200))

    # Relasi untuk memanggil data barang dari tabel transaksi
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
        # Menangkap nilai checkbox (akan bernilai 'on' jika dicentang, atau None jika tidak)
        remember = True if request.form.get('remember') else False

        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            # Tambahkan parameter remember di sini
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
    # Menangkap parameter pencarian dari URL
    search_query = request.args.get('search', '')
    
    # Query data untuk tabel (berdasarkan pencarian jika ada)
    if search_query:
        barang_habis_pakai = BarangIT.query.filter(
            (BarangIT.nama_barang.ilike(f'%{search_query}%')) | 
            (BarangIT.kode_barang.ilike(f'%{search_query}%'))
        ).all()
    else:
        barang_habis_pakai = BarangIT.query.all()
        
    # Kalkulasi data statistik (menggunakan seluruh data di database, bukan data hasil filter)
    semua_barang = BarangIT.query.all()
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
        
        # Ubah password jika form diisi
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
    # Jika user menekan tombol 'Simpan' (metode POST)
    if request.method == 'POST':
        # Mengambil data dari form HTML
        kode = request.form['kode_barang']
        nama = request.form['nama_barang']
        kategori = request.form['kategori']
        stok = request.form['stok']
        satuan = request.form['satuan']

        # Membuat objek barang baru
        barang_baru = BarangIT(
            kode_barang=kode, 
            nama_barang=nama, 
            kategori=kategori, 
            stok=stok, 
            satuan=satuan
        )
        
        # Menyimpan ke database
        db.session.add(barang_baru)
        db.session.commit()
        
        # Mengarahkan kembali ke halaman utama setelah berhasil
        return redirect(url_for('index'))
    
    # Jika user hanya membuka halaman (metode GET), tampilkan form
    return render_template('tambah.html')

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit(id):
    # Mencari data barang berdasarkan ID, jika tidak ada kembalikan error 404
    barang = BarangIT.query.get_or_404(id)
    
    if request.method == 'POST':
        # Memperbarui data objek barang dengan data dari form
        barang.kode_barang = request.form['kode_barang']
        barang.nama_barang = request.form['nama_barang']
        barang.kategori = request.form['kategori']
        barang.stok = request.form['stok']
        barang.satuan = request.form['satuan']
        
        # Menyimpan perubahan ke database
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
        jenis = request.form['jenis']
        jumlah = int(request.form['jumlah'])
        keterangan = request.form['keterangan']

        # Validasi agar stok tidak minus
        if jenis == 'Keluar' and jumlah > barang.stok:
            return "Error: Stok tidak mencukupi untuk dikeluarkan.", 400

        # Catat ke tabel Transaksi
        transaksi_baru = Transaksi(
            barang_id=barang.id, 
            jenis=jenis, 
            jumlah=jumlah, 
            keterangan=keterangan
        )
        
        # Perbarui stok di tabel BarangIT
        if jenis == 'Masuk':
            barang.stok += jumlah
        elif jenis == 'Keluar':
            barang.stok -= jumlah

        db.session.add(transaksi_baru)
        db.session.commit()
        
        return redirect(url_for('index'))
        
    return render_template('form_transaksi.html', barang=barang)

@app.route('/riwayat')
@login_required
def riwayat():
    # Mengambil data transaksi diurutkan dari yang terbaru
    data_riwayat = Transaksi.query.order_by(Transaksi.tanggal.desc()).all()
    return render_template('riwayat.html', riwayat=data_riwayat)

import pandas as pd
from flask import send_file
import io
from datetime import datetime
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

@app.route('/export/excel')
@login_required
def export_excel():
    # Ambil data dari database
    data_barang = BarangIT.query.all()
    data_transaksi = Transaksi.query.order_by(Transaksi.tanggal.desc()).all()
    
    # Panggil fungsi dari file eksternal
    output, nama_file = generate_excel_report(data_barang, data_transaksi)
    
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=nama_file
    )

import os # Pastikan modul ini sudah diimpor di bagian atas

@app.route('/export/pdf')
@login_required
def export_pdf():
    data_barang = BarangIT.query.all()
    data_transaksi = Transaksi.query.order_by(Transaksi.tanggal.desc()).all()
    tanggal_cetak = datetime.now().strftime('%d %B %Y %H:%M WIB')

    # Mendapatkan jalur absolut gambar logo
    logo_path = os.path.join(app.root_path, 'static', 'img', 'logo-tomori.png')
    # Ubah backslash (\) menjadi slash (/) agar file:/// dapat membacanya di Windows
    logo_path = logo_path.replace('\\', '/')

    rendered_html = render_template(
        'surat_laporan.html', 
        data=data_barang,
        riwayat=data_transaksi, 
        tanggal_cetak=tanggal_cetak,
        logo_path=logo_path # Kirim variabel logo_path ke template
    )

    path_wkhtmltopdf = r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe'
    config = pdfkit.configuration(wkhtmltopdf=path_wkhtmltopdf)

    options = {
        'page-size': 'A4',
        'margin-top': '20mm',
        'margin-right': '20mm',
        'margin-bottom': '20mm',
        'margin-left': '20mm',
        'encoding': "UTF-8",
        'enable-local-file-access': None # Opsi ini wajib agar wkhtmltopdf bisa membaca gambar lokal
    }

    pdf = pdfkit.from_string(rendered_html, False, configuration=config, options=options)

    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=Laporan_Inventaris_Tomori_{datetime.now().strftime("%Y%m%d")}.pdf'
    
    return response

@app.route('/users')
@login_required
@admin_required
def kelola_user():
    users = User.query.all()
    return render_template('users.html', users=users)

@app.route('/users/tambah', methods=['POST'])
@login_required
@admin_required
def tambah_user():
    username = request.form['username']
    password = request.form['password']
    role = request.form['role']

    # Validasi jika username sudah digunakan
    user_exists = User.query.filter_by(username=username).first()
    if user_exists:
        return "Error: Username sudah digunakan.", 400

    hashed_password = generate_password_hash(password)
    user_baru = User(username=username, password=hashed_password, role=role)
    db.session.add(user_baru)
    db.session.commit()
    
    return redirect(url_for('kelola_user'))

@app.route('/users/hapus/<int:id>')
@login_required
@admin_required
def hapus_user(id):
    # Mencegah Admin menghapus akun yang sedang digunakannya sendiri
    if id == current_user.id:
        return "Error: Tidak dapat menghapus akun yang sedang digunakan.", 400
        
    user = User.query.get_or_404(id)
    db.session.delete(user)
    db.session.commit()
    
    return redirect(url_for('kelola_user'))

if __name__ == '__main__':
    app.run(debug=True)