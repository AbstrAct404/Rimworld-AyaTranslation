"""Fail closed if a maintained translation package contains non-text overrides.

The preview under About is not a game texture. BodyDef.customLabel is display
text AND a cached identity in BodyPartRecord.PostLoad, so only DefInjected may
translate it; XML PatchOperation must never rewrite the source value.
"""
import json
import re
from pathlib import Path
import xml.etree.ElementTree as E

TEXT_LEAVES = {
    'label', 'description', 'summary', 'commandLabel', 'commandDesc',
    'CommandLabel', 'CommandDesc', 'AutoLabel', 'AutoDesc', 'useLabel',
    'ingestCommandString', 'ingestReportString', 'textKey',
}
RESEARCH_TEXT = {'generalTitle', 'generalDescription'}
PRIORITY = 'Defs/GeneCategoryDef[defName="Aya_Race_GeneCategory_ChaouraUB"]/displayPriorityInXenotype'

def inspect_package(package):
    errors = []
    counts = {'patchModifiers': 0, 'bodyDisplayTranslations': 0, 'previewImages': 0}
    for file in sorted(package.rglob('*')):
        if not file.is_file():
            continue
        parts = file.relative_to(package).parts
        if any(p.lower() in {'textures', 'sounds', 'meshes', 'materials', 'shaders', 'defs'} for p in parts):
            errors.append(f'Game resources/defs included: {file}')
        if file.suffix.lower() in {'.png', '.jpg', '.jpeg', '.dds', '.tga', '.wav', '.ogg', '.mp3', '.shader', '.asset', '.bundle'}:
            if parts == ('About', 'Preview.png'):
                counts['previewImages'] += 1
            else:
                errors.append(f'Non-preview asset: {file}')
        if file.suffix.lower() != '.xml':
            continue
        tree = E.parse(file).getroot()
        if 'DefInjected' in parts:
            for entry in tree:
                key = entry.tag
                if any(x in key for x in ('.alienRace.', '.graphicData.', '.renderTree.', '.texPath', '.shader', '.statBases.')):
                    errors.append(f'Render/gameplay language override: {file}: {key}')
                if 'BodyDef' in parts and key.endswith('.customLabel'):
                    counts['bodyDisplayTranslations'] += 1
        if 'Patches' not in parts:
            continue
        for op in tree.iter():
            kind = op.get('Class')
            if kind not in {'PatchOperationReplace', 'PatchOperationAdd', 'PatchOperationRemove'}:
                continue
            counts['patchModifiers'] += 1
            xpath = op.findtext('xpath') or ''
            leaf = re.sub(r'\[.*', '', xpath.rsplit('/', 1)[-1])
            value = op.find('value')
            fields = {n.tag for n in value} if value is not None else set()
            if kind == 'PatchOperationReplace' and leaf in TEXT_LEAVES and fields == {leaf} and '/alienRace/' not in xpath:
                continue
            if kind == 'PatchOperationAdd' and xpath.startswith('Defs/ResearchTabDef[') and fields <= RESEARCH_TEXT and fields:
                continue
            # Existing, explicitly reviewed UI-only category sorting fix.
            if kind == 'PatchOperationReplace' and xpath == PRIORITY and op.findtext('value/displayPriorityInXenotype') == '-460':
                continue
            errors.append(f'Non-text/identity patch: {file}: {kind}: {xpath}')
    return {'package': package.name, **counts, 'violations': errors}

def main():
    packages = sorted(p for p in Path('Mods').glob('* Chinese') if (p/'About/About.xml').is_file())
    rows = [inspect_package(p) for p in packages]
    report = {'packages': len(rows), 'violations': sum(len(r['violations']) for r in rows), 'results': rows,
              'scope': 'XML and packaged assets; runtime DLL source requires separate review; not an in-game rendering test'}
    Path('TRANSLATION-SAFETY-AUDIT.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k != 'results'}, ensure_ascii=False))
    for row in rows:
        for error in row['violations']:
            print(error)
    if report['violations']:
        raise SystemExit(1)

if __name__ == '__main__':
    main()
