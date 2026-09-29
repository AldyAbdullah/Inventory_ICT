import io
import pandas as pd
from sqlalchemy import or_
from flask import render_template, request, redirect, url_for, flash, send_file
from flask_login import login_required, current_user

# Import dari file lokal proyek Anda (Sesuai dengan struktur asli Anda)
from main import app, admin_required
from models import db, Inventory, Lokasi, Transaksi, Karyawan, StatusAset


@app.route('/master_inventory', methods=['GET'])
@login_required
def master_inventory():
    search_query = request.args.get('search', '').strip()
    filter_kategori = request.args.get('kategori', '').strip()
    filter_tipe = request.args.get('tipe', '').strip()
    filter_lokasi = request.args.get('lokasi', '').strip()
    filter_status = request.args.get('status', '').strip()
    page = request.args.get('page', 1, type=int)

    query = Inventory.query

    # Pencarian Universal
    if search_query:
        query = query.filter(or_(
            Inventory.kode_barang.ilike(f'%{search_query}%'),
            Inventory.nama_barang.ilike(f'%{search_query}%'),
            Inventory.brand.ilike(f'%{search_query}%'),
            Inventory.serial_number.ilike(f'%{search_query}%'),
            Inventory.karyawan_terkait.has(Karyawan.nama.ilike(f'%{search_query}%')),
            Inventory.karyawan_terkait.has(Karyawan.payroll.ilike(f'%{search_query}%'))
        ))
    
    # Filter Berdasarkan Dropdown
    if filter_kategori:
        query = query.filter_by(kategori=filter_kategori)
    if filter_tipe:
        query = query.filter_by(unit_type=filter_tipe)
    if filter_lokasi:
        query = query.filter_by(lokasi_id=filter_lokasi)
    if filter_status:
        query = query.filter_by(status_id=filter_status)

    # Paginasi (10 data per halaman)
    data = query.order_by(Inventory.id.desc()).paginate(page=page, per_page=10, error_out=False)

    # Menyiapkan data unik untuk dropdown filter
    kategori_list = [k[0] for k in db.session.query(Inventory.kategori).distinct().filter(Inventory.kategori != None, Inventory.kategori != '').all()]
    tipe_list = [t[0] for t in db.session.query(Inventory.unit_type).distinct().filter(Inventory.unit_type != None, Inventory.unit_type != '').all()]
    lokasi_list = Lokasi.query.all()
    status_list = StatusAset.query.all()

    return render_template('inventory/master.html', 
                           data=data,
                           search_query=search_query,
                           filter_kategori=filter_kategori,
                           filter_tipe=filter_tipe,
                           filter_lokasi=filter_lokasi,
                           filter_status=filter_status,
                           kategori_list=kategori_list,
                           tipe_list=tipe_list,
                           lokasi_list=lokasi_list,
                           status_list=status_list)

@app.route('/tambah_inventory', methods=['GET', 'POST'])
@login_required
@admin_required
def tambah_inventory():
    if request.method == 'POST':
        kode_barang = request.form.get('kode_barang', '').strip()
        serial_number = request.form.get('serial_number', '').strip()
        nama_barang = request.form.get('nama_barang', '').strip()
        brand = request.form.get('brand', '').strip()
        vendor = request.form.get('vendor', '').strip()
        kategori = request.form.get('kategori', '').strip()
        unit_type = request.form.get('unit_type', '').strip()
        
        karyawan_id = request.form.get('karyawan_id') or None
        status_id = request.form.get('status_id') or None
        lokasi_id = request.form.get('lokasi_id') or None

        # Cek duplikasi Serial Number dan Brand
        cek_sn = Inventory.query.filter_by(serial_number=serial_number, brand=brand).first()
        if cek_sn:
            flash(f'Gagal! Serial Number "{serial_number}" dengan Brand "{brand}" sudah digunakan barang lain.', 'danger')
            return redirect(url_for('tambah_inventory'))

        # Penomoran otomatis jika kode_barang kosong
        if not kode_barang:
            last_item = Inventory.query.order_by(Inventory.id.desc()).first()
            if last_item and last_item.kode_barang and last_item.kode_barang.startswith('INV-'):
                try:
                    last_num = int(last_item.kode_barang.split('-')[1])
                    kode_barang = f'INV-{last_num + 1:04d}'
                except ValueError:
                    kode_barang = 'INV-0001'
            else:
                kode_barang = 'INV-0001'

        # Otomatisasi Lokasi jika Karyawan dipilih
        if karyawan_id:
            lokasi_user = Lokasi.query.filter_by(main_lokasi='Senoro Field', nama_lokasi='User/Employee').first()
            if not lokasi_user:
                lokasi_user = Lokasi(main_lokasi='Senoro Field', nama_lokasi='User/Employee')
                db.session.add(lokasi_user)
                db.session.flush()
            lokasi_id = lokasi_user.id

        # Simpan ke pangkalan data
        barang_baru = Inventory(
            kode_barang=kode_barang,
            serial_number=serial_number,
            nama_barang=nama_barang,
            brand=brand,
            vendor=vendor,
            kategori=kategori,
            unit_type=unit_type,
            karyawan_id=karyawan_id,
            status_id=status_id,
            lokasi_id=lokasi_id
        )
        db.session.add(barang_baru)
        db.session.flush()

        # Buat teks riwayat lokasi/PIC awal otomatis
        if karyawan_id:
            karyawan = Karyawan.query.get(karyawan_id)
            ket_awal = f"PIC: {karyawan.nama} (Payroll: {karyawan.payroll})"
        elif lokasi_id:
            lok = Lokasi.query.get(lokasi_id)
            ket_awal = f"Lokasi: {lok.main_lokasi} - {lok.nama_lokasi}"
        else:
            ket_awal = "Belum Dialokasikan"

        # Catat Riwayat Transaksi Masuk
        transaksi = Transaksi(
            user_id=current_user.id,
            inventory_id=barang_baru.id,
            jenis='Masuk',
            jumlah=1,
            keterangan=ket_awal
        )
        db.session.add(transaksi)
        db.session.commit()

        flash('Aset baru berhasil ditambahkan ke dalam sistem.', 'success')
        return redirect(url_for('master_inventory'))

    karyawan_list = Karyawan.query.filter_by(status='Aktif').order_by(Karyawan.nama.asc()).all()
    lokasi_list = Lokasi.query.all()
    status_list = StatusAset.query.all()
    
    return render_template('inventory/tambah.html',
                           karyawan_list=karyawan_list,
                           lokasi_list=lokasi_list,
                           status_list=status_list)

@app.route('/edit_inventory/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_inventory(id):
    barang = Inventory.query.get_or_404(id)

    if request.method == 'POST':
        # 1. Ambil data dari form
        serial_number_baru = request.form.get('serial_number', '').strip()
        brand_baru = request.form.get('brand', '').strip()
        
        # Validasi duplikasi SN & Brand
        cek_sn = Inventory.query.filter(Inventory.id != id, Inventory.serial_number == serial_number_baru, Inventory.brand == brand_baru).first()
        if cek_sn:
            flash(f'Gagal! Serial Number "{serial_number_baru}" dengan Brand "{brand_baru}" sudah digunakan barang lain.', 'danger')
            return redirect(url_for('edit_inventory', id=id))

        # 2. Tangkap data lama SEBELUM diubah (Untuk pelacakan Edit & Mutasi)
        old_nama = barang.nama_barang
        old_brand = barang.brand or ''
        old_sn = barang.serial_number
        old_kategori = barang.kategori or ''
        old_tipe = barang.unit_type or ''
        old_vendor = barang.vendor or ''
        old_status_id = barang.status_id
        
        old_pic_id = barang.karyawan_id
        old_lokasi_id = barang.lokasi_id

        # 3. Tangkap data baru dari form
        new_nama = request.form.get('nama_barang', '').strip()
        new_kategori = request.form.get('kategori', '').strip()
        new_tipe = request.form.get('unit_type', '').strip()
        new_vendor = request.form.get('vendor', '').strip()
        
        status_id_raw = request.form.get('status_id')
        new_status_id = int(status_id_raw) if status_id_raw and status_id_raw.isdigit() else None
        
        pic_id_raw = request.form.get('karyawan_id')
        new_pic_id = int(pic_id_raw) if pic_id_raw and pic_id_raw.isdigit() else None
        
        lok_id_raw = request.form.get('lokasi_id')
        new_lokasi_id = int(lok_id_raw) if lok_id_raw and lok_id_raw.isdigit() else None
        
        # Otomatisasi Lokasi Karyawan
        if new_pic_id:
            lokasi_user = Lokasi.query.filter_by(main_lokasi='Senoro Field', nama_lokasi='User/Employee').first()
            if not lokasi_user:
                lokasi_user = Lokasi(main_lokasi='Senoro Field', nama_lokasi='User/Employee')
                db.session.add(lokasi_user)
                db.session.flush()
            new_lokasi_id = lokasi_user.id

        # 4. Deteksi Kolom Apa Saja Yang Diedit (Kecuali Mutasi Lokasi/PIC)
        perubahan_edit = []
        if old_nama != new_nama: perubahan_edit.append("Nama Perangkat")
        if old_brand != brand_baru: perubahan_edit.append("Brand")
        if old_sn != serial_number_baru: perubahan_edit.append("Serial Number")
        if old_kategori != new_kategori: perubahan_edit.append("Kategori")
        if old_tipe != new_tipe: perubahan_edit.append("Tipe Unit")
        if old_vendor != new_vendor: perubahan_edit.append("Vendor")
        if old_status_id != new_status_id:
            status_obj = StatusAset.query.get(new_status_id) if new_status_id else None
            nama_status_baru = status_obj.nama_status if status_obj else "Kosong"
            perubahan_edit.append(f"Status ({nama_status_baru})")

        # 5. Terapkan pembaruan ke objek barang
        barang.kode_barang = request.form.get('kode_barang', '').strip()
        barang.nama_barang = new_nama
        barang.brand = brand_baru
        barang.serial_number = serial_number_baru
        barang.kategori = new_kategori
        barang.unit_type = new_tipe
        barang.vendor = new_vendor
        barang.status_id = new_status_id
        barang.karyawan_id = new_pic_id
        barang.lokasi_id = new_lokasi_id

        # 6. Catat Jejak Riwayat (Edit Spesifikasi)
        if perubahan_edit:
            keterangan_edit = "Edit data: " + ", ".join(perubahan_edit)
            db.session.add(Transaksi(user_id=current_user.id, inventory_id=barang.id, jenis='Edit', jumlah=1, keterangan=keterangan_edit))

        # 7. Catat Jejak Riwayat (Mutasi) JIKA ADA PERUBAHAN LOKASI/PIC
        if old_pic_id != new_pic_id or old_lokasi_id != new_lokasi_id:
            ket_mutasi = ""
            if new_pic_id:
                karyawan = Karyawan.query.get(new_pic_id)
                ket_mutasi = f"PIC Baru: {karyawan.nama} (Payroll: {karyawan.payroll})" if karyawan else "PIC Baru Ditetapkan"
            elif new_lokasi_id:
                lok = Lokasi.query.get(new_lokasi_id)
                ket_mutasi = f"Pindah ke: {lok.main_lokasi} - {lok.nama_lokasi}" if lok else "Pindah Lokasi"
            else:
                ket_mutasi = "Ditarik ke Gudang / Belum Dialokasikan"
                
            db.session.add(Transaksi(user_id=current_user.id, inventory_id=barang.id, jenis='Mutasi', jumlah=1, keterangan=ket_mutasi))

        db.session.commit()
        flash('Data Inventory berhasil diperbarui.', 'success')
        return redirect(url_for('master_inventory'))
        
    # Menampilkan SEMUA riwayat (termasuk Edit) khusus di halaman jejak aset ini
    riwayat_barang = Transaksi.query.filter_by(inventory_id=id).order_by(Transaksi.tanggal.desc()).all()
        
    return render_template('inventory/edit.html', 
                           barang=barang, 
                           riwayat=riwayat_barang,
                           lokasi_list=Lokasi.query.all(),
                           karyawan_list=Karyawan.query.filter_by(status='Aktif').order_by(Karyawan.nama.asc()).all(),
                           status_list=StatusAset.query.all())

@app.route('/export_inventory')
@login_required
@admin_required
def export_inventory():
    search = request.args.get('search', '').strip()
    filter_kategori = request.args.get('kategori', '').strip()
    filter_tipe = request.args.get('tipe', '').strip()
    filter_lokasi = request.args.get('lokasi', '').strip()
    filter_status = request.args.get('status', '').strip()
    
    query = Inventory.query.filter_by(is_active=True)
    
    if search:
        query = query.filter(or_(
            Inventory.nama_barang.ilike(f"%{search}%"), 
            Inventory.kode_barang.ilike(f"%{search}%"),
            Inventory.serial_number.ilike(f"%{search}%"),
            Inventory.brand.ilike(f"%{search}%")
        ))
    if filter_kategori: query = query.filter(Inventory.kategori == filter_kategori)
    if filter_tipe: query = query.filter(Inventory.unit_type == filter_tipe)
    if filter_lokasi: query = query.filter(Inventory.lokasi_id == filter_lokasi)
    if filter_status: query = query.filter(Inventory.status_id == filter_status)
        
    items = query.order_by(Inventory.id.asc()).all()

    data = []
    for i, item in enumerate(items, 1):
        if item.karyawan_id and item.karyawan_terkait:
            payroll = item.karyawan_terkait.payroll or "-"
            full_name = item.karyawan_terkait.nama or "-"
        else:
            payroll = "-"
            full_name = "ICT ASSET"
            
        data.append({
            'No': i,
            'Kode Aset': item.kode_barang or '-',
            'Payroll': payroll,
            'Full Name': full_name,
            'Nama Perangkat': item.nama_barang or '-',
            'Brand': item.brand or '-',
            'Serial Number': item.serial_number or '-',
            'Kategori': item.kategori or '-',
            'Tipe Unit': item.unit_type or '-',
            'Vendor': item.vendor or '-',
            'Main Location': item.lokasi.main_lokasi if item.lokasi else 'Belum Dialokasikan',
            'Sub Location': item.lokasi.nama_lokasi if item.lokasi else '-',
            'Status Aset': item.status_terkait.nama_status if item.status_id and item.status_terkait else 'Tanpa Status'
        })
        
    df = pd.DataFrame(data)
    output = io.BytesIO()
    
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Inventory Data')
        workbook = writer.book
        worksheet = writer.sheets['Inventory Data']
        
        header_format = workbook.add_format({
            'bold': True, 'valign': 'vcenter', 'align': 'center',
            'fg_color': '#D3D3D3', 'border': 1
        })
        cell_format = workbook.add_format({'valign': 'vcenter', 'border': 1})
        center_format = workbook.add_format({'valign': 'vcenter', 'align': 'center', 'border': 1})
        
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, header_format)
            
        for idx, col_name in enumerate(df.columns):
            max_len = max(df[col_name].astype(str).map(len).max(), len(col_name)) + 3
            worksheet.set_column(idx, idx, max_len)
            
            for row_idx in range(len(df)):
                val = df.iloc[row_idx, idx]
                if col_name in ['No', 'Kode Aset', 'Payroll', 'Status Aset']:
                    worksheet.write(row_idx + 1, idx, val, center_format)
                else:
                    worksheet.write(row_idx + 1, idx, val, cell_format)

    output.seek(0)
    return send_file(output, download_name="Laporan_Data_Inventory.xlsx", as_attachment=True)

@app.route('/export_riwayat_inventory')
@login_required
@admin_required
def export_riwayat_inventory():
    search = request.args.get('search', '').strip()
    start_date = request.args.get('start_date', '').strip()
    end_date = request.args.get('end_date', '').strip()
    
    # Hanya ambil riwayat Mutasi dan Masuk (Tolak 'Edit')
    query = Transaksi.query.filter(Transaksi.inventory_id != None, Transaksi.jenis != 'Edit')
    
    if search:
        query = query.join(Inventory).filter(or_(
            Inventory.nama_barang.ilike(f"%{search}%"),
            Inventory.serial_number.ilike(f"%{search}%"),
            Inventory.kode_barang.ilike(f"%{search}%"),
            Transaksi.keterangan.ilike(f"%{search}%")
        ))
        
    if start_date: 
        query = query.filter(Transaksi.tanggal >= f"{start_date} 00:00:00")
    if end_date: 
        query = query.filter(Transaksi.tanggal <= f"{end_date} 23:59:59")
        
    items = query.order_by(Transaksi.tanggal.desc()).all()

    data = []
    for i, item in enumerate(items, 1):
        pic_name = 'Sistem'
        if item.user:
            pic_name = item.user.nama_lengkap.split(' ')[0] if item.user.nama_lengkap else item.user.payroll
            
        data.append({
            'No': i,
            'Tanggal': item.tanggal.strftime('%Y-%m-%d %H:%M:%S') if item.tanggal else "-",
            'Kode Aset': item.inventory.kode_barang if item.inventory else '-',
            'Serial Number': item.inventory.serial_number if item.inventory else '-',
            'Nama Perangkat': item.inventory.nama_barang if item.inventory else 'Aset Dihapus',
            'Jenis Transaksi': item.jenis,
            'Lokasi & Penugasan': item.keterangan or '-',
            'Operator Sistem': pic_name
        })
        
    df = pd.DataFrame(data)
    output = io.BytesIO()
    
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Riwayat Mutasi Inventory')
        workbook = writer.book
        worksheet = writer.sheets['Riwayat Mutasi Inventory']
        
        header_format = workbook.add_format({
            'bold': True, 'valign': 'vcenter', 'align': 'center',
            'fg_color': '#D3D3D3', 'border': 1
        })
        cell_format = workbook.add_format({'valign': 'vcenter', 'border': 1})
        center_format = workbook.add_format({'valign': 'vcenter', 'align': 'center', 'border': 1})
        
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, header_format)
            
        for idx, col_name in enumerate(df.columns):
            max_len = max(df[col_name].astype(str).map(len).max(), len(col_name)) + 3
            worksheet.set_column(idx, idx, max_len)
            
            for row_idx in range(len(df)):
                val = df.iloc[row_idx, idx]
                if col_name in ['No', 'Tanggal', 'Kode Aset', 'Jenis Transaksi', 'Operator Sistem']:
                    worksheet.write(row_idx + 1, idx, val, center_format)
                else:
                    worksheet.write(row_idx + 1, idx, val, cell_format)

    output.seek(0)
    return send_file(output, download_name="Laporan_Riwayat_Inventory.xlsx", as_attachment=True)