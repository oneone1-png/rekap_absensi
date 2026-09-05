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

st.markdown(
    """
    <style>
    [data-testid="stMetric"] {
        padding: 0.1rem 0.2rem;
    }

    [data-testid="stMetricLabel"] p {
        font-size: 0.82rem;
    }

    [data-testid="stMetricValue"] {
        font-size: 1.5rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

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


def kartu_metrik(
    kolom,
    label,
    nilai,
):
    with kolom:
        with st.container(border=True):
            st.metric(
                label,
                nilai,
            )


def tampilkan_metrik(
    total,
    jumlah_karyawan=None,
):
    tanpa_data = (
        total.get("tidak_ada_data", 0)
        + total.get("tidak_hadir", 0)
    )

    # Kartu utama
    if jumlah_karyawan is None:
        kartu_pertama = (
            "Hari Kerja",
            total.get("hari_kerja", 0),
        )
    else:
        kartu_pertama = (
            "Karyawan",
            jumlah_karyawan,
        )

    data_utama = [
        kartu_pertama,
        (
            "Hadir",
            total.get("hadir", 0),
        ),
        (
            "Terlambat",
            total.get("terlambat", 0),
        ),
        (
            "Pulang Awal",
            total.get("pulang_awal", 0),
        ),
        (
            "Scan Tidak Lengkap",
            total.get(
                "scan_tidak_lengkap",
                0,
            ),
        ),
        (
            "Tanpa Data",
            tanpa_data,
        ),
    ]

    kolom_utama = st.columns(6)

    for kolom, (label, nilai) in zip(
        kolom_utama,
        data_utama,
    ):
        kartu_metrik(
            kolom,
            label,
            nilai,
        )

    # Detail disembunyikan agar halaman ringkas
    with st.expander(
        "Detail jam dan status khusus"
    ):
        st.markdown(
            "##### Ringkasan Waktu"
        )

        data_waktu = [
            (
                "Total Jam Kerja",
                menit_ke_jam(
                    total.get(
                        "total_menit_kerja",
                        0,
                    )
                ),
            ),
            (
                "Total Jam Lembur",
                menit_ke_jam(
                    total.get(
                        "total_menit_lembur",
                        0,
                    )
                ),
            ),
            (
                "Menit Terlambat",
                str(
                    total.get(
                        "total_menit_terlambat",
                        0,
                    )
                ) + " menit",
            ),
            (
                "Menit Pulang Awal",
                str(
                    total.get(
                        "total_menit_pulang_awal",
                        0,
                    )
                ) + " menit",
            ),
        ]

        kolom_waktu = st.columns(4)

        for kolom, (label, nilai) in zip(
            kolom_waktu,
            data_waktu,
        ):
            kartu_metrik(
                kolom,
                label,
                nilai,
            )

        st.markdown(
            "##### Status Khusus"
        )

        data_status = [
            (
                "Izin",
                total.get("izin", 0),
            ),
            (
                "Sakit",
                total.get("sakit", 0),
            ),
            (
                "Cuti",
                total.get("cuti", 0),
            ),
            (
                "Libur",
                total.get("libur", 0),
            ),
            
        ]

        kolom_status = st.columns(4)

        for kolom, (label, nilai) in zip(
            kolom_status,
            data_status,
        ):
            kartu_metrik(
                kolom,
                label,
                nilai,
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
        st.subheader(
            "Rekap Absensi Per Karyawan"
        )

        # ==============================
        # INFORMASI KARYAWAN
        # ==============================

        with st.container(border=True):
            info_id, info_nama, info_departemen = (
                st.columns([1, 2, 1.5])
            )

            with info_id:
                st.caption("ID Karyawan")
                st.markdown(
                    f"### {id_karyawan}"
                )

            with info_nama:
                st.caption("Nama Karyawan")
                st.markdown(
                    f"### {master['nama']}"
                )

            with info_departemen:
                st.caption("Departemen")
                st.markdown(
                    f"### {master.get('departemen', '-') or '-'}"
                )

        # ==============================
        # RINGKASAN KEHADIRAN
        # ==============================

        st.markdown(
            "#### Ringkasan Kehadiran"
        )

        total_individu = ringkas_rekap(
            hasil_individu
        )

        tampilkan_metrik(
            total_individu
        )

        # ==============================
        # TABEL ABSENSI
        # ==============================

        st.markdown(
            "#### Rincian Absensi"
        )

        df_individu = pd.DataFrame(
            hasil_individu
        )

        # ID, nama, dan departemen tidak perlu
        # ditampilkan lagi karena sudah ada di atas
        kolom_tabel = [
            "No",
            "Tanggal",
            "Pagi Masuk",
            "Pagi Pulang",
            "Siang Masuk",
            "Siang Pulang",
            "Lembur Masuk",
            "Lembur Pulang",
            "Jam Kerja",
            "Jam Lembur",
            "Terlambat",
            "Pulang Awal",
            "Status",
            "Keterangan",
        ]

        # Mencegah error jika kolom tertentu
        # belum tersedia
        kolom_tabel = [
            kolom
            for kolom in kolom_tabel
            if kolom in df_individu.columns
        ]

        df_tampil = df_individu[
            kolom_tabel
        ].copy()

        # ==============================
        # FILTER STATUS
        # ==============================

        daftar_status = sorted(
            df_tampil["Status"]
            .dropna()
            .unique()
            .tolist()
        )

        pilihan_status = st.multiselect(
            "Filter status",
            options=daftar_status,
            default=daftar_status,
            key=f"filter_status_{id_karyawan}",
        )

        if pilihan_status:
            df_tampil = df_tampil[
                df_tampil["Status"].isin(
                    pilihan_status
                )
            ]

        st.caption(
            f"Menampilkan {len(df_tampil)} "
            "baris data absensi."
        )

        st.dataframe(
            df_tampil,
            use_container_width=True,
            hide_index=True,
            height=520,
            column_config={
                "No": st.column_config.NumberColumn(
                    "No",
                    width="small",
                ),
                "Tanggal": st.column_config.DateColumn(
                    "Tanggal",
                    format="DD/MM/YYYY",
                    width="medium",
                ),
                "Pagi Masuk": st.column_config.TextColumn(
                    "Pagi Masuk",
                    width="small",
                ),
                "Pagi Pulang": st.column_config.TextColumn(
                    "Pagi Pulang",
                    width="small",
                ),
                "Siang Masuk": st.column_config.TextColumn(
                    "Siang Masuk",
                    width="small",
                ),
                "Siang Pulang": st.column_config.TextColumn(
                    "Siang Pulang",
                    width="small",
                ),
                "Jam Kerja": st.column_config.TextColumn(
                    "Jam Kerja",
                    width="small",
                ),
                "Jam Lembur": st.column_config.TextColumn(
                    "Jam Lembur",
                    width="small",
                ),
                "Terlambat": st.column_config.NumberColumn(
                    "Terlambat",
                    width="small",
                ),
                "Pulang Awal": st.column_config.NumberColumn(
                    "Pulang Awal",
                    width="small",
                ),
                "Status": st.column_config.TextColumn(
                    "Status",
                    width="large",
                ),
                "Keterangan": st.column_config.TextColumn(
                    "Keterangan",
                    width="large",
                ),
            },
        )

        # ==============================
        # DOWNLOAD EXCEL
        # ==============================

        excel_individu = buat_excel_rekap(
            hasil_individu,
            master["nama"],
            id_karyawan,
            master.get(
                "departemen",
                "",
            ),
        )

        nama_individu = nama_file_aman(
            master["nama"]
        )

        with st.container(border=True):
            download_col, informasi_col = (
                st.columns([1, 2])
            )

            with download_col:
                st.download_button(
                    "⬇️ Download Rekap Excel",
                    data=excel_individu,
                    file_name=(
                        f"Absensi_{nama_individu}_"
                        f"{tahun}_"
                        f"{int(bulan):02d}.xlsx"
                    ),
                    mime=(
                        "application/vnd."
                        "openxmlformats-officedocument."
                        "spreadsheetml.sheet"
                    ),
                    use_container_width=True,
                )

            with informasi_col:
                st.info(
                    "File Excel berisi seluruh data "
                    "karyawan pada periode yang dipilih."
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
