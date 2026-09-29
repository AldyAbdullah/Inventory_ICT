import sys
import os
import random

# Mengarahkan Python untuk membaca modul di folder utama (satu tingkat di atas folder seed)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from main import app
from models import db, User, Karyawan, Lokasi, StatusAset, Inventory, Consumable, Transaksi
from werkzeug.security import generate_password_hash

def reset_and_seed():
    with app.app_context():
        print("1. Menghapus pangkalan data lama...")
        db.drop_all()
        
        print("2. Membuat ulang struktur tabel...")
        db.create_all()

        print("3. Membuat akun Admin...")
        admin = User(
            payroll="admin",
            nama_lengkap="Administrator ICT",
            password=generate_password_hash("admin123"),
            role="Admin"
        )
        db.session.add(admin)

        print("4. Mengisi tabel Lokasi Gudang/Area...")
        lokasi_data = [
            Lokasi(main_lokasi="Senoro Field", nama_lokasi="IT Warehouse"),
            Lokasi(main_lokasi="Senoro Field", nama_lokasi="User/Employee"),
            Lokasi(main_lokasi="Senoro Field", nama_lokasi="Server Room"),
            Lokasi(main_lokasi="Luwuk Office", nama_lokasi="IT Warehouse"),
            Lokasi(main_lokasi="Luwuk Office", nama_lokasi="Meeting Room"),
        ]
        db.session.add_all(lokasi_data)

        print("5. Mengisi tabel Status Aset...")
        status_data = [
            StatusAset(nama_status="Baik"),
            StatusAset(nama_status="Rusak (Perbaikan)"),
            StatusAset(nama_status="Rusak (Disposal)"),
            StatusAset(nama_status="Hilang"),
        ]
        db.session.add_all(status_data)

        print("6. Mengisi tabel Data Karyawan (PIC)...")
        karyawan_data = [
            Karyawan(payroll="TM-001", nama="Budi Santoso", status="Aktif"),
            Karyawan(payroll="TM-002", nama="Citra Kirana", status="Aktif"),
            Karyawan(payroll="TM-003", nama="Andi Pratama", status="Aktif"),
        ]
        db.session.add_all(karyawan_data)
        
        # Simpan sesi sementara agar ID dari Lokasi, Status, dan Karyawan bisa digunakan
        db.session.commit()

        print("7. Mengisi tabel Master Inventory...")
        inventory_data = [
            Inventory(
                kode_barang="INV-0001", serial_number="LNV-112233", nama_barang="Laptop Bisnis",
                brand="Lenovo", vendor="PT Lintas Teknologi", kategori="PC/Laptop", unit_type="ThinkPad T14 Gen 2",
                karyawan_id=1, status_id=1, lokasi_id=2
            ),
            Inventory(
                kode_barang="INV-0002", serial_number="HP-998877", nama_barang="Laptop Operasional",
                brand="HP", vendor="PT Lintas Teknologi", kategori="PC/Laptop", unit_type="ProBook 440 G8",
                karyawan_id=2, status_id=1, lokasi_id=2
            ),
            Inventory(
                kode_barang="INV-0003", serial_number="CS-555444", nama_barang="Access Point Wireless",
                brand="Cisco", vendor="PT Jaringan Nusantara", kategori="Networking", unit_type="Meraki MR46",
                karyawan_id=None, status_id=1, lokasi_id=5
            )
        ]
        db.session.add_all(inventory_data)

        print("8. Mengisi tabel Consumable...")
        consumable_data = [
            Consumable(
                kode_barang="CNS-0001", nama_barang="Kertas HVS A4 80gr", brand="PaperOne", vendor="CV Mulia",
                kategori="ATK", unit_type="-", stok=50, satuan="Rim", lokasi_id=1
            ),
            Consumable(
                kode_barang="CNS-0002", nama_barang="Kabel UTP Cat 6", brand="Belden", vendor="PT Jaringan Nusantara",
                kategori="Networking", unit_type="Roll 305m", stok=5, satuan="Roll", lokasi_id=1
            ),
            Consumable(
                kode_barang="CNS-0003", nama_barang="Tinta Printer Hitam", brand="Epson", vendor="CV Mulia",
                kategori="Tinta/Toner", unit_type="003 Black", stok=15, satuan="Botol", lokasi_id=4
            )
        ]
        db.session.add_all(consumable_data)
        db.session.commit()

        print("9. Membuat Riwayat Transaksi (Jejak Audit)...")
        # Riwayat Inventory Masuk
        transaksi_data = []
        for inv in Inventory.query.all():
            transaksi_data.append(Transaksi(
                user_id=1, inventory_id=inv.id, jenis='Masuk', jumlah=1,
                keterangan=f"PIC: {inv.karyawan_terkait.nama} (Payroll: {inv.karyawan_terkait.payroll})" if inv.karyawan_id else f"Lokasi: {inv.lokasi.main_lokasi} - {inv.lokasi.nama_lokasi}"
            ))
            
        # Riwayat Consumable Masuk
        for cns in Consumable.query.all():
            transaksi_data.append(Transaksi(
                user_id=1, consumable_id=cns.id, jenis='Masuk', jumlah=cns.stok,
                keterangan=f"Lokasi: {cns.lokasi.main_lokasi} - {cns.lokasi.nama_lokasi}" if cns.lokasi_id else "Belum Dialokasikan"
            ))
            
        db.session.add_all(transaksi_data)
        db.session.commit()

        print("=================================================")
        print("Selesai! Database berhasil direset dan diisi data.")
        print("Gunakan akun berikut untuk masuk:")
        print("Payroll  : admin")
        print("Password : admin123")
        print("=================================================")

if __name__ == "__main__":
    reset_and_seed()