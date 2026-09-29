from datetime import datetime, timedelta
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()

def waktu_lokal():
    return datetime.utcnow() + timedelta(hours=8)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    payroll = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    nama_lengkap = db.Column(db.String(100))
    jabatan = db.Column(db.String(100))
    role = db.Column(db.String(20), default='Viewer')

class Lokasi(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    main_lokasi = db.Column(db.String(100), nullable=False)
    nama_lokasi = db.Column(db.String(100), nullable=False)
    keterangan = db.Column(db.Text)
    inventories = db.relationship('Inventory', backref='lokasi', lazy=True)
    consumables = db.relationship('Consumable', backref='lokasi', lazy=True)

# TABEL BARU: Master Karyawan
class Karyawan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    payroll = db.Column(db.String(50), unique=True, nullable=False)
    nama = db.Column(db.String(150), nullable=False)
    status = db.Column(db.String(50), default='Aktif') # Aktif / Tidak Aktif
    inventories = db.relationship('Inventory', backref='karyawan_terkait', lazy=True)

# TABEL BARU: Master Status Aset
class StatusAset(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nama_status = db.Column(db.String(50), unique=True, nullable=False)
    inventories = db.relationship('Inventory', backref='status_terkait', lazy=True)

class Inventory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    kode_barang = db.Column(db.String(50), unique=True, nullable=False)
    nama_barang = db.Column(db.String(150), nullable=False)
    brand = db.Column(db.String(100)) # Kolom Baru
    serial_number = db.Column(db.String(100), nullable=False) # Aturan 'unique=True' telah dihapus
    kategori = db.Column(db.String(50))
    unit_type = db.Column(db.String(100))
    vendor = db.Column(db.String(100)) # Kolom Baru
    lokasi_id = db.Column(db.Integer, db.ForeignKey('lokasi.id'))
    karyawan_id = db.Column(db.Integer, db.ForeignKey('karyawan.id'), nullable=True) # Relasi ke Karyawan
    status_id = db.Column(db.Integer, db.ForeignKey('status_aset.id'), nullable=True) # Relasi ke StatusAset
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=waktu_lokal)

class Consumable(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    kode_barang = db.Column(db.String(50), unique=True, nullable=False)
    nama_barang = db.Column(db.String(150), nullable=False)
    kategori = db.Column(db.String(50))
    unit_type = db.Column(db.String(100))
    brand = db.Column(db.String(100))
    vendor = db.Column(db.String(100))
    lokasi_id = db.Column(db.Integer, db.ForeignKey('lokasi.id'))
    stok = db.Column(db.Integer, default=0)
    satuan = db.Column(db.String(20))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=waktu_lokal)

class Transaksi(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tanggal = db.Column(db.DateTime, default=waktu_lokal)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    inventory_id = db.Column(db.Integer, db.ForeignKey('inventory.id'), nullable=True)
    consumable_id = db.Column(db.Integer, db.ForeignKey('consumable.id'), nullable=True)
    jenis = db.Column(db.String(20), nullable=False)
    jumlah = db.Column(db.Integer, nullable=False, default=1)
    keterangan = db.Column(db.String(255))
    
    user = db.relationship('User', backref='transaksi', lazy=True)
    inventory = db.relationship('Inventory', backref='transaksi_item', lazy=True)
    consumable = db.relationship('Consumable', backref='transaksi_item', lazy=True)