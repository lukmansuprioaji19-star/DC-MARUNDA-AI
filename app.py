import streamlit as st
import pandas as pd
from groq import Groq

# 1. Konfigurasi Halaman Web Streamlit
st.set_page_config(page_title="Bot Informasi DC Marunda", page_icon="🤖")
st.title("🤖 Bot Informasi DC Marunda")

# 2. Ambil API Key Groq dari Secrets Streamlit
GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", "")

# 3. ID Google Sheet Operasional DC Marunda
SHEET_ID = "1pCLPIS2Gi55_hQPTAp8v753TeU6WWPbchAAKGPDg6wE"

@st.cache_data(ttl=60)
def load_all_sheets(sheet_id):
    tab_names = ["INDENTITAS", "INSENTIF", "KPI", "PENCAPAIAN", "T-CODE"]
    all_context = ""
    for tab in tab_names:
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={tab}"
        try:
            df = pd.read_csv(url)
            # Hapus baris & kolom yang kosong agar super hemat token
            df = df.dropna(how="all").dropna(how="all", axis=1)
            if not df.empty:
                all_context += f"\n--- TAB: {tab} ---\n"
                all_context += df.to_csv(index=False)
        except Exception:
            continue
    return all_context

context_data = load_all_sheets(SHEET_ID)

# 4. Inisialisasi Riwayat Chat
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 5. Input Pertanyaan Pengguna
user_query = st.chat_input("Tanyakan jadwal, nama karyawan, atau informasi DC Marunda...")

if user_query:
    if not GROQ_API_KEY:
        st.error("GROQ_API_KEY belum diset di Secrets Streamlit!")
    else:
        st.session_state.messages.append({"role": "user", "content": user_query})
        with st.chat_message("user"):
            st.markdown(user_query)

        system_prompt = f"""
        Kamu adalah asisten bot informasi DC Marunda.
        Tugasmu adalah menjawab pertanyaan pengguna dengan cepat, ramah, dan akurat berdasarkan data tabel yang diberikan.

        ATURAN JAWABAN:
        1. Jawab pertanyaan pengguna secara langsung tanpa meminta kata kunci/rahasia apa pun.
        2. Jika pengguna menanyakan data insentif/poin karyawan, tampilkan jawabannya secara menurun (list/bullet points) yang rapi, contoh:
           Informasi Insentif [Nama Karyawan] per [Tanggal]:
           - NIK: [NIK]
           - Job: [Job/Posisi]
           - Total Poin: [Total Poin & Nominal]

        3. Jawab hanya berdasarkan data yang ada di tabel. Jika data tidak ditemukan, sampaikan secara sopan bahwa data tidak ditemukan.

        [DATA TABEL OPERASIONAL DC MARUNDA]:
        {context_data}
        """

        with st.spinner("Mencari data..."):
            try:
                client = Groq(api_key=GROQ_API_KEY)
                
                # Menggunakan model Groq resmi yang aktif
                models_to_try = [
                    "llama-3.1-8b-instant",
                    "llama3-8b-8192",
                    "llama3-70b-8192"
                ]
                
                bot_reply = None
                last_err = ""

                for model_name in models_to_try:
                    try:
                        completion = client.chat.completions.create(
                            model=model_name,
                            messages=[
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": user_query}
                            ],
                            temperature=0.2
                        )
                        bot_reply = completion.choices[0].message.content
                        if bot_reply:
                            break
                    except Exception as err:
                        last_err = str(err)
                        continue

                if bot_reply:
                    with st.chat_message("assistant"):
                        st.markdown(bot_reply)
                    st.session_state.messages.append({"role": "assistant", "content": bot_reply})
                else:
                    st.error(f"Gagal memproses pesan: {last_err}")
                
            except Exception as e:
                st.error(f"Gagal memproses pesan: {str(e)}")
