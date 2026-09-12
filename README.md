# Sistem Rekap Absensi Karyawan

Aplikasi Streamlit untuk memproses dua jenis file Excel:

1. **Fingerprint** — sheet harian bernama `1` sampai `31`, berisi jam masuk dan pulang.
2. **Audit** — sheet `PRODUKSI` atau `OFFICE`, berisi rekap jam dan status per tanggal.

Format file dideteksi otomatis setelah diunggah.

## Fitur

- Rekap per karyawan dan seluruh karyawan
- Filter unit, departemen, karyawan, dan status
- Perhitungan hadir, terlambat, pulang awal, jam kerja, dan lembur untuk fingerprint
- Input status khusus: `IZIN`, `SAKIT`, `CUTI`, dan `LIBUR`
- Rekap jam hadir, libur dibayar, sakit, cuti, lembur, shift malam, dan uang makan untuk audit
- Ekspor hasil ke Excel
- Tampilan responsif untuk penggunaan lokal dan Streamlit Cloud

## Menjalankan secara lokal

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Buka alamat yang tampil di terminal, biasanya `http://localhost:8501`.

## Menjalankan pengujian

```bash
python -m unittest discover -s tests -v
python -m py_compile app.py src/*.py
```

## Deploy ke Streamlit Cloud

1. Push repository ke GitHub.
2. Buka Streamlit Community Cloud.
3. Pilih repository dan branch `main`.
4. Isi **Main file path** dengan `app.py`.
5. Tekan **Deploy**.

Jika perubahan belum terlihat setelah push, pastikan commit terbaru sudah berada pada branch yang dipakai aplikasi, kemudian pilih **Reboot app** dari pengaturan Streamlit Cloud.

## Struktur proyek

```text
app.py
src/
  attendance_parser.py  # membaca file fingerprint
  attendance_logic.py   # perhitungan fingerprint
  special_status.py     # status izin/sakit/cuti/libur
  audit_parser.py       # membaca file audit
  audit_logic.py        # filter dan ringkasan audit
  audit_export.py       # ekspor audit
  file_parser.py        # deteksi format otomatis
  excel_export.py       # ekspor fingerprint
tests/
  test_attendance.py
```

## Batasan file audit

File audit tidak menyimpan waktu scan masuk dan pulang. Karena itu mode audit tidak menghitung keterlambatan, pulang awal, atau scan tidak lengkap. Mode audit menampilkan data jam dan status yang tersedia pada sumber.
