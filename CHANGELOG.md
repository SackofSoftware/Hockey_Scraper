# Changelog

## [0.2.0] - 2026-01-27

### Changed
- Reorganized project structure from flat root (158 items) into organized directories (~25 root items)
- Moved 45 documentation files into categorized `docs/` subdirectories (api, pipeline, scrapers, stats, deployment, setup, llm)
- Moved test files into `tests/` with JSON fixtures in `tests/fixtures/`
- Moved research/exploration scripts into `research/`
- Moved automation/runner scripts into `scripts/`
- Archived old experimental versions (v0.1, v0.2, v2, hockey_scraper_repo, etc.) into `archive/`

### Added
- `.gitignore` for Python, databases, data outputs, and OS files
- `pyproject.toml` with modern Python project configuration
- `CHANGELOG.md`
- `logos/` directory with 40 SVG team logos as single source of truth
- `logo_service.py` - Logo cross-reference system mapping team names to local SVGs and GameSheet CDN URLs
- Logo API endpoints (`/api/v1/logos/`) for manifest, team lookup, file serving, and search
- `LogoInfo` and `LogoManifest` Pydantic models
- Structured `data/` directory with `.gitkeep` placeholders
- `config/` directory for JSON configuration files

### Fixed
- Removed stale `.tmp` editor autosave files
- Removed cached `__pycache__` directories
- Fixed import paths in `scripts/` runner files

## [0.1.0] - 2025-09-04

### Added
- Initial scraper (`sprocket_scraper.py`) for Bay State Hockey League
- Playwright-based SPA scraping with JSON API capture
- SSC Hockey scraper for SportsEngine sites
- GameSheet API integration for schedules, standings, and box scores
- Advanced stats database and calculator
- FastAPI REST API server
- Data quality analysis pipeline
- Smart time-aware update system
- Multi-league support (BSHL, Eastern Hockey Federation)
