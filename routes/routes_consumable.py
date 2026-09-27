import io
from openpyxl import Workbook
from openpyxl.styles import Font, Border, Side, Alignment
from flask import render_template, request, redirect, url_for, flash, send_file
from flask_login import login_required, current_user
from main import app, admin_required
from models import db, Consumable, Transaksi, Lokasi

@app.route('/consumable')
@login_required
def master_consumable():
    search = request.args.get('search', '')
    filter_kategori = request.args.get('kategori', '')
    filter_tipe = request.args.get('tipe', '')
    filter_lokasi = request.args.get('lokasi', '')
    
    query = Consumable.query.filter_by(is_active=True)
    if search: query = query.filter(db.or_(Consumable.nama_barang.ilike(f"%{search}%"), Consumable.kode_barang.ilike(f"%{search}%")))
    if filter_kategori: query = query.filter(Consumable.kategori == filter_kategori)
    if filter_tipe: query = query.filter(Consumable.unit_type == filter_tipe)
    if filter_lokasi: query = query.filter(Consumable.lokasi_id == filter_lokasi)
        
    kategori_list = [k[0] for k in db.session.query(Consumable.kategori).filter(Consumable.is_active==True, Consumable.kategori != None, Consumable.kategori != '').distinct().all()]
    tipe_list = [t[0] for t in db.session.query(Consumable.unit_type).filter(Consumable.is_active==True, Consumable.unit_type != None, Consumable.unit_type != '').distinct().all()]
    lokasi_list = Lokasi.query.order_by(Lokasi.main_lokasi.asc(), Lokasi.nama_lokasi.asc()).all()
    
    return render_template('consumable/master.html', data=query.paginate(page=request.args.get('page', 1, type=int), per_page=50, error_out=False), search_query=search, filter_kategori=filter_kategori, filter_tipe=filter_tipe, filter_lokasi=filter_lokasi, kategori_list=kategori_list, tipe_list=tipe_list, lokasi_list=lokasi_list)

@app.route('/tambah_consumable', methods=['GET', 'POST'])
@login_required
@admin_required
def tambah_consumable():
    if request.method == 'POST':
        kode_barang = request.form.get('kode_barang', '').strip()
        stok = int(request.form.get('stok', 0))
        if stok < 0 or Consumable.query.filter_by(kode_barang=kode_barang).first():
            flash('Gagal! Stok minus atau Kode terdaftar.', 'danger')
            return redirect(url_for('tambah_consumable'))
            
        barang_baru = Consumable(kode_barang=kode_barang, nama_barang=request.form.get('nama_barang', '').strip(), kategori=request.form.get('kategori', '').strip(), unit_type=request.form.get('unit_type', '').strip(), lokasi_id=request.form.get('lokasi_id') or None, stok=stok, satuan=request.form.get('satuan', '').strip(), notes=request.form.get('notes', '').strip())
        db.session.add(barang_baru)
        db.session.flush()
        if stok > 0: db.session.add(Transaksi(user_id=current_user.id, consumable_id=barang_baru.id, jenis='Masuk', jumlah=stok, keterangan='Stok Awal'))
        db.session.commit()
        flash('Barang Consumable ditambahkan.', 'success')
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
        barang.kategori = request.form.get('kategori', '').strip()
        barang.unit_type = request.form.get('unit_type', '').strip()
        barang.lokasi_id = request.form.get('lokasi_id') or None
        barang.satuan = request.form.get('satuan', '').strip()
        barang.notes = request.form.get('notes', '').strip()
        db.session.commit()
        flash('Data Consumable diperbarui.', 'success')
        return redirect(url_for('master_consumable'))
    return render_template('consumable/edit.html', barang=barang, lokasi_list=Lokasi.query.all())

@app.route('/hapus_consumable/<int:id>')
@login_required
@admin_required
def hapus_consumable(id):
    barang = Consumable.query.get_or_404(id)
    barang.is_active = False 
    db.session.commit()
    flash('Data dihapus.', 'success')
    return redirect(url_for('master_consumable'))

@app.route('/mutasi_consumable_bulk', methods=['POST'])
@login_required
@admin_required
def mutasi_consumable_bulk():
    item_ids = request.form.getlist('item_ids')
    lokasi_baru_id = request.form.get('lokasi_id_bulk')
    keterangan = request.form.get('keterangan_bulk', '').strip()
    
    if not item_ids:
        flash('Gagal: Tidak ada barang yang dipilih.', 'danger')
        return redirect(url_for('master_consumable'))
        
    for item_id in item_ids:
        barang = Consumable.query.get(item_id)
        if barang:
            if lokasi_baru_id: barang.lokasi_id = lokasi_baru_id
            db.session.add(Transaksi(consumable_id=barang.id, user_id=current_user.id, jenis='Mutasi', jumlah=0, keterangan=keterangan or 'Mutasi Lokasi Massal'))
    db.session.commit()
    flash(f'{len(item_ids)} barang berhasil dimutasi.', 'success')
    return redirect(url_for('master_consumable'))

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
        if barang: barang.is_active = False
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
            
        keterangan_form = request.form.get('keterangan', '').strip()
        if not keterangan_form:
            keterangan_form = "-"
        
        # Logika Pengurangan / Penambahan Stok
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

        # Mencatat jejak ke tabel Transaksi dengan keterangan bersih
        transaksi_baru = Transaksi(
            consumable_id=barang.id,
            user_id=current_user.id,
            jenis=jenis,
            jumlah=jumlah,
            keterangan=keterangan_form
        )
        
        db.session.add(transaksi_baru)
        db.session.commit()
        
        flash(f'Berhasil: {jumlah} {barang.satuan} {barang.nama_barang} telah dicatat sebagai barang {jenis.lower()}.', 'success')
        return redirect(url_for('master_consumable'))
        
    return render_template('transaksi/form_transaksi.html', barang=barang, tipe='consumable')

@app.route('/export_consumable')
@login_required
@admin_required
def export_consumable():
    search = request.args.get('search', '')
    filter_kategori = request.args.get('kategori', '')
    filter_tipe = request.args.get('tipe', '')
    filter_lokasi = request.args.get('lokasi', '')
    
    query = Consumable.query.filter_by(is_active=True)
    
    if search:
        query = query.filter(db.or_(Consumable.nama_barang.ilike(f"%{search}%"), Consumable.kode_barang.ilike(f"%{search}%")))
    if filter_kategori: query = query.filter(Consumable.kategori == filter_kategori)
    if filter_tipe: query = query.filter(Consumable.unit_type == filter_tipe)
    if filter_lokasi: query = query.filter(Consumable.lokasi_id == filter_lokasi)
        
    data_consumable = query.all()

    wb = Workbook()
    ws = wb.active
    ws.title = "Data Consumable"

    thin_border = Border(
        left=Side(style='thin'), 
        right=Side(style='thin'), 
        top=Side(style='thin'), 
        bottom=Side(style='thin')
    )

    headers = ['No', 'Kode Barang', 'Nama Barang', 'Kategori', 'Tipe Unit', 'Main Location', 'Sub Location', 'Sisa Stok', 'Satuan', 'Tanggal Register']
    ws.append(headers)
    
    for cell in ws[1]:
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal='center', vertical='center')

    for idx, item in enumerate(data_consumable, 1):
        main_lokasi = item.lokasi.main_lokasi if item.lokasi else "Belum Dialokasikan"
        sub_lokasi = item.lokasi.nama_lokasi if item.lokasi else "-"
        tanggal = item.created_at.strftime('%Y-%m-%d %H:%M:%S') if item.created_at else "-"
        
        ws.append([
            idx,
            item.kode_barang,
            item.nama_barang,
            item.kategori or '-',
            item.unit_type or '-',
            main_lokasi,
            sub_lokasi,
            item.stok,
            item.satuan or '-',
            tanggal
        ])

    for col in ws.columns:
        max_length = 0
        column_letter = col[0].column_letter
        
        for cell in col:
            if cell.value is not None:
                cell.border = thin_border
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        
        adjusted_width = (max_length + 2)
        ws.column_dimensions[column_letter].width = adjusted_width

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='Data_Consumable.xlsx'
    )

@app.route('/export_riwayat_consumable')
@login_required
@admin_required
def export_riwayat_consumable():
    search = request.args.get('search', '')
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    
    query = Transaksi.query.filter(Transaksi.consumable_id != None)
    
    if search:
        query = query.join(Consumable).filter(
            db.or_(
                Consumable.nama_barang.ilike(f"%{search}%"),
                Consumable.kode_barang.ilike(f"%{search}%"),
                Transaksi.keterangan.ilike(f"%{search}%")
            )
        )
        
    if start_date: query = query.filter(Transaksi.tanggal >= f"{start_date} 00:00:00")
    if end_date: query = query.filter(Transaksi.tanggal <= f"{end_date} 23:59:59")
        
    data_riwayat = query.order_by(Transaksi.tanggal.desc()).all()

    wb = Workbook()
    ws = wb.active
    ws.title = "Riwayat Consumable"
    thin_border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))

    headers = ['No', 'Waktu', 'Kode Barang', 'Nama Barang', 'Jenis', 'Jumlah', 'Satuan', 'Keterangan', 'PIC (User)']
    ws.append(headers)
    
    for cell in ws[1]:
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal='center', vertical='center')

    for idx, item in enumerate(data_riwayat, 1):
        waktu = item.tanggal.strftime('%Y-%m-%d %H:%M:%S') if item.tanggal else "-"
        
        ws.append([
            idx, waktu, 
            item.consumable.kode_barang if item.consumable else '-', 
            item.consumable.nama_barang if item.consumable else '-', 
            item.jenis, item.jumlah, 
            item.consumable.satuan if item.consumable else '-', 
            item.keterangan or '-', item.user.username if item.user else 'Sistem'
        ])

    for col in ws.columns:
        max_length = 0
        column_letter = col[0].column_letter
        for cell in col:
            if cell.value is not None: cell.border = thin_border
            try:
                if len(str(cell.value)) > max_length: max_length = len(str(cell.value))
            except: pass
        ws.column_dimensions[column_letter].width = (max_length + 2)

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', as_attachment=True, download_name='Riwayat_Stok_Consumable.xlsx')