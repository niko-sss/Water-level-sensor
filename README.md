# Vedenkorkeusmittari – Pico W + DHT11 + potentiometri + ThingSpeak
---
### Tämä projekti on AT00BY06-3013 IoT:n ja sulautettujen järjestelmien soveltaminen -kurssin lopputehtävä, jossa aiemmin toteutettu vedenkorkeuden sekä lämpötila–/kosteusmittausjärjestelmä tuotteistetaan kokonaiseksi sovellukseksi.
---

<br>
<br>

### Järjestelmään kuuluu:
•	Laitteisto (Raspberry Pi Pico W)
•	Laitekoodi (MicroPython)
•	Backend (PHP)
•	Tietovarasto (Pilvipalvelu ThingSpeak +  tiedostopohjainen (txt))
•	Frontend (HTML + CSS + JavaScript + Google Charts)
Frontista voidaan sekä ohjata Picoon kytkettyä pumppua (Päälle / Pois Päältä) että visualisoida kerättyä anturidataa.

<br>

## 1. Järjestelmän arkkitehtuuri

<br>

### 1.1 Laitteisto (Raspberry Pi Pico W)
__Raspberry Pi Pico W lukee:__
•	vedenkorkeuden (potentiometri B10K → ADC)
•	lämpötilan (DHT11)
•	kosteuden (DHT11)

<br>

__Laite:__
1.	Kalibroi vedenkorkeuden (0 % / 100 %) käyttäjän ohjeiden mukaan.
2.	Näyttää arvot ILI9341-TFT-näytöllä (vedenkorkeus prosenteina, varoitus "Empty" / "Full", lämpötilan, kosteuden, wifi yhteyden statuksen, viimeisen lähetetyn datan ThingSpeakiin, laitteen uudelleen­kalibroinnin ohjeet).
3.	Yhdistää Wi-Fi-verkkoon.
4.	Lähettää mittaustiedot ThingSpeakiin 10 minuutin välein.
5.	Hakee pumpun tilan backendistä HTTP-pyynnöllä:
GET pump_control.php?get=1
6.	Ohjaa pumppua (rele / GPIO) ja Pico W:n sisäistä LEDiä pumpun tilan mukaan.
### 1.2 Backend (PHP)

<br>

__Backend koostuu tiedostoista:__
- index.php
    - Tehtävät:
        1. Kokoaa HTML:n kasaan
<br>
<br>

- pump_control.php
    - Tehtävät:
        1. Vastaa kutsuihin 
            - pump_control.php?state=on
            - pump_control.php?state=off
        2. Tallentaa pumpun tilan mariaDB-tietokantaan (sisältö: on tai off)
        3. Vastaa tilakyselyihin 
            - pump_control.php?get=1

<br>

### 1.3 Tietovarasto (ThingSpeak)
__ThingSpeak-kanava tallentaa:__
|Kenttä|Arvo|
|---|---|
field1|lämpötila (°C)
field2|kosteus (%)
field3|vedenkorkeus (%)

<br>

Frontend hakee datan JSON-rajapinnasta: https://api.thingspeak.com/channels/<channel_id>/feeds.json?api_key=<read_key>&results=... 

### 1.4 Frontend (HTML + JS)

<br>

__Frontend koostuu:__
•	`index.php`
•	`googlechart.js`
•	`googlechart_style.css`

<br> 

__Toiminnot:__
- Lataa viimeiset mittaukset ThingSpeakista.
- Piirtää Google Charts -linjakaavion (lämpötila, kosteus, vedenkorkeus).
- Näyttää viimeisimmän mittauksen tekstinä.
- reCAPTCHA-suojattu Discord-webhook viimeisimmän mittauksen lähettämiseksi käyttäjän Discord palvelimelle.
- Pumpun ohjaus:
    - "Pumppu päälle" → `state=on`
    - "Pumppu pois" → `state=off`
- Pumpun tila näytetään tekstinä ja päivittyy automaattisesti.
<br>

__Muotoilu:__
- `googlechart_style.css`
<br>

## 2. Käyttöönotto-ohje

<br>

### 2.1 ThingSpeak
1.	Luo uusi kanava, jossa 3 kenttää.
2.	Aseta API-avaimet main.py-tiedostoon.
3.	Kirjoita channel ID ja read key googlechart.js-tiedostoon.
### 2.2 Web-palvelin
1.	Siirrä web/-hakemiston tiedostot palvelimelle.
2.	Varmista, että PHP toimii.
3.	Alusta tietokanta.
    - `CREATE TABLE pump_status (
    id INT PRIMARY KEY,
    state ENUM('on','off') NOT NULL DEFAULT 'off',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    );`
    - `INSERT INTO pump_status (id, state) VALUES (1, 'off');`
### 2.3 Pico W
1.	Flashaa MicroPython.
2.	Kopioi main.py ja näytinkirjastot.
3.	Aseta:
a.	SSID `Pico/main.py`
b.	salasana `Pico/main.py`
c.	ThingSpeak API-key `googlechart.js`
d.	backendin osoite `pump_control.php`
4.	Käynnistä laite → sen pitäisi heti kalibroinnin jälkeen alkaa lähettää dataa.
<br>

## 3. Käyttöohje

<br>

### 3.1 Kalibrointi Pico W:ssä
•	Ensimmäisellä käynnistyksellä laite pyytää asettamaan varren ala- ja ylärajoille (vesiastian 0 % ja 100 % rajat)
•	Arvot tallentuvat calib.json-tiedostoon.
### 3.2 Normaalikäyttö
•	Mittaus → näyttöön → ThingSpeakiin 10 min välein.
•	Pumpun tila haetaan backendistä muutaman sekunnin välein.
### 3.3 Frontend
•	Kaavio näyttää viimeisen 24h / 30vrk datan.
•	Pumpun tila näkyy reaaliaikaisesti.
•	Painikkeilla ohjataan pumppua.
•	Discord-painikkeella voi lähettää viimeisimmän mittauksen suoraan käyttäjän Discord palvelimelle.
<br>
<br>

## 4. Testausraportti

<br>

### 4.1 Pico W
Testi|Kuvaus|Tulos
|---|---|---|
Wi-Fi-yhteys|Yhdistyy oikeilla tunnuksilla|OK
Kalibrointi|0 % ja 100 % tallentuvat|OK
ThingSpeak-lähetys|Lähettää 10 min välein|OK
Pumpun tila|Hakee pump_control.php?get=1|OK
Pumpun ohjaus|LED + pumppu vaihtaa tilaa|OK

### 4.2 Backend (PHP)
|Testi|Tulos|
|---|---|
get=1 palauttaa oikean tilan|OK
Virhetilanteet → palauttaa off jos tietokantaa ei löydy|OK

### 4.3 Frontend
Testi|Kuvaus|Tulos
|---|---|---|
Kaavio latautuu|Data näkyy ThingSpeakista|OK
Aikavälin vaihto 24h ↔ 30vrk|Kaavio päivittyy|OK
Pumpun tilan polling|Teksti päivittyy|OK
“Pumppu päälle / pois”|Backend → txt → frontti|OK
Discord-lähetys|toimii reCAPTCHA:n kanssa|OK

<br>

## 5. Tunnetut rajoitukset
- Pumpun tila ei tallennu historiaan (vain pumpun tilan hakeminen tietokannasta).
- HTTP-yhteys ilman salausta (demokäyttö ok).
- ThingSpeakin päivitysrajoitus 15 s → siksi vain 10 min välein.
