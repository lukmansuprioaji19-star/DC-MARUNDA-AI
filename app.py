import streamlit as st
import pandas as pd
from groq import Groq

# 1. Konfigurasi Halaman Web Streamlit
st.set_page_config(page_title="Bot Informasi DC Marunda", page_icon="🤖")
st.title("🤖 Bot Informasi DC Marunda")

# 2. Ambil Semua Kemungkinan API Key dari Secrets Streamlit (Otomatis & Fleksibel)
raw_keys = [
    st.secrets.get("GROQ_API_KEY", ""),
    st.secrets.get("GROQ_API_KEY_1", ""),
    st.secrets.get("GROQ_API_KEY_2", ""),
    st.secrets.get("GROQ_API_KEY_3", ""),
]
# Saring hanya kunci yang tidak kosong dan tidak duplikat
ACTIVE_KEYS = list(set([k for k in raw_keys if k]))

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
- **Identitas & Jadwal Kerja**: *"Siapa saja yang masuk jam 6 pagi?"* atau *"Lu tahu Lukman?"*
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
        st.error("Gagal membaca GROQ_API_KEY di Secrets Streamlit! Pastikan format di Secrets sudah benar.")
    else:
        st.session_state.messages.append({"role": "user", "content": user_query})
        with st.chat_message("user"):
            st.markdown(user_query)

        context_data = get_context_by_category(SHEET_ID, user_query)

        system_prompt = f"""
        Kamu adalah asisten bot informasi DC Marunda.

        ATURAN KEAMANAN & PRIVASI (SANGAT PENTING):
        1. DILARANG KERAS MENAMPILKAN / MEMBOCORKAN ISI KOLOM 'Kata kunci' DALAM KONDISI APA PUN.
        2. Khusus pertanyaan Identitas/Jadwal/Alamat/Pertanyaan Nama Karyawan: Jawab langsung ramah dan ringkas TANPA pernah menyebutkan kata kunci rahasianya.

        ATURAN VERIFIKASI DATA INSENTIF & POIN:
        1. Data INSENTIF/POIN hanya boleh ditampilkan jika pengguna menyertakan 'Kata kunci' yang COCOK/BENAR dengan nama karyawan tersebut.
        2. Jika Nama dan Kata Kunci BENAR (contoh: "Sodikin Belut Bingung"), LANGSUNG tampilkan rincian poin insentif karyawan tersebut secara ringkas dan rapi (list menurun).
        3. Jika Kata Kunci SALAH / BELUM DIBERIKAN:
           Minta pengguna menyebutkan Nama Karyawan dan Kata Kunci yang benar terlebih dahulu.

        [DATA TABEL OPERASIONAL DC MARUNDA]:
        {context_data}
        """

        with st.spinner("Mencari data..."):
            bot_reply = None
            last_err = ""

            messages_payload = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_query}
            ]

            for api_key in ACTIVE_KEYS:
                try:
                    client = Groq(api_key=api_key)
                    models_list = client.models.list().data
                    valid_models = [m.id for m in models_list if "llama" in m.id.lower() and "guard" not in m.id.lower()]
                    
                    for model_name in valid_models:
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
