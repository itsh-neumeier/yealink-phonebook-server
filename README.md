# YeaBook

Dockerized Flask application providing:
- WebUI (Bootstrap) for managing multiple Yealink phonebooks
- Authenticated WebUI with admin user management
- FTP account management and FTP phonebook delivery
- CSV import/export
- Yealink XML import/export (UI + API)
- Yealink XML provisioning endpoint

## Language Versions
- German documentation: [README.de.md](README.de.md)

## Features
- Multiple phonebooks with unique slug per phonebook
- Contact management (office/mobile/other phone numbers)
- Automatic Yealink XML file generation per phonebook
- CSV import/export
- Yealink XML import/export (UI + API) for bulk operations
- Web authentication (session-based)
- Admin-managed users (Web + FTP credentials)
- FTP server with read-only permissions
- Functional tests with pytest
- CI and GHCR release pipeline

## Security Focus
- Passwords are stored as hashes (Werkzeug)
- No plaintext passwords in the database
- WebUI is protected by login
- User and FTP management limited to admins
- FTP users are read-only (`elr` permissions)
- Container runs as non-root user

Important: FTP is not encrypted by default. For production, place this service behind a VPN or use a protected network segment. For internet exposure, add TLS termination and strict firewall rules.

## Quick Start (Docker)
```bash
docker compose up --build
```

WebUI:
- URL: `http://localhost:8080/login`
- Default admin user: `admin`
- Default admin password: `change-me-now` (set in `docker-compose.yml`)

FTP:
- Host: `localhost`
- Port: `2121`
- Credentials: managed in WebUI (`Users` page)
- Phonebook files: `/<phonebook-slug>.xml`

## Yealink Provisioning URLs
Per phonebook:
- HTTP: `http://<host>:8080/<slug>.xml`
- HTTP (with auth in URL): `http://<user>:<password>@<host>:8080/<slug>.xml`
- FTP: `ftp://<ftp-user>:<ftp-pass>@<host>:2121/<slug>.xml`

Optional env vars for auth-link generation in UI:
- `PROVISION_USERNAME`
- `PROVISION_PASSWORD`

## CSV Format
Header columns:
```csv
name,office,mobile,other,line,ring,group
```
Rules:
- `name` required
- At least one of `office`, `mobile`, `other` required

## Development
### Local Setup
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\Activate.ps1  # Windows PowerShell
pip install -r requirements.txt -r requirements-dev.txt
python -m app.main
```

### Run Tests
```bash
pytest -q
```

## GitHub and Versioning (SemVer)
This project is prepared for Semantic Versioning 2.0.0: [https://semver.org/spec/v2.0.0.html](https://semver.org/spec/v2.0.0.html)

Release process:
1. Update `CHANGELOG.md`
2. Create and push a tag in format `vMAJOR.MINOR.PATCH`
3. GitHub Action validates the tag
4. Docker image is built and pushed to GHCR:
   - `ghcr.io/<owner>/<repo>:vMAJOR.MINOR.PATCH`
   - `ghcr.io/<owner>/<repo>:latest`

Example:
```bash
git tag v0.1.0
git push origin v0.1.0
```

## Create Public GitHub Repository
```bash
git init
git add .
git commit -m "feat: initial release"
git branch -M main
git remote add origin https://github.com/<owner>/<repo>.git
git push -u origin main
```

Then set repository visibility to `Public` in GitHub settings.

## GHCR Permissions
The included workflow uses `GITHUB_TOKEN` with `packages: write` permissions.
No additional PAT is required for publishing from Actions in most setups.

## Changelog
See [CHANGELOG.md](CHANGELOG.md).

## License
MIT, see [LICENSE](LICENSE).
