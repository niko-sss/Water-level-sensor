google.charts.load('current', { packages: ['corechart'], language: 'fi' });
google.charts.setOnLoadCallback(loadAndDraw);

let RANGE_DAYS = 1;
let LAST_MEASUREMENT_TEXT = '';

let captchaOk = false;
let captchaWidgetId = null; // widget id after explicit render

// Called by Google reCAPTCHA API when it loads (?onload=initCaptcha)
window.initCaptcha = function () {
    const container = document.getElementById('recaptcha_container');
    if (!container || !window.grecaptcha) return;

    // Render and keep widget id
    captchaWidgetId = grecaptcha.render(container, {
        sitekey: 'YourSiteKey', //Add your sitekey
        callback: onCaptchaSuccess,
        'expired-callback': onCaptchaExpired
    });
};

window.onCaptchaSuccess = function () {
    captchaOk = true;
    const btn = document.getElementById('send_discord');
    if (btn) btn.disabled = false;
};

window.onCaptchaExpired = function () {
    captchaOk = false;
    const btn = document.getElementById('send_discord');
    if (btn) btn.disabled = true;
};

function toggleRange() {
    RANGE_DAYS = (RANGE_DAYS === 1) ? 30 : 1;
    updateToolbarText();
    loadAndDraw();
}

function updateToolbarText() {
    const titleEl = document.getElementById('chart_title_text');
    const linkEl = document.getElementById('range_toggle');
    if (titleEl) {
        titleEl.textContent = (RANGE_DAYS === 1)
            ? 'Lämpötila ja kosteusdata viimeisen vuorokauden ajalta'
            : 'Lämpötila ja kosteusdata viimeisen 30 päivän ajalta';
    }
    if (linkEl) {
        linkEl.textContent = (RANGE_DAYS === 1)
            ? 'Katso tiedot 30pv ajalta →'
            : 'Katso tiedot 24h ajalta →';
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const btn = document.getElementById('send_discord');
    if (!btn) return;
    btn.addEventListener('click', async () => {
        const input = document.getElementById('webhook_url');
        const statusEl = document.getElementById('send_status');
        if (!input || !statusEl) return;

        // read token from the explicitly rendered widget
        const token = (window.grecaptcha && captchaWidgetId !== null)
            ? grecaptcha.getResponse(captchaWidgetId)
            : '';
        if (!captchaOk || !token) {
            statusEl.textContent = 'Suorita reCAPTCHA-vahvistus ensin.';
            return;
        }

        const webhookUrl = (input.value || '').trim();
        if (!webhookUrl) {
            statusEl.textContent = 'Anna webhook-osoite.';
            return;
        }
        if (!webhookUrl.startsWith('https://discord.com/api/webhooks/')) {
            statusEl.textContent = 'Virheellinen Discord webhook -osoite.';
            return;
        }
        if (!LAST_MEASUREMENT_TEXT) {
            statusEl.textContent = 'Ei mittaustietoja lähetettäväksi.';
            return;
        }

        statusEl.textContent = 'Lähetetään...';
        try {
            const resp = await fetch(webhookUrl, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ content: LAST_MEASUREMENT_TEXT })
            });
            if (!resp.ok) {
                const t = await resp.text().catch(() => '');
                statusEl.textContent = `Discord virhe: ${resp.status}. ${t.slice(0, 120)}`;
            } else {
                statusEl.textContent = 'OK: Viesti lähetetty Discordiin.';
                // reset captcha after success
                if (window.grecaptcha && captchaWidgetId !== null) {
                    grecaptcha.reset(captchaWidgetId);
                }
                onCaptchaExpired();
            }
        } catch (e) {
            statusEl.textContent = 'Verkkovirhe (voi olla CORS).';
            console.error(e);
        }
    });

    loadPumpStatus();

});

function loadAndDraw() {
    updateToolbarText();

    const RESULTS = (RANGE_DAYS > 1) ? 5000 : 150;
    const URL = `YourApiKey`;

    fetch(URL)
        .then(response => response.json())
        .then(data => {
            const feeds = data.feeds;
            const temperatures = feeds.map(feed => ({
                time: feed.created_at,
                temperature: parseFloat(feed.field1),
                humidity: parseFloat(feed.field2),
                waterLevel: parseFloat(feed.field3)
            }));

            const now = new Date();
            const from = new Date(now.getTime() - RANGE_DAYS * 24 * 60 * 60 * 1000);

            let latestMeasurement = null;
            let latestTime = null;
            let earliestTime = null;

            const dataTable = new google.visualization.DataTable();
            dataTable.addColumn('datetime', 'Kellonaika');
            dataTable.addColumn('number', 'Lämpötila');
            dataTable.addColumn('number', 'Kosteus');
            dataTable.addColumn('number', 'Vedenkorkeus');

            temperatures.forEach(item => {
                const date = new Date(item.time);
                if (
                    !isNaN(date.getTime()) &&
                    !isNaN(item.temperature) &&
                    !isNaN(item.humidity) &&
                    !isNaN(item.waterLevel)&&
                    date >= from && date <= now
                ) {
                    dataTable.addRow([date, item.temperature, item.humidity, item.waterLevel]);

                    if (!earliestTime || date < earliestTime) {
                        earliestTime = date;
                    }
                    if (!latestTime || date > latestTime) {
                        latestTime = date;
                        latestMeasurement = { date, temperature: item.temperature, humidity: item.humidity, waterLevel: item.waterLevel};
                    }
                }
            });

            // latest line for banner + Discord message
            if (latestMeasurement) {
                const hh = String(latestMeasurement.date.getHours()).padStart(2, '0');
                const mm = String(latestMeasurement.date.getMinutes()).padStart(2, '0');
                const textLine =
                    `Lämpötila tällä hetkellä: ${Math.round(latestMeasurement.temperature)} °C, ` +
                    `Kosteus: ${Math.round(latestMeasurement.humidity)} % (klo ${hh}:${mm})` +
                    `,Vedenkorkeus: ${Math.round(latestMeasurement.waterLevel)} %.`;
                const box = document.getElementById('temp_and_hum_now');
                if (box) box.textContent = textLine;
                LAST_MEASUREMENT_TEXT = textLine;
            } else {
                LAST_MEASUREMENT_TEXT = '';
            }

            // start axis at earliest available point if data < selected range
            const effectiveFrom = earliestTime ? new Date(Math.max(earliestTime, from)) : from;

            const ticks = (RANGE_DAYS === 1)
                ? buildHourlyTicks(effectiveFrom, now)
                : buildDailyTicks(effectiveFrom, now);

            const options = {
                fontName: 'Poppins',
                width: 1500,
                height: 800,
                legend: {
                    position: 'bottom',
                    textStyle: { fontName: 'Poppins', fontSize: 16, bold: true, color: '#0f172a' }
                },
                hAxis: {
                    title: 'Kellonaika',
                    format: (RANGE_DAYS === 1) ? 'HH:mm' : 'dd.MM.',
                    ticks: ticks,
                    viewWindowMode: 'explicit',
                    viewWindow: { min: effectiveFrom, max: now },
                    titleTextStyle: { fontName: 'Poppins', fontSize: 12, bold: true }
                },
                vAxis: {
                    titleTextStyle: { fontName: 'Poppins', fontSize: 12, bold: true }
                },
                chartArea: {
                    left: 50,
                    top: 10,
                    width: '85%',
                    height: '75%'
                }
            };

            const tempformat = new google.visualization.NumberFormat({ suffix: ' °C', fractionDigits: 0 });
            const humformat  = new google.visualization.NumberFormat({ suffix: ' %', fractionDigits: 0 });
            const waterformat  = new google.visualization.NumberFormat({ suffix: ' %', fractionDigits: 0 });
            waterformat.format(dataTable, 3);
            tempformat.format(dataTable, 1);
            humformat.format(dataTable, 2);

            const chart = new google.visualization.LineChart(document.getElementById('chart_div'));
            chart.draw(dataTable, options);
        })
        .catch(error => {
            console.error('Error fetching data:', error);
            const output = document.getElementById('output');
            if (output) output.textContent = 'Error loading data';
        });
}

function buildHourlyTicks(minDate, maxDate) {
    const ticks = [];
    const d = new Date(minDate);
    d.setMinutes(0, 0, 0);
    if (d < minDate) d.setHours(d.getHours() + 1);
    while (d <= maxDate) {
        ticks.push(new Date(d));
        d.setHours(d.getHours() + 1);
    }
    return ticks;
}

function buildDailyTicks(minDate, maxDate) {
    const ticks = [];
    const d = new Date(minDate);
    d.setHours(0, 0, 0, 0);
    if (d < minDate) d.setDate(d.getDate() + 1);
    while (d <= maxDate) {
        ticks.push(new Date(d));
        d.setDate(d.getDate() + 1);
    }
    return ticks;
}

async function setPump(state) {
    const statusEl = document.getElementById('pump_status');
    if (!statusEl) return;

    statusEl.textContent = 'Päivitetään...';

    try {
        const resp = await fetch('pump_control.php?state=' + encodeURIComponent(state));
        const text = (await resp.text()).trim();

        if (text === 'on') {
            statusEl.textContent = 'Pumpun tila: PÄÄLLÄ';
        } else if (text === 'off') {
            statusEl.textContent = 'Pumpun tila: POIS';
        } else {
            statusEl.textContent = 'Pumpun tila: tuntematon (' + text + ')';
        }
    } catch (err) {
        console.error(err);
        statusEl.textContent = 'Virhe yhteydessä palvelimeen.';
    }
}

async function loadPumpStatus() {
    const statusEl = document.getElementById('pump_status');
    if (!statusEl) return;

    try {
        const resp = await fetch('pump_control.php?get=1');
        const text = (await resp.text()).trim();

        statusEl.textContent = 'Pumpun tila: ' + (text === 'on' ? 'PÄÄLLÄ' : 'POIS');
    } catch (err) {
        console.error(err);
        statusEl.textContent = 'Pumpun tila: ei saatavilla';
    }
}
