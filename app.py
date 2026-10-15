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

        ATURAN KEAMANAN & PRIVASI (SANGAT PENTING):
        1. DILARANG KERAS MENAMPILKAN / MEMBOCORKAN ISI KOLOM 'Kata Kunci' (seperti Belut Bingung, Kucing Keriting, dll) DALAM KONDISI APA PUN, TERMASUK SAAT USER MENANYAKAN IDENTITAS KARYAWAN.
        2. Khusus pertanyaan umum/identitas (NIK, Jabatan, Nama): Jawab langsung TANPA menyebutkan kata kunci rahasianya.

        ATURAN VERIFIKASI DATA INSENTIF & POIN:
        1. Data INSENTIF/POIN hanya boleh diberikan jika pengguna menyebutkan 'Kata kunci' yang cocok dengan karyawan tersebut.
        2. Jika pengguna hanya mengetikkan Kata Kunci (contoh: "belut bingung") atau menanyakan insentif setelah chat sebelumnya:
           - Periksa seluruh tabel untuk menemukan karyawan yang memiliki Kata Kunci tersebut.
           - Jika Kata Kunci BENAR/COCOK dengan karyawan (misal: "Belut Bingung" milik Sodikin), LANGSUNG tampilkan seluruh rincian insentif dan poin karyawan tersebut secara lengkap dan rapi (menurun).
        3. Jika Kata Kunci SALAH / BELUM DIBERIKAN:
           - Sampaikan dengan sopan bahwa data insentif bersifat rahasia dan minta pengguna menyebutkan Kata Kunci yang benar.

        FORMAT JAWABAN INSENTIF:
        Tampilkan rincian data insentif secara menurun (list/bullet points) yang rapi.

        [DATA TABEL OPERASIONAL DC MARUNDA]:
        {context_data}
        """

        with st.spinner("Mencari data..."):
            try:
                client = Groq(api_key=GROQ_API_KEY)
                
                # Ambil daftar model aktif di Groq
                available_models = [m.id for m in client.models.list().data]
                
                bot_reply = None
                last_err = ""

                # Buat percakapan memahami riwayat chat sebelumnya
                messages_payload = [{"role": "system", "content": system_prompt}]
                for msg in st.session_state.messages:
                    messages_payload.append({"role": msg["role"], "content": msg["content"]})

                for model_name in available_models:
                    if any(brand in model_name.lower() for brand in ["llama", "qwen", "mixtral", "gemma"]):
                        try:
                            completion = client.chat.completions.create(
                                model=model_name,
                                messages=messages_payload,
                                temperature=0.1
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
