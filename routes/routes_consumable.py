import io
import pandas as pd
from flask import render_template, request, redirect, url_for, flash, send_file
from flask_login import login_required, current_user
from sqlalchemy import or_

from main import app, admin_required
from models import db, Consumable, Transaksi, MainLokasi, SubLokasi, KategoriBarang, SatuanBarang

@app.route('/consumable')
@login_required
def master_consumable():
    search = request.args.get('search', '').strip()
    filter_kategori = request.args.get('kategori', '').strip()
    filter_stok = request.args.get('stok', '').strip()
    filter_lokasi = request.args.get('lokasi', '').strip()
    
    query = Consumable.query.filter_by(is_active=True)
    
    if search: 
        query = query.filter(or_(
            Consumable.nama_barang.ilike(f"%{search}%"), 
            Consumable.kode_barang.ilike(f"%{search}%"),
            Consumable.brand.ilike(f"%{search}%"),
            Consumable.vendor.ilike(f"%{search}%")
        ))
    
    if filter_kategori: query = query.filter(Consumable.kategori_id == filter_kategori)
    if filter_lokasi: query = query.filter(Consumable.lokasi_id == filter_lokasi)
    
    if filter_stok == 'sedikit':
        query = query.filter(Consumable.stok <= 5)
    elif filter_stok == 'banyak':
        query = query.filter(Consumable.stok > 5)
        
    kategori_list = KategoriBarang.query.filter_by(jenis='Consumable').order_by(KategoriBarang.nama_kategori.asc()).all()
    lokasi_list = SubLokasi.query.join(MainLokasi).order_by(MainLokasi.nama_main.asc(), SubLokasi.nama_sub.asc()).all()
    
    data = query.order_by(Consumable.id.desc()).all()
    
    return render_template('consumable/master.html', data=data, search_query=search, filter_kategori=filter_kategori, filter_stok=filter_stok, filter_lokasi=filter_lokasi, kategori_list=kategori_list, lokasi_list=lokasi_list)

@app.route('/tambah_consumable', methods=['GET', 'POST'])
@login_required
@admin_required
def tambah_consumable():
    if request.method == 'POST':
        kode_barang = request.form.get('kode_barang', '').strip()
        stok = int(request.form.get('stok', 0))
        keterangan_tambahan = request.form.get('keterangan', '').strip()
        
        kategori_id_raw = request.form.get('kategori_id')
        kategori_id = int(kategori_id_raw) if kategori_id_raw and kategori_id_raw.isdigit() else None
        
        satuan_id_raw = request.form.get('satuan_id')
        satuan_id = int(satuan_id_raw) if satuan_id_raw and satuan_id_raw.isdigit() else None
        
        lok_id_raw = request.form.get('lokasi_id')
        lokasi_id = int(lok_id_raw) if lok_id_raw and lok_id_raw.isdigit() else None

        if not kode_barang:
            flash('Gagal! Kode Barang wajib diisi manual.', 'danger')
            return redirect(url_for('tambah_consumable'))
        
        if Consumable.query.filter_by(kode_barang=kode_barang).first():
            flash(f'Gagal! Kode Barang "{kode_barang}" sudah terdaftar di sistem.', 'danger')
            return redirect(url_for('tambah_consumable'))
            
        if stok < 0:
            flash('Gagal! Stok awal tidak boleh bernilai minus.', 'danger')
            return redirect(url_for('tambah_consumable'))
            
        barang_baru = Consumable(
            kode_barang=kode_barang, 
            nama_barang=request.form.get('nama_barang', '').strip(), 
            brand=request.form.get('brand', '').strip(),
            vendor=request.form.get('vendor', '').strip(),
            kategori_id=kategori_id,
            unit_type=request.form.get('unit_type', '').strip(), 
            lokasi_id=lokasi_id, 
            stok=stok, 
            satuan_id=satuan_id
        )
        db.session.add(barang_baru)
        db.session.flush()
        
        if stok > 0: 
            ket_awal = "Stok Awal Registrasi"
            if lokasi_id:
               lok = SubLokasi.query.get(lokasi_id)
               if lok and lok.main:
                   ket_awal += f" | Lokasi: {lok.main.nama_main} - {lok.nama_sub}"
               else:
                   ket_awal += f" | Lokasi: {lok.nama_sub}" if lok else " | Lokasi Tidak Diketahui"
            
            if keterangan_tambahan:
                ket_awal += f" | Catatan: {keterangan_tambahan}"
                
            db.session.add(Transaksi(user_id=current_user.id, consumable_id=barang_baru.id, jenis='Masuk', jumlah=stok, keterangan=ket_awal))
        
        db.session.commit()
        flash('Barang Consumable berhasil ditambahkan.', 'success')
        return redirect(url_for('tambah_consumable'))
        
    return render_template('consumable/tambah.html', 
                           main_lokasi_list=MainLokasi.query.order_by(MainLokasi.nama_main.asc()).all(),
                           sub_lokasi_list=SubLokasi.query.join(MainLokasi).order_by(MainLokasi.nama_main.asc(), SubLokasi.nama_sub.asc()).all(),
                           kategori_list=KategoriBarang.query.filter_by(jenis='Consumable').order_by(KategoriBarang.nama_kategori.asc()).all(),
                           satuan_list=SatuanBarang.query.order_by(SatuanBarang.nama_satuan.asc()).all())

@app.route('/edit_consumable/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_consumable(id):
    barang = Consumable.query.get_or_404(id)
    if request.method == 'POST':
        new_kode = request.form.get('kode_barang', '').strip()
        
        if not new_kode:
            flash('Gagal! Kode Barang wajib diisi.', 'danger')
            return redirect(url_for('edit_consumable', id=id))
            
        if Consumable.query.filter(Consumable.id != id, Consumable.kode_barang == new_kode).first():
            flash(f'Gagal! Kode Barang "{new_kode}" sudah dipakai item lain.', 'danger')
            return redirect(url_for('edit_consumable', id=id))

        old_kode = barang.kode_barang
        old_nama = barang.nama_barang
        old_brand = barang.brand or 'Kosong'
        old_vendor = barang.vendor or 'Kosong'
        old_kategori_id = barang.kategori_id
        old_tipe = barang.unit_type or 'Kosong'
        old_lokasi_id = barang.lokasi_id
        old_satuan_id = barang.satuan_id
        old_stok = barang.stok

        new_nama = request.form.get('nama_barang', '').strip()
        new_brand = request.form.get('brand', '').strip() or 'Kosong'
        new_vendor = request.form.get('vendor', '').strip() or 'Kosong'
        new_tipe = request.form.get('unit_type', '').strip() or 'Kosong'
        new_stok = int(request.form.get('stok', 0))
        keterangan_tambahan = request.form.get('keterangan', '').strip()
        
        kat_id_raw = request.form.get('kategori_id')
        new_kategori_id = int(kat_id_raw) if kat_id_raw and kat_id_raw.isdigit() else None
        
        sat_id_raw = request.form.get('satuan_id')
        new_satuan_id = int(sat_id_raw) if sat_id_raw and sat_id_raw.isdigit() else None
        
        lok_id_raw = request.form.get('lokasi_id')
        new_lokasi_id = int(lok_id_raw) if lok_id_raw and lok_id_raw.isdigit() else None

        perubahan_edit = []
        if old_kode != new_kode: perubahan_edit.append(f"Kode ({old_kode} -> {new_kode})")
        if old_nama != new_nama: perubahan_edit.append(f"Nama ({old_nama} -> {new_nama})")
        if old_brand != new_brand: perubahan_edit.append(f"Brand ({old_brand} -> {new_brand})")
        if old_vendor != new_vendor: perubahan_edit.append(f"Vendor ({old_vendor} -> {new_vendor})")
        if old_tipe != new_tipe: perubahan_edit.append(f"Tipe ({old_tipe} -> {new_tipe})")
        if old_stok != new_stok: perubahan_edit.append(f"Stok Awal ({old_stok} -> {new_stok})")
        
        if old_kategori_id != new_kategori_id:
            old_kat = barang.kategori_terkait.nama_kategori if barang.kategori_terkait else "Kosong"
            new_kat_obj = KategoriBarang.query.get(new_kategori_id) if new_kategori_id else None
            new_kat = new_kat_obj.nama_kategori if new_kat_obj else "Kosong"
            perubahan_edit.append(f"Kategori ({old_kat} -> {new_kat})")
            
        if old_satuan_id != new_satuan_id:
            old_sat = barang.satuan_terkait.nama_satuan if barang.satuan_terkait else "Kosong"
            new_sat_obj = SatuanBarang.query.get(new_satuan_id) if new_satuan_id else None
            new_sat = new_sat_obj.nama_satuan if new_sat_obj else "Kosong"
            perubahan_edit.append(f"Satuan ({old_sat} -> {new_sat})")

        barang.kode_barang = new_kode
        barang.nama_barang = new_nama
        barang.brand = request.form.get('brand', '').strip()
        barang.vendor = request.form.get('vendor', '').strip()
        barang.kategori_id = new_kategori_id
        barang.unit_type = request.form.get('unit_type', '').strip()
        barang.lokasi_id = new_lokasi_id
        barang.satuan_id = new_satuan_id
        barang.stok = new_stok
        
        if perubahan_edit or keterangan_tambahan:
            keterangan_edit = "Edit: " + ", ".join(perubahan_edit) if perubahan_edit else "Edit Data Tambahan"
            if keterangan_tambahan:
                keterangan_edit += f" | Catatan: {keterangan_tambahan}"
            db.session.add(Transaksi(user_id=current_user.id, consumable_id=barang.id, jenis='Edit', jumlah=1, keterangan=keterangan_edit))
            
        if old_lokasi_id != new_lokasi_id:
            lok_baru = SubLokasi.query.get(new_lokasi_id)
            if lok_baru and lok_baru.main:
                ket_mutasi = f"Pindah Lokasi ke: {lok_baru.main.nama_main} - {lok_baru.nama_sub}"
            else:
                ket_mutasi = f"Pindah Lokasi ke: {lok_baru.nama_sub}" if lok_baru else "Ditarik dari Lokasi"
            db.session.add(Transaksi(user_id=current_user.id, consumable_id=barang.id, jenis='Mutasi', jumlah=1, keterangan=ket_mutasi))

        db.session.commit()
        flash('Data Consumable berhasil diperbarui.', 'success')
        return redirect(url_for('edit_consumable', id=id))
        
    riwayat_barang = Transaksi.query.filter_by(consumable_id=id).order_by(Transaksi.tanggal.desc()).all()
        
    return render_template('consumable/edit.html', 
                           barang=barang, 
                           riwayat=riwayat_barang,
                           main_lokasi_list=MainLokasi.query.order_by(MainLokasi.nama_main.asc()).all(),
                           sub_lokasi_list=SubLokasi.query.join(MainLokasi).order_by(MainLokasi.nama_main.asc(), SubLokasi.nama_sub.asc()).all(),
                           kategori_list=KategoriBarang.query.filter_by(jenis='Consumable').order_by(KategoriBarang.nama_kategori.asc()).all(),
                           satuan_list=SatuanBarang.query.order_by(SatuanBarang.nama_satuan.asc()).all())

@app.route('/hapus_consumable/<int:id>')
@login_required
@admin_required
def hapus_consumable(id):
    barang = Consumable.query.get_or_404(id)
    barang.is_active = False 
    db.session.commit()
    flash('Data Consumable berhasil dihapus.', 'success')
    return redirect(url_for('master_consumable'))

@app.route('/transaksi_consumable_bulk', methods=['POST'])
@login_required
@admin_required
def transaksi_consumable_bulk():
    if 'process_bulk' in request.form:
        item_ids = request.form.getlist('item_ids')
        berhasil = 0
        
        for item_id in item_ids:
            jenis = request.form.get(f'jenis_transaksi_{item_id}')
            jumlah_str = request.form.get(f'jumlah_{item_id}')
            keterangan = request.form.get(f'keterangan_{item_id}', '').strip()
            
            if not jenis or not jumlah_str or not jumlah_str.isdigit():
                continue
                
            jumlah = int(jumlah_str)
            if jumlah <= 0:
                continue
                
            barang = Consumable.query.get(item_id)
            if not barang:
                continue
                
            if jenis == 'Keluar':
                if barang.stok < jumlah:
                    flash(f'Gagal: Stok {barang.nama_barang} tidak mencukupi (sisa {barang.stok}).', 'danger')
                    continue
                barang.stok -= jumlah
            elif jenis == 'Masuk':
                barang.stok += jumlah
                
            db.session.add(Transaksi(consumable_id=barang.id, user_id=current_user.id, jenis=jenis, jumlah=jumlah, keterangan=keterangan))
            berhasil += 1
            
        db.session.commit()
        if berhasil > 0:
            flash(f'{berhasil} data transaksi barang berhasil diproses.', 'success')
        else:
            flash('Tidak ada transaksi yang valid untuk diproses.', 'warning')
            
        return redirect(url_for('master_consumable'))
        
    item_ids = request.form.getlist('item_ids')
    if not item_ids:
        flash('Pilih minimal satu barang untuk ditransaksikan.', 'danger')
        return redirect(url_for('master_consumable'))
        
    barangs = Consumable.query.filter(Consumable.id.in_(item_ids)).all()
    return render_template('consumable/transaksi_bulk.html', barangs=barangs)

@app.route('/hapus_consumable_bulk', methods=['POST'])
@login_required
@admin_required
def hapus_consumable_bulk():
    item_ids = request.form.getlist('item_ids')
    if not item_ids:
        flash('Gagal: Tidak ada barang yang dipilih.', 'danger')
        return redirect(url_for('master_consumable'))
        
    for item_id in item_ids:
        barang = Consumable.query.get(item_id)
        if barang: 
            barang.is_active = False
            
    db.session.commit()
    flash(f'{len(item_ids)} barang berhasil dihapus.', 'success')
    return redirect(url_for('master_consumable'))

@app.route('/transaksi_consumable/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def catat_transaksi_cns(id):
    barang = Consumable.query.get_or_404(id)
    
    if request.method == 'POST':
        jenis = request.form.get('jenis_transaksi')
        keterangan = request.form.get('keterangan', '').strip()
        try:
            jumlah = int(request.form.get('jumlah', 1))
        except ValueError:
            flash('Jumlah harus berupa angka.', 'danger')
            return redirect(url_for('catat_transaksi_cns', id=id))
            
        satuan_teks = barang.satuan_terkait.nama_satuan if barang.satuan_terkait else "unit"
            
        if jenis == 'Keluar':
            if barang.stok < jumlah:
                flash(f'Gagal: Stok tidak mencukupi! Sisa stok {barang.nama_barang} saat ini hanya {barang.stok} {satuan_teks}.', 'danger')
                return redirect(url_for('catat_transaksi_cns', id=id))
            barang.stok -= jumlah
        elif jenis == 'Masuk':
            barang.stok += jumlah
        else:
            flash('Jenis transaksi tidak valid.', 'danger')
            return redirect(url_for('catat_transaksi_cns', id=id))

        db.session.add(Transaksi(consumable_id=barang.id, user_id=current_user.id, jenis=jenis, jumlah=jumlah, keterangan=keterangan))
        db.session.commit()
        
        flash(f'Berhasil: {jumlah} {satuan_teks} {barang.nama_barang} telah dicatat ({jenis}).', 'success')
        return redirect(url_for('master_consumable'))
        
    return render_template('transaksi/form_transaksi.html', barang=barang, tipe='consumable')

@app.route('/export_consumable')
@login_required
@admin_required
def export_consumable():
    search = request.args.get('search', '').strip()
    filter_kategori = request.args.get('kategori', '').strip()
    filter_stok = request.args.get('stok', '').strip()
    filter_lokasi = request.args.get('lokasi', '').strip()
    
    query = Consumable.query.filter_by(is_active=True)
    
    if search:
        query = query.filter(or_(
            Consumable.nama_barang.ilike(f"%{search}%"), 
            Consumable.kode_barang.ilike(f"%{search}%"),
            Consumable.brand.ilike(f"%{search}%"),
            Consumable.vendor.ilike(f"%{search}%")
        ))
    if filter_kategori: query = query.filter(Consumable.kategori_id == filter_kategori)
    if filter_lokasi: query = query.filter(Consumable.lokasi_id == filter_lokasi)
    
    if filter_stok == 'sedikit': query = query.filter(Consumable.stok <= 5)
    elif filter_stok == 'banyak': query = query.filter(Consumable.stok > 5)
        
    items = query.order_by(Consumable.id.asc()).all()

    data = []
    for i, item in enumerate(items, 1):
        data.append({
            'No': i,
            'Kode Barang': item.kode_barang,
            'Nama Barang': item.nama_barang,
            'Brand': item.brand or '-',
            'Vendor': item.vendor or '-',
            'Kategori': item.kategori_terkait.nama_kategori if item.kategori_id and item.kategori_terkait else '-',
            'Tipe Unit': item.unit_type or '-',
            'Main Location': item.lokasi.main.nama_main if item.lokasi and item.lokasi.main else 'Belum Dialokasikan',
            'Sub Location': item.lokasi.nama_sub if item.lokasi else '-',
            'Sisa Stok': item.stok,
            'Satuan': item.satuan_terkait.nama_satuan if item.satuan_id and item.satuan_terkait else '-',
            'Tanggal Register': item.created_at.strftime('%Y-%m-%d %H:%M:%S') if item.created_at else "-"
        })
    
    df = pd.DataFrame(data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Data Consumable')
        worksheet = writer.sheets['Data Consumable']
        
        header_format = writer.book.add_format({'bold': True, 'bg_color': '#D3D3D3', 'border': 1})
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, header_format)
            
        for idx, col in enumerate(df.columns):
            max_len = max((df[col].astype(str).map(len).max(), len(col))) + 2
            worksheet.set_column(idx, idx, max_len)

    output.seek(0)
    return send_file(output, download_name="Data_Consumable.xlsx", as_attachment=True, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

@app.route('/export_riwayat_consumable')
@login_required
@admin_required
def export_riwayat_consumable():
    search = request.args.get('search', '')
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    
    query = Transaksi.query.filter(Transaksi.consumable_id != None)
    
    if search:
        query = query.join(Consumable).filter(or_(
            Consumable.nama_barang.ilike(f"%{search}%"),
            Consumable.kode_barang.ilike(f"%{search}%"),
            Transaksi.keterangan.ilike(f"%{search}%")
        ))
        
    if start_date: query = query.filter(Transaksi.tanggal >= f"{start_date} 00:00:00")
    if end_date: query = query.filter(Transaksi.tanggal <= f"{end_date} 23:59:59")
        
    items = query.order_by(Transaksi.tanggal.desc()).all()

    data = []
    for i, item in enumerate(items, 1):
        pic_name = 'Sistem'
        if item.user:
            pic_name = item.user.nama_lengkap.split(' ')[0] if item.user.nama_lengkap else item.user.payroll
            
        data.append({
            'No': i,
            'Waktu': item.tanggal.strftime('%Y-%m-%d %H:%M:%S') if item.tanggal else "-",
            'Kode Barang': item.consumable.kode_barang if item.consumable else '-',
            'Nama Barang': item.consumable.nama_barang if item.consumable else '-',
            'Jenis': item.jenis,
            'Jumlah': item.jumlah,
            'Satuan': item.consumable.satuan_terkait.nama_satuan if item.consumable and item.consumable.satuan_id else '-',
            'Operator': pic_name,
            'Keterangan': item.keterangan or '-'
        })
        
    df = pd.DataFrame(data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Riwayat Consumable')
        worksheet = writer.sheets['Riwayat Consumable']
        
        header_format = writer.book.add_format({'bold': True, 'bg_color': '#D3D3D3', 'border': 1})
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, header_format)
            
        for idx, col in enumerate(df.columns):
            max_len = max((df[col].astype(str).map(len).max(), len(col))) + 2
            worksheet.set_column(idx, idx, max_len)

    output.seek(0)
    return send_file(output, download_name="Riwayat_Stok_Consumable.xlsx", as_attachment=True, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

# ==========================================
# FITUR IMPORT EXCEL CONSUMABLE (DENGAN DROPDOWN)
# ==========================================

@app.route('/download_template_consumable')
@login_required
@admin_required
def download_template_consumable():
    kolom = ['Kode Barang', 'Nama Barang', 'Brand', 'Vendor', 'Tipe Unit', 'Kategori', 'Satuan', 'Stok Awal', 'Main Lokasi', 'Sub Lokasi']
    df = pd.DataFrame(columns=kolom)
    
    # Menarik data aktif dari Database untuk Dropdown
    kategori_list = [k.nama_kategori for k in KategoriBarang.query.filter_by(jenis='Consumable').order_by(KategoriBarang.nama_kategori.asc()).all()]
    satuan_list = [s.nama_satuan for s in SatuanBarang.query.order_by(SatuanBarang.nama_satuan.asc()).all()]
    main_lokasi_list = [m.nama_main for m in MainLokasi.query.order_by(MainLokasi.nama_main.asc()).all()]
    # Menghapus duplikat nama Sub Lokasi
    sub_lokasi_list = list(set([s.nama_sub for s in SubLokasi.query.all()]))
    sub_lokasi_list.sort()
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Template_Import')
        workbook = writer.book
        worksheet = writer.sheets['Template_Import']
        
        # 1. Formatting Header Utama
        header_format = workbook.add_format({'bold': True, 'bg_color': '#0a2540', 'font_color': 'white', 'border': 1})
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, header_format)
            worksheet.set_column(col_num, col_num, 20)
            
        # 2. Membuat Sheet Tersembunyi (Referensi) untuk menampung list panjang
        ref_sheet = workbook.add_worksheet('Referensi')
        ref_sheet.hide() # Disembunyikan agar user tidak bingung
        
        # 3. Menulis Data ke Sheet Referensi & Menyuntikkan Dropdown ke Template
        # Index kolom excel (0=A, 1=B, ..., 5=F(Kategori), 6=G(Satuan), 8=I(MainLok), 9=J(SubLok))
        
        if kategori_list:
            ref_sheet.write_column('A2', kategori_list)
            # Apply validasi ke kolom F (Baris 2 hingga 1000)
            worksheet.data_validation('F2:F1000', {'validate': 'list', 'source': f'=Referensi!$A$2:$A${len(kategori_list)+1}'})
            
        if satuan_list:
            ref_sheet.write_column('B2', satuan_list)
            worksheet.data_validation('G2:G1000', {'validate': 'list', 'source': f'=Referensi!$B$2:$B${len(satuan_list)+1}'})
            
        if main_lokasi_list:
            ref_sheet.write_column('C2', main_lokasi_list)
            worksheet.data_validation('I2:I1000', {'validate': 'list', 'source': f'=Referensi!$C$2:$C${len(main_lokasi_list)+1}'})
            
        if sub_lokasi_list:
            ref_sheet.write_column('D2', sub_lokasi_list)
            worksheet.data_validation('J2:J1000', {'validate': 'list', 'source': f'=Referensi!$D$2:$D${len(sub_lokasi_list)+1}'})
            
    output.seek(0)
    return send_file(output, download_name="Template_Import_Consumable.xlsx", as_attachment=True)

@app.route('/import_consumable', methods=['POST'])
@login_required
@admin_required
def import_consumable():
    if 'file' not in request.files:
        flash('Tidak ada file yang dipilih.', 'danger')
        return redirect(url_for('master_consumable'))
        
    file = request.files['file']
    if file.filename == '':
        flash('File tidak valid.', 'danger')
        return redirect(url_for('master_consumable'))
        
    try:
        df = pd.read_excel(file)
        
        required_cols = ['Kode Barang', 'Nama Barang']
        for col in required_cols:
            if col not in df.columns:
                flash(f'Gagal: Kolom wajib "{col}" tidak ditemukan di file Excel.', 'danger')
                return redirect(url_for('master_consumable'))
                
        berhasil = 0
        gagal = 0
        
        for index, row in df.iterrows():
            val_kode = row.get('Kode Barang')
            val_nama = row.get('Nama Barang')
            
            kode = str(val_kode).strip() if pd.notna(val_kode) else ''
            nama = str(val_nama).strip() if pd.notna(val_nama) else ''
            
            if not kode or not nama:
                gagal += 1
                continue
                
            if Consumable.query.filter_by(kode_barang=kode).first():
                gagal += 1
                continue
                
            brand = str(row.get('Brand')).strip() if pd.notna(row.get('Brand')) else ''
            vendor = str(row.get('Vendor')).strip() if pd.notna(row.get('Vendor')) else ''
            tipe = str(row.get('Tipe Unit')).strip() if pd.notna(row.get('Tipe Unit')) else ''
            
            # --- PENANGANAN STOK ---
            val_stok = row.get('Stok Awal')
            stok = 0
            if pd.notna(val_stok):
                try:
                    stok = int(val_stok)
                except ValueError:
                    stok = 0
            if stok < 0: stok = 0
            
            # --- PENANGANAN RELASI KATEGORI ---
            val_kat = row.get('Kategori')
            kat_nama = str(val_kat).strip() if pd.notna(val_kat) else ''
            kategori_id = None
            if kat_nama:
                kat = KategoriBarang.query.filter(KategoriBarang.nama_kategori.ilike(kat_nama), KategoriBarang.jenis=='Consumable').first()
                if not kat:
                    kat = KategoriBarang(nama_kategori=kat_nama, jenis='Consumable')
                    db.session.add(kat)
                    db.session.flush()
                kategori_id = kat.id
                
            # --- PENANGANAN RELASI SATUAN ---
            val_sat = row.get('Satuan')
            sat_nama = str(val_sat).strip() if pd.notna(val_sat) else ''
            satuan_id = None
            if sat_nama:
                sat = SatuanBarang.query.filter(SatuanBarang.nama_satuan.ilike(sat_nama)).first()
                if not sat:
                    sat = SatuanBarang(nama_satuan=sat_nama)
                    db.session.add(sat)
                    db.session.flush()
                satuan_id = sat.id
                
            # --- PENANGANAN RELASI LOKASI ---
            val_main = row.get('Main Lokasi')
            val_sub = row.get('Sub Lokasi')
            lok_main_nama = str(val_main).strip() if pd.notna(val_main) else ''
            lok_sub_nama = str(val_sub).strip() if pd.notna(val_sub) else '-'
            lokasi_id = None
            
            if lok_main_nama:
                main_lok = MainLokasi.query.filter(MainLokasi.nama_main.ilike(lok_main_nama)).first()
                if not main_lok:
                    main_lok = MainLokasi(nama_main=lok_main_nama)
                    db.session.add(main_lok)
                    db.session.flush()
                    
                sub_lok = SubLokasi.query.filter(SubLokasi.main_lokasi_id==main_lok.id, SubLokasi.nama_sub.ilike(lok_sub_nama)).first()
                if not sub_lok:
                    sub_lok = SubLokasi(main_lokasi_id=main_lok.id, nama_sub=lok_sub_nama)
                    db.session.add(sub_lok)
                    db.session.flush()
                lokasi_id = sub_lok.id
                
            # Simpan Barang Consumable
            cons = Consumable(
                kode_barang=kode, nama_barang=nama, brand=brand, vendor=vendor,
                unit_type=tipe, kategori_id=kategori_id, lokasi_id=lokasi_id,
                satuan_id=satuan_id, stok=stok, is_active=True
            )
            db.session.add(cons)
            db.session.flush()
            
            # Catat Riwayat Mutasi "Masuk" jika stok > 0
            if stok > 0:
                ket_masuk = "Stok Awal via Import Excel massal."
                trx_masuk = Transaksi(user_id=current_user.id, consumable_id=cons.id, jenis='Masuk', jumlah=stok, keterangan=ket_masuk)
                db.session.add(trx_masuk)
                
            berhasil += 1
            
        db.session.commit()
        if berhasil > 0:
            flash(f'Import Sukses! {berhasil} consumable ditambahkan. {gagal} baris dilewati (duplikat/tidak valid).', 'success')
        else:
            flash(f'Gagal: Tidak ada data valid yang diimport. {gagal} baris bermasalah.', 'warning')
            
    except Exception as e:
        db.session.rollback()
        flash(f'Sistem gagal membaca isi Excel Anda. Error Code: {str(e)}', 'danger')
        
    return redirect(url_for('master_consumable'))