from datetime import date, time, timedelta
from src.special_status import buat_peta_status

import re

import pandas as pd
import streamlit as st

from src.attendance_logic import (
    buat_rekap_bulanan,
    buat_rekap_semua_karyawan,
    buat_ringkasan_karyawan,
    menit_ke_jam,
    ringkas_rekap,
)
from src.attendance_parser import baca_file_absensi
from src.excel_export import buat_excel_rekap, buat_excel_rekap_semua


st.set_page_config(page_title="Sistem Rekap Absensi", page_icon="📋", layout="wide")

NAMA_BULAN = [
    "Januari",
    "Februari",
    "Maret",
    "April",
    "Mei",
    "Juni",
    "Juli",
    "Agustus",
    "September",
    "Oktober",
    "November",
    "Desember",
]

PILIHAN_HARI = {
    "Senin": 0,
    "Selasa": 1,
    "Rabu": 2,
    "Kamis": 3,
    "Jumat": 4,
    "Sabtu": 5,
    "Minggu": 6,
}


@st.cache_data(show_spinner=False)
def parse_file(file_bytes):
    return baca_file_absensi(file_bytes)


def waktu_ke_teks(nilai):
    return nilai.strftime("%H:%M")


def nama_file_aman(teks):
    return re.sub(r"[^A-Za-z0-9_-]+", "_", teks.strip()).strip("_")


def tampilkan_metrik(
    total,
    jumlah_karyawan=None,
):
    if jumlah_karyawan is not None:
        kolom = st.columns(6)

        kolom[0].metric(
            "Karyawan",
            jumlah_karyawan,
        )

        offset = 1
    else:
        kolom = st.columns(5)
        offset = 0

    kolom[offset].metric(
        "Hadir",
        total["hadir"],
    )

    kolom[offset + 1].metric(
        "Terlambat",
        total["terlambat"],
    )

    kolom[offset + 2].metric(
        "Pulang Awal",
        total["pulang_awal"],
    )

    kolom[offset + 3].metric(
        "Scan Tidak Lengkap",
        total["scan_tidak_lengkap"],
    )

    kolom[offset + 4].metric(
        "Tanpa Data",
        (
            total["tidak_ada_data"]
            + total["tidak_hadir"]
        ),
    )

    # TOTAL JAM DAN MENIT
    detail = st.columns(4)

    detail[0].metric(
        "Total Jam Kerja",
        menit_ke_jam(
            total["total_menit_kerja"]
        ),
    )

    detail[1].metric(
        "Total Jam Lembur",
        menit_ke_jam(
            total["total_menit_lembur"]
        ),
    )

    detail[2].metric(
        "Total Menit Terlambat",
        f'{total["total_menit_terlambat"]} menit',
    )

    detail[3].metric(
        "Total Menit Pulang Awal",
        f'{total["total_menit_pulang_awal"]} menit',
    )

    # STATUS IZIN, SAKIT, CUTI, DAN LIBUR
    status_resmi = st.columns(4)

    status_resmi[0].metric(
        "Izin",
        total["izin"],
    )

    status_resmi[1].metric(
        "Sakit",
        total["sakit"],
    )

    status_resmi[2].metric(
        "Cuti",
        total["cuti"],
    )

    status_resmi[3].metric(
        "Libur",
        total["libur"],
    )


hari_ini = date.today()

st.title("📋 Sistem Rekap Absensi Karyawan")
st.caption(
    "Upload file Excel dari mesin fingerprint, atur jadwal kerja, lalu unduh rekap."
)

with st.sidebar:
    st.header("Pengaturan Rekap")
    tahun = st.number_input(
        "Tahun", min_value=2020, max_value=2100, value=hari_ini.year, step=1
    )
    bulan = st.selectbox(
        "Bulan",
        range(1, 13),
        index=hari_ini.month - 1,
        format_func=lambda angka: NAMA_BULAN[angka - 1],
    )

    st.subheader("Jadwal Kerja")
    jam_masuk = st.time_input(
        "Jam masuk", value=time(7, 30), step=timedelta(minutes=5)
    )
    jam_pulang = st.time_input(
        "Jam pulang", value=time(16, 30), step=timedelta(minutes=5)
    )
    toleransi_terlambat = st.number_input(
        "Toleransi terlambat (menit)", min_value=0, max_value=180, value=0
    )
    toleransi_pulang_awal = st.number_input(
        "Toleransi pulang awal (menit)", min_value=0, max_value=180, value=0
    )
    nama_hari_kerja = st.multiselect(
        "Hari kerja",
        list(PILIHAN_HARI),
        default=["Senin", "Selasa", "Rabu", "Kamis", "Jumat"],
    )

file = st.file_uploader("Upload file attendance (.xlsx)", type=["xlsx"])

if not file:
    st.info("Silakan upload file attendance untuk mulai membuat rekap.")
    st.stop()

if not nama_hari_kerja:
    st.error("Pilih minimal satu hari kerja pada panel Pengaturan Rekap.")
    st.stop()

try:
    with st.spinner("Membaca data attendance..."):
        parsed = parse_file(file.getvalue())

    karyawan = parsed["karyawan"]
    if not karyawan:
        st.error(
            "Data karyawan tidak ditemukan. Pastikan sheet bernama 1–31 dan data dimulai dari baris 9."
        )
        st.stop()

    st.success(f"{len(karyawan)} karyawan berhasil ditemukan.")

    daftar_departemen = sorted(
        {data.get("departemen", "") or "Tanpa Departemen" for data in karyawan.values()}
    )
    departemen_filter = st.selectbox(
        "Filter departemen", ["Semua Departemen", *daftar_departemen]
    )

    daftar_id = sorted(
        [
            id_karyawan
            for id_karyawan, data in karyawan.items()
            if departemen_filter == "Semua Departemen"
            or (data.get("departemen", "") or "Tanpa Departemen")
            == departemen_filter
        ],
        key=lambda item: (
            karyawan[item].get(
                "nama", 
                "").lower(), 
                item),
    )

    st.subheader(
        "Izin, Sakit, Cuti, Libur Nasional, dan Cuti Hamil"
    )

    st.caption(
        "Pilih SEMUA untuk hari libur perusahaan, "
        "atau pilih ID untuk izin, sakit, dan cuti."
    )

    template_status = pd.DataFrame({
        "Tanggal": pd.Series(
            dtype="datetime64[ns]"
        ),
        "ID Karyawan": pd.Series(
            dtype="str"
        ),
        "Status": pd.Series(
            dtype="str"
        ),
        "Keterangan": pd.Series(
            dtype="str"
        ),
    })

    status_input = st.data_editor(
        template_status,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        key="editor_status_khusus",
        column_config={
            "Tanggal": (
                st.column_config.DateColumn(
                    "Tanggal",
                    format="DD/MM/YYYY",
                    required=True,
                )
            ),
            "ID Karyawan": (
                st.column_config.SelectboxColumn(
                    "ID Karyawan",
                    options=[
                        "SEMUA",
                        *sorted(karyawan.keys()),
                    ],
                    required=True,
                )
            ),
            "Status": (
                st.column_config.SelectboxColumn(
                    "Status",
                    options=[
                        "IZIN",
                        "SAKIT",
                        "CUTI",
                        "LIBUR",
                        "Libur Nasional",
                        "CUTI HAMIL",
                    ],
                    required=True,
                )
            ),
            "Keterangan": (
                st.column_config.TextColumn(
                    "Keterangan"
                )
            ),
        },
    )

    records_status = (
        status_input
        .dropna(
            subset=[
                "Tanggal",
                "ID Karyawan",
                "Status",
            ]
        )
        .to_dict("records")
    )

    status_khusus = buat_peta_status(
        records_status
    )

    # Kode lama dilanjutkan dari sini
    label_ke_id = {
        f"{karyawan[item]['nama']} ({item})": item
        for item in daftar_id
    }

    label_ke_id = {
        f"{karyawan[item]['nama']} ({item})": item for item in daftar_id
    }
    pilihan_user = st.selectbox("Pilih karyawan", list(label_ke_id))
    id_karyawan = label_ke_id[pilihan_user]
    master = karyawan[id_karyawan]

    pengaturan = {
        "jam_masuk_normal": waktu_ke_teks(jam_masuk),
        "jam_pulang_normal": waktu_ke_teks(jam_pulang),
        "toleransi_terlambat": int(toleransi_terlambat),
        "toleransi_pulang_awal": int(toleransi_pulang_awal),
        "hari_kerja": [PILIHAN_HARI[nama] for nama in nama_hari_kerja],
        "status_khusus": status_khusus,
    }

    hasil_individu = buat_rekap_bulanan(
        parsed, id_karyawan, int(tahun), int(bulan), **pengaturan
    )
    hasil_semua = buat_rekap_semua_karyawan(
        parsed, daftar_id, int(tahun), int(bulan), **pengaturan
    )
    ringkasan_semua = buat_ringkasan_karyawan(
        parsed, daftar_id, int(tahun), int(bulan), **pengaturan
    )

    tab_individu, tab_semua = st.tabs(["Rekap Per Karyawan", "Rekap Semua Karyawan"])

    with tab_individu:
        info = st.columns(3)
        info[0].metric("ID Karyawan", id_karyawan)
        info[1].metric("Nama", master["nama"])
        info[2].metric("Departemen", master.get("departemen", "-") or "-")

        total_individu = ringkas_rekap(hasil_individu)
        tampilkan_metrik(total_individu)
        st.dataframe(pd.DataFrame(hasil_individu), use_container_width=True, hide_index=True)

        excel_individu = buat_excel_rekap(
            hasil_individu,
            master["nama"],
            id_karyawan,
            master.get("departemen", ""),
        )
        nama_individu = nama_file_aman(master["nama"])
        st.download_button(
            "⬇️ Download Rekap Karyawan",
            data=excel_individu,
            file_name=f"Absensi_{nama_individu}_{tahun}_{int(bulan):02d}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

    with tab_semua:
        total_semua = ringkas_rekap(hasil_semua)
        tampilkan_metrik(total_semua, jumlah_karyawan=len(daftar_id))
        st.subheader("Ringkasan per Karyawan")
        st.dataframe(
            pd.DataFrame(ringkasan_semua), use_container_width=True, hide_index=True
        )
        with st.expander("Lihat rincian seluruh karyawan"):
            st.dataframe(
                pd.DataFrame(hasil_semua), use_container_width=True, hide_index=True
            )

        excel_semua = buat_excel_rekap_semua(ringkasan_semua, hasil_semua)
        suffix_departemen = (
            "Semua_Departemen"
            if departemen_filter == "Semua Departemen"
            else nama_file_aman(departemen_filter)
        )
        st.download_button(
            "⬇️ Download Rekap Semua Karyawan",
            data=excel_semua,
            file_name=f"Absensi_{suffix_departemen}_{tahun}_{int(bulan):02d}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

except Exception as error:
    st.error("Terjadi kesalahan saat memproses data attendance.")
    st.exception(error)
