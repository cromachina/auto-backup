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

old_file_limit = timedelta(weeks=1)
remove_by_time = False
backup_limit = 6
file_match = re.compile()
recursive = True
scan_directory = Path()
backup_directory = Path()

logging.basicConfig(
    format='[%(asctime)s][%(levelname)s] %(message)s',
    level=logging.INFO,
)

def try_get_file_time(file):
    try:
        return datetime.fromtimestamp(float(file.suffixes[0][1:]) / 1_000_000_000)
    except:
        return datetime.fromtimestamp(os.path.getmtime(file))

def remove_backups_by_time():
    if not remove_by_time:
        return
    if not backup_directory.exists():
        return
    limit = datetime.now() - old_file_limit
    for root, _, files in os.walk(backup_directory):
        for file in files:
            file = Path(root) / file
            if try_get_file_time(file) < limit:
                file.unlink(missing_ok=True)
                logging.debug(f'removed old {file}')

def get_backup_root(src_path:Path):
    return backup_directory / src_path.relative_to(scan_directory).parent

def remove_backups_by_count(src_path:Path):
    matcher = re.compile(f'{src_path.stem}\\.\\d+\\.*')
    sub_backup_dir = get_backup_root(src_path)
    files = os.listdir(sub_backup_dir)
    files = [file for file in files if matcher.match(file)]
    files.sort()
    files = files[:-backup_limit]
    for file in files:
        file = Path(sub_backup_dir) / file
        logging.debug(f'removed old {file}')
        file.unlink(missing_ok=True)

def backup_file(src_path:Path):
    timestamp = time.time_ns()
    backup_path = get_backup_root(src_path) / f'{src_path.stem}.{timestamp}{src_path.suffix}'
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
    def __init__(self) -> None:
        super().__init__()

    def on_closed(self, event):
        if file_match.match(event.src_path) is None:
            return
        src_path = Path(event.src_path)
        if src_path.is_relative_to(backup_directory):
            return
        backup_file(src_path)
        remove_backups_by_count(src_path)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--scan-directory', default='/home/cro/aux/art')
    parser.add_argument('--backup-directory', default='/home/cro/aux/backups')
    parser.add_argument('--file-match', default='.*\\.sai2')
    args = parser.parse_args()

    scan_directory = Path(args.scan_directory)
    backup_directory = Path(args.backup_directory)
    file_match = re.compile(args.file_match)

    schedule.every().hour.do(remove_backups_by_time)
    schedule.run_all()
    observer = Observer()
    observer.schedule(EventHandler(), str(scan_directory), recursive=recursive)
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