
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

st.set_page_config(layout="wide", page_title="Dashboard Kepatuhan Pajak")

st.markdown("<h1 style='text-align: center;'>📊 Dashboard Kepatuhan Pajak</h1>", unsafe_allow_html=True)

# ============================
# Fungsi bantu
# ============================
def normalize_colname(col):
    col = str(col).strip().lower().replace(" ", "").replace("_", "")
    if "nama" in col and ("op" in col or "unit" in col):
        return "nama_op"
    elif "up" in col:
        return "upppd"
    elif "status" in col:
        return "status"
    elif "tmt" in col:
        return "tmt"
    elif "kategori" in col or "klasifikasi" in col or "jenis" in col:
        return "klasifikasi"
    elif "npwpd" in col or "nopok" in col:
        return "npwpd"
    elif "bayar" in col or "setor" in col:
        return "pembayaran"
    else:
        return col

def detect_columns(df):
    renamed_cols = {col: normalize_colname(col) for col in df.columns}
    df = df.rename(columns=renamed_cols)
    return df

def hitung_kepatuhan(df, tahun_pajak):
    df["tmt"] = pd.to_datetime(df["tmt"], errors="coerce")
    df["bulan_aktif"] = df["tmt"].apply(lambda x: max(0, 12 - x.month + 1) if pd.notnull(x) and x.year == tahun_pajak else (12 if pd.notnull(x) and x.year < tahun_pajak else 0))
    bulan_cols = [col for col in df.columns if str(tahun_pajak) in str(col) and any(bln in str(col).lower() for bln in ["jan", "feb", "mar", "apr", "mei", "jun", "jul", "agu", "sep", "okt", "nov", "des"])]
    df["bulan_bayar"] = df[bulan_cols].apply(lambda row: row.gt(0).sum(), axis=1)
    df["total_pembayaran"] = df[bulan_cols].sum(axis=1)
    df["rata2_per_bulan"] = df["total_pembayaran"] / df["bulan_bayar"].replace(0, np.nan)
    df["kepatuhan"] = df["bulan_bayar"] / df["bulan_aktif"].replace(0, np.nan)
    df["kategori_kepatuhan"] = df["kepatuhan"].apply(lambda x: "PATUH" if x == 1 else ("KURANG PATUH" if x >= 0.75 else "TIDAK PATUH"))
    df["kepatuhan"] = (df["kepatuhan"] * 100).round(2)
    return df

# ============================
# Sidebar input
# ============================
st.sidebar.subheader("🕰️ Filter Data")

jenis_pajak = st.sidebar.selectbox("Pilih Jenis Pajak", ["HIBURAN", "MAKAN MINUM"])

uploaded = st.sidebar.file_uploader(f"📂 Upload File Excel untuk Pajak {jenis_pajak}", type=["xlsx"])

if uploaded:
    xl = pd.ExcelFile(uploaded)
    sheet = st.sidebar.selectbox("📄 Pilih Nama Sheet", xl.sheet_names)
    tahun_pajak = st.sidebar.number_input("📅 Pilih Tahun Pajak", min_value=2000, max_value=2100, value=2024)

    df = xl.parse(sheet)
    df = detect_columns(df)

    required_cols = ["nama_op", "upppd", "status", "tmt"]
    if not all(col in df.columns for col in required_cols):
        st.error("Kolom wajib seperti 'UPPPD', 'Nama OP', 'Status', dan 'TMT' tidak ditemukan di file Excel.")
    else:
        if jenis_pajak == "HIBURAN" and "klasifikasi" not in df.columns:
            st.error("Untuk pajak HIBURAN, kolom 'Klasifikasi' wajib ada di file Excel.")
        else:
            df = hitung_kepatuhan(df, tahun_pajak)

            # Dropdown filter
            df_display = df.copy()
            upppd_list = ["Semua"] + sorted(df["upppd"].dropna().unique().tolist())
            klasifikasi_list = ["Semua"] + sorted(df["klasifikasi"].dropna().unique().tolist()) if "klasifikasi" in df.columns else ["Semua"]
            status_list = ["Semua"] + sorted(df["status"].dropna().unique().tolist())

            selected_upppd = st.sidebar.selectbox("Pilih UPPPD", upppd_list)
            selected_klasifikasi = st.sidebar.selectbox("Pilih Klasifikasi", klasifikasi_list)
            selected_status = st.sidebar.selectbox("Pilih Status WP", status_list)

            if selected_upppd != "Semua":
                df_display = df_display[df_display["upppd"] == selected_upppd]
            if selected_klasifikasi != "Semua" and "klasifikasi" in df_display.columns:
                df_display = df_display[df_display["klasifikasi"] == selected_klasifikasi]
            if selected_status != "Semua":
                df_display = df_display[df_display["status"] == selected_status]

            st.success("✅ Data berhasil diproses dan difilter!")
            st.dataframe(df_display.head(10))

            # Visualisasi
            st.subheader("📈 Tren Pembayaran Jan–Des")
            bulan_cols = [col for col in df.columns if str(tahun_pajak) in str(col)]
            df_trend = df_display[["nama_op"] + bulan_cols].set_index("nama_op").T
            st.line_chart(df_trend)

            st.subheader("🥧 Distribusi Kepatuhan")
            pie = df_display["kategori_kepatuhan"].value_counts().reset_index()
            pie.columns = ["Kategori", "Jumlah"]
            fig = px.pie(pie, names="Kategori", values="Jumlah", color_discrete_sequence=px.colors.qualitative.Pastel)
            st.plotly_chart(fig, use_container_width=True)

            st.subheader("🏅 Top 5 OP berdasarkan Total Pembayaran")
            top5 = df_display.sort_values("total_pembayaran", ascending=False).head(5)
            st.dataframe(top5[["nama_op", "total_pembayaran", "bulan_bayar", "kepatuhan", "kategori_kepatuhan"]])
