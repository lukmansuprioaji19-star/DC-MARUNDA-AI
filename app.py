import streamlit as st
import pandas as pd
import google.generativeai as genai
import time

# 1. Konfigurasi Halaman Web
st.set_page_config(page_title="Bot Informasi DC Marunda", page_icon="🤖")
st.title("🤖 Bot Informasi DC Marunda")

# 2. Ambil API Key dari Secrets Streamlit
API_KEY = st.secrets.get("GEMINI_API_KEY")

# 3. ID GOOGLE SHEET DC MARUNDA AI (5 TAB)
SHEET_ID = "1pCLPIS2Gi55_hQPTAp8v753TeU6WWPbchAAKGPDg6wE"

@st.cache_data(ttl=60)
def load_all_sheets(sheet_id):
    tab_names = ["INDENTITAS", "INSENTIF", "KPI", "PENCAPAIAN", "T-CODE"]
    all_context = ""
    for tab in tab_names:
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={tab}"
        try:
            df = pd.read_csv(url)
            if not df.empty:
                all_context += f"\n\n--- TAB SHEET: {tab} ---\n"
                all_context += df.to_string(index=False)
        except Exception:
            continue
    return all_context

context_data = load_all_sheets(SHEET_ID)

# 4. Chat History Simpel
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 5. Eksekusi Pertanyaan & Jawaban AI
user_query = st.chat_input("Tanyakan jadwal, nama karyawan, atau informasi DC Marunda...")

if user_query:
    if not API_KEY:
        st.error("API Key belum diset di Secrets Streamlit!")
    else:
        st.session_state.messages.append({"role": "user", "content": user_query})
        with st.chat_message("user"):
            st.markdown(user_query)

        prompt = f"""
        Kamu adalah asisten bot informasi DC Marunda. 
        Jawab pertanyaan pengguna secara ramah, akurat, dan langsung berdasarkan data 5 tab tabel berikut.
        Jika nama atau informasi tidak ada dalam data, jawab dengan sopan bahwa data tidak ditemukan.

        [DATA TABEL OPERASIONAL DC MARUNDA]:
        {context_data}

        [PERTANYAAN PENGGUNA]:
        {user_query}
        """

        with st.spinner("Mencari data..."):
            genai.configure(api_key=API_KEY)
            # Menggunakan model aktif gemini-2.0-flash
            model = genai.GenerativeModel("gemini-2.0-flash")
            
            bot_reply = None
            max_retries = 3
            
            for attempt in range(max_retries):
                try:
                    response = model.generate_content(prompt)
                    if response and response.text:
                        bot_reply = response.text
                        break
                except Exception as e:
                    if "503" in str(e) or "UNAVAILABLE" in str(e):
                        time.sleep(2)
                        continue
                    else:
                        st.error(f"Terjadi kesalahan: {e}")
                        break

            if bot_reply:
                with st.chat_message("assistant"):
                    st.markdown(bot_reply)
                st.session_state.messages.append({"role": "assistant", "content": bot_reply})
            elif not bot_reply and attempt == max_retries - 1:
                st.warning("Server Google lagi padat banget, coba tekan tombol kirim sekali lagi ya!")
