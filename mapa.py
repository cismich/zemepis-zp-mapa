import pandas as pd
# pyrefly: ignore [missing-import]
import matplotlib.pyplot as plt
# pyrefly: ignore [missing-import]
import numpy as np
# pyrefly: ignore [missing-import]
import matplotlib.dates as mdates
# pyrefly: ignore [missing-import]
import folium
# pyrefly: ignore [missing-import]
import base64
# pyrefly: ignore [missing-import]
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

# Oprava pro senzor L-V1 podle nastavení (v hlavním datasetu necháme jako chybějící hodnoty pro výpočty)
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

# Převod celých realných dat df_vysledne do JSONu (pro prohlížeč dat a CSV)
df_pro_json = df_vysledne.copy()
df_pro_json.index = df_pro_json.index.strftime('%Y-%m-%d %H:%M')
# Nahrazení případných NaN (chybějících) hodnot za None, aby se v JSONu správně uložily jako null
df_pro_json = df_pro_json.replace({np.nan: None})
json_data = json.dumps(df_pro_json.to_dict(orient='index'))

# Příprava odhadnutých dat do JSONu (pouze pro interaktivní srovnávací graf v modalu)
df_imputed = df_vysledne.copy()
if getattr(settings, "LES_IMPUTACE_AKTIVNI", False):
    metoda = getattr(settings, "LES_IMPUTACE_METODA", "linear")
    
    if "Lesní krajina" in df_imputed.columns:
        mask_missing = df_imputed["Lesní krajina"].isna()
        
        if metoda == "multiple":
            # Vícesenzorová regrese podle všech ostatních dostupných senzorů
            predictor_cols = [c for c in df_imputed.columns if c != ("Lesní krajina" or "Městský park")]
            
            # Ošetříme případné NaNs v prediktorech (ffill + bfill)
            df_predictors = df_imputed[predictor_cols].ffill().bfill()
            
            # Překryvné období pro odhad (kde Lesní krajina má reálná data)
            df_prekryv = df_imputed[["Lesní krajina"]].copy()
            df_prekryv = df_prekryv.join(df_predictors).dropna()
            
            if len(df_prekryv) >= len(predictor_cols) + 1:
                X_train = df_prekryv[predictor_cols].values
                X_train = np.hstack([np.ones((X_train.shape[0], 1)), X_train])  # sloupec jedniček pro absolutní člen
                y_train = df_prekryv["Lesní krajina"].values
                
                # Výpočet koeficientů metodou nejmenších čtverců
                beta, _, _, _ = np.linalg.lstsq(X_train, y_train, rcond=None)
                
                # Predikce chybějících hodnot
                X_predict = df_predictors.loc[mask_missing, predictor_cols].values
                X_predict = np.hstack([np.ones((X_predict.shape[0], 1)), X_predict])
                odhad = np.dot(X_predict, beta)
                
                coef_desc = ", ".join([f"{name}: {coef:.3f}" for name, coef in zip(predictor_cols, beta[1:])])
                print(f"Odhady pro graf Lesní krajiny vypočteny vícesenzorovou regresí (intercept: {beta[0]:.3f}, {coef_desc})")
                df_imputed.loc[mask_missing, "Lesní krajina"] = odhad
            else:
                print("VAROVÁNÍ: Nedostatek překrývajících se dat pro vícesenzorovou regresi. Používám jednoduchou regresi.")
                metoda = "linear"  # Fallback na lineární regresi
                
        if metoda in ["linear", "offset"]:
            ref_col = getattr(settings, "LES_IMPUTACE_REFERENCE", "Niky")
            ref_col_mapped = nazvy_prostredi.get(ref_col, ref_col)
            
            if ref_col_mapped in df_imputed.columns:
                df_prekryv = df_imputed[["Lesní krajina", ref_col_mapped]].dropna()
                
                if len(df_prekryv) >= 2:
                    if metoda == "linear":
                        # Lineární fit: L-V1 = a * ref + b
                        a, b = np.polyfit(df_prekryv[ref_col_mapped], df_prekryv["Lesní krajina"], 1)
                        odhad = df_imputed.loc[mask_missing, ref_col_mapped] * a + b
                        print(f"Odhady pro graf Lesní krajiny vypočteny lineární regresí podle '{ref_col_mapped}' (a={a:.3f}, b={b:.3f})")
                    else:
                        # Konstantní posun: L-V1 = ref + průměrný_rozdíl
                        rozdil = (df_prekryv["Lesní krajina"] - df_prekryv[ref_col_mapped]).mean()
                        odhad = df_imputed.loc[mask_missing, ref_col_mapped] + rozdil
                        print(f"Odhady pro graf Lesní krajiny vypočteny posunem podle '{ref_col_mapped}' (rozdíl: {rozdil:.2f} °C)")
                    
                    df_imputed.loc[mask_missing, "Lesní krajina"] = odhad
                else:
                    print("VAROVÁNÍ: Překryvné období neobsahuje dostatek společných dat. Chybějící data nebudou nahrazena.")
            else:
                print(f"VAROVÁNÍ: Referenční senzor '{ref_col_mapped}' nebyl nalezen. Chybějící data nebudou nahrazena.")

df_imputed_pro_json = df_imputed.copy()
df_imputed_pro_json.index = df_imputed_pro_json.index.strftime('%Y-%m-%d %H:%M')
df_imputed_pro_json = df_imputed_pro_json.replace({np.nan: None})
json_imputed_data = json.dumps(df_imputed_pro_json.to_dict(orient='index'))

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

# Pomocná funkce pro načítání webových šablon ze souborů
def nacti_sablonu(nazev_souboru):
    with open(f"templates/{nazev_souboru}", "r", encoding="utf-8") as f:
        return f.read()

# Načtení šablon ze souborů (modulární struktura)
overlay_html = nacti_sablonu("overlay.html")
overlay_css = nacti_sablonu("overlay.css")
overlay_js = nacti_sablonu("overlay.js")

# Sestavení finálního kódu pro injektáž do HTML
injected_html = f"""
<!-- INTERAKTIVNÍ PRAVÝ PANEL MĚŘENÍ -->
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
<style>
{overlay_css}
</style>

{overlay_html}

<script>
{overlay_js}
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
injected_html = injected_html.replace("{json_imputed_data_str}", json_imputed_data)
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