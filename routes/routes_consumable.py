import io
import pandas as pd
from flask import render_template, request, redirect, url_for, flash, send_file
from flask_login import login_required, current_user
from sqlalchemy import or_

# Sesuaikan dengan struktur impor proyek Anda
from main import app, admin_required
from models import db, Consumable, Transaksi, Lokasi

@app.route('/consumable')
@login_required
def master_consumable():
    search = request.args.get('search', '').strip()
    filter_kategori = request.args.get('kategori', '').strip()
    filter_tipe = request.args.get('tipe', '').strip()
    filter_lokasi = request.args.get('lokasi', '').strip()
    page = request.args.get('page', 1, type=int)
    
    query = Consumable.query.filter_by(is_active=True)
    
    if search: 
        query = query.filter(or_(
            Consumable.nama_barang.ilike(f"%{search}%"), 
            Consumable.kode_barang.ilike(f"%{search}%"),
            Consumable.brand.ilike(f"%{search}%"),
            Consumable.vendor.ilike(f"%{search}%")
        ))
    if filter_kategori: query = query.filter(Consumable.kategori == filter_kategori)
    if filter_tipe: query = query.filter(Consumable.unit_type == filter_tipe)
    if filter_lokasi: query = query.filter(Consumable.lokasi_id == filter_lokasi)
        
    kategori_list = [k[0] for k in db.session.query(Consumable.kategori).filter(Consumable.is_active==True, Consumable.kategori != None, Consumable.kategori != '').distinct().all()]
    tipe_list = [t[0] for t in db.session.query(Consumable.unit_type).filter(Consumable.is_active==True, Consumable.unit_type != None, Consumable.unit_type != '').distinct().all()]
    lokasi_list = Lokasi.query.order_by(Lokasi.main_lokasi.asc(), Lokasi.nama_lokasi.asc()).all()
    
    data = query.order_by(Consumable.id.desc()).paginate(page=page, per_page=50, error_out=False)
    
    return render_template('consumable/master.html', data=data, search_query=search, filter_kategori=filter_kategori, filter_tipe=filter_tipe, filter_lokasi=filter_lokasi, kategori_list=kategori_list, tipe_list=tipe_list, lokasi_list=lokasi_list)

@app.route('/tambah_consumable', methods=['GET', 'POST'])
@login_required
@admin_required
def tambah_consumable():
    if request.method == 'POST':
        kode_barang = request.form.get('kode_barang', '').strip()
        stok = int(request.form.get('stok', 0))
        
        if stok < 0 or Consumable.query.filter_by(kode_barang=kode_barang).first():
            flash('Gagal! Stok minus atau Kode aset sudah terdaftar.', 'danger')
            return redirect(url_for('tambah_consumable'))
            
        barang_baru = Consumable(
            kode_barang=kode_barang, 
            nama_barang=request.form.get('nama_barang', '').strip(), 
            brand=request.form.get('brand', '').strip(),
            vendor=request.form.get('vendor', '').strip(),
            kategori=request.form.get('kategori', '').strip(), 
            unit_type=request.form.get('unit_type', '').strip(), 
            lokasi_id=request.form.get('lokasi_id') or None, 
            stok=stok, 
            satuan=request.form.get('satuan', '').strip()
        )
        db.session.add(barang_baru)
        db.session.flush()
        
        if stok > 0: 
            # Keterangan dihapus dari Transaksi
            db.session.add(Transaksi(user_id=current_user.id, consumable_id=barang_baru.id, jenis='Masuk', jumlah=stok))
        
        db.session.commit()
        flash('Barang Consumable berhasil ditambahkan.', 'success')
        return redirect(url_for('master_consumable'))
        
    return render_template('consumable/tambah.html', lokasi_list=Lokasi.query.all())

@app.route('/edit_consumable/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_consumable(id):
    barang = Consumable.query.get_or_404(id)
    if request.method == 'POST':
        barang.stok = int(request.form.get('stok', 0))
        barang.kode_barang = request.form.get('kode_barang', '').strip()
        barang.nama_barang = request.form.get('nama_barang', '').strip()
        barang.brand = request.form.get('brand', '').strip()
        barang.vendor = request.form.get('vendor', '').strip()
        barang.kategori = request.form.get('kategori', '').strip()
        barang.unit_type = request.form.get('unit_type', '').strip()
        barang.lokasi_id = request.form.get('lokasi_id') or None
        barang.satuan = request.form.get('satuan', '').strip()
        
        db.session.commit()
        flash('Data Consumable berhasil diperbarui.', 'success')
        return redirect(url_for('master_consumable'))
        
    return render_template('consumable/edit.html', barang=barang, lokasi_list=Lokasi.query.all())

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
                
            # Pencatatan Transaksi tanpa Keterangan
            db.session.add(Transaksi(consumable_id=barang.id, user_id=current_user.id, jenis=jenis, jumlah=jumlah))
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
        try:
            jumlah = int(request.form.get('jumlah', 1))
        except ValueError:
            flash('Jumlah harus berupa angka.', 'danger')
            return redirect(url_for('catat_transaksi_cns', id=id))
            
        if jenis == 'Keluar':
            if barang.stok < jumlah:
                flash(f'Gagal: Stok tidak mencukupi! Sisa stok {barang.nama_barang} saat ini hanya {barang.stok} {barang.satuan}.', 'danger')
                return redirect(url_for('catat_transaksi_cns', id=id))
            barang.stok -= jumlah
        elif jenis == 'Masuk':
            barang.stok += jumlah
        else:
            flash('Jenis transaksi tidak valid.', 'danger')
            return redirect(url_for('catat_transaksi_cns', id=id))

        # Pencatatan Transaksi tunggal tanpa keterangan
        db.session.add(Transaksi(consumable_id=barang.id, user_id=current_user.id, jenis=jenis, jumlah=jumlah))
        db.session.commit()
        
        flash(f'Berhasil: {jumlah} {barang.satuan} {barang.nama_barang} telah dicatat ({jenis}).', 'success')
        return redirect(url_for('master_consumable'))
        
    return render_template('transaksi/form_transaksi.html', barang=barang, tipe='consumable')

@app.route('/export_consumable')
@login_required
@admin_required
def export_consumable():
    search = request.args.get('search', '').strip()
    filter_kategori = request.args.get('kategori', '').strip()
    filter_tipe = request.args.get('tipe', '').strip()
    filter_lokasi = request.args.get('lokasi', '').strip()
    
    query = Consumable.query.filter_by(is_active=True)
    
    if search:
        query = query.filter(or_(
            Consumable.nama_barang.ilike(f"%{search}%"), 
            Consumable.kode_barang.ilike(f"%{search}%"),
            Consumable.brand.ilike(f"%{search}%"),
            Consumable.vendor.ilike(f"%{search}%")
        ))
    if filter_kategori: query = query.filter(Consumable.kategori == filter_kategori)
    if filter_tipe: query = query.filter(Consumable.unit_type == filter_tipe)
    if filter_lokasi: query = query.filter(Consumable.lokasi_id == filter_lokasi)
        
    items = query.order_by(Consumable.id.asc()).all()

    data = []
    for i, item in enumerate(items, 1):
        data.append({
            'No': i,
            'Kode Barang': item.kode_barang,
            'Nama Barang': item.nama_barang,
            'Brand': item.brand or '-',
            'Vendor': item.vendor or '-',
            'Kategori': item.kategori or '-',
            'Tipe Unit': item.unit_type or '-',
            'Main Location': item.lokasi.main_lokasi if item.lokasi else 'Belum Dialokasikan',
            'Sub Location': item.lokasi.nama_lokasi if item.lokasi else '-',
            'Sisa Stok': item.stok,
            'Satuan': item.satuan or '-',
            'Tanggal Register': item.created_at.strftime('%Y-%m-%d %H:%M:%S') if item.created_at else "-"
        })
    
    df = pd.DataFrame(data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Data Consumable')
        worksheet = writer.sheets['Data Consumable']
        for idx, col in enumerate(df.columns):
            max_len = max((df[col].astype(str).map(len).max(), len(col))) + 2
            worksheet.set_column(idx, idx, max_len)

    output.seek(0)
    return send_file(output, download_name="Data_Consumable.xlsx", as_attachment=True)

@app.route('/export_riwayat_consumable')
@login_required
@admin_required
def export_riwayat_consumable():
    search = request.args.get('search', '')
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    
    query = Transaksi.query.filter(Transaksi.consumable_id != None)
    
    if search:
        # Menghapus pencarian berdasarkan keterangan
        query = query.join(Consumable).filter(or_(
            Consumable.nama_barang.ilike(f"%{search}%"),
            Consumable.kode_barang.ilike(f"%{search}%")
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
            'Satuan': item.consumable.satuan if item.consumable else '-',
            'PIC (User)': pic_name # Kolom Keterangan Dihapus
        })
        
    df = pd.DataFrame(data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Riwayat Consumable')
        worksheet = writer.sheets['Riwayat Consumable']
        for idx, col in enumerate(df.columns):
            max_len = max((df[col].astype(str).map(len).max(), len(col))) + 2
            worksheet.set_column(idx, idx, max_len)

    output.seek(0)
    return send_file(output, download_name="Riwayat_Stok_Consumable.xlsx", as_attachment=True)