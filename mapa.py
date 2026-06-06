import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import matplotlib.dates as mdates
import folium
import base64
from io import BytesIO
import settings

# ==============================================================================
# KROK 1: NAČTENÍ A OČIŠTĚNÍ DAT
# ==============================================================================
df_raw = pd.read_csv("data_teplomery.csv", header=None)
cidla_list = []

for i in range(0, df_raw.shape[1], 2):
    nazev_cidla = df_raw.iloc[0, i]
    if pd.isna(nazev_cidla):
        continue
    
    data_cidla = df_raw.iloc[1:, [i, i + 1]].copy()
    data_cidla.columns = ["Hodina", nazev_cidla]
    data_cidla["Hodina"] = pd.to_numeric(data_cidla["Hodina"], errors="coerce")
    data_cidla[nazev_cidla] = pd.to_numeric(data_cidla[nazev_cidla], errors="coerce")
    data_cidla = data_cidla.dropna(how="all").set_index("Hodina")
    cidla_list.append(data_cidla)

df_vysledne = pd.concat(cidla_list, axis=1, join="outer").sort_index()

# Časová korekce a oříznutí ze settings.py
pocatek_mereni = pd.to_datetime(settings.POCATEK_MERENI)
df_vysledne.index = pocatek_mereni + pd.to_timedelta(df_vysledne.index, unit="h")
df_vysledne.index.name = "Datum_a_Cas"

# Oříznutí dat (zahrnutí dnů z nastavení)
df_vysledne = df_vysledne[(df_vysledne.index >= pocatek_mereni + pd.Timedelta(days=settings.DEN_START)) & 
                          (df_vysledne.index <= pocatek_mereni + pd.Timedelta(days=settings.DEN_KONEC))]

# Oprava pro senzor L-V1 podle nastavení
mask = df_vysledne.index >= pocatek_mereni + pd.Timedelta(days=settings.LES_OPRAVA_START_DEN)
if "L-V1" in df_vysledne.columns:
    df_vysledne.loc[~mask, "L-V1"] = np.nan

# Přejmenování čidel na hezké názvy (provedeno hned na začátku pro usnadnění)
nazvy_prostredi = {
    "GMT-M1": "Městský park",
    "JH-V1 SK38": "Centrum města",
    "JH-V2": "Okraj města",
    "Niky": "Venkovská krajina",
    "L-V1": "Lesní krajina"
}
df_vysledne = df_vysledne.rename(columns=nazvy_prostredi)

# ==============================================================================
# KROK 2: VÝPOČTY PRŮMĚRŮ PRO MAPU (Den, Noc, Celkově)
# ==============================================================================
hodiny = df_vysledne.index.hour
je_den = (hodiny >= 6) & (hodiny < 22)

# Vytvoření oddělených tabulek pro den a noc
df_den = df_vysledne[je_den]
df_noc = df_vysledne[~je_den]

prumery_celkove = df_vysledne.mean().round(2)
prumery_den = df_den.mean().round(2)
prumery_noc = df_noc.mean().round(2)

# Seskupení pro denní profil (0-23 h) - využijeme pro malé grafy do mapy
denni_chod = df_vysledne.groupby(df_vysledne.index.hour).mean()

# Výpočet UHI průměrného rozdílu a dalších celkových statistik pro pravý panel
mesto_cols = [c for c in ["Centrum města", "Městský park"] if c in df_vysledne.columns]
priroda_cols = [c for c in ["Okraj města", "Venkovská krajina", "Lesní krajina"] if c in df_vysledne.columns]

if mesto_cols and priroda_cols:
    df_mesto_avg = df_vysledne[mesto_cols].mean(axis=1)
    df_priroda_avg = df_vysledne[priroda_cols].mean(axis=1)
    rozdil_skupin_avg = df_mesto_avg - df_priroda_avg
    prumerny_rozdil_celkovy = rozdil_skupin_avg.mean()
else:
    prumerny_rozdil_celkovy = 0.0

# Výpočet extrémních průměrných teplot pro statistické karty
hottest_loc = prumery_celkove.idxmax() if not prumery_celkove.empty else "N/A"
hottest_temp = prumery_celkove.max() if not prumery_celkove.empty else 0.0
coolest_loc = prumery_celkove.idxmin() if not prumery_celkove.empty else "N/A"
coolest_temp = prumery_celkove.min() if not prumery_celkove.empty else 0.0

# Barevné schéma, souřadnice a popisy načtené ze settings.py
barvy = settings.BARVY
souradnice = settings.SOURADNICE
popisy = settings.POPISY

# Vytvoření základní mapy s parametry ze settings.py
mapa = folium.Map(location=settings.MAPA_STRED, zoom_start=settings.MAPA_ZOOM, tiles="CartoDB positron")

# ==============================================================================
# KROK 4: VKLÁDÁNÍ BODŮ A GRAFŮ DO MAPY
# ==============================================================================
for lokalita in souradnice.keys():
    if lokalita in df_vysledne.columns:
        
        # 1. Vygenerování miniaturního grafu pro bublinu v mapě
        fig, ax = plt.subplots(figsize=(4, 2.5))
        ax.plot(denni_chod.index, denni_chod[lokalita], color=barvy[lokalita], linewidth=2)
        ax.set_title(f"Průměrný denní chod teplot - {lokalita}", fontsize=10)
        ax.set_xlabel("Hodina", fontsize=8)
        ax.set_ylabel("Teplota (°C)", fontsize=8)
        ax.tick_params(axis='both', which='major', labelsize=8)
        ax.grid(True, linestyle=':', alpha=0.6)
        plt.tight_layout()
        
        # Převedení grafu na obrázek v textovém formátu (Base64), aby šel vložit do HTML
        buf = BytesIO()
        plt.savefig(buf, format='png', dpi=100)
        plt.close(fig)
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode('utf-8')
        
        # 2. Vytvoření HTML obsahu pro bublinu (Popup)
        html_obsah = f"""
        <div style="font-family: Arial, sans-serif; width: 350px;">
            <h3 style="color: {barvy[lokalita]}; margin-bottom: 5px;">{lokalita}</h3>
            <p style="font-size: 12px; margin-top: 0px; color: #555;"><i>{popisy[lokalita]}</i></p>
            <table style="width: 100%; border-collapse: collapse; font-size: 12px; margin-bottom: 10px;">
                <tr style="border-bottom: 1px solid #ddd;">
                    <td style="padding: 3px;"><b>Průměrná teplota:</b></td>
                    <td style="padding: 3px; text-align: right;">{prumery_celkove[lokalita]} °C</td>
                </tr>
                <tr style="border-bottom: 1px solid #ddd;">
                    <td style="padding: 3px;"><b>Ve dne (06-22):</b></td>
                    <td style="padding: 3px; text-align: right;">{prumery_den[lokalita]} °C</td>
                </tr>
                <tr>
                    <td style="padding: 3px;"><b>V noci (22-06):</b></td>
                    <td style="padding: 3px; text-align: right;"><b>{prumery_noc[lokalita]} °C</b></td>
                </tr>
            </table>
            <img src="data:image/png;base64,{img_base64}" style="width: 100%;">
        </div>
        """
        
        # Vytvoření iFrame a Popup pro Folium
        iframe = folium.IFrame(html=html_obsah, width=380, height=340)
        popup = folium.Popup(iframe, max_width=380)
        
        # 3. Přidání bodu (Markeru) do mapy
        folium.Circle(
            location=souradnice[lokalita],
            radius=150,  # Poloměr kruhu v metrech
            popup=popup,
            color=barvy[lokalita],
            fill=True,
            fill_color=barvy[lokalita],
            fill_opacity=0.8,
            tooltip=lokalita # Text, který se ukáže při přejetí myší
        ).add_to(mapa)

# Uložení mapy do souboru
mapa.save("mapa_lokalit.html")

# ==============================================================================
# POST-PROCESSING: INJEKTÁŽ INTERAKTIVNÍHO OVERLAY PANELU DO VYGENEROVANÉHO HTML
# ==============================================================================
print("\nProbíhá injektáž interaktivního panelu s daty a nastavením do HTML...")

import json

# Převod souřadnic na JSON pro JavaScript
json_coords = json.dumps(souradnice)

# Převod celých dat df_vysledne do JSONu (pro prohlížeč dat v JS)
df_pro_json = df_vysledne.copy()
df_pro_json.index = df_pro_json.index.strftime('%Y-%m-%d %H:%M')
# Nahrazení případných NaN (chybějících) hodnot za None, aby se v JSONu správně uložily jako null
df_pro_json = df_pro_json.replace({np.nan: None})
json_data = json.dumps(df_pro_json.to_dict(orient='index'))

# Dynamická tvorba HTML pro seznam lokalit v panelu
sensor_cards_html = ""
for lokalita in souradnice.keys():
    if lokalita in df_vysledne.columns:
        sensor_color = barvy[lokalita]
        sensor_cards_html += f"""
        <div class="sensor-card" style="--sensor-color: {sensor_color};" onclick="focusSensor('{lokalita}')">
          <div class="sensor-card-header">
            <span class="sensor-name">{lokalita}</span>
            <span class="sensor-type">{popisy[lokalita]}</span>
          </div>
          <div class="sensor-averages">
            <div class="sensor-avg-item">
              <span class="sensor-avg-lbl">Celkově</span>
              <span class="sensor-avg-val">{prumery_celkove[lokalita]:.2f} °C</span>
            </div>
            <div class="sensor-avg-item">
              <span class="sensor-avg-lbl">Den (6-22)</span>
              <span class="sensor-avg-val">{prumery_den[lokalita]:.2f} °C</span>
            </div>
            <div class="sensor-avg-item">
              <span class="sensor-avg-lbl">Noc (22-6)</span>
              <span class="sensor-avg-val" style="font-weight: 700; color: {sensor_color};">{prumery_noc[lokalita]:.2f} °C</span>
            </div>
          </div>
        </div>
        """

# Dynamická tvorba HTML možností pro výběr senzoru
sensor_options_html = ""
for lokalita in souradnice.keys():
    if lokalita in df_vysledne.columns:
        sensor_options_html += f'<option value="{lokalita}">{lokalita}</option>'

# Kompletní HTML, CSS a JS kód panelu
injected_html = """
<!-- INTERAKTIVNÍ PRAVÝ PANEL MĚŘENÍ -->
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
<style>
  @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap');
  
  :root {
    --panel-bg-light: rgba(255, 255, 255, 0.82);
    --panel-bg-dark: rgba(15, 23, 42, 0.85);
    --text-light: #1e293b;
    --text-dark: #f1f5f9;
    --border-light: rgba(255, 255, 255, 0.35);
    --border-dark: rgba(255, 255, 255, 0.08);
  }

  #overlay-toggle-btn {
    position: fixed;
    top: 15px;
    right: 15px;
    width: 48px;
    height: 48px;
    border-radius: 50%;
    background: rgba(255, 255, 255, 0.85);
    backdrop-filter: blur(8px);
    -webkit-backdrop-filter: blur(8px);
    border: 1px solid rgba(255, 255, 255, 0.4);
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    z-index: 10000;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  }
  
  #overlay-toggle-btn:hover {
    transform: scale(1.05);
    box-shadow: 0 6px 24px rgba(0, 0, 0, 0.12);
    border-color: rgba(255, 255, 255, 0.6);
  }

  #overlay-toggle-btn i {
    font-size: 18px;
    color: #334155;
    transition: transform 0.3s;
  }
  
  #overlay-toggle-btn.open i {
    transform: rotate(90deg);
  }

  #right-overlay {
    position: fixed;
    top: 0;
    right: 0;
    height: 100vh;
    width: 440px;
    max-width: 100vw;
    background: var(--panel-bg-light);
    backdrop-filter: blur(18px);
    -webkit-backdrop-filter: blur(18px);
    border-left: 1px solid var(--border-light);
    box-shadow: -10px 0 30px rgba(0, 0, 0, 0.1);
    z-index: 9999;
    font-family: 'Outfit', sans-serif;
    color: var(--text-light);
    transform: translateX(100%);
    transition: transform 0.4s cubic-bezier(0.16, 1, 0.3, 1);
    display: flex;
    flex-direction: column;
    box-sizing: border-box;
  }

  #right-overlay.open {
    transform: translateX(0);
  }

  #right-overlay.dark-theme {
    background: var(--panel-bg-dark);
    border-left: 1px solid var(--border-dark);
    color: var(--text-dark);
  }

  #overlay-header {
    padding: 24px 24px 16px 24px;
    border-bottom: 1px solid rgba(0, 0, 0, 0.05);
    display: flex;
    align-items: center;
    justify-content: space-between;
  }
  
  #right-overlay.dark-theme #overlay-header {
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  }

  #overlay-header h2 {
    margin: 0;
    font-size: 20px;
    font-weight: 700;
    letter-spacing: -0.02em;
    background: linear-gradient(135deg, #1e293b, #475569);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }

  #right-overlay.dark-theme #overlay-header h2 {
    background: linear-gradient(135deg, #ffffff, #cbd5e1);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }

  #overlay-header p {
    margin: 2px 0 0 0;
    font-size: 12px;
    color: #64748b;
  }
  
  #right-overlay.dark-theme #overlay-header p {
    color: #94a3b8;
  }

  #overlay-close-btn {
    background: transparent;
    border: none;
    font-size: 24px;
    cursor: pointer;
    color: #64748b;
    display: flex;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 32px;
    border-radius: 50%;
    transition: background 0.2s, color 0.2s;
  }

  #overlay-close-btn:hover {
    background: rgba(0,0,0,0.05);
    color: #0f172a;
  }

  #right-overlay.dark-theme #overlay-close-btn:hover {
    background: rgba(255,255,255,0.08);
    color: #ffffff;
  }

  #overlay-content {
    flex: 1;
    overflow-y: auto;
    padding: 24px;
    display: flex;
    flex-direction: column;
    gap: 24px;
    scrollbar-width: thin;
  }

  .section-title {
    font-size: 13px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #64748b;
    margin: 0 0 12px 0;
    display: flex;
    align-items: center;
    gap: 8px;
  }
  
  #right-overlay.dark-theme .section-title {
    color: #94a3b8;
  }

  /* Dashboard Stats Grid */
  .stats-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 12px;
  }

  .stat-card {
    background: rgba(255, 255, 255, 0.45);
    border: 1px solid rgba(0,0,0,0.04);
    border-radius: 12px;
    padding: 12px;
    display: flex;
    flex-direction: column;
    transition: transform 0.2s, background 0.2s;
  }
  
  #right-overlay.dark-theme .stat-card {
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.04);
  }

  .stat-card:hover {
    transform: translateY(-2px);
    background: rgba(255, 255, 255, 0.65);
  }
  
  #right-overlay.dark-theme .stat-card:hover {
    background: rgba(255, 255, 255, 0.06);
  }

  .stat-label {
    font-size: 10px;
    font-weight: 500;
    color: #64748b;
    text-transform: uppercase;
    letter-spacing: 0.02em;
    margin-bottom: 4px;
    line-height: 1.2;
  }

  .stat-value {
    font-size: 15px;
    font-weight: 700;
    color: #0f172a;
    word-break: break-all;
  }
  
  #right-overlay.dark-theme .stat-value {
    color: #ffffff;
  }

  .stat-sub {
    font-size: 9px;
    color: #94a3b8;
    margin-top: 2px;
  }

  /* Sensors List */
  .sensors-list {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .sensor-card {
    background: rgba(255, 255, 255, 0.45);
    border: 1px solid rgba(0,0,0,0.04);
    border-left: 4px solid var(--sensor-color);
    border-radius: 10px;
    padding: 12px;
    cursor: pointer;
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
    display: flex;
    flex-direction: column;
    gap: 6px;
  }
  
  #right-overlay.dark-theme .sensor-card {
    background: rgba(255, 255, 255, 0.03);
    border-color: rgba(255, 255, 255, 0.04);
    border-left-color: var(--sensor-color);
  }

  .sensor-card:hover {
    background: rgba(255, 255, 255, 0.75);
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.02);
  }
  
  #right-overlay.dark-theme .sensor-card:hover {
    background: rgba(255, 255, 255, 0.07);
  }

  .sensor-card-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 8px;
  }

  .sensor-name {
    font-size: 13px;
    font-weight: 600;
    color: #0f172a;
    white-space: nowrap;
  }
  
  #right-overlay.dark-theme .sensor-name {
    color: #ffffff;
  }

  .sensor-type {
    font-size: 11px;
    color: #64748b;
    font-style: italic;
    text-align: right;
    word-break: break-word;
  }
  
  #right-overlay.dark-theme .sensor-type {
    color: #94a3b8;
  }

  .sensor-averages {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 8px;
    background: rgba(0,0,0,0.02);
    padding: 6px 8px;
    border-radius: 6px;
    font-size: 10.5px;
  }
  
  #right-overlay.dark-theme .sensor-averages {
    background: rgba(255, 255, 255, 0.02);
  }

  .sensor-avg-item {
    display: flex;
    flex-direction: column;
  }
  
  .sensor-avg-lbl {
    color: #64748b;
    font-size: 9px;
  }
  
  .sensor-avg-val {
    font-weight: 600;
    color: #334155;
  }

  #right-overlay.dark-theme .sensor-avg-val {
    color: #cbd5e1;
  }

  /* Data Explorer */
  .explorer-container {
    background: rgba(255, 255, 255, 0.35);
    border: 1px solid rgba(0,0,0,0.04);
    border-radius: 12px;
    padding: 16px;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }
  
  #right-overlay.dark-theme .explorer-container {
    background: rgba(255, 255, 255, 0.02);
    border-color: rgba(255, 255, 255, 0.04);
  }

  .form-group {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .form-group label {
    font-size: 11px;
    font-weight: 500;
    color: #64748b;
    text-transform: uppercase;
  }

  .select-input {
    width: 100%;
    padding: 8px 12px;
    border-radius: 8px;
    border: 1px solid rgba(0,0,0,0.08);
    background: rgba(255,255,255,0.7);
    font-family: inherit;
    font-size: 13px;
    color: inherit;
    outline: none;
    transition: border-color 0.2s;
  }

  .select-input:focus {
    border-color: #94a3b8;
  }

  #right-overlay.dark-theme .select-input {
    background: rgba(15, 23, 42, 0.6);
    border-color: rgba(255,255,255,0.08);
  }

  .search-export-bar {
    display: flex;
    gap: 8px;
  }

  .search-input {
    flex: 1;
    padding: 8px 12px;
    border-radius: 8px;
    border: 1px solid rgba(0,0,0,0.08);
    background: rgba(255,255,255,0.7);
    font-family: inherit;
    font-size: 13px;
    color: inherit;
    outline: none;
  }
  
  #right-overlay.dark-theme .search-input {
    background: rgba(15, 23, 42, 0.6);
    border-color: rgba(255,255,255,0.08);
  }

  .action-btn {
    padding: 8px 12px;
    border-radius: 8px;
    border: 1px solid rgba(0,0,0,0.08);
    background: #0f172a;
    color: #ffffff;
    font-family: inherit;
    font-size: 13px;
    font-weight: 500;
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: 6px;
    transition: background 0.2s;
  }

  .action-btn:hover {
    background: #334155;
  }
  
  #right-overlay.dark-theme .action-btn {
    background: #f1f5f9;
    color: #0f172a;
    border-color: transparent;
  }
  
  #right-overlay.dark-theme .action-btn:hover {
    background: #cbd5e1;
  }

  .table-wrapper {
    max-height: 200px;
    overflow-y: auto;
    border: 1px solid rgba(0,0,0,0.05);
    border-radius: 8px;
    background: rgba(255,255,255,0.2);
  }
  
  #right-overlay.dark-theme .table-wrapper {
    border-color: rgba(255, 255, 255, 0.05);
    background: rgba(0,0,0,0.1);
  }

  .data-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 12px;
    text-align: left;
  }

  .data-table th {
    position: sticky;
    top: 0;
    background: #f8fafc;
    padding: 8px 12px;
    font-weight: 600;
    color: #64748b;
    text-transform: uppercase;
    font-size: 10px;
    border-bottom: 1px solid rgba(0,0,0,0.05);
  }
  
  #right-overlay.dark-theme .data-table th {
    background: #1e293b;
    color: #94a3b8;
    border-bottom-color: rgba(255, 255, 255, 0.05);
  }

  .data-table td {
    padding: 8px 12px;
    border-bottom: 1px solid rgba(0,0,0,0.02);
  }
  
  #right-overlay.dark-theme .data-table td {
    border-bottom-color: rgba(255, 255, 255, 0.02);
  }

  .data-table tbody tr:hover {
    background: rgba(0,0,0,0.02);
  }
  
  #right-overlay.dark-theme .data-table tbody tr:hover {
    background: rgba(255,255,255,0.02);
  }

  /* Controls Section */
  .control-card {
    background: rgba(255, 255, 255, 0.35);
    border: 1px solid rgba(0,0,0,0.04);
    border-radius: 12px;
    padding: 16px;
    display: flex;
    flex-direction: column;
    gap: 16px;
  }
  
  #right-overlay.dark-theme .control-card {
    background: rgba(255, 255, 255, 0.02);
    border-color: rgba(255, 255, 255, 0.04);
  }

  .control-row {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .control-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .control-label {
    font-size: 11px;
    font-weight: 500;
    color: #64748b;
    text-transform: uppercase;
  }

  .control-value {
    font-size: 12px;
    font-weight: 600;
    color: #334155;
  }
  
  #right-overlay.dark-theme .control-value {
    color: #cbd5e1;
  }

  /* Range Input Stylings */
  .range-slider {
    width: 100%;
    -webkit-appearance: none;
    background: rgba(0,0,0,0.08);
    height: 6px;
    border-radius: 3px;
    outline: none;
  }
  
  #right-overlay.dark-theme .range-slider {
    background: rgba(255,255,255,0.1);
  }

  .range-slider::-webkit-slider-thumb {
    -webkit-appearance: none;
    appearance: none;
    width: 16px;
    height: 16px;
    border-radius: 50%;
    background: #0f172a;
    cursor: pointer;
    transition: transform 0.1s;
  }
  
  .range-slider::-webkit-slider-thumb:hover {
    transform: scale(1.2);
  }

  #right-overlay.dark-theme .range-slider::-webkit-slider-thumb {
    background: #f1f5f9;
  }

  /* Basemap Toggles */
  .basemap-group {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
  }

  .basemap-btn {
    padding: 8px;
    border-radius: 8px;
    border: 1px solid rgba(0,0,0,0.08);
    background: rgba(255,255,255,0.6);
    font-family: inherit;
    font-size: 12px;
    font-weight: 500;
    cursor: pointer;
    color: #475569;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
    transition: all 0.2s;
  }

  .basemap-btn.active {
    background: #0f172a;
    color: #ffffff;
    border-color: #0f172a;
  }

  #right-overlay.dark-theme .basemap-btn {
    background: rgba(255,255,255,0.03);
    border-color: rgba(255,255,255,0.06);
    color: #94a3b8;
  }

  #right-overlay.dark-theme .basemap-btn.active {
    background: #f1f5f9;
    color: #0f172a;
    border-color: transparent;
  }
</style>

<div id="overlay-toggle-btn" onclick="toggleOverlay()">
  <i class="fa-solid fa-sliders"></i>
</div>

<div id="right-overlay">
  <div id="overlay-header">
    <div>
      <h2>Analýza teplot</h2>
      <p>Moravská Třebová & okolí</p>
    </div>
    <button id="overlay-close-btn" onclick="toggleOverlay()">&times;</button>
  </div>
  
  <div id="overlay-content">
    <!-- STATS -->
    <div>
      <h3 class="section-title"><i class="fa-solid fa-chart-simple"></i> Přehled měření</h3>
      <div class="stats-grid">
        <div class="stat-card">
          <span class="stat-label">Intenzita UHI</span>
          <span class="stat-value">{prumerny_rozdil_celkovy:.2f} °C</span>
          <span class="stat-sub">město vs venkov</span>
        </div>
        <div class="stat-card">
          <span class="stat-label">Nejteplejší</span>
          <span class="stat-value" style="font-size: 11px; font-weight:700;">{hottest_loc}</span>
          <span class="stat-sub">{hottest_temp:.2f} °C průměr</span>
        </div>
        <div class="stat-card">
          <span class="stat-label">Nejchladnější</span>
          <span class="stat-value" style="font-size: 11px; font-weight:700;">{coolest_loc}</span>
          <span class="stat-sub">{coolest_temp:.2f} °C průměr</span>
        </div>
      </div>
    </div>
    
    <!-- LOCATIONS -->
    <div>
      <h3 class="section-title"><i class="fa-solid fa-location-dot"></i> Měřicí lokality</h3>
      <div class="sensors-list">
        {sensor_cards_html}
      </div>
    </div>
    
    <!-- DATA EXPLORER -->
    <div>
      <h3 class="section-title"><i class="fa-solid fa-database"></i> Prohlížeč dat</h3>
      <div class="explorer-container">
        <div class="form-group">
          <label for="sensor-select">Zvolit senzor</label>
          <select id="sensor-select" class="select-input" onchange="loadSensorData()">
            {sensor_options_html}
          </select>
        </div>
        
        <div class="search-export-bar">
          <input type="text" id="table-search" class="search-input" placeholder="Hledat datum / teplotu..." oninput="filterTable()">
          <button class="action-btn" onclick="exportToCSV()"><i class="fa-solid fa-download"></i> CSV</button>
        </div>
        
        <div class="table-wrapper">
          <table class="data-table" id="data-table">
            <thead>
              <tr>
                <th>Čas měření</th>
                <th>Teplota (°C)</th>
              </tr>
            </thead>
            <tbody id="table-body">
              <!-- Dynamické řádky pomocí JS -->
            </tbody>
          </table>
        </div>
      </div>
    </div>
    
    <!-- MAP SETTINGS -->
    <div>
      <h3 class="section-title"><i class="fa-solid fa-gears"></i> Nastavení mapy</h3>
      <div class="control-card">
        <div class="control-row">
          <div class="control-header">
            <span class="control-label">Velikost bodů (Radius)</span>
            <span class="control-value" id="radius-val">150 m</span>
          </div>
          <input type="range" class="range-slider" id="radius-slider" min="50" max="1000" value="150" step="10" oninput="changeRadius(this.value)">
        </div>
        
        <div class="control-row">
          <span class="control-label" style="margin-bottom: 4px;">Mapový podklad</span>
          <div class="basemap-group">
            <button class="basemap-btn active" id="basemap-light" onclick="setBasemap('light')">
              <i class="fa-solid fa-sun"></i> Světlý
            </button>
            <button class="basemap-btn" id="basemap-dark" onclick="setBasemap('dark')">
              <i class="fa-solid fa-moon"></i> Tmavý
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</div>

<script>
  // Dynamická data injektovaná z Pythonu
  const rawSensorData = {json_data_str};
  const sensorCoords = {json_coords_str};
  
  let mapInstance = null;
  const sensorCircles = {};
  
  // Custom dlaždice pro přepínač basemap
  let lightTiles = null;
  let darkTiles = L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
    attribution: "&copy; OpenStreetMap contributors &copy; CARTO",
    subdomains: "abcd",
    maxZoom: 20
  });

  // Přepínání vysunutí panelu
  function toggleOverlay() {
    const overlay = document.getElementById("right-overlay");
    const toggleBtn = document.getElementById("overlay-toggle-btn");
    overlay.classList.toggle("open");
    toggleBtn.classList.toggle("open");
  }

  // Pomocná inicializace pro přístup k Leafletu
  function initLeafletAccess() {
    // Nalezení instance mapy na objektu window
    for (let key in window) {
      if (key.startsWith("map_") && window[key] instanceof L.Map) {
        mapInstance = window[key];
        break;
      }
    }
    
    if (!mapInstance) {
      console.warn("Leaflet map instance nebyla nalezena!");
      return;
    }

    // Odchycení výchozí světlé tile mapy
    mapInstance.eachLayer((layer) => {
      if (layer instanceof L.TileLayer && !lightTiles) {
        lightTiles = layer;
      }
    });

    // Vyhledání a uložení kruhových markerů
    mapInstance.eachLayer((layer) => {
      if (layer instanceof L.Circle) {
        const name = getCleanTooltipText(layer);
        if (name) {
          sensorCircles[name] = layer;
        }
      }
    });
  }

  function getCleanTooltipText(layer) {
    const tooltip = layer.getTooltip();
    if (!tooltip) return null;
    const content = tooltip.getContent();
    const tempDiv = document.createElement("div");
    tempDiv.innerHTML = content;
    return tempDiv.textContent.trim() || tempDiv.innerText.trim();
  }

  // Centrování mapy a otevření popupu na vybraný senzor
  function focusSensor(name) {
    if (!mapInstance) initLeafletAccess();
    
    const circle = sensorCircles[name];
    if (circle) {
      mapInstance.setView(circle.getLatLng(), 15, {
        animate: true,
        duration: 1.2
      });
      circle.openPopup();
      
      // Pro mobilní displeje skryjeme panel, aby byla mapa vidět
      if (window.innerWidth < 600) {
        toggleOverlay();
      }
    }
  }

  // Změna poloměru kružnic
  function changeRadius(value) {
    document.getElementById("radius-val").textContent = value + " m";
    if (!mapInstance) initLeafletAccess();
    
    for (let name in sensorCircles) {
      sensorCircles[name].setRadius(parseInt(value));
    }
  }

  // Změna mapového podkladu a barevného motivu panelu
  function setBasemap(theme) {
    if (!mapInstance) initLeafletAccess();
    if (!mapInstance) return;

    const btnLight = document.getElementById("basemap-light");
    const btnDark = document.getElementById("basemap-dark");
    const panel = document.getElementById("right-overlay");
    const toggleBtn = document.getElementById("overlay-toggle-btn");

    if (theme === 'dark') {
      btnLight.classList.remove("active");
      btnDark.classList.add("active");
      panel.classList.add("dark-theme");
      toggleBtn.style.background = "rgba(15, 23, 42, 0.85)";
      toggleBtn.style.borderColor = "rgba(255, 255, 255, 0.08)";
      toggleBtn.querySelector("i").style.color = "#f1f5f9";
      
      if (lightTiles) mapInstance.removeLayer(lightTiles);
      darkTiles.addTo(mapInstance);
    } else {
      btnDark.classList.remove("active");
      btnLight.classList.add("active");
      panel.classList.remove("dark-theme");
      toggleBtn.style.background = "rgba(255, 255, 255, 0.85)";
      toggleBtn.style.borderColor = "rgba(255, 255, 255, 0.4)";
      toggleBtn.querySelector("i").style.color = "#334155";
      
      mapInstance.removeLayer(darkTiles);
      if (lightTiles) lightTiles.addTo(mapInstance);
    }
  }

  // Načtení dat vybraného senzoru do prohlížeče
  function loadSensorData() {
    const sensorName = document.getElementById("sensor-select").value;
    const tbody = document.getElementById("table-body");
    tbody.innerHTML = "";

    const records = [];
    for (let time in rawSensorData) {
      const val = rawSensorData[time][sensorName];
      if (val !== null && val !== undefined) {
        records.push({ time, val });
      }
    }

    // Seřazení záznamů od nejnovějšího po nejstarší
    records.sort((a, b) => b.time.localeCompare(a.time));

    records.forEach(rec => {
      const tr = document.createElement("tr");
      const tdTime = document.createElement("td");
      tdTime.textContent = rec.time;
      const tdVal = document.createElement("td");
      tdVal.innerHTML = `<strong>${rec.val.toFixed(2)}</strong> °C`;
      tr.appendChild(tdTime);
      tr.appendChild(tdVal);
      tbody.appendChild(tr);
    });
    
    document.getElementById("table-search").value = "";
  }

  // Vyhledávání v tabulce dat
  function filterTable() {
    const query = document.getElementById("table-search").value.toLowerCase();
    const rows = document.querySelectorAll("#table-body tr");
    
    rows.forEach(row => {
      const text = row.textContent.toLowerCase();
      row.style.display = text.includes(query) ? "" : "none";
    });
  }

  // Export zobrazených dat tabulky do CSV souboru
  function exportToCSV() {
    const sensorName = document.getElementById("sensor-select").value;
    const rows = document.querySelectorAll("#table-body tr");
    
    let csvContent = "";
    // Hlavička s BOM pro správné kódování češtiny v Excelu
    csvContent = "\uFEFF" + "Cas mereni,Teplota - " + sensorName + " (C)\\r\\n";
    
    let count = 0;
    rows.forEach(row => {
      if (row.style.display !== "none") {
        const cells = row.querySelectorAll("td");
        if (cells.length >= 2) {
          const time = cells[0].textContent;
          const temp = cells[1].textContent.replace(" °C", "").trim();
          csvContent += time + "," + temp + "\\r\\n";
          count++;
        }
      }
    });

    if (count === 0) {
      alert("Žádná data pro export.");
      return;
    }

    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const encodedUri = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", "teploty_" + sensorName.replace(/\s+/g, '_') + ".csv");
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }

  // Automatické načtení a dohledání Leaflet objektů po načtení stránky
  window.addEventListener("load", () => {
    initLeafletAccess();
    loadSensorData();
  });
</script>
"""

# Zástupné řetězce (placeholders) pro Python format nahradíme textovými hodnotami
injected_html = injected_html.replace("{prumerny_rozdil_celkovy}", f"{prumerny_rozdil_celkovy:.2f}")
injected_html = injected_html.replace("{hottest_loc}", str(hottest_loc))
injected_html = injected_html.replace("{hottest_temp}", f"{hottest_temp:.2f}")
injected_html = injected_html.replace("{coolest_loc}", str(coolest_loc))
injected_html = injected_html.replace("{coolest_temp}", f"{coolest_temp:.2f}")
injected_html = injected_html.replace("{sensor_cards_html}", sensor_cards_html)
injected_html = injected_html.replace("{sensor_options_html}", sensor_options_html)
injected_html = injected_html.replace("{json_data_str}", json_data)
injected_html = injected_html.replace("{json_coords_str}", json_coords)

# Načtení hotového HTML souboru, vložení panelu před </body> a uložení
with open("mapa_lokalit.html", "r", encoding="utf-8") as f:
    html_content = f.read()

if "</body>" in html_content:
    html_content = html_content.replace("</body>", injected_html + "\n</body>")
    with open("mapa_lokalit.html", "w", encoding="utf-8") as f:
        f.write(html_content)
    print("Injektáž ovládacího panelu do 'mapa_lokalit.html' proběhla úspěšně!")
else:
    print("VAROVÁNÍ: V HTML souboru nebyl nalezen tag </body>, panel nebyl injektován.")

print("\n=== INTERAKTIVNÍ MAPA BYLA ÚSPĚŠNĚ VYTVOŘENA ===")
print("Otevři soubor 'mapa_lokalit.html' ve svém webovém prohlížeči.\n")

# ==============================================================================
# KROK 5: TVÉ PŮVODNÍ VYKRESLOVÁNÍ GRAFŮ A ANALÝZ
# ==============================================================================
# Tvé grafy pro textovou část práce (využijí upravená data z KROKU 1)
df_grafy = df_vysledne.copy()

# ... ZDE MŮŽEŠ VLOŽIT ZBYTEK SVÉHO KÓDU NA VYKRESLOVÁNÍ PROFESIONÁLNÍCH GRAFŮ ...
# Například graf "Průběh teplot v různých typech zástavby" atd.

# Ukázka zachování tisku pro UHI:
df_grafy["Městské prostředí (průměr)"] = df_grafy[["Centrum města", "Městský park"]].mean(axis=1)
df_grafy["Přírodní zázemí (průměr)"] = df_grafy[["Okraj města", "Venkovská krajina", "Lesní krajina"]].mean(axis=1)
rozdil_skupin = df_grafy["Městské prostředí (průměr)"] - df_grafy["Přírodní zázemí (průměr)"]

prumerny_rozdil_celkovy = rozdil_skupin.mean()
print(f"Průměrně bylo ve městě o {prumerny_rozdil_celkovy:.2f} °C tepleji než na venkově.")

# plt.show() # Odkomentuj pro zobrazení běžných Matplotlib grafů