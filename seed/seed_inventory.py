import sys
import os
import random

# Mengarahkan Python untuk membaca modul di folder utama (satu tingkat di atas folder seed)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from main import app
from models import db, Inventory, Transaksi, Lokasi
import random

def jalankan_seeder():
    with app.app_context():
        # Cek dan buat data lokasi default jika kosong (karena database baru direset)
        lokasi_list = Lokasi.query.all()
        if not lokasi_list:
            print("Data Lokasi kosong. Membuat lokasi dummy otomatis...")
            lokasi_baru = [
                Lokasi(main_lokasi="Head Office", nama_lokasi="Ruang Server"),
                Lokasi(main_lokasi="Head Office", nama_lokasi="Gudang IT"),
                Lokasi(main_lokasi="Site", nama_lokasi="Pos Jaga 1")
            ]
            db.session.add_all(lokasi_baru)
            db.session.commit()
            lokasi_list = Lokasi.query.all() # Ambil ulang data lokasi yang baru dibuat

        kategori_opsi = ["PC/Laptop", "Perangkat Jaringan", "Perangkat Cetak", "Komunikasi", "Server & Storage"]
        tipe_opsi = {
            "PC/Laptop": ["ThinkPad T14 Gen 2", "Dell Latitude 5420", "HP EliteBook"],
            "Perangkat Jaringan": ["Cisco Meraki MR46", "MikroTik RB750Gr3", "Aruba Switch 2930F"],
            "Perangkat Cetak": ["Epson EcoTank L3110", "HP LaserJet Pro", "Brother MFC"],
            "Komunikasi": ["Radio HT Motorola GP338", "IP Phone Yealink T46U"],
            "Server & Storage": ["Dell PowerEdge R740", "NAS Synology RS1221+"]
        }
        status_opsi = ["Kondisi baik, operasional", "Unit baru", "Spare/Cadangan", "Perlu maintenance", ""]

        start_id = random.randint(100, 900)

        for i in range(1, 51):
            kategori = random.choice(kategori_opsi)
            tipe = random.choice(tipe_opsi[kategori])
            nama_barang = f"{tipe} (Aset {i})"
            kode_barang = f"INV-DUMMY-{start_id + i}"
            serial_number = f"SN-{random.randint(1000,9999)}-TMRI-{i:03d}"
            
            # Hindari duplikasi jika kode/SN kebetulan sama
            if Inventory.query.filter_by(kode_barang=kode_barang).first():
                continue

            # 1. Masukkan data ke tabel Inventory
            barang_baru = Inventory(
                kode_barang=kode_barang,
                nama_barang=nama_barang,
                serial_number=serial_number,
                kategori=kategori,
                unit_type=tipe,
                lokasi_id=random.choice(lokasi_list).id,
                notes=random.choice(status_opsi)
            )
            db.session.add(barang_baru)
            db.session.flush()

            # 2. Catat otomatis ke tabel Transaksi
            transaksi_baru = Transaksi(
                user_id=1, 
                inventory_id=barang_baru.id,
                jenis='Masuk',
                jumlah=1,
                keterangan='Registrasi Aset Dummy (Seeder)'
            )
            db.session.add(transaksi_baru)

        db.session.commit()
        print(f"Berhasil! 50 data inventory dummy telah ditambahkan ke database.")

if __name__ == '__main__':
    jalankan_seeder()