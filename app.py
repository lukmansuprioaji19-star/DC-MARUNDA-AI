import streamlit as st
import pandas as pd
import google.generativeai as genai
import random
import time

# 1. Konfigurasi Halaman Web
st.set_page_config(page_title="Bot Informasi DC Marunda", page_icon="🤖")
st.title("🤖 Bot Informasi DC Marunda")

# 2. Ambil Daftar API Key
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

# 4. Chat History
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 5. Eksekusi Pertanyaan (Gunakan Model Gratisan Utama)
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

            shuffled_keys = API_KEYS.copy()
            random.shuffle(shuffled_keys)

            # Daftar model gratisan (diurutkan dari yang kuotanya melimpah 1500/hari)
            model_options = ["gemini-1.5-flash", "gemini-1.5-flash-8b"]

            for current_key in shuffled_keys:
                genai.configure(api_key=current_key)
                for model_name in model_options:
                    try:
                        model = genai.GenerativeModel(model_name)
                        response = model.generate_content(prompt)
                        if response and response.text:
                            bot_reply = response.text
                            break
                    except Exception as e:
                        last_error = str(e)
                        continue
                if bot_reply:
                    break

            if bot_reply:
                with st.chat_message("assistant"):
                    st.markdown(bot_reply)
                st.session_state.messages.append({"role": "assistant", "content": bot_reply})
            else:
                st.error(f"Gagal memproses pesan: {last_error}")
