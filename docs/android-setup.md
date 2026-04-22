# Android Setup Guide

Run duoVoiceCoach on an Android device using ngrok to expose the local backend over HTTPS (required for mic access on Android Chrome).

## Prerequisites

- Backend dependencies installed: `uv sync`
- Frontend built: `cd frontend && npm run build`
- ngrok installed: https://ngrok.com/download (free account, no paid plan needed)

## Steps

### 1. Build the frontend

```bash
cd frontend
npm run build
cd ..
```

This creates `frontend/dist/` which the backend serves as static files.

### 2. Start the backend

```bash
uv run uvicorn backend.main:app --host 0.0.0.0 --port 8001
```

`--host 0.0.0.0` makes the server reachable on the network (not just localhost).

### 3. Start ngrok

In a second terminal:

```bash
ngrok http 8001
```

ngrok will print a line like:

```
Forwarding  https://abc123.ngrok-free.app -> http://localhost:8001
```

Copy the `https://...` URL.

### 4. Open on Android

1. Open Android Chrome.
2. Navigate to the ngrok HTTPS URL.
3. To install as a PWA: tap the browser menu → "Add to Home screen".

## Notes

- Both laptop and phone must be running (the phone hits the laptop's ngrok tunnel).
- The ngrok URL changes each session on the free plan — you'll need to copy a new URL each time.
- If mic access is denied on first visit, go to Chrome site settings and grant microphone permission for the ngrok URL.
- Rebuild the frontend (`npm run build`) after any UI changes before testing on Android.
