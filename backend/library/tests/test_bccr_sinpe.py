"""Library regressions. Run: python -m unittest discover -s . -p test_bccr_sinpe.py"""
from pathlib import Path
import hashlib
import json
import unittest
import yaml

ROOT=Path(__file__).resolve().parents[1]/'libraries'


class TestBccrSinpe(unittest.TestCase):
    def test_category_libraries(self):
        baseline={'6.1.1': {'category_1': 'mandatory',
                   'category_2': 'mandatory',
                   'hash': 'a5954ccdb2329e2f997e73a03a874ee14887307e66d2c38ec72206fc4c5bfbf3'},
         '6.1.2': {'category_1': 'mandatory',
                   'category_2': 'mandatory',
                   'hash': 'cdfa95fa570f98022c607a737bcb2818d6b7b0fceb890b5c322ef9d8e138b498'},
         '6.10.1': {'category_1': 'mandatory',
                    'category_2': 'not_applicable',
                    'hash': '7f35889db1f7762112649c9e38b22487958bc9acee2f8ab137c0b3a8bdfd91fb'},
         '6.11.1': {'category_1': 'mandatory',
                    'category_2': 'mandatory',
                    'hash': '7e8ee96506c1baf7c850f43f1919b63c96c4103925b7efde413a74f9f7f8c6a8'},
         '6.11.2': {'category_1': 'mandatory',
                    'category_2': 'mandatory',
                    'hash': 'dcc24834d3a6085b575695903e8aeeb6883a84f969b1b48ae8dd7987302af4ca'},
         '6.11.3': {'category_1': 'mandatory',
                    'category_2': 'mandatory',
                    'hash': 'b8aefc1ea20be47e8d4a1295b771e763820045ee342c46d55a1acb8ba63cc048'},
         '6.12.1': {'category_1': 'mandatory',
                    'category_2': 'not_applicable',
                    'hash': '91d98fb9e9d75d141a3ec9b74286a72cfa72d3be9675cb79311df3cc9fb9f968'},
         '6.12.2': {'category_1': 'mandatory',
                    'category_2': 'optional',
                    'hash': 'aab726740c164382d16b7f2527385717fb1b50178c66c50cea4026f9c0dbee88'},
         '6.12.3': {'category_1': 'mandatory',
                    'category_2': 'not_applicable',
                    'hash': 'c399faff4748b2f022731f2939e7ffa26e2ae829ea7e2a833360bb0e220e8f3a'},
         '6.13.1': {'category_1': 'mandatory',
                    'category_2': 'mandatory',
                    'hash': '7521ee77128b9328517e21bb38ebc3eb3cdb273eceefb36c2d7e4cd9b3b02520'},
         '6.13.2': {'category_1': 'optional',
                    'category_2': 'optional',
                    'hash': 'eed12eaf401561aec60a99f67a16e3063f74216cedbfffd482d6d3c9888b3a79'},
         '6.14.1': {'category_1': 'mandatory',
                    'category_2': 'mandatory',
                    'hash': '0155491f0aa648d58a570b9e965f3e32dddf69665a4583e08f5b740a8b403b7e'},
         '6.15.1': {'category_1': 'mandatory',
                    'category_2': 'not_applicable',
                    'hash': '11c573d728ad42e341cf2500c16cb34b9dd909224c9f61d18f0c742ed04b118b'},
         '6.15.2': {'category_1': 'mandatory',
                    'category_2': 'not_applicable',
                    'hash': '35b7ae083687d569176bf725cec34b82c1d1b43600378a1eae78edb524619153'},
         '6.15.3': {'category_1': 'mandatory',
                    'category_2': 'not_applicable',
                    'hash': 'c910d4f5487a8e3cf3a6b15030a5f3460e25e621ce6d2c5515cea5c2183dd6d4'},
         '6.15.4': {'category_1': 'mandatory',
                    'category_2': 'not_applicable',
                    'hash': '894832b7d62fabba76e82813193de9f482df73ba6262a762b601d76c8664a817'},
         '6.16.1': {'category_1': 'mandatory',
                    'category_2': 'mandatory',
                    'hash': '690eb1f0919d2d2f89d7219fdcf41342bb2b73e6219b61e8226bf0b942b6f726'},
         '6.16.2': {'category_1': 'mandatory',
                    'category_2': 'mandatory',
                    'hash': 'fe621a162b47491e9267b5e14b78f0c1a317c49a5da77549e4987101be807166'},
         '6.16.3': {'category_1': 'mandatory',
                    'category_2': 'mandatory',
                    'hash': 'f469c21ccb4b32e8cff9414cf673ef294e178a88ffe911bec9185ad0cac23b73'},
         '6.16.4': {'category_1': 'mandatory',
                    'category_2': 'mandatory',
                    'hash': 'cdeeb0511e623b33ad04815555a090db26aae02cae1c82a98647bda589de2a54'},
         '6.2.1': {'category_1': 'mandatory',
                   'category_2': 'mandatory',
                   'hash': '49f5a88071895d1be17d60f06afd56705439dfc694534236aabe27383280f4ce'},
         '6.2.2': {'category_1': 'mandatory',
                   'category_2': 'mandatory',
                   'hash': '028d9b3f5f091e3a458f5f2234b74b0a3caf4f809a16c49c840b3f84c2f4e81b'},
         '6.3.1': {'category_1': 'mandatory',
                   'category_2': 'mandatory',
                   'hash': '4dd6da79bc96cd688f0d4b46cf080754626b2851706a90fe220c56570a1e2e81'},
         '6.3.2': {'category_1': 'mandatory',
                   'category_2': 'not_applicable',
                   'hash': '596c7ae92ea6f9221efec7cce85f87a0f1bd7796cddc500925b74bcc410677b8'},
         '6.3.3': {'category_1': 'optional',
                   'category_2': 'optional',
                   'hash': '8c6c70d361a2d31458d3c60a82cad67f19d3f76fd2ca2962defdb6cc95457b10'},
         '6.3.4': {'category_1': 'optional',
                   'category_2': 'optional',
                   'hash': '7f10b0e8519f790788b00e6899e0ce8af61a7c7b870e56fa60cfce423eb196ac'},
         '6.4.1': {'category_1': 'mandatory',
                   'category_2': 'mandatory',
                   'hash': 'ba211625ace3befe2e6b0617234f8a759df29fa7072211bd3ce34dbfbbcd8d67'},
         '6.4.2': {'category_1': 'mandatory',
                   'category_2': 'mandatory',
                   'hash': 'de003543e91d3b34d5d9cf45e85cfd5b8cc95e3e140ed73cb7c82b3122ddafce'},
         '6.5.1': {'category_1': 'mandatory',
                   'category_2': 'mandatory',
                   'hash': '799e6ad8045cd58561cd41ea8cec67115c8873cd6e61a72afe8f24a1475a8784'},
         '6.5.2': {'category_1': 'mandatory',
                   'category_2': 'mandatory',
                   'hash': '936b9319dc467be33a7eba4660c7c3f1156e7061faa4675b6f4b34cdb6d5e4f3'},
         '6.5.3': {'category_1': 'mandatory',
                   'category_2': 'mandatory',
                   'hash': '93e9d97222df1410f6eb0a14f0e688ccd2c943be3d47c07bbcf4b96c68fe2827'},
         '6.5.4': {'category_1': 'mandatory',
                   'category_2': 'mandatory',
                   'hash': '5712a7a54b169ad780902c216d27327ac33f5523e4b99947726daae58827fb5f'},
         '6.5.5': {'category_1': 'mandatory',
                   'category_2': 'optional',
                   'hash': '89877af9764a173a5ecc0169b8bbf25e8545f6a8ebc8df716d71b7f0ccec5d43'},
         '6.6.1': {'category_1': 'mandatory',
                   'category_2': 'mandatory',
                   'hash': '088a20d22df460bb1e13ab307d756cba915684c824984b246c56627925d7fdd1'},
         '6.6.2': {'category_1': 'mandatory',
                   'category_2': 'mandatory',
                   'hash': 'c4ab727c4db999378f2652ff0b26bb3b7c3001775ddcaeb092491303cd2270b1'},
         '6.6.3': {'category_1': 'mandatory',
                   'category_2': 'mandatory',
                   'hash': '10921377070ba608ca314faa11fa1e32d124741bd9ee3f1df47d9cd3b4506e21'},
         '6.7.1': {'category_1': 'mandatory',
                   'category_2': 'optional',
                   'hash': 'a318ec2ad31eaa1c13c28899922d79ed233877c8979fcd696cd93083d1e4d631'},
         '6.7.2': {'category_1': 'mandatory',
                   'category_2': 'optional',
                   'hash': 'f3ff2e78446a03a39a4c9ee5f22be50202dc51e5318fe3190d73d7d1b8888f0a'},
         '6.7.3': {'category_1': 'mandatory',
                   'category_2': 'optional',
                   'hash': '20686e73f1a9d75c25cb71f59358abc1bad9efb4989cc99f7eff25e35c90b67a'},
         '6.7.4': {'category_1': 'mandatory',
                   'category_2': 'optional',
                   'hash': 'ddb5178bd8b4ac2490e0de27c74c990ed31bbb83757dcee172a26f2c84771f6a'},
         '6.8.1': {'category_1': 'mandatory',
                   'category_2': 'mandatory',
                   'hash': '5b0b43049256834f44b2b966b002445ce7b8e7403eadd3ca448199a6db359748'},
         '6.8.2': {'category_1': 'mandatory',
                   'category_2': 'mandatory',
                   'hash': '65d799fdbd7d298b303517c8b7e76871f980b954bff0ad2e3bc31058f51a9f89'},
         '6.8.3': {'category_1': 'mandatory',
                   'category_2': 'mandatory',
                   'hash': '35217717cb43d93ff430a16475ca3548799d34b8437d19a6f9641e8c2e520860'},
         '6.8.4': {'category_1': 'mandatory',
                   'category_2': 'mandatory',
                   'hash': 'f5ace27a1430d2014699e7d426c04fa0c76306ba63a7332f5d2570e8b263f7bc'},
         '6.9.1': {'category_1': 'mandatory',
                   'category_2': 'mandatory',
                   'hash': '1292ceeae6ec1ba45efb91f4802204b407a90d30e4acad781c6eb7359ef4c632'},
         '6.9.2': {'category_1': 'mandatory',
                   'category_2': 'mandatory',
                   'hash': '71abd87b31f645259dc7f1896b03b0b241c469359aad79fc7c803dee4f3a1b4d'},
         '6.9.3': {'category_1': 'optional',
                   'category_2': 'optional',
                   'hash': 'bacb63dc972cc478297ee8375a9f5bdaa4db115ad28f32761ad4bbcd52ce7595'}}
        all_urns=set()
        for cat,expected in ((1,(47,43,4)),(2,(39,29,10))):
            with self.subTest(category=cat):
                path=ROOT/('bccr-sinpe-nt-rcs-ed7-evaluacion-integral'+('' if cat==1 else '-cat2')+'.yaml')
                lib=yaml.safe_load(path.read_text())
                fw=lib['objects']['framework']
                nodes=fw['requirement_nodes']
                by_urn={n['urn']:n for n in nodes}
                self.assertEqual(len(nodes),len(by_urn))
                self.assertFalse(fw.get('implementation_groups_definition'))
                technical=[n for n in nodes if n.get('ref_id') in baseline]
                self.assertEqual((len(technical),sum(n['importance']=='mandatory' for n in technical),sum(n['importance']=='recommended' for n in technical)),expected)
                self.assertEqual({n['ref_id'] for n in technical},{ref for ref,b in baseline.items() if b[f'category_{cat}']!='not_applicable'})
                self.assertEqual(next(n for n in technical if n['ref_id']=='6.3.3')['importance'],'recommended')
                for ref in ('6.5.5','6.7.1','6.7.2','6.7.3','6.7.4','6.12.2'):
                    self.assertEqual(next(n for n in technical if n['ref_id']==ref)['importance'],'mandatory' if cat==1 else 'recommended')
                for n in technical:
                    fields={'ref_id':n['ref_id'],'name':n['name'],'description':n['description'].split('\n\n',1)[1],'name_en':n['translations']['en']['name'],'description_en':n['translations']['en']['description'].split('\n\n',1)[1]}
                    self.assertEqual(hashlib.sha256(json.dumps(fields,ensure_ascii=False,sort_keys=True).encode()).hexdigest(),baseline[n['ref_id']]['hash'])
                checklist=[n for n in nodes if n.get('assessable') and n not in technical]
                self.assertEqual(len(checklist),66)
                for n in nodes:
                    self.assertFalse(n.get('implementation_groups'))
                    if n.get('parent_urn'):
                        self.assertIn(n['parent_urn'],by_urn)
                        self.assertEqual(n['depth'],by_urn[n['parent_urn']]['depth']+1)
                    self.assertIn('en',n['translations'])
                    self.assertNotIn(n['urn'],all_urns)
                    all_urns.add(n['urn'])
                    if not n.get('assessable'):
                        self.assertFalse(n.get('questions'))
                        continue
                    self.assertEqual(len(n['questions']),1)
                    qurn,q=next(iter(n['questions'].items()))
                    self.assertEqual(q['type'],'unique_choice')
                    self.assertTrue(q['required'])
                    expected_results={'compliant','non_compliant'}|({'not_applicable'} if n in checklist else set())
                    self.assertEqual({c['compute_result'] for c in q['choices']},expected_results)
                    for c in q['choices']:
                        self.assertIsNone(c.get('add_score'))
                        self.assertTrue(c['urn'].startswith(qurn+':choice:'))
                        self.assertIn('en',c['translations'])
                self.assertEqual(sum(n.get('assessable',False) for n in nodes),expected[0]+66)
                for field in ('score','documentation_score'):
                    self.assertEqual(fw['field_visibility'][field],{'auditor':'hidden','respondent':'hidden'})


if __name__=='__main__':
    unittest.main()
