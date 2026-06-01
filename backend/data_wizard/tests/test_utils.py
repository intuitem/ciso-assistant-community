"""Unit tests for the data wizard helpers."""

import unittest
from pathlib import Path

from data_wizard.egerie_xml_helpers import (
    map_egerie_status,
    process_xml_file,
    quartile_to_index,
)

import pandas as pd
from data_wizard.views import normalize_df_columns

# Minimal Egerie analysis XML covering the elements we actually consume.
# Kept inline so the parser test runs without external fixtures.
MINIMAL_EGERIE_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<analysis xmlns="http://www.egerie-software.com/riskmanager" id="REF_ID_X" version="EgerieSuite_v4.5.0">
  <meta>
    <label xml:lang="fr">Test Study</label>
    <description xml:lang="fr">A study description</description>
  </meta>
  <context><metrics/></context>
  <system>
    <supportingAssets>
      <supportingAsset id="SA_1"><label>Web Server</label></supportingAsset>
    </supportingAssets>
    <primaryAssets>
      <primaryAsset id="PA_1"><label>Member Database</label><information/></primaryAsset>
    </primaryAssets>
    <riskSources>
      <riskSource id="RS_1">
        <label>hacktivist</label>
        <category ref="RSC_X"/>
        <objectives><objective ref="O_1"/></objectives>
      </riskSource>
    </riskSources>
    <objectives>
      <objective id="O_1"><label>Cause reputational damage</label></objective>
    </objectives>
    <stakeholders>
      <stakeholder id="SH_1" supportingAsset="SA_1">
        <label>Hosting Provider</label>
        <dependence>0.6667</dependence>
        <penetration>1.0000</penetration>
        <maturity>0.3333</maturity>
        <trust>0.6667</trust>
      </stakeholder>
    </stakeholders>
  </system>
  <assessment>
    <controls>
      <control id="C_1" category="protection">
        <label>MFA enforcement</label>
        <implementation><default>planned</default></implementation>
      </control>
    </controls>
    <fearedEvents>
      <fearedEvent id="FE_1">
        <label>Data leak</label>
        <primaryAsset ref="PA_1"/>
        <severity>0.6667</severity>
      </fearedEvent>
    </fearedEvents>
    <strategicScenarios>
      <strategicScenario id="SS_1">
        <label>hacktivist / Cause reputational damage</label>
        <severity>1.0</severity>
        <resources>0.3333</resources>
        <motivation>1.0</motivation>
        <links>
          <riskSource ref="RS_1"/>
          <objective ref="O_1"/>
          <fearedEvent ref="FE_1"/>
        </links>
        <attackPaths>
          <attackPath id="AP_1"/>
        </attackPaths>
      </strategicScenario>
    </strategicScenarios>
    <operationalScenarios>
      <operationalScenario id="OS_1">
        <label>brute force admin panel</label>
        <likelihood>0.6667</likelihood>
        <links>
          <strategicScenario ref="SS_1"/>
          <attackPath ref="AP_1"/>
          <fearedEvent ref="FE_1"/>
        </links>
        <mitigation>
          <risk>
            <controls>
              <control ref="C_1"><coverage>10</coverage></control>
            </controls>
          </risk>
        </mitigation>
      </operationalScenario>
    </operationalScenarios>
    <elementaryActions>
      <elementaryAction id="EA_1">
        <label>Discover login page</label>
        <description>via google dorking</description>
        <success>0.6667</success>
        <links>
          <supportingAsset ref="SA_1"/>
        </links>
      </elementaryAction>
    </elementaryActions>
  </assessment>
</analysis>
"""


class MapEgerieStatusTest(unittest.TestCase):
    def test_known_statuses(self):
        self.assertEqual(map_egerie_status("inactive"), "to_do")
        self.assertEqual(map_egerie_status("planned"), "to_do")
        self.assertEqual(map_egerie_status("in_progress"), "in_progress")
        self.assertEqual(map_egerie_status("applied"), "active")
        self.assertEqual(map_egerie_status("active"), "active")
        self.assertEqual(map_egerie_status("deprecated"), "deprecated")

    def test_case_insensitive(self):
        self.assertEqual(map_egerie_status("PLANNED"), "to_do")
        self.assertEqual(map_egerie_status("Applied"), "active")

    def test_unknown_and_empty(self):
        self.assertEqual(map_egerie_status("nonsense"), "")
        self.assertEqual(map_egerie_status(""), "")
        self.assertEqual(map_egerie_status(None), "")


class QuartileMappingTest(unittest.TestCase):
    def test_endpoints(self):
        self.assertEqual(quartile_to_index(0.0, 4), 0)
        self.assertEqual(quartile_to_index(1.0, 4), 3)

    def test_quartiles(self):
        self.assertEqual(quartile_to_index(0.3333, 4), 1)
        self.assertEqual(quartile_to_index(0.6667, 4), 2)

    def test_intermediate_rounding(self):
        # 0.5 * 3 = 1.5 -> banker's rounding gives 2
        self.assertEqual(quartile_to_index(0.5, 4), 2)

    def test_none(self):
        self.assertIsNone(quartile_to_index(None, 4))

    def test_clamping(self):
        # Out-of-range floats must still produce a valid index
        self.assertEqual(quartile_to_index(2.0, 4), 3)
        self.assertEqual(quartile_to_index(-0.5, 4), 0)


class EgerieXmlParserTest(unittest.TestCase):
    def test_minimal_xml(self):
        data = process_xml_file(MINIMAL_EGERIE_XML)

        self.assertEqual(data["study"]["name"], "Test Study")
        self.assertEqual(data["study"]["ref_id"], "REF_ID_X")

        self.assertEqual(len(data["primary_assets"]), 1)
        self.assertEqual(data["primary_assets"][0]["type"], "PR")
        self.assertEqual(data["primary_assets"][0]["name"], "Member Database")

        self.assertEqual(len(data["supporting_assets"]), 1)
        self.assertEqual(data["supporting_assets"][0]["type"], "SP")

        self.assertEqual(len(data["risk_sources"]), 1)
        self.assertEqual(data["risk_sources"][0]["name"], "hacktivist")
        self.assertEqual(data["risk_sources"][0]["objective_ids"], ["O_1"])

        self.assertEqual(len(data["objectives"]), 1)
        self.assertEqual(data["objectives"][0]["name"], "Cause reputational damage")

        self.assertEqual(len(data["stakeholders"]), 1)
        sh = data["stakeholders"][0]
        self.assertEqual(sh["supporting_asset_id"], "SA_1")
        self.assertAlmostEqual(sh["dependence"], 0.6667)
        self.assertAlmostEqual(sh["penetration"], 1.0)

        self.assertEqual(len(data["feared_events"]), 1)
        fe = data["feared_events"][0]
        self.assertEqual(fe["primary_asset_id"], "PA_1")
        self.assertAlmostEqual(fe["severity"], 0.6667)

        self.assertEqual(len(data["strategic_scenarios"]), 1)
        ss = data["strategic_scenarios"][0]
        self.assertEqual(ss["risk_source_id"], "RS_1")
        self.assertEqual(ss["objective_id"], "O_1")
        self.assertEqual(ss["feared_event_ids"], ["FE_1"])
        self.assertEqual(len(ss["attack_paths"]), 1)
        self.assertEqual(ss["attack_paths"][0]["id"], "AP_1")

        self.assertEqual(len(data["operational_scenarios"]), 1)
        os_ = data["operational_scenarios"][0]
        self.assertEqual(os_["attack_path_ids"], ["AP_1"])
        self.assertEqual(os_["strategic_scenario_ids"], ["SS_1"])
        self.assertAlmostEqual(os_["likelihood"], 0.6667)
        self.assertEqual(len(os_["control_refs"]), 1)
        self.assertEqual(os_["control_refs"][0]["ref"], "C_1")

        self.assertEqual(len(data["elementary_actions"]), 1)
        ea = data["elementary_actions"][0]
        self.assertEqual(ea["supporting_asset_ids"], ["SA_1"])

        self.assertEqual(len(data["controls"]), 1)
        ctl = data["controls"][0]
        self.assertEqual(ctl["category"], "protection")
        self.assertEqual(ctl["egerie_status"], "planned")


# Optional integration test against the real Egerie samples in the repo root.
# Skipped if the files aren't present (they are not checked in).
_REPO_ROOT = Path(__file__).resolve().parents[2]
_SAMPLE_STAGE = _REPO_ROOT / "analyse_fictive_egerie_stage.xml"
_SAMPLE_SAAS = _REPO_ROOT / "analyse_training_egerie_saas.xml"


@unittest.skipUnless(
    _SAMPLE_STAGE.is_file() and _SAMPLE_SAAS.is_file(),
    "Egerie sample XML files not present at repo root; skipping integration test.",
)
class EgerieRealSamplesTest(unittest.TestCase):
    def test_fictive_stage(self):
        data = process_xml_file(_SAMPLE_STAGE.read_bytes())
        # Counts observed from the sample; bump if Egerie updates the file.
        self.assertEqual(data["study"]["name"], "AR FICTIF STAGE")
        self.assertEqual(len(data["primary_assets"]), 5)
        self.assertEqual(len(data["supporting_assets"]), 18)
        self.assertEqual(len(data["feared_events"]), 4)
        self.assertEqual(len(data["risk_sources"]), 3)
        self.assertEqual(len(data["objectives"]), 6)
        self.assertEqual(len(data["stakeholders"]), 11)
        self.assertEqual(len(data["strategic_scenarios"]), 7)
        self.assertEqual(len(data["operational_scenarios"]), 4)
        self.assertEqual(len(data["elementary_actions"]), 19)
        self.assertEqual(len(data["controls"]), 14)

    def test_training_saas(self):
        data = process_xml_file(_SAMPLE_SAAS.read_bytes())
        # The training file is a partial study (only workshop 1 + some W4 data).
        self.assertIn("Getting Started", data["study"]["name"])
        self.assertEqual(len(data["primary_assets"]), 7)
        self.assertEqual(len(data["supporting_assets"]), 16)
        self.assertEqual(len(data["feared_events"]), 7)
        self.assertEqual(len(data["controls"]), 27)
        # Workshop 3 is empty in this sample
        self.assertEqual(len(data["stakeholders"]), 0)
        self.assertEqual(len(data["strategic_scenarios"]), 0)


class NormalizeDfColumnsTest(unittest.TestCase):
    def test_strips_and_lowercases(self):
        # check that the fields are well trimed and put in lowercase
        df = pd.DataFrame(columns=[" Name ", "DESCRIPTION", "  Ref_ID"])
        df = normalize_df_columns(df)
        self.assertEqual(list(df.columns), ["name", "description", "ref_id"])

    def test_already_normalized(self):
        # checks that nothing changes
        df = pd.DataFrame(columns=["name", "ref"])
        df = normalize_df_columns(df)
        self.assertEqual(list(df.columns), ["name", "ref"])

    def test_numeric_column_name(self):
        # check for int values
        df = pd.DataFrame(columns=[0, 1, 2])
        df = normalize_df_columns(df)
        self.assertEqual(list(df.columns), ["0", "1", "2"])

    def test_duplicate_after_normalization_raises(self):
        df = pd.DataFrame(columns=["Name", " name"])
        with self.assertRaises(ValueError) as ctx:
            normalize_df_columns(df)
        self.assertIn("name", str(ctx.exception))
