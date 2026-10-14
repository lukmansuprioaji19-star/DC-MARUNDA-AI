import streamlit as st
import pandas as pd
import google.generativeai as genai

# 1. Konfigurasi Halaman Web
st.set_page_config(page_title="Bot Informasi DC Marunda", page_icon="🤖")
st.title("🤖 Bot Informasi DC Marunda")

# 2. Ambil API Key dari Secrets
API_KEY = st.secrets.get("GEMINI_API_KEY")

# 3. ID GOOGLE SHEETS
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

# 5. Input User & Respon AI
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
                genai.configure(api_key=API_KEY)
                
                # Cari otomatis model aktif yang support di akun kamu
                available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                
                # Utamakan model flash, kalau tidak ada pakai model pertama yang tersedia
                target_model = next((m for m in available_models if 'flash' in m), available_models[0])
                
                model = genai.GenerativeModel(target_model)
                response = model.generate_content(prompt)
                
                bot_reply = response.text
                with st.chat_message("assistant"):
                    st.markdown(bot_reply)
                st.session_state.messages.append({"role": "assistant", "content": bot_reply})
                
            except Exception as e:
                st.error(f"Error Detail: {e}")
