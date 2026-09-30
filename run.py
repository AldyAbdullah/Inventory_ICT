import os
from main import app, db

with app.app_context():
    db.create_all()
    print("Database baru beserta tabel-tabelnya berhasil diciptakan!")

if __name__ == '__main__':
    # Mengambil pengaturan debug dari file .env (jika ada), default-nya False
    debug_mode = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    # Menyalakan server
    app.run(host='0.0.0.0', port=5000, debug=debug_mode)