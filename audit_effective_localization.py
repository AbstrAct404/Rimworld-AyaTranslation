"""Execute integrated XML patches, then check the resulting visible leaves.

Unlike coverage by XPath string comparison, this catches a conditional that
silently misses a renamed component. Optional EX defs are included for coverage.
This is a static load simulation, not a claim of an in-game play test.
"""
import copy
import json
import re
from pathlib import Path
from lxml import etree as E
from build_translations import MODS, WORKSHOP, active_defs, FIELDS
from audit_summon_equipment_translations import FIELDS as EXTRA_FIELDS

PACKAGE = Path('Mods/0000000000 - Aya Integrated Chinese')

def main():
    root = E.Element('root')
    defs = E.SubElement(root, 'Defs')
    document = E.ElementTree(root)
    rows = []
    for mod_id, _ in MODS:
        folder = active_defs(WORKSHOP/mod_id)
        if folder is None:
            continue
        for file in sorted(folder.rglob('*.xml')):
            source = E.parse(str(file)).getroot()
            if source.tag != 'Defs':
                continue
            for definition in source:
                if not isinstance(definition.tag, str):
                    continue
                defs.append(definition)
                name = definition.findtext('defName') or definition.get('Name', '')
                if not name:
                    continue
                for node in definition.iterdescendants():
                    if not isinstance(node.tag, str) or len(node) or node.tag not in FIELDS | EXTRA_FIELDS:
                        continue
                    value = (node.text or '').strip()
                    if not value or value == '[PAWN_nameDef]':
                        continue
                    if node.tag not in {'customLabel'} and not re.search(r'[A-Za-z\u3040-\u30ff\u4e00-\u9fff]', value):
                        continue
                    relative = document.getpath(node)[len(document.getpath(definition))+1:]
                    rows.append(dict(modId=mod_id, type=definition.tag, name=name,
                                     path=document.getpath(node), relative=relative, source=value))
    counts = {'replaced': 0, 'added': 0, 'skippedConditions': 0}
    def apply(op):
        kind = op.get('Class', '')
        if kind == 'PatchOperationConditional':
            matches = document.xpath(op.findtext('xpath'))
            branch = op.find('match' if matches else 'nomatch')
            if not matches:
                counts['skippedConditions'] += 1
            if branch is not None:
                apply(branch)
        elif kind == 'PatchOperationSequence':
            for child in op.findall('operations/li'):
                apply(child)
        elif kind in {'PatchOperationReplace', 'PatchOperationAdd'}:
            nodes = document.xpath(op.findtext('xpath'))
            if not nodes:
                raise AssertionError('Executed patch missed: '+op.findtext('xpath'))
            for target in nodes:
                values = list(op.find('value'))
                if kind == 'PatchOperationReplace':
                    assert len(values) == 1
                    target.getparent().replace(target, copy.deepcopy(values[0]))
                    counts['replaced'] += 1
                else:
                    for value in values:
                        target.append(copy.deepcopy(value))
                    counts['added'] += 1
        elif kind:
            raise AssertionError('Unsupported operation '+kind)
    for file in sorted((PACKAGE/'Patches').glob('*.xml')):
        for op in E.parse(str(file)).getroot():
            apply(op)
    translations = {}
    for file in (PACKAGE/'Languages/ChineseSimplified/DefInjected').rglob('*.xml'):
        for node in E.parse(str(file)).getroot():
            translations[(file.parent.name, node.tag)] = (node.text or '').strip()
    missing = []
    checked = 0
    for row in rows:
        node = document.xpath(row['path'])
        after = (node[0].text or '').strip() if node else ''
        key_path = re.sub(r'li(?:\[(\d+)\])?', lambda m: str(int(m.group(1) or '1')-1), row['relative'])
        key_path = re.sub(r'\[1\]', '', key_path)
        key = row['name']+'.'+key_path.replace('/', '.')
        translated = translations.get((row['type'], key))
        if translated:
            after = translated
        checked += 1
        if after == row['source'] and translated is None:
            if re.fullmatch(r'(?:Lv\d+|EN:\d+%)', after) or not re.search(r'[A-Za-z\u3040-\u30ff]', after):
                continue
            # Identifier-only values are excluded except explicit body names.
            if re.fullmatch(r'[A-Za-z0-9_.]+', after) and row['relative'].split('/')[-1].split('[')[0] not in {'label','customLabel','description','reportString','commandLabel'}:
                continue
            missing.append(dict(row, effective=after))
    report = dict(checked=checked, patchExecution=counts, missingCount=len(missing), missing=missing)
    Path('EFFECTIVE-LOCALIZATION-AUDIT.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='missing'}))
    if missing:
        raise SystemExit(1)

if __name__ == '__main__':
    main()
