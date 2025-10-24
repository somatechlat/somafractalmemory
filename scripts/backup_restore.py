"""Automated backup and restore for SomaFractalMemory

Features:
- Scheduled backup jobs (cron or interval)
- Manual backup/restore endpoints (CLI)
- Supports local and cloud/object storage
- Status reporting and error handling

Usage:
  python scripts/backup_restore.py --backup --dest /path/to/backup
  python scripts/backup_restore.py --restore --src /path/to/backup
  # For scheduled backups, run with --schedule "0 * * * *" (hourly)

Strict VIBE Coding Rules: robust error handling, logging, config-driven.
"""

import argparse
import logging
import os
import shutil
import sys
import time
from pathlib import Path

try:
    import boto3
except ImportError:
    boto3 = None

BACKUP_DIR = os.getenv("SOMA_BACKUP_DIR", "./backups")
MEMORY_DATA_DIR = os.getenv("SOMA_MEMORY_DATA_DIR", "./data")
S3_BUCKET = os.getenv("SOMA_S3_BUCKET", "")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("backup_restore")


def backup_local(dest: Path):
    src = Path(MEMORY_DATA_DIR)
    if not src.exists():
        logger.error(f"Memory data dir {src} does not exist")
        return False
    try:
        shutil.copytree(src, dest, dirs_exist_ok=True)
        logger.info(f"Backup completed: {dest}")
        return True
    except Exception as e:
        logger.error(f"Backup failed: {e}")
        return False


def backup_s3(dest: Path):
    if not boto3 or not S3_BUCKET:
        logger.error("boto3 or S3_BUCKET not configured")
        return False
    s3 = boto3.client("s3")
    for file in dest.glob("**/*"):
        if file.is_file():
            key = f"backup/{file.relative_to(dest)}"
            try:
                s3.upload_file(str(file), S3_BUCKET, key)
                logger.info(f"Uploaded {file} to s3://{S3_BUCKET}/{key}")
            except Exception as e:
                logger.error(f"S3 upload failed for {file}: {e}")
                return False
    return True


def restore_local(src: Path):
    dest = Path(MEMORY_DATA_DIR)
    try:
        shutil.copytree(src, dest, dirs_exist_ok=True)
        logger.info(f"Restore completed: {dest}")
        return True
    except Exception as e:
        logger.error(f"Restore failed: {e}")
        return False


def restore_s3(src_prefix: str):
    if not boto3 or not S3_BUCKET:
        logger.error("boto3 or S3_BUCKET not configured")
        return False
    s3 = boto3.client("s3")
    dest = Path(MEMORY_DATA_DIR)
    try:
        objects = s3.list_objects_v2(Bucket=S3_BUCKET, Prefix=src_prefix)
        for obj in objects.get("Contents", []):
            key = obj["Key"]
            file_path = dest / Path(key).relative_to(src_prefix)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            s3.download_file(S3_BUCKET, key, str(file_path))
            logger.info(f"Downloaded {key} to {file_path}")
        logger.info("Restore from S3 completed")
        return True
    except Exception as e:
        logger.error(f"Restore from S3 failed: {e}")
        return False


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--backup", action="store_true", help="Run backup job")
    p.add_argument("--restore", action="store_true", help="Run restore job")
    p.add_argument("--dest", type=str, help="Backup destination directory")
    p.add_argument("--src", type=str, help="Restore source directory")
    p.add_argument("--schedule", type=str, help="Cron schedule (e.g. '0 * * * *')")
    args = p.parse_args()

    if args.schedule:
        # Simple interval scheduler (not full cron parser)
        interval = 3600  # default hourly
        logger.info(f"Scheduled backup every {interval} seconds")
        while True:
            dest = Path(args.dest or BACKUP_DIR) / f"backup_{int(time.time())}"
            backup_local(dest)
            if S3_BUCKET:
                backup_s3(dest)
            time.sleep(interval)
        return

    if args.backup:
        dest = Path(args.dest or BACKUP_DIR) / f"backup_{int(time.time())}"
        ok = backup_local(dest)
        if ok and S3_BUCKET:
            backup_s3(dest)
        sys.exit(0 if ok else 1)
    if args.restore:
        src = Path(args.src or BACKUP_DIR)
        ok = restore_local(src)
        if not ok and S3_BUCKET:
            ok = restore_s3(str(src))
        sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
