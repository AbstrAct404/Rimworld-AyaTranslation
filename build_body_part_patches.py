"""Translate BodyDef display labels without changing original part identity.

Vanilla anatomical terms are taken verbatim from the installed Chinese language
archive. Special Aya terms are reviewed here; an unknown term stops the build.
"""
import json
import os
import re
import tarfile
from pathlib import Path
import xml.etree.ElementTree as ET
from build_translations import MODS, WORKSHOP, active_defs, text, xml_write
from build_skill_command_patches import iter_nodes_with_paths, xpath_literal

GAME = Path(os.environ.get('AYA_GAME_ROOT', '/Users/studyhard/Library/Application Support/Steam/steamapps/common/RimWorld' if os.name != 'nt' else r'D:\SteamLibrary\steamapps\common\RimWorld'))
SPECIAL = {
    'Wing': '翅膀', 'Horn': '角', 'Tail': '尾巴', 'Ear': '耳朵',
    'Fillet': '鳍', 'Gills': '鳃', '光暈': '光晕',
    'FrontParts': '前部', 'BackParts': '后部',
    'Back_DevilFire': '后部魔焰', 'Front_DevilFire': '前部魔焰',
    'left blade': '左刃', 'right blade': '右刃',
}

def translation_key(name, path):
    """DefInjected list indexes are zero-based; only li is a list entry."""
    segments = []
    for part in path.split('/'):
        match = re.fullmatch(r'li\[(\d+)\]', part)
        segments.append(str(int(match.group(1)) - 1) if match else re.sub(r'\[1\]$', '', part))
    return name + '.' + '.'.join(segments)

def main():
    translations = {}
    archive = GAME/'Data/Core/Languages/ChineseSimplified (简体中文).tar'
    with tarfile.open(archive) as tar:
        members = [m for m in tar.getmembers() if '/BodyDef/' in '/'+m.name and m.name.endswith('.xml')]
        members.sort(key=lambda m: ('Human' not in m.name, m.name))
        for member in members:
            source = tar.extractfile(member).read().decode('utf-8-sig')
            for original, translated in re.findall(r'<!-- EN: (.*?) -->\s*<[^>]+>(.*?)</', source, re.S):
                translations.setdefault(original.strip(), translated.strip())
    translations.update(SPECIAL)
    report = []
    for mod_id, _ in MODS:
        defs = active_defs(WORKSHOP/mod_id)
        if defs is None:
            continue
        language = ET.Element('LanguageData')
        for file in sorted(defs.rglob('*.xml')):
            for definition in ET.parse(file).getroot():
                if definition.tag != 'BodyDef':
                    continue
                name = text(definition.find('defName'))
                for node, path in iter_nodes_with_paths(definition):
                    if node.tag != 'customLabel' or not text(node):
                        continue
                    original = text(node)
                    translated = translations[original]
                    xpath = f'Defs/BodyDef[defName={xpath_literal(name)}]/{path}'
                    key = translation_key(name, path)
                    ET.SubElement(language, key).text = translated
                    report.append(dict(modId=mod_id, defName=name, xpath=xpath, key=key, source=original, translation=translated, mode='DefInjected'))
        if len(language):
            package = next(Path('Mods').glob(f'{mod_id} - * Chinese'))
            for root in (package, Path('supplemental')/mod_id):
                # PatchOperation changes customLabel BEFORE BodyPartRecord.PostLoad
                # caches untranslatedCustomLabel. HAR uses that cache as identity.
                # Language injection occurs later and preserves the original key.
                legacy = root/'Patches/Aya_Body_CustomLabels.xml'
                if legacy.exists():
                    legacy.unlink()
                target = root/'Languages/ChineseSimplified/DefInjected/BodyDef/Aya_CustomLabels.xml'
                target.parent.mkdir(parents=True, exist_ok=True)
                xml_write(target, language)
    Path('BODY-PART-AUDIT.json').write_text(json.dumps({'count': len(report), 'operations': report}, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(f'Generated {len(report)} body custom-label translations')

if __name__ == '__main__':
    main()
