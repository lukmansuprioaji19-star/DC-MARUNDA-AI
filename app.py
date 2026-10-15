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
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={tab_name}"
    try:
        df = pd.read_csv(url)
        # Hapus baris dan kolom yang benar-benar kosong
        df = df.dropna(how="all").dropna(how="all", axis=1)
        # Bersihkan nama kolom dari spasi berlebih
        df.columns = [str(col).strip() for col in df.columns]
        if not df.empty:
            # Ubah ke string Markdown rapi daripada CSV mentah agar AI tidak bingung
            return f"\n--- TAB: {tab_name} ---\n" + df.to_markdown(index=False)
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
        return load_sheet_tab(sheet_id, "INDENTITAS")

# 4. Inisialisasi Riwayat Chat
if "messages" not in st.session_state:
    st.session_state.messages = []
    welcome_text = """
👋 **Selamat Datang di Bot Informasi DC Marunda!**

Silakan tanyakan informasi yang Anda butuhkan:
- **Identitas & Jadwal Kerja**: *"Siapa saja yang masuk jam 6 pagi?"* atau *"Sodikin jabatannya apa?"*
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
        st.error("Gagal membaca GROQ_API_KEY di Secrets Streamlit! Pastikan Secrets sudah terisi.")
    else:
        st.session_state.messages.append({"role": "user", "content": user_query})
        with st.chat_message("user"):
            st.markdown(user_query)

        context_data = get_context_by_category(SHEET_ID, user_query)

        system_prompt = f"""
        Kamu adalah asisten bot informasi DC Marunda yang komunikatif, ramah, dan rapi.

        ATURAN FORMAT JAWABAN:
        1. Jawablah SELALU menggunakan Bahasa Indonesia yang mudah dipahami, ramah, dan rapi (gunakan bullet points/daftar).
        2. DILARANG KERAS menyajikan jawaban berupa potongan CSV mentah atau teks deretan koma melingkar (seperti '51040682.0, Muhammad Fauzi, ZONE...').
        3. Jika mencari karyawan berdasarkan jam masuk atau zona, saring data secara teliti dan hanya tampilkan nama-nama unik (jangan mengulang nama yang sama berkali-kali).

        ATURAN KEAMANAN & PRIVASI (SANGAT PENTING):
        1. DILARANG KERAS MENAMPILKAN / MEMBOCORKAN ISI KOLOM 'Kata kunci' DALAM KONDISI APA PUN.
        2. Khusus pertanyaan Identitas/Jadwal/Alamat/Jabatan Karyawan: Jawab langsung ramah dan ringkas TANPA pernah menyebutkan kata kunci rahasianya.

        ATURAN VERIFIKASI DATA INSENTIF & POIN:
        1. Data INSENTIF/POIN hanya boleh ditampilkan jika pengguna menyertakan 'Kata kunci' yang COCOK/BENAR dengan nama karyawan tersebut.
        2. Jika Nama dan Kata Kunci BENAR (contoh: "Sodikin Belut Bingung"), LANGSUNG tampilkan rincian poin insentif karyawan tersebut secara ringkas dan rapi.
        3. Jika Kata Kunci SALAH / BELUM DIBERIKAN:
           Minta pengguna menyebutkan Nama Karyawan dan Kata Kunci yang benar terlebih dahulu.

        [DATA TABEL OPERASIONAL DC MARUNDA]:
        {context_data}
        """

        with st.spinner("Mencari data..."):
            bot_reply = None
            last_err = "Gagal memproses."

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
