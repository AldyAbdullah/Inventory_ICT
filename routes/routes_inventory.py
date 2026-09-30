import io
import pandas as pd
from sqlalchemy import or_
from flask import render_template, request, redirect, url_for, flash, send_file
from flask_login import login_required, current_user

from main import app, admin_required
from models import db, Inventory, Lokasi, Transaksi, Karyawan, StatusAset, KategoriBarang

@app.route('/master_inventory', methods=['GET'])
@login_required
def master_inventory():
    search_query = request.args.get('search', '').strip()
    filter_kategori = request.args.get('kategori', '').strip()
    filter_lokasi = request.args.get('lokasi', '').strip()
    filter_status = request.args.get('status', '').strip()
    page = request.args.get('page', 1, type=int)

    query = Inventory.query

    # 1. Terapkan Filter Aktif ke Tabel Utama (Menggunakan kategori_id)
    if filter_kategori:
        query = query.filter_by(kategori_id=filter_kategori)
    if filter_lokasi:
        query = query.filter_by(lokasi_id=filter_lokasi)
    if filter_status:
        query = query.filter_by(status_id=filter_status)

    if search_query:
        query = query.filter(or_(
            Inventory.kode_barang.ilike(f'%{search_query}%'),
            Inventory.nama_barang.ilike(f'%{search_query}%'),
            Inventory.brand.ilike(f'%{search_query}%'),
            Inventory.serial_number.ilike(f'%{search_query}%'),
            Inventory.karyawan_terkait.has(Karyawan.nama.ilike(f'%{search_query}%')),
            Inventory.karyawan_terkait.has(Karyawan.payroll.ilike(f'%{search_query}%'))
        ))

    data = query.order_by(Inventory.id.desc()).paginate(page=page, per_page=10, error_out=False)

    # === LOGIKA CASCADING FILTER ===
    base_query = Inventory.query
    
    # Dropdown 1: Kategori
    kategori_list = KategoriBarang.query.filter_by(jenis='Inventory').order_by(KategoriBarang.nama_kategori.asc()).all()

    # Dropdown 2: Lokasi
    lok_q = base_query
    if filter_kategori: lok_q = lok_q.filter_by(kategori_id=filter_kategori)
    if filter_status: lok_q = lok_q.filter_by(status_id=filter_status)
    lokasi_ids = [l[0] for l in lok_q.with_entities(Inventory.lokasi_id).distinct().filter(Inventory.lokasi_id != None).all()]
    lokasi_list = Lokasi.query.filter(Lokasi.id.in_(lokasi_ids)).all() if lokasi_ids else []

    # Dropdown 3: Status
    stat_q = base_query
    if filter_kategori: stat_q = stat_q.filter_by(kategori_id=filter_kategori)
    if filter_lokasi: stat_q = stat_q.filter_by(lokasi_id=filter_lokasi)
    status_ids = [s[0] for s in stat_q.with_entities(Inventory.status_id).distinct().filter(Inventory.status_id != None).all()]
    status_list = StatusAset.query.filter(StatusAset.id.in_(status_ids)).all() if status_ids else []

    # === PERHITUNGAN UNTUK KARTU WIDGET ===
    all_inventory = Inventory.query.all()
    total_aset = len(all_inventory)
    
    total_baik = total_dipinjamkan = total_rusak = total_missing = total_dibuang = 0
    
    for item in all_inventory:
        if item.karyawan_id:
            total_dipinjamkan += 1
        if item.status_terkait:
            st = item.status_terkait.nama_status.lower()
            if 'baik' in st: total_baik += 1
            elif 'hilang' in st or 'missing' in st: total_missing += 1
            elif 'disposal' in st or 'dibuang' in st: total_dibuang += 1
            elif 'rusak' in st: total_rusak += 1
                
    pct_baik = round((total_baik / total_aset * 100), 1) if total_aset > 0 else 0
    pct_dipinjamkan = round((total_dipinjamkan / total_aset * 100), 1) if total_aset > 0 else 0
    pct_rusak = round((total_rusak / total_aset * 100), 1) if total_aset > 0 else 0
    pct_missing = round((total_missing / total_aset * 100), 1) if total_aset > 0 else 0
    pct_dibuang = round((total_dibuang / total_aset * 100), 1) if total_aset > 0 else 0

    return render_template('inventory/master.html', 
                           data=data,
                           search_query=search_query,
                           filter_kategori=filter_kategori,
                           filter_lokasi=filter_lokasi,
                           filter_status=filter_status,
                           kategori_list=kategori_list,
                           lokasi_list=lokasi_list,
                           status_list=status_list,
                           total_aset=total_aset,
                           total_baik=total_baik, pct_baik=pct_baik,
                           total_dipinjamkan=total_dipinjamkan, pct_dipinjamkan=pct_dipinjamkan,
                           total_rusak=total_rusak, pct_rusak=pct_rusak,
                           total_missing=total_missing, pct_missing=pct_missing,
                           total_dibuang=total_dibuang, pct_dibuang=pct_dibuang)

@app.route('/tambah_inventory', methods=['GET', 'POST'])
@login_required
@admin_required
def tambah_inventory():
    if request.method == 'POST':
        kode_barang = request.form.get('kode_barang', '').strip()
        if not kode_barang:
            flash('Gagal! Kode Barang wajib diisi.', 'danger')
            return redirect(url_for('tambah_inventory'))

        serial_number = request.form.get('serial_number', '').strip()
        nama_barang = request.form.get('nama_barang', '').strip()
        brand = request.form.get('brand', '').strip()
        vendor = request.form.get('vendor', '').strip()
        
        kategori_id_raw = request.form.get('kategori_id')
        kategori_id = int(kategori_id_raw) if kategori_id_raw and kategori_id_raw.isdigit() else None
        
        unit_type = request.form.get('unit_type', '').strip()
        karyawan_id = request.form.get('karyawan_id') or None
        status_id = request.form.get('status_id') or None
        lokasi_id = request.form.get('lokasi_id') or None
        
        keterangan_tambahan = request.form.get('keterangan', '').strip()

        cek_sn = Inventory.query.filter_by(serial_number=serial_number, brand=brand).first()
        if cek_sn:
            flash(f'Gagal! Serial Number "{serial_number}" dengan Brand "{brand}" sudah digunakan barang lain.', 'danger')
            return redirect(url_for('tambah_inventory'))

        if Inventory.query.filter_by(kode_barang=kode_barang).first():
            flash(f'Gagal! Kode Barang "{kode_barang}" sudah ada di sistem.', 'danger')
            return redirect(url_for('tambah_inventory'))

        if karyawan_id:
            lokasi_user = Lokasi.query.filter_by(main_lokasi='Senoro Field', nama_lokasi='User/Employee').first()
            if not lokasi_user:
                lokasi_user = Lokasi(main_lokasi='Senoro Field', nama_lokasi='User/Employee')
                db.session.add(lokasi_user)
                db.session.flush()
            lokasi_id = lokasi_user.id

        barang_baru = Inventory(
            kode_barang=kode_barang,
            serial_number=serial_number,
            nama_barang=nama_barang,
            brand=brand,
            vendor=vendor,
            kategori_id=kategori_id,
            unit_type=unit_type,
            karyawan_id=karyawan_id,
            status_id=status_id,
            lokasi_id=lokasi_id
        )
        db.session.add(barang_baru)
        db.session.flush()

        if karyawan_id:
            karyawan = Karyawan.query.get(karyawan_id)
            ket_awal = f"PIC: {karyawan.nama} (Payroll: {karyawan.payroll})"
        elif lokasi_id:
            lok = Lokasi.query.get(lokasi_id)
            ket_awal = f"Lokasi: {lok.main_lokasi} - {lok.nama_lokasi}"
        else:
            ket_awal = "Belum Dialokasikan"

        if keterangan_tambahan:
            ket_awal += f" | Catatan: {keterangan_tambahan}"

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
        # PERBAIKAN: Redirect ke halaman tambah agar form bersih kembali dan memunculkan notif
        return redirect(url_for('tambah_inventory'))

    return render_template('inventory/tambah.html',
                           karyawan_list=Karyawan.query.filter_by(status='Aktif').order_by(Karyawan.nama.asc()).all(),
                           lokasi_list=Lokasi.query.all(),
                           status_list=StatusAset.query.all(),
                           kategori_list=KategoriBarang.query.filter_by(jenis='Inventory').order_by(KategoriBarang.nama_kategori.asc()).all())

@app.route('/edit_inventory/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_inventory(id):
    barang = Inventory.query.get_or_404(id)

    if request.method == 'POST':
        new_kode = request.form.get('kode_barang', '').strip()
        serial_number_baru = request.form.get('serial_number', '').strip()
        brand_baru = request.form.get('brand', '').strip()
        
        if not new_kode:
            flash('Gagal! Kode Barang wajib diisi.', 'danger')
            return redirect(url_for('edit_inventory', id=id))
            
        cek_kode = Inventory.query.filter(Inventory.id != id, Inventory.kode_barang == new_kode).first()
        if cek_kode:
            flash(f'Gagal! Kode Barang "{new_kode}" sudah dipakai aset lain.', 'danger')
            return redirect(url_for('edit_inventory', id=id))

        cek_sn = Inventory.query.filter(Inventory.id != id, Inventory.serial_number == serial_number_baru, Inventory.brand == brand_baru).first()
        if cek_sn:
            flash(f'Gagal! Serial Number "{serial_number_baru}" dengan Brand "{brand_baru}" sudah digunakan barang lain.', 'danger')
            return redirect(url_for('edit_inventory', id=id))

        old_kode = barang.kode_barang or 'Kosong'
        old_nama = barang.nama_barang or 'Kosong'
        old_brand = barang.brand or 'Kosong'
        old_sn = barang.serial_number or 'Kosong'
        old_tipe = barang.unit_type or 'Kosong'
        old_vendor = barang.vendor or 'Kosong'
        old_kategori_id = barang.kategori_id
        old_status_id = barang.status_id
        old_pic_id = barang.karyawan_id
        old_lokasi_id = barang.lokasi_id

        new_nama = request.form.get('nama_barang', '').strip() or 'Kosong'
        new_brand = brand_baru or 'Kosong'
        new_sn = serial_number_baru or 'Kosong'
        new_tipe = request.form.get('unit_type', '').strip() or 'Kosong'
        new_vendor = request.form.get('vendor', '').strip() or 'Kosong'
        
        kat_id_raw = request.form.get('kategori_id')
        new_kategori_id = int(kat_id_raw) if kat_id_raw and kat_id_raw.isdigit() else None
        
        status_id_raw = request.form.get('status_id')
        new_status_id = int(status_id_raw) if status_id_raw and status_id_raw.isdigit() else None
        
        pic_id_raw = request.form.get('karyawan_id')
        new_pic_id = int(pic_id_raw) if pic_id_raw and pic_id_raw.isdigit() else None
        
        lok_id_raw = request.form.get('lokasi_id')
        new_lokasi_id = int(lok_id_raw) if lok_id_raw and lok_id_raw.isdigit() else None
        
        keterangan_tambahan = request.form.get('keterangan', '').strip()

        if new_pic_id:
            lokasi_user = Lokasi.query.filter_by(main_lokasi='Senoro Field', nama_lokasi='User/Employee').first()
            if not lokasi_user:
                lokasi_user = Lokasi(main_lokasi='Senoro Field', nama_lokasi='User/Employee')
                db.session.add(lokasi_user)
                db.session.flush()
            new_lokasi_id = lokasi_user.id

        perubahan_edit = []
        if old_kode != new_kode: perubahan_edit.append(f"Kode ({old_kode} -> {new_kode})")
        if old_nama != new_nama: perubahan_edit.append(f"Nama ({old_nama} -> {new_nama})")
        if old_brand != new_brand: perubahan_edit.append(f"Brand ({old_brand} -> {new_brand})")
        if old_sn != new_sn: perubahan_edit.append(f"SN ({old_sn} -> {new_sn})")
        if old_tipe != new_tipe: perubahan_edit.append(f"Tipe ({old_tipe} -> {new_tipe})")
        if old_vendor != new_vendor: perubahan_edit.append(f"Vendor ({old_vendor} -> {new_vendor})")
        
        if old_kategori_id != new_kategori_id:
            old_kat_nama = barang.kategori_terkait.nama_kategori if barang.kategori_terkait else "Kosong"
            new_kat_obj = KategoriBarang.query.get(new_kategori_id) if new_kategori_id else None
            new_kat_nama = new_kat_obj.nama_kategori if new_kat_obj else "Kosong"
            perubahan_edit.append(f"Kategori ({old_kat_nama} -> {new_kat_nama})")

        if old_status_id != new_status_id:
            old_stat_nama = barang.status_terkait.nama_status if barang.status_terkait else "Kosong"
            new_stat_obj = StatusAset.query.get(new_status_id) if new_status_id else None
            new_stat_nama = new_stat_obj.nama_status if new_stat_obj else "Kosong"
            perubahan_edit.append(f"Status ({old_stat_nama} -> {new_stat_nama})")

        barang.kode_barang = new_kode if new_kode != 'Kosong' else ''
        barang.nama_barang = new_nama if new_nama != 'Kosong' else ''
        barang.brand = new_brand if new_brand != 'Kosong' else ''
        barang.serial_number = new_sn if new_sn != 'Kosong' else ''
        barang.unit_type = new_tipe if new_tipe != 'Kosong' else ''
        barang.vendor = new_vendor if new_vendor != 'Kosong' else ''
        barang.kategori_id = new_kategori_id
        barang.status_id = new_status_id
        barang.karyawan_id = new_pic_id
        barang.lokasi_id = new_lokasi_id

        if perubahan_edit or keterangan_tambahan:
            keterangan_edit = "Edit: " + ", ".join(perubahan_edit) if perubahan_edit else "Edit Data Tambahan"
            if keterangan_tambahan:
                keterangan_edit += f" | Catatan: {keterangan_tambahan}"
            db.session.add(Transaksi(user_id=current_user.id, inventory_id=barang.id, jenis='Edit', jumlah=1, keterangan=keterangan_edit))

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
            
            if keterangan_tambahan:
                ket_mutasi += f" | Catatan: {keterangan_tambahan}"
                
            db.session.add(Transaksi(user_id=current_user.id, inventory_id=barang.id, jenis='Mutasi', jumlah=1, keterangan=ket_mutasi))

        db.session.commit()
        flash('Data Inventory berhasil diperbarui.', 'success')
        # PERBAIKAN: Redirect ke halaman edit yang sama agar memunculkan data & riwayat baru beserta notif
        return redirect(url_for('edit_inventory', id=id))
        
    riwayat_barang = Transaksi.query.filter_by(inventory_id=id).order_by(Transaksi.tanggal.desc()).all()
        
    return render_template('inventory/edit.html', 
                           barang=barang, 
                           riwayat=riwayat_barang,
                           lokasi_list=Lokasi.query.all(),
                           karyawan_list=Karyawan.query.filter_by(status='Aktif').order_by(Karyawan.nama.asc()).all(),
                           status_list=StatusAset.query.all(),
                           kategori_list=KategoriBarang.query.filter_by(jenis='Inventory').order_by(KategoriBarang.nama_kategori.asc()).all())

@app.route('/export_inventory')
@login_required
@admin_required
def export_inventory():
    search = request.args.get('search', '').strip()
    filter_kategori = request.args.get('kategori', '').strip()
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
    if filter_kategori: query = query.filter(Inventory.kategori_id == filter_kategori)
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
            'Kategori': item.kategori_terkait.nama_kategori if item.kategori_id and item.kategori_terkait else '-',
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
    
    return send_file(
        output, 
        download_name="Laporan_Data_Inventory.xlsx", 
        as_attachment=True,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

@app.route('/export_riwayat_inventory')
@login_required
@admin_required
def export_riwayat_inventory():
    search = request.args.get('search', '').strip()
    start_date = request.args.get('start_date', '').strip()
    end_date = request.args.get('end_date', '').strip()
    
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
    
    return send_file(
        output, 
        download_name="Laporan_Riwayat_Inventory.xlsx", 
        as_attachment=True,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )