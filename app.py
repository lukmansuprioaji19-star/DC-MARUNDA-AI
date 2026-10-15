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
            # Hapus baris & kolom kosong agar super hemat token
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

        ATURAN KEAMANAN & RAHASIA DATA INSENTIF (SANGAT PENTING):
        1. Khusus untuk pertanyaan mengenai data INSENTIF / POIN karyawan:
           - Kamu HARUS memeriksa apakah pengguna telah menyertakan kata kunci yang sesuai untuk nama karyawan tersebut (data terdapat pada kolom 'Kata kunci' di tab INSENTIF).
           - Jika pengguna BELUM menyebutkan 'Kata kunci' atau kata kuncinya SALAH/TIDAK COCOK dengan nama karyawan yang ditanyakan:
             Sampaikan dengan sopan bahwa data insentif bersifat rahasia dan minta pengguna menyebutkan kata kunci yang benar terlebih dahulu.
           - Jika pengguna SUDAH menyebutkan 'Kata kunci' yang BENAR dan cocok dengan nama karyawannya:
             Tampilkan rincian insentif dan poin secara lengkap.

        2. FORMAT TAMPILAN JAWABAN INSENTIF:
           Tampilkan rincian data insentif secara menurun (list/bullet points) yang rapi, contoh:
           Informasi Insentif [Nama Karyawan] per tanggal [Tanggal]:
           - NIK: [NIK]
           - Job: [Job/Posisi]
           - Total Poin / Rincian: [Total Poin / Rincian dari tabel]

        3. Untuk pertanyaan umum di luar insentif (seperti NIK, Jabatan, KPI, Pencapaian, T-Code), kamu boleh menjawab langsung tanpa perlu kata kunci.

        [DATA TABEL OPERASIONAL DC MARUNDA]:
        {context_data}
        """

        with st.spinner("Mencari data..."):
            try:
                client = Groq(api_key=GROQ_API_KEY)
                
                # Otomatis ambil daftar model aktif di akun Groq kamu
                available_models = [m.id for m in client.models.list().data]
                
                bot_reply = None
                last_err = ""

                for model_name in available_models:
                    if any(brand in model_name.lower() for brand in ["llama", "qwen", "mixtral", "gemma"]):
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
