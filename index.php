<!DOCTYPE html>
<html lang="fi">
    <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width,initial-scale=1" />
        <title>Vedenkorkeusmittari + DHT11</title>

        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
        <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@600;700&display=swap" rel="stylesheet" />

        <link rel="stylesheet" href="googlechart_syle.css" />

        <script src="https://www.gstatic.com/charts/loader.js"></script>

        <!-- Explicit render for reCAPTCHA v2 -->
        <script src="https://www.google.com/recaptcha/api.js?onload=initCaptcha&render=explicit" async defer></script>


    </head>

    <body>
        <h1 class="page-title">Lämpötila, kosteus ja Vedenkorkeusmittari <br />Pico W + DHT11 + B10K + ThingSpeak</h1>
        <p class="page-sub">Tiedot päivittyvät 10 minuutin välein (time.sleep(600))</p>

        <div id="temp_and_hum_now"></div>

        <div class="webhook-box">
            <label for="webhook_url">Viesti Discordiin Webhook</label>
            <div class="webhook-row">
                <input type="url" id="webhook_url" placeholder="https://discord.com/api/webhooks/...(Laita tähän oman palvelimesi webhook-osoite)" />
            </div>
        </div>

        <div class="webhook-box">
            <div class="captcha-row">
                <div id="recaptcha_container"></div>
                <span class="captcha-hint">Suorita vahvistus ennen viestin lähetystä</span>
            </div>

            <div class="webhook-row">
                <button id="send_discord" disabled>Lähetä viimeisin mittaus →</button>
            </div>

            <div id="send_status"></div>
        </div>

        <div class="content">
            <div class="chart-toolbar">
                <span id="chart_title_text">Vedenkorkeus, lämpötila ja kosteusdata viimeisen vuorokauden ajalta</span>
                <a href="#" id="range_toggle" onclick="toggleRange(); return false;">Näytä tiedot 30 päivää →</a>
            </div>

            <!-- PUMP CONTROL  -->
            <div class="pump-inline">
                <button class="pump-btn pump-on" onclick="setPump('on')">Pumppu päälle</button>
                <button class="pump-btn pump-off" onclick="setPump('off')">Pumppu pois</button>

                <span id="pump_status">Pumpun tila: tuntematon</span>
            </div>

            <div id="chart_div"></div>
            <div id="output"></div>
        </div>

        <script src="googlechart.js"></script>

        <!-- BACKEND PUMP CONTROL JS
        <script>
            function setPump(state) {
                fetch("pump_control.php?set=" + encodeURIComponent(state))
                    .then(r => r.text())
                    .then(text => {
                        const el = document.getElementById("pump_status");
                        if (!el) return;

                        if (text.trim() === "on") {
                            el.textContent = "Pumpun tila: PÄÄLLÄ";
                        } else if (text.trim() === "off") {
                            el.textContent = "Pumpun tila: POIS PÄÄLTÄ";
                        } else {
                            el.textContent = "Pumpun tila: tuntematon (" + text + ")";
                        }
                    })
                    .catch(() => {
                        const el = document.getElementById("pump_status");
                        if (el) el.textContent = "Pumpun tila: VIRHE (backend)";
                    });
            }

            function refreshPump() {
                fetch("pump_control.php?get=1")
                    .then(r => r.text())
                    .then(text => {
                        const el = document.getElementById("pump_status");
                        if (!el) return;

                        if (text.trim() === "on") {
                            el.textContent = "Pumpun tila: PÄÄLLÄ";
                        } else {
                            el.textContent = "Pumpun tila: POIS PÄÄLTÄ";
                        }
                    });
            }

            document.addEventListener("DOMContentLoaded", () => {
                refreshPump();
                setInterval(refreshPump, 10000);
            });
        </script> -->

        <div id="copyright">Lab Team 2025</div>
    </body>
</html>
