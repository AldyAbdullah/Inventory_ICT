// 1. Script Pencarian Real-time (AJAX + Debounce)
const searchInput = document.getElementById("searchInput");
const tableContainer = document.getElementById("tabelBarangContainer");
let debounceTimer;

if (searchInput && tableContainer) {
    searchInput.addEventListener("input", function () {
        clearTimeout(debounceTimer);
        let query = this.value;

        // Debounce: Tunggu pengguna selesai mengetik selama 300ms sebelum request ke server
        debounceTimer = setTimeout(() => {
            tableContainer.style.opacity = "0.5"; // Efek visual memuat data

            // Melakukan request ke server tanpa me-refresh halaman
            fetch(`/master_barang?search=${encodeURIComponent(query)}`)
                .then(response => response.text())
                .then(html => {
                    let parser = new DOMParser();
                    let doc = parser.parseFromString(html, "text/html");
                    let newContainer = doc.getElementById("tabelBarangContainer");

                    if (newContainer) {
                        // Mengganti isi tabel lama dengan hasil pencarian baru dari server
                        tableContainer.innerHTML = newContainer.innerHTML;
                    }
                    tableContainer.style.opacity = "1"; // Mengembalikan efek visual
                })
                .catch(error => {
                    console.error("Gagal memuat data:", error);
                    tableContainer.style.opacity = "1";
                });
        }, 300);
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
        // Memicu event 'input' secara terprogram agar pencarian AJAX otomatis berjalan
        searchInput.dispatchEvent(new Event("input"));
    }
}

function onScanFailure(error) {
    // Abaikan error pembacaan frame per frame dari library
}

// 3. Scanner untuk Transaksi (Otomatis Masuk/Keluar)
let scannerTransaksi;
const modalScanTransaksi = document.getElementById("modalScanTransaksi");
let jenisScanAktif = '';

// Fungsi yang dipanggil oleh tombol di HTML
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