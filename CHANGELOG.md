# Changelog

All notable changes to this project are documented in this file.
The format follows Keep a Changelog and Semantic Versioning 2.0.0.

## [Unreleased]
### Changed
- Auto-update CHANGELOG.

## [0.3.0] - 2026-03-10
### Added
- Add AX86R local phonebook import profiles.
### Changed
- Auto-update CHANGELOG.
- Auto-update CHANGELOG.

## [0.2.10] - 2026-03-09
### Changed
- Prepare v0.2.10 changelog.
- Auto-update CHANGELOG.
- Auto-update CHANGELOG.
- Auto-update CHANGELOG.
### Fixed
- Support bind mounts via PUID/PGID entrypoint.

## [0.2.9] - 2026-03-09
### Changed
- Remove ringtone feature from UI, backend and CSV.
- Auto-update CHANGELOG.
- Auto-update CHANGELOG.
- Auto-update CHANGELOG.
### Fixed
- Reliably show and persist custom ringtone input.

## [0.2.8] - 2026-03-09
### Changed
- Remove contact photo feature from app and docs.
- Auto-update CHANGELOG.
- Auto-update CHANGELOG.

## [0.2.7] - 2026-03-09
### Changed
- Update GHCR image name to yeabook.
- Auto-update CHANGELOG.
- Auto-update CHANGELOG.

## [0.2.6] - 2026-03-09
### Added
- Add contact photo crop/upload, library zip export and safe phonebook delete.
- Extend ringtone presets and add wav filename hint.
- Auto-migrate persistent volume schema on startup.
### Changed
- Auto-update CHANGELOG.
- Auto-update CHANGELOG.
- Auto-update CHANGELOG.
- Auto-update CHANGELOG.

## [0.2.5] - 2026-03-09
### Added
- Add ringtone presets with custom input and rename number labels.
- Add error pages and fix language dropdown layering.
### Changed
- Backfill releases and automate future updates.
### Fixed
- Update German labels for line and department.

## [0.2.4] - 2026-03-09
### Added
- Improve mobile nav, language dropdown and dark mode grouping.

## [0.2.3] - 2026-03-09
### Fixed
- Preserve auth across department menu links using signed tokens.

## [0.2.2] - 2026-03-09
### Added
- Phonebook-scoped HTTP auth permissions and localized UI fixes.

## [0.2.1] - 2026-03-09
### Added
- Add footer branding, umlaut DE texts, access toggle labels, business departments and visual redesign.

## [0.2.0] - 2026-03-09
### Added
- Enforce basic auth for XML with access-list management; remove FTP.
- Support direct /<slug>.xml links and auth-style provisioning URLs.
- Add persistent light/dark mode toggle.
### Changed
- Add docker compose example to setup guide.
- Rename application to YeaBook.
### Fixed
- Set PYTHONPATH and run pytest via python module.

## [0.1.0] - 2026-03-09
### Added
- Initial yealink phonebook server with auth, ftp, csv/xml import-export, docker and ci.
