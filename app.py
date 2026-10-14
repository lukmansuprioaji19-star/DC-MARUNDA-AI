import streamlit as st
import pandas as pd
from google import genai
import time

# 1. Konfigurasi Halaman Web
st.set_page_config(page_title="Bot Informasi DC Marunda", page_icon="🤖")
st.title("🤖 Bot Informasi DC Marunda")

# 2. Ambil API Key dari Secrets Streamlit
API_KEY = st.secrets.get("GEMINI_API_KEY")

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
    if not API_KEY:
        st.error("API Key belum diset di Secrets Streamlit!")
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
            try:
                client = genai.Client(api_key=API_KEY)
                models_to_try = ["gemini-1.5-flash", "gemini-2.0-flash", "gemini-3.8-flash"]
                bot_reply = None
                last_error = ""

                # Coba sampai 3 kali per model jika server Google sibuk (503)
                for model_name in models_to_try:
                    for attempt in range(3):
                        try:
                            response = client.models.generate_content(
                                model=model_name,
                                contents=prompt
                            )
                            if response and response.text:
                                bot_reply = response.text
                                break
                        except Exception as err_item:
                            last_error = str(err_item)
                            if "503" in last_error or "UNAVAILABLE" in last_error:
                                time.sleep(2) # Tunggu 2 detik lalu coba lagi
                                continue
                            else:
                                break
                    if bot_reply:
                        break

                if bot_reply:
                    with st.chat_message("assistant"):
                        st.markdown(bot_reply)
                    st.session_state.messages.append({"role": "assistant", "content": bot_reply})
                else:
                    if "503" in last_error or "UNAVAILABLE" in last_error:
                        st.warning("⏳ Server Google AI sedang sangat sibuk di pusat. Coba klik kirim lagi dalam beberapa detik ya!")
                    elif "429" in last_error or "RESOURCE_EXHAUSTED" in last_error:
                        st.warning("⏳ Kuota gratisan menit ini sedang penuh. Tunggu 20 detik lalu coba lagi!")
                    else:
                        st.error(f"Gagal terhubung ke AI: {last_error}")

            except Exception as e:
                st.error(f"Error Sistem: {e}")
