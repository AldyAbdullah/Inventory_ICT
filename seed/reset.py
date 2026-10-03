import sys
import os
import random
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from main import app
from models import db, User, MainLokasi, SubLokasi, Karyawan, StatusAset, KategoriBarang, SatuanBarang, Inventory, Consumable, Transaksi

def run_seed():
    with app.app_context():
        print("Menghapus database lama dan membuat tabel baru...")
        db.drop_all()
        db.create_all()

        print("Seeding Administrator...")
        admin = User(
            payroll="200505", 
            password=generate_password_hash("12345678"), 
            nama_lengkap="Aldi Abdullah", 
            jabatan="ICT Support", 
            role="Admin"
        )
        user2 = User(
            payroll="staff_it",
            password=generate_password_hash("staff123"),
            nama_lengkap="Staff ICT",
            jabatan="IT Staff",
            role="User"
        )
        db.session.add_all([admin, user2])

        print("Seeding Karyawan (PIC)...")
        karyawans = []
        nama_karyawan = ["Andi Pratama", "Budi Santoso", "Citra Kirana", "Dian Sastro", "Eko Yulianto", "Fahri Hamzah", "Gita Gutawa", "Hendra Setiawan", "Irfan Hakim", "Joko Anwar"]
        for i, nama in enumerate(nama_karyawan, 1):
            kr = Karyawan(payroll=f"TM-{i:03d}", nama=nama, status="Aktif")
            karyawans.append(kr)
        db.session.add_all(karyawans)
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
        sub_pic = SubLokasi(main_lokasi_id=main_user.id, nama_sub="-", keterangan="Otomatis (Sistem)")
        db.session.add_all([sub_it, sub_meeting, sub_control, sub_pic])
        db.session.commit()
        
        lokasi_gudang = [sub_it.id, sub_meeting.id, sub_control.id]

        print("Seeding Status Aset...")
        status_good = StatusAset(nama_status="Good")
        status_repair = StatusAset(nama_status="In Repair")
        status_broken = StatusAset(nama_status="Broken")
        status_missing = StatusAset(nama_status="Missing")
        db.session.add_all([status_good, status_repair, status_broken, status_missing])
        db.session.commit()
        
        status_pilihan = [status_good.id, status_repair.id, status_broken.id]

        print("Seeding Kategori & Satuan Barang...")
        kat_inv = [
            KategoriBarang(nama_kategori="Laptop", jenis="Inventory"),
            KategoriBarang(nama_kategori="Radio Komunikasi", jenis="Inventory"),
            KategoriBarang(nama_kategori="Router / Switch", jenis="Inventory"),
            KategoriBarang(nama_kategori="Printer", jenis="Inventory"),
            KategoriBarang(nama_kategori="CCTV", jenis="Inventory")
        ]
        
        kat_cons = [
            KategoriBarang(nama_kategori="Tinta Printer", jenis="Consumable"),
            KategoriBarang(nama_kategori="Alat Tulis Kantor (ATK)", jenis="Consumable"),
            KategoriBarang(nama_kategori="Kabel & Kelistrikan", jenis="Consumable"),
            KategoriBarang(nama_kategori="Sparepart IT", jenis="Consumable")
        ]
        db.session.add_all(kat_inv + kat_cons)
        
        satuans = [
            SatuanBarang(nama_satuan="Unit"),
            SatuanBarang(nama_satuan="Pcs"),
            SatuanBarang(nama_satuan="Box"),
            SatuanBarang(nama_satuan="Roll"),
            SatuanBarang(nama_satuan="Pack")
        ]
        db.session.add_all(satuans)
        db.session.commit()

        # ==========================================
        # SEEDING 40 DATA INVENTORY
        # ==========================================
        print("Membangkitkan 40 Data Inventory...")
        inventory_list = []
        brand_inv = ["Dell", "Lenovo", "HP", "Cisco", "Mikrotik", "Motorola", "Epson", "Hikvision"]
        
        for i in range(1, 41):
            kategori_terpilih = random.choice(kat_inv)
            brand_terpilih = random.choice(brand_inv)
            is_assigned = random.choice([True, False])
            
            lok_id = sub_pic.id if is_assigned else random.choice(lokasi_gudang)
            karyawan1 = random.choice(karyawans).id if is_assigned else None
            karyawan2 = random.choice(karyawans).id if is_assigned and random.random() < 0.3 else None
            stat_id = status_good.id if random.random() < 0.8 else random.choice(status_pilihan)

            inv = Inventory(
                kode_barang=f"INV-{datetime.now().strftime('%y%m')}-{i:03d}",
                nama_barang=f"{kategori_terpilih.nama_kategori} {brand_terpilih} Seri-{random.randint(100, 999)}",
                brand=brand_terpilih,
                serial_number=f"SN-{brand_terpilih[:3].upper()}-{random.randint(10000, 99999)}",
                kategori_id=kategori_terpilih.id,
                unit_type=f"Model {random.choice(['X', 'Z', 'Pro', 'Max'])}-{random.randint(10, 99)}",
                lokasi_id=lok_id,
                karyawan_id=karyawan1,
                karyawan_id_2=karyawan2,
                status_id=stat_id,
                vendor=random.choice(["PT IT Indah", "Bhinneka", "Maju Jaya", None]),
                is_active=True
            )
            inventory_list.append(inv)
            
        db.session.add_all(inventory_list)
        db.session.commit()

        # ==========================================
        # SEEDING 40 DATA CONSUMABLE
        # ==========================================
        print("Membangkitkan 40 Data Consumable...")
        consumable_list = []
        nama_cons_dasar = ["Tinta Epson", "Kertas HVS A4", "Kabel UTP Cat6", "Konektor RJ45", "Mouse Wireless", "Keyboard USB", "Flashdisk 32GB", "Baterai AA", "Toner Printer", "Isolasi Listrik"]
        
        for i in range(1, 41):
            kat_terpilih = random.choice(kat_cons)
            nama_barang = random.choice(nama_cons_dasar)
            stok_awal = random.randint(2, 50)
            
            cons = Consumable(
                kode_barang=f"CNS-{datetime.now().strftime('%y%m')}-{i:03d}",
                nama_barang=f"{nama_barang} Variasi {i}",
                brand=random.choice(["Logitech", "Epson", "Belden", "PaperOne", "Alkaline", "Standard", None]),
                vendor=random.choice(["Toko Sukses", "Gudang ATK", "PT Elektro", None]),
                kategori_id=kat_terpilih.id,
                unit_type=random.choice(["Original", "OEM", "Standard", "Premium", ""]),
                lokasi_id=random.choice(lokasi_gudang),
                stok=stok_awal,
                satuan_id=random.choice(satuans).id,
                is_active=True
            )
            consumable_list.append(cons)
            
        db.session.add_all(consumable_list)
        db.session.commit()

        # ==========================================
        # SEEDING 20 TRANSAKSI INVENTORY (DIPERBAIKI)
        # ==========================================
        print("Membangkitkan 20 Riwayat Transaksi Inventory...")
        transaksi_inv = []
        for _ in range(20):
            inv_terpilih = random.choice(inventory_list)
            jenis = random.choice(['Deliver', 'Retrieval', 'Mutasi'])
            waktu_acak = datetime.now() - timedelta(days=random.randint(1, 30), hours=random.randint(1, 12))
            
            kar = random.choice(karyawans)
            lok = random.choice([sub_it, sub_meeting, sub_control])
            
            # SINKRONISASI DATABASE & FORMAT TEKS AGAR FITUR CETAK BERFUNGSI
            if jenis == 'Deliver':
                ket = f"Diserahkan ke PIC: {kar.nama} | Catatan: Penugasan Baru dari Seed"
                
                # Update status wujud asli inventory agar sinkron dengan riwayat Deliver
                inv_terpilih.karyawan_id = kar.id
                inv_terpilih.karyawan_id_2 = None
                inv_terpilih.lokasi_id = sub_pic.id
                
            elif jenis == 'Retrieval':
                ket = f"Dari: {kar.nama} | NIP: {kar.payroll} | ke {lok.main.nama_main} - {lok.nama_sub}"
                
                # Update status wujud asli inventory agar sinkron (kosong dari PIC, ditaruh di Gudang)
                inv_terpilih.karyawan_id = None
                inv_terpilih.karyawan_id_2 = None
                inv_terpilih.lokasi_id = lok.id
                
            else: # Mutasi
                ket = f"Pindah Lokasi ke: {lok.main.nama_main} - {lok.nama_sub}"
                
                # Update wujud lokasi fisik di database
                inv_terpilih.lokasi_id = lok.id
                
            trx = Transaksi(
                inventory_id=inv_terpilih.id,
                user_id=admin.id,
                jenis=jenis,
                jumlah=1,
                keterangan=ket,
                tanggal=waktu_acak
            )
            transaksi_inv.append(trx)
        
        db.session.add_all(transaksi_inv)

        # ==========================================
        # SEEDING 20 TRANSAKSI CONSUMABLE
        # ==========================================
        print("Membangkitkan 20 Riwayat Transaksi Consumable...")
        transaksi_cons = []
        for _ in range(20):
            cons_terpilih = random.choice(consumable_list)
            jenis = random.choice(['Masuk', 'Keluar'])
            jumlah_trx = random.randint(1, 5)
            waktu_acak = datetime.now() - timedelta(days=random.randint(1, 30), hours=random.randint(1, 12))
            
            if jenis == 'Keluar':
                ket = f"Catatan: Diambil oleh tim {random.choice(['Drilling', 'Production', 'HSE', 'Maintenance'])}"
            else:
                ket = "Catatan: Restock barang bulanan"
                
            trx = Transaksi(
                consumable_id=cons_terpilih.id,
                user_id=admin.id,
                jenis=jenis,
                jumlah=jumlah_trx,
                keterangan=ket,
                tanggal=waktu_acak
            )
            transaksi_cons.append(trx)
            
        db.session.add_all(transaksi_cons)
        db.session.commit()

        print("=== PROSES SEEDING 100+ DATA SELESAI DENGAN SUKSES ===")
        print("Silakan Login dengan:")
        print("Payroll: 200505")
        print("Password: 12345678")

if __name__ == "__main__":
    run_seed()