from datetime import date, time, timedelta
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
from src.audit_export import buat_excel_audit_individu, buat_excel_audit_semua
from src.audit_logic import (
    buat_ringkasan_audit,
    filter_karyawan_audit,
    rincian_karyawan_audit,
    rincian_untuk_tampilan,
    ringkas_audit,
)
from src.excel_export import buat_excel_rekap, buat_excel_rekap_semua
from src.file_parser import proses_file
from src.special_status import buat_peta_status


st.set_page_config(page_title="Sistem Rekap Absensi", page_icon="📋", layout="wide")

st.markdown(
    """
    <style>
    .block-container {padding-top: 2rem; padding-bottom: 3rem;}
    [data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 0.75rem;
        padding: 0.75rem 0.9rem;
        min-height: 5.6rem;
    }
    [data-testid="stMetricLabel"] p {font-size: 0.82rem; color: #475569;}
    [data-testid="stMetricValue"] {font-size: 1.45rem; color: #0f172a;}
    </style>
    """,
    unsafe_allow_html=True,
)

NAMA_BULAN = [
    "Januari", "Februari", "Maret", "April", "Mei", "Juni",
    "Juli", "Agustus", "September", "Oktober", "November", "Desember",
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
    return proses_file(file_bytes)


def nama_file_aman(teks):
    return re.sub(r"[^A-Za-z0-9_-]+", "_", str(teks).strip()).strip("_")


def angka_ringkas(nilai):
    nilai = float(nilai or 0)
    return str(int(nilai)) if nilai.is_integer() else f"{nilai:.2f}".rstrip("0").rstrip(".")


def tampilkan_kartu(data, jumlah_kolom=6):
    for awal in range(0, len(data), jumlah_kolom):
        bagian = data[awal:awal + jumlah_kolom]
        kolom = st.columns(jumlah_kolom)
        for tempat, (label, nilai) in zip(kolom, bagian):
            tempat.metric(label, nilai)


def tampilkan_metrik_fingerprint(total, jumlah_karyawan=None):
    pertama = (
        ("Karyawan", jumlah_karyawan)
        if jumlah_karyawan is not None
        else ("Hari Kerja", total.get("hari_kerja", 0))
    )
    tampilkan_kartu(
        [
            pertama,
            ("Hadir", total.get("hadir", 0)),
            ("Terlambat", total.get("terlambat", 0)),
            ("Pulang Awal", total.get("pulang_awal", 0)),
            ("Scan Tidak Lengkap", total.get("scan_tidak_lengkap", 0)),
            (
                "Tanpa Data",
                total.get("tidak_ada_data", 0) + total.get("tidak_hadir", 0),
            ),
        ]
    )

    with st.expander("Detail jam dan status khusus"):
        tampilkan_kartu(
            [
                ("Total Jam Kerja", menit_ke_jam(total.get("total_menit_kerja", 0))),
                ("Total Jam Lembur", menit_ke_jam(total.get("total_menit_lembur", 0))),
                ("Menit Terlambat", f'{total.get("total_menit_terlambat", 0)} menit'),
                ("Menit Pulang Awal", f'{total.get("total_menit_pulang_awal", 0)} menit'),
            ],
            jumlah_kolom=4,
        )
        st.markdown("##### Status Khusus")
        tampilkan_kartu(
            [
                ("Izin", total.get("izin", 0)),
                ("Sakit", total.get("sakit", 0)),
                ("Cuti", total.get("cuti", 0)),
                ("Libur", total.get("libur", 0)),
            ],
            jumlah_kolom=4,
        )


def editor_status_khusus(karyawan):
    with st.expander("Tambahkan izin, sakit, cuti, atau libur"):
        st.caption(
            "Gunakan ID karyawan untuk status individu. Pilih SEMUA untuk "
            "libur yang berlaku bagi seluruh karyawan."
        )
        template = pd.DataFrame(
            {
                "Tanggal": pd.Series(dtype="datetime64[ns]"),
                "ID Karyawan": pd.Series(dtype="str"),
                "Status": pd.Series(dtype="str"),
                "Keterangan": pd.Series(dtype="str"),
            }
        )
        input_status = st.data_editor(
            template,
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            key="editor_status_khusus",
            column_config={
                "Tanggal": st.column_config.DateColumn(
                    "Tanggal", format="DD/MM/YYYY", required=True
                ),
                "ID Karyawan": st.column_config.SelectboxColumn(
                    "ID Karyawan",
                    options=["SEMUA", *sorted(karyawan)],
                    required=True,
                ),
                "Status": st.column_config.SelectboxColumn(
                    "Status",
                    options=["IZIN", "SAKIT", "CUTI", "LIBUR"],
                    required=True,
                ),
                "Keterangan": st.column_config.TextColumn("Keterangan"),
            },
        )

    records = input_status.dropna(
        subset=["Tanggal", "ID Karyawan", "Status"]
    ).to_dict("records")
    return buat_peta_status(records)


def filter_departemen(karyawan, key):
    daftar = sorted(
        {data.get("departemen", "") or "Tanpa Departemen" for data in karyawan.values()}
    )
    pilihan = st.selectbox(
        "Departemen", ["Semua Departemen", *daftar], key=key
    )
    return None if pilihan == "Semua Departemen" else pilihan


def tampilkan_fingerprint(parsed):
    karyawan = parsed.get("karyawan", {})
    if not karyawan:
        raise ValueError(
            "Data karyawan tidak ditemukan. Format fingerprint membutuhkan "
            "sheet bernama 1 sampai 31 dan data mulai sekitar baris 9."
        )

    hari_ini = date.today()
    with st.sidebar:
        st.header("Pengaturan Fingerprint")
        tahun = st.number_input(
            "Tahun", min_value=2020, max_value=2100, value=hari_ini.year, step=1
        )
        bulan = st.selectbox(
            "Bulan",
            range(1, 13),
            index=hari_ini.month - 1,
            format_func=lambda value: NAMA_BULAN[value - 1],
        )
        st.subheader("Jadwal Kerja")
        jam_masuk = st.time_input(
            "Jam masuk", value=time(7, 30), step=timedelta(minutes=5)
        )
        jam_pulang = st.time_input(
            "Jam pulang", value=time(16, 30), step=timedelta(minutes=5)
        )
        toleransi_terlambat = st.number_input(
            "Toleransi terlambat (menit)", 0, 180, 0
        )
        toleransi_pulang_awal = st.number_input(
            "Toleransi pulang awal (menit)", 0, 180, 0
        )
        nama_hari_kerja = st.multiselect(
            "Hari kerja",
            list(PILIHAN_HARI),
            default=["Senin", "Selasa", "Rabu", "Kamis", "Jumat"],
        )

    if not nama_hari_kerja:
        st.warning("Pilih minimal satu hari kerja pada panel sebelah kiri.")
        return

    st.success(f"Format fingerprint terdeteksi. {len(karyawan)} karyawan ditemukan.")
    filter_col, karyawan_col = st.columns([1, 2])
    with filter_col:
        departemen = filter_departemen(karyawan, "departemen_fingerprint")

    daftar_id = [
        item
        for item, data in karyawan.items()
        if departemen is None
        or (data.get("departemen", "") or "Tanpa Departemen") == departemen
    ]
    daftar_id.sort(key=lambda item: (karyawan[item].get("nama", "").casefold(), item))
    if not daftar_id:
        st.warning("Tidak ada karyawan pada filter yang dipilih.")
        return

    label_ke_id = {f"{karyawan[item]['nama']} ({item})": item for item in daftar_id}
    with karyawan_col:
        pilihan = st.selectbox("Karyawan", list(label_ke_id), key="karyawan_fingerprint")
    id_karyawan = label_ke_id[pilihan]
    master = karyawan[id_karyawan]
    status_khusus = editor_status_khusus(karyawan)

    pengaturan = {
        "jam_masuk_normal": jam_masuk.strftime("%H:%M"),
        "jam_pulang_normal": jam_pulang.strftime("%H:%M"),
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

    tab_individu, tab_semua = st.tabs(["Per Karyawan", "Semua Karyawan"])
    with tab_individu:
        st.subheader("Rekap Absensi Per Karyawan")
        with st.container(border=True):
            info = st.columns([1, 2, 1.5])
            info[0].caption("ID Karyawan")
            info[0].markdown(f"### {id_karyawan}")
            info[1].caption("Nama Karyawan")
            info[1].markdown(f"### {master['nama']}")
            info[2].caption("Departemen")
            info[2].markdown(f"### {master.get('departemen', '-') or '-'}")

        total = ringkas_rekap(hasil_individu)
        tampilkan_metrik_fingerprint(total)
        df = pd.DataFrame(hasil_individu)
        kolom = [
            "No", "Tanggal", "Pagi Masuk", "Pagi Pulang", "Siang Masuk",
            "Siang Pulang", "Lembur Masuk", "Lembur Pulang", "Jam Kerja",
            "Jam Lembur", "Terlambat", "Pulang Awal", "Status", "Keterangan",
        ]
        kolom = [item for item in kolom if item in df.columns]
        daftar_status = sorted(df["Status"].dropna().unique().tolist())
        status = st.multiselect(
            "Filter status", daftar_status, default=daftar_status, key="status_fingerprint"
        )
        df_tampil = df[df["Status"].isin(status)][kolom] if status else df.iloc[0:0][kolom]
        st.caption(f"Menampilkan {len(df_tampil)} baris.")
        st.dataframe(df_tampil, use_container_width=True, hide_index=True, height=500)

        excel = buat_excel_rekap(
            hasil_individu, master["nama"], id_karyawan, master.get("departemen", "")
        )
        st.download_button(
            "Download rekap karyawan",
            data=excel,
            file_name=(
                f"Absensi_{nama_file_aman(master['nama'])}_{tahun}_{int(bulan):02d}.xlsx"
            ),
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

    with tab_semua:
        total = ringkas_rekap(hasil_semua)
        tampilkan_metrik_fingerprint(total, len(daftar_id))
        st.subheader("Ringkasan Per Karyawan")
        st.dataframe(pd.DataFrame(ringkasan_semua), use_container_width=True, hide_index=True)
        with st.expander("Lihat rincian seluruh karyawan"):
            st.dataframe(pd.DataFrame(hasil_semua), use_container_width=True, hide_index=True)
        excel = buat_excel_rekap_semua(ringkasan_semua, hasil_semua)
        suffix = "Semua_Departemen" if departemen is None else nama_file_aman(departemen)
        st.download_button(
            "Download rekap semua karyawan",
            data=excel,
            file_name=f"Absensi_{suffix}_{tahun}_{int(bulan):02d}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )


def tampilkan_metrik_audit(total, jumlah_karyawan=None):
    data = []
    if jumlah_karyawan is not None:
        data.append(("Karyawan", jumlah_karyawan))
    data.extend(
        [
            ("Hari Hadir", total["hari_hadir"]),
            ("Jam Hadir", angka_ringkas(total["jam_hadir"])),
            ("Libur Dibayar", angka_ringkas(total["libur_dibayar"])),
            ("Jam Lembur", angka_ringkas(total["jam_lembur"])),
            ("Jam Sakit", angka_ringkas(total["jam_sakit"])),
            (
                "Hari Cuti",
                total["hari_cuti_tahunan"] + total["hari_cuti_khusus"],
            ),
        ]
    )
    tampilkan_kartu(data, jumlah_kolom=4 if jumlah_karyawan is not None else 6)


def tampilkan_audit(parsed):
    periode = parsed["periode"]
    tahun, bulan = periode["tahun"], periode["bulan"]
    karyawan = parsed["karyawan"]
    st.success(
        f"Format audit terdeteksi. Periode {NAMA_BULAN[bulan - 1]} {tahun}, "
        f"{len(karyawan)} karyawan ditemukan."
    )
    st.info(
        "File audit berisi jumlah jam dan status harian. Keterlambatan, pulang awal, "
        "dan scan tidak lengkap tidak dihitung karena waktu scan tidak tersedia."
    )

    unit_col, dept_col, employee_col = st.columns([1, 1.4, 2])
    with unit_col:
        unit_pilihan = st.selectbox(
            "Unit", ["Semua Unit", *parsed["sheet"]], key="unit_audit"
        )
    unit = None if unit_pilihan == "Semua Unit" else unit_pilihan

    departemen_unit = sorted(
        {
            data.get("departemen", "") or "Tanpa Departemen"
            for data in karyawan.values()
            if unit is None or data.get("unit") == unit
        }
    )
    with dept_col:
        departemen_pilihan = st.selectbox(
            "Departemen",
            ["Semua Departemen", *departemen_unit],
            key="departemen_audit",
        )
    departemen = None if departemen_pilihan == "Semua Departemen" else departemen_pilihan
    daftar_id = filter_karyawan_audit(parsed, unit, departemen)
    if not daftar_id:
        st.warning("Tidak ada karyawan pada filter yang dipilih.")
        return

    label_ke_id = {f"{karyawan[item]['nama']} ({item})": item for item in daftar_id}
    with employee_col:
        pilihan = st.selectbox("Karyawan", list(label_ke_id), key="karyawan_audit")
    id_karyawan = label_ke_id[pilihan]
    master = karyawan[id_karyawan]

    tab_individu, tab_semua = st.tabs(["Per Karyawan", "Semua Karyawan"])
    with tab_individu:
        with st.container(border=True):
            info = st.columns([1, 2, 1, 1.5])
            info[0].caption("ID Karyawan")
            info[0].markdown(f"### {id_karyawan}")
            info[1].caption("Nama")
            info[1].markdown(f"### {master['nama']}")
            info[2].caption("Unit")
            info[2].markdown(f"### {master['unit']}")
            info[3].caption("Departemen")
            info[3].markdown(f"### {master.get('departemen', '-') or '-'}")
            st.caption(f"Jabatan: {master.get('jabatan', '-') or '-'}")

        rincian_lengkap = rincian_karyawan_audit(parsed, id_karyawan)
        total = ringkas_audit(rincian_lengkap)
        tampilkan_metrik_audit(total)
        tampilkan_kosong = st.checkbox(
            "Tampilkan tanggal tanpa data", value=False, key="kosong_audit_individu"
        )
        rincian = (
            rincian_lengkap
            if tampilkan_kosong
            else [row for row in rincian_lengkap if row["status"] != "TANPA DATA"]
        )
        df = pd.DataFrame(rincian_untuk_tampilan(rincian))
        if not df.empty:
            status_tersedia = sorted(df["Status"].unique().tolist())
            status = st.multiselect(
                "Filter status", status_tersedia, default=status_tersedia, key="status_audit"
            )
            df = df[df["Status"].isin(status)] if status else df.iloc[0:0]
        st.caption(f"Menampilkan {len(df)} baris audit.")
        st.dataframe(df, use_container_width=True, hide_index=True, height=500)

        excel = buat_excel_audit_individu(rincian_lengkap)
        st.download_button(
            "Download audit karyawan",
            data=excel,
            file_name=(
                f"Audit_{nama_file_aman(master['nama'])}_{tahun}_{bulan:02d}.xlsx"
            ),
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

    with tab_semua:
        id_terpilih = set(daftar_id)
        rincian_semua = [
            row for row in parsed["rincian"] if row.get("id") in id_terpilih
        ]
        total = ringkas_audit(rincian_semua)
        tampilkan_metrik_audit(total, len(daftar_id))
        ringkasan = buat_ringkasan_audit(parsed, daftar_id)
        st.subheader("Ringkasan Audit Per Karyawan")
        st.dataframe(pd.DataFrame(ringkasan), use_container_width=True, hide_index=True)
        with st.expander("Lihat rincian audit"):
            rincian_berdata = [
                row for row in rincian_semua if row.get("status") != "TANPA DATA"
            ]
            st.dataframe(
                pd.DataFrame(rincian_untuk_tampilan(rincian_berdata)),
                use_container_width=True,
                hide_index=True,
                height=550,
            )

        excel = buat_excel_audit_semua(ringkasan, rincian_semua)
        suffix = "Semua_Unit" if unit is None else nama_file_aman(unit)
        st.download_button(
            "Download audit semua karyawan",
            data=excel,
            file_name=f"Audit_{suffix}_{tahun}_{bulan:02d}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )


st.title("📋 Sistem Rekap Absensi Karyawan")
st.caption(
    "Unggah file fingerprint atau file audit Excel. Sistem akan mengenali format "
    "secara otomatis dan menampilkan rekap yang sesuai."
)

file = st.file_uploader("Upload file Excel (.xlsx)", type=["xlsx"])
if not file:
    st.info("Silakan upload file Excel untuk mulai membuat rekap.")
    with st.expander("Format file yang didukung"):
        st.markdown(
            "- **Fingerprint:** sheet bernama `1` sampai `31`, data mulai sekitar baris 9.\n"
            "- **Audit:** memiliki sheet `PRODUKSI` atau `OFFICE`, dengan nomor tanggal pada baris 3."
        )
    st.stop()

try:
    with st.spinner("Membaca dan memvalidasi file..."):
        parsed = parse_file(file.getvalue())
    if parsed["jenis"] == "audit":
        tampilkan_audit(parsed)
    else:
        tampilkan_fingerprint(parsed)
except Exception as error:
    st.error(str(error))
    with st.expander("Detail teknis"):
        st.exception(error)
