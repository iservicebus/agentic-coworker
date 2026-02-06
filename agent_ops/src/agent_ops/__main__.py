#!/usr/bin/env python3
"""Main CLI entry point for agent_ops package."""

import sys
import argparse
from typing import Optional


def run_backup(backup_path: Optional[str] = None, tenant_name: Optional[str] = None):
    """Run the backup command."""
    # Modify sys.argv to pass parameters to backup/main.py
    original_argv = sys.argv.copy()

    # Set up arguments for backup module
    sys.argv = ['backup']
    if backup_path:
        sys.argv.append(backup_path)
    if tenant_name:
        sys.argv.append(tenant_name)

    try:
        # Import and run the backup module
        from agent_ops.backup.main import backup_all
        backup_all()
    finally:
        # Restore original argv
        sys.argv = original_argv


def run_init_db():
    """Run the init-db command."""
    original_argv = sys.argv.copy()
    sys.argv = ['init-db']
    try:
        from agent_ops.init.main import init_db
        init_db()
    finally:
        sys.argv = original_argv


def run_init_defaults():
    """Run the init-defaults command."""
    original_argv = sys.argv.copy()
    sys.argv = ['init-defaults']
    try:
        from agent_ops.init.main import init_with_defaults
        init_with_defaults()
    finally:
        sys.argv = original_argv


def run_init_seed(seed_path: Optional[str] = None):
    """Run the init-seed command."""
    original_argv = sys.argv.copy()
    sys.argv = ['init-seed']
    if seed_path:
        sys.argv.append(seed_path)
    try:
        from agent_ops.init.main import init_with_seed
        init_with_seed()
    finally:
        sys.argv = original_argv


def run_load_seed(seed_path: Optional[str] = None):
    """Run the load-seed command."""
    original_argv = sys.argv.copy()
    sys.argv = ['load-seed']
    if seed_path:
        sys.argv.append(seed_path)
    try:
        from agent_ops.seed.main import seed_all
        seed_all()
    finally:
        sys.argv = original_argv


def run_restore(restore_from: Optional[str] = None, tenant_name: Optional[str] = None):
    """Run the restore command."""
    original_argv = sys.argv.copy()
    sys.argv = ['restore']
    if restore_from:
        sys.argv.append(restore_from)
    if tenant_name:
        sys.argv.append(tenant_name)
    try:
        from agent_ops.restore.main import restore_all
        restore_all()
    finally:
        sys.argv = original_argv


def run_update(update_folder: Optional[str] = None):
    """Run the update command."""
    original_argv = sys.argv.copy()
    sys.argv = ['update']
    if update_folder:
        sys.argv.append(update_folder)
    try:
        from agent_ops.update.main import process_update_folder
        default_update_folder = "../data/update_data"
        folder_path = update_folder if update_folder else default_update_folder
        process_update_folder(folder_path)
    finally:
        sys.argv = original_argv


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Agent Operations CLI',
        prog='agent_ops'
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Backup command
    backup_parser = subparsers.add_parser('backup', help='Run backup operations')
    backup_parser.add_argument(
        '--backup-path',
        type=str,
        help='Path where backup files will be stored',
        default=None
    )
    backup_parser.add_argument(
        '--tenant-name',
        type=str,
        help='Specific tenant name to backup (optional, defaults to all tenants)',
        default=None
    )

    # Init-db command
    init_db_parser = subparsers.add_parser('init-db', help='Initialize database schema only')

    # Init-defaults command
    init_defaults_parser = subparsers.add_parser(
        'init-defaults',
        help='Initialize database schema and restore default data'
    )

    # Init-seed command
    init_seed_parser = subparsers.add_parser(
        'init-seed',
        help='Initialize database schema and load seed data'
    )
    init_seed_parser.add_argument(
        '--seed-path',
        type=str,
        help='Path to seed data directory (default: ../data/seed_data)',
        default=None
    )

    # Load-seed command
    load_seed_parser = subparsers.add_parser(
        'load-seed',
        help='Load seed data into existing database'
    )
    load_seed_parser.add_argument(
        '--seed-path',
        type=str,
        help='Path to seed data directory (default: ../data/seed_data)',
        default=None
    )

    # Restore command
    restore_parser = subparsers.add_parser('restore', help='Restore data from backup')
    restore_parser.add_argument(
        '--restore-from',
        type=str,
        help='Path to backup directory (default: ../data/backup_data/default_restore)',
        default=None
    )
    restore_parser.add_argument(
        '--tenant-name',
        type=str,
        help='Specific tenant name to restore (optional)',
        default=None
    )

    # Update command
    update_parser = subparsers.add_parser('update', help='Update app keys and auth providers from data files')
    update_parser.add_argument(
        '--update-folder',
        type=str,
        help='Path to folder containing update data files (default: ../data/update_data)',
        default=None
    )

    args = parser.parse_args()

    if args.command == 'backup':
        run_backup(args.backup_path, args.tenant_name)
    elif args.command == 'init-db':
        run_init_db()
    elif args.command == 'init-defaults':
        run_init_defaults()
    elif args.command == 'init-seed':
        run_init_seed(args.seed_path)
    elif args.command == 'load-seed':
        run_load_seed(args.seed_path)
    elif args.command == 'restore':
        run_restore(args.restore_from, args.tenant_name)
    elif args.command == 'update':
        run_update(args.update_folder)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
