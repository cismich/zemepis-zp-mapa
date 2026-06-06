// Dynamická data injektovaná z Pythonu (placeholders)
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
  csvContent = "\uFEFF" + "Cas mereni,Teplota - " + sensorName + " (C)\r\n";
  
  let count = 0;
  rows.forEach(row => {
    if (row.style.display !== "none") {
      const cells = row.querySelectorAll("td");
      if (cells.length >= 2) {
        const time = cells[0].textContent;
        const temp = cells[1].textContent.replace(" °C", "").trim();
        csvContent += time + "," + temp + "\r\n";
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

/* ---------------------------------------------------------
   POMOCNÉ JS FUNKCE PRO MAKSIMÁLNÍ POPUP OKNO (MODAL)
   --------------------------------------------------------- */
// Globální proměnné pro správu grafu a barev
let modalChartInstance = null;
const sensorColors = {
  "Centrum města": "#e31a1c",
  "Okraj města": "#ff7f00",
  "Městský park": "#fdbf6f",
  "Venkovská krajina": "#33a02c",
  "Lesní krajina": "#1f78b4"
};

function openModal(title, htmlContent) {
  const modal = document.getElementById("global-modal");
  const titleEl = document.getElementById("modal-title");
  const bodyEl = document.getElementById("modal-body-content");
  
  if (!modal || !titleEl || !bodyEl) return;
  
  titleEl.textContent = title;
  // Pokud je předán obsah, přepíšeme modal. Pokud ne, zachováme předpřipravenou HTML kostru.
  if (htmlContent) {
    bodyEl.innerHTML = htmlContent;
  }
  
  // Detekce, zda je aktivní tmavý režim hlavního panelu, a synchronizace motivu
  const panel = document.getElementById("right-overlay");
  if (panel && panel.classList.contains("dark-theme")) {
    modal.classList.add("dark-theme");
  } else {
    modal.classList.remove("dark-theme");
  }
  
  modal.classList.add("open");
}

function closeModal(event) {
  // Pokud klikneme mimo okno na pozadí, nebo klikneme na křížek
  if (event && event.target !== event.currentTarget) return;
  
  const modal = document.getElementById("global-modal");
  if (modal) {
    modal.classList.remove("open");
  }
}

// OTEVŘENÍ PLNÉHO ROZHRANÍ ANALÝZY S GRAFEM
function openFullAnalysis() {
  // Otevře modal s naším předpřipraveným layoutem
  openModal("Podrobná teplotní analýza a srovnání");

  // 1. Zjistíme dostupné časové rozmezí z dat
  const times = Object.keys(rawSensorData).sort();
  if (times.length > 0) {
    const minTime = times[0];
    const maxTime = times[times.length - 1];
    
    // Získáme pouze datum (YYYY-MM-DD)
    const minDateStr = minTime.split(" ")[0];
    const maxDateStr = maxTime.split(" ")[0];

    const inputStart = document.getElementById("modal-date-start");
    const inputEnd = document.getElementById("modal-date-end");

    if (inputStart && inputEnd) {
      inputStart.min = minDateStr;
      inputStart.max = maxDateStr;
      inputStart.value = minDateStr;

      inputEnd.min = minDateStr;
      inputEnd.max = maxDateStr;
      inputEnd.value = maxDateStr;
    }
  }

  // 2. Dynamicky vygenerujeme checkboxy pro senzory
  const checkboxContainer = document.getElementById("modal-sensor-checkboxes");
  if (checkboxContainer) {
    checkboxContainer.innerHTML = "";
    
    // Použijeme senzory přítomné v datech (klíče prvního záznamu)
    const firstTime = Object.keys(rawSensorData)[0];
    if (firstTime) {
      const sensors = Object.keys(rawSensorData[firstTime]);
      sensors.forEach(sensor => {
        const color = sensorColors[sensor] || "#64748b";
        const div = document.createElement("div");
        div.className = "checkbox-item";
        div.style.setProperty("--sensor-color", color);
        div.innerHTML = `
          <input type="checkbox" id="chk-${sensor.replace(/\s+/g, '')}" value="${sensor}" checked onchange="updateModalChart()">
          <span style="--sensor-color: ${color};">${sensor}</span>
        `;
        checkboxContainer.appendChild(div);
      });
    }
  }

  // 3. Vykreslíme výchozí graf
  setTimeout(() => {
    updateModalChart();
  }, 100);
}

// AKTUALIZACE A VYKERESLENÍ GRAFU
function updateModalChart() {
  const startVal = document.getElementById("modal-date-start").value;
  const endVal = document.getElementById("modal-date-end").value;
  const warningEl = document.getElementById("range-warning");

  if (!startVal || !endVal) return;

  // Kontrola rozsahu
  if (startVal > endVal) {
    if (warningEl) {
      warningEl.textContent = "Chyba: Datum od musí být před datem do.";
      warningEl.style.display = "block";
    }
    return;
  } else {
    if (warningEl) warningEl.style.display = "none";
  }

  // Filtrujeme časy spadající do vybraného rozmezí
  const filteredTimes = Object.keys(rawSensorData).sort().filter(time => {
    const date = time.split(" ")[0];
    return date >= startVal && date <= endVal;
  });

  // Zjistíme, které lokality jsou vybrané
  const checkedBoxes = Array.from(document.querySelectorAll("#modal-sensor-checkboxes input:checked"));
  const activeSensors = checkedBoxes.map(cb => cb.value);

  // Připravíme datové sady pro Chart.js
  const datasets = activeSensors.map(sensor => {
    const color = sensorColors[sensor] || "#64748b";
    const dataPoints = filteredTimes.map(time => rawSensorData[time][sensor]);

    return {
      label: sensor,
      data: dataPoints,
      borderColor: color,
      backgroundColor: color + "1a", // 10% průhlednost pro výplň
      borderWidth: 2,
      tension: 0.15,
      pointRadius: 0,
      pointHoverRadius: 5,
      fill: false
    };
  });

  // Získání plátna canvasu
  const canvas = document.getElementById("modal-chart");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");

  // Pokud graf již existuje, zničíme jej před překreslením
  if (modalChartInstance) {
    modalChartInstance.destroy();
  }

  // Nastavení barev mřížky a textu podle motivu panelu
  const panel = document.getElementById("right-overlay");
  const isDark = panel && panel.classList.contains("dark-theme");
  const gridColor = isDark ? "rgba(255, 255, 255, 0.08)" : "rgba(0, 0, 0, 0.05)";
  const textColor = isDark ? "#cbd5e1" : "#475569";

  modalChartInstance = new Chart(ctx, {
    type: 'line',
    data: {
      labels: filteredTimes,
      datasets: datasets
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: {
        mode: 'index',
        intersect: false
      },
      scales: {
        x: {
          grid: { color: gridColor },
          ticks: {
            color: textColor,
            maxTicksLimit: 12
          }
        },
        y: {
          grid: { color: gridColor },
          ticks: { color: textColor },
          title: {
            display: true,
            text: 'Teplota (°C)',
            color: textColor
          }
        }
      },
      plugins: {
        legend: {
          display: false // Vlastní checkboxy na levé straně zastoupí legendu
        },
        tooltip: {
          backgroundColor: isDark ? "rgba(15, 23, 42, 0.95)" : "rgba(255, 255, 255, 0.95)",
          titleColor: isDark ? "#ffffff" : "#0f172a",
          bodyColor: isDark ? "#cbd5e1" : "#334155",
          borderColor: isDark ? "rgba(255, 255, 255, 0.08)" : "rgba(0, 0, 0, 0.08)",
          borderWidth: 1,
          padding: 10
        }
      }
    }
  });
}

// Automatické načtení a dohledání Leaflet objektů po načtení stránky
window.addEventListener("load", () => {
  initLeafletAccess();
  loadSensorData();
});
