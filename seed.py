from app import app, db, BarangIT

# Data contoh barang IT di JOB Tomori
data_awal = [
    BarangIT(kode_barang="IT-INK-001", nama_barang="Tinta Epson 664 Hitam", kategori="Tinta Printer", stok=15, satuan="Botol"),
    BarangIT(kode_barang="IT-INK-002", nama_barang="Tinta HP 680 Color", kategori="Cartridge", stok=8, satuan="Pcs"),
    BarangIT(kode_barang="IT-NET-001", nama_barang="Kabel UTP Cat6 Belden", kategori="Jaringan", stok=2, satuan="Roll"),
    BarangIT(kode_barang="IT-NET-002", nama_barang="Konektor RJ45 AMP", kategori="Jaringan", stok=150, satuan="Pcs"),
    BarangIT(kode_barang="IT-PWR-001", nama_barang="Baterai UPS 12V 7Ah", kategori="Power/Listrik", stok=10, satuan="Pcs"),
]

with app.app_context():
    # Tambahkan semua data ke sesi database
    db.session.bulk_save_objects(data_awal)
    # Simpan perubahan
    db.session.commit()
    print("Data awal berhasil ditambahkan ke database!")