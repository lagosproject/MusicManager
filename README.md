# MusicManager

[![Python Version](https://img.shields.io/badge/python-3.11%20%7C%203.12-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.42+-FF4B4B.svg)](https://streamlit.io/)
[![Powered by MusicCore](https://img.shields.io/badge/Powered%20by-MusicCore-green.svg)](https://github.com/lagosproject/MusicCore)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

A powerful, privacy-first **Spotify playlist manager and music library organizer** built with Streamlit and powered by [MusicCore](https://github.com/lagosproject/MusicCore). 

MusicManager solves the clutter in large Spotify music libraries by providing automated hierarchical playlist merges, version-aware track deduplication, library coverage audits, and intelligent genre discovery—without sending your personal listening data to third-party cloud servers.

---

## 🌟 Why MusicManager?

Managing hundreds of playlists and thousands of saved tracks on Spotify is cumbersome:
- **Nested / Hierarchical Playlists**: Spotify does not natively allow automated cascading playlists (e.g. automatically syncing Subgenres → Main Genre → Master Playlist).
- **Silent Duplicates**: Remasters, Deluxe editions, live recordings, and multi-album releases clutter playlists with identical songs.
- **Lost & Forgotten Tracks**: Saved songs in "Liked Songs" frequently slip through the cracks and never get assigned to any playlist.
- **Spotify API Rate Limits**: Complex bulk operations trigger HTTP 429 penalties and 403 bulk restrictions.

**MusicManager** solves these problems directly in a clean, local web dashboard.

---

## 🚀 Key Features

* 🔀 **Hierarchical Playlist Merges**: Build directed dependency trees of playlists. Merging a child playlist automatically ripples up and updates all parent playlists.
* 🛡️ **Safe Merge Previews & Dry-Runs**: Inspect incoming tracks, track diffs, and exact counts in a detailed preview table before writing any changes to your Spotify account.
* 🧹 **Advanced Track Deduplication**: Detect duplicate songs across playlists using both exact Spotify URI matching and fuzzy metadata matching (title + primary artist). Visually choose which edition to retain.
* 📊 **Library Organization & Coverage Audit**: Discover unorganized tracks, find saved songs not belonging to any playlist, and sync missing songs directly back to "Liked Songs" with minimal API requests.
* 🏷️ **Smart Offline Genre Classifier**: Categorize and group songs based on artist overlap and playlist metadata, completely independent of external rate-limited APIs.
* ⚡ **Resilient Engine via [MusicCore](https://github.com/lagosproject/MusicCore)**: Automatic HTTP 429 exponential backoff, persistent atomic local caching (85% disk footprint reduction), and bulk batching optimization.

---

## 🛠️ Requirements

- **Python**: 3.11 or 3.12+
- A free **Spotify Developer Application** (Client ID & Client Secret)
- *(Optional)* [MusicCore](https://github.com/lagosproject/MusicCore) installed in your Python environment

---

## 📦 Quickstart & Installation

### 1. Clone the repository
```bash
git clone https://github.com/lagosproject/MusicManager.git
cd MusicManager
```

### 2. Create and activate a virtual environment
```bash
# Linux / macOS
python -m venv .venv
source .venv/bin/activate

# Windows (PowerShell)
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 3. Install dependencies
```bash
pip install -e ".[dev]"
```

### 4. Configure Spotify credentials
Copy the template and set up your credentials:
```bash
cp .env.template .env     # Linux / macOS
# or: copy .env.template .env (Windows)
```

Edit `.env` with your Spotify app details:
```env
SPOTIPY_CLIENT_ID=your_spotify_client_id
SPOTIPY_CLIENT_SECRET=your_spotify_client_secret
SPOTIPY_REDIRECT_URI=http://127.0.0.1:8978/callback
```

> **Setting up your Spotify App**:
> 1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard) and click **Create app**.
> 2. Set **Redirect URI** to `http://127.0.0.1:8978/callback` (must use `127.0.0.1`, not `localhost`).
> 3. Select **Web API** under APIs used.
> 4. Copy your **Client ID** and **Client Secret** into your `.env` file.

---

## 🖥️ Usage

Launch the Streamlit web dashboard:
```bash
streamlit run main_streamlit.py
```

The app will open automatically in your browser at `http://localhost:8501`. 
On first launch, you will be prompted to authorize your Spotify account. Tokens are securely stored in your local `data/` directory and are never transmitted externally.

---

## 📂 Project Architecture

```
MusicManager/
├── main_streamlit.py          # App entrypoint (st.navigation multi-page controller)
├── app_pages/                 # Modular Streamlit dashboard pages
│   ├── ui_common.py           # Shared UI helpers, session state, Spotify client loader
│   ├── 01_dashboard.py        # Library summary & stats
│   ├── 02_merges_manage.py    # Visual merge tree editor & graph
│   ├── 03_merges_run.py       # Hierarchical merge runner with safe dry-run preview
│   ├── 04_organization.py     # Organization health check & playlist coverage
│   ├── 05_unplaced.py         # "Saved but unplaced" track resolver
│   ├── 06_genre_sorter.py     # Artist overlap & title-based genre classification
│   └── 07_duplicates.py       # Multi-version deduplication & cleanup
├── music_manager/             # Core business logic
│   ├── config.py              # Environment settings & path configuration
│   └── core/                  # Spotify client wrapper, merge trees, deduplication engine
├── tests/                     # 110+ offline unit tests with mock Spotify backends
└── tools/diag/                # CLI diagnostics & real Spotify API integration tests
```

---

## 🧪 Running Tests

Run the full offline test suite without touching your real Spotify account:
```bash
pytest
```

---

## 🤝 Ecosystem & Related Projects

* **[MusicCore](https://github.com/lagosproject/MusicCore)**: Resilient Spotify Web API toolkit, rate-limit retry, audio preview resolver fallback, and playlist engine.
* **[ArtistCollabMap](https://github.com/lagosproject/ArtistCollabMap)**: Interactive force-directed network graph exploring artist collaborations and music discovery.

---

## 📄 License

This project is open-source under the [MIT License](LICENSE).
