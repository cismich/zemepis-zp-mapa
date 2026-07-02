**🇬🇧 English version available below 🇬🇧**
# Měření městského tepelného ostrova (UHI) – Moravská Třebová

Tento repozitář obsahuje data a zdrojové kódy k mé závěrečné práci ze zeměpisu (2025/2026), která se zabývá měřením teplotních rozdílů mezi městskou zástavbou a okolní venkovskou krajinou. 

Cílem projektu bylo ověřit existenci tzv. tepelného ostrova města (Urban Heat Island - UHI) v podmínkách menšího města (Moravská Třebová). 

## 🛠️ O projektu a hardwaru
Pro účely výzkumu jsem zkonstruoval 5 vlastních meteorologických stanic:
* **Mikrokontrolér:** ESP32
* **Senzor:** Digitální teplotní senzor DS18B20
* **Konstrukce:** 3D tištěná konstrukce, napájení na baterie.

Stanice byly rozmístěny v 5 typech prostředí (centrum města, městský park, okraj města, venkovská zástavba, les) a sbíraly data v hodinovém intervalu po dobu téměř 3 týdnů.

*Přesná místa měření nejsou z důvodu ochrany osobních udájů uvedena, jakékoliv GPS souřadnice jsou pouze přibližné.*

## 🚀 Jak kód spustit
1. Ujistěte se, že máte nainstalovaný Python 3.x.
2. Nainstalujte potřebné knihovny:
   ```bash
   pip install pandas matplotlib numpy folium
   ```
   
## 🤖 Prohlášení o využití AI 
Hlavním osobním vkladem v tomto projektu byl návrh a stavba hardwarových měřicích stanic, sběr dat v terénu (včetně řešení problémů s počasím) a prvotní čištění dat.
Modely umělé inteligence (LLM) byly využity jako asistenti při psaní částí Python kódu – konkrétně při generování interaktivní webové mapy (knihovna Folium) a při ladění estetiky grafů v knihovně Matplotlib. AI mi pomohla data lépe vizualizovat, ale veškerá naměřená data, metodika a závěry jsou výhradně výsledkem mého vlastního terénního výzkumu.


---

# Urban Heat Island (UHI) Measurement – Moravská Třebová

This repository contains the data and source code for my final Geography thesis (2025/2026), which focuses on measuring temperature differences between urban areas and the surrounding rural landscape. 

The goal of the project was to verify the existence of the Urban Heat Island (UHI) effect in a smaller city environment (Moravská Třebová). 

## 🛠️ Project and Hardware Overview
For the purposes of this research, I constructed 5 custom weather stations:
* **Microcontroller:** ESP32
* **Sensor:** Digital temperature sensor DS18B20
* **Housing:** 3D-printed enclosure, battery-powered.

The stations were deployed across 5 different environments (city center, city park, city outskirts, rural landscape, forest) and collected data at hourly intervals for nearly 3 weeks.

*Exact measurement locations are omitted for privacy protection; any provided GPS coordinates are approximate only.*

## 🚀 How to Run the Code
1. Ensure you have Python 3.x installed.
2. Install the required libraries:
   ```bash
   pip install pandas matplotlib numpy folium
   ```
   
## 🤖 AI Disclosure
The primary contribution and personal effort in this project lay in designing and building the hardware measurement stations, collecting field data (including troubleshooting weather-related hardware issues), and initial data cleaning.
Artificial Intelligence (LLM) models were utilized as assistants for writing portions of the Python code—specifically for generating the interactive web map (Folium library) and fine-tuning the aesthetics of the Matplotlib charts. While AI helped enhance the visualization, all measured data, methodology, and conclusions are strictly the result of my own independent field research.
