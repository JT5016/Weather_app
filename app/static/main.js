// app/static/main.js

/**
 * Collapse the 3-hourly forecast into one item per day,
 * preferring the "12:00:00" slot if available.
 */
function renderDailyForecast(data) {
  const raw = data.list || [];
  const byDate = {};

  raw.forEach(item => {
    const [day, time] = item.dt_txt.split(" ");
    if (!byDate[day] || time === "12:00:00") {
      byDate[day] = item;
    }
  });

  return Object.keys(byDate)
    .sort()
    .map(day => {
      const itm = byDate[day];
      return `
        <div class="forecast-card-clean">
          <div class="forecast-info">
            <h3 class="forecast-date">${day}</h3>
            <img
              src="http://openweathermap.org/img/wn/${itm.weather[0].icon}@2x.png"
              alt="${itm.weather[0].description}"
              class="forecast-icon"
            />
            <p class="temp">${itm.main.temp}°F</p>
            <p class="humidity">Humidity: ${itm.main.humidity}%</p>
            <p class="desc">${itm.weather[0].description}</p>
          </div>
        </div>`;
    })
    .join("");
}

document.addEventListener("DOMContentLoaded", () => {

  // — Weather lookup form (weather.html) —
  const form   = document.getElementById("weatherForm");
  const result = document.getElementById("weatherResult");
  if (form) {
    form.addEventListener("submit", async e => {
      e.preventDefault();
      result.innerHTML = `<p class="loading">Loading…</p>`;

      const payload = {
        location:   form.location.value.trim(),
        start_date: form.start_date.value || null,
        end_date:   form.end_date.value   || null,
      };

      try {
        const res    = await fetch("/weather", {
          method:  "POST",
          headers: { "Content-Type": "application/json" },
          body:    JSON.stringify(payload)
        });
        if (!res.ok) throw new Error(res.statusText);

        const record = await res.json();
        const data   = JSON.parse(record.response);

        // If forecast, render strip; else render current
        if (data.list) {
          result.innerHTML = `<div class="forecast-container">${renderDailyForecast(data)}</div>`;
        } else {
          result.innerHTML = `
            <div class="current-card">
              <img
                src="http://openweathermap.org/img/wn/${data.weather[0].icon}@2x.png"
                alt="${data.weather[0].description}"
              />
              <div class="current-info">
                <h3>${data.name}</h3>
                <p class="temp">${data.main.temp}°F</p>
                <p class="humidity">Humidity: ${data.main.humidity}%</p>
                <p class="desc">${data.weather[0].description}</p>
              </div>
            </div>`;
        }
      } catch (err) {
        result.innerHTML = `<p class="error">Error: ${err.message}</p>`;
      }
    });
  }

  // — Forecast & Sun buttons on home.html —
  const home = document.querySelector(".home-container");
  if (!home) return;

  home.addEventListener("click", async e => {
    // Forecast toggle
    const fbtn = e.target.closest(".forecast-btn");
    if (fbtn) {
      const card = fbtn.closest(".saved-weather-card");
      const fc   = card.querySelector(".forecast-container");

      // Remember if this card was already open
      const wasOpen = card.classList.contains("show-forecast");

      // Close all forecast panels
      document
        .querySelectorAll(".saved-weather-card.show-forecast")
        .forEach(c => {
          c.classList.remove("show-forecast");
          c.querySelector(".forecast-container").innerHTML = '';
        });

      // If it was closed before, open & fetch
      if (!wasOpen) {
        card.classList.add("show-forecast");
        try {
          const res        = await fetch(`/weather/${card.dataset.id}/forecast`);
          if (!res.ok) throw new Error(res.statusText);
          const { response } = await res.json();
          fc.innerHTML      = renderDailyForecast(JSON.parse(response));
        } catch {
          fc.innerHTML      = `<p class="error">Forecast load failed</p>`;
        }
      }
      return;
    }

    // Sun toggle
    const sbtn = e.target.closest(".sun-btn");
    if (sbtn) {
      const card = sbtn.closest(".saved-weather-card");
      const sn   = card.querySelector(".sun-container");

      // Remember if this card was already open
      const wasOpen = card.classList.contains("show-sun");

      // Close all sun panels
      document
        .querySelectorAll(".saved-weather-card.show-sun")
        .forEach(c => {
          c.classList.remove("show-sun");
          c.querySelector(".sun-container").innerHTML = '';
        });

      // If it was closed before, open & fetch
      if (!wasOpen) {
        card.classList.add("show-sun");
        try {
          const res                 = await fetch(`/weather/${card.dataset.id}/sun`);
          if (!res.ok) throw new Error(res.statusText);
          const { sunrise, sunset } = await res.json();
          sn.innerHTML              = `
            <p>🌅 Sunrise: ${new Date(sunrise).toLocaleTimeString()}</p>
            <p>🌇 Sunset:  ${new Date(sunset).toLocaleTimeString()}</p>`;
        } catch {
          sn.innerHTML              = `<p class="error">Sun times load failed</p>`;
        }
      }
      return;
    }
  });

});
