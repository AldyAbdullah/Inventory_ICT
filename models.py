from datetime import datetime, timedelta
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
import uuid

db = SQLAlchemy()

def waktu_lokal():
    return datetime.utcnow() + timedelta(hours=8)

def generate_grup_id():
    # Fungsi pembantu untuk membuat ID unik sebagai pengikat Bundling (Inventory + Consumable)
    return str(uuid.uuid4())

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    payroll = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    nama_lengkap = db.Column(db.String(100))
    jabatan = db.Column(db.String(100))
    role = db.Column(db.String(20), default='Viewer')
    
    # FITUR BARU: Merekam waktu terakhir login
    last_login = db.Column(db.DateTime, nullable=True)

class MainLokasi(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nama_main = db.Column(db.String(100), nullable=False, unique=True)
    keterangan = db.Column(db.Text)
    sub_lokasi = db.relationship('SubLokasi', backref='main', lazy=True, cascade="all, delete-orphan")

class SubLokasi(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    main_lokasi_id = db.Column(db.Integer, db.ForeignKey('main_lokasi.id'), nullable=False)
    nama_sub = db.Column(db.String(100), nullable=False)
    keterangan = db.Column(db.Text)
    inventories = db.relationship('Inventory', backref='lokasi', lazy=True)
    consumables = db.relationship('Consumable', backref='lokasi', lazy=True)

class Karyawan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    payroll = db.Column(db.String(50), unique=True, nullable=False)
    nama = db.Column(db.String(150), nullable=False)
    status = db.Column(db.String(50), default='Aktif') 
    
    # FITUR BARU: Properti untuk menghitung otomatis total aset aktif yang dipegang
    @property
    def total_aset_aktif(self):
        # Hitung aset sebagai PIC 1
        pic1_count = len([aset for aset in self.aset_pic_1 if aset.is_active])
        # Hitung aset sebagai PIC 2
        pic2_count = len([aset for aset in self.aset_pic_2 if aset.is_active])
        return pic1_count + pic2_count

class StatusAset(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nama_status = db.Column(db.String(50), unique=True, nullable=False)
    inventories = db.relationship('Inventory', backref='status_terkait', lazy=True)

class Inventory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    kode_barang = db.Column(db.String(50), unique=True, nullable=False)
    nama_barang = db.Column(db.String(150), nullable=False)
    brand = db.Column(db.String(100)) 
    serial_number = db.Column(db.String(100), nullable=False) 
    
    kategori_id = db.Column(db.Integer, db.ForeignKey('kategori_barang.id'), nullable=True)
    kategori_terkait = db.relationship('KategoriBarang', backref='inventories', lazy=True)
    
    unit_type = db.Column(db.String(100))
    vendor = db.Column(db.String(100)) 
    
    lokasi_id = db.Column(db.Integer, db.ForeignKey('sub_lokasi.id'))
    
    karyawan_id = db.Column(db.Integer, db.ForeignKey('karyawan.id'), nullable=True)   
    karyawan_id_2 = db.Column(db.Integer, db.ForeignKey('karyawan.id'), nullable=True) 
    
    pic_1 = db.relationship('Karyawan', foreign_keys=[karyawan_id], backref='aset_pic_1', lazy=True)
    pic_2 = db.relationship('Karyawan', foreign_keys=[karyawan_id_2], backref='aset_pic_2', lazy=True)
    
    status_id = db.Column(db.Integer, db.ForeignKey('status_aset.id'), nullable=True) 
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=waktu_lokal)

class KategoriBarang(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nama_kategori = db.Column(db.String(100), nullable=False)
    jenis = db.Column(db.String(50), nullable=False) 

class SatuanBarang(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nama_satuan = db.Column(db.String(50), unique=True, nullable=False)

class Consumable(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    kode_barang = db.Column(db.String(50), unique=True, nullable=False)
    nama_barang = db.Column(db.String(150), nullable=False)
    
    kategori_id = db.Column(db.Integer, db.ForeignKey('kategori_barang.id'), nullable=True)
    kategori_terkait = db.relationship('KategoriBarang', backref='consumables', lazy=True)
    
    unit_type = db.Column(db.String(100))
    brand = db.Column(db.String(100))
    vendor = db.Column(db.String(100))
    
    lokasi_id = db.Column(db.Integer, db.ForeignKey('sub_lokasi.id'))
    
    stok = db.Column(db.Integer, default=0)
    
    satuan_id = db.Column(db.Integer, db.ForeignKey('satuan_barang.id'), nullable=True)
    satuan_terkait = db.relationship('SatuanBarang', backref='consumables', lazy=True)
    
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=waktu_lokal)

class Transaksi(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tanggal = db.Column(db.DateTime, default=waktu_lokal)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    inventory_id = db.Column(db.Integer, db.ForeignKey('inventory.id'), nullable=True)
    consumable_id = db.Column(db.Integer, db.ForeignKey('consumable.id'), nullable=True)
    
    grup_id = db.Column(db.String(100), nullable=True)
    
    jenis = db.Column(db.String(20), nullable=False)
    jumlah = db.Column(db.Integer, nullable=False, default=1)
    keterangan = db.Column(db.String(255))
    
    user = db.relationship('User', backref='transaksi_user', lazy=True)
    inventory = db.relationship('Inventory', backref='riwayat_mutasi', lazy=True)
    consumable = db.relationship('Consumable', backref='riwayat_mutasi', lazy=True)