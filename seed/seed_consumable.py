import sys
import os
import random

# Mengarahkan Python untuk membaca modul di folder utama (satu tingkat di atas folder seed)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from main import app
from models import db, Consumable, Transaksi, Lokasi  # Sesuaikan dengan model yang dibutuhkan

def jalankan_seeder_consumable():
# ... (lanjutan kode tetap sama seperti sebelumnya) ...
    with app.app_context():
        # Memastikan data lokasi sudah ada
        lokasi_list = Lokasi.query.all()
        if not lokasi_list:
            print("Gagal: Data Lokasi kosong. Silakan jalankan seed_inventory.py terlebih dahulu.")
            return

        kategori_opsi = ["ATK", "Tinta & Toner", "Kabel & Konektor", "Aksesoris IT"]
        tipe_opsi = {
            "ATK": ["Kertas HVS A4 80gr", "Pulpen Faster Hitam", "Buku Catatan", "Isi Staples", "Lakban Hitam"],
            "Tinta & Toner": ["Toner HP 85A", "Tinta Epson 003 Black", "Tinta Epson 003 Color", "Toner Brother TN-1000"],
            "Kabel & Konektor": ["Kabel UTP Cat6 (Roll)", "Konektor RJ45 (Box)", "Kabel Power PC", "Kabel HDMI 2m"],
            "Aksesoris IT": ["Mouse Wireless", "Flashdisk 32GB", "Baterai CMOS", "Keyboard Standar USB"]
        }
        satuan_opsi = {
            "ATK": ["Rim", "Pack", "Kotak", "Pcs", "Roll"],
            "Tinta & Toner": ["Botol", "Catridge"],
            "Kabel & Konektor": ["Roll", "Box", "Pcs"],
            "Aksesoris IT": ["Unit", "Pcs"]
        }

        # Menghindari bentrok ID kode barang dummy
        start_id = random.randint(100, 900)
        
        print("Memulai proses seeding data Consumable...")

        for i in range(1, 31): # Kita buat 30 data barang habis pakai
            kategori = random.choice(kategori_opsi)
            tipe = random.choice(tipe_opsi[kategori])
            nama_barang = f"{tipe} (Merek {chr(random.randint(65, 90))})"
            kode_barang = f"CNS-DUMMY-{start_id + i}"
            
            # Lewati jika kebetulan kodenya sama
            if Consumable.query.filter_by(kode_barang=kode_barang).first():
                continue
                
            stok_awal = random.randint(5, 100) # Variasi stok awal antara 5 hingga 100
            satuan = random.choice(satuan_opsi[kategori])

            # 1. Masukkan data ke tabel Consumable
            barang_baru = Consumable(
                kode_barang=kode_barang,
                nama_barang=nama_barang,
                kategori=kategori,
                unit_type=tipe,
                lokasi_id=random.choice(lokasi_list).id,
                stok=stok_awal,
                satuan=satuan,
                notes="Stok awal dari seeder"
            )
            db.session.add(barang_baru)
            db.session.flush() # Dapatkan ID sebelum lanjut

            # 2. Catat otomatis ke tabel Transaksi sebagai barang Masuk
            transaksi_baru = Transaksi(
                user_id=1, # Menggunakan ID Admin default
                consumable_id=barang_baru.id,
                jenis='Masuk',
                jumlah=stok_awal,
                keterangan='Stok Awal Dummy (Seeder)'
            )
            db.session.add(transaksi_baru)

        db.session.commit()
        print("Berhasil! 30 data Consumable dummy telah ditambahkan ke database.")

if __name__ == '__main__':
    jalankan_seeder_consumable()