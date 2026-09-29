import sys
import os

# Mengarahkan Python untuk membaca modul di folder utama
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from main import app
from models import db, User, StatusAset
from werkzeug.security import generate_password_hash

def reset_database():
    with app.app_context():
        print("Menghapus struktur tabel lama...")
        db.drop_all()
        
        print("Membuat struktur tabel baru versi 2.0...")
        db.create_all()

        print("Membuat akun Admin default...")
        admin_user = User(
            payroll='admin123',
            password=generate_password_hash('admin123'),
            role='Admin',
            nama_lengkap='Administrator Sistem',
            jabatan='IT Support'
        )
        db.session.add(admin_user)
        
        print("Membuat Data Master Status Aset...")
        # Status standar IT Asset Management
        status_list = ['Baik', 'Rusak', 'Missing', 'Disposed / Dibuang']
        for s in status_list:
            status_baru = StatusAset(nama_status=s)
            db.session.add(status_baru)

        db.session.commit()
        
        print("-" * 40)
        print("Database berhasil di-reset ke struktur baru!")
        print("Tabel Karyawan, StatusAset, dan Kolom Vendor telah siap.")
        print("-" * 40)

if __name__ == '__main__':
    reset_database()