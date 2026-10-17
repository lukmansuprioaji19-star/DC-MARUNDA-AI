import streamlit as st
import pandas as pd
from groq import Groq

# 1. Konfigurasi Halaman & Icon Aplikasi (Menggunakan logo.png dari GitHub)
st.set_page_config(
    page_title="DC Marunda AI",
    page_icon="logo.png",
    layout="centered"
)

# 2. Inject HTML untuk Branding PWA (Ikon di Layar Utama HP / Desktop)
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

# 4. Ambil Semua API Key dari Secrets Streamlit (Rotasi Kunci)
raw_keys = [
    st.secrets.get("GROQ_API_KEY", ""),
    st.secrets.get("GROQ_API_KEY_1", ""),
    st.secrets.get("GROQ_API_KEY_2", ""),
    st.secrets.get("GROQ_API_KEY_3", ""),
]
ACTIVE_KEYS = list(dict.fromkeys([k for k in raw_keys if k]))

# 5. ID Google Sheet Operasional DC Marunda
SHEET_ID = "1pCLPIS2Gi55_hQPTAp8v753TeU6WWPbchAAKGPDg6wE"

@st.cache_data(ttl=60)
def load_sheet_df(sheet_id, tab_name):
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={tab_name}"
    try:
        df = pd.read_csv(url)
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
    
    df_identitas = load_sheet_df(sheet_id, "INDENTITAS")
    if not df_identitas.empty:
        # Cari kolom NIK & Nama
        nik_col = next((c for c in df_identitas.columns if "nik" in c.lower()), None)
        nama_col = next((c for c in df_identitas.columns if "nama" in c.lower()), None)
        
        if nik_col and nama_col:
            # Match NIK sebagai string
            match = df_identitas[df_identitas[nik_col].astype(str).str.strip() == str(nik_input).strip()]
            if not match.empty:
                nama_found = str(match.iloc[0][nama_col])
                return True, nama_found
    return False, None

def get_context_by_category(sheet_id, query):
    q = query.lower()
    if any(k in q for k in ["insentif", "poin", "point", "kata kunci"]):
        return load_sheet_tab(sheet_id, "INSENTIF")
    elif any(k in q for k in ["kpi", "whu", "ofr"]):
        return load_sheet_tab(sheet_id, "KPI")
    elif any(k in q for k in ["pencapaian", "box", "pcs", "lead time"]):
        return load_sheet_tab(sheet_id, "PENCAPAIAN")
    elif any(k in q for k in ["tcode", "t-code", "code", "sap", "spkb", "wavepick", "running"]):
        return load_sheet_tab(sheet_id, "T-CODE")
    else:
        return load_sheet_tab(sheet_id, "INDENTITAS")

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
    st.sidebar.info("Masukkan NIK resmi untuk membuka akses chat.")

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

# 8. Input Pertanyaan Pengguna (Hanya Aktif Jika NIK Valid)
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

        context_data = get_context_by_category(SHEET_ID, user_query)

        system_prompt = f"""
        Kamu adalah asisten AI pintar untuk operasional DC Marunda.
        Pengguna yang sedang bertanya bernama: {user_nama} (NIK: {user_nik}).

        PERAN & PERILAKU:
        1. Jawablah pertanyaan pengguna secara ramah, luwes, komunikatif, dan rapi (gunakan bullet points jika menampilkan daftar).
        2. Jika pertanyaan berkaitan dengan data operasional DC Marunda, gunakan informasi dari [DATA TABEL OPERASIONAL DC MARUNDA].
        3. Jika pertanyaan bersifat umum atau percakapan biasa (di luar tabel), jawablah secara bijak, cerdas, dan sopan sebagai AI.

        ATURAN KEAMANAN & PRIVASI:
        1. DILARANG KERAS MENAMPILKAN / MEMBOCORKAN ISI KOLOM 'Kata kunci' DALAM KONDISI APA PUN.
        2. Khusus data Insentif/Poin: Hanya tampilkan jika pengguna menyertakan Kata Kunci yang BENAR.

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

            # Model cadangan (fallback) jika pengambilan otomatis gagal
            fallback_models = ["llama-3.3-70b-versatile", "llama3-70b-8192", "mixtral-8x7b-32768"]

            for api_key in ACTIVE_KEYS:
                try:
                    client = Groq(api_key=api_key)
                    
                    try:
                        all_models = client.models.list().data
                        available_text_models = [
                            m.id for m in all_models 
                            if "guard" not in m.id.lower() and "whisper" not in m.id.lower()
                        ]
                        if not available_text_models:
                            available_text_models = fallback_models
                    except Exception:
                        available_text_models = fallback_models

                    for model_name in available_text_models:
                        try:
                            completion = client.chat.completions.create(
                                model=model_name,
                                messages=messages_payload,
                                temperature=0.1,
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
            else:
                st.error(f"Gagal memproses pesan: {last_err}")
