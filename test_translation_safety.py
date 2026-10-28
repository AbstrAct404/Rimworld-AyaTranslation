"""Regression tests for translation/identity separation (no game launch)."""
import json
import tempfile
import unittest
from pathlib import Path
from lxml import etree as E
from audit_translation_safety import inspect_package
from build_body_part_patches import translation_key
from build_translations import WORKSHOP, active_defs


class TranslationSafetyTests(unittest.TestCase):
    def test_list_indexes(self):
        self.assertEqual(translation_key('Body', 'corePart[1]/parts[1]/li[3]/customLabel[1]'),
                         'Body.corePart.parts.2.customLabel')

    def test_body_translations_preserve_original_identity(self):
        rows = json.loads(Path('BODY-PART-AUDIT.json').read_text())['operations']
        sources = {}
        for row in rows:
            mod_id = row['modId']
            if mod_id not in sources:
                root = E.Element('root')
                defs = E.SubElement(root, 'Defs')
                for file in active_defs(WORKSHOP/mod_id).rglob('*.xml'):
                    parsed = E.parse(str(file)).getroot()
                    if parsed.tag == 'Defs':
                        defs.extend(list(parsed))
                sources[mod_id] = E.ElementTree(root)
            nodes = sources[mod_id].xpath(row['xpath'])
            self.assertTrue(nodes, row['xpath'])
            original = nodes[0].text.strip()
            self.assertEqual(original, row['source'])
            # Model BodyPartRecord.PostLoad: snapshot BEFORE language injection.
            untranslated_custom_label = original
            display_label = row['translation']
            package = next(Path('Mods').glob(mod_id+' - * Chinese'))
            file = package/'Languages/ChineseSimplified/DefInjected/BodyDef/Aya_CustomLabels.xml'
            entries = {n.tag: n.text for n in E.parse(str(file)).getroot()}
            self.assertEqual(entries[row['key']], display_label)
            self.assertEqual(untranslated_custom_label, original)
            self.assertFalse((package/'Patches/Aya_Body_CustomLabels.xml').exists())
        self.assertEqual(len(rows), 964)

    def test_rejects_source_label_and_asset_overrides(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root/'Patches').mkdir()
            patch = root/'Patches/unsafe.xml'
            patch.write_text('<Patch><Operation Class="PatchOperationReplace"><xpath>Defs/BodyDef[defName="Body"]/corePart/customLabel</xpath><value><customLabel>左眼</customLabel></value></Operation></Patch>')
            self.assertTrue(inspect_package(root)['violations'])
            patch.write_text('<Patch/>')
            (root/'Textures').mkdir()
            (root/'Textures/eye.png').write_bytes(b'fixture')
            self.assertTrue(inspect_package(root)['violations'])

    def test_all_packages_text_only(self):
        for package in Path('Mods').glob('* Chinese'):
            if (package/'About/About.xml').is_file():
                self.assertEqual(inspect_package(package)['violations'], [], package.name)


if __name__ == '__main__':
    unittest.main()
