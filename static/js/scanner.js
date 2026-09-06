// 1. Script Pencarian Real-time di Tabel
const searchInput = document.getElementById("searchInput");
if (searchInput) {
    searchInput.addEventListener("keyup", function () {
        let filter = this.value.toLowerCase();
        let rows = document.querySelectorAll("#tableBody tr");

        rows.forEach((row) => {
            if (row.cells.length < 2) return;

            // Ambil teks dari kolom Kode (index 1) dan Nama Barang (index 2)
            let kode = row.cells[1].textContent.toLowerCase();
            let nama = row.cells[2].textContent.toLowerCase();

            if (kode.includes(filter) || nama.includes(filter)) {
                row.style.display = "";
            } else {
                row.style.display = "none";
            }
        });
    });
}

// 2. Scanner untuk Pencarian Barcode
let html5QrcodeScanner;
const scannerModal = document.getElementById("scannerModal");

if (scannerModal) {
    scannerModal.addEventListener("shown.bs.modal", function () {
        html5QrcodeScanner = new Html5QrcodeScanner(
            "reader",
            { fps: 10, qrbox: { width: 250, height: 250 } },
            false
        );
        html5QrcodeScanner.render(onScanSuccess, onScanFailure);
    });

    scannerModal.addEventListener("hidden.bs.modal", function () {
        if (html5QrcodeScanner) {
            html5QrcodeScanner.clear();
        }
    });
}

function onScanSuccess(decodedText, decodedResult) {
    html5QrcodeScanner.clear();
    const btnClose = document.getElementById("closeScanner");
    if (btnClose) btnClose.click();

    if (searchInput) {
        searchInput.value = decodedText;
        searchInput.dispatchEvent(new Event("keyup"));
    }
}

function onScanFailure(error) {
    // Abaikan error pembacaan frame per frame dari library
}

// 3. Scanner untuk Transaksi (Otomatis Masuk/Keluar)
let scannerTransaksi;
const modalScanTransaksi = document.getElementById("modalScanTransaksi");
let jenisScanAktif = '';

// Fungsi yang dipanggil oleh tombol di HTML (contoh: onclick="setJenisScan('masuk')")
function setJenisScan(jenis) {
    jenisScanAktif = jenis;
}

if (modalScanTransaksi) {
    modalScanTransaksi.addEventListener("shown.bs.modal", function () {
        scannerTransaksi = new Html5QrcodeScanner(
            "readerTransaksi",
            { fps: 10, qrbox: { width: 250, height: 250 } },
            false
        );
        scannerTransaksi.render(onScanTransaksiSuccess, onScanTransaksiFailure);
    });

    modalScanTransaksi.addEventListener("hidden.bs.modal", function () {
        if (scannerTransaksi) {
            scannerTransaksi.clear();
        }
    });
}

function onScanTransaksiSuccess(decodedText, decodedResult) {
    scannerTransaksi.clear();
    const btnCloseTransaksi = document.getElementById("closeScanTransaksi");
    if (btnCloseTransaksi) btnCloseTransaksi.click();
    
    // Arahkan ke URL transaksi beserta parameter jenis dan kode barang
    window.location.href = "/scan_transaksi/" + jenisScanAktif + "/" + encodeURIComponent(decodedText);
}

function onScanTransaksiFailure(error) {
    // Abaikan error pembacaan frame per frame dari library
}