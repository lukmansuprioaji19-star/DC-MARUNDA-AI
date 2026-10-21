def search_mid_data(sheet_id, query):
    df_mid = load_sheet_df(sheet_id, "MID")
    if df_mid.empty:
        return "\n--- DATA TAB: MID kosong atau tidak ditemukan ---\n"
    
    words = [w.strip() for w in query.lower().split() if len(w.strip()) > 1]
    filtered_df = pd.DataFrame()
    
    mid_col = next((c for c in df_mid.columns if "mid" in c.lower()), df_mid.columns[0])
    desc_col = next((c for c in df_mid.columns if "desc" in c.lower()), df_mid.columns[1] if len(df_mid.columns)>1 else df_mid.columns[0])
    mg2_col = next((c for c in df_mid.columns if "mg2" in c.lower() or "mg" in c.lower()), df_mid.columns[2] if len(df_mid.columns)>2 else None)
    
    # 1. Cek apakah ada nomor MID spesifik dalam query untuk dicari MG2 samanya
    target_mg2 = None
    if mg2_col:
        for word in words:
            exact_mid_match = df_mid[df_mid[mid_col].astype(str).str.strip() == word]
            if not exact_mid_match.empty:
                target_mg2 = exact_mid_match.iloc[0][mg2_col]
                break
    
    # 2. Jika ketemu MID & MG2-nya, ambil SEMUA barang yang punya MG2 sama
    if target_mg2 and mg2_col:
        filtered_df = df_mid[df_mid[mg2_col].astype(str).str.strip().str.lower() == str(target_mg2).strip().lower()]
    else:
        # 3. Pencarian standar berdasarkan kata kunci MID/DESC/MG2
        for word in words:
            cond = (
                df_mid[mid_col].astype(str).str.lower().str.contains(word, na=False) |
                df_mid[desc_col].astype(str).str.lower().str.contains(word, na=False)
            )
            if mg2_col:
                cond = cond | df_mid[mg2_col].astype(str).str.lower().str.contains(word, na=False)
            
            match = df_mid[cond]
            if not match.empty:
                filtered_df = pd.concat([filtered_df, match]).drop_duplicates()
    
    if not filtered_df.empty:
        return f"\n--- DATA TAB: MID (HASIL PENCARIAN RELEVAN) ---\n" + filtered_df.head(30).to_csv(index=False)
    
    return f"\n--- DATA TAB: MID (SAMPEL 10 BARANG PERTAMA) ---\n" + df_mid.head(10).to_csv(index=False)
