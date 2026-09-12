"""Deteksi dan pemrosesan format file Excel yang didukung aplikasi."""

from io import BytesIO

from openpyxl import load_workbook

from src.attendance_parser import baca_file_absensi
from src.audit_parser import SHEET_AUDIT, baca_file_audit


def deteksi_jenis_file(file_bytes):
    if not file_bytes:
        raise ValueError("File Excel kosong.")

    try:
        workbook = load_workbook(
            BytesIO(file_bytes), read_only=True, data_only=True
        )
    except Exception as error:
        raise ValueError("File tidak dapat dibuka sebagai Excel .xlsx.") from error

    try:
        nama_sheet = {sheet.title.strip() for sheet in workbook.worksheets}
    finally:
        workbook.close()

    if nama_sheet.intersection(SHEET_AUDIT):
        return "audit"
    if any(name.isdigit() and 1 <= int(name) <= 31 for name in nama_sheet):
        return "fingerprint"

    raise ValueError(
        "Format Excel belum didukung. Gunakan file fingerprint dengan sheet 1–31 "
        "atau file audit dengan sheet PRODUKSI/OFFICE."
    )


def proses_file(file_bytes):
    jenis = deteksi_jenis_file(file_bytes)
    if jenis == "audit":
        return baca_file_audit(file_bytes)

    parsed = baca_file_absensi(file_bytes)
    parsed["jenis"] = "fingerprint"
    return parsed
