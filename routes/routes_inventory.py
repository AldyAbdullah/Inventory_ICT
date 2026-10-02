import io
import pandas as pd
from sqlalchemy import or_
from flask import render_template, request, redirect, url_for, flash, send_file
from flask_login import login_required, current_user

from main import app, admin_required
from models import db, Inventory, MainLokasi, SubLokasi, Transaksi, Karyawan, StatusAset, KategoriBarang

@app.route('/master_inventory', methods=['GET'])
@login_required
def master_inventory():
    search_query = request.args.get('search', '').strip()
    filter_kategori = request.args.get('kategori', '').strip()
    filter_lokasi = request.args.get('lokasi', '').strip()
    filter_status = request.args.get('status', '').strip()
    page = request.args.get('page', 1, type=int)

    query = Inventory.query

    if filter_kategori: query = query.filter_by(kategori_id=filter_kategori)
    if filter_lokasi: query = query.filter_by(lokasi_id=filter_lokasi)
    if filter_status: query = query.filter_by(status_id=filter_status)

    if search_query:
        query = query.filter(or_(
            Inventory.kode_barang.ilike(f'%{search_query}%'),
            Inventory.nama_barang.ilike(f'%{search_query}%'),
            Inventory.brand.ilike(f'%{search_query}%'),
            Inventory.serial_number.ilike(f'%{search_query}%'),
            Inventory.pic_1.has(Karyawan.nama.ilike(f'%{search_query}%')),
            Inventory.pic_1.has(Karyawan.payroll.ilike(f'%{search_query}%')),
            Inventory.pic_2.has(Karyawan.nama.ilike(f'%{search_query}%')),
            Inventory.pic_2.has(Karyawan.payroll.ilike(f'%{search_query}%'))
        ))

    data = query.order_by(Inventory.id.desc()).paginate(page=page, per_page=10, error_out=False)

    base_query = Inventory.query
    kategori_list = KategoriBarang.query.filter_by(jenis='Inventory').order_by(KategoriBarang.nama_kategori.asc()).all()

    lok_q = base_query
    if filter_kategori: lok_q = lok_q.filter_by(kategori_id=filter_kategori)
    if filter_status: lok_q = lok_q.filter_by(status_id=filter_status)
    lokasi_ids = [l[0] for l in lok_q.with_entities(Inventory.lokasi_id).distinct().filter(Inventory.lokasi_id != None).all()]
    lokasi_list = SubLokasi.query.filter(SubLokasi.id.in_(lokasi_ids)).all() if lokasi_ids else []

    stat_q = base_query
    if filter_kategori: stat_q = stat_q.filter_by(kategori_id=filter_kategori)
    if filter_lokasi: stat_q = stat_q.filter_by(lokasi_id=filter_lokasi)
    status_ids = [s[0] for s in stat_q.with_entities(Inventory.status_id).distinct().filter(Inventory.status_id != None).all()]
    status_list = StatusAset.query.filter(StatusAset.id.in_(status_ids)).all() if status_ids else []

    all_inventory = Inventory.query.all()
    total_aset = len(all_inventory)
    
    total_good = total_assigned = total_repair = total_missing = total_broken = 0
    
    for item in all_inventory:
        if item.karyawan_id or item.karyawan_id_2:
            total_assigned += 1
        if item.status_terkait:
            st = item.status_terkait.nama_status.lower()
            if 'good' in st: total_good += 1
            elif 'missing' in st: total_missing += 1
            elif 'broken' in st: total_broken += 1
            elif 'repair' in st: total_repair += 1
                
    pct_good = round((total_good / total_aset * 100), 1) if total_aset > 0 else 0
    pct_assigned = round((total_assigned / total_aset * 100), 1) if total_aset > 0 else 0
    pct_repair = round((total_repair / total_aset * 100), 1) if total_aset > 0 else 0
    pct_missing = round((total_missing / total_aset * 100), 1) if total_aset > 0 else 0
    pct_broken = round((total_broken / total_aset * 100), 1) if total_aset > 0 else 0

    return render_template('inventory/master.html', 
                           data=data, search_query=search_query, 
                           filter_kategori=filter_kategori, filter_lokasi=filter_lokasi, filter_status=filter_status, 
                           kategori_list=kategori_list, lokasi_list=lokasi_list, status_list=status_list, 
                           total_aset=total_aset, 
                           total_good=total_good, pct_good=pct_good,
                           total_assigned=total_assigned, pct_assigned=pct_assigned,
                           total_repair=total_repair, pct_repair=pct_repair,
                           total_missing=total_missing, pct_missing=pct_missing,
                           total_broken=total_broken, pct_broken=pct_broken)

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
        karyawan_id_2 = request.form.get('karyawan_id_2') or None
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

        if karyawan_id or karyawan_id_2:
            main_lok_user = MainLokasi.query.filter_by(nama_main='User / Employee').first()
            if not main_lok_user:
                main_lok_user = MainLokasi(nama_main='User / Employee', keterangan='Sistem Bawaan')
                db.session.add(main_lok_user)
                db.session.flush()
                
            sub_lok_pic = SubLokasi.query.filter_by(main_lokasi_id=main_lok_user.id, nama_sub='-').first()
            if not sub_lok_pic:
                sub_lok_pic = SubLokasi(main_lokasi_id=main_lok_user.id, nama_sub='-')
                db.session.add(sub_lok_pic)
                db.session.flush()
                
            lokasi_id = sub_lok_pic.id

        barang_baru = Inventory(
            kode_barang=kode_barang, serial_number=serial_number, nama_barang=nama_barang,
            brand=brand, vendor=vendor, kategori_id=kategori_id, unit_type=unit_type,
            karyawan_id=karyawan_id, karyawan_id_2=karyawan_id_2, status_id=status_id, lokasi_id=lokasi_id
        )
        db.session.add(barang_baru)
        db.session.flush()

        ket_awal = "Registrasi Aset Baru"
        if not (karyawan_id or karyawan_id_2):
            if lokasi_id:
                lok = SubLokasi.query.get(lokasi_id)
                if lok and lok.main:
                    ket_awal = f"Lokasi: {lok.main.nama_main}" if lok.nama_sub == '-' else f"Lokasi: {lok.main.nama_main} - {lok.nama_sub}"
                else:
                    ket_awal = f"Lokasi: {lok.nama_sub}" if lok else "Lokasi Tidak Diketahui"
            else:
                ket_awal = "Belum Dialokasikan"
                
            if keterangan_tambahan:
                ket_awal += f" | Catatan: {keterangan_tambahan}"

        transaksi_masuk = Transaksi(user_id=current_user.id, inventory_id=barang_baru.id, jenis='Masuk', jumlah=1, keterangan=ket_awal)
        db.session.add(transaksi_masuk)

        if karyawan_id or karyawan_id_2:
            pic_names = []
            if karyawan_id:
                k1 = Karyawan.query.get(karyawan_id)
                if k1: pic_names.append(k1.nama)
            if karyawan_id_2:
                k2 = Karyawan.query.get(karyawan_id_2)
                if k2: pic_names.append(k2.nama)
            
            ket_deliver = f"Diserahkan ke PIC: {' & '.join(pic_names)}"
            if keterangan_tambahan:
                ket_deliver += f" | Catatan: {keterangan_tambahan}"
                
            transaksi_deliver = Transaksi(user_id=current_user.id, inventory_id=barang_baru.id, jenis='Deliver', jumlah=1, keterangan=ket_deliver)
            db.session.add(transaksi_deliver)

        db.session.commit()
        flash('Aset baru berhasil ditambahkan.', 'success')
        return redirect(url_for('tambah_inventory'))

    karyawan_list = Karyawan.query.filter_by(status='Aktif').order_by(Karyawan.nama.asc()).all()
    main_lokasi_list = MainLokasi.query.filter(MainLokasi.nama_main != 'User / Employee').order_by(MainLokasi.nama_main.asc()).all()
    sub_lokasi_list = SubLokasi.query.join(MainLokasi).filter(MainLokasi.nama_main != 'User / Employee').order_by(MainLokasi.nama_main.asc(), SubLokasi.nama_sub.asc()).all()

    return render_template('inventory/tambah.html', karyawan_list=karyawan_list, main_lokasi_list=main_lokasi_list, sub_lokasi_list=sub_lokasi_list, status_list=StatusAset.query.all(), kategori_list=KategoriBarang.query.filter_by(jenis='Inventory').order_by(KategoriBarang.nama_kategori.asc()).all())

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
        old_pic_2_id = barang.karyawan_id_2
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
        
        pic_2_id_raw = request.form.get('karyawan_id_2')
        new_pic_2_id = int(pic_2_id_raw) if pic_2_id_raw and pic_2_id_raw.isdigit() else None
        
        lok_id_raw = request.form.get('lokasi_id')
        new_lokasi_id = int(lok_id_raw) if lok_id_raw and lok_id_raw.isdigit() else None
        
        keterangan_tambahan = request.form.get('keterangan', '').strip()

        if new_pic_id or new_pic_2_id:
            main_lok_user = MainLokasi.query.filter_by(nama_main='User / Employee').first()
            if not main_lok_user:
                main_lok_user = MainLokasi(nama_main='User / Employee', keterangan='Sistem Bawaan')
                db.session.add(main_lok_user)
                db.session.flush()
                
            sub_lok_pic = SubLokasi.query.filter_by(main_lokasi_id=main_lok_user.id, nama_sub='-').first()
            if not sub_lok_pic:
                sub_lok_pic = SubLokasi(main_lokasi_id=main_lok_user.id, nama_sub='-')
                db.session.add(sub_lok_pic)
                db.session.flush()
                
            new_lokasi_id = sub_lok_pic.id

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
        barang.karyawan_id_2 = new_pic_2_id
        barang.lokasi_id = new_lokasi_id

        if perubahan_edit or (keterangan_tambahan and old_pic_id == new_pic_id and old_pic_2_id == new_pic_2_id and old_lokasi_id == new_lokasi_id):
            keterangan_edit = "Edit: " + ", ".join(perubahan_edit) if perubahan_edit else "Edit Data Tambahan"
            if keterangan_tambahan:
                keterangan_edit += f" | Catatan: {keterangan_tambahan}"
            db.session.add(Transaksi(user_id=current_user.id, inventory_id=barang.id, jenis='Edit', jumlah=1, keterangan=keterangan_edit))

        # === LOGIKA BARU: DETEKSI DELIVER, RETRIEVAL, DAN MUTASI ===
        if old_pic_id != new_pic_id or old_pic_2_id != new_pic_2_id or old_lokasi_id != new_lokasi_id:
            ket_transaksi = ""
            jenis_transaksi = "Mutasi" 
            
            # 1. RETRIEVAL (Dari PIC ditarik ke Gudang)
            if (old_pic_id or old_pic_2_id) and not (new_pic_id or new_pic_2_id):
                jenis_transaksi = "Retrieval"
                
                # --- MENYIMPAN DATA PIC LAMA SEBELUM DIHAPUS DARI SISTEM ---
                pic_names = []
                pic_payrolls = []
                if old_pic_id:
                    k1 = Karyawan.query.get(old_pic_id)
                    if k1:
                        pic_names.append(k1.nama)
                        pic_payrolls.append(k1.payroll or '-')
                if old_pic_2_id:
                    k2 = Karyawan.query.get(old_pic_2_id)
                    if k2:
                        pic_names.append(k2.nama)
                        pic_payrolls.append(k2.payroll or '-')
                        
                nama_lama = " / ".join(pic_names) if pic_names else "Pengguna"
                nip_lama = " / ".join(pic_payrolls) if pic_payrolls else "-"
                
                lok = SubLokasi.query.get(new_lokasi_id)
                if lok and lok.main:
                    lok_str = f"ke {lok.main.nama_main}" if lok.nama_sub == '-' else f"ke {lok.main.nama_main} - {lok.nama_sub}"
                else:
                    lok_str = "ke Gudang"
                    
                # Format Sakti agar mudah dipisah di HTML
                ket_transaksi = f"Dari: {nama_lama} | NIP: {nip_lama} | {lok_str}"
                    
            # 2. DELIVER (Diserahkan ke PIC / Ganti PIC)
            elif (new_pic_id or new_pic_2_id) and (old_pic_id != new_pic_id or old_pic_2_id != new_pic_2_id):
                jenis_transaksi = "Deliver"
                pic_names = []
                if new_pic_id:
                    k1 = Karyawan.query.get(new_pic_id)
                    if k1: pic_names.append(k1.nama)
                if new_pic_2_id:
                    k2 = Karyawan.query.get(new_pic_2_id)
                    if k2: pic_names.append(k2.nama)
                ket_transaksi = f"Diserahkan ke PIC: {' & '.join(pic_names)}"
                
            # 3. MUTASI (Hanya pindah gudang)
            elif not (new_pic_id or new_pic_2_id) and not (old_pic_id or old_pic_2_id) and (old_lokasi_id != new_lokasi_id):
                jenis_transaksi = "Mutasi"
                lok = SubLokasi.query.get(new_lokasi_id)
                if lok and lok.main:
                    ket_transaksi = f"Pindah Lokasi: {lok.main.nama_main}" if lok.nama_sub == '-' else f"Pindah Lokasi: {lok.main.nama_main} - {lok.nama_sub}"
                else:
                    ket_transaksi = "Pindah Lokasi Gudang"

            if ket_transaksi:
                if keterangan_tambahan:
                    ket_transaksi += f" | Catatan: {keterangan_tambahan}"
                db.session.add(Transaksi(user_id=current_user.id, inventory_id=barang.id, jenis=jenis_transaksi, jumlah=1, keterangan=ket_transaksi))

        db.session.commit()
        flash('Data Inventory berhasil diperbarui.', 'success')
        return redirect(url_for('edit_inventory', id=id))
        
    riwayat_barang = Transaksi.query.filter_by(inventory_id=id).order_by(Transaksi.tanggal.desc()).all()
    karyawan_list = Karyawan.query.filter_by(status='Aktif').order_by(Karyawan.nama.asc()).all()
    main_lokasi_list = MainLokasi.query.filter(MainLokasi.nama_main != 'User / Employee').order_by(MainLokasi.nama_main.asc()).all()
    sub_lokasi_list = SubLokasi.query.join(MainLokasi).filter(MainLokasi.nama_main != 'User / Employee').order_by(MainLokasi.nama_main.asc(), SubLokasi.nama_sub.asc()).all()
        
    return render_template('inventory/edit.html', barang=barang, riwayat=riwayat_barang, main_lokasi_list=main_lokasi_list, sub_lokasi_list=sub_lokasi_list, karyawan_list=karyawan_list, status_list=StatusAset.query.all(), kategori_list=KategoriBarang.query.filter_by(jenis='Inventory').order_by(KategoriBarang.nama_kategori.asc()).all())

# ... (KODE EXPORT INVENTORY DAN EXPORT RIWAYAT TETAP SAMA) ...
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
        pic_1_name = item.pic_1.nama if item.karyawan_id and item.pic_1 else "-"
        pic_1_payroll = item.pic_1.payroll if item.karyawan_id and item.pic_1 else "-"
        pic_2_name = item.pic_2.nama if item.karyawan_id_2 and item.pic_2 else "-"
        pic_2_payroll = item.pic_2.payroll if item.karyawan_id_2 and item.pic_2 else "-"
        
        if not item.karyawan_id and not item.karyawan_id_2:
            pic_1_name = "ICT ASSET"
            
        data.append({
            'No': i,
            'Kode Aset': item.kode_barang or '-',
            'Nama Perangkat': item.nama_barang or '-',
            'Brand': item.brand or '-',
            'Serial Number': item.serial_number or '-',
            'Kategori': item.kategori_terkait.nama_kategori if item.kategori_id and item.kategori_terkait else '-',
            'PIC 1 Name': pic_1_name,
            'PIC 1 Payroll': pic_1_payroll,
            'PIC 2 Name': pic_2_name,
            'PIC 2 Payroll': pic_2_payroll,
            'Tipe Unit': item.unit_type or '-',
            'Vendor': item.vendor or '-',
            'Main Location': item.lokasi.main.nama_main if item.lokasi and item.lokasi.main else 'Belum Dialokasikan',
            'Sub Location': item.lokasi.nama_sub if item.lokasi else '-',
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
                if col_name in ['No', 'Kode Aset', 'PIC 1 Payroll', 'PIC 2 Payroll', 'Status Aset']:
                    worksheet.write(row_idx + 1, idx, val, center_format)
                else:
                    worksheet.write(row_idx + 1, idx, val, cell_format)

    output.seek(0)
    
    return send_file(output, download_name="Laporan_Data_Inventory.xlsx", as_attachment=True, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

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
    
    return send_file(output, download_name="Laporan_Riwayat_Inventory.xlsx", as_attachment=True, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

@app.route('/cetak_delivery/<int:id>')
@login_required
@admin_required
def cetak_delivery(id):
    tr = Transaksi.query.get_or_404(id)
    if tr.jenis != 'Deliver':
        flash('Dokumen ini hanya untuk transaksi Deliver.', 'danger')
        return redirect(url_for('riwayat_inventory'))
        
    tahun = tr.tanggal.strftime('%Y') if tr.tanggal else '2026'
    no_surat = f"{tr.id:05d}/Tomori/BSD/IDS-S/{tahun}"
    return render_template('inventory/delivery_slip.html', tr=tr, no_surat=no_surat)

@app.route('/cetak_retrieval/<int:id>')
@login_required
@admin_required
def cetak_retrieval(id):
    tr = Transaksi.query.get_or_404(id)
    if tr.jenis != 'Retrieval':
        flash('Dokumen ini hanya untuk transaksi Retrieval.', 'danger')
        return redirect(url_for('riwayat_inventory'))
        
    tahun = tr.tanggal.strftime('%Y') if tr.tanggal else '2026'
    no_surat = f"{tr.id:05d}/Tomori/BSD/IRS-S/{tahun}" # Sesuai format gambar
    return render_template('inventory/retrieval_slip.html', tr=tr, no_surat=no_surat)