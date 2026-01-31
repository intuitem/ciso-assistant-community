import pytest
from core.models import StoredLibrary

SAMPLE_YAML_LIB_WITH_MAPPINGS = """
urn: urn:intuitem:test:library:map-nist-csf-1.1-nist-csf-2.0
locale: en
ref_id: test-map-nist-csf-1.1-nist-csf-2.0
name: Sample test mapping from nist-csf-1.1 to nist-csf-2.0
description: Sample test mapping from nist-csf-1.1 to nist-csf-2.0
version: 1
publication_date: 2024-06-29
copyright: NIST
provider: NIST
packager: intuitem
dependencies:
- urn:intuitem:risk:library:nist-csf-2.0
- urn:intuitem:risk:library:nist-csf-1.1
objects:
  requirement_mapping_set:
    urn: urn:intuitem:test:requirement_mapping_set:nist-csf-1.1-to-nist-csf-2.0
    ref_id: test-mapping-nist-csf-1.1-nist-csf-2.0
    name: test-mapping-nist-csf-1.1-nist-csf-2.0
    source_framework_urn: urn:intuitem:risk:framework:nist-csf-1.1
    target_framework_urn: urn:intuitem:risk:framework:nist-csf-2.0
    requirement_mappings:
    - source_requirement_urn: urn:intuitem:risk:req_node:nist-csf-1.1:id.gv
      target_requirement_urn: urn:intuitem:risk:req_node:nist-csf-2.0:gv
      relationship: intersect
      rationale: semantic
      annotation: ''
""".lstrip().encode("utf-8")

SAMPLE_YAML_LIB_NO_MAPPINGS = """
urn: urn:intuitem:test:library:nist-csf-1.1
locale: en
ref_id: NIST-CSF-1.1
name: NIST CSF v1.1
description: National Institute of Standards and Technology - Cybersecurity Framework
  (CSF 1.1)
copyright: With the exception of material marked as copyrighted, information presented
  on NIST sites are considered public information and may be distributed or copied.
version: 5
publication_date: 2025-05-22
provider: NIST
packager: intuitem
translations:
  fr:
    name: NIST CSF version 1.1
    description: National Institute of Standards and Technology - Cybersecurity Framework
      (CSF 1.1)
objects:
  framework:
    urn: urn:intuitem:test:framework:nist-csf-1.1
    ref_id: NIST-CSF-1.1
    name: NIST CSF v1.1
    description: NIST Cybersecurity Framework
    min_score: 1
    max_score: 4
    scores_definition:
    - score: 1
      name: Partial
      description: 'Application of the organizational cybersecurity risk strategy
        is managed in an ad hoc manner.

        There is limited awareness of cybersecurity risks at the organizational level.'
      translations:
        fr:
          name: Partiel
          description: "L\u2019application de la strat\xe9gie de gestion des risques\
            \ cybers\xe9curit\xe9 de l\u2019organisation est g\xe9r\xe9e de mani\xe8\
            re ad hoc.\nLa sensibilisation aux risques cybers\xe9curit\xe9 est limit\xe9\
            e au niveau organisationnel.\nLes pratiques de gestion des risques sont\
            \ approuv\xe9es par la direction, mais ne sont peut-\xeatre pas \xe9tablies\
            \ comme une politique \xe0 l\u2019\xe9chelle de l\u2019organisation."
    - score: 2
      name: Risk informed
      description: 'Risk management practices are approved by management but may not
        be established as organization-wide policy.

        There is an awareness of cybersecurity risks at the organizational level,
        but an organization-wide approach to managing cybersecurity risks has not
        been established.'
      translations:
        fr:
          name: "Inform\xe9 des risques"
          description: "Les pratiques de gestion des risques sont approuv\xe9es par\
            \ la direction, mais ne sont peut-\xeatre pas \xe9tablies comme une politique\
            \ \xe0 l\u2019\xe9chelle de l\u2019organisation.\nIl existe une sensibilisation\
            \ aux risques cybers\xe9curit\xe9 au niveau de l\u2019organisation, mais\
            \ une approche globale pour les g\xe9rer n\u2019a pas \xe9t\xe9 mise en\
            \ place."
    - score: 3
      name: Repeatable
      description: "The organization\u2019s risk management practices are formally\
        \ approved and expressed as policy.\nOrganizational cybersecurity practices\
        \ are regularly updated based on the application of risk management processes\
        \ to changes in business/mission requirements, threats, and technological\
        \ landscape."
      translations:
        fr:
          name: "R\xe9p\xe9table"
          description: "Les pratiques de gestion des risques de l\u2019organisation\
            \ sont formellement approuv\xe9es et exprim\xe9es sous forme de politique.\n\
            Les pratiques cybers\xe9curit\xe9 de l\u2019organisation sont r\xe9guli\xe8\
            rement mises \xe0 jour en fonction de l\u2019application des processus\
            \ de gestion des risques, pour r\xe9pondre \xe0 l\u2019\xe9volution des\
            \ exigences m\xe9tiers ou missions, des menaces et du paysage technologique."
    - score: 4
      name: Adaptive
      description: 'There is an organization-wide approach to managing cybersecurity
        risks that uses risk-informed policies, processes, and procedures to address
        potential cybersecurity events.

        The organization adapts its cybersecurity practices based on previous and
        current cybersecurity activities, including lessons learned and predictive
        indicators.'
      translations:
        fr:
          name: Adaptatif
          description: "L\u2019organisation dispose d\u2019une approche \xe0 l\u2019\
            \xe9chelle de l\u2019entreprise pour g\xe9rer les risques cybers\xe9curit\xe9\
            , en utilisant des politiques, processus et proc\xe9dures inform\xe9s\
            \ par les risques pour traiter les \xe9v\xe9nements potentiels.\nL\u2019\
            organisation adapte ses pratiques cybers\xe9curit\xe9 en fonction des\
            \ activit\xe9s pass\xe9es et pr\xe9sentes, y compris les retours d\u2019\
            exp\xe9rience et les indicateurs pr\xe9dictifs."
    requirement_nodes:
    - urn: urn:intuitem:test:req_node:nist-csf-1.1:id
      assessable: false
      depth: 1
      ref_id: ID
      name: Identify
      translations:
        fr:
          name: Identifier
          description: null
""".lstrip().encode("utf-8")


class TestStoreLibraryContent:
    @pytest.mark.django_db
    def test_store_library_content_sets_autoload_to_true_if_lib_has_mappings(self):
        stored_library, _ = StoredLibrary.store_library_content(
            SAMPLE_YAML_LIB_WITH_MAPPINGS
        )
        assert stored_library is not None
        assert stored_library.autoload is True

    @pytest.mark.django_db
    def test_store_library_content_sets_autoload_to_false_if_lib_has_no_mappings(self):
        stored_library, _ = StoredLibrary.store_library_content(
            SAMPLE_YAML_LIB_NO_MAPPINGS
        )
        assert stored_library is not None
        assert stored_library.autoload is False

    @pytest.mark.django_db
    def test_store_library_content_dry_run(self):
        library_data = StoredLibrary.store_library_content(
            SAMPLE_YAML_LIB_NO_MAPPINGS, dry_run=True
        )
        assert isinstance(library_data, dict)
        assert library_data["urn"] == "urn:intuitem:test:library:nist-csf-1.1"
        assert library_data["version"] == 5
        assert library_data["objects_meta"]["framework"] == 1
        # Check that no object was created
        assert not StoredLibrary.objects.filter(
            urn="urn:intuitem:test:library:nist-csf-1.1"
        ).exists()
