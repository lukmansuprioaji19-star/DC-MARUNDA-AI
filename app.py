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
    
    if not tabs:
        tabs = ["INDENTITAS"]

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

        context_data = get_smart_context(SHEET_ID, user_query)

        system_prompt = f"""
        Kamu adalah asisten bot informasi DC Marunda.

        ATURAN KEAMANAN & RAHASIA DATA INSENTIF (SANGAT PENTING):
        1. Khusus untuk pertanyaan mengenai data INSENTIF karyawan:
           - Kamu HARUS memeriksa apakah pengguna telah menyertakan kata kunci "Hewan Lucu" yang sesuai untuk nama karyawan tersebut (data terdapat pada kolom 'Hewan Lucu' di tab INSENTIF).
           - Jika pengguna BELUM menyebutkan kata kunci "Hewan Lucu" atau kata kuncinya SALAH/TIDAK COCOK dengan nama karyawan yang ditanyakan:
             Sampaikan dengan sopan bahwa data insentif bersifat rahasia dan minta pengguna menyebutkan kata kunci/Hewan Lucu yang benar terlebih dahulu.
           - Jika pengguna SUDAH menyebutkan kata kunci "Hewan Lucu" yang BENAR dan cocok dengan nama karyawannya:
             Tampilkan rincian insentif secara lengkap.

        2. FORMAT TAMPILAN JAWABAN INSENTIF:
           Tampilkan rincian data insentif secara menurun (list/bullet points) yang rapi, contoh:
           Insentif [Nama Karyawan] per tanggal [Tanggal]:
           - Point Absen: [Point] - Rp [Nominal]
           - Point Daily PI: [Point] - Rp [Nominal]
           - [Komponen insentif lain yang ada nilainya]

        3. Untuk pertanyaan umum (seperti Jabatan, NIK, KPI, Pencapaian, T-Code), kamu boleh menjawab langsung tanpa perlu kata kunci, kecuali jika pengguna menanyakan data insentif.

        [DATA TABEL OPERASIONAL DC MARUNDA]:
        {context_data}
        """

        with st.spinner("Mencari data..."):
            try:
                client = Groq(api_key=GROQ_API_KEY)
                
                # NAMA MODEL RESMI GROQ AKTIF: llama3-8b-8192
                completion = client.chat.completions.create(
                    model="llama3-8b-8192",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_query}
                    ],
                    temperature=0.2
                )
                
                bot_reply = completion.choices[0].message.content
                
                with st.chat_message("assistant"):
                    st.markdown(bot_reply)
                st.session_state.messages.append({"role": "assistant", "content": bot_reply})
                
            except Exception as e:
                st.error(f"Gagal memproses pesan: {str(e)}")
