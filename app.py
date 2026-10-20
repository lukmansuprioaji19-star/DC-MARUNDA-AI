import streamlit as st
import pandas as pd
from groq import Groq
import requests
from datetime import datetime, timezone, timedelta

# 1. Konfigurasi Halaman & Icon Aplikasi
st.set_page_config(
    page_title="DC Marunda AI",
    page_icon="logo.png",
    layout="centered"
)

# 2. Inject HTML untuk Branding PWA
st.markdown(
    """
    <head>
        <title>DC Marunda AI</title>
        <meta name="apple-mobile-web-app-title" content="DC Marunda AI">
        <meta name="application-name" content="DC Marunda AI">
        <link rel="icon" type="image/png" href="logo.png">
        <link rel="apple-touch-icon" href="logo.png">
        <link rel="shortcut icon" href="logo.png">
    </head>
    """,
    unsafe_allow_html=True
)

# 3. Header Tampilan Aplikasi dengan Logo
col1, col2 = st.columns([1, 5])
with col1:
    st.image("logo.png", width=65)
with col2:
    st.title("DC Marunda AI")

# 4. Ambil Secrets dari Streamlit
raw_keys = [
    st.secrets.get("GROQ_API_KEY", ""),
    st.secrets.get("GROQ_API_KEY_1", ""),
    st.secrets.get("GROQ_API_KEY_2", ""),
    st.secrets.get("GROQ_API_KEY_3", ""),
]
ACTIVE_KEYS = list(dict.fromkeys([k for k in raw_keys if k]))
LOG_WEBHOOK_URL = st.secrets.get("LOG_WEBHOOK_URL", "")

# 5. ID Google Sheet Operasional DC Marunda
SHEET_ID = "1pCLPIS2Gi55_hQPTAp8v753TeU6WWPbchAAKGPDg6wE"

@st.cache_data(ttl=60)
def load_sheet_df(sheet_id, tab_name):
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={tab_name}"
    try:
        df = pd.read_csv(url, dtype=str)
        df = df.dropna(how="all").dropna(how="all", axis=1)
        df.columns = [str(col).strip() for col in df.columns]
        return df
    except Exception:
        return pd.DataFrame()

def load_sheet_tab(sheet_id, tab_name):
    df = load_sheet_df(sheet_id, tab_name)
    if not df.empty:
        return f"\n--- DATA TAB: {tab_name} ---\n" + df.to_csv(index=False)
    return ""

def validate_and_get_user(sheet_id, nik_input):
    if not nik_input or not str(nik_input).strip():
        return False, None
    
    clean_nik = str(nik_input).strip()
    df_identitas = load_sheet_df(sheet_id, "IDENTITAS")
    
    if not df_identitas.empty:
        nik_col = next((c for c in df_identitas.columns if "nik" in c.lower()), None)
        nama_col = next((c for c in df_identitas.columns if "nama" in c.lower()), None)
        
        if not nik_col and len(df_identitas.columns) > 0:
            nik_col = df_identitas.columns[0]
        if not nama_col and len(df_identitas.columns) > 1:
            nama_col = df_identitas.columns[1]
            
        if nik_col and nama_col:
            df_identitas[nik_col] = df_identitas[nik_col].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
            match = df_identitas[df_identitas[nik_col] == clean_nik]
            if not match.empty:
                nama_found = str(match.iloc[0][nama_col]).strip()
                return True, nama_found
                
    return False, None

def get_user_insentif_data(sheet_id, user_nik):
    df_insentif = load_sheet_df(sheet_id, "INSENTIF")
    if not df_insentif.empty:
        nik_col = next((c for c in df_insentif.columns if "nik" in c.lower()), None)
        if not nik_col and len(df_insentif.columns) > 0:
            nik_col = df_insentif.columns[0]
            
        if nik_col:
            df_insentif[nik_col] = df_insentif[nik_col].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
            user_data = df_insentif[df_insentif[nik_col] == str(user_nik).strip()]
            if not user_data.empty:
                return f"\n--- DATA INSENTIF KHUSUS KARYAWAN LOGIN (NIK: {user_nik}) ---\n" + user_data.to_csv(index=False)
    return "\n--- DATA INSENTIF KHUSUS: Data tidak ditemukan untuk NIK ini ---\n"

def log_chat_to_sheet(nik, nama, pertanyaan, jawaban_ai):
    if not LOG_WEBHOOK_URL:
        return
    try:
        wib = timezone(timedelta(hours=7))
        waktu_sekarang = datetime.now(wib).strftime("%Y-%m-%d %H:%M:%S")
        
        payload = {
            "waktu": waktu_sekarang,
            "nik": str(nik).strip(),
            "nama": str(nama).strip(),
            "pertanyaan": str(pertanyaan).strip(),
            "jawaban_ai": str(jawaban_ai).strip()
        }
        
        # Kirim payload data ke Google Apps Script
        requests.post(LOG_WEBHOOK_URL.strip(), data=payload, timeout=5)
    except Exception:
        pass

def get_context_by_category(sheet_id, query, user_nik):
    q = query.lower()
    if any(k in q for k in ["insentif", "poin", "point", "kata kunci"]):
        return get_user_insentif_data(sheet_id, user_nik)
    elif any(k in q for k in ["kpi", "whu", "ofr"]):
        return load_sheet_tab(sheet_id, "KPI")
    elif any(k in q for k in ["pencapaian", "box", "pcs", "lead time"]):
        return load_sheet_tab(sheet_id, "PENCAPAIAN")
    elif any(k in q for k in ["tcode", "t-code", "code", "sap", "spkb", "wavepick", "running"]):
        return load_sheet_tab(sheet_id, "T-CODE")
    else:
        return load_sheet_tab(sheet_id, "IDENTITAS")

# 6. Sidebar Input NIK & Validasi Ketat
st.sidebar.header("🔐 Access Control")
user_nik = st.sidebar.text_input("Masukkan NIK Anda:", value="", placeholder="Contoh: 5104001")

is_valid_user = False
user_nama = None

if user_nik:
    is_valid_user, user_nama = validate_and_get_user(SHEET_ID, user_nik)
    if is_valid_user:
        st.sidebar.success(f"👤 **{user_nama}**\nNIK: `{user_nik}`")
    else:
        st.sidebar.error("❌ NIK Tidak Terdaftar di Data Karyawan!")
else:
    st.sidebar.info("Masukkan NIK resmi di tab **IDENTITAS** untuk membuka akses chat.")

# 7. Inisialisasi Riwayat Chat
if "messages" not in st.session_state:
    st.session_state.messages = []
    welcome_text = """
👋 **Selamat Datang di DC Marunda AI!**

Silakan tanyakan informasi operasional yang Anda butuhkan:
- **Identitas & Jadwal Kerja**: *"Siapa saja yang masuk jam 6 pagi?"* atau *"Anwar jam berapa masuk?"*
- **Cek Insentif**: *"Sodikin Belut Bingung"* (Memerlukan Kata Kunci)
- **T-Code SAP**: *"T-Code running SPKB"*
- **KPI & Pencapaian**: *"Cek KPI"* atau *"Pencapaian lead time"*
    """
    st.session_state.messages.append({"role": "assistant", "content": welcome_text})

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 8. Input Pertanyaan Pengguna
if is_valid_user:
    user_query = st.chat_input(f"Halo {user_nama}, ketik pertanyaan Anda di sini...")
else:
    st.chat_input("🔒 Akses Dikunci: Masukkan NIK resmi di sidebar terlebih dahulu...", disabled=True)
    user_query = None

if user_query and is_valid_user:
    if not ACTIVE_KEYS:
        st.error("Gagal membaca GROQ_API_KEY di Secrets Streamlit!")
    else:
        st.session_state.messages.append({"role": "user", "content": user_query})
        with st.chat_message("user"):
            st.markdown(user_query)

        context_data = get_context_by_category(SHEET_ID, user_query, user_nik)

        system_prompt = f"""
        Kamu adalah asisten AI pintar untuk operasional DC Marunda.
        Pengguna yang sedang bertanya bernama: {user_nama} (NIK: {user_nik}).

        GAYA BAHASA & KELUESAN BERBICARA:
        1. ADAPTIF & FLEKSIBEL: Ikuti gaya bahasa pengguna. Jika pengguna bertanya dengan bahasa gaul/santai, jawablah dengan bahasa gaul/santai yang akrab. Jika pengguna bertanya dengan bahasa selain Indonesia (Jawa, Sunda, Inggris, dll), jawablah dengan bahasa yang sama atau bahasa yang diminta.
        2. CERDAS & LUAS: Jika pertanyaan bersifat umum, percakapan sehari-hari, atau di luar tabel, jawablah secara bijak, cerdas, luwes, dan menyenangkan sebagai AI.
        3. ANTI-HALUSINASI: DILARANG KERAS mengarang/menciptakan link website (seperti hrd.marunda.co.id), email, atau nomor telepon palsu. Jika pengguna bertanya cara cek insentif, jelaskan langsung aturan main di aplikasi ini: "Sebutkan kata kunci insentif Anda di chat ini".

        ATURAN PENGGUNAAN DATA TABEL OPERASIONAL:
        1. Jika pertanyaan berkaitan dengan data operasional DC Marunda, gunakan informasi resmi dari [DATA TABEL OPERASIONAL DC MARUNDA].
        2. KEAMANAN INSENTIF: DILARANG KERAS membocorkan isi kolom 'Kata kunci'. Tampilkan data nominal/poin insentif HANYA JIKA kata kunci yang dimasukkan oleh pengguna di dalam chat cocok dengan kata kunci milik NIK {user_nik} di dalam data.
        3. Jika kata kunci belum disertakan atau salah, minta pengguna memberikan kata kunci yang benar secara sopan.

        [DATA TABEL OPERASIONAL DC MARUNDA]:
        {context_data}
        """

        with st.spinner("Mencari data..."):
            bot_reply = None
            last_err = "Gagal memproses pesan."

            messages_payload = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_query}
            ]

            for api_key in ACTIVE_KEYS:
                try:
                    client = Groq(api_key=api_key)
                    all_models = client.models.list().data
                    available_text_models = [
                        m.id for m in all_models 
                        if "guard" not in m.id.lower() and "whisper" not in m.id.lower()
                    ]

                    for model_name in available_text_models:
                        try:
                            completion = client.chat.completions.create(
                                model=model_name,
                                messages=messages_payload,
                                temperature=0.2,
                                max_tokens=600
                            )
                            bot_reply = completion.choices[0].message.content
                            if bot_reply:
                                break
                        except Exception as m_err:
                            last_err = str(m_err)
                            continue
                    
                    if bot_reply:
                        break
                except Exception as err:
                    last_err = str(err)
                    continue

            if bot_reply:
                with st.chat_message("assistant"):
                    st.markdown(bot_reply)
                st.session_state.messages.append({"role": "assistant", "content": bot_reply})
                
                # Kirim log pertanyaan + jawaban AI setelah AI selesai menjawab
                log_chat_to_sheet(user_nik, user_nama, user_query, bot_reply)
            else:
                st.error(f"Gagal memproses pesan: {last_err}")
