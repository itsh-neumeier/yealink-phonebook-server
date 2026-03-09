# YeaBook

Dockerized Flask application for Yealink phonebook provisioning over HTTP.

## Language Versions
- German documentation: [README.de.md](README.de.md)

## Features
- Manage multiple phonebooks
- Edit phonebook name/description
- Add, edit, and delete contacts
- Contact photo upload with browser cropper and automatic Yealink-size JPEG normalization
- Default silhouette photo for contacts without custom image
- Import/export CSV
- Import/export Yealink XML
- HTTP provisioning endpoint per phonebook: `/<slug>.xml`
- Phonebook photo library with ZIP export
- Safe phonebook deletion with slug confirmation
- Web authentication with admin user management
- UI language switch (EN/DE)
- Light/Dark theme toggle with system auto-detection
- Favicon included
- Functional tests with pytest
- CI and GHCR release pipeline

## Security Focus
- Passwords are stored as hashes
- Session-based login for WebUI
- Admin-only user management
- Non-root container user
- Automatic startup database migrations for persistent volume compatibility

## Quick Start (Docker)
Example `docker-compose.yml`:
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
- Default admin user: `admin`
- Default admin password: `change-me-now`

## Yealink Provisioning URLs
Per phonebook:
- HTTP: `http://<host>:8080/<slug>.xml`
- HTTP (with auth in URL): `http://<user>:<password>@<host>/<slug>.xml`

Default bootstrap credential env vars:
- `ACCESS_DEFAULT_USERNAME`
- `ACCESS_DEFAULT_PASSWORD`

Additional credentials are managed in the Access List admin page in the header.

## CSV Format
```csv
name,office,mobile,other,line,ring,group
```
Rules:
- `name` required
- At least one of `office`, `mobile`, `other` required

## Development
```bash
python -m venv .venv
# Linux/macOS
source .venv/bin/activate
# Windows PowerShell
# .venv\Scripts\Activate.ps1
pip install -r requirements.txt -r requirements-dev.txt
python -m app.main
```

Run tests:
```bash
python -m pytest -q
```

## Data Compatibility (Persistent Volumes)
- The app runs automatic schema migrations on startup.
- Existing SQLite data in mounted volumes is migrated forward when new versions add schema changes.
- Migration is additive and designed to keep existing phonebooks/users/credentials usable across image upgrades.

## Versioning
Semantic Versioning 2.0.0: [https://semver.org/spec/v2.0.0.html](https://semver.org/spec/v2.0.0.html)

## Changelog
See [CHANGELOG.md](CHANGELOG.md).

## License
MIT, see [LICENSE](LICENSE).
