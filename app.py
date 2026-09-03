from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# Konfigurasi database SQLite (file akan otomatis dibuat dengan nama ini)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///inventaris_job_tomori.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Inisialisasi Database
db = SQLAlchemy(app)

# Membuat Model/Tabel untuk Barang IT Habis Pakai
class BarangIT(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    kode_barang = db.Column(db.String(20), unique=True, nullable=False)
    nama_barang = db.Column(db.String(100), nullable=False)
    kategori = db.Column(db.String(50), nullable=False) # Contoh: Tinta, Kabel, Jaringan
    stok = db.Column(db.Integer, default=0)
    satuan = db.Column(db.String(20), nullable=False) # Contoh: Botol, Pcs, Roll, Meter

# Membuat tabel di database jika belum ada
with app.app_context():
    db.create_all()

@app.route('/')
def index():
    # Mengambil seluruh data barang dari database
    barang_habis_pakai = BarangIT.query.all()
    return render_template('index.html', data=barang_habis_pakai)

if __name__ == '__main__':
    app.run(debug=True)