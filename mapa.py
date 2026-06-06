import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import matplotlib.dates as mdates
import folium
import base64
from io import BytesIO

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

# Časová korekce a oříznutí
pocatek_mereni = pd.to_datetime("2024-04-26 15:00:00")
df_vysledne.index = pocatek_mereni + pd.to_timedelta(df_vysledne.index, unit="h")
df_vysledne.index.name = "Datum_a_Cas"

# Oříznutí dat (bez prvních a posledních 3 dnů)
df_vysledne = df_vysledne[(df_vysledne.index >= pocatek_mereni + pd.Timedelta(days=4)) & 
                          (df_vysledne.index <= pocatek_mereni + pd.Timedelta(days=17))]

# Oprava pro senzor L-V1
mask = df_vysledne.index >= pocatek_mereni + pd.Timedelta(days=13)
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

# Barevné schéma
barvy = {
    "Centrum města": "#e31a1c",      # Červená
    "Okraj města": "#ff7f00",        # Oranžová
    "Městský park": "#fdbf6f",       # Žlutá
    "Venkovská krajina": "#33a02c",  # Zelená
    "Lesní krajina": "#1f78b4"       # Modrá
}

# ==============================================================================
# KROK 3: NASTAVENÍ MAPY A SOUŘADNIC LOKALIT
# ==============================================================================
# SEM ZAPIŠ PŘESNÉ SOUŘADNICE TVÝCH ČIDEL (Formát: [Zeměpisná šířka, Zeměpisná délka])
# Tyto souřadnice najdeš například tak, že klikneš pravým tlačítkem do Google Map
souradnice = {
    "Centrum města": [49.75798, 16.66414],       # <-- DOPLŇ SKUTEČNÉ SOUŘADNICE
    "Městský park": [49.75840, 16.65818],        # <-- DOPLŇ SKUTEČNÉ SOUŘADNICE
    "Okraj města": [49.76695, 16.66529],         # <-- DOPLŇ SKUTEČNÉ SOUŘADNICE
    "Venkovská krajina": [49.79214, 16.67956],   # <-- DOPLŇ SKUTEČNÉ SOUŘADNICE (Staré Město)
    "Lesní krajina": [49.76783, 16.60518]        # <-- DOPLŇ SKUTEČNÉ SOUŘADNICE
}

# Popisky povrchů do mapy (uprav si podle sebe z tvé Tabulky 2)
popisy = {
    "Centrum města": "Hustá historická zástavba, kamenná dlažba, beton.",
    "Městský park": "Městská zástavba, tráva a stromy. Došlo k roztavení čidla.",
    "Okraj města": "Zahradní vegetace, u budovy.",
    "Venkovská krajina": "Rodinný dům mimo město, zahradní vegetace.",
    "Lesní krajina": "Lesní porost, plné stínění, nezastavěno."
}

# Vytvoření základní mapy s centrem v Moravské Třebové
mapa = folium.Map(location=[49.7583, 16.6651], zoom_start=13, tiles="CartoDB positron")

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