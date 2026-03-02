from contextvars import ContextVar

focus_folder_id_var = ContextVar("focus_folder_id", default=None)
