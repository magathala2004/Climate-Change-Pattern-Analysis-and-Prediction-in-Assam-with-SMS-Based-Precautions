// ------- GLOBALS -------
let currentForecastRows = null;
let currentDistrictName = null;
let currentSlide = 0;

// Helper: choose emoji based on rain probability
function getWeatherIcon(rainProb, rainMm) {
  if (rainProb >= 80 || rainMm >= 50) return "⛈️";
  if (rainProb >= 50 || rainMm >= 20) return "🌧️";
  if (rainProb >= 20 || rainMm >= 5)  return "🌦️";
  return "☀️";
}

// Helper: classify rain text + color class
function getRainClass(rainProb) {
  if (rainProb >= 80) return { text: "Very High", cls: "rain-high" };
  if (rainProb >= 50) return { text: "High", cls: "rain-med" };
  if (rainProb >= 20) return { text: "Moderate", cls: "rain-med" };
  return { text: "Low", cls: "rain-low" };
}

// Helper: short day name from date string
function getDayName(dateStr) {
  const d = new Date(dateStr);
  return d.toLocaleDateString("en-IN", { weekday: "short" });
}

// Helper: pretty date
function prettyDate(dateStr) {
  const d = new Date(dateStr);
  return d.toLocaleDateString("en-IN", { day: "numeric", month: "short" });
}

// Focus the district selector when map clicked
function focusDistrictSelect() {
  const sel = document.getElementById("districtSelect");
  if (!sel) return;
  sel.scrollIntoView({ behavior: "smooth", block: "center" });
  sel.classList.add("highlight-select");
  setTimeout(() => sel.classList.remove("highlight-select"), 1500);
}

// MAIN: load forecast for selected district
async function loadForecast() {
  const district = document.getElementById("districtSelect").value;
  const subtitle = document.getElementById("forecastSubtitle");
  const content = document.getElementById("forecastContent");
  const alertStatus = document.getElementById("alertStatus");

  content.innerHTML = "";
  alertStatus.innerHTML = "";
  currentForecastRows = null;
  currentDistrictName = null;

  if (!district) {
    subtitle.textContent = "Please choose a district.";
    content.innerHTML = `<p class="muted">No forecast loaded. Select a district above.</p>`;
    return;
  }

  subtitle.textContent = `Loading forecast for ${district}...`;
  content.innerHTML = `<span class="loader"></span> <span class="muted">Fetching 7-day forecast...</span>`;

  try {
    const res = await fetch(`/api/forecast?district=${encodeURIComponent(district)}`);
    const data = await res.json();

    if (!res.ok) {
      subtitle.textContent = "Unable to load forecast.";
      content.innerHTML = `<p class="error">${data.error || "Failed to load forecast data."}</p>`;
      return;
    }

    const rows = data.forecast;
    if (!rows || rows.length === 0) {
      subtitle.textContent = `No forecast data found for ${district}.`;
      content.innerHTML = `<p class="muted">No records available.</p>`;
      return;
    }

    currentForecastRows = rows;
    currentDistrictName = district;

    subtitle.textContent = `${district} · Next 7 days`;

    const today = rows[0];
    const icon = getWeatherIcon(today.rain_possibility_percent, today.pred_rain_mm);
    const rainInfo = getRainClass(today.rain_possibility_percent);

    const avgRain = rows.reduce((acc, r) => acc + r.rain_possibility_percent, 0) / rows.length;
    const avgHum  = rows.reduce((acc, r) => acc + r.pred_humidity_avg_pct, 0) / rows.length;
    const maxTmax = Math.max(...rows.map(r => r.pred_tmax_c));

    let html = "";

    // Current summary section
    html += `
      <div class="current-summary">
        <div class="current-icon">${icon}</div>
        <div class="current-main">
          <h3>${prettyDate(today.date)} · ${getDayName(today.date)}</h3>
          <p>Rain: ${today.rain_possibility_percent.toFixed(1)}% · ${today.pred_rain_mm.toFixed(1)} mm
             · Temp: ${today.pred_tmax_c.toFixed(1)}° / ${today.pred_tmin_c.toFixed(1)}°</p>
          <p>Humidity avg: ${today.pred_humidity_avg_pct.toFixed(1)}%</p>
        </div>
        <div class="current-extra">
          <span class="pill pill-rain">
            💧 ${rainInfo.text} rain risk
          </span><br>
          <span class="pill pill-temp" style="margin-top:4px;">
            🔥 Tmax up to ${maxTmax.toFixed(1)}°C next 7 days
          </span>
        </div>
      </div>
    `;

    // 7-day cards strip
    html += `<div class="days-strip">`;
    for (const r of rows) {
      const dname = getDayName(r.date);
      const dpretty = prettyDate(r.date);
      const ic = getWeatherIcon(r.rain_possibility_percent, r.pred_rain_mm);
      const rc = getRainClass(r.rain_possibility_percent);

      html += `
        <div class="day-card">
          <div class="day-top">
            <div class="day-name">${dname}</div>
            <div class="day-icon">${ic}</div>
          </div>
          <div class="mini-date">${dpretty}</div>
          <div class="day-rain ${rc.cls}">
            ${r.rain_possibility_percent.toFixed(0)}% · ${r.pred_rain_mm.toFixed(1)} mm
          </div>
          <div class="mini-temp">
            🌡️ ${r.pred_tmax_c.toFixed(1)}° / ${r.pred_tmin_c.toFixed(1)}°
          </div>
          <div class="mini-hum">
            💧 Hum avg: ${r.pred_humidity_avg_pct.toFixed(0)}%
          </div>
        </div>
      `;
    }
    html += `</div>`;

    html += `
      <p class="muted">
        7-day avg rain probability: ${avgRain.toFixed(1)}% ·
        avg humidity: ${avgHum.toFixed(1)}% ·
        max temperature: ${maxTmax.toFixed(1)}°C
      </p>
    `;

    content.innerHTML = html;

    alertStatus.innerHTML = `
      <div class="badge">
        ✅ Forecast loaded for <strong>${district}</strong>
      </div>
    `;

  } catch (err) {
    console.error(err);
    subtitle.textContent = "Error while loading forecast.";
    content.innerHTML = `<p class="error">Something went wrong while fetching forecast.</p>`;
  }
}

// ------- Slider logic -------
function initSlider() {
  const slides = document.querySelectorAll(".slide");
  const dotsContainer = document.getElementById("sliderDots");
  dotsContainer.innerHTML = "";

  slides.forEach((_, idx) => {
    const dot = document.createElement("button");
    dot.className = "slider-dot" + (idx === 0 ? " active" : "");
    dot.addEventListener("click", (e) => {
      e.stopPropagation();
      showSlide(idx);
    });
    dotsContainer.appendChild(dot);
  });

  currentSlide = 0;
  setInterval(() => {
    nextSlide();
  }, 7000);
}

function showSlide(index) {
  const slides = document.querySelectorAll(".slide");
  const dots = document.querySelectorAll(".slider-dot");
  if (!slides.length) return;

  currentSlide = (index + slides.length) % slides.length;
  slides.forEach((s, i) => {
    s.classList.toggle("active", i === currentSlide);
  });
  dots.forEach((d, i) => {
    d.classList.toggle("active", i === currentSlide);
  });
}

function nextSlide(ev) {
  if (ev) ev.stopPropagation();
  showSlide(currentSlide + 1);
}

function prevSlide(ev) {
  if (ev) ev.stopPropagation();
  showSlide(currentSlide - 1);
}

// ------- Chat / interactive Q&A -------
function addChatBubble(sender, text) {
  const win = document.getElementById("chatWindow");
  if (!win) return;
  const div = document.createElement("div");
  div.className = "chat-bubble " + (sender === "user" ? "user" : "bot");
  div.textContent = text;
  win.appendChild(div);
  win.scrollTop = win.scrollHeight;
}

function handleQuestion(type) {
  if (!currentForecastRows || !currentForecastRows.length) {
    addChatBubble("bot", "Please load a district forecast first using the top selector.");
    return;
  }

  let userQ = "";
  let answer = "";

  const rows = currentForecastRows;
  const district = currentDistrictName || "this district";

  if (type === "rain") {
    userQ = "Will it rain heavily this week?";
    const heavyDays = rows.filter(r => r.rain_possibility_percent >= 60);
    const maxProb = Math.max(...rows.map(r => r.rain_possibility_percent));
    const maxMm = Math.max(...rows.map(r => r.pred_rain_mm));
    answer =
      `In ${district}, ${heavyDays.length} out of 7 days have rain probability ≥ 60%. ` +
      `The highest rain chance is ${maxProb.toFixed(1)}% with up to ${maxMm.toFixed(1)} mm rainfall.`;
  } else if (type === "heat") {
    userQ = "Will temperature cross my limit?";
    const maxT = Math.max(...rows.map(r => r.pred_tmax_c));
    answer =
      `The maximum forecast Tmax in ${district} over the next 7 days is ` +
      `${maxT.toFixed(1)}°C. Days with Tmax > 35°C: ` +
      `${rows.filter(r => r.pred_tmax_c > 35).length}.`;
  } else if (type === "humidity") {
    userQ = "How humid will it feel?";
    const avgHum = rows.reduce((a, r) => a + r.pred_humidity_avg_pct, 0) / rows.length;
    const highHumDays = rows.filter(r => r.pred_humidity_avg_pct >= 80).length;
    answer =
      `Average humidity in ${district} is about ${avgHum.toFixed(1)}%. ` +
      `${highHumDays} out of 7 days have humidity ≥ 80%, so it will feel quite sticky on those days.`;
  } else if (type === "summary") {
    userQ = "Give me a short summary.";
    const avgRain = rows.reduce((a, r) => a + r.rain_possibility_percent, 0) / rows.length;
    const avgHum = rows.reduce((a, r) => a + r.pred_humidity_avg_pct, 0) / rows.length;
    const maxT = Math.max(...rows.map(r => r.pred_tmax_c));
    answer =
      `Summary for ${district}: average rain chance ~${avgRain.toFixed(1)}%, ` +
      `average humidity ~${avgHum.toFixed(1)}%, and Tmax up to ${maxT.toFixed(1)}°C over the next 7 days.`;
  }

  if (userQ) addChatBubble("user", userQ);
  if (answer) addChatBubble("bot", answer);
}

// ------- Registration / alerts -------
async function registerAlert() {
  const email = document.getElementById("emailInput").value.trim();
  const district = document.getElementById("districtRegSelect").value;
  const rainThreshold = parseFloat(document.getElementById("thresholdRain").value);
  const tmaxThreshold = parseFloat(document.getElementById("thresholdTmax").value);
  const humThreshold  = parseFloat(document.getElementById("thresholdHum").value);
  const msgDiv = document.getElementById("regMessage");

  msgDiv.innerHTML = "";

  if (!email || !district || isNaN(rainThreshold) || isNaN(tmaxThreshold) || isNaN(humThreshold)) {
    msgDiv.innerHTML = `<span class="error">Please fill all fields correctly.</span>`;
    return;
  }

  msgDiv.innerHTML = `<span class="loader"></span> <span class="muted">Registering...</span>`;

  try {
    const res = await fetch("/api/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email,
        district,
        rain_threshold: rainThreshold,
        tmax_threshold: tmaxThreshold,
        humidity_threshold: humThreshold
      })
    });

    const data = await res.json();

    if (!res.ok) {
      msgDiv.innerHTML = `<span class="error">${data.error || "Registration failed."}</span>`;
      return;
    }

    msgDiv.innerHTML = `<span class="success">✅ ${data.message}. Alerts will use your thresholds.</span>`;
  } catch (err) {
    console.error(err);
    msgDiv.innerHTML = `<span class="error">Error during registration. Please try again.</span>`;
  }
}

// Initialise slider after DOM loaded
document.addEventListener("DOMContentLoaded", () => {
  initSlider();
});
