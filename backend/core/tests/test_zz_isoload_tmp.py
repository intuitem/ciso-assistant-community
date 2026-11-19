import pytest
from core.models import StoredLibrary, LoadedLibrary, Framework


@pytest.mark.django_db
def test_iso_loads_from_store():
    StoredLibrary.__init_class__()
    from django.core.management import call_command

    call_command("storelibraries")
    stored = StoredLibrary.objects.filter(
        urn="urn:intuitem:risk:library:iso27001-2022"
    ).first()
    print(
        "stored",
        stored and stored.version,
        "loaded already:",
        LoadedLibrary.objects.filter(urn=stored.urn).exists(),
    )
    print("load ->", stored.load())
    print("frameworks", list(Framework.objects.values_list("urn", flat=True)))
