"""Penyaringan dan peringkasan data audit."""


FIELD_TOTAL = (
    "jam_normal",
    "jam_hadir",
    "libur_dibayar",
    "uang_makan",
    "shift_malam",
    "jam_sakit",
    "cuti_tahunan",
    "cuti_khusus",
    "jam_lembur",
    "uang_makan_lembur",
)


def filter_karyawan_audit(parsed, unit=None, departemen=None):
    hasil = []
    for id_karyawan, data in parsed.get("karyawan", {}).items():
        if unit and data.get("unit") != unit:
            continue
        if departemen and data.get("departemen") != departemen:
            continue
        hasil.append(id_karyawan)
    return sorted(
        hasil,
        key=lambda item: (
            parsed["karyawan"][item].get("nama", "").casefold(), item
        ),
    )


def rincian_karyawan_audit(parsed, id_karyawan, tampilkan_kosong=True):
    if id_karyawan not in parsed.get("karyawan", {}):
        raise ValueError(f"ID karyawan {id_karyawan!r} tidak ditemukan.")

    hasil = [
        row.copy()
        for row in parsed.get("rincian", [])
        if row.get("id") == id_karyawan
        and (tampilkan_kosong or row.get("status") != "TANPA DATA")
    ]
    return sorted(hasil, key=lambda row: row["tanggal"])


def ringkas_audit(rincian):
    total = {field: 0 for field in FIELD_TOTAL}
    total.update(
        {
            "jumlah_karyawan": len({row.get("id") for row in rincian}),
            "hari_hadir": 0,
            "hari_sakit": 0,
            "hari_cuti_tahunan": 0,
            "hari_cuti_khusus": 0,
            "hari_berdata": 0,
        }
    )

    for row in rincian:
        for field in FIELD_TOTAL:
            total[field] += row.get(field, 0) or 0
        total["hari_hadir"] += int((row.get("jam_hadir", 0) or 0) > 0)
        total["hari_sakit"] += int((row.get("jam_sakit", 0) or 0) > 0)
        total["hari_cuti_tahunan"] += int(
            (row.get("cuti_tahunan", 0) or 0) > 0
        )
        total["hari_cuti_khusus"] += int(
            (row.get("cuti_khusus", 0) or 0) > 0
        )
        total["hari_berdata"] += int(row.get("status") != "TANPA DATA")
    return total


def buat_ringkasan_audit(parsed, daftar_id):
    hasil = []
    for nomor, id_karyawan in enumerate(daftar_id, start=1):
        master = parsed["karyawan"][id_karyawan]
        total = ringkas_audit(rincian_karyawan_audit(parsed, id_karyawan))
        hasil.append(
            {
                "No": nomor,
                "ID": id_karyawan,
                "Nama": master.get("nama", ""),
                "Unit": master.get("unit", ""),
                "Departemen": master.get("departemen", ""),
                "Jabatan": master.get("jabatan", ""),
                "Hari Hadir": total["hari_hadir"],
                "Hari Sakit": total["hari_sakit"],
                "Hari Cuti Tahunan": total["hari_cuti_tahunan"],
                "Hari Cuti Khusus": total["hari_cuti_khusus"],
                "Jam Hadir": total["jam_hadir"],
                "Libur Dibayar": total["libur_dibayar"],
                "Jam Standar": total["jam_normal"],
                "Jam Sakit": total["jam_sakit"],
                "Jam Lembur": total["jam_lembur"],
                "Uang Makan": total["uang_makan"],
                "Uang Makan Lembur": total["uang_makan_lembur"],
                "Shift Malam": total["shift_malam"],
            }
        )
    return hasil


def rincian_untuk_tampilan(rincian):
    return [
        {
            "Tanggal": row["tanggal"],
            "ID": row["id"],
            "Nama": row["nama"],
            "Unit": row["unit"],
            "Departemen": row["departemen"],
            "Jabatan": row["jabatan"],
            "Jam Standar": row["jam_normal"],
            "Jam Hadir": row["jam_hadir"],
            "Libur Dibayar": row["libur_dibayar"],
            "Jam Sakit": row["jam_sakit"],
            "Cuti Tahunan": row["cuti_tahunan"],
            "Cuti Khusus": row["cuti_khusus"],
            "Jam Lembur": row["jam_lembur"],
            "Uang Makan": row["uang_makan"],
            "Uang Makan Lembur": row["uang_makan_lembur"],
            "Shift Malam": row["shift_malam"],
            "Status": row["status"],
        }
        for row in rincian
    ]
