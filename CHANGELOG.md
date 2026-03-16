# Changelog

All notable changes to PeerView are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/).

---

## [1.1.1] - 2026-03-16

### Fixed
- **Status colors not showing for down sessions** — BIRD router returns timestamps in format `2026-03-12 07:24:33` (space separator), but code expected ISO format `2026-03-12T07:24:33Z`. When parsing failed, all down sessions defaulted to gray (`secondary`) instead of showing appropriate warning colors (yellow/orange/red) based on session age. Added handling for plain datetime format with `strptime`.

---

## [1.1.0] - 2026-03-15

### Added
- Time format dropdown (Local 24h / Local 12h / UTC 24h), persisted in `localStorage`
- Datetime formatting applied to session "since" timestamps in the peer detail modal and footer
- Security response headers: `Content-Security-Policy`, `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`
- SSRF protection: `session_definition_url` is now rejected unless it starts with `https://`
- Input allowlist validation for `sort` and `sortdir` query parameters
- `requirements-dev.txt` separating development dependencies from production

### Fixed
- **Dashboard established/down counters were incorrect** — the stats counter queried all `.session-status` elements including the legend badges, inflating "down" counts; selector scoped to `.peer-table .session-status`
- **Established sessions never counted** — `get_session_status_class()` returned `'success'` but the CSS and JS expected `'established'`; corrected the return value
- **All non-established sessions rendered grey** — timezone-naive `datetime.now()` was subtracted from a timezone-aware `since_time`, raising `TypeError` silently swallowed by a bare `except`; replaced with `datetime.now(tz=timezone.utc)`
- **`not_connected` filter matched unconfigured peers** — filter now correctly excludes peers with no sessions at the given IXP/AFI
- **Container failed to start** — gunicorn worker class was `aiohttp.GunicornWebWorker` (for aiohttp apps only); replaced with `uvicorn.workers.UvicornWorker`
- **XSS in peer detail modal** — all API-sourced values interpolated into `innerHTML` are now escaped via `escapeHtml()`
- **`debug=True` in `__main__` block** — changed to `False` to prevent exposing the Werkzeug interactive debugger
- **Dockerfile HEALTHCHECK** — was hitting `/api/summary` (full data fetch); corrected to use the lightweight `/health` endpoint
- Replaced deprecated integer `timeout=30` with `aiohttp.ClientTimeout(total=30)`
- Replaced bare `except:` with `except Exception:` in session status class resolution

### Changed
- **aiohttp** upgraded from 3.9.1 to 3.13.3 (14 CVEs resolved, including CVE-2024-23334 directory traversal, CVE-2024-23829 and CVE-2024-52304 request smuggling, multiple DoS vulnerabilities)
- **Flask** upgraded from 3.0.0 to 3.1.3 (CVE-2026-27205)
- **gunicorn** upgraded from 21.2.0 to 25.1.0 (CVE-2024-1135, CVE-2024-6827 request smuggling)
- **PyYAML** upgraded from 6.0.1 to 6.0.2
- **python-dateutil** upgraded from 2.8.2 to 2.9.0.post0
- Added **uvicorn[standard]** as a runtime dependency (required for gunicorn UvicornWorker)

### Removed
- `asyncio-mqtt` — not used anywhere in the codebase
- `ipaddress` — stdlib backport; `ipaddress` is built into Python 3.3+
- `redis` — declared as optional but not implemented
- `prometheus-client` — declared as optional but not implemented
- `pytest`, `black`, `flake8`, `pytest-asyncio` moved to `requirements-dev.txt`

---

## [1.0.1] - 2024-01-17

### Changed
- Updated `requirements.txt` dependency versions
- Added Podman support in container configuration

---

## [1.0.0] - 2024-01-16

### Added
- Initial release of PeerView BGP peering dashboard
- Real-time BGP session monitoring via BIRD looking glass API
- Bootstrap 5 responsive UI with sortable peer table
- Multi-IXP support (AMS-IX, Frys-IX, SpeedIX, NL-IX, Loc-IX, InterIX, LayerswitchIX, FogIXP)
- IPv4 and IPv6 session tracking per exchange
- Peer detail modal with session breakdown
- In-memory cache with configurable TTL
- Docker / Podman multi-stage build with non-root user
- Health check endpoint at `/health`
- API endpoints: `/api/peers`, `/api/peer/<asn>`, `/api/summary`, `/api/version`
