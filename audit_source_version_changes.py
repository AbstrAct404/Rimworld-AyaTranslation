"""Inventory the installed, Steam-verified 1.6/1.7 source text differences."""
import hashlib
import json
from collections import Counter
from pathlib import Path
from lxml import etree as E
from build_translations import MODS, WORKSHOP, FIELDS
from audit_summon_equipment_translations import FIELDS as EXTRA

def inventory(folder):
    values = Counter()
    bodies = {}
    classes = Counter()
    for file in sorted(folder.rglob('*.xml')):
        for definition in E.parse(str(file)).getroot():
            if not isinstance(definition.tag, str):
                continue
            name = definition.findtext('defName') or definition.get('Name', '')
            if not name:
                continue
            if definition.tag in {'BodyDef','BodyPartDef'}:
                bodies[(definition.tag,name)] = E.tostring(definition,method='c14n',with_comments=False).decode()
            for node in definition.iter():
                if node.get('Class') and ('Skill' in node.get('Class') or 'Summon' in node.get('Class')):
                    classes[node.get('Class')] += 1
                value = (node.text or '').strip().replace('\\n','\n')
                if node.tag in FIELDS | EXTRA and value and not len(node):
                    values[(definition.tag,name,node.tag,value)] += 1
    return values, bodies, classes

def main():
    remote = json.loads(Path('STEAM-REMOTE-DETAILS.json').read_text(encoding='utf-8'))['response']['publishedfiledetails']
    by_id = {x['publishedfileid']: x for x in remote}
    acf = Path(r'D:\SteamLibrary\steamapps\workshop\appworkshop_294100.acf').read_text()
    import re
    report = []
    for mid,name in MODS:
        root = WORKSHOP/mid
        old,old_bodies,old_classes = inventory(root/'1.6/Defs')
        new,new_bodies,new_classes = inventory(root/'1.7/Defs')
        metadata = by_id[mid]
        block = re.search('"'+mid+r'"\s*\{([^{}]*)\}',acf)
        local = dict(re.findall(r'"([^"\n]+)"\s+"([^"\n]+)"',block[1]))
        assert str(metadata['time_updated']) == local['timeupdated'], mid+' is stale'
        files = {str(f.relative_to(root)): hashlib.sha256(f.read_bytes()).hexdigest()
                 for f in root.rglob('*') if f.is_file() and (f.suffix=='.xml' or f.suffix=='.dll') and ('1.7' in f.parts or 'About' in f.parts)}
        report.append(dict(modId=mid,name=name,timeUpdated=metadata['time_updated'],localMatchesSteam=True,hashes=files,
                           addedText=[dict(type=k[0],defName=k[1],field=k[2],source=k[3],count=v) for k,v in (new-old).items()],
                           addedBodyDefs=[list(k) for k in new_bodies.keys()-old_bodies.keys()],
                           bodyDefinitionChanges=[list(k) for k in new_bodies.keys() & old_bodies.keys() if new_bodies[k]!=old_bodies[k]],
                           oldSkillClasses=dict(old_classes),newSkillClasses=dict(new_classes)))
    Path('SOURCE-1.7-DELTA.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Verified current Steam timestamps and recorded source hashes for',len(report),'mods')

if __name__=='__main__':
    main()
