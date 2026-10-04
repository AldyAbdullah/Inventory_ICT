import io
import json
import uuid
import pandas as pd
from sqlalchemy import or_
from flask import render_template, request, redirect, url_for, flash, send_file
from flask_login import login_required, current_user

from main import app, admin_required
from models import db, Inventory, MainLokasi, SubLokasi, Transaksi, Karyawan, StatusAset, KategoriBarang, Consumable

@app.route('/master_inventory', methods=['GET'])
@login_required
def master_inventory():
    search_query = request.args.get('search', '').strip()
    filter_kategori = request.args.get('kategori', '').strip()
    filter_lokasi = request.args.get('lokasi', '').strip()
    filter_status = request.args.get('status', '').strip()

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

    data = query.order_by(Inventory.id.desc()).all()

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
        
        # Array Bundling Consumable
        bundle_cons_ids = request.form.getlist('bundle_cons_id[]')
        bundle_cons_qtys = request.form.getlist('bundle_cons_qty[]')
        
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

        # TRANSAKSI: EDIT (TERPISAH)
        if perubahan_edit or (keterangan_tambahan and old_pic_id == new_pic_id and old_pic_2_id == new_pic_2_id and old_lokasi_id == new_lokasi_id):
            keterangan_edit = "Edit: " + ", ".join(perubahan_edit) if perubahan_edit else "Edit Data Tambahan"
            if keterangan_tambahan:
                keterangan_edit += f" | Catatan: {keterangan_tambahan}"
            db.session.add(Transaksi(user_id=current_user.id, inventory_id=barang.id, jenis='Edit', jumlah=1, keterangan=keterangan_edit))

        # ========================================================
        # TRANSAKSI: MUTASI & BUNDLING CONSUMABLE
        # ========================================================
        if old_pic_id != new_pic_id or old_pic_2_id != new_pic_2_id or old_lokasi_id != new_lokasi_id:
            ket_transaksi = ""
            jenis_transaksi = "Mutasi" 
            
            # CEK KELENGKAPAN CONSUMABLE YANG VALID DULU (Agar tidak terjadi Badge Bundling Palsu)
            valid_bundles = []
            if bundle_cons_ids:
                for i in range(len(bundle_cons_ids)):
                    c_id_str = bundle_cons_ids[i]
                    qty_str = bundle_cons_qtys[i] if i < len(bundle_cons_qtys) else '1'
                    
                    if c_id_str and qty_str.isdigit():
                        qty = int(qty_str)
                        if qty > 0:
                            cons = Consumable.query.get(int(c_id_str))
                            if cons:
                                valid_bundles.append({'cons': cons, 'qty': qty})
                                
            # Buat grup_id HANYA jika benar-benar ada Consumable yang valid
            grup_id = str(uuid.uuid4()) if valid_bundles else None
            
            # MODE: RETRIEVAL (KEMBALI KE GUDANG)
            if (old_pic_id or old_pic_2_id) and not (new_pic_id or new_pic_2_id):
                jenis_transaksi = "Retrieval"
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
                    lok_sub = f" - {lok.nama_sub}" if lok.nama_sub != '-' else ""
                    lok_str = f"ke {lok.main.nama_main}{lok_sub}"
                else:
                    lok_str = "ke Gudang"
                    
                ket_transaksi = f"Dari: {nama_lama} | NIP: {nip_lama} | {lok_str}"
                    
            # MODE: DELIVER (DISERAHKAN KE PIC)
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
                
            # MODE: MUTASI LOKASI GUDANG (Tanpa PIC)
            elif not (new_pic_id or new_pic_2_id) and not (old_pic_id or old_pic_2_id) and (old_lokasi_id != new_lokasi_id):
                jenis_transaksi = "Mutasi"
                
                # PERBAIKAN FORMAT MUTASI: Lokasi Awal ➔ Lokasi Baru
                old_lok = SubLokasi.query.get(old_lokasi_id) if old_lokasi_id else None
                new_lok = SubLokasi.query.get(new_lokasi_id) if new_lokasi_id else None
                
                old_sub = f" - {old_lok.nama_sub}" if old_lok and old_lok.nama_sub != '-' else ""
                new_sub = f" - {new_lok.nama_sub}" if new_lok and new_lok.nama_sub != '-' else ""
                
                old_str = f"{old_lok.main.nama_main}{old_sub}" if old_lok and old_lok.main else "Lokasi Awal"
                new_str = f"{new_lok.main.nama_main}{new_sub}" if new_lok and new_lok.main else "Lokasi Baru"
                
                ket_transaksi = f"{old_str} ➔ {new_str}"

            # SIMPAN TRANSAKSI INVENTORY (INDUK)
            if ket_transaksi:
                if keterangan_tambahan:
                    ket_transaksi += f" | Catatan: {keterangan_tambahan}"
                db.session.add(Transaksi(user_id=current_user.id, inventory_id=barang.id, jenis=jenis_transaksi, jumlah=1, keterangan=ket_transaksi, grup_id=grup_id))

                # PROSES KELENGKAPAN CONSUMABLE (ANAK/BUNDLE)
                if valid_bundles and jenis_transaksi in ['Deliver', 'Retrieval']:
                    for bundle in valid_bundles:
                        cons = bundle['cons']
                        qty = bundle['qty']
                        
                        if jenis_transaksi == 'Deliver':
                            if cons.stok < qty:
                                flash(f'Peringatan: Stok {cons.nama_barang} tidak cukup. Kelengkapan ini dibatalkan secara otomatis.', 'warning')
                                continue 
                            
                            cons.stok -= qty
                            pic_names = []
                            if new_pic_id: pic_names.append(Karyawan.query.get(new_pic_id).nama)
                            if new_pic_2_id: pic_names.append(Karyawan.query.get(new_pic_2_id).nama)
                            nama_pic = " & ".join(pic_names) if pic_names else "PIC"
                            
                            ket_cons = f"Kelengkapan untuk {barang.nama_barang} ({barang.kode_barang}) ke PIC: {nama_pic}."
                            db.session.add(Transaksi(user_id=current_user.id, consumable_id=cons.id, jenis='Keluar', jumlah=qty, keterangan=ket_cons, grup_id=grup_id))
                            
                        elif jenis_transaksi == 'Retrieval':
                            cons.stok += qty
                            ket_cons = f"Dikembalikan ke gudang bersama penarikan {barang.nama_barang} ({barang.kode_barang})."
                            db.session.add(Transaksi(user_id=current_user.id, consumable_id=cons.id, jenis='Masuk', jumlah=qty, keterangan=ket_cons, grup_id=grup_id))

        db.session.commit()
        flash('Data Inventory berhasil diperbarui.', 'success')
        return redirect(url_for('edit_inventory', id=id))
        
    riwayat_barang = Transaksi.query.filter_by(inventory_id=id).order_by(Transaksi.tanggal.desc()).all()
    karyawan_list = Karyawan.query.filter_by(status='Aktif').order_by(Karyawan.nama.asc()).all()
    main_lokasi_list = MainLokasi.query.filter(MainLokasi.nama_main != 'User / Employee').order_by(MainLokasi.nama_main.asc()).all()
    sub_lokasi_list = SubLokasi.query.join(MainLokasi).filter(MainLokasi.nama_main != 'User / Employee').order_by(MainLokasi.nama_main.asc(), SubLokasi.nama_sub.asc()).all()
        
    cns_data = []
    for c in Consumable.query.filter_by(is_active=True).order_by(Consumable.nama_barang.asc()).all():
        satuan_nama = c.satuan_terkait.nama_satuan if c.satuan_terkait else 'Unit'
        cns_data.append({
            'id': c.id,
            'text': f"{c.nama_barang} (Sisa: {c.stok} {satuan_nama})"
        })
    all_consumables_json = json.dumps(cns_data)

    return render_template('inventory/edit.html', 
                           barang=barang, 
                           riwayat=riwayat_barang, 
                           main_lokasi_list=main_lokasi_list, 
                           sub_lokasi_list=sub_lokasi_list, 
                           karyawan_list=karyawan_list, 
                           status_list=StatusAset.query.all(), 
                           kategori_list=KategoriBarang.query.filter_by(jenis='Inventory').order_by(KategoriBarang.nama_kategori.asc()).all(),
                           all_consumables_json=all_consumables_json)

@app.route('/mutasi_massal', methods=['POST'])
@login_required
@admin_required
def mutasi_massal():
    # Ambil daftar ID barang yang dicentang
    selected_ids = request.form.get('selected_ids', '')
    if not selected_ids:
        flash('Gagal! Tidak ada aset yang dipilih.', 'danger')
        return redirect(url_for('master_inventory'))

    id_list = [int(i.strip()) for i in selected_ids.split(',') if i.strip().isdigit()]
    if not id_list:
        flash('Gagal! Format ID tidak valid.', 'danger')
        return redirect(url_for('master_inventory'))

    # Ambil data form tujuan mutasi
    karyawan_id_raw = request.form.get('karyawan_id')
    karyawan_id_2_raw = request.form.get('karyawan_id_2')
    lokasi_id_raw = request.form.get('lokasi_id')
    catatan_massal = request.form.get('keterangan', '').strip()

    new_pic_id = int(karyawan_id_raw) if karyawan_id_raw and karyawan_id_raw.isdigit() else None
    new_pic_2_id = int(karyawan_id_2_raw) if karyawan_id_2_raw and karyawan_id_2_raw.isdigit() else None
    new_lokasi_id = int(lokasi_id_raw) if lokasi_id_raw and lokasi_id_raw.isdigit() else None

    # Jika diserahkan ke PIC, pastikan lokasinya adalah 'User / Employee' -> '-'
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

    berhasil = 0
    # Proses mutasi untuk setiap aset yang dipilih
    for item_id in id_list:
        barang = Inventory.query.get(item_id)
        if not barang:
            continue

        old_pic_id = barang.karyawan_id
        old_pic_2_id = barang.karyawan_id_2
        old_lokasi_id = barang.lokasi_id

        # Cegah mutasi ganda jika tujuan sama dengan lokasi saat ini
        if old_pic_id == new_pic_id and old_pic_2_id == new_pic_2_id and old_lokasi_id == new_lokasi_id:
            continue

        # Tentukan jenis mutasi
        ket_transaksi = ""
        jenis_transaksi = "Mutasi"

        # MODE: RETRIEVAL (KEMBALI KE GUDANG DARI PIC)
        if (old_pic_id or old_pic_2_id) and not (new_pic_id or new_pic_2_id):
            jenis_transaksi = "Retrieval"
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
                lok_sub = f" - {lok.nama_sub}" if lok.nama_sub != '-' else ""
                lok_str = f"ke {lok.main.nama_main}{lok_sub}"
            else:
                lok_str = "ke Gudang"
                
            ket_transaksi = f"Dari: {nama_lama} | NIP: {nip_lama} | {lok_str}"

        # MODE: DELIVER (DISERAHKAN KE PIC)
        elif (new_pic_id or new_pic_2_id):
            jenis_transaksi = "Deliver"
            pic_names = []
            if new_pic_id:
                k1 = Karyawan.query.get(new_pic_id)
                if k1: pic_names.append(k1.nama)
            if new_pic_2_id:
                k2 = Karyawan.query.get(new_pic_2_id)
                if k2: pic_names.append(k2.nama)
            ket_transaksi = f"Diserahkan ke PIC: {' & '.join(pic_names)}"

        # MODE: MUTASI GUDANG (Tanpa PIC)
        else:
            jenis_transaksi = "Mutasi"
            old_lok = SubLokasi.query.get(old_lokasi_id) if old_lokasi_id else None
            new_lok = SubLokasi.query.get(new_lokasi_id) if new_lokasi_id else None
            
            old_sub = f" - {old_lok.nama_sub}" if old_lok and old_lok.nama_sub != '-' else ""
            new_sub = f" - {new_lok.nama_sub}" if new_lok and new_lok.nama_sub != '-' else ""
            
            old_str = f"{old_lok.main.nama_main}{old_sub}" if old_lok and old_lok.main else "Lokasi Awal"
            new_str = f"{new_lok.main.nama_main}{new_sub}" if new_lok and new_lok.main else "Lokasi Baru"
            
            ket_transaksi = f"{old_str} ➔ {new_str}"

        # Terapkan perubahan ke database
        barang.karyawan_id = new_pic_id
        barang.karyawan_id_2 = new_pic_2_id
        barang.lokasi_id = new_lokasi_id

        if catatan_massal:
            ket_transaksi += f" | Catatan: {catatan_massal}"
            
        db.session.add(Transaksi(user_id=current_user.id, inventory_id=barang.id, jenis=jenis_transaksi, jumlah=1, keterangan=ket_transaksi))
        berhasil += 1

    db.session.commit()
    
    if berhasil > 0:
        flash(f'Sukses! {berhasil} Aset berhasil dimutasi.', 'success')
    else:
        flash('Tidak ada aset yang dimutasi (Semua aset sudah berada di tujuan yang sama).', 'warning')
        
    return redirect(url_for('master_inventory'))

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
    
    bundle_trx = []
    if tr.grup_id:
        bundle_trx = Transaksi.query.filter_by(grup_id=tr.grup_id).filter(Transaksi.consumable_id != None).all()
        
    return render_template('inventory/delivery_slip.html', tr=tr, no_surat=no_surat, bundle_trx=bundle_trx)

@app.route('/cetak_retrieval/<int:id>')
@login_required
@admin_required
def cetak_retrieval(id):
    tr = Transaksi.query.get_or_404(id)
    if tr.jenis != 'Retrieval':
        flash('Dokumen ini hanya untuk transaksi Retrieval.', 'danger')
        return redirect(url_for('riwayat_inventory'))
        
    tahun = tr.tanggal.strftime('%Y') if tr.tanggal else '2026'
    no_surat = f"{tr.id:05d}/Tomori/BSD/IRS-S/{tahun}" 
    
    bundle_trx = []
    if tr.grup_id:
        bundle_trx = Transaksi.query.filter_by(grup_id=tr.grup_id).filter(Transaksi.consumable_id != None).all()
        
    return render_template('inventory/retrieval_slip.html', tr=tr, no_surat=no_surat, bundle_trx=bundle_trx)

# ==========================================
# FITUR IMPORT EXCEL INVENTORY (DENGAN DROPDOWN)
# ==========================================

@app.route('/download_template_inventory')
@login_required
@admin_required
def download_template_inventory():
    kolom = ['Kode Barang', 'Nama Barang', 'Brand', 'Serial Number', 'Tipe Unit', 'Vendor', 'Kategori', 'Status', 'Payroll PIC 1', 'Payroll PIC 2', 'Main Lokasi', 'Sub Lokasi']
    df = pd.DataFrame(columns=kolom)
    
    kategori_list = [k.nama_kategori for k in KategoriBarang.query.filter_by(jenis='Inventory').order_by(KategoriBarang.nama_kategori.asc()).all()]
    status_list = [s.nama_status for s in StatusAset.query.order_by(StatusAset.nama_status.asc()).all()]
    main_lokasi_list = [m.nama_main for m in MainLokasi.query.order_by(MainLokasi.nama_main.asc()).all()]
    sub_lokasi_list = list(set([s.nama_sub for s in SubLokasi.query.all()]))
    sub_lokasi_list.sort()
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Template_Import')
        workbook = writer.book
        worksheet = writer.sheets['Template_Import']
        
        header_format = workbook.add_format({'bold': True, 'bg_color': '#0a2540', 'font_color': 'white', 'border': 1})
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, header_format)
            worksheet.set_column(col_num, col_num, 20)
            
        ref_sheet = workbook.add_worksheet('Referensi')
        ref_sheet.hide() 
        
        if kategori_list:
            ref_sheet.write_column('A2', kategori_list)
            worksheet.data_validation('G2:G1000', {'validate': 'list', 'source': f'=Referensi!$A$2:$A${len(kategori_list)+1}'})
            
        if status_list:
            ref_sheet.write_column('B2', status_list)
            worksheet.data_validation('H2:H1000', {'validate': 'list', 'source': f'=Referensi!$B$2:$B${len(status_list)+1}'})
            
        if main_lokasi_list:
            ref_sheet.write_column('C2', main_lokasi_list)
            worksheet.data_validation('K2:K1000', {'validate': 'list', 'source': f'=Referensi!$C$2:$C${len(main_lokasi_list)+1}'})
            
        if sub_lokasi_list:
            ref_sheet.write_column('D2', sub_lokasi_list)
            worksheet.data_validation('L2:L1000', {'validate': 'list', 'source': f'=Referensi!$D$2:$D${len(sub_lokasi_list)+1}'})
            
    output.seek(0)
    return send_file(output, download_name="Template_Import_Inventory.xlsx", as_attachment=True)

@app.route('/import_inventory', methods=['POST'])
@login_required
@admin_required
def import_inventory():
    if 'file' not in request.files:
        flash('Tidak ada file yang dipilih.', 'danger')
        return redirect(url_for('master_inventory'))
        
    file = request.files['file']
    if file.filename == '':
        flash('File tidak valid.', 'danger')
        return redirect(url_for('master_inventory'))
        
    try:
        df = pd.read_excel(file)
        
        required_cols = ['Kode Barang', 'Nama Barang', 'Serial Number']
        for col in required_cols:
            if col not in df.columns:
                flash(f'Gagal: Kolom wajib "{col}" tidak ditemukan di file Excel.', 'danger')
                return redirect(url_for('master_inventory'))
                
        berhasil = 0
        gagal = 0
        
        for index, row in df.iterrows():
            val_kode = row.get('Kode Barang')
            val_nama = row.get('Nama Barang')
            val_sn = row.get('Serial Number')
            
            kode = str(val_kode).strip() if pd.notna(val_kode) else ''
            nama = str(val_nama).strip() if pd.notna(val_nama) else ''
            sn = str(val_sn).strip() if pd.notna(val_sn) else ''
            
            if not kode or not nama or not sn:
                gagal += 1
                continue
                
            if Inventory.query.filter_by(kode_barang=kode).first() or Inventory.query.filter_by(serial_number=sn).first():
                gagal += 1
                continue
                
            val_brand = row.get('Brand')
            val_tipe = row.get('Tipe Unit')
            val_vendor = row.get('Vendor')
            brand = str(val_brand).strip() if pd.notna(val_brand) else ''
            tipe = str(val_tipe).strip() if pd.notna(val_tipe) else ''
            vendor = str(val_vendor).strip() if pd.notna(val_vendor) else ''
            
            val_kat = row.get('Kategori')
            kat_nama = str(val_kat).strip() if pd.notna(val_kat) else ''
            kategori_id = None
            if kat_nama:
                kat = KategoriBarang.query.filter(KategoriBarang.nama_kategori.ilike(kat_nama), KategoriBarang.jenis=='Inventory').first()
                if not kat:
                    kat = KategoriBarang(nama_kategori=kat_nama, jenis='Inventory')
                    db.session.add(kat)
                    db.session.flush()
                kategori_id = kat.id
                
            val_stat = row.get('Status')
            stat_nama = str(val_stat).strip() if pd.notna(val_stat) else ''
            status_id = None
            if stat_nama:
                stat = StatusAset.query.filter(StatusAset.nama_status.ilike(stat_nama)).first()
                if not stat:
                    stat = StatusAset(nama_status=stat_nama)
                    db.session.add(stat)
                    db.session.flush()
                status_id = stat.id
                
            val_pic1 = row.get('Payroll PIC 1')
            val_pic2 = row.get('Payroll PIC 2')
            pic1_payroll = str(val_pic1).strip() if pd.notna(val_pic1) else ''
            pic2_payroll = str(val_pic2).strip() if pd.notna(val_pic2) else ''
            
            karyawan_id = None
            karyawan_id_2 = None
            
            if pic1_payroll:
                kar1 = Karyawan.query.filter_by(payroll=pic1_payroll).first()
                if kar1: karyawan_id = kar1.id
                
            if pic2_payroll:
                kar2 = Karyawan.query.filter_by(payroll=pic2_payroll).first()
                if kar2: karyawan_id_2 = kar2.id
                
            val_main = row.get('Main Lokasi')
            val_sub = row.get('Sub Lokasi')
            lok_main_nama = str(val_main).strip() if pd.notna(val_main) else ''
            lok_sub_nama = str(val_sub).strip() if pd.notna(val_sub) else '-'
            lokasi_id = None
            
            if karyawan_id or karyawan_id_2:
                main_user = MainLokasi.query.filter_by(nama_main='User / Employee').first()
                if not main_user:
                    main_user = MainLokasi(nama_main='User / Employee', keterangan='Sistem Bawaan')
                    db.session.add(main_user)
                    db.session.flush()
                sub_user = SubLokasi.query.filter_by(main_lokasi_id=main_user.id, nama_sub='-').first()
                if not sub_user:
                    sub_user = SubLokasi(main_lokasi_id=main_user.id, nama_sub='-')
                    db.session.add(sub_user)
                    db.session.flush()
                lokasi_id = sub_user.id
            elif lok_main_nama:
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
                
            inv = Inventory(
                kode_barang=kode, nama_barang=nama, brand=brand, serial_number=sn,
                unit_type=tipe, vendor=vendor, kategori_id=kategori_id, status_id=status_id,
                karyawan_id=karyawan_id, karyawan_id_2=karyawan_id_2, lokasi_id=lokasi_id,
                is_active=True
            )
            db.session.add(inv)
            db.session.flush()
            
            ket_masuk = "Registrasi via Import Excel massal."
            trx_masuk = Transaksi(user_id=current_user.id, inventory_id=inv.id, jenis='Masuk', jumlah=1, keterangan=ket_masuk)
            db.session.add(trx_masuk)
            
            if karyawan_id or karyawan_id_2:
                pic_names = []
                if karyawan_id: pic_names.append(Karyawan.query.get(karyawan_id).nama)
                if karyawan_id_2: pic_names.append(Karyawan.query.get(karyawan_id_2).nama)
                
                ket_deliver = f"Diserahkan ke PIC: {' & '.join(pic_names)} | Catatan: Auto Deliver via Excel"
                trx_deliver = Transaksi(user_id=current_user.id, inventory_id=inv.id, jenis='Deliver', jumlah=1, keterangan=ket_deliver)
                db.session.add(trx_deliver)
                
            berhasil += 1
            
        db.session.commit()
        if berhasil > 0:
            flash(f'Import Sukses! {berhasil} aset ditambahkan. {gagal} baris dilewati (duplikat/tidak valid).', 'success')
        else:
            flash(f'Gagal: Tidak ada data valid yang diimport. {gagal} baris bermasalah.', 'warning')
            
    except Exception as e:
        db.session.rollback()
        flash(f'Sistem gagal membaca isi Excel Anda. Error Code: {str(e)}', 'danger')
        
    return redirect(url_for('master_inventory'))