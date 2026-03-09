# Yealink Phonebook Server (Deutsch)

Dockerisierte Flask-Anwendung mit:
- WebUI (Bootstrap) zur Verwaltung mehrerer Yealink-Telefonbücher
- Authentifiziertem WebUI inkl. Admin-Userverwaltung
- FTP-Usermanagement und Bereitstellung der Telefonbücher per FTP
- CSV Import/Export`r`n- Yealink XML Import/Export (UI + API)
- Yealink XML Provisioning Endpoint

## Sprachversionen
- Englische Dokumentation: [README.md](README.md)

## Funktionen
- Mehrere Telefonbücher mit eindeutigen Slugs
- Kontaktverwaltung (office/mobile/other)
- Automatische Yealink-XML-Generierung je Telefonbuch
- CSV Import/Export`r`n- Yealink XML Import/Export (UI + API) für Massenpflege
- Web-Authentifizierung (Session-basiert)
- Admin-verwaltete Benutzer (Web + FTP)
- FTP-Server mit Read-only Rechten
- Funktionstests mit pytest
- CI- und GHCR-Release-Pipeline

## IT-Sicherheit
- Passwörter werden gehasht gespeichert (Werkzeug)
- Keine Klartext-Passwörter in der Datenbank
- WebUI nur nach Login erreichbar
- User- und FTP-Verwaltung nur für Admins
- FTP-Nutzer haben nur Leserechte (`elr`)
- Container läuft als Nicht-Root-Benutzer

Wichtig: FTP ist standardmäßig unverschlüsselt. Für Produktion nur in geschützten Netzen (z. B. VPN) oder mit zusätzlicher Absicherung (TLS-Termination, Firewall, Segmentierung) einsetzen.

## Schnellstart (Docker)
```bash
docker compose up --build
```

WebUI:
- URL: `http://localhost:8080/login`
- Standard-Admin: `admin`
- Standard-Passwort: `change-me-now` (in `docker-compose.yml`)

FTP:
- Host: `localhost`
- Port: `2121`
- Zugangsdaten: über WebUI (`Users`)
- Telefonbuchdateien: `/<phonebook-slug>.xml`

## Yealink Provisioning URLs
Pro Telefonbuch:
- HTTP: `http://<host>:8080/api/phonebooks/<slug>.xml`
- FTP: `ftp://<ftp-user>:<ftp-pass>@<host>:2121/<slug>.xml`

## CSV-Format
Header:
```csv
name,office,mobile,other,line,ring,group
```
Regeln:
- `name` ist Pflicht
- Mindestens eine Nummer aus `office`, `mobile`, `other` ist Pflicht

## Entwicklung
### Lokal starten
```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
pip install -r requirements.txt -r requirements-dev.txt
python -m app.main
```

### Tests ausführen
```bash
pytest -q
```

## GitHub + Versionierung (SemVer)
Dieses Projekt ist auf Semantic Versioning 2.0.0 ausgelegt: [https://semver.org/spec/v2.0.0.html](https://semver.org/spec/v2.0.0.html)

Release-Ablauf:
1. `CHANGELOG.md` aktualisieren
2. Tag im Format `vMAJOR.MINOR.PATCH` setzen und pushen
3. GitHub Action validiert den Tag
4. Docker-Image wird nach GHCR veröffentlicht:
   - `ghcr.io/<owner>/<repo>:vMAJOR.MINOR.PATCH`
   - `ghcr.io/<owner>/<repo>:latest`

Beispiel:
```bash
git tag v0.1.0
git push origin v0.1.0
```

## Öffentliches GitHub-Repo erstellen
```bash
git init
git add .
git commit -m "feat: initial release"
git branch -M main
git remote add origin https://github.com/<owner>/<repo>.git
git push -u origin main
```

Danach in den GitHub-Repo-Einstellungen auf `Public` stellen.

## Changelog
Siehe [CHANGELOG.md](CHANGELOG.md).

## Lizenz
MIT, siehe [LICENSE](LICENSE).