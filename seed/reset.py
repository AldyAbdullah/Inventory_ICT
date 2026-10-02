import sys
import os
from werkzeug.security import generate_password_hash

# Tambahkan root direktori ke sistem agar bisa melakukan import dari folder luar
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from main import app
from models import db, User, MainLokasi, SubLokasi, Karyawan, StatusAset, KategoriBarang, SatuanBarang, Inventory, Consumable

def run_seed():
    with app.app_context():
        print("Menghapus database lama dan membuat tabel baru...")
        db.drop_all()
        db.create_all()

        print("Seeding User...")
        admin = User(
            payroll="admin", 
            password=generate_password_hash("admin123"), 
            nama_lengkap="Administrator ICT", 
            jabatan="ICT Support", 
            role="Admin"
        )
        db.session.add(admin)

        print("Seeding Karyawan...")
        karyawan1 = Karyawan(payroll="TM-001", nama="Andi Pratama", status="Aktif")
        karyawan2 = Karyawan(payroll="TM-002", nama="Budi Santoso", status="Aktif")
        karyawan3 = Karyawan(payroll="TM-003", nama="Citra Kirana", status="Aktif")
        db.session.add_all([karyawan1, karyawan2, karyawan3])
        db.session.commit() 

        print("Seeding Master Lokasi...")
        main_cpp = MainLokasi(nama_main="Office CPP", keterangan="Area Perkantoran Central Processing Plant")
        main_senoro = MainLokasi(nama_main="Senoro", keterangan="Area Operasional Senoro")
        main_user = MainLokasi(nama_main="User / Employee", keterangan="Aset yang dipegang langsung oleh Karyawan")
        db.session.add_all([main_cpp, main_senoro, main_user])
        db.session.commit()

        sub_it = SubLokasi(main_lokasi_id=main_cpp.id, nama_sub="Ruang IT / Gudang", keterangan="Gudang penyimpanan ICT")
        sub_meeting = SubLokasi(main_lokasi_id=main_cpp.id, nama_sub="Ruang Meeting Utama", keterangan="Lantai 2")
        sub_control = SubLokasi(main_lokasi_id=main_senoro.id, nama_sub="Control Room", keterangan="Pusat Kendali Senoro")
        # PERBAIKAN: Sub Lokasi untuk User/Employee dijadikan tanda strip (Kosong)
        sub_pic = SubLokasi(main_lokasi_id=main_user.id, nama_sub="-", keterangan="Otomatis (Sistem)")
        db.session.add_all([sub_it, sub_meeting, sub_control, sub_pic])
        db.session.commit()

        print("Seeding Status Aset...")
        # Kita gunakan 4 status utama dalam bahasa Inggris
        status_good = StatusAset(nama_status="Good")
        status_repair = StatusAset(nama_status="In Repair")
        status_broken = StatusAset(nama_status="Broken")
        status_missing = StatusAset(nama_status="Missing")
        db.session.add_all([status_good, status_repair, status_broken, status_missing])
        db.session.commit()

        print("Seeding Kategori & Satuan Barang...")
        kat_laptop = KategoriBarang(nama_kategori="Laptop", jenis="Inventory")
        kat_radio = KategoriBarang(nama_kategori="Radio Komunikasi", jenis="Inventory")
        kat_tinta = KategoriBarang(nama_kategori="Tinta Printer", jenis="Consumable")
        kat_atk = KategoriBarang(nama_kategori="ATK", jenis="Consumable")
        db.session.add_all([kat_laptop, kat_radio, kat_tinta, kat_atk])
        
        sat_unit = SatuanBarang(nama_satuan="Unit")
        sat_pcs = SatuanBarang(nama_satuan="Pcs")
        sat_box = SatuanBarang(nama_satuan="Box")
        db.session.add_all([sat_unit, sat_pcs, sat_box])
        db.session.commit()

        print("Seeding Contoh Inventory...")
        inv_radio = Inventory(kode_barang="INV-RAD-001", nama_barang="Radio Motorola Xir P8668", brand="Motorola", serial_number="MTR-998877", kategori_id=kat_radio.id, unit_type="Xir P8668", lokasi_id=sub_pic.id, karyawan_id=karyawan1.id, karyawan_id_2=karyawan2.id, status_id=status_good.id)
        inv_laptop = Inventory(kode_barang="INV-LPT-001", nama_barang="Laptop Dell Latitude", brand="Dell", serial_number="DELL-112233", kategori_id=kat_laptop.id, unit_type="Latitude 3420", lokasi_id=sub_pic.id, karyawan_id=karyawan3.id, karyawan_id_2=None, status_id=status_good.id)
        inv_router = Inventory(kode_barang="INV-NET-001", nama_barang="Router Mikrotik", brand="Mikrotik", serial_number="MK-554433", kategori_id=kat_radio.id, lokasi_id=sub_it.id, karyawan_id=None, karyawan_id_2=None, status_id=status_good.id)
        db.session.add_all([inv_radio, inv_laptop, inv_router])
        
        print("Seeding Contoh Consumable...")
        cons_tinta = Consumable(kode_barang="CNS-001", nama_barang="Tinta Epson 664 Hitam", brand="Epson", kategori_id=kat_tinta.id, lokasi_id=sub_it.id, satuan_id=sat_pcs.id, stok=15)
        db.session.add(cons_tinta)

        db.session.commit()
        print("=== PROSES SEEDING SELESAI ===")

if __name__ == "__main__":
    run_seed()