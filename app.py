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
def load_sheet_tab(sheet_id, tab_name):
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={tab_name}"
    try:
        df = pd.read_csv(url)
        df = df.dropna(how="all").dropna(how="all", axis=1)
        if not df.empty:
            return f"\n--- TAB: {tab_name} ---\n" + df.to_csv(index=False)
    except Exception:
        pass
    return ""

def get_smart_context(sheet_id, query):
    q = query.lower()
    tabs = []
    
    # Filter tab sesuai kebutuhan pertanyaan (Sangat Hemat Token)
    if any(k in q for k in ["insentif", "poin", "point", "absen", "kata kunci"]):
        tabs.append("INSENTIF")
    if any(k in q for k in ["nik", "nama", "jabatan", "identitas", "job", "alamat"]):
        tabs.append("INDENTITAS")
    if any(k in q for k in ["kpi", "whu", "ofr"]):
        tabs.append("KPI")
    if any(k in q for k in ["pencapaian", "box", "pcs", "lead time"]):
        tabs.append("PENCAPAIAN")
    if any(k in q for k in ["tcode", "t-code", "code"]):
        tabs.append("T-CODE")
    
    # Jika sapaan santai / tidak spesifik, muat tab INSENTIF & INDENTITAS saja
    if not tabs:
        tabs = ["INSENTIF", "INDENTITAS"]

    context = ""
    for tab in tabs:
        context += load_sheet_tab(sheet_id, tab)
    return context

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

        # Hanya muat context tab yang dibutuhkan pengguna
        context_data = get_smart_context(SHEET_ID, user_query)

        system_prompt = f"""
        Kamu adalah asisten bot informasi DC Marunda.

        ATURAN KEAMANAN & PRIVASI (SANGAT PENTING):
        1. DILARANG KERAS MENAMPILKAN / MEMBOCORKAN ISI KOLOM 'Kata kunci' DALAM KONDISI APA PUN, TERMASUK SAAT USER MENANYAKAN IDENTITAS KARYAWAN.
        2. Khusus pertanyaan umum/identitas (NIK, Jabatan, Nama, Alamat): Jawab langsung TANPA pernah menyebutkan kata kunci rahasianya.

        ATURAN VERIFIKASI DATA INSENTIF & POIN:
        1. Data INSENTIF/POIN di kolom 'Total Poin' hanya boleh ditampilkan jika pengguna menyebutkan 'Kata kunci' yang COCOK/BENAR dengan nama karyawan tersebut.
        2. Jika pengguna menyebutkan Kata Kunci yang BENAR, LANGSUNG tampilkan seluruh isi teks rincian poin insentif karyawan tersebut secara rapi dan utuh.
        3. Jika Kata Kunci SALAH / BELUM DIBERIKAN oleh pengguna:
           Sampaikan dengan sopan bahwa data insentif bersifat rahasia dan minta pengguna menyebutkan Kata Kunci yang benar terlebih dahulu.

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

                # Kirim riwayat chat (4 pesan terakhir) agar AI paham konteks
                messages_payload = [{"role": "system", "content": system_prompt}]
                for msg in st.session_state.messages[-4:]:
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
