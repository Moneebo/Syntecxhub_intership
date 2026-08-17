#!/usr/bin/env python3
"""
Folder Backup / Sync Tool
==========================
Syntecxhub Internship - Python Programming - Project 3

A command-line utility that backs up a folder to another location (local
folder or mounted drive) using timestamped, incremental backups. Files that
are unchanged since the last backup are hard-linked instead of copied, so
repeated backups are fast and space-efficient -- the same technique used by
tools like Time Machine and rsnapshot (rsync --link-dest).

Features
--------
* Timestamped backup folders: backup_YYYYMMDD_HHMMSS
* Incremental backups: unchanged files are hard-linked, changed/new files
  are copied. Falls back to a plain copy automatically if hard links aren't
  supported (e.g. destination is on a different filesystem/drive).
* --dry-run: preview exactly what would happen without touching any files
* --compress: zip up the finished backup and remove the loose folder
* --rotate N: keep only the N most recent backups, delete the rest
* Logging to console and to a log file, with a --verbose switch
* Only uses the Python standard library -- nothing to pip install

Usage
-----
    python backup_tool.py -s ./my_folder -d /mnt/backup_drive
    python backup_tool.py -s ./my_folder -d ./backups --compress --rotate 5
    python backup_tool.py -s ./my_folder -d ./backups --dry-run -v
"""

from __future__ import annotations

import argparse
import logging
import os
import shutil
import sys
import time
import zipfile
from datetime import datetime
from pathlib import Path

BACKUP_PREFIX = "backup_"
# Microsecond resolution avoids two backups colliding on the same folder
# name if the tool is ever run twice within the same second.
TIMESTAMP_FMT = "%Y%m%d_%H%M%S_%f"


# ---------------------------------------------------------------------------
# Stats / helpers
# ---------------------------------------------------------------------------
class BackupStats:
    """Tracks what happened during a backup run for the final summary."""

    def __init__(self) -> None:
        self.files_copied = 0
        self.files_linked = 0
        self.files_failed = 0
        self.dirs_created = 0
        self.bytes_copied = 0
        self.bytes_linked = 0
        self.start_time = time.time()

    def elapsed(self) -> float:
        return time.time() - self.start_time

    def summary(self) -> str:
        return (
            f"copied {self.files_copied} file(s) ({human_size(self.bytes_copied)}), "
            f"linked {self.files_linked} unchanged file(s) "
            f"(saved {human_size(self.bytes_linked)}), "
            f"{self.files_failed} failure(s), "
            f"{self.dirs_created} directorie(s), "
            f"in {self.elapsed():.2f}s"
        )


def human_size(num_bytes: float) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if num_bytes < 1024:
            return f"{num_bytes:.1f}{unit}"
        num_bytes /= 1024
    return f"{num_bytes:.1f}PB"


def setup_logging(log_file: str | None, verbose: bool) -> logging.Logger:
    logger = logging.getLogger("backup_tool")
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()
    logger.propagate = False

    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S")

    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.DEBUG if verbose else logging.INFO)
    console.setFormatter(fmt)
    logger.addHandler(console)

    if log_file:
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(fmt)
        logger.addHandler(file_handler)

    return logger


# ---------------------------------------------------------------------------
# Backup discovery
# ---------------------------------------------------------------------------
def _parse_backup_timestamp(name: str) -> datetime | None:
    """Return the datetime encoded in a backup_* folder/zip name, or None."""
    base = name[:-4] if name.endswith(".zip") else name
    if not base.startswith(BACKUP_PREFIX):
        return None
    try:
        return datetime.strptime(base[len(BACKUP_PREFIX):], TIMESTAMP_FMT)
    except ValueError:
        return None


def list_backups(destination: Path) -> list[Path]:
    """All valid backup folders/zips in destination, oldest first."""
    if not destination.exists():
        return []
    found = [p for p in destination.iterdir() if _parse_backup_timestamp(p.name)]
    found.sort(key=lambda p: _parse_backup_timestamp(p.name))
    return found


def find_previous_backup(destination: Path) -> Path | None:
    """Most recent *uncompressed* backup folder, used as the link-dest for
    incremental backups. Compressed (zip) backups can't be used this way."""
    folders = [p for p in list_backups(destination) if p.is_dir()]
    return folders[-1] if folders else None


# ---------------------------------------------------------------------------
# Core backup logic
# ---------------------------------------------------------------------------
def files_unchanged(src_file: Path, prev_file: Path) -> bool:
    """Cheap unchanged check: same size and same mtime (to the second)."""
    try:
        s1, s2 = src_file.stat(), prev_file.stat()
        return s1.st_size == s2.st_size and int(s1.st_mtime) == int(s2.st_mtime)
    except OSError:
        return False


def backup_tree(
    source: Path,
    current_backup: Path,
    previous_backup: Path | None,
    dry_run: bool,
    logger: logging.Logger,
    stats: BackupStats,
) -> None:
    for root, _dirs, files in os.walk(source):
        rel_root = Path(root).relative_to(source)
        target_dir = current_backup / rel_root
        prev_dir = (previous_backup / rel_root) if previous_backup else None

        if not dry_run:
            target_dir.mkdir(parents=True, exist_ok=True)
        stats.dirs_created += 1
        logger.debug(f"DIR   {rel_root}")

        for filename in files:
            src_file = Path(root) / filename
            dest_file = target_dir / filename
            prev_file = (prev_dir / filename) if prev_dir else None
            rel_path = rel_root / filename

            try:
                size = src_file.stat().st_size
            except OSError as exc:
                stats.files_failed += 1
                logger.error(f"SKIP  {rel_path}: cannot read source ({exc})")
                continue

            unchanged = bool(
                prev_file and prev_file.exists() and files_unchanged(src_file, prev_file)
            )

            try:
                if unchanged:
                    if dry_run:
                        logger.info(f"LINK  {rel_path} (unchanged, dry-run)")
                    else:
                        try:
                            os.link(prev_file, dest_file)
                        except OSError:
                            # Different filesystem / hard links unsupported -> plain copy
                            shutil.copy2(src_file, dest_file)
                        logger.debug(f"LINK  {rel_path}")
                    stats.files_linked += 1
                    stats.bytes_linked += size
                else:
                    if dry_run:
                        logger.info(f"COPY  {rel_path} ({human_size(size)}, dry-run)")
                    else:
                        shutil.copy2(src_file, dest_file)
                        logger.debug(f"COPY  {rel_path} ({human_size(size)})")
                    stats.files_copied += 1
                    stats.bytes_copied += size
            except (OSError, shutil.Error) as exc:
                stats.files_failed += 1
                logger.error(f"FAIL  {rel_path}: {exc}")


def compress_backup(backup_dir: Path, logger: logging.Logger, dry_run: bool) -> Path:
    zip_path = backup_dir.with_suffix(".zip")
    if dry_run:
        logger.info(f"Would compress {backup_dir.name} -> {zip_path.name} and remove the folder")
        return zip_path

    logger.info(f"Compressing {backup_dir.name} ...")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in backup_dir.rglob("*"):
            if file.is_file():
                zf.write(file, arcname=file.relative_to(backup_dir.parent))
    shutil.rmtree(backup_dir)
    logger.info(f"Compressed -> {zip_path.name} ({human_size(zip_path.stat().st_size)}), removed folder")
    return zip_path


def rotate_backups(destination: Path, keep: int, logger: logging.Logger, dry_run: bool) -> None:
    backups = list_backups(destination)  # oldest first
    excess = len(backups) - keep
    if excess <= 0:
        logger.info(f"Rotation: {len(backups)} backup(s) present, keep={keep}, nothing to remove")
        return

    for item in backups[:excess]:
        if dry_run:
            logger.info(f"Would remove old backup: {item.name}")
            continue
        if item.is_dir():
            shutil.rmtree(item)
        else:
            item.unlink()
        logger.info(f"Removed old backup: {item.name}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="backup_tool.py",
        description="Back up a folder to another location with incremental, timestamped backups.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python backup_tool.py -s ./data -d /mnt/backup_drive\n"
            "  python backup_tool.py -s ./data -d ./backups --compress --rotate 5\n"
            "  python backup_tool.py -s ./data -d ./backups --dry-run -v\n"
        ),
    )
    parser.add_argument("-s", "--source", required=True, help="Source folder to back up")
    parser.add_argument("-d", "--destination", required=True, help="Destination folder (local path or mounted drive)")
    parser.add_argument("--dry-run", action="store_true", help="Preview actions without changing anything on disk")
    parser.add_argument("--compress", action="store_true", help="Zip the finished backup and remove the loose folder")
    parser.add_argument("--rotate", type=int, metavar="N", help="Keep only the N most recent backups")
    parser.add_argument("--full", action="store_true", help="Force a full backup (skip incremental hard-linking)")
    parser.add_argument("--log-file", help="Log file path (default: <destination>/backup.log)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose (debug-level) console output")
    return parser


def main() -> None:
    args = build_parser().parse_args()

    source = Path(args.source).expanduser().resolve()
    destination = Path(args.destination).expanduser().resolve()

    if not source.is_dir():
        print(f"Error: source folder does not exist: {source}", file=sys.stderr)
        sys.exit(1)

    log_file = None if args.dry_run else (args.log_file or str(destination / "backup.log"))
    logger = setup_logging(log_file, args.verbose)

    logger.info("=" * 70)
    logger.info(f"Source:      {source}")
    logger.info(f"Destination: {destination}")
    if args.dry_run:
        logger.info("Mode:        DRY RUN (console log only, nothing will be written)")

    try:
        if not args.dry_run:
            destination.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        logger.error(f"Cannot access or create destination '{destination}': {exc}")
        sys.exit(1)

    previous_backup = None if args.full else find_previous_backup(destination)
    if previous_backup:
        logger.info(f"Incremental base: {previous_backup.name}")
    else:
        logger.info("No usable previous backup found -- this will be a full backup")

    timestamp = datetime.now().strftime(TIMESTAMP_FMT)
    current_backup = destination / f"{BACKUP_PREFIX}{timestamp}"

    if not args.dry_run:
        current_backup.mkdir(parents=True, exist_ok=True)

    stats = BackupStats()
    backup_tree(source, current_backup, previous_backup, args.dry_run, logger, stats)
    logger.info(f"Backup {current_backup.name}: {stats.summary()}")

    if args.compress:
        compress_backup(current_backup, logger, args.dry_run)

    if args.rotate is not None:
        if args.rotate < 1:
            logger.warning("--rotate must be at least 1; skipping rotation")
        else:
            rotate_backups(destination, args.rotate, logger, args.dry_run)

    logger.info("Done." if stats.files_failed == 0 else f"Done with {stats.files_failed} file error(s).")
    logger.info("=" * 70)

    sys.exit(0 if stats.files_failed == 0 else 2)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nBackup interrupted by user.", file=sys.stderr)
        sys.exit(130)
