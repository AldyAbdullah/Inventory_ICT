from app import app, db, User
from werkzeug.security import generate_password_hash

with app.app_context():
    # Cek apakah user admin sudah ada
    admin = User.query.filter_by(username='admin').first()
    hashed_password = generate_password_hash('admin123')
    
    if admin:
        # Jika sudah ada, perbarui password-nya
        admin.password = hashed_password
        print("Password akun 'admin' berhasil di-reset!")
    else:
        # Jika belum ada, buat baru
        admin = User(username='admin', password=hashed_password, role='Admin')
        db.session.add(admin)
        print("Akun 'admin' baru berhasil dibuat!")
        
    db.session.commit()