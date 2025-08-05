#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from bs4 import BeautifulSoup

# ========== Barèmes ==========
POINTS = {0: 0.6, 1: 1.3, 2: 1.9, 3: 2.5}
CATEGORIES = {0: "Chocolate", 1: "Bronze", 2: "Silver", 3: "Gold"}

def score_ebitda(x):
    if x < 10: return 0
    elif x < 20: return 1
    elif x < 35: return 2
    else: return 3

def score_margin(x):
    if x < 8: return 0
    elif x < 15: return 1
    elif x < 25: return 2
    else: return 3

def score_de_ratio(x):
    if x > 1: return 0
    elif x > 0.5: return 1
    elif x > 0.25: return 2
    else: return 3

def score_current(x):
    if x < 1.2: return 0
    elif x < 1.5: return 1
    elif x < 3: return 2
    else: return 3

def score_quick(x):
    if x < 1: return 0
    elif x < 1.5: return 1
    elif x < 3: return 2
    else: return 3

def score_roa(x):
    if x < 5: return 0
    elif x < 8: return 1
    elif x < 12: return 2
    else: return 3

def score_roe(x):
    if x < 10: return 0
    elif x < 15: return 1
    elif x < 25: return 2
    else: return 3

def score_analyst(x):
    if x > 3.5: return 0
    elif x > 2.5: return 1
    elif x > 1.5: return 2
    else: return 3

def safe_extract(info, key, default=None):
    return info.get(key, default)

# ======== FINVIZ PEERS SCRAPER ==========
def get_finviz_peers(ticker):
    url = f"https://finviz.com/quote.ashx?t={ticker}"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        td = soup.find("td", class_="js-quote-correlation-links-container")
        if not td:
            return []
        peers = [a.text.strip().upper() for a in td.find_all("a", class_="tab-link")]
        peers = [p for p in peers if p != ticker.upper()]
        return peers[:5]
    except Exception as e:
        return []

# ======== SCORING POUR LE TICKER PRINCIPAL ==========
def analyze_ticker(ticker):
    info = yf.Ticker(ticker).info
    d = {
        "EBITDA": safe_extract(info, "ebitdaMargins", 0)*100,
        "Marge nette": safe_extract(info, "profitMargins", 0)*100,
        "D/E ratio": safe_extract(info, "debtToEquity", 0)/100,
        "Current ratio": safe_extract(info, "currentRatio", 0),
        "Quick ratio": safe_extract(info, "quickRatio", 0),
        "ROA": safe_extract(info, "returnOnAssets", 0)*100,
        "ROE": safe_extract(info, "returnOnEquity", 0)*100,
        "Analystes": safe_extract(info, "recommendationMean", 3),
    }
    if d["D/E ratio"] == 0:
        d["D/E ratio"] = safe_extract(info, "debtToEquity", 0)

    scores = [
        score_ebitda(d["EBITDA"]),
        score_margin(d["Marge nette"]),
        score_de_ratio(d["D/E ratio"]),
        score_current(d["Current ratio"]),
        score_quick(d["Quick ratio"]),
        score_roa(d["ROA"]),
        score_roe(d["ROE"]),
        score_analyst(d["Analystes"])
    ]
    labels = ["EBITDA", "Marge nette", "D/E ratio", "Current ratio", "Quick ratio", "ROA", "ROE", "Analystes"]
    points = [POINTS[s] for s in scores]
    cats = [CATEGORIES[s] for s in scores]
    note = sum(points)
    # Résumé détaillé seulement pour le principal
    df_detail = pd.DataFrame({
        "Critère": labels,
        "Valeur": [d[k] for k in labels],
        "Score": cats,
        "Points": points,
    })
    return df_detail, note

def get_note_only(ticker):
    try:
        _, note = analyze_ticker(ticker)
        return note
    except Exception:
        return None

# ========== FRONTEND STREAMLIT ==========
st.set_page_config(layout="wide")
st.title("📊 Scoring automatique & comparatif sectoriel (Finviz + Yahoo Finance)")
st.caption("Entrez un ticker US, analyse complète + comparaison automatique des scores sectoriels.")

TICKER_PRINCIPAL = st.text_input("Entrez le ticker principal (ex: AAPL)", value="PAY").upper()

if st.button("Lancer l'analyse & le comparatif"):
    # 1. Ratios détaillés pour le principal uniquement
    try:
        df_detail, note_principal = analyze_ticker(TICKER_PRINCIPAL)
    except Exception as e:
        st.error(f"Erreur : impossible d'extraire les données pour {TICKER_PRINCIPAL} ({e})")
        st.stop()

    st.subheader(f"Ratios et scoring pour : {TICKER_PRINCIPAL}")
    st.dataframe(df_detail, use_container_width=True)

    # 2. Peers
    peers = get_finviz_peers(TICKER_PRINCIPAL)
    all_tickers = [TICKER_PRINCIPAL] + peers

    # 3. Calculer les notes finales (sur 20)
    notes_data = []
    for t in all_tickers:
        note = get_note_only(t)
        if note is not None:
            finviz_url = f"https://finviz.com/quote.ashx?t={t}"
            name_display = t
            # Lien cliquable pour les peers uniquement
            if t != TICKER_PRINCIPAL:
                name_display = f'<a href="{finviz_url}" target="_blank">{t}</a>'
            notes_data.append({
                "Entreprise": name_display,
                "Note sur 20": round(note, 2)
            })

    # 4. Tableau des notes finales, en mode HTML pour les liens cliquables
    st.markdown("### Notes finales (sur 20)")
    df_notes = pd.DataFrame(notes_data)
    st.write(df_notes.to_html(escape=False, index=False), unsafe_allow_html=True)

    st.caption("Cliquez sur un nom d'entreprise du secteur pour ouvrir sa fiche sur Finviz.")

    st.success("Analyse et comparaison terminées ✅")

# ====================


