"""Audit summon names/descriptions, summon drops, equipment text and other
Japanese residuals against the Chinese packages.

Coverage is checked across every Chinese pack (DefInjected, supplemental and
runtime Patches) so that MayRequire-gated defs translated in their extension
pack (e.g. Chaoura UB) are not reported as false positives.
"""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

from build_translations import MODS, WORKSHOP, active_defs


MODS_ROOT = Path("Mods")
SUPP = Path("supplemental")
REPORT = Path("SUMMON-EQUIPMENT-AUDIT.json")
JAPANESE = re.compile(
    r"[\u3040-\u30ff\u31f0-\u31ff\u3400-\u4dbf\u4e00-\u9fff]"
)

# Top-level or nested leaf fields that are game-visible text.
FIELDS = {
    "label", "description", "labelMale", "labelFemale", "labelNoun",
    "title", "titleShort", "baseDesc", "jobString", "reportString", "verb",
    "gerund", "beginLetter", "recoveryMessage", "discoveredLetterText",
    "letterLabel", "letterText", "fixedName", "pawnSingular", "pawnPlural",
    "pawnsPlural", "commandLabel", "commandDesc", "AutoLabel", "AutoDesc",
    "CommandLabel", "CommandDesc", "useLabel", "summary", "name",
    "commandName",
}


def load_definjected(pkg: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    root = pkg / "Languages" / "ChineseSimplified" / "DefInjected"
    if not root.is_dir():
        return out
    for file in root.rglob("*.xml"):
        try:
            language = ET.parse(file).getroot()
        except ET.ParseError:
            continue
        for node in language:
            out[node.tag] = (node.text or "").strip()
    return out


def patch_targets(pkg: Path) -> list[tuple[str, str, list[str]]]:
    """Extract (defType, defName, normalized path parts) from every patch
    xpath.  The def type is kept so a patch that targets, say, a HediffDef
    label is not mistaken for coverage of a same-named ThoughtDef stage."""
    out: list[tuple[str, str, list[str]]] = []
    root = pkg / "Patches"
    if not root.is_dir():
        return out
    for file in root.rglob("*.xml"):
        try:
            patch = ET.parse(file).getroot()
        except ET.ParseError:
            continue
        for element in patch.iter():
            if element.find("xpath") is None:
                continue
            xpath = (element.findtext("xpath") or "").strip()
            if not xpath:
                continue
            match = re.search(
                r'\[(?:defName|@Name)\s*=\s*"([^"]+)"\]', xpath
            )
            parts = [
                re.sub(r"\[.*?\]", "", part)
                for part in xpath.split("/")[2:]
            ] if xpath.startswith("Defs/") else []
            def_type = (
                re.sub(r"\[.*?\]", "", xpath.split("/")[1])
                if xpath.startswith("Defs/") else ""
            )
            out.append((def_type, match.group(1) if match else "", parts))
    return out


def walk_leaves(element: ET.Element, path: str):
    for child in element:
        child_path = f"{path}/{child.tag}"
        if child.text and child.text.strip() and not list(child):
            yield child_path, child.text.strip()
        else:
            yield from walk_leaves(child, child_path)


def main() -> None:
    # Global coverage index across every Chinese pack, so extension-pack
    # translations (e.g. Chaoura UB defs living inside the base mod) count.
    translations: dict[str, str] = {}
    patches: list[tuple[str, str, list[str]]] = []
    for mod_id, _ in MODS:
        package = next(MODS_ROOT.glob(f"{mod_id} - * Chinese"), None)
        if package is None:
            continue
        translations.update(load_definjected(package))
        patches.extend(patch_targets(package))
        supplemental = SUPP / mod_id
        if supplemental.is_dir():
            translations.update(load_definjected(supplemental))
            patches.extend(patch_targets(supplemental))

    missing: list[dict[str, str]] = []
    by_type: Counter[tuple[str, str]] = Counter()

    for mod_id, mod_name in MODS:
        source = WORKSHOP / mod_id
        defs = active_defs(source)
        if defs is None:
            continue
        for file in defs.rglob("*.xml"):
            try:
                root = ET.parse(file).getroot()
            except ET.ParseError:
                continue
            for definition in root:
                def_name = (
                    (definition.findtext("defName") or "").strip()
                    or definition.get("Name", "").strip()
                )
                if not def_name:
                    continue
                for path, value in walk_leaves(definition, ""):
                    leaf = path.rsplit("/", 1)[-1]
                    if leaf not in FIELDS:
                        continue
                    if not JAPANESE.search(value):
                        continue
                    if re.fullmatch(r"[\d\s.,%\-+<>\[\]]+", value):
                        continue
                    if re.fullmatch(r"[A-Za-z0-9_.]+", value):
                        continue
                    parts = path.split("/")[1:]
                    if not covered(
                        definition.tag, def_name, parts, leaf,
                        translations, patches,
                    ):
                        by_type[(definition.tag, leaf)] += 1
                        missing.append({
                            "modId": mod_id,
                            "mod": mod_name,
                            "defType": definition.tag,
                            "defName": def_name,
                            "field": path,
                            "japanese": value,
                        })

    data = {
        "missingCount": len(missing),
        "byType": {
            f"{def_type}.{field}": count
            for (def_type, field), count in by_type.most_common()
        },
        "missing": missing,
    }
    REPORT.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(data, ensure_ascii=False, indent=2))


def covered(
    def_type: str,
    def_name: str,
    parts: list[str],
    leaf: str,
    translations: dict[str, str],
    patches: list[tuple[str, str, list[str]]],
) -> bool:
    key = f"{def_name}.{'.'.join(parts)}"
    if key in translations:
        return True
    if "li" in parts:
        for index in range(8):
            if key.replace(".li.", f".{index}.") in translations:
                return True
    for patch_type, patch_def, patch_parts in patches:
        if patch_type and patch_type != def_type:
            continue
        if patch_def and patch_def not in (def_name,):
            continue
        if not patch_parts or patch_parts[-1] != leaf:
            continue
        patch_mid = patch_parts[:-1]
        if patch_mid == parts[:-1] or (
            patch_mid and parts[:-1][-len(patch_mid):] == patch_mid
        ):
            return True
    return False


if __name__ == "__main__":
    main()
