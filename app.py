import streamlit as st
import pandas as pd
import google.generativeai as genai
import random
import time

# 1. Konfigurasi Halaman Web
st.set_page_config(page_title="Bot Informasi DC Marunda", page_icon="🤖")
st.title("🤖 Bot Informasi DC Marunda")

# 2. Ambil Daftar API Key (Bisa Single atau Multiple dipisah koma)
RAW_KEYS = st.secrets.get("GEMINI_API_KEYS", st.secrets.get("GEMINI_API_KEY", ""))
API_KEYS = [k.strip() for k in RAW_KEYS.split(",") if k.strip()]

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

# 5. Eksekusi Pertanyaan & Jawaban AI (Rotasi Key Kebal 429 & 503)
user_query = st.chat_input("Tanyakan jadwal, nama karyawan, atau informasi DC Marunda...")

if user_query:
    if not API_KEYS:
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
            bot_reply = None
            last_error = ""

            # Acak urutan API Key agar beban terbagi adil
            shuffled_keys = API_KEYS.copy()
            random.shuffle(shuffled_keys)

            for current_key in shuffled_keys:
                try:
                    genai.configure(api_key=current_key)
                    model = genai.GenerativeModel("gemini-3.8-flash")
                    
                    # Percobaan panggil
                    response = model.generate_content(prompt)
                    if response and response.text:
                        bot_reply = response.text
                        break  # Berhasil dapat jawaban!
                        
                except Exception as e:
                    last_error = str(e)
                    # Jika kena limit (429) atau server sibuk (503), ABAIKAN dan lanjut ke API Key berikutnya di loop!
                    continue

            if bot_reply:
                with st.chat_message("assistant"):
                    st.markdown(bot_reply)
                st.session_state.messages.append({"role": "assistant", "content": bot_reply})
            else:
                st.error(f"Gagal memproses pesan: {last_error}")
