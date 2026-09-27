import io
from openpyxl import Workbook
from openpyxl.styles import Font, Border, Side, Alignment
from openpyxl.utils import get_column_letter
from flask import render_template, request, redirect, url_for, flash, send_file
from flask_login import login_required, current_user
from main import app, admin_required
from models import db, Inventory, Lokasi, Transaksi

@app.route('/inventory')
@login_required
def master_inventory():
    search = request.args.get('search', '')
    filter_kategori = request.args.get('kategori', '')
    filter_tipe = request.args.get('tipe', '')
    filter_lokasi = request.args.get('lokasi', '')
    filter_status = request.args.get('status', '') 
    
    query = Inventory.query.filter_by(is_active=True)
    
    if search:
        query = query.filter(db.or_(Inventory.nama_barang.ilike(f"%{search}%"), Inventory.serial_number.ilike(f"%{search}%"), Inventory.kode_barang.ilike(f"%{search}%")))
        
    if filter_kategori: query = query.filter(Inventory.kategori == filter_kategori)
    if filter_tipe: query = query.filter(Inventory.unit_type == filter_tipe)
    if filter_lokasi: query = query.filter(Inventory.lokasi_id == filter_lokasi)
    if filter_status: query = query.filter(Inventory.notes.ilike(f"%{filter_status}%"))
        
    kategori_list = [k[0] for k in db.session.query(Inventory.kategori).filter(Inventory.is_active==True, Inventory.kategori != None, Inventory.kategori != '').distinct().all()]
    tipe_list = [t[0] for t in db.session.query(Inventory.unit_type).filter(Inventory.is_active==True, Inventory.unit_type != None, Inventory.unit_type != '').distinct().all()]
    lokasi_list = Lokasi.query.order_by(Lokasi.main_lokasi.asc(), Lokasi.nama_lokasi.asc()).all()
    
    return render_template('inventory/master.html', data=query.paginate(page=request.args.get('page', 1, type=int), per_page=50, error_out=False), search_query=search, filter_kategori=filter_kategori, filter_tipe=filter_tipe, filter_lokasi=filter_lokasi, filter_status=filter_status, kategori_list=kategori_list, tipe_list=tipe_list, lokasi_list=lokasi_list)

@app.route('/tambah_inventory', methods=['GET', 'POST'])
@login_required
@admin_required
def tambah_inventory():
    if request.method == 'POST':
        kode_barang = request.form.get('kode_barang', '').strip()
        serial_number = request.form.get('serial_number', '').strip()
        if Inventory.query.filter_by(kode_barang=kode_barang).first() or Inventory.query.filter_by(serial_number=serial_number).first():
            flash('Gagal! Kode barang atau Serial Number sudah terdaftar.', 'danger')
            return redirect(url_for('tambah_inventory'))
        
        barang_baru = Inventory(kode_barang=kode_barang, nama_barang=request.form.get('nama_barang', '').strip(), serial_number=serial_number, kategori=request.form.get('kategori', '').strip(), unit_type=request.form.get('unit_type', '').strip(), lokasi_id=request.form.get('lokasi_id') or None, notes=request.form.get('notes', '').strip())
        db.session.add(barang_baru)
        db.session.flush()
        db.session.add(Transaksi(user_id=current_user.id, inventory_id=barang_baru.id, jenis='Masuk', jumlah=1, keterangan='Registrasi Aset Baru'))
        db.session.commit()
        flash('Aset Inventory baru berhasil ditambahkan.', 'success')
        return redirect(url_for('master_inventory'))
    return render_template('inventory/tambah.html', lokasi_list=Lokasi.query.all())

@app.route('/edit_inventory/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_inventory(id):
    barang = Inventory.query.get_or_404(id)
    if request.method == 'POST':
        barang.kode_barang = request.form.get('kode_barang', '').strip()
        barang.nama_barang = request.form.get('nama_barang', '').strip()
        barang.serial_number = request.form.get('serial_number', '').strip()
        barang.kategori = request.form.get('kategori', '').strip()
        barang.unit_type = request.form.get('unit_type', '').strip()
        barang.lokasi_id = request.form.get('lokasi_id') or None
        barang.notes = request.form.get('notes', '').strip()
        db.session.commit()
        flash('Data Inventory berhasil diperbarui.', 'success')
        return redirect(url_for('master_inventory'))
    return render_template('inventory/edit.html', barang=barang, lokasi_list=Lokasi.query.all())

@app.route('/hapus_inventory/<int:id>')
@login_required
@admin_required
def hapus_inventory(id):
    barang = Inventory.query.get_or_404(id)
    barang.is_active = False 
    db.session.commit()
    flash(f'Inventory {barang.nama_barang} berhasil dihapus.', 'success')
    return redirect(url_for('master_inventory'))

@app.route('/hapus_inventory_bulk', methods=['POST'])
@login_required
@admin_required
def hapus_inventory_bulk():
    item_ids = request.form.getlist('item_ids')
    if not item_ids:
        flash('Gagal: Tidak ada barang yang dipilih.', 'danger')
        return redirect(url_for('master_inventory'))
        
    for item_id in item_ids:
        barang = Inventory.query.get(item_id)
        if barang: barang.is_active = False
    db.session.commit()
    flash(f'{len(item_ids)} aset berhasil dihapus.', 'success')
    return redirect(url_for('master_inventory'))

@app.route('/mutasi_inventory_bulk', methods=['POST'])
@login_required
@admin_required
def mutasi_inventory_bulk():
    item_ids = request.form.getlist('item_ids')
    lokasi_baru_id = request.form.get('lokasi_id_bulk')
    keterangan_form = request.form.get('keterangan_bulk', '').strip()
    status_baru = request.form.get('status_aset_bulk', '').strip()
    
    if not item_ids:
        flash('Gagal: Tidak ada barang yang dipilih.', 'danger')
        return redirect(url_for('master_inventory'))
        
    lokasi_tujuan_obj = Lokasi.query.get(lokasi_baru_id) if lokasi_baru_id else None
    nama_lokasi_tujuan = lokasi_tujuan_obj.nama_lokasi if lokasi_tujuan_obj else "Lokasi Tidak Diketahui"

    for item_id in item_ids:
        barang = Inventory.query.get(item_id)
        if barang:
            nama_lokasi_asal = barang.lokasi.nama_lokasi if barang.lokasi else "Belum Dialokasikan"
            
            status_tambahan = ""
            if status_baru:
                barang.notes = status_baru
                status_tambahan = f" [Status: {status_baru}]"
            
            keterangan_full = f"[{nama_lokasi_asal} ➔ {nama_lokasi_tujuan}]{status_tambahan} {keterangan_form}".strip()
            
            if lokasi_baru_id: 
                barang.lokasi_id = lokasi_baru_id
            
            db.session.add(Transaksi(inventory_id=barang.id, user_id=current_user.id, jenis='Mutasi', jumlah=1, keterangan=keterangan_full))
            
    db.session.commit()
    flash(f'{len(item_ids)} aset berhasil dimutasi.', 'success')
    return redirect(url_for('master_inventory'))

@app.route('/export_inventory')
@login_required
@admin_required
def export_inventory():
    search = request.args.get('search', '')
    filter_kategori = request.args.get('kategori', '')
    filter_tipe = request.args.get('tipe', '')
    filter_lokasi = request.args.get('lokasi', '')
    filter_status = request.args.get('status', '') 
    
    query = Inventory.query.filter_by(is_active=True)
    
    if search:
        query = query.filter(db.or_(
            Inventory.nama_barang.ilike(f"%{search}%"), 
            Inventory.serial_number.ilike(f"%{search}%"), 
            Inventory.kode_barang.ilike(f"%{search}%")
        ))
    if filter_kategori: query = query.filter(Inventory.kategori == filter_kategori)
    if filter_tipe: query = query.filter(Inventory.unit_type == filter_tipe)
    if filter_lokasi: query = query.filter(Inventory.lokasi_id == filter_lokasi)
    if filter_status: query = query.filter(Inventory.notes.ilike(f"%{filter_status}%"))
        
    data_inventory = query.all()

    wb = Workbook()
    ws = wb.active
    ws.title = "Data Inventory"

    thin_border = Border(
        left=Side(style='thin'), right=Side(style='thin'), 
        top=Side(style='thin'), bottom=Side(style='thin')
    )

    headers = ['No', 'Kode Aset', 'Nama Perangkat', 'Serial Number', 'Kategori', 'Tipe Unit', 'Main Location', 'Sub Location', 'Status/Notes', 'Tanggal Register']
    ws.append(headers)
    
    for cell in ws[1]:
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal='center', vertical='center')

    for idx, item in enumerate(data_inventory, 1):
        main_lokasi = item.lokasi.main_lokasi if item.lokasi else "Belum Dialokasikan"
        sub_lokasi = item.lokasi.nama_lokasi if item.lokasi else "-"
        tanggal = item.created_at.strftime('%Y-%m-%d %H:%M:%S') if item.created_at else "-"
        
        ws.append([
            idx,
            item.kode_barang,
            item.nama_barang,
            item.serial_number,
            item.kategori or '-',
            item.unit_type or '-',
            main_lokasi,
            sub_lokasi,
            item.notes or '-',
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
        download_name='Data_Inventory.xlsx'
    )

@app.route('/transaksi_inventory/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def catat_transaksi_inv(id):
    barang = Inventory.query.get_or_404(id)
    if request.method == 'POST':
        lokasi_baru_id = request.form.get('lokasi_id')
        keterangan_form = request.form['keterangan'].strip()
        status_baru = request.form.get('status_aset', '').strip()
        
        nama_lokasi_asal = barang.lokasi.nama_lokasi if barang.lokasi else "Belum Dialokasikan"
        lokasi_tujuan_obj = Lokasi.query.get(lokasi_baru_id) if lokasi_baru_id else None
        nama_lokasi_tujuan = lokasi_tujuan_obj.nama_lokasi if lokasi_tujuan_obj else "Lokasi Tidak Diketahui"
        
        status_tambahan = ""
        if status_baru != (barang.notes or ''):
            barang.notes = status_baru
            status_tambahan = f" [Ubah Status ➔ {status_baru}]"

        keterangan_full = f"[{nama_lokasi_asal} ➔ {nama_lokasi_tujuan}]{status_tambahan} {keterangan_form}".strip()

        db.session.add(Transaksi(inventory_id=barang.id, user_id=current_user.id, jenis='Mutasi', jumlah=1, keterangan=keterangan_full))
        
        if lokasi_baru_id: 
            barang.lokasi_id = lokasi_baru_id
            
        db.session.commit()
        flash('Mutasi Inventory berhasil dicatat.', 'success')
        return redirect(url_for('master_inventory'))
        
    return render_template('transaksi/form_transaksi.html', barang=barang, tipe='inventory', lokasi_list=Lokasi.query.all())

@app.route('/export_riwayat_inventory')
@login_required
@admin_required
def export_riwayat_inventory():
    search = request.args.get('search', '')
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    
    query = Transaksi.query.filter(Transaksi.inventory_id != None)
    
    if search:
        query = query.join(Inventory).filter(
            db.or_(
                Inventory.nama_barang.ilike(f"%{search}%"),
                Inventory.kode_barang.ilike(f"%{search}%"),
                Inventory.serial_number.ilike(f"%{search}%"),
                Transaksi.keterangan.ilike(f"%{search}%")
            )
        )
        
    if start_date: query = query.filter(Transaksi.tanggal >= f"{start_date} 00:00:00")
    if end_date: query = query.filter(Transaksi.tanggal <= f"{end_date} 23:59:59")
        
    data_riwayat = query.order_by(Transaksi.tanggal.desc()).all()

    wb = Workbook()
    ws = wb.active
    ws.title = "Riwayat Inventory"
    thin_border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))

    # Header diperbarui dengan pemisahan Kode, SN, dan penambahan Kategori serta Tipe Unit
    headers = ['No', 'Waktu', 'Kode Aset', 'Serial Number', 'Nama Aset', 'Kategori', 'Tipe Unit', 'Jenis', 'Keterangan', 'PIC (User)']
    ws.append(headers)
    
    for cell in ws[1]:
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal='center', vertical='center')

    for idx, item in enumerate(data_riwayat, 1):
        waktu = item.tanggal.strftime('%Y-%m-%d %H:%M:%S') if item.tanggal else "-"
        
        if item.inventory:
            kode_aset = item.inventory.kode_barang
            serial_number = item.inventory.serial_number
            nama_aset = item.inventory.nama_barang
            kategori = item.inventory.kategori or '-'
            tipe_unit = item.inventory.unit_type or '-'
        else:
            kode_aset = serial_number = nama_aset = kategori = tipe_unit = "-"
            
        # Logika memanggil nama depan atau payroll pengguna
        if item.user:
            pic_name = item.user.nama_lengkap.split(' ')[0] if item.user.nama_lengkap else item.user.payroll
        else:
            pic_name = 'Sistem'
        
        ws.append([
            idx, waktu, kode_aset, serial_number, nama_aset, kategori, tipe_unit, 
            item.jenis, item.keterangan or '-', pic_name
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
    
    return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', as_attachment=True, download_name='Riwayat_Mutasi_Inventory.xlsx')