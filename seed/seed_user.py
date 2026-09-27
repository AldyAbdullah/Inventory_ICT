from app import app, db, User
from werkzeug.security import generate_password_hash

with app.app_context():
    # Cek apakah user admin sudah ada
    admin_cek = User.query.filter_by(username='admin').first()
    if not admin_cek:
        hashed_password = generate_password_hash('admin123', method='scrypt')
        user_baru = User(username='admin', password=hashed_password, role='Admin')
        db.session.add(user_baru)
        db.session.commit()
        print("Akun default berhasil dibuat! Username: admin, Password: admin123")
    else:
        print("Akun admin sudah ada.")