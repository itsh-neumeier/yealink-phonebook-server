# Changelog

All notable changes to this project are documented in this file.
The format follows Keep a Changelog and Semantic Versioning 2.0.0.

## [Unreleased]
### Added
- Add ringtone presets with custom input and rename number labels.
- Add error pages and fix language dropdown layering.
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
