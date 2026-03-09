# Changelog

All notable changes to this project are documented in this file.
The format follows Keep a Changelog and Semantic Versioning 2.0.0.

## [Unreleased]
### Changed
- Removed FTP service and FTP user management.
- Switched provisioning to HTTP-only XML delivery.
- Added phonebook edit (name/description) in WebUI.
- Added contact edit in WebUI.
- Added UI language switch (EN/DE).
- Added light/dark mode with system auto-detection.
- Added favicon.

## [0.1.0] - 2026-03-09
### Added
- Flask WebUI with Bootstrap for multi-phonebook management.
- Contact CRUD and Yealink XML export endpoint.
- CSV import/export per phonebook.
- Built-in FTP server exposing generated phonebook XML files.
- Web authentication and admin user management.
- FTP account management with hashed FTP passwords.
- Dockerfile and docker-compose setup.
- Functional test suite with pytest.
- GitHub Actions CI and GHCR release pipeline.
- English and German README documentation.
