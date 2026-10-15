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
        # Hapus baris & kolom yang benar-benar kosong
        df = df.dropna(how="all").dropna(how="all", axis=1)
        if not df.empty:
            return f"\n--- TAB: {tab_name} ---\n" + df.to_csv(index=False)
    except Exception:
        pass
    return ""

def get_smart_context(sheet_id, query):
    q = query.lower()
    tabs = []
    
    # Deteksi kebutuhan tab berdasarkan kata kunci pertanyaan
    if any(k in q for k in ["insentif", "poin", "point", "absen", "hewan"]):
        tabs.append("INSENTIF")
    if any(k in q for k in ["nik", "nama", "jabatan", "identitas", "job"]):
        tabs.append("INDENTITAS")
    if any(k in q for k in ["kpi", "whu", "ofr"]):
        tabs.append("KPI")
    if any(k in q for k in ["pencapaian", "box", "pcs", "lead time"]):
        tabs.append("PENCAPAIAN")
    if any(k in q for k in ["tcode", "t-code", "code"]):
        tabs.append("T-CODE")
    
    # Jika sapaan umum / tidak spesifik, default muat tab INDENTITAS & INSENTIF saja
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

        # Hanya ambil data dari tab yang dibutuhkan (Super Hemat Token!)
        context_data = get_smart_context(SHEET_ID, user_query)

        system_prompt = f"""
        Kamu adalah asisten bot informasi DC Marunda.
        Tugasmu adalah menjawab pertanyaan pengguna secara ramah, lengkap, dan akurat berdasarkan data tabel yang diberikan.

        ATURAN TAMPILAN JAWABAN INSENTIF:
        1. Jika pengguna menanyakan data insentif/poin karyawan, tampilkan SELURUH rincian komponen poin yang ada di tabel secara menurun (list/bullet points) yang rapi, contoh:
           Informasi Insentif [Nama Karyawan] per [Tanggal]:
           - NIK: [NIK]
           - Job: [Job/Posisi]
           - [Komponen Point 1]: [Nilai]
           - [Komponen Point 2]: [Nilai]
           - ...
           - Total Poin: [Total Poin]

        2. Tampilkan semua detail rincian kolom yang tersedia agar informasinya lengkap.
        3. Jawab hanya berdasarkan data yang ada di tabel. Jika data tidak ditemukan, sampaikan secara sopan.

        [DATA TABEL OPERASIONAL DC MARUNDA]:
        {context_data}
        """

        with st.spinner("Mencari data..."):
            try:
                client = Groq(api_key=GROQ_API_KEY)
                
                # Auto-detect model aktif di Groq
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
