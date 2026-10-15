import streamlit as st
import pandas as pd
from groq import Groq

# 1. Konfigurasi Halaman Web Streamlit
st.set_page_config(page_title="Bot Informasi DC Marunda", page_icon="🤖")
st.title("🤖 Bot Informasi DC Marunda")

# 2. Ambil Semua API Key dari Secrets Streamlit
raw_keys = [
    st.secrets.get("GROQ_API_KEY", ""),
    st.secrets.get("GROQ_API_KEY_1", ""),
    st.secrets.get("GROQ_API_KEY_2", ""),
    st.secrets.get("GROQ_API_KEY_3", ""),
]
ACTIVE_KEYS = list(dict.fromkeys([k for k in raw_keys if k]))

# 3. ID Google Sheet Operasional DC Marunda
SHEET_ID = "1pCLPIS2Gi55_hQPTAp8v753TeU6WWPbchAAKGPDg6wE"

@st.cache_data(ttl=60)
def load_sheet_tab(sheet_id, tab_name):
    # Menggunakan export format CSV spesifik per nama sheet
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={tab_name}"
    try:
        df = pd.read_csv(url)
        # Hapus baris & kolom yang seluruh isinya kosong
        df = df.dropna(how="all").dropna(how="all", axis=1)
        
        # Ambil maksimal 4 kolom pertama saja (NIK, Nama, Job, Shift/Hari) untuk menghemat token & membuang kolom sampah di kanan
        if tab_name == "INDENTITAS" and df.shape[1] >= 4:
            df = df.iloc[:, :4]
            
        if not df.empty:
            return f"\n--- DATA TAB: {tab_name} ---\n" + df.to_string(index=False)
    except Exception:
        pass
    return ""

def get_context_by_category(sheet_id, query):
    q = query.lower()
    if any(k in q for k in ["insentif", "poin", "point", "kata kunci"]):
        return load_sheet_tab(sheet_id, "INSENTIF")
    elif any(k in q for k in ["kpi", "whu", "ofr"]):
        return load_sheet_tab(sheet_id, "KPI")
    elif any(k in q for k in ["pencapaian", "box", "pcs", "lead time"]):
        return load_sheet_tab(sheet_id, "PENCAPAIAN")
    elif any(k in q for k in ["tcode", "t-code", "code", "sap"]):
        return load_sheet_tab(sheet_id, "T-CODE")
    else:
        # PENTING: Memanggil nama tab "INDENTITAS" (sesuai judul tab di Google Sheet)
        return load_sheet_tab(sheet_id, "INDENTITAS")

# 4. Inisialisasi Riwayat Chat
if "messages" not in st.session_state:
    st.session_state.messages = []
    welcome_text = """
👋 **Selamat Datang di Bot Informasi DC Marunda!**

Silakan tanyakan informasi yang Anda butuhkan:
- **Identitas & Jadwal Kerja**: *"Siapa saja yang masuk jam 6 pagi?"* atau *"Anwar jam berapa masuk?"*
- **Cek Insentif**: *"Sodikin Belut Bingung"* (Memerlukan Kata Kunci)
    """
    st.session_state.messages.append({"role": "assistant", "content": welcome_text})

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 5. Input Pertanyaan Pengguna
user_query = st.chat_input("Ketik pertanyaan Anda di sini...")

if user_query:
    if not ACTIVE_KEYS:
        st.error("Gagal membaca GROQ_API_KEY di Secrets Streamlit!")
    else:
        st.session_state.messages.append({"role": "user", "content": user_query})
        with st.chat_message("user"):
            st.markdown(user_query)

        context_data = get_context_by_category(SHEET_ID, user_query)

        system_prompt = f"""
        Kamu adalah asisten bot informasi operasional DC Marunda.

        ATURAN FORMAT JAWABAN (WAJIB DIPATUHI):
        1. Jawablah menggunakan Bahasa Indonesia yang ramah, sopan, dan rapi menggunakan bullet points.
        2. DILARANG KERAS mengeluarkan teks potongan CSV mentah atau daftar nama berulang-ulang seperti (ZONE - W X Y, Muhammad Fikri...).
        3. Jika ditanya jadwal/jam masuk (misal jam 6:00 atau jam 6 pagi), saring data hanya dari kolom jadwal/Senin, lalu tampilkan daftar NAMA UNIK karyawan beserta jabatannya secara rapi.

        ATURAN KEAMANAN & PRIVASI:
        1. DILARANG KERAS MENAMPILKAN / MEMBOCORKAN ISI KOLOM 'Kata kunci' DALAM KONDISI APA PUN.
        2. Khusus data Insentif/Poin: Hanya tampilkan jika pengguna menyertakan Kata Kunci yang BENAR.

        [DATA TABEL OPERASIONAL DC MARUNDA]:
        {context_data}
        """

        with st.spinner("Mencari data..."):
            bot_reply = None
            last_err = "Gagal memproses pesan."

            messages_payload = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_query}
            ]

            for api_key in ACTIVE_KEYS:
                try:
                    client = Groq(api_key=api_key)
                    all_models = client.models.list().data
                    available_text_models = [
                        m.id for m in all_models 
                        if "guard" not in m.id.lower() and "whisper" not in m.id.lower()
                    ]

                    for model_name in available_text_models:
                        try:
                            completion = client.chat.completions.create(
                                model=model_name,
                                messages=messages_payload,
                                temperature=0.1,
                                max_tokens=600
                            )
                            bot_reply = completion.choices[0].message.content
                            if bot_reply:
                                break
                        except Exception as m_err:
                            last_err = str(m_err)
                            continue
                    
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
