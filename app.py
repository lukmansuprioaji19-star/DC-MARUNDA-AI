import streamlit as st
import pandas as pd
import google.generativeai as genai

# 1. Konfigurasi Halaman Web
st.set_page_config(page_title="Bot Informasi DC Marunda", page_icon="🤖")
st.title("🤖 Bot Informasi DC Marunda")

# 2. Ambil API Key dari Secrets Streamlit
API_KEY = st.secrets.get("GEMINI_API_KEY")

# 3. LINK GOOGLE SHEET CSV UTAMA KAMU
SHEET_ID = "1pCLPIS2Gi55_hQPTAp8v753TeU6WWPbchAAKGPDg6wE"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

@st.cache_data(ttl=60)
def load_data(url):
    try:
        df = pd.read_csv(url)
        return df.to_string(index=False)
    except Exception as e:
        st.error(f"Gagal membaca data dari Google Sheets: {e}")
        return ""

context_data = load_data(CSV_URL)

# 4. Chat History Simpel
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 5. Eksekusi Pertanyaan & Jawaban AI (Logika Versi Awal)
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
        Jawab pertanyaan pengguna secara ramah, akurat, dan langsung berdasarkan data tabel berikut.
        Jika nama atau informasi tidak ada dalam data, jawab dengan sopan bahwa data tidak ditemukan.

        [DATA TABEL OPERASIONAL]:
        {context_data}

        [PERTANYAAN PENGGUNA]:
        {user_query}
        """

        with st.spinner("Mencari data..."):
            try:
                # Menggunakan library standar persis seperti versi awal kamu
                genai.configure(api_key=API_KEY)
                model = genai.GenerativeModel("gemini-1.5-flash")
                
                response = model.generate_content(prompt)
                
                bot_reply = response.text
                with st.chat_message("assistant"):
                    st.markdown(bot_reply)
                st.session_state.messages.append({"role": "assistant", "content": bot_reply})

            except Exception as e:
                st.error(f"Terjadi kesalahan pada API Gemini: {e}")
