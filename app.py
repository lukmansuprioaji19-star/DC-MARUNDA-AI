import streamlit as st
import pandas as pd
from google import genai
import random

# 1. Konfigurasi Halaman Web
st.set_page_config(page_title="Bot Informasi DC Marunda", page_icon="🤖")
st.title("🤖 Bot Informasi DC Marunda")

# 2. Ambil Daftar API Key dari Secrets Streamlit
RAW_KEYS = st.secrets.get("GEMINI_API_KEYS", st.secrets.get("GEMINI_API_KEY", ""))
# Ubah string koma menjadi list
API_KEYS = [k.strip() for k in RAW_KEYS.split(",") if k.strip()]

# 3. ID GOOGLE SHEETS UTAMA
SHEET_ID = "1e6eazfxdEfNXgupSIZNm7747Am4v2fU-b8VmfEp0gDs"

@st.cache_data(ttl=60)
def load_all_sheets(sheet_id):
    tab_names = ["Identitas", "Insentif", "KPI Gudang", "Pencapaian", "T-Code"]
    all_context = ""
    for tab in tab_names:
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={tab}"
        try:
            df = pd.read_csv(url)
            if not df.empty:
                all_context += f"\n\n--- TAB SHEET: {tab.upper()} ---\n"
                all_context += df.to_string(index=False)
        except Exception:
            continue
    return all_context

context_data = load_all_sheets(SHEET_ID)

# 4. Tampilkan Chat History
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 5. Eksekusi Jawaban AI
user_query = st.chat_input("Tanyakan soal Identitas, Insentif, KPI, Pencapaian, atau T-Code SAP...")

if user_query:
    if not API_KEYS:
        st.error("Belum ada API Key yang terpasang di Secrets Streamlit!")
    else:
        st.session_state.messages.append({"role": "user", "content": user_query})
        with st.chat_message("user"):
            st.markdown(user_query)

        prompt = f"""
        Kamu adalah AI Asisten Operasional Pintar DC Marunda.
        Jawab pertanyaan pengguna dengan ramah, lugas, dan akurat berdasarkan data 5 tab berikut:

        ATURAN KHUSUS JAWABAN:
        1. Jika pertanyaan mengenai Insentif, KPI, atau Pencapaian TANPA menyebutkan tanggal/waktu, ambil dan jawablah data pada TANGGAL TERAKHIR / PALING UPDATE.
        2. Jika pengguna menanyakan T-Code SAP, jelaskan fungsi beserta alur prosedurnya dengan jelas.
        3. Jika data tidak ditemukan di tabel, katakan dengan sopan bahwa data belum tercatat di sistem.

        ================ DATABASES OPERASIONAL DC MARUNDA ================
        {context_data}
        ==================================================================

        PERTANYAAN PENGGUNA:
        {user_query}
        """

        with st.spinner("Mencari data..."):
            bot_reply = None
            last_error = ""
            
            # Acak urutan key biar beban terbagi adil
            shuffled_keys = API_KEYS.copy()
            random.shuffle(shuffled_keys)

            # ROTATION SYSTEM: Coba setiap API Key satu per satu
            for current_key in shuffled_keys:
                try:
                    client = genai.Client(api_key=current_key)
                    response = client.models.generate_content(
                        model="gemini-3.8-flash",
                        contents=prompt
                    )
                    if response and response.text:
                        bot_reply = response.text
                        break
                except Exception as err:
                    last_error = str(err)
                    continue

            if bot_reply:
                with st.chat_message("assistant"):
                    st.markdown(bot_reply)
                st.session_state.messages.append({"role": "assistant", "content": bot_reply})
            else:
                st.error(f"Gagal memproses pesan: {last_error}")
