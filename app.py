import streamlit as st
import pandas as pd
import google.generativeai as genai
import time

# 1. Konfigurasi Halaman Web
st.set_page_config(page_title="Bot Informasi DC Marunda", page_icon="🤖")
st.title("🤖 Bot Informasi DC Marunda")

# 2. Pengaturan API Key dari Streamlit Secrets atau Sidebar
API_KEY = st.secrets.get("GEMINI_API_KEY") or st.sidebar.text_input("Masukkan Gemini API Key:", type="password")

# 3. ID GOOGLE SHEETS UTAMA
SHEET_ID = "1e6eazfxdEfNXgupSIZNm7747Am4v2fU-b8VmfEp0gDs"

@st.cache_data(ttl=60)
def load_all_sheets(sheet_id):
    # 5 Tab Sheet Sesuai Permintaan
    tab_names = [
        "Identitas", 
        "Insentif", 
        "KPI Gudang", 
        "Pencapaian", 
        "T-Code"
    ]
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

# 4. Inisialisasi Riwayat Percakapan Chat
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 5. Eksekusi Jawaban AI
if context_data and API_KEY:
    try:
        genai.configure(api_key=API_KEY)
        # Menggunakan model gemini-3.8-flash sesuai instruksi API Google
        model = genai.GenerativeModel("gemini-3.8-flash")

        user_query = st.chat_input("Tanyakan soal Identitas, Insentif, KPI, Pencapaian, atau T-Code SAP...")

        if user_query:
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
                response_text = None
                for attempt in range(3):
                    try:
                        response = model.generate_content(prompt)
                        response_text = response.text
                        break
                    except Exception as err:
                        if "429" in str(err) and attempt < 2:
                            time.sleep(5)
                        else:
                            raise err

                if response_text:
                    with st.chat_message("assistant"):
                        st.markdown(response_text)
                    st.session_state.messages.append({"role": "assistant", "content": response_text})

    except Exception as e:
        st.error(f"Terjadi kendala pada koneksi AI: {e}")

elif not API_KEY:
    st.info("Sistem sedang memuat API Key. Jika tidak merespons, pastikan API Key di Secrets Streamlit sudah terisi.")
