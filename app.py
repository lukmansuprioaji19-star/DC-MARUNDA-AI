import streamlit as st
import pandas as pd
from groq import Groq

# 1. Konfigurasi Halaman Web Streamlit
st.set_page_config(page_title="DC Marunda AI", page_icon="🤖")
st.title("🤖 DC Marunda AI")

# 2. Ambil Semua API Key dari Secrets Streamlit (Rotasi Opsi Kunci)
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
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={tab_name}"
    try:
        df = pd.read_csv(url)
        # Hapus baris & kolom yang seluruh isinya kosong
        df = df.dropna(how="all").dropna(how="all", axis=1)
        
        # Bersihkan nama header kolom
        df.columns = [str(col).strip() for col in df.columns]
        
        if not df.empty:
            return f"\n--- DATA TAB: {tab_name} ---\n" + df.to_csv(index=False)
    except Exception:
        pass
    return ""

def get_context_by_category(sheet_id, query):
    q = query.lower()
    
    # 1. Kategori Insentif & Poin
    if any(k in q for k in ["insentif", "poin", "point", "kata kunci"]):
        return load_sheet_tab(sheet_id, "INSENTIF")
    
    # 2. Kategori KPI
    elif any(k in q for k in ["kpi", "whu", "ofr"]):
        return load_sheet_tab(sheet_id, "KPI")
    
    # 3. Kategori Pencapaian Operasional
    elif any(k in q for k in ["pencapaian", "box", "pcs", "lead time"]):
        return load_sheet_tab(sheet_id, "PENCAPAIAN")
    
    # 4. Kategori SAP & T-Code
    elif any(k in q for k in ["tcode", "t-code", "code", "sap", "spkb", "wavepick", "running"]):
        return load_sheet_tab(sheet_id, "T-CODE")
    
    # 5. Kategori Identitas, Jadwal & Karyawan
    elif any(k in q for k in ["jadwal", "masuk", "kerja", "shift", "identitas", "nama", "jabatan", "nik", "siapa", "karyawan", "lu tahu", "u tahu", "tahu"]):
        return load_sheet_tab(sheet_id, "INDENTITAS")
    
    # PINTU DEFAULT: Jika topik/kata kunci tidak dikenal
    else:
        return "UNKNOWN_CATEGORY"

# 4. Inisialisasi Riwayat Chat
if "messages" not in st.session_state:
    st.session_state.messages = []
    welcome_text = """
👋 **Selamat Datang di DC Marunda AI!**

Silakan tanyakan informasi yang Anda butuhkan:
- **Identitas & Jadwal Kerja**: *"Siapa saja yang masuk jam 6 pagi?"* atau *"Sodikin jabatannya apa?"*
- **Cek Insentif**: *"Sodikin Belut Bingung"* (Memerlukan Kata Kunci)
- **T-Code SAP**: *"T-Code running SPKB"*
- **KPI & Pencapaian**: *"Cek KPI"* atau *"Pencapaian lead time"*
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

        # A. JIKA KATEGORI TIDAK DIKENAL (Langsung tampilkan menu panduan lokal)
        if context_data == "UNKNOWN_CATEGORY":
            guide_reply = """
Mohon maaf, kata kunci topik belum dikenali. 🙏

Agar saya dapat menampilkan data operasional **DC Marunda** yang tepat, silakan sertakan topik/kata kunci berikut:

- 📅 **Jadwal & Identitas**: Ketik nama, jabatan, atau jadwal (misal: *"Jadwal masuk jam 6"* atau *"Sodikin jabatannya apa"*).
- 💰 **Cek Insentif**: Sebutkan Nama Karyawan & Kata Kunci Rahasia.
- 💻 **T-Code SAP**: Ketik kata *"T-Code"*, *"SAP"*, *"SPKB"*, atau *"Wavepick"*.
- 📊 **KPI & Pencapaian**: Ketik *"KPI"*, *"Pencapaian"*, *"Box"*, atau *"Lead Time"*.
"""
            with st.chat_message("assistant"):
                st.markdown(guide_reply)
            st.session_state.messages.append({"role": "assistant", "content": guide_reply})

        # B. JIKA KATEGORI COCOK (Proses via AI Groq)
        else:
            system_prompt = f"""
            Kamu adalah asisten bot informasi operasional DC Marunda.

            ATURAN FORMAT JAWABAN (WAJIB DIPATUHI):
            1. Jawablah menggunakan Bahasa Indonesia yang ramah, sopan, dan rapi menggunakan bullet points.
            2. DILARANG KERAS mengeluarkan teks potongan CSV mentah atau daftar nama berulang-ulang secara acak.
            3. Jika ditanya jadwal/jam masuk, saring data secara teliti dan tampilkan daftar NAMA UNIK karyawan beserta jabatannya secara rapi.

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
                                    max_tokens=500
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
