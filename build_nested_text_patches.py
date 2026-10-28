"""Patch reviewed nested tool labels and action strings missed by DefInjected."""
import json
from pathlib import Path
from lxml import etree as E
from build_translations import MODS, WORKSHOP, active_defs
from build_skill_command_patches import xpath_literal

def main():
    translations = json.loads(Path('nested_text_translations.json').read_text(encoding='utf-8'))
    total = 0
    for mod_id, _ in MODS:
        folder = active_defs(WORKSHOP/mod_id)
        if folder is None:
            continue
        patch = E.Element('Patch')
        for file in sorted(folder.rglob('*.xml')):
            tree = E.parse(str(file))
            for definition in tree.getroot():
                if not isinstance(definition.tag, str):
                    continue
                name = definition.findtext('defName') or definition.get('Name', '')
                if not name:
                    continue
                for node in definition.iterdescendants():
                    source = (node.text or '').strip()
                    if len(node) or source not in translations or node.getparent() is definition:
                        continue
                    relative = tree.getpath(node)[len(tree.getpath(definition))+1:]
                    selector = 'defName' if definition.findtext('defName') else '@Name'
                    xpath = f'Defs/{definition.tag}[{selector}={xpath_literal(name)}]/{relative}'
                    operation = E.SubElement(patch, 'Operation', Class='PatchOperationConditional')
                    E.SubElement(operation, 'success').text = 'Always'
                    E.SubElement(operation, 'xpath').text = xpath
                    match = E.SubElement(operation, 'match', Class='PatchOperationReplace')
                    E.SubElement(match, 'xpath').text = xpath
                    E.SubElement(E.SubElement(match, 'value'), node.tag).text = translations[source]
                    total += 1
        if len(patch):
            package = next(Path('Mods').glob(mod_id+' - * Chinese'))
            for root in (package, Path('supplemental')/mod_id):
                target = root/'Patches/Aya_Nested_Text.xml'
                target.parent.mkdir(parents=True, exist_ok=True)
                E.ElementTree(patch).write(str(target), encoding='utf-8', xml_declaration=True, pretty_print=True)
    print(f'Generated {total} nested text translations')

if __name__ == '__main__':
    main()
