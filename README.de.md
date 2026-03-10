# YeaBook (Deutsch)

Dockerisierte Flask-Anwendung fuer Yealink-Telefonbuch-Provisionierung ueber HTTP.

## Sprachversionen
- Englische Dokumentation: [README.md](README.md)

## Funktionen
- Mehrere Telefonbuecher verwalten
- Telefonbuchname/Beschreibung bearbeiten
- Kontakte anlegen, bearbeiten und loeschen
- CSV Import/Export
- Yealink XML Import/Export
- AX86R Local-Telefonbuch Import (manuell + geplanter Geräte-Sync)
- HTTP Provisioning Endpoint pro Telefonbuch: `/<slug>.xml`
- Sicheres Loeschen von Telefonbuechern mit Slug-Bestaetigung
- Web-Authentifizierung mit Admin-Benutzerverwaltung
- UI Sprachumschaltung (DE/EN)
- Light/Dark Theme Toggle mit System-Autoerkennung
- Favicon enthalten
- Funktionstests mit pytest
- CI- und GHCR-Release-Pipeline

## IT-Sicherheit
- Passwoerter werden gehasht gespeichert
- Session-basierte Anmeldung fuer die WebUI
- Benutzerverwaltung nur fuer Admins
- Container laeuft als Nicht-Root-Benutzer
- Automatische Datenbank-Migrationen beim Start fuer persistente Volume-Kompatibilitaet
- `PUID`/`PGID` Unterstuetzung fuer Bind-Mount Host-Volumes
- Gespeicherte AX86R-Web-Zugangsdaten werden verschluesselt abgelegt (abgeleitet aus `SECRET_KEY`)

## Schnellstart (Docker)
Beispiel `docker-compose.yml`:
```yaml
version: "3.9"
services:
  yeabook:
    image: ghcr.io/itsh-neumeier/yeabook:latest
    container_name: yeabook
    restart: unless-stopped
    ports:
      - "8080:8080"
    environment:
      SECRET_KEY: "change-me"
      BASE_HTTP_URL: "https://phonebook.neumeier.cloud"
      ACCESS_DEFAULT_USERNAME: "yeabook_demo_u82"
      ACCESS_DEFAULT_PASSWORD: "YbDemo!9K2xP4"
      ADMIN_USERNAME: "admin"
      ADMIN_PASSWORD: "change-me-now"
      PUID: "1000"
      PGID: "1000"
    volumes:
      - ./data:/data
```

Start:
```bash
docker compose up --build
```

WebUI:
- URL: `http://localhost:8080/login`
- Standard-Admin: `admin`
- Standard-Passwort: `change-me-now`

## Yealink Provisioning URLs
Pro Telefonbuch:
- HTTP: `http://<host>:8080/<slug>.xml`
- HTTP (mit Auth in URL): `http://<user>:<password>@<host>/<slug>.xml`

Default Bootstrap-Zugangsdaten per Env:
- `ACCESS_DEFAULT_USERNAME`
- `ACCESS_DEFAULT_PASSWORD`

Weitere Zugangsdaten werden in der Access-Liste im Header verwaltet.

## AX86R Local-Telefonbuch Sync
1. `Geräte-Sync` im Admin-Menü öffnen.
2. Geräte-Verknüpfung mit AX86R IP/Host, Yealink-Weblogin und Ziel-Telefonbuch anlegen.
3. Intervall in Minuten setzen und Profil aktivieren.
4. Für Sofortlauf `Jetzt ausführen` verwenden.

Verhalten:
- Beim Import werden bestehende Einträge im verknüpften lokalen Telefonbuch immer komplett ersetzt.
- Klingeltöne werden aus AX86R Local Contacts synchronisiert.
- Fotos werden nur synchronisiert, wenn sie zum erlaubten Yealink-Standardfoto-Set in YeaBook gehören.

## Bind-Mount Berechtigungen
Wenn ein Host-Pfad gemountet wird (`./data:/data` oder `/docker-volumes/...:/data`), muss der Ordner fuer den Container-Benutzer beschreibbar sein.

- `PUID` und `PGID` auf die Host-UID/GID setzen.
- Eigentuemer des Host-Ordners auf diese IDs setzen.
- Bei Startfehlern gibt YeaBook jetzt eine klare Berechtigungs-Fehlermeldung fuer `/data/phonebooks` aus.

## CSV-Format
```csv
name,office,mobile,other,line,group
```
Regeln:
- `name` ist Pflicht
- Mindestens eine Nummer aus `office`, `mobile`, `other` ist Pflicht

## Entwicklung
```bash
python -m venv .venv
# Linux/macOS
source .venv/bin/activate
# Windows PowerShell
# .venv\Scripts\Activate.ps1
pip install -r requirements.txt -r requirements-dev.txt
python -m app.main
```

Tests ausfuehren:
```bash
python -m pytest -q
```

## Datenkompatibilitaet (Persistente Volumes)
- Die Anwendung fuehrt beim Start automatische Schema-Migrationen aus.
- Bestehende SQLite-Daten in gemounteten Volumes werden bei neuen Versionen vorwaerts migriert.
- Die Migration ist additiv ausgelegt, damit vorhandene Telefonbuecher/Benutzer/Zugangsdaten bei Upgrades nutzbar bleiben.

## Versionierung
Semantic Versioning 2.0.0: [https://semver.org/spec/v2.0.0.html](https://semver.org/spec/v2.0.0.html)

## Changelog
Siehe [CHANGELOG.md](CHANGELOG.md).

## Lizenz
MIT, siehe [LICENSE](LICENSE).
