# ==============================================================================
# GLOBÁLNÍ NASTAVENÍ PRO ANALÝZU TEPLOT A MAPU LOKALIT
# ==============================================================================

# Počátek měření v CSV datech (čas nuly)
POCATEK_MERENI = "2024-04-26 15:00:00"

# Které dny od počátku měření se mají zahrnout do analýzy (filtrace dat)
# Změnou těchto hodnot se automaticky přepočítají průměry a aktualizují všechny grafy i mapy.
DEN_START = 4   # Zahrnout od dne (např. 4. den = 2024-04-30)
DEN_KONEC = 17  # Zahrnout do dne (např. 17. den = 2024-05-13)

# Oprava pro senzor L-V1 (Lesní krajina)
# Od kterého dne se mají brát data pro tento konkrétní senzor (např. 13. den)
LES_OPRAVA_START_DEN = 13

# Střed mapy při prvním načtení [zeměpisná šířka, zeměpisná délka]
MAPA_STRED = [49.7583, 16.6651]  # Moravská Třebová
MAPA_ZOOM = 13

# Souřadnice jednotlivých čidel/lokalit
SOURADNICE = {
    "Centrum města": [49.75798, 16.66414],
    "Městský park": [49.75840, 16.65818],
    "Okraj města": [49.76695, 16.66529],
    "Venkovská krajina": [49.79214, 16.67956],
    "Lesní krajina": [49.76783, 16.60518]
}

# Popisky povrchů do mapy a bublin
POPISY = {
    "Centrum města": "Hustá historická zástavba, kamenná dlažba, beton.",
    "Městský park": "Městská zástavba, tráva a stromy. Došlo k roztavení čidla.",
    "Okraj města": "Zahradní vegetace, u budovy.",
    "Venkovská krajina": "Rodinný dům mimo město, zahradní vegetace.",
    "Lesní krajina": "Lesní porost, plné stínění, nezastavěno."
}

# Barevné schéma pro vizuální odlišení lokalit
# Tyto barvy se použijí pro markery na mapě, grafy i pro decentní akcenty v pravém panelu.
BARVY = {
    "Centrum města": "#e31a1c",      # Červená
    "Okraj města": "#ff7f00",        # Oranžová
    "Městský park": "#fdbf6f",       # Žlutá
    "Venkovská krajina": "#33a02c",  # Zelená
    "Lesní krajina": "#1f78b4"       # Modrá
}
