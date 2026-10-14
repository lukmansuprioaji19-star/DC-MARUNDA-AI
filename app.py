import streamlit as st
import pandas as pd
from google import genai
import random

# 1. Konfigurasi Halaman Web
st.set_page_config(page_title="Bot Informasi DC Marunda", page_icon="🤖")
st.title("🤖 Bot Informasi DC Marunda")

# 2. Ambil API Key dari Secrets Streamlit
RAW_KEYS = st.secrets.get("GEMINI_API_KEYS", st.secrets.get("GEMINI_API_KEY", ""))
API_KEYS = [k.strip() for k in RAW_KEYS.split(",") if k.strip()]

# 3. ID GOOGLE SHEET BARU KAMU
NEW_SHEET_ID = "1pCLPIS2Gi55_hQPTAp8v753TeU6WWPbchAAKGPDg6wE"

@st.cache_data(ttl=60)
def load_new_sheet_data(sheet_id):
    # Mengambil data dari Google Sheet baru
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    try:
        df = pd.read_csv(url)
        if not df.empty:
            return df.to_string(index=False)
    except Exception as e:
        return f"Gagal membaca sheet: {e}"
    return ""

context_data = load_new_sheet_data(NEW_SHEET_ID)

# 4. Tampilkan Chat History
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 5. Eksekusi Jawaban AI
user_query = st.chat_input("Tanyakan informasi seputar data DC Marunda...")

if user_query:
    if not API_KEYS:
        st.error("Belum ada API Key yang terpasang di Secrets Streamlit!")
    else:
        st.session_state.messages.append({"role": "user", "content": user_query})
        with st.chat_message("user"):
            st.markdown(user_query)

        prompt = f"""
        Kamu adalah AI Asisten Operasional Pintar DC Marunda.
        Jawab pertanyaan pengguna secara ramah, lugas, dan akurat berdasarkan data tabel berikut.
        Jika nama, jadwal, atau informasi tidak ada dalam tabel, jawab dengan sopan bahwa data tidak ditemukan.

        ================ DATA TABEL DC MARUNDA ================
        {context_data}
        =======================================================

        PERTANYAAN PENGGUNA:
        {user_query}
        """

        with st.spinner("Mencari data..."):
            bot_reply = None
            last_error = ""

            # Acak urutan API Key jika ada lebih dari satu
            shuffled_keys = API_KEYS.copy()
            random.shuffle(shuffled_keys)

            # Pakai model gemini-1.5-flash (kuota harian besar & paling stabil)
            for current_key in shuffled_keys:
                try:
                    client = genai.Client(api_key=current_key)
                    response = client.models.generate_content(
                        model="gemini-1.5-flash",
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
