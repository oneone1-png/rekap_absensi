import streamlit as st
import pandas as pd

from src.attendance_parser import baca_file_absensi
from src.attendance_logic import buat_rekap_bulanan
from src.excel_export import buat_excel_rekap


st.set_page_config(
    page_title="Sistem Rekap Absensi",
    page_icon="📋",
    layout="wide"
)


st.title(
    "📋 Sistem Rekap Absensi Karyawan"
)

st.write(
    "Upload file attendance kemudian pilih karyawan."
)



# UPLOAD FILE


file = st.file_uploader(
    "Upload file attendance",
    type=["xlsx"]
)


if file:

    try:

        # BACA FILE
        parsed = baca_file_absensi(
            file.getvalue()
        )

        karyawan = parsed[
            "karyawan"
        ]

        if not karyawan:

            st.error(
                "Data karyawan tidak ditemukan."
            )

            st.stop()

        st.success(
            f"{len(karyawan)} karyawan berhasil ditemukan."
        )


        # PILIH KARYAWAN
        pilihan = {}

        for id_karyawan, data in karyawan.items():

            label = (
                f"{id_karyawan} - "
                f"{data['nama']}"
            )

            pilihan[
                label
            ] = id_karyawan

        daftar_nama = sorted(
            pilihan.keys()
        )

        pilihan_user = st.selectbox(
            "Pilih karyawan",
            daftar_nama
        )

        id_karyawan = pilihan[
            pilihan_user
        ]

        master = karyawan[
            id_karyawan
        ]

        nama_karyawan = master[
            "nama"
        ]

        departemen = master[
            "departemen"
        ]

        # INFORMASI KARYAWAN
        col1, col2, col3 = st.columns(3)

        with col1:

            st.metric(
                "ID Karyawan",
                id_karyawan
            )

        with col2:

            st.metric(
                "Nama",
                nama_karyawan
            )

        with col3:

            st.metric(
                "Departemen",
                departemen
            )


        # PERIODE
       

        st.subheader(
            "Periode Absensi"
        )

        col_tahun, col_bulan = st.columns(2)

        with col_tahun:

            tahun = st.number_input(
                "Tahun",
                min_value=2020,
                max_value=2100,
                value=2026
            )

        with col_bulan:

            bulan = st.selectbox(
                "Bulan",
                list(range(1, 13)),
                index=7
            )

        # BUAT REKAP

        hasil = buat_rekap_bulanan(
            parsed,
            id_karyawan,
            int(tahun),
            int(bulan)
        )

        df = pd.DataFrame(
            hasil
        )


        # TAMPILKAN TABEL
        st.subheader(
            f"Rekap Absensi - {nama_karyawan}"
        )

        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True
        )

        
        # RINGKASAN
        hadir = len(
            df[
                df["Status"]
                == "HADIR"
            ]
        )

        scan_tidak_lengkap = len(
            df[
                df["Status"]
                == "SCAN TIDAK LENGKAP"
            ]
        )

        tidak_ada_data = len(
            df[
                df["Status"]
                == "TIDAK ADA DATA"
            ]
        )

        total_terlambat = df[
            "Terlambat"
        ].sum()

        st.subheader(
            "Ringkasan"
        )

        c1, c2, c3, c4 = st.columns(4)

        with c1:

            st.metric(
                "Hadir",
                hadir
            )

        with c2:

            st.metric(
                "Scan Tidak Lengkap",
                scan_tidak_lengkap
            )

        with c3:

            st.metric(
                "Tidak Ada Data",
                tidak_ada_data
            )

        with c4:

            st.metric(
                "Total Terlambat",
                f"{total_terlambat} menit"
            )


        # EXPORT EXCEL
        excel_file = buat_excel_rekap(
            hasil,
            nama_karyawan,
            id_karyawan,
            departemen
        )

        nama_file = (
            f"Absensi_"
            f"{nama_karyawan.replace(' ', '_')}_"
            f"{tahun}_"
            f"{int(bulan):02d}.xlsx"
        )

        st.download_button(
            label="⬇️ Download Rekap Excel",
            data=excel_file,
            file_name=nama_file,
            mime=(
                "application/"
                "vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            ),
            use_container_width=True
        )


    except Exception as error:

        st.error(
            "Terjadi kesalahan saat membaca data."
        )

        st.exception(
            error
        )