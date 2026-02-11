from django.urls import path

from . import views

urlpatterns = [
    path("dump-db/", views.ExportBackupView.as_view(), name="dump-db"),
    path(
        "load-backup/",
        views.LoadBackupView.as_view(),
        name="load-backup",
    ),
    path(
        "full-restore/",
        views.FullRestoreView.as_view(),
        name="full-restore",
    ),
    # New streaming batch endpoints
    path(
        "attachment-metadata/",
        views.AttachmentMetadataView.as_view(),
        name="attachment-metadata",
    ),
    path(
        "batch-download-attachments/",
        views.BatchDownloadAttachmentsView.as_view(),
        name="batch-download-attachments",
    ),
    path(
        "batch-upload-attachments/",
        views.BatchUploadAttachmentsView.as_view(),
        name="batch-upload-attachments",
    ),
]
