from datetime import date, datetime


STATUS_VALID = {
    "IZIN",
    "SAKIT",
    "CUTI",
    "LIBUR",
    "LIBUR NASIONAL",
    "CUTI HAMIL",
}


def normalisasi_tanggal(value):
    if value is None or value == "":
        return None

    # Mendukung Timestamp dari pandas
    if hasattr(value, "to_pydatetime"):
        value = value.to_pydatetime()

    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    try:
        return datetime.fromisoformat(
            str(value)
        ).date()
    except ValueError:
        return None


def buat_peta_status(records):
    """
    Mengubah tabel status khusus menjadi dictionary.
    """

    hasil = {}

    for record in records:
        tanggal = normalisasi_tanggal(
            record.get("Tanggal")
        )

        id_karyawan = str(
            record.get(
                "ID Karyawan",
                "",
            )
        ).strip()

        status = str(
            record.get(
                "Status",
                "",
            )
        ).strip().upper()

        keterangan = str(
            record.get(
                "Keterangan",
                "",
            )
        ).strip()

        # Continue harus berada di dalam for
        if (
            not tanggal
            or not id_karyawan
            or not status
        ):
            continue

        if status not in STATUS_VALID:
            raise ValueError(
                f"Status {status!r} tidak dikenal."
            )

        # SEMUA digunakan untuk libur perusahaan
        if id_karyawan.upper() == "SEMUA":
            id_karyawan = "*"

        hasil[
            (id_karyawan, tanggal)
        ] = {
            "status": status,
            "keterangan": keterangan,
        }

    return hasil


def cari_status_khusus(
    peta_status,
    id_karyawan,
    tanggal,
):
    if not peta_status:
        return None

    # Cari status khusus karyawan terlebih dahulu
    status_karyawan = peta_status.get(
        (id_karyawan, tanggal)
    )

    if status_karyawan:
        return status_karyawan

    # Tanda * berarti berlaku untuk semua karyawan
    return peta_status.get(
        ("*", tanggal)
    )