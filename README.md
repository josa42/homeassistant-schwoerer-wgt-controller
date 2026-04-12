# Schwörer WGT Controller

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)

Eine Home Assistant Custom Integration zur intelligenten Steuerung der Schwörer WGT/WRT Wohnraumlüftung.

Diese Integration fungiert als "Controller" für die [schwoerer_lueftung](https://github.com/josa42/homeassistant-schwoerer-lueftung) Integration und automatisiert die Heizungs- und Lüftungssteuerung basierend auf:

- 🌙 **Nachtabsenkung** - Temperatur reduzieren nachts
- 🏖️ **Urlaubsmodus** - Energie sparen bei Abwesenheit
- 🪟 **Fenster-Erkennung** - Heizung drosseln bei offenen Fenstern
- 🌡️ **Außentemperatur** - Wärmepumpe nur bei Bedarf freigeben
- 💨 **Lüfterstufen** - Automatik basierend auf Luftfeuchtigkeit und Tageszeit

## Entscheidungslogik

Der Controller wertet bei jedem Update-Zyklus 7 Regeln aus und führt die Aktionen mit der höchsten Priorität aus:

1. 🔒 **Heizsperre** (Priorität 100) - Manuelle Sperrung
2. 🌡️ **Heizfreigabe** (Priorität 50) - Außentemperatur-basiert  
3. 🏠 **Raumtemperatur** (Priorität 10) - Fenster → Urlaub → Nacht → Normal
4. 🔥 **Zusatzheizer** (Priorität 20) - Bei aktiver Heizfreigabe
5. 💨 **Lüfterstufen** (Priorität 30/100) - Automatik oder manuell

**[Vollständiges Ablauf-Diagramm anzeigen →](docs/decision-logic.md)**

## Installation

### HACS (empfohlen)

1. HACS öffnen
2. Auf die drei Punkte oben rechts klicken → "Benutzerdefinierte Repositories"
3. Repository-URL eingeben: `https://github.com/josa42/homeassistant-schwoerer-wgt-controller`
4. Kategorie: "Integration"
5. "Hinzufügen" klicken
6. Integration suchen und installieren
7. Home Assistant neu starten

### Manuell

1. Repository herunterladen
2. `custom_components/schwoerer_wgt_controller` in deinen `custom_components` Ordner kopieren
3. Home Assistant neu starten

## Konfiguration

### Voraussetzungen

- Die [schwoerer_lueftung](https://github.com/josa42/homeassistant-schwoerer-lueftung) Integration muss installiert und konfiguriert sein
- Optional: Fenstersensoren (z.B. Zigbee) für die Fenster-Erkennung
- Optional: Luftfeuchtigkeitssensor für automatische Lüfterstufen-Anpassung

### Setup

1. **Einstellungen** → **Geräte & Dienste** → **Integration hinzufügen**
2. **"Schwörer WGT Controller"** suchen
3. Die Integration erkennt automatisch:
   - Alle Räume aus `schwoerer_lueftung` (via `room_number` Attribut)
   - Außentemperatursensor
   - Wärmepumpen-Steuerung
   - Lüfterstufen-Select
4. **Testmodus** auswählen (empfohlen für ersten Start):
   - ✅ Aktiviert: Nur Logging, keine Änderungen
   - ❌ Deaktiviert: Controller steuert aktiv
5. **Absenden** klicken - fertig!

### Nachträgliche Konfiguration

Über **Optionen** (Zahnrad-Symbol in der Integration):

#### Allgemein
- **Testmodus**: Ein/Ausschalten für sicheres Testen

#### Temperaturen  
- **Normal-Temperatur**: 20°C (Standard-Raumtemperatur)
- **Nacht-Temperatur**: 19°C (Absenkung nachts)
- **Urlaubs-Temperatur**: 18°C (Energie sparen bei Abwesenheit)
- **Fenster-offen-Temperatur**: 12°C (Bei offenen Fenstern)

#### Zeiteinstellungen
- **Nachtmodus Start**: 20:00 (Beginn Nachtabsenkung)
- **Nachtmodus Ende**: 05:00 (Ende Nachtabsenkung)
- **Fenster-Verzögerung**: 1 Min (Wie lange Fenster offen sein muss)

#### Lüfterstufen
- **Normal**: Stufe 2
- **Nacht**: Stufe 1
- **Urlaub**: Stufe 1  
- **Hohe Feuchtigkeit**: Stufe 3

#### Schwellwerte
- **Außentemperatur für Heizfreigabe**: 16°C (WP nur darunter)
- **Luftfeuchtigkeit**: 70% (Schwelle für Lüfterstufe 3)
- **Luftfeuchtigkeitssensor**: Optional konfigurierbar

#### Räume
Pro Raum konfigurierbar:
- Fenstersensor-Zuordnung
- Etage (EG/OG) - bestimmt Zusatzheizer-Steuerung
- Individuelle Temperaturen (überschreiben global)

## Entities

### Steuerung (Switches)

| Entity | Beschreibung |
|--------|--------------|
| `switch.wgt_controller_aktiv` | Controller ein/ausschalten |
| `switch.wgt_controller_testmodus` | Testmodus aktivieren |
| `switch.wgt_controller_urlaubsmodus` | Urlaubsmodus (senkt Temperaturen) |
| `switch.wgt_controller_heizsperre` | Heizung manuell sperren |

### Lüftersteuerung (Select)

| Entity | Beschreibung |
|--------|--------------|
| `select.wgt_controller_lufterstufen_override` | Manuelle Lüfterstufe (Auto, 0-4) |

### Status (Sensoren)

| Entity | Beschreibung |
|--------|--------------|
| `sensor.wgt_controller_status` | Globaler Status (Normal/Nacht/Urlaub/Gesperrt) |
| `sensor.wgt_controller_explanation` | Textuelle Erklärung aller aktiven Regeln |

### Raum-Sensoren (pro Raum)

| Entity | Beschreibung |
|--------|--------------|
| `sensor.wgt_controller_room_N_mode` | Modus des Raums |
| `sensor.wgt_controller_room_N_target_temp` | Berechnete Solltemperatur |
| `sensor.wgt_controller_room_N_explanation` | Warum diese Temperatur |

### Binary Sensoren

| Entity | Beschreibung |
|--------|--------------|
| `binary_sensor.wgt_controller_heizfreigabe` | Wärmepumpe Heizen freigegeben |
| `binary_sensor.wgt_controller_kuhlfreigabe` | Wärmepumpe Kühlen freigegeben |
| `binary_sensor.wgt_controller_nachtmodus` | Nachtzeit aktiv |
| `binary_sensor.wgt_controller_urlaubsmodus` | Urlaubsmodus aktiv |

**Hinweis**: Alle Controller-Entities sind am WGT-Gerät angehängt. Raum-spezifische Entities erscheinen unter den jeweiligen Raum-Geräten.

## Testmodus

Im Testmodus werden alle Aktionen nur geloggt, aber nicht ausgeführt. **Ideal zum Testen der Logik ohne die Anlage zu beeinflussen.**

### Aktivieren:
- ✅ **Bei Setup**: Checkbox "Testmodus" aktivieren (standardmäßig an)
- ✅ **Nachträglich**: Über `switch.wgt_controller_testmodus`
- ✅ **In Optionen**: Allgemein → Testmodus

### Log-Ausgabe:
```
[TEST MODE] Would execute: set_room_temperature on climate.wgt_raum_1 = 19.0 (Reason: Nachtmodus → 19.0°C)
[TEST MODE] Would execute: set_heat_pump_heating on heat_pump = True (Reason: Außentemperatur 6.5°C < 16.0°C)
[TEST MODE] Would execute: set_fan_level on fan = 1 (Reason: Nachtmodus → Stufe 1)
```

## Beispiel: Erklärungssensoren

Die Erklärungssensoren zeigen immer transparent, warum der aktuelle Zustand so ist:

**Global** (`sensor.wgt_controller_explanation`):
- "Nachtmodus (20:00-05:00), Außentemperatur 6.5°C < 16.0°C → Heizfreigabe, Lüfterstufe: Nachtmodus → Stufe 1"

**Pro Raum** (`sensor.wgt_controller_room_1_explanation`):
- "Nachtmodus → 19.0°C"
- "Fenster offen seit 3 Min → 12.0°C"
- "Urlaubsmodus → 18.0°C"

## Automatisierungs-Beispiele

### Benachrichtigung bei Heizfreigabe
```yaml
automation:
  - alias: "WGT: Heizfreigabe geändert"
    trigger:
      - platform: state
        entity_id: binary_sensor.wgt_controller_heizfreigabe
    action:
      - service: notify.mobile_app
        data:
          message: "Heizfreigabe: {{ trigger.to_state.state }}"
```

### Urlaubsmodus automatisch aktivieren
```yaml
automation:
  - alias: "WGT: Urlaubsmodus bei Abwesenheit"
    trigger:
      - platform: state
        entity_id: person.owner
        to: "not_home"
        for:
          hours: 2
    action:
      - service: switch.turn_on
        target:
          entity_id: switch.wgt_controller_urlaubsmodus
```

## Default-Werte

| Einstellung | Default |
|-------------|---------|
| **Temperaturen** | |
| Normal-Temperatur | 20°C |
| Nacht-Temperatur | 19°C |
| Urlaubs-Temperatur | 18°C |
| Fenster-offen-Temperatur | 12°C |
| **Zeiteinstellungen** | |
| Nachtmodus Start | 20:00 |
| Nachtmodus Ende | 05:00 |
| Fenster-Verzögerung | 1 Min |
| **Lüfterstufen** | |
| Normal | Stufe 2 |
| Nacht | Stufe 1 |
| Urlaub | Stufe 1 |
| Hohe Feuchtigkeit | Stufe 3 |
| **Schwellwerte** | |
| Außentemperatur für Heizfreigabe | 16°C |
| Luftfeuchtigkeit | 70% |

## Features

✅ **Automatische Entdeckung**: Erkennt alle Räume aus `schwoerer_lueftung` automatisch  
✅ **Testmodus**: Sicheres Testen ohne Änderungen an der Anlage  
✅ **Erklärungssensoren**: Transparente Darstellung aller Entscheidungen  
✅ **Flexible Konfiguration**: Globale und raum-spezifische Einstellungen  
✅ **Integrierte Steuerung**: Urlaubsmodus, Heizsperre, Lüfterstufen als Teil der Integration  
✅ **Geräte-Integration**: Alle Entities am WGT-Gerät bzw. Raum-Geräten angehängt  
✅ **Mehrsprachig**: Deutsche und englische UI-Übersetzungen  

## Entwicklung

Siehe [AGENTS.md](AGENTS.md) für Beitragsrichtlinien.

## Lizenz

MIT
