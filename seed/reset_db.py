import sys
import os
import random

# Mengarahkan Python untuk membaca modul di folder utama (satu tingkat di atas folder seed)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from main import app
from models import db, User
from werkzeug.security import generate_password_hash

def reset_database():
    with app.app_context():
        print("Menghapus struktur tabel lama...")
        db.drop_all()
        
        print("Membuat struktur tabel baru...")
        db.create_all()

        print("Membuat akun Admin default...")
        admin_user = User(
            username='admin',
            password=generate_password_hash('admin123'),
            role='Admin',
            nama_lengkap='Administrator Sistem'
        )
        db.session.add(admin_user)
        db.session.commit()
        
        print("-" * 30)
        print("Database berhasil direset!")
        print("Gunakan akun berikut untuk login:")
        print("Username : admin")
        print("Password : admin123")
        print("-" * 30)

if __name__ == '__main__':
    reset_database()