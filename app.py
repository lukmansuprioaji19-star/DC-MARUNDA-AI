import streamlit as st
import pandas as pd
from google import genai
import random
import time

# ==========================================
# 1. KONFIGURASI HALAMAN WEB
# ==========================================
st.set_page_config(page_title="Bot Informasi DC Marunda", page_icon="🤖")
st.title("🤖 Bot Informasi DC Marunda")

# ==========================================
# 2. AMBIL API KEYS DARI SECRETS STREAMLIT
# ==========================================
RAW_KEYS = st.secrets.get("GEMINI_API_KEYS", st.secrets.get("GEMINI_API_KEY", ""))
API_KEYS = [k.strip() for k in RAW_KEYS.split(",") if k.strip()]

# ==========================================
# 3. LINK / ID GOOGLE SHEETS OPERASIONAL & JADWAL ABSEN
# ==========================================
# Database 1: 5 Tab Operasional (Identitas, Insentif, KPI, Pencapaian, T-Code)
SHEET_ID_OPERASIONAL = "1e6eazfxdEfNXgupSIZNm7747Am4v2fU-b8VmfEp0gDs"

# Database 2: Jadwal Absen Karyawan (Ganti ID ini jika ada ID Sheet Jadwal Absen terpisah)
# Catatan: Jika data Jadwal Absen ada di sheet terpisah, masukkan ID-nya di bawah ini.
SHEET_ID_JADWAL = "1e6eazfxdEfNXgupSIZNm7747Am4v2fU-b8VmfEp0gDs" 

@st.cache_data(ttl=60)
def load_all_databases():
    all_context = ""
    
    # --------------------------------------
    # A. MUAT DATABASE OPERASIONAL (5 TAB)
    # --------------------------------------
    tab_operasional = ["Identitas", "Insentif", "KPI Gudang", "Pencapaian", "T-Code"]
    for tab in tab_operasional:
        url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID_OPERASIONAL}/gviz/tq?tqx=out:csv&sheet={tab}"
        try:
            df = pd.read_csv(url)
            if not df.empty:
                all_context += f"\n\n--- TAB OPERASIONAL: {tab.upper()} ---\n"
                all_context += df.to_string(index=False)
        except Exception:
            continue

    # --------------------------------------
    # B. MUAT DATABASE JADWAL ABSEN KARYAWAN
    # --------------------------------------
    # Mencoba membaca tab 'Jadwal' atau halaman utama CSV
    url_jadwal = f"https://docs.google.com/spreadsheets/d/{SHEET_ID_JADWAL}/gviz/tq?tqx=out:csv&sheet=Jadwal"
    try:
        df_jadwal = pd.read_csv(url_jadwal)
        if not df_jadwal.empty:
            all_context += f"\n\n--- TAB DATABASE: JADWAL ABSEN KARYAWAN ---\n"
            all_context += df_jadwal.to_string(index=False)
    except Exception:
        # Fallback ke format export standar jika tidak menggunakan nama tab khusus
        try:
            url_fallback = f"https://docs.google.com/spreadsheets/d/{SHEET_ID_JADWAL}/export?format=csv"
            df_fallback = pd.read_csv(url_fallback)
            if not df_fallback.empty:
                all_context += f"\n\n--- DATABASE: JADWAL ABSEN KARYAWAN ---\n"
                all_context += df_fallback.to_string(index=False)
        except Exception:
            pass

    return all_context

context_data = load_all_databases()

# ==========================================
# 4. TAMPILKAN RIWAYAT CHAT
# ==========================================
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# ==========================================
# 5. EXECUTION & LOGIKA JAWABAN AI
# ==========================================
user_query = st.chat_input("Tanyakan jadwal absen, insentif, KPI, identitas, atau T-Code SAP...")

if user_query:
    if not API_KEYS:
        st.error("Belum ada API Key yang terpasang di Secrets Streamlit!")
    else:
        st.session_state.messages.append({"role": "user", "content": user_query})
        with st.chat_message("user"):
            st.markdown(user_query)

        prompt = f"""
        Kamu adalah AI Asisten Operasional Pintar DC Marunda.
        Jawab pertanyaan pengguna secara ramah, lugas, dan akurat berdasarkan gabungan data operasional dan jadwal absen berikut.

        ATURAN KHUSUS JAWABAN:
        1. Jika pertanyaan mengenai JADWAL ABSEN / NAMA KARYAWAN: Cari dari data Jadwal Absen Karyawan dan berikan informasi shift / jadwalnya dengan jelas.
        2. Jika pertanyaan mengenai INSENTIF, KPI, atau PENCAPAIAN (tanpa menyebutkan tanggal), ambil data pada TANGGAL TERAKHIR / PALING UPDATE.
        3. Jika pengguna menanyakan T-Code SAP, jelaskan fungsi beserta alur prosedurnya dengan ringkas dan jelas.
        4. Jika data nama / informasi tidak ditemukan di semua tabel, katakan dengan sopan bahwa data belum tercatat di sistem.

        ================ DATABASES GABUNGAN DC MARUNDA ================
        {context_data}
        ==================================================================

        PERTANYAAN PENGGUNA:
        {user_query}
        """

        with st.spinner("Mencari data di seluruh database..."):
            bot_reply = None
            last_error = ""
            
            # ACAK API KEY
            shuffled_keys = API_KEYS.copy()
            random.shuffle(shuffled_keys)

            # DAFTAR MODEL YANG DICOBA DENGAN FALLBACK
            models_to_try = [
                "gemini-1.5-flash",
                "gemini-2.0-flash",
                "gemini-2.5-flash",
                "gemini-3.8-flash"
            ]

            # ROTASI GANDA: PUTAR API KEY & PUTAR MODEL DENGAN DELAY
            for current_key in shuffled_keys:
                try:
                    client = genai.Client(api_key=current_key)
                    for model_name in models_to_try:
                        try:
                            response = client.models.generate_content(
                                model=model_name,
                                contents=prompt
                            )
                            if response and response.text:
                                bot_reply = response.text
                                break
                        except Exception as m_err:
                            last_error = str(m_err)
                            # Jeda 1.5 detik jika server Google menanggapi dengan 503/UNAVAILABLE
                            if "503" in last_error or "UNAVAILABLE" in last_error:
                                time.sleep(1.5)
                            continue
                    
                    if bot_reply:
                        break
                except Exception as k_err:
                    last_error = str(k_err)
                    continue

            if bot_reply:
                with st.chat_message("assistant"):
                    st.markdown(bot_reply)
                st.session_state.messages.append({"role": "assistant", "content": bot_reply})
            else:
                st.error(f"Gagal memproses pesan: {last_error}")
