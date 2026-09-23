class CacheDBRouter:
    """Routes the login-throttle cache table to CACHE_DB_PATH's SQLite file
    when configured. Only registered when CACHE_DB_PATH is set — otherwise
    Django's router chain is empty and everything falls through to "default".
    """

    def db_for_read(self, model, **hints):
        if model._meta.app_label == "django_cache":
            return "cache_db"
        return None

    db_for_write = db_for_read

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label == "django_cache":
            return db == "cache_db"
        return None
