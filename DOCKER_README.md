# Docker Setup for Chit Fund Management System

## Quick Start

### Development Mode (Recommended for Development)

This mode mounts your code directory, so changes are reflected immediately:

```bash
docker-compose -f docker-compose.dev.yml up
```

### Production Mode

```bash
docker-compose up -d
```

## Access the Application

Once the container is running, access the application at:
- **URL**: `http://localhost:3434`
- **Admin Login**: 
  - Username: `admin`
  - Password: `admin123`

## First Time Setup

If this is the first time running, you need to seed the database:

```bash
# Enter the container
docker-compose exec fundmgr-app bash

# Run the seed script
python seed_data.py

# Exit the container
exit
```

Or run it in one command:

```bash
docker-compose exec fundmgr-app python seed_data.py
```

## Useful Commands

### View logs
```bash
docker-compose logs -f
```

### Stop the container
```bash
docker-compose down
```

### Rebuild the container
```bash
docker-compose build --no-cache
```

### Restart the container
```bash
docker-compose restart
```

### Access container shell
```bash
docker-compose exec fundmgr-app bash
```

## Data Persistence

The database is stored in the `data/` directory, which is mounted as a volume. This means your data persists even if you remove the container.

## Port Configuration

The application runs on port **3434** by default. You can change this in `docker-compose.yml`:

```yaml
ports:
  - "0.0.0.0:3434:3434"  # Change the first number to map to a different host port
```

## Troubleshooting

### Container won't start
- Check logs: `docker-compose logs`
- Ensure port 3434 is not already in use
- Try rebuilding: `docker-compose build --no-cache`

### Database errors
- Make sure the `data/` directory exists and is writable
- Run the seed script: `docker-compose exec fundmgr-app python seed_data.py`

### Code changes not reflecting
- In development mode, changes should reflect automatically
- If not, restart: `docker-compose restart`
- Check that volumes are mounted correctly

