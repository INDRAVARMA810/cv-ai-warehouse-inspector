# Manual Setup Guide — AI Warehouse Safety Inspector

Running the project **without Docker** requires setting up the backend, frontend, and database separately on your machine.

---

## ✅ Prerequisites

- **Python 3.12+** — [Download](https://www.python.org/downloads/)
- **Node.js 20+** — [Download](https://nodejs.org/)
- **PostgreSQL 16** — [Download](https://www.postgresql.org/download/) *(optional; SQLite works for quick start)*
- **Git** — for cloning and version control

### Verify Installations

```bash
python --version        # Should be 3.12+
node --version          # Should be 20+
npm --version           # Comes with Node.js
psql --version          # Optional; PostgreSQL 16+
```

---

## 📦 1. Database Setup

### Option A: PostgreSQL (Recommended for production)

#### Windows

1. **Install PostgreSQL 16**
   - Accept default settings (port 5432, superuser `postgres`)
   - Remember the password you set during installation

2. **Create the database**
   ```bash
   psql -U postgres
   ```
   Then in the `psql` prompt:
   ```sql
   CREATE DATABASE warehouse_ai;
   \q
   ```

3. **Verify connection**
   ```bash
   psql -U postgres -d warehouse_ai -c "SELECT 1;"
   ```

#### Linux / macOS

```bash
# Install PostgreSQL (example: Ubuntu/Debian)
sudo apt-get install postgresql postgresql-contrib

# Start the service
sudo systemctl start postgresql

# Create database
sudo -u postgres psql -c "CREATE DATABASE warehouse_ai;"

# Verify
psql -U postgres -d warehouse_ai -c "SELECT 1;"
```

### Option B: SQLite (Quick start, no installation needed)

Skip PostgreSQL entirely. The backend will create a local `warehouse_ai.db` file automatically. 
Set in `.env`:
```
DATABASE_URL=sqlite:///warehouse_ai.db
```

---

## 🔧 2. Backend Setup

### Step 1: Prepare the environment

```bash
# Navigate to project root
cd d:/Projects/AI-Warehouse-Safety-Inspector

# Create Python virtual environment
python -m venv venv

# Activate it
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate```

### Step 2: Install dependencies

```bash
# Install main requirements
pip install -r requirements.txt

# Install ByteTrack's linear-assignment solver (required)
pip install "lap>=0.5.12"

# Optional: GPU support (CUDA)
# pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
```

> **Note:** `requirements.txt` is UTF-16LE (from Windows PowerShell). If you get encoding errors on Linux/macOS:
> ```bash
> iconv -f UTF-16 -t UTF-8 requirements.txt -o requirements-utf8.txt
> pip install -r requirements-utf8.txt
> ```

### Step 3: Configure the backend

```bash
cd backend

# Copy the example config
cp .env.example .env

# Edit .env and set DATABASE_URL:
# Option A (PostgreSQL):
# DATABASE_URL=postgresql+psycopg://postgres:password@localhost:5432/warehouse_ai

# Option B (SQLite, no setup needed):
# DATABASE_URL=sqlite:////absolute/path/to/warehouse_ai.db
# Or relative:
# DATABASE_URL=sqlite:///./warehouse_ai.db
```

### Step 4: Initialize the database

```bash
cd backend

# Create schema (tables)
python -c "from app.database import initialize; initialize()"

# Load demo data (optional)
python -m app.database.seed
```

### Step 5: Start the backend

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

**Expected output:**
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete.
```

**Access:**
- Dashboard API: `http://localhost:8000/api/v1`
- API docs: `http://localhost:8000/docs` (Swagger UI)
- H
ealth check: `http://localhost:8000/api/v1/health`

> The `--reload` flag auto-restarts when you edit Python files (development only).

---

## 💻 3. Frontend Setup

### In a new terminal (with venv still activated)

```bash
cd frontend

# Install dependencies
npm install

# Start dev server
npm run dev
```

**Expected output:**
```
VITE v5.x.x  ready in XXX ms

➜  Local:   http://localhost:5173/
```

**Access:**
- Dashboard: `http://localhost:5173/`

> **Important:** Use `localhost`, not `127.0.0.1`. Vite binds to IPv6 by default.

---

## 🎬 4. Verify Everything Works

1. **Backend running?**
   ```bash
   curl http://localhost:8000/api/v1/health
   ```
   Should return:
   ```json
   {"status":"ok","application":"AI Warehouse Safety Inspector",...}
   ```

2. **Frontend loaded?**
   - Open `http://localhost:5173/` in your browser
   - You should see the dark-themed dashboard

3. **Database connected?**
   - Check backend console for `Schema ready` message
   - API `/health` endpoint should show `"database": {"healthy": true}`

---

## 🎥 5. Using the Pipeline

### Option A: Live detection in the dashboard

1. Open `http://localhost:5173/` in your browser
2. Go to the **Live Monitoring** tab
3. The pipeline auto-starts when you view the stream
4. Provide a video source (see [Video Sources](#video-sources) below)

### Option B: Standalone pipeline (no dashboard)

```bash
cd backend

# Camera feed only (OpenCV window)
python run_camera.py

# Full pipeline with rule detection (OpenCV window)
python run_detection.py

# Use a video file
python run_detection.py --source videos/warehouse-demo.mp4 --device cpu

# Use GPU (if available)
python run_detection.py --device cuda
```

> **Note:** `run_detection.py` runs in its own process and does NOT send output to the dashboard. 
> The dashboard stream requires the pipeline to run inside the API process.

---

## 🎬 Video Sources

The `STREAM_SOURCE` environment variable controls what to capture:

| Source | Example | Notes |
|:--|:--|:--|
| **Webcam** | `0` | First connected camera (default) |
| **Video file** | `/path/to/video.mp4` | Absolute or relative path inside working dir |
| **IP camera** | `http://192.168.1.100:8080/video` | MJPEG or RTSP stream |
| **Screen** | `"screen://desktop"` | Requires `mss` library |

### Set in `.env`:
```bash
STREAM_SOURCE=/path/to/videos/warehouse-demo.mp4
STREAM_AUTO_START=true
```

### Or pass on command line:
```bash
STREAM_SOURCE=videos/warehouse-demo.mp4 uvicorn app.main:app --reload --port 8000
```

---

## 🔧 Environment Variables Reference

### Database

| Variable | Default | Example |
|:--|:--|:--|
| `DATABASE_URL` | — | `postgresql+psycopg://postgres:password@localhost:5432/warehouse_ai` |
| `DB_POOL_SIZE` | `5` | Number of connections to keep open |
| `DB_POOL_PRE_PING` | `true` | Validate connection before use |
| `DB_ECHO` | `false` | Log SQL statements (verbose) |

### Video Stream

| Variable | Default | Example |
|:--|:--|:--|
| `STREAM_SOURCE` | `0` | `videos/warehouse-demo.mp4` |
| `STREAM_WEIGHTS` | `yolov8n.pt` | `yolov8m.pt` (larger, slower) |
| `STREAM_DEVICE` | *(auto)* | `cuda` or `cpu` |
| `STREAM_CONF` | `0.25` | Detection confidence threshold (0–1) |
| `STREAM_WIDTH` | `960` | Inference frame width |
| `STREAM_HEIGHT` | `540` | Inference frame height |
| `STREAM_AUTO_START` | `true` | Start capture on first viewer |

### Application

| Variable | Default |
|:--|:--|
| `APP_NAME` | `AI Warehouse Safety Inspector` |
| `APP_VERSION` | `1.0.0` |
| `LOG_LEVEL` | `INFO` |

---

## 🐛 Troubleshooting

### Backend fails to start

**Error:** `ModuleNotFoundError: No module named 'app'`
- **Solution:** Ensure you're running from the project root, not inside `backend/`
  ```bash
  # ✅ Correct
  cd d:/Projects/AI-Warehouse-Safety-Inspector
  python -c "from app.database import initialize; ..."
  
  # ❌ Wrong
  cd backend
  python -c "from app.database import ..."
  ```

**Error:** `psycopg.OperationalError: connection failed`
- **Solution:** Check PostgreSQL is running and credentials are correct
  ```bash
  psql -U postgres -d warehouse_ai -c "SELECT 1;"
  ```

**Error:** `lap not found`
- **Solution:** ByteTrack's linear-assignment solver is missing
  ```bash
  pip install "lap>=0.5.12"
  ```

### Frontend doesn't load

**Error:** Port 5173 already in use
- **Solution:** Vite will try 5174, 5175, etc. Check the console output. Or kill the existing process:
  ```bash
  # Windows: find and kill the process on port 5173
  netstat -ano | findstr :5173
  taskkill /PID <PID> /F
  
  # Linux/macOS:
  lsof -ti:5173 | xargs kill -9
  ```

**Error:** `http://localhost:5173` gives connection refused
- **Solution:** Use `http://localhost:5173` (not `127.0.0.1:5173`). Vite binds to IPv6 by default.

### API doesn't respond to frontend requests

**Error:** `Failed to fetch /api/v1/tracks`
- **Check:** Are backend and frontend both running?
  ```bash
  curl http://localhost:8000/api/v1/health
  ```
- **Check:** Frontend dev server proxies to `http://127.0.0.1:8000` by default.
  Edit `frontend/vite.config.ts` if your backend is on a different host.

### Video stream doesn't start

**Error:** `OpenCV cannot open camera source`
- **Solution:** Check the source exists and permissions are correct
  ```bash
  # Verify file exists
  ls -la videos/warehouse-demo.mp4
  
  # Use camera index directly (0 = first webcam)
  STREAM_SOURCE=0 uvicorn app.main:app --reload
  ```

**Error:** `YOLO weights download fails`
- **Solution:** Pre-download weights outside Docker:
  ```bash
  python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"
  ```
  Then set `STREAM_WEIGHTS=yolov8n.pt` to use the cached copy.

### Database schema not initialized

**Error:** `ProgrammingError: relation "alert_records" does not exist`
- **Solution:** Run initialization:
  ```bash
  python -c "from app.database import initialize; initialize()"
  ```

---

## 🚀 Running All Services at Once

For convenience, you can run everything in separate terminal tabs:

### Terminal 1: PostgreSQL (if not auto-started)
```bash
# Linux
sudo systemctl start postgresql

# macOS (with Homebrew)
brew services start postgresql

# Windows: Already running as a service
```

### Terminal 2: Backend
```bash
cd d:/Projects/AI-Warehouse-Safety-Inspector
venv\Scripts\activate
cd backend
uvicorn app.main:app --reload --port 8000
```

### Terminal 3: Frontend
```bash
cd d:/Projects/AI-Warehouse-Safety-Inspector
cd frontend
npm run dev
```

### Access
- **Dashboard:** `http://localhost:5173/`
- **API Docs:** `http://localhost:8000/docs`

---

## 📝 Tips

- **Hot reload:** Both `uvicorn --reload` and `npm run dev` watch for file changes and restart automatically
- **Faster inference:** Use a smaller model (`yolov8n.pt` = nano, ~50ms) instead of larger ones
- **GPU acceleration:** Install CUDA-enabled PyTorch and set `STREAM_DEVICE=cuda`
- **Disable auto-start:** Set `STREAM_AUTO_START=false` to manually start the pipeline from the UI
- **Logging:** Set `LOG_LEVEL=DEBUG` for verbose output when troubleshooting

---

## ⚡ Quick Start (Minimal)

```bash
# 1. Backend
cd d:/Projects/AI-Warehouse-Safety-Inspector
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
pip install "lap>=0.5.12"

cd backend
cp .env.example .env
# Edit .env and set DATABASE_URL to sqlite:///warehouse_ai.db (no PostgreSQL needed!)

python -c "from app.database import initialize; initialize()"
uvicorn app.main:app --reload --port 8000

# 2. Frontend (new terminal)
cd frontend
npm install
npm run dev

# 3. Open dashboard
# http://localhost:5173/
```

Done! The pipeline starts automatically when you open the dashboard.
