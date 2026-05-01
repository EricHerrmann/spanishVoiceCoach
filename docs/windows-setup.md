# duoVoiceCoach — Windows 11 Docker Setup

This guide packages the full app behind Docker Compose so a Windows 11 user only needs Docker Desktop and the repo checkout.

## Prerequisites

- Windows 11
- Docker Desktop installed and running
- Git installed
- A `.env` file at the repo root with the required provider keys and `DVC_SESSION_SECRET`

No local Python, Node.js, `uv`, or npm install is required for the packaged run path.

## First Run

From the repo root:

```bash
docker compose build
docker compose up
```

Open:

```text
http://localhost:8001
```

The container serves both the FastAPI backend and the built React frontend from the same origin.

## Run In Background

```bash
docker compose up -d
```

Stop it later with:

```bash
docker compose down
```

## Persistence

Session data is stored in the named Docker volume `duo_data`, mounted at `/data` in the container.

That means:

- saved sessions survive container restarts
- image rebuilds do not wipe session history
- deleting the volume will remove persisted app data

To inspect volumes:

```bash
docker volume ls
```

To remove the persisted app data intentionally:

```bash
docker compose down -v
```

## Updating After Pulling Changes

After pulling the latest repo changes:

```bash
docker compose build
docker compose up -d
```

## Useful Checks

Verify the health endpoint:

```bash
curl http://localhost:8001/health
```

Expected response:

```json
{"status":"ok"}
```

View logs:

```bash
docker compose logs -f
```

## Notes

- The image builds the frontend inside Docker; there is no separate `npm run build` step on Windows.
- `ffmpeg` is installed in the runtime image for Whisper support.
- If you are using local Whisper instead of `STT_PROVIDER=openai`, the first transcription may be slower while the model is prepared inside the container.
- If Docker Desktop is configured for Linux containers, no extra setup is needed; the provided image is Linux-based.

## Troubleshooting

### Port 8001 already in use

Stop the other process using port `8001`, or change the port mapping in `docker-compose.yml`.

### App starts but the browser shows a blank page

Run:

```bash
docker compose logs -f
```

Look for build/runtime errors from the `app` service.

### Sessions are not persisting

Confirm the container has `/data` mounted:

```bash
docker compose exec app sh -lc "ls -la /data"
```

If the app is writing somewhere else, confirm `DVC_DATA_DIR=/data` is present in the container environment:

```bash
docker compose exec app sh -lc "env | grep DVC_DATA_DIR"
```
