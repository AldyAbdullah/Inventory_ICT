from datetime import datetime, timedelta
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()

def waktu_lokal():
    return datetime.utcnow() + timedelta(hours=8)

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    nama_lengkap = db.Column(db.String(100))
    transaksi = db.relationship('Transaksi', backref='user', lazy=True)

class Lokasi(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    main_lokasi = db.Column(db.String(100), nullable=False)
    nama_lokasi = db.Column(db.String(100), nullable=False)
    keterangan = db.Column(db.Text)
    inventories = db.relationship('Inventory', backref='lokasi', lazy=True)
    consumables = db.relationship('Consumable', backref='lokasi', lazy=True)

class Inventory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    kode_barang = db.Column(db.String(50), unique=True, nullable=False)
    nama_barang = db.Column(db.String(150), nullable=False)
    serial_number = db.Column(db.String(100), unique=True, nullable=False)
    kategori = db.Column(db.String(50))
    unit_type = db.Column(db.String(100))
    lokasi_id = db.Column(db.Integer, db.ForeignKey('lokasi.id'))
    notes = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=waktu_lokal) # Diseragamkan
    transaksi = db.relationship('Transaksi', backref='inventory_item', lazy=True)

class Consumable(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    kode_barang = db.Column(db.String(50), unique=True, nullable=False)
    nama_barang = db.Column(db.String(150), nullable=False)
    kategori = db.Column(db.String(50))
    unit_type = db.Column(db.String(100))
    lokasi_id = db.Column(db.Integer, db.ForeignKey('lokasi.id'))
    stok = db.Column(db.Integer, default=0)
    satuan = db.Column(db.String(20))
    notes = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=waktu_lokal) # Diseragamkan
    transaksi = db.relationship('Transaksi', backref='consumable_item', lazy=True)

class Transaksi(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tanggal = db.Column(db.DateTime, default=waktu_lokal) # Sudah seragam
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    inventory_id = db.Column(db.Integer, db.ForeignKey('inventory.id'), nullable=True)
    consumable_id = db.Column(db.Integer, db.ForeignKey('consumable.id'), nullable=True)
    jenis = db.Column(db.String(20), nullable=False)
    jumlah = db.Column(db.Integer, nullable=False, default=1)
    keterangan = db.Column(db.String(200))
    
    inventory = db.relationship('Inventory', backref='transaksi_terkait', lazy=True)
    consumable = db.relationship('Consumable', backref='transaksi_terkait', lazy=True)