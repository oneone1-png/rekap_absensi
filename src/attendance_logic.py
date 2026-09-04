from datetime import datetime, date
import calendar


def jam_ke_menit(jam):
    if not jam:
        return None

    try:
        waktu = datetime.strptime(jam, "%H:%M")
        return waktu.hour * 60 + waktu.minute
    except ValueError:
        return None


def hitung_terlambat(jam_masuk, jam_normal="07:30"):
    masuk = jam_ke_menit(jam_masuk)
    normal = jam_ke_menit(jam_normal)

    if masuk is None:
        return 0

    return max(0, masuk - normal)


def hitung_pulang_awal(jam_pulang, jam_normal="16:30"):
    pulang = jam_ke_menit(jam_pulang)
    normal = jam_ke_menit(jam_normal)

    if pulang is None:
        return 0

    return max(0, normal - pulang)


def durasi(start, end):
    mulai = jam_ke_menit(start)
    selesai = jam_ke_menit(end)

    if mulai is None or selesai is None:
        return None

    # Jika melewati tengah malam
    if selesai < mulai:
        selesai += 24 * 60

    return selesai - mulai


def hitung_jam_kerja(data):
    sesi_pagi = durasi(
        data.get("pagi_masuk", ""),
        data.get("pagi_pulang", "")
    )

    sesi_siang = durasi(
        data.get("siang_masuk", ""),
        data.get("siang_pulang", "")
    )

    if sesi_pagi is None or sesi_siang is None:
        return None

    return sesi_pagi + sesi_siang


def hitung_lembur(data):
    masuk = data.get("lembur_masuk", "")
    pulang = data.get("lembur_pulang", "")

    if not masuk or not pulang:
        return 0

    hasil = durasi(masuk, pulang)

    if hasil is None:
        return 0

    return hasil


def menit_ke_jam(menit):
    if menit is None:
        return ""

    jam = menit // 60
    sisa_menit = menit % 60

    return f"{jam}:{sisa_menit:02d}"


def cek_status(data):
    pagi_masuk = data.get("pagi_masuk", "")
    pagi_pulang = data.get("pagi_pulang", "")
    siang_masuk = data.get("siang_masuk", "")
    siang_pulang = data.get("siang_pulang", "")

    daftar_scan = [
        pagi_masuk,
        pagi_pulang,
        siang_masuk,
        siang_pulang
    ]

    jumlah_scan = sum(
        1 for scan in daftar_scan if scan
    )

    if jumlah_scan == 0:
        return "TIDAK HADIR"

    if jumlah_scan < 4:
        return "SCAN TIDAK LENGKAP"

    return "HADIR"


# MEMBUAT LAPORAN BULANAN

def buat_rekap_bulanan(
    parsed,
    id_karyawan,
    tahun,
    bulan
):
    hasil = []

    jumlah_hari = calendar.monthrange(
        tahun,
        bulan
    )[1]

    nomor = 1

    # Ambil data master karyawan
    master = parsed["karyawan"].get(
        id_karyawan,
        {}
    )

    nama = master.get("nama", "")
    departemen = master.get("departemen", "")

    for hari in range(1, jumlah_hari + 1):

        tanggal = date(
            tahun,
            bulan,
            hari
        )

        # Lewati Sabtu dan Minggu
        if tanggal.weekday() >= 5:
            continue

        data = parsed["data_harian"].get(
            hari, {}
        ).get(id_karyawan)

        # ==============================
        # TIDAK ADA DATA
        # ==============================
        if data is None:

            hasil.append({
                "No": nomor,
                "Tanggal": tanggal,

                "ID": (
                    id_karyawan
                    if nomor == 1
                    else ""
                ),

                "Departemen": (
                    departemen
                    if nomor == 1
                    else ""
                ),

                "Nama": (
                    nama
                    if nomor == 1
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

                "Status": "TIDAK ADA DATA"
            })

        # ==============================
        # ADA DATA
        # ==============================
        else:

            jam_kerja = hitung_jam_kerja(data)
            lembur = hitung_lembur(data)

            hasil.append({
                "No": nomor,
                "Tanggal": tanggal,

                "ID": (
                    id_karyawan
                    if nomor == 1
                    else ""
                ),

                "Departemen": (
                    departemen
                    if nomor == 1
                    else ""
                ),

                "Nama": (
                    nama
                    if nomor == 1
                    else ""
                ),

                "Pagi Masuk":
                    data.get(
                        "pagi_masuk",
                        ""
                    ),

                "Pagi Pulang":
                    data.get(
                        "pagi_pulang",
                        ""
                    ),

                "Siang Masuk":
                    data.get(
                        "siang_masuk",
                        ""
                    ),

                "Siang Pulang":
                    data.get(
                        "siang_pulang",
                        ""
                    ),

                "Lembur Masuk":
                    data.get(
                        "lembur_masuk",
                        ""
                    ),

                "Lembur Pulang":
                    data.get(
                        "lembur_pulang",
                        ""
                    ),

                "Jam Lembur":
                    menit_ke_jam(lembur),

                "Jam Kerja":
                    menit_ke_jam(
                        jam_kerja
                    ),

                "Terlambat":
                    hitung_terlambat(
                        data.get(
                            "pagi_masuk",
                            ""
                        )
                    ),

                "Pulang Awal":
                    hitung_pulang_awal(
                        data.get(
                            "siang_pulang",
                            ""
                        )
                    ),

                "Status":
                    cek_status(data)
            })

        nomor += 1

    return hasil