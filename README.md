# AI Surveillance — Vision + Face Recognition

Autonomous surveillance system for isolated sites (agricultural warehouse, off-grid). An IP camera is polled every 30 seconds. Claude Vision detects people, AWS Rekognition tells authorized staff from intruders, and only unknown people trigger a Telegram alert with a photo.

## How it works

```
IP camera (RTSP/ONVIF)
        │  snapshot every 30s (09:00–23:00 test window, 18:00–06:00 in prod)
        ▼
Claude Vision ── no human ──► photo deleted
        │ human
        ▼
AWS Rekognition (authorized-employee collection)
        │ match ──► photo deleted, no alert
        │ unknown
        ▼
Telegram alert (photo) + n8n webhook ──► logs / downstream automation
```

## Features

- Automatic RTSP URL discovery via ONVIF (the camera rotates its stream token)
- Human detection with a structured description (gender, approximate age, clothing, activity)
- Authorized vs unknown person check with AWS Rekognition
- 5-minute anti-spam cooldown between alerts
- Time-window scheduling
- Auto-deletion of every photo without an intruder (nothing stored by default)
- Resilient loop: a dropped camera or network error never stops the script
- n8n webhook for downstream workflows

## Stack

Python · OpenCV · Anthropic API (Claude Vision) · AWS Rekognition (boto3) · ONVIF · Telegram Bot API · n8n

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env        # fill in your own values
python main.py
```

Requires an AWS Rekognition face collection named `employes-autorises`, indexed with the photos of authorized staff (with their written consent: biometric data is regulated under GDPR).

## Screenshots

| Terminal log | n8n workflow |
|---|---|
| ![log](screenshots/terminal.png) | ![n8n](screenshots/n8n.png) |

## Deployment target

Raspberry Pi 4 + solar panel + battery + Starlink for off-grid sites.

## Roadmap

- Systemd service for auto-start on the Raspberry Pi
- SMS fallback alert
- Web dashboard for detection history
- Two-way audio deterrent through the camera speaker

## Author

Thomas Plasseraud, [FlowsOps AI](https://flowsopsai.com)
