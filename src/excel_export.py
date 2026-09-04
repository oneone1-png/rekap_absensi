from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import (
    Alignment,
    Border,
    Side,
    PatternFill,
    Font
)
from openpyxl.utils import get_column_letter


def buat_excel_rekap(
    hasil,
    nama_karyawan,
    id_karyawan,
    departemen
):

    # Membuat workbook baru
    wb = Workbook()

    ws = wb.active
    ws.title = "Absensi"

    # HEADER

    headers = [
        "NO\n序",
        "Tanggal\n日期",
        "ID\n員工號",
        "Dep:\n部門",
        "Nama\n姓名",
        "pagi\nmasuk\n上午上班",
        "pagi\npulang\n上午下班",
        "siang\nmasuk\n下午上班",
        "siang\npulang\n下午下班",
        "lembur\nmasuk\n加班上班",
        "lembur\npulang\n加班下班",
        "jam\nlembur\n加班時"
    ]

    ws.append(headers)

    # BORDER  

    thin = Side(
        border_style="thin",
        color="000000"
    )

    border = Border(
        left=thin,
        right=thin,
        top=thin,
        bottom=thin
    )

    # FORMAT HEADER

    header_fill = PatternFill(
        fill_type="solid",
        fgColor="E7E6E6"
    )

    for cell in ws[1]:

        cell.alignment = Alignment(
            horizontal="center",
            vertical="center",
            wrap_text=True
        )

        cell.border = border
        cell.fill = header_fill

        cell.font = Font(
            name="Arial",
            size=9
        )

    ws.row_dimensions[1].height = 55

    # MASUKKAN DATA

    for index, data in enumerate(
        hasil,
        start=1
    ):

        # ID, departemen dan nama hanya
        # ditampilkan pada baris pertama
        if index == 1:

            id_tampil = id_karyawan
            dep_tampil = departemen
            nama_tampil = nama_karyawan

        else:

            id_tampil = ""
            dep_tampil = ""
            nama_tampil = ""

        row = [
            data.get("No", index),

            data.get(
                "Tanggal",
                ""
            ),

            id_tampil,

            dep_tampil,

            nama_tampil,

            data.get(
                "Pagi Masuk",
                ""
            ),

            data.get(
                "Pagi Pulang",
                ""
            ),

            data.get(
                "Siang Masuk",
                ""
            ),

            data.get(
                "Siang Pulang",
                ""
            ),

            data.get(
                "Lembur Masuk",
                ""
            ),

            data.get(
                "Lembur Pulang",
                ""
            ),

            data.get(
                "Jam Lembur",
                ""
            )
        ]

        ws.append(row)

    # FORMAT ISI


    for row in ws.iter_rows(
        min_row=2,
        max_row=ws.max_row,
        min_col=1,
        max_col=12
    ):

        for cell in row:

            cell.border = border

            cell.alignment = Alignment(
                horizontal="center",
                vertical="center"
            )

            cell.font = Font(
                name="Arial",
                size=9
            )

        # Nama dibuat rata kiri
        row[4].alignment = Alignment(
            horizontal="left",
            vertical="center"
        )

    # FORMAT TANGGAL
   
    for row in range(
        2,
        ws.max_row + 1
    ):

        ws.cell(
            row=row,
            column=2
        ).number_format = "yyyy/mm/dd"

    # LEBAR KOLOM
    
    ukuran = {
        "A": 5,
        "B": 13,
        "C": 10,
        "D": 16,
        "E": 25,
        "F": 10,
        "G": 10,
        "H": 10,
        "I": 10,
        "J": 10,
        "K": 10,
        "L": 10
    }

    for kolom, width in ukuran.items():

        ws.column_dimensions[
            kolom
        ].width = width

   
    # TINGGI BARIS


    for row in range(
        2,
        ws.max_row + 1
    ):

        ws.row_dimensions[
            row
        ].height = 22

   
    # FREEZE HEADER
 

    ws.freeze_panes = "A2"

  
    # SET PRINT
 

    ws.page_setup.orientation = "landscape"

    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0

    ws.sheet_properties.pageSetUpPr.fitToPage = True

    ws.print_title_rows = "1:1"

  
    # SIMPAN KE MEMORY
  

    output = BytesIO()

    wb.save(output)

    output.seek(0)

    return output