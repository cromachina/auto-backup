import argparse
from pathlib import Path
import shutil
import re
import os
from datetime import datetime, timedelta
import time
import logging

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
import schedule

logging.basicConfig(
    format='[%(asctime)s][%(levelname)s] %(message)s',
    level=logging.INFO,
)

def try_get_file_time(file):
    try:
        return datetime.fromtimestamp(float(file.suffixes[0][1:]) / 1_000_000_000)
    except:
        return datetime.fromtimestamp(os.path.getmtime(file))

def remove_backups_by_time(config):
    if not config.remove_by_time:
        return
    if not config.backup_directory.exists():
        return
    limit = datetime.now() - config.old_file_limit_days
    for root, _, files in os.walk(config.backup_directory):
        for file in files:
            file = Path(root) / file
            if try_get_file_time(file) < limit:
                file.unlink(missing_ok=True)
                logging.debug(f'removed old {file}')

def get_backup_root(config, src_path:Path):
    return config.backup_directory / src_path.relative_to(config.scan_directory).parent

def remove_backups_by_count(config, src_path:Path):
    matcher = re.compile(f'{src_path.stem}\\.\\d+\\{src_path.suffix}')
    sub_backup_dir = get_backup_root(config, src_path)
    files = os.listdir(sub_backup_dir)
    files = [file for file in files if matcher.match(file)]
    files.sort()
    files = files[:-config.backup_limit]
    for file in files:
        file = Path(sub_backup_dir) / file
        logging.debug(f'removed old {file}')
        file.unlink(missing_ok=True)

def backup_file(config, src_path:Path):
    timestamp = time.time_ns()
    backup_path = get_backup_root(config, src_path) / f'{src_path.stem}.{timestamp}{src_path.suffix}'
    temp_path = backup_path.with_name(f'{backup_path.name}.tmp')
    os.makedirs(backup_path.parent, exist_ok=True)
    shutil.move(src_path, backup_path)
    shutil.copy2(backup_path, temp_path)
    if src_path.exists():
        temp_path.unlink(missing_ok=True)
    else:
        shutil.move(temp_path, src_path)
    logging.info(f'backup {src_path} -> {backup_path}')

class EventHandler(FileSystemEventHandler):
    def __init__(self, config) -> None:
        super().__init__()
        self.config = config

    def on_closed(self, event):
        if self.config.file_match.match(event.src_path) is None:
            return
        src_path = Path(event.src_path)
        if src_path.is_relative_to(self.config.backup_directory):
            return
        backup_file(self.config, src_path)
        remove_backups_by_count(self.config, src_path)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--old-file-limit-days', type=lambda s: timedelta(days=float(float(s))), default=7)
    parser.add_argument('--remove-by-time', default=False, action=argparse.BooleanOptionalAction)
    parser.add_argument('--backup-limit', type=int, default=6)
    parser.add_argument('--recursive', default=True, action=argparse.BooleanOptionalAction)
    parser.add_argument('--scan-directory', type=Path, default='/home/cro/aux/art')
    parser.add_argument('--backup-directory', type=Path, default='/home/cro/aux/backups')
    parser.add_argument('--file-match', type=re.compile, default='.*\\.sai2')
    config = parser.parse_args()

    schedule.every().hour.do(lambda: remove_backups_by_time(config))
    schedule.run_all()
    observer = Observer()
    observer.schedule(EventHandler(config), str(config.scan_directory), recursive=config.recursive)
    observer.start()
    try:
        while observer.is_alive():
            schedule.run_pending()
            observer.join(1)
    finally:
        observer.stop()
        observer.join()

if __name__ == '__main__':
    main()