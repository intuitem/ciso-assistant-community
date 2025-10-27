# Clone Instance Management Command

## Overview

The `clone_instance` Django management command creates a complete copy of a CISO Assistant instance by copying both the SQLite database file and evidence attachments directory. This is useful for:

- **Creating backups** of your CISO Assistant instance
- **Setting up testing/staging environments** from production data
- **Migrating instances** to new servers or locations
- **Creating snapshots** before major updates or changes

## Prerequisites

- The command works with **SQLite databases only**
- For PostgreSQL databases, you must explicitly specify the source database file path
- The Django application must be properly configured

## Usage

### Basic Syntax

```bash
python manage.py clone_instance --dest-db <destination_db> --dest-attachments <destination_attachments>
```

### Command Options

| Option | Required | Description |
|--------|----------|-------------|
| `--source-db` | No | Path to source SQLite database (defaults to current database from Django settings) |
| `--dest-db` | **Yes** | Path to destination SQLite database |
| `--source-attachments` | No | Path to source attachments directory (defaults to MEDIA_ROOT from Django settings) |
| `--dest-attachments` | **Yes** | Path to destination attachments directory |
| `--force` | No | Overwrite destination files if they exist without prompting |

## Examples

### Example 1: Create a Backup (Using Defaults)

Creates a backup using the current database and attachments from Django settings:

```bash
python manage.py clone_instance \
  --dest-db /backups/ciso-assistant-backup-$(date +%Y%m%d).sqlite3 \
  --dest-attachments /backups/attachments-backup-$(date +%Y%m%d)
```

### Example 2: Clone with Custom Source Paths

Explicitly specify both source and destination paths:

```bash
python manage.py clone_instance \
  --source-db /opt/ciso/db/ciso-assistant.sqlite3 \
  --source-attachments /opt/ciso/db/attachments \
  --dest-db /backup/ciso-assistant.sqlite3 \
  --dest-attachments /backup/attachments
```

### Example 3: Force Overwrite Without Prompts

Use `--force` to skip confirmation prompts (useful for automated backups):

```bash
python manage.py clone_instance \
  --dest-db /backups/ciso-assistant.sqlite3 \
  --dest-attachments /backups/attachments \
  --force
```

### Example 4: Clone for Testing Environment

Create a copy of production data for testing:

```bash
python manage.py clone_instance \
  --source-db /prod/db/ciso-assistant.sqlite3 \
  --source-attachments /prod/db/attachments \
  --dest-db /test/db/ciso-assistant.sqlite3 \
  --dest-attachments /test/db/attachments
```

## How It Works

The command performs the following steps:

1. **Validation**
   - Verifies source database exists and is a valid SQLite file
   - Checks if destination files already exist
   - Prompts for confirmation (unless `--force` is used)

2. **Size Calculation**
   - Calculates database size
   - Calculates total attachments directory size
   - Displays summary before proceeding

3. **Database Cloning**
   - Creates destination directory if needed
   - Copies the SQLite database file
   - Validates the copied database integrity

4. **Attachments Cloning**
   - Recursively copies all files from source attachments directory
   - Preserves file metadata (timestamps, permissions)
   - Reports number of files copied

5. **Verification**
   - Confirms the cloned database is valid
   - Provides summary of cloned instance location

## Using the Cloned Instance

After cloning, to use the new instance:

1. **Update Django settings** or environment variables to point to the new database:
   ```bash
   export SQLITE_FILE=/backup/ciso-assistant.sqlite3
   ```

2. **Update attachments path** in settings:
   ```bash
   export LOCAL_STORAGE_DIRECTORY=/backup/attachments
   ```

3. **Restart the CISO Assistant service** to apply the changes

## Best Practices

### For Production Backups

1. **Stop the service** before cloning to ensure data consistency:
   ```bash
   systemctl stop ciso-assistant
   python manage.py clone_instance --dest-db /backup/db.sqlite3 --dest-attachments /backup/attachments
   systemctl start ciso-assistant
   ```

2. **Automate regular backups** with cron:
   ```bash
   # Daily backup at 2 AM
   0 2 * * * cd /app/backend && python manage.py clone_instance \
     --dest-db /backups/daily/ciso-$(date +\%Y\%m\%d).sqlite3 \
     --dest-attachments /backups/daily/attachments-$(date +\%Y\%m\%d) \
     --force
   ```

3. **Implement backup rotation** to manage disk space

### For Testing Environments

1. Clone production data to a test environment regularly
2. Sanitize sensitive data if needed
3. Keep test and production databases clearly labeled

### Storage Considerations

- Ensure sufficient disk space (at least 2x the combined size of database + attachments)
- Consider using compression for long-term archival
- Store backups on separate physical disks or remote storage

## Error Handling

The command includes comprehensive error handling:

- **Source database not found**: Verifies the source file exists before starting
- **Invalid SQLite database**: Validates the source is a proper SQLite file
- **Permission errors**: Checks write permissions to destination
- **Disk space issues**: Reports if copy operations fail
- **Database validation**: Verifies copied database integrity after cloning

## Limitations

- **SQLite only**: Designed for SQLite databases (for PostgreSQL, use `pg_dump` instead)
- **No authentication required**: This is a file-based operation, doesn't use API authentication
- **Single-server operation**: Both source and destination must be accessible from the same server
- **No incremental backups**: Always creates a full copy

## Troubleshooting

### "Source database not found"
- Check the path to your database file
- Verify Django settings are correct
- Use `--source-db` to explicitly specify the path

### "Permission denied"
- Ensure you have read permissions for source files
- Ensure you have write permissions for destination directories
- Run with appropriate user privileges

### "Copied database validation failed"
- Check disk space availability
- Verify source database is not corrupted
- Ensure no write locks on the database during copy

## Related Commands

- `python manage.py status` - Display instance statistics
- `python manage.py prune_auditlog` - Clean up audit logs
- Database-specific backup tools (e.g., `sqlite3 .backup`, `pg_dump`)

## Security Notes

- **Copied instances contain all data** including user credentials and sensitive information
- **Protect backup files** with appropriate file permissions
- **Encrypt backups** if storing on remote or shared storage
- **Regularly test restoration** from backups to ensure they work
