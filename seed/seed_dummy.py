import sys
import os
from datetime import datetime

# Mengarahkan Python untuk membaca modul di folder utama
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from main import app
from models import db, User, Lokasi, Inventory, Consumable, Karyawan, StatusAset, Transaksi

def jalankan_seeder():
    with app.app_context():
        print("Memulai proses seeding data dummy v2.0...")

        # 1. Ambil data Admin dan Status Aset (sudah dibuat saat reset_db)
        admin = User.query.filter_by(payroll='admin123').first()
        status_baik = StatusAset.query.filter_by(nama_status='Baik').first()
        status_rusak = StatusAset.query.filter_by(nama_status='Rusak').first()

        if not admin or not status_baik:
            print("Error: Harap jalankan 'python seed/reset_db.py' terlebih dahulu!")
            return

        # 2. Buat Data Karyawan (PIC)
        print("Menambahkan data Master Karyawan...")
        karyawan_data = [
            Karyawan(payroll='TM-001', nama='Budi Santoso', status='Aktif'),
            Karyawan(payroll='TM-002', nama='Citra Kirana', status='Aktif'),
            Karyawan(payroll='TM-003', nama='Andi Wijaya', status='Aktif')
        ]
        db.session.add_all(karyawan_data)
        db.session.commit()

        # 3. Buat Data Lokasi
        print("Menambahkan data Area & Lokasi...")
        lokasi_data = [
            Lokasi(main_lokasi='Senoro Field', nama_lokasi='User/Employee', keterangan='Lokasi default untuk aset yang dipegang user'),
            Lokasi(main_lokasi='Senoro Field', nama_lokasi='Server Room', keterangan='Ruang Server Utama Senoro'),
            Lokasi(main_lokasi='Senoro Field', nama_lokasi='IT Warehouse', keterangan='Gudang penyimpanan aset IT'),
            Lokasi(main_lokasi='Luwuk Office', nama_lokasi='Meeting Room', keterangan='Fasilitas kantor operasional')
        ]
        db.session.add_all(lokasi_data)
        db.session.commit()

        # Ambil ID yang baru dibuat untuk dipakai di Inventory
        karyawan_budi = Karyawan.query.filter_by(payroll='TM-001').first()
        karyawan_citra = Karyawan.query.filter_by(payroll='TM-002').first()
        lokasi_user = Lokasi.query.filter_by(nama_lokasi='User/Employee').first()
        lokasi_gudang = Lokasi.query.filter_by(nama_lokasi='IT Warehouse').first()
        lokasi_luwuk = Lokasi.query.filter_by(main_lokasi='Luwuk Office').first()

        # 4. Buat Data Inventory
        print("Menambahkan data Inventory...")
        inventory_list = [
            Inventory(
                kode_barang='INV-0001', nama_barang='Laptop Bisnis', merk='Lenovo', serial_number='LNV-112233',
                kategori='PC/Laptop', unit_type='ThinkPad T14 Gen 2', vendor='PT Lintas Teknologi',
                karyawan_id=karyawan_budi.id, status_id=status_baik.id, lokasi_id=lokasi_user.id
            ),
            Inventory(
                kode_barang='INV-0002', nama_barang='Laptop Bisnis', merk='HP', serial_number='HP-998877',
                kategori='PC/Laptop', unit_type='ProBook 440 G8', vendor='PT Lintas Teknologi',
                karyawan_id=karyawan_citra.id, status_id=status_baik.id, lokasi_id=lokasi_user.id
            ),
            # Contoh ICT ASSET (Tidak ada PIC)
            Inventory(
                kode_barang='INV-0003', nama_barang='Access Point', merk='Cisco', serial_number='CS-555444',
                kategori='Networking', unit_type='Meraki MR46', vendor='PT Jaringan Nusantara',
                karyawan_id=None, status_id=status_baik.id, lokasi_id=lokasi_luwuk.id
            ),
            # Contoh barang rusak di gudang
            Inventory(
                kode_barang='INV-0004', nama_barang='Monitor 24 Inch', merk='Dell', serial_number='DL-000111',
                kategori='Peripheral', unit_type='P2419H', vendor='PT Elektronik Maju',
                karyawan_id=None, status_id=status_rusak.id, lokasi_id=lokasi_gudang.id
            )
        ]
        db.session.add_all(inventory_list)
        db.session.commit()

        # 5. Buat Data Consumable
        print("Menambahkan data Consumable...")
        consumable_list = [
            Consumable(
                kode_barang='CNS-001', nama_barang='Tinta Printer Hitam', kategori='Tinta/Toner',
                unit_type='Epson 003', vendor='Toko Komputer Sentosa', lokasi_id=lokasi_gudang.id, 
                stok=25, satuan='Botol'
            ),
            Consumable(
                kode_barang='CNS-002', nama_barang='Kabel UTP Cat 6', kategori='Networking',
                unit_type='Belden Cat 6', vendor='PT Jaringan Nusantara', lokasi_id=lokasi_gudang.id, 
                stok=5, satuan='Roll'
            )
        ]
        db.session.add_all(consumable_list)
        db.session.commit()

        # 6. Catat Transaksi Awal untuk Inventory & Consumable
        print("Mencatat jejak transaksi...")
        semua_inventory = Inventory.query.all()
        for inv in semua_inventory:
            trx = Transaksi(user_id=admin.id, inventory_id=inv.id, jenis='Masuk', jumlah=1, keterangan='Registrasi Aset Awal (Seeder)')
            db.session.add(trx)

        semua_consumable = Consumable.query.all()
        for cons in semua_consumable:
            trx = Transaksi(user_id=admin.id, consumable_id=cons.id, jenis='Masuk', jumlah=cons.stok, keterangan='Stok Awal Consumable (Seeder)')
            db.session.add(trx)

        db.session.commit()
        print("-" * 40)
        print("SELESAI! Data dummy berhasil dimasukkan ke database.")
        print("-" * 40)

if __name__ == '__main__':
    jalankan_seeder()