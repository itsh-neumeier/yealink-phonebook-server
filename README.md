# YeaBook

Dockerized Flask application for Yealink phonebook provisioning over HTTP.

## Language Versions
- German documentation: [README.de.md](README.de.md)

## Features
- Manage multiple phonebooks
- Edit phonebook name/description
- Add, edit, and delete contacts
- Import/export CSV
- Import/export Yealink XML
- AX86R local phonebook import (manual + scheduled device sync)
- HTTP provisioning endpoint per phonebook: `/<slug>.xml`
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
- `PUID`/`PGID` support for bind-mounted host volumes
- Saved AX86R web credentials are stored encrypted at rest (derived from `SECRET_KEY`)

## Quick Start (Docker)
Example `docker-compose.yml`:
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

## AX86R Local Phonebook Sync
1. Open `Device Sync` (admin menu).
2. Create a device link with AX86R IP/host, Yealink web login and target YeaBook phonebook.
3. Set an interval in minutes and enable the profile.
4. Use `Run now` for immediate import.

Behavior:
- Import replaces all existing entries in the linked local phonebook on each run.
- Ringtones are synchronized from AX86R local contacts.
- Photos are synchronized only when they match YeaBook's allowed Yealink standard photo set.

## Bind Mount Permissions
If you use a host path (`./data:/data` or `/docker-volumes/...:/data`), the mounted folder must be writable by the container user.

- Set `PUID` and `PGID` to your host user/group ID.
- Ensure the host directory owner matches these IDs.
- If startup fails, YeaBook now prints a clear permission error for `/data/phonebooks`.

## CSV Format
```csv
name,office,mobile,other,line,group
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
