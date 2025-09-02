from utils.old_migrator import OldRecordMigrator

if __name__ == "__main__":
    migrator = OldRecordMigrator(
        db_file="/qbox_data.db"
    )
    migrator.run_migration()