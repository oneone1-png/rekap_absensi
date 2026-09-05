import calendar
from datetime import date, datetime
from src.special_status import cari_status_khusus



STATUS_HADIR = {
    "HADIR",
    "TERLAMBAT",
    "PULANG AWAL",
    "TERLAMBAT & PULANG AWAL",
}


def jam_ke_menit(jam):
    """Mengubah teks HH:MM menjadi jumlah menit sejak tengah malam."""
    if not jam:
        return None

    if isinstance(jam, (int, float)):
        return int(jam)

    try:
        waktu = datetime.strptime(str(jam).strip(), "%H:%M")
    except (TypeError, ValueError):
        return None

    return waktu.hour * 60 + waktu.minute


def hitung_terlambat(jam_masuk, jam_normal="07:30", toleransi=0):
    masuk = jam_ke_menit(jam_masuk)
    normal = jam_ke_menit(jam_normal)

    if masuk is None or normal is None:
        return 0

    selisih = max(0, masuk - normal)
    return selisih if selisih > max(0, int(toleransi)) else 0


def hitung_pulang_awal(jam_pulang, jam_normal="16:30", toleransi=0):
    pulang = jam_ke_menit(jam_pulang)
    normal = jam_ke_menit(jam_normal)

    if pulang is None or normal is None:
        return 0

    selisih = max(0, normal - pulang)
    return selisih if selisih > max(0, int(toleransi)) else 0


def durasi(start, end):
    mulai = jam_ke_menit(start)
    selesai = jam_ke_menit(end)

    if mulai is None or selesai is None:
        return None

    if selesai < mulai:
        selesai += 24 * 60

    return selesai - mulai


def hitung_jam_kerja(data):
    sesi_pagi = durasi(data.get("pagi_masuk", ""), data.get("pagi_pulang", ""))
    sesi_siang = durasi(data.get("siang_masuk", ""), data.get("siang_pulang", ""))

    if sesi_pagi is None or sesi_siang is None:
        return None

    return sesi_pagi + sesi_siang


def hitung_lembur(data):
    hasil = durasi(data.get("lembur_masuk", ""), data.get("lembur_pulang", ""))
    return hasil if hasil is not None else 0


def menit_ke_jam(menit):
    if menit is None:
        return ""

    menit = int(menit)
    return f"{menit // 60}:{menit % 60:02d}"


def cek_status(data, terlambat=0, pulang_awal=0):
    daftar_scan = [
        data.get("pagi_masuk", ""),
        data.get("pagi_pulang", ""),
        data.get("siang_masuk", ""),
        data.get("siang_pulang", ""),
    ]
    jumlah_scan = sum(bool(scan) for scan in daftar_scan)

    if jumlah_scan == 0:
        return "TIDAK HADIR"
    if jumlah_scan < 4:
        return "SCAN TIDAK LENGKAP"
    if terlambat and pulang_awal:
        return "TERLAMBAT & PULANG AWAL"
    if terlambat:
        return "TERLAMBAT"
    if pulang_awal:
        return "PULANG AWAL"
    return "HADIR"


def _baris_kosong(
        nomor,
        tanggal,
        id_karyawan,
        nama, 
        departemen, 
        tampilkan_identitas,
        status="TIDAK ADA DATA",
        keterangan="",
    ):
     return {
        "No": nomor,
        "Tanggal": tanggal,
        "ID": (
            id_karyawan
            if tampilkan_identitas or nomor == 1
            else ""
        ),
        "Departemen": (
            departemen
            if tampilkan_identitas or nomor == 1
            else ""
        ),
        "Nama": (
            nama
            if tampilkan_identitas or nomor == 1
            else ""
        ),
        "Pagi Masuk": "",
        "Pagi Pulang": "",
        "Siang Masuk": "",
        "Siang Pulang": "",
        "Lembur Masuk": "",
        "Lembur Pulang": "",
        "Jam Lembur": "",
        "Jam Kerja": "",
        "Terlambat": 0,
        "Pulang Awal": 0,
        "Status": status,
        "Keterangan": keterangan,
    }


def buat_rekap_bulanan(
    parsed,
    id_karyawan,
    tahun,
    bulan,
    jam_masuk_normal="07:30",
    jam_pulang_normal="16:30",
    toleransi_terlambat=0,
    toleransi_pulang_awal=0,
    hari_kerja=None,
    tampilkan_identitas_setiap_baris=False,
    status_khusus=None,
):
    """Membuat rincian rekap satu karyawan untuk satu bulan."""
    if id_karyawan not in parsed.get("karyawan", {}):
        raise ValueError(f"ID karyawan {id_karyawan!r} tidak ditemukan")

    if hari_kerja is None:
        hari_kerja = {0, 1, 2, 3, 4}
    else:
        hari_kerja = {int(hari) for hari in hari_kerja}

    if not hari_kerja or not hari_kerja.issubset(set(range(7))):
        raise ValueError("Hari kerja harus berisi angka 0 (Senin) sampai 6 (Minggu)")

    master = parsed["karyawan"][id_karyawan]
    nama = master.get("nama", "")
    departemen = master.get("departemen", "")
    jumlah_hari = calendar.monthrange(int(tahun), int(bulan))[1]
    hasil = []

    for hari in range(1, jumlah_hari + 1):
        tanggal = date(int(tahun), int(bulan), hari)
        if tanggal.weekday() not in hari_kerja:
            continue

        nomor = len(hasil) + 1

        data = parsed.get("data_harian", {}).get(
            hari, {}
            ).get(id_karyawan)

        khusus = cari_status_khusus(
            status_khusus, 
            id_karyawan, 
            tanggal,
        )

        if khusus is not None:
            hasil.append(
                _baris_kosong(
                    nomor,
                    tanggal,
                    id_karyawan,
                    nama,
                    departemen,
                    tampilkan_identitas_setiap_baris,
                    status=khusus.get("status", "TIDAK ADA DATA"),
                    keterangan=khusus.get("keterangan", ""),
                )
            )
            continue

        if data is None:
            hasil.append(
                _baris_kosong(
                    nomor,
                    tanggal,
                    id_karyawan,
                    nama,
                    departemen,
                    tampilkan_identitas_setiap_baris,
                    
                )
            )
            continue

        jam_kerja = hitung_jam_kerja(data)
        lembur = hitung_lembur(data)
        terlambat = hitung_terlambat(
            data.get("pagi_masuk", ""), jam_masuk_normal, toleransi_terlambat
        )
        pulang_awal = hitung_pulang_awal(
            data.get("siang_pulang", ""),
            jam_pulang_normal,
            toleransi_pulang_awal,
        )

        hasil.append(
            {
                "No": nomor,
                "Tanggal": tanggal,
                "ID": (
                    id_karyawan
                    if tampilkan_identitas_setiap_baris or nomor == 1
                    else ""
                ),
                "Departemen": (
                    departemen
                    if tampilkan_identitas_setiap_baris or nomor == 1
                    else ""
                ),
                "Nama": nama if tampilkan_identitas_setiap_baris or nomor == 1 else "",
                "Pagi Masuk": data.get("pagi_masuk", ""),
                "Pagi Pulang": data.get("pagi_pulang", ""),
                "Siang Masuk": data.get("siang_masuk", ""),
                "Siang Pulang": data.get("siang_pulang", ""),
                "Lembur Masuk": data.get("lembur_masuk", ""),
                "Lembur Pulang": data.get("lembur_pulang", ""),
                "Jam Lembur": menit_ke_jam(lembur),
                "Jam Kerja": menit_ke_jam(jam_kerja),
                "Terlambat": terlambat,
                "Pulang Awal": pulang_awal,
                "Status": cek_status(
                    data, 
                    terlambat, 
                    pulang_awal
                ),

                "Keterangan": "",
            }
        )

    return hasil


def buat_rekap_semua_karyawan(parsed, daftar_id, tahun, bulan, **pengaturan):
    hasil = []
    for id_karyawan in daftar_id:
        hasil.extend(
            buat_rekap_bulanan(
                parsed,
                id_karyawan,
                tahun,
                bulan,
                tampilkan_identitas_setiap_baris=True,
                **pengaturan,
            )
        )
    return hasil


def ringkas_rekap(hasil):
    ringkasan = {
        "hari_kerja": len(hasil),
        "hadir": 0,
        "scan_tidak_lengkap": 0,
        "tidak_ada_data": 0,
        "tidak_hadir": 0,

        "izin": 0,
        "sakit": 0,
        "cuti": 0,
        "libur": 0,
        "libur_nasional": 0,
        "cuti_hamil": 0,

        "terlambat": 0,
        "pulang_awal": 0,

        "total_menit_terlambat": 0,
        "total_menit_pulang_awal": 0,
        "total_menit_kerja": 0,
        "total_menit_lembur": 0,
    }

    for baris in hasil:
        status = baris.get(
            "Status",
            "",
        )

        if status in STATUS_HADIR:
            ringkasan["hadir"] += 1

        elif status == "SCAN TIDAK LENGKAP":
            ringkasan[
                "scan_tidak_lengkap"
            ] += 1

        elif status == "TIDAK ADA DATA":
            ringkasan[
                "tidak_ada_data"
            ] += 1

        elif status == "TIDAK HADIR":
            ringkasan[
                "tidak_hadir"
            ] += 1

        elif status == "IZIN":
            ringkasan["izin"] += 1

        elif status == "SAKIT":
            ringkasan["sakit"] += 1

        elif status == "CUTI":
            ringkasan["cuti"] += 1

        elif status == "LIBUR":
            ringkasan["libur"] += 1

        elif status == "LIBUR NASIONAL":
            ringkasan[
                "libur_nasional"
            ] += 1

        elif status == "CUTI HAMIL":
            ringkasan[
                "cuti_hamil"
            ] += 1

        if "TERLAMBAT" in status:
            ringkasan[
                "terlambat"
            ] += 1

        if "PULANG AWAL" in status:
            ringkasan[
                "pulang_awal"
            ] += 1

        ringkasan[
            "total_menit_terlambat"
        ] += int(
            baris.get(
                "Terlambat",
                0,
            ) or 0
        )

        ringkasan[
            "total_menit_pulang_awal"
        ] += int(
            baris.get(
                "Pulang Awal",
                0,
            ) or 0
        )

        ringkasan[
            "total_menit_kerja"
        ] += (
            jam_ke_menit(
                baris.get("Jam Kerja")
            ) or 0
        )

        ringkasan[
            "total_menit_lembur"
        ] += (
            jam_ke_menit(
                baris.get("Jam Lembur")
            ) or 0
        )

    return ringkasan




def buat_ringkasan_karyawan(parsed, daftar_id, tahun, bulan, **pengaturan):
    ringkasan = []
    for nomor, id_karyawan in enumerate(daftar_id, start=1):
        master = parsed["karyawan"][id_karyawan]
        hasil = buat_rekap_bulanan(parsed, id_karyawan, tahun, bulan, **pengaturan)
        total = ringkas_rekap(hasil)
        ringkasan.append(
            {
                "No": nomor,
                "ID": id_karyawan,
                "Nama": master.get("nama", ""),
                "Departemen": master.get("departemen", ""),
                "Hadir": total["hadir"],
                "Terlambat": total["terlambat"],
                "Pulang Awal": total["pulang_awal"],
                "Izin": total["izin"],
                "Sakit": total["sakit"],
                "Cuti": total["cuti"],            
                "Scan Tidak Lengkap": total["scan_tidak_lengkap"],
                "Tidak Hadir": total["tidak_hadir"],
                "Tidak Ada Data": total["tidak_ada_data"],
                "Total Jam Kerja": menit_ke_jam(total["total_menit_kerja"]),
                "Total Jam Lembur": menit_ke_jam(total["total_menit_lembur"]),
            }
        )
    return ringkasan
