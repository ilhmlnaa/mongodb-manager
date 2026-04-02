<div align="center">

<img src="https://giffiles.alphacoders.com/243/243.gif" alt="Mongo Manager" width="420" height="220" style="border-radius: 10px;" />

<p>
  <img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white" alt="python">
  <img src="https://img.shields.io/badge/Textual-TUI-5B3DF5?style=flat-square" alt="textual">
  <img src="https://img.shields.io/badge/MongoDB-Tools-47A248?style=flat-square&logo=mongodb&logoColor=white" alt="mongodb">
  <img src="https://img.shields.io/badge/Docker-Supported-2496ED?style=flat-square&logo=docker&logoColor=white" alt="docker">
</p>

<p>
  <a href="../../issues">
    <img src="https://img.shields.io/badge/Report_Bug-DC143C?style=for-the-badge&logo=github&logoColor=white" alt="bug">
  </a>
  <a href="../../issues">
    <img src="https://img.shields.io/badge/Request_Feature-4285F4?style=for-the-badge&logo=github&logoColor=white" alt="feature">
  </a>
</p>

</div>

<hr />

# 🗂️ Mongo Manager

> **A TUI, CLI, and Web tool for MongoDB backup/restore/sync, scheduled backups, and ZIP uploads to S3 (Cloudflare R2).**

Mongo Manager is built to simplify day-to-day MongoDB operations: fast backups, controlled restores, server-to-server sync, and schedule automation with ready-to-use cron lines.

---

## 📑 Table of Contents

- [Features](#-features)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Prerequisites](#-prerequisites)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Running the Application](#-running-the-application)
- [CLI Reference](#-cli-reference)
- [Scheduled Backups Guide](#-scheduled-backups-guide)
- [Docker](#-docker)
- [Troubleshooting](#-troubleshooting)

---

## ✨ Features

- **📦 MongoDB Backup**
  - Backup all databases or a specific database.
  - Optional ZIP compression.
  - Optional ZIP upload to S3 (Cloudflare R2).
- **📥 MongoDB Restore**
  - Restore dumps from backup folders.
- **🔄 Database Synchronization**
  - Dump from a source server and restore to a target server.
- **🧭 Web Mode**
  - Run the Textual UI in a browser via `textual-serve`.
- **⏱️ Scheduled Backups (TUI)**
  - Schedule types: daily, weekly, monthly, quarterly, custom cron.
  - Saves schedules to `backup_schedules.json`.
  - Generates cron lines automatically.
- **🛡️ ZIP/S3 Validation**
  - `Upload ZIP to S3` can only be enabled if `Compress to ZIP` is enabled.
- **🗒️ Consistent Top Log Panel**
  - Backup, schedule, and manage-schedules screens show process logs at the top.

---

## 🛠 Tech Stack

- **Language**: [Python 3.11+](https://www.python.org/)
- **TUI Framework**: [Textual](https://github.com/Textualize/textual)
- **Web Bridge**: [textual-serve](https://github.com/Textualize/textual-serve)
- **MongoDB Driver**: [PyMongo](https://pymongo.readthedocs.io/)
- **Object Storage SDK**: [boto3](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)
- **Environment Loader**: [python-dotenv](https://github.com/theskumar/python-dotenv)

---

## 📁 Project Structure

```text
mongo-manager/
├── main.py
├── requirements.txt
├── servers.json
├── .env
├── CRON_SETUP.md
├── Dockerfile
├── core/
│   ├── config.py
│   ├── database.py
│   ├── storage.py
│   ├── tui.py
│   └── utils.py
├── mongo-tools/
│   ├── linux/bin/
│   └── windows/bin/
└── mongodb-backup/
```

---

## ✅ Prerequisites

Make sure you have:

- **Python** `>= 3.11`
- **pip**
- **MongoDB Database Tools** (`mongodump`, `mongorestore`)
  - You can use the bundled `mongo-tools/` folder or install them globally.

---

## 📦 Installation

1. Go to the project root:

```bash
cd mongo-manager
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Configure `.env`:

```dotenv
MONGO_MANAGER_WEB_HOST=127.0.0.1
MONGO_MANAGER_WEB_PORT=8000

S3_ENDPOINT=https://your-account-id.r2.cloudflarestorage.com
S3_ACCESS_KEY=your-access-key
S3_SECRET_KEY=your-secret-key
S3_BUCKET_NAME=your-bucket-name
```

4. Configure `servers.json` with MongoDB aliases:

```json
{
  "local": "mongodb://localhost:27017",
  "production": "mongodb+srv://<user>:<pass>@cluster.mongodb.net/"
}
```

---

## ⚙️ Configuration

### Environment Variables

- `MONGO_MANAGER_WEB_HOST`: default host for `web` mode.
- `MONGO_MANAGER_WEB_PORT`: default port for `web` mode.
- `S3_ENDPOINT`: S3/R2 endpoint.
- `S3_ACCESS_KEY`: S3/R2 access key.
- `S3_SECRET_KEY`: S3/R2 secret key.
- `S3_BUCKET_NAME`: destination bucket name.

### Important Files

- `servers.json`: MongoDB server aliases.
- `backup_schedules.json`: scheduled backup definitions saved from the TUI.
- `mongodb-backup/`: backup output directory.

---

## 🚀 Running the Application

### 1) TUI Mode (default)

```bash
python main.py
```

### 2) Web Mode (browser)

```bash
python main.py web
```

Override host/port if needed:

```bash
python main.py web --host 127.0.0.1 --port 8000
```

### 3) CLI Backup Mode

```bash
python main.py backup <SERVER_ALIAS> --db all --zip --s3
```

---

## 📚 CLI Reference

### Command: `backup`

```bash
python main.py backup <server> [--db DB_NAME] [--out PATH] [--zip] [--s3]
```

Options:

- `<server>`: server alias defined in `servers.json`.
- `--db`: database name, default is `all`.
- `--out`: custom output folder path.
- `--zip`: compress dump into ZIP.
- `--s3`: upload ZIP to S3/R2 (effective only with `--zip`).

### Command: `web`

```bash
python main.py web [--host HOST] [--port PORT]
```

Options:

- `--host`: host bind address (default from `MONGO_MANAGER_WEB_HOST`).
- `--port`: port number (default from `MONGO_MANAGER_WEB_PORT`).

---

## ⏱️ Scheduled Backups Guide

From the main menu, open **Schedule Backup** and set:

- Server + Database
- Schedule type:
  - `Every Day`
  - `Every Week`
  - `Every Month`
  - `Every 3 Months`
  - `Custom Cron`
- Time (`HH:MM`) for non-custom schedules
- Cron expression for `Custom Cron` (5 fields)

When you click `Save`, the app will:

- Store configuration in `config-data/backup_schedules.json`
- Generate a cron expression
- Show a ready-to-use cron line

### Manage Schedules

The **Manage Schedules** menu allows you to:

- Select schedule entries from a dropdown
- View full details (server, db, cron, command)
- Delete selected schedules
- Monitor operations from the top log panel

### Important S3 Rule

- S3 upload **requires** ZIP compression.
- If `Compress to ZIP` is disabled, `Upload ZIP to S3` is automatically disabled.

---

## 🐳 Docker

### Build Image

```bash
docker build -t mongo-manager .
```

### Run Container

```bash
docker run --rm -p 8000:8000 --env-file .env mongo-manager
```

### Run with Docker Compose (Recommended for persistent data)

Use bind volumes for both configs and backups:

```bash
docker compose up -d --build
```

This project includes `docker-compose.yml` with:

- `./config-data:/app/config-data` for JSON configs (`servers.json`, `backup_schedules.json`, `app_settings.json`)
- `./mongodb-backup:/app/mongodb-backup` for backup output

For Linux hosts, set UID/GID so container file permissions match your user:

```bash
export UID=$(id -u)
export GID=$(id -g)
docker compose up -d --build
```

Default container command:

```bash
python main.py web
```

---

## 🧯 Troubleshooting

- **Web only shows intro/logo screen**
  - Use `127.0.0.1` for local browser access.
- **`mongodump` / `mongorestore` not found**
  - Ensure MongoDB Database Tools are in `PATH`, or use binaries in `mongo-tools/`.
- **S3 upload fails**
  - Verify all S3 variables in `.env`.
  - Ensure `Compress to ZIP` is enabled.
- **Permission denied on `/app/config-data`**
  - Use the provided `docker-compose.yml` and set `UID`/`GID` on Linux.
- **Custom schedule is rejected**
  - Ensure the cron expression has exactly 5 fields.

---

## 🙌 Contributing

Feel free to open issues for bugs/features or submit pull requests.
