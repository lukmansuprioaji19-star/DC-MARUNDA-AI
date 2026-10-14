import streamlit as st
import pandas as pd
from google import genai
import random

# 1. Konfigurasi Halaman Web
st.set_page_config(page_title="Bot Informasi DC Marunda", page_icon="🤖")
st.title("🤖 Bot Informasi DC Marunda")

# 2. Ambil & Pemisahan API Key dari Secrets Streamlit
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

        ================ DATABASES OPERASIONAL DC MARUNDA ================
        {context_data}
        ==================================================================

        PERTANYAAN PENGGUNA:
        {user_query}
        """

        with st.spinner("Mencari data..."):
            bot_reply = None
            last_error = ""

            # Acak urutan API Key
            shuffled_keys = API_KEYS.copy()
            random.shuffle(shuffled_keys)

            # Daftar model yang dicoba secara berurutan (fallback)
            models_to_try = ["gemini-3.8-flash", "gemini-2.0-flash", "gemini-1.5-flash"]

            for single_key in shuffled_keys:
                try:
                    client = genai.Client(api_key=single_key)
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
                            continue
                    if bot_reply:
                        break
                except Exception as e:
                    last_error = str(e)
                    continue

            if bot_reply:
                with st.chat_message("assistant"):
                    st.markdown(bot_reply)
                st.session_state.messages.append({"role": "assistant", "content": bot_reply})
            else:
                if "429" in last_error or "RESOURCE_EXHAUSTED" in last_error:
                    st.warning("⏳ Kuota gratisan sedang penuh/habis untuk menit ini. Silakan tunggu 30 detik lalu coba lagi!")
                elif "503" in last_error or "UNAVAILABLE" in last_error:
                    st.warning("⏳ Server Google AI sedang sibuk. Silakan coba klik kirim lagi!")
                else:
                    st.error(f"Terjadi kesalahan: {last_error}")
