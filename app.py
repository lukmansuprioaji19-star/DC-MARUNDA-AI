import streamlit as st
import pandas as pd
from groq import Groq

# 1. Konfigurasi Halaman Web Streamlit
st.set_page_config(page_title="Bot Informasi DC Marunda", page_icon="🤖")
st.title("🤖 Bot Informasi DC Marunda")

# 2. Ambil Daftar API Key untuk Fitur Rotation (3 Akun)
API_KEYS = [
    st.secrets.get("GROQ_API_KEY_1", ""),
    st.secrets.get("GROQ_API_KEY_2", ""),
    st.secrets.get("GROQ_API_KEY_3", ""),
]
# Filter key yang tidak kosong
ACTIVE_KEYS = [k for k in API_KEYS if k]

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
    
    # Cek apakah user mengetikkan angka 1-5 di awal pesan
    first_char = query.strip()[0] if query.strip() else ""
    
    if first_char == "1" or any(k in q for k in ["identitas", "jadwal", "alamat", "nik", "nama", "jabatan"]):
        return load_sheet_tab(sheet_id, "INDENTITAS")
    elif first_char == "2" or any(k in q for k in ["insentif", "poin", "point", "absen", "kata kunci"]):
        return load_sheet_tab(sheet_id, "INSENTIF")
    elif first_char == "3" or any(k in q for k in ["kpi", "whu", "ofr"]):
        return load_sheet_tab(sheet_id, "KPI")
    elif first_char == "4" or any(k in q for k in ["pencapaian", "box", "pcs", "lead time"]):
        return load_sheet_tab(sheet_id, "PENCAPAIAN")
    elif first_char == "5" or any(k in q for k in ["tcode", "t-code", "code", "sap"]):
        return load_sheet_tab(sheet_id, "T-CODE")
    else:
        # Default jika pertanyaan umum
        return load_sheet_tab(sheet_id, "INDENTITAS")

# 4. Inisialisasi Riwayat Chat & Tampilan Menu Awal
if "messages" not in st.session_state:
    st.session_state.messages = []
    # Pesan Sapaan & Menu Pilihan Pertama Kali
    welcome_text = """
👋 **Selamat Datang di Bot Informasi DC Marunda!**

Silakan pilih kategori informasi yang ingin Anda tanyakan:
* **[1]** Background Kantor & Jadwal / Identitas Karyawan
* **[2]** Cek Insentif & Poin *(Memerlukan Kata Kunci Rahasia)*
* **[3]** KPI Gudang Operasional
* **[4]** Pencapaian Produktivitas Karyawan
* **[5]** T-Code SAP HANA

*Contoh pertanyaan:*
- Ketik **1** lalu tanyakan *"Jadwal atau Alamat Herry Irawan"*
- Ketik **2** lalu tanyakan *"Insentif Sodikin kata kunci Belut Bingung"*
    """
    st.session_state.messages.append({"role": "assistant", "content": welcome_text})

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 5. Input Pertanyaan Pengguna
user_query = st.chat_input("Ketik pertanyaan Anda di sini...")

if user_query:
    if not ACTIVE_KEYS:
        st.error("API Key Groq belum diset di Secrets Streamlit!")
    else:
        st.session_state.messages.append({"role": "user", "content": user_query})
        with st.chat_message("user"):
            st.markdown(user_query)

        # Muat HANYA 1 TAB SHEET sesuai kategori menu (Hemat Token 90%!)
        context_data = get_context_by_category(SHEET_ID, user_query)

        system_prompt = f"""
        Kamu adalah asisten bot informasi DC Marunda.

        ATURAN KEAMANAN & PRIVASI (SANGAT PENTING):
        1. DILARANG KERAS MENAMPILKAN / MEMBOCORKAN ISI KOLOM 'Kata kunci' DALAM KONDISI APA PUN, TERMASUK SAAT USER MENANYAKAN IDENTITAS KARYAWAN.
        2. Khusus pertanyaan Menu 1 (Identitas, Jadwal, Alamat): Jawab langsung TANPA pernah menyebutkan kata kunci rahasianya.

        ATURAN VERIFIKASI DATA INSENTIF & POIN (MENU 2):
        1. Data INSENTIF/POIN di kolom 'Total Poin' hanya boleh ditampilkan jika pengguna menyebutkan 'Kata kunci' yang COCOK/BENAR dengan nama karyawan tersebut.
        2. Jika pengguna menyebutkan Kata Kunci yang BENAR, LANGSUNG tampilkan seluruh isi teks rincian poin insentif karyawan tersebut secara rapi dan utuh (menurun).
        3. Jika Kata Kunci SALAH / BELUM DIBERIKAN oleh pengguna:
           Sampaikan dengan sopan bahwa data insentif bersifat rahasia dan minta pengguna menyebutkan Nama Karyawan dan Kata Kunci yang benar.

        [DATA TABEL OPERASIONAL DC MARUNDA]:
        {context_data}
        """

        with st.spinner("Mencari data..."):
            bot_reply = None
            last_err = ""

            # Rotasi 3 API Key secara bergantian jika ada key yang habis kuota/error
            for api_key in ACTIVE_KEYS:
                try:
                    client = Groq(api_key=api_key)
                    
                    # OTOMATIS AMBIL DAFTAR MODEL YANG BENAR-BENAR AKTIF DI AKUN TERSEBUT
                    available_models = [m.id for m in client.models.list().data]
                    
                    for model_name in available_models:
                        # Prioritaskan model Llama, Qwen, atau Mixtral yang tersedia
                        if any(brand in model_name.lower() for brand in ["llama", "qwen", "mixtral", "gemma"]):
                            try:
                                completion = client.chat.completions.create(
                                    model=model_name,
                                    messages=[
                                        {"role": "system", "content": system_prompt},
                                        {"role": "user", "content": user_query}
                                    ],
                                    temperature=0.1
                                )
                                bot_reply = completion.choices[0].message.content
                                if bot_reply:
                                    break
                            except Exception as err:
                                last_err = str(err)
                                continue
                    
                    if bot_reply:
                        break # Berhasil dapat jawaban, hentikan loop key
                except Exception as err:
                    last_err = str(err)
                    continue

            if bot_reply:
                with st.chat_message("assistant"):
                    st.markdown(bot_reply)
                st.session_state.messages.append({"role": "assistant", "content": bot_reply})
            else:
                st.error(f"Gagal memproses pesan: {last_err}")
