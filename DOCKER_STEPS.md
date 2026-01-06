# Docker Steps for Chit Fund Management System

## Quick Start (Development Mode)

### Step 1: Navigate to Project Directory
```bash
cd /Users/rsk/Documents/GitHub/fundmgr
```

### Step 2: Start Docker Containers
```bash
# Development mode (with auto-reload on code changes)
docker-compose -f docker-compose.dev.yml up
```

**OR use the convenience script:**
```bash
./docker-start.sh
```

### Step 3: Access the Application
- Open your browser and go to: **http://localhost:3434**
- **Admin Login:**
  - Username: `admin`
  - Password: `admin123`

The database will be automatically seeded on first run.

---

## Detailed Steps

### Option A: Development Mode (Recommended for Development)

**Step 1: Build and Start**
```bash
cd /Users/rsk/Documents/GitHub/fundmgr
docker-compose -f docker-compose.dev.yml up --build
```

**What this does:**
- Builds the Docker image
- Starts the container
- Mounts your code directory (changes reflect immediately)
- Enables auto-reload on code changes
- Auto-seeds database on first run

**Step 2: View Logs (in another terminal)**
```bash
cd /Users/rsk/Documents/GitHub/fundmgr
docker-compose -f docker-compose.dev.yml logs -f
```

**Step 3: Stop the Container**
Press `Ctrl+C` in the terminal where it's running, or:
```bash
docker-compose -f docker-compose.dev.yml down
```

---

### Option B: Production Mode

**Step 1: Build and Start in Background**
```bash
cd /Users/rsk/Documents/GitHub/fundmgr
docker-compose up -d --build
```

**Step 2: Check Status**
```bash
docker-compose ps
```

**Step 3: View Logs**
```bash
docker-compose logs -f
```

**Step 4: Stop**
```bash
docker-compose down
```

---

## Common Docker Commands

### View Running Containers
```bash
docker-compose ps
```

### View Logs
```bash
# Follow logs in real-time
docker-compose logs -f

# View last 100 lines
docker-compose logs --tail=100
```

### Restart Container
```bash
docker-compose restart
```

### Rebuild Container (after dependency changes)
```bash
docker-compose build --no-cache
docker-compose up -d
```

### Access Container Shell
```bash
docker-compose exec fundmgr-app bash
```

### Run Commands Inside Container
```bash
# Seed database manually
docker-compose exec fundmgr-app python seed_data.py

# Check Python version
docker-compose exec fundmgr-app python --version
```

### Stop and Remove Everything
```bash
# Stop containers
docker-compose down

# Stop and remove volumes (WARNING: deletes database)
docker-compose down -v
```

---

## Troubleshooting

### Port 3434 Already in Use
```bash
# Find what's using the port
lsof -i :3434

# Kill the process or change port in docker-compose.yml
```

### Container Won't Start
```bash
# Check logs
docker-compose logs

# Rebuild from scratch
docker-compose down
docker-compose build --no-cache
docker-compose up
```

### Database Issues
```bash
# Re-seed the database
docker-compose exec fundmgr-app python seed_data.py

# Or remove and recreate
docker-compose down -v
docker-compose up
```

### Code Changes Not Reflecting (Development Mode)
```bash
# Restart the container
docker-compose restart

# Or rebuild
docker-compose -f docker-compose.dev.yml up --build
```

### View Container Status
```bash
docker-compose ps
docker stats
```

---

## First Time Setup Checklist

1. ✅ Navigate to project: `cd /Users/rsk/Documents/GitHub/fundmgr`
2. ✅ Start Docker: `docker-compose -f docker-compose.dev.yml up`
3. ✅ Wait for "Application startup complete" in logs
4. ✅ Open browser: http://localhost:3434
5. ✅ Login with admin/admin123
6. ✅ Verify database is seeded (you should see 10 months)

---

## Environment Variables (Optional)

Create a `.env` file in the project root if you need custom settings:

```bash
# .env file (optional)
SECRET_KEY=your-secret-key-here
```

---

## Data Persistence

- Database is stored in `./data/fundmgr.db`
- This directory is mounted as a volume, so data persists between container restarts
- To reset everything: `docker-compose down -v` (WARNING: deletes data)

---

## Summary

**Quickest way to start:**
```bash
cd /Users/rsk/Documents/GitHub/fundmgr
docker-compose -f docker-compose.dev.yml up
```

**Then open:** http://localhost:3434

That's it! 🚀

