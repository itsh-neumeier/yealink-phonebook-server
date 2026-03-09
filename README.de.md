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
- HTTP Provisioning Endpoint pro Telefonbuch: `/<slug>.xml`
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

## Schnellstart (Docker)
Beispiel `docker-compose.yml`:
```yaml
version: "3.9"
services:
  yeabook:
    image: ghcr.io/itsh-neumeier/yealink-phonebook-server:latest
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
    volumes:
      - yeabook_data:/data

volumes:
  yeabook_data:
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

## CSV-Format
```csv
name,office,mobile,other,line,ring,group
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

## Versionierung
Semantic Versioning 2.0.0: [https://semver.org/spec/v2.0.0.html](https://semver.org/spec/v2.0.0.html)

## Changelog
Siehe [CHANGELOG.md](CHANGELOG.md).

## Lizenz
MIT, siehe [LICENSE](LICENSE).
