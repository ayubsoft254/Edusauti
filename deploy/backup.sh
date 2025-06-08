#!/bin/bash

# EduSauti Backup Script
# Creates backups of database and media files

set -e

BACKUP_DIR="/opt/edusauti-backups"
PROJECT_DIR="/opt/edusauti"
DATE=$(date +%Y%m%d-%H%M%S)
BACKUP_NAME="edusauti-backup-$DATE"

echo "💾 Creating backup: $BACKUP_NAME"

# Create backup directory
mkdir -p $BACKUP_DIR

cd $PROJECT_DIR

# Backup database
echo "🗄️ Backing up SQLite database..."
if [ -f "$PROJECT_DIR/sqlite_data/db.sqlite3" ]; then
    cp "$PROJECT_DIR/sqlite_data/db.sqlite3" "$BACKUP_DIR/$BACKUP_NAME-db.sqlite3"
else
    echo "Warning: SQLite database not found"
fi

# Backup media files
echo "📁 Backing up media files..."
sudo tar -czf "$BACKUP_DIR/$BACKUP_NAME-media.tar.gz" -C ./media . 2>/dev/null || true

# Backup environment files
echo "⚙️ Backing up configuration..."
cp .env.production "$BACKUP_DIR/$BACKUP_NAME-env.production"

# Create backup info file
echo "📝 Creating backup info..."
cat > "$BACKUP_DIR/$BACKUP_NAME-info.txt" << EOF
Backup created: $(date)
Application: EduSauti
Database: SQLite
Environment: Production
Docker Compose Version: $(docker-compose version --short)
EOF

# Compress all backup files
echo "🗜️ Compressing backup..."
cd $BACKUP_DIR
tar -czf "$BACKUP_NAME.tar.gz" "$BACKUP_NAME-"*
rm "$BACKUP_NAME-"*

# Clean up old backups (keep last 7 days)
echo "🧹 Cleaning up old backups..."
find $BACKUP_DIR -name "edusauti-backup-*.tar.gz" -mtime +7 -delete

echo "✅ Backup completed: $BACKUP_DIR/$BACKUP_NAME.tar.gz"
echo "📊 Backup size: $(du -h "$BACKUP_DIR/$BACKUP_NAME.tar.gz" | cut -f1)"
echo "📁 Available backups:"
ls -la $BACKUP_DIR/edusauti-backup-*.tar.gz
