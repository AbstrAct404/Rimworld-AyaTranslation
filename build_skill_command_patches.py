"""Generate translation patches for nested custom skill command text."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path

from build_translations import MODS, WORKSHOP, active_defs, text, xml_write


MODS_ROOT = Path("Mods")
TRANSLATIONS = Path("skill_command_translations.json")
FIELDS = {
    "commandLabel": "labels",
    "commandDesc": "descriptions",
    "CommandLabel": "labels",
    "CommandDesc": "descriptions",
    "AutoLabel": "labels",
    "AutoDesc": "descriptions",
}
# Several Aya consumables define their right-click verb in a nested component
# rather than in a translatable Def field.  Preserve the item placeholder and
# translate the Japanese verb at the component level.
EXTRA_FIELD_TRANSLATIONS = {
    "useLabel": {
        "{0} を使用する": "使用 {0}",
        "{0} を使用して能力を獲得する": "使用 {0} 以获得能力",
        "Activate {0_label}": "激活 {0_label}",
    },
}
OUTPUT_NAME = "Aya_Skill_Command_Translations.xml"


def xpath_literal(value: str) -> str:
    if '"' not in value:
        return f'"{value}"'
    if "'" not in value:
        return f"'{value}'"
    raise ValueError(f"XPath value contains both quote styles: {value!r}")


def iter_nodes_with_paths(
    parent: ET.Element, prefix: str = ""
) -> list[tuple[ET.Element, str]]:
    """Return descendants with resilient source-structural XPath fragments.

    Custom skill components have a stable CLR ``Class`` name but their ordinal
    position in ``comps`` can change when an upstream update adds a component.
    Prefer the class selector for a uniquely named component; retain the
    positional form where a class is absent or repeated, so every selector
    remains unambiguous.
    """

    found: list[tuple[ET.Element, str]] = []
    positions: dict[str, int] = {}
    class_counts: dict[str, int] = {}
    for child in parent:
        if child.tag == "li" and child.get("Class"):
            class_name = child.get("Class", "")
            class_counts[class_name] = class_counts.get(class_name, 0) + 1
    for child in parent:
        positions[child.tag] = positions.get(child.tag, 0) + 1
        class_name = child.get("Class", "")
        if (
            child.tag == "li"
            and class_name
            and class_counts.get(class_name) == 1
        ):
            fragment = f"li[@Class={xpath_literal(class_name)}]"
        elif child.tag == "li" and class_name:
            # Repeated component classes need one more discriminator.  The
            # field-specific predicate is filled when generating the patch,
            # allowing e.g. three CommandExplosive instances to survive a
            # component-order change without one patch selecting the others.
            fragment = f"li[@Class={xpath_literal(class_name)}]__AYA_FIELD_ID__"
        else:
            fragment = f"{child.tag}[{positions[child.tag]}]"
        path = f"{prefix}/{fragment}" if prefix else fragment
        found.append((child, path))
        found.extend(iter_nodes_with_paths(child, path))
    return found


def main() -> None:
    translations = json.loads(TRANSLATIONS.read_text(encoding="utf-8"))
    generated: list[dict[str, object]] = []
    missing: list[dict[str, str]] = []

    for mod_id, mod_name in MODS:
        source = WORKSHOP / mod_id
        defs = active_defs(source)
        package = next(MODS_ROOT.glob(f"{mod_id} - * Chinese"), None)
        if defs is None or package is None:
            continue
        source_about = ET.parse(source / "About" / "About.xml").getroot()
        # Keep the package ID in the audit report.  Patch activation itself is
        # based on target Def existence below because PatchOperationFindMod
        # expects a display name rather than this stable identifier.
        source_package_id = text(source_about.find("packageId"))
        operations: list[tuple[str, str, str, str, str, str, str]] = []

        for file in defs.rglob("*.xml"):
            try:
                root = ET.parse(file).getroot()
            except ET.ParseError:
                continue
            for definition in root:
                def_name = text(definition.find("defName"))
                if def_name:
                    definition_xpath = (
                        f"Defs/{definition.tag}[defName={xpath_literal(def_name)}]"
                    )
                else:
                    def_name = definition.get("Name", "")
                    definition_xpath = (
                        f"Defs/{definition.tag}[@Name={xpath_literal(def_name)}]"
                    )
                if not def_name:
                    continue
                for node, relative_path in iter_nodes_with_paths(definition):
                    if node.tag not in FIELDS and node.tag not in EXTRA_FIELD_TRANSLATIONS:
                        continue
                    if not text(node):
                        continue
                    original = text(node)
                    if node.tag in EXTRA_FIELD_TRANSLATIONS:
                        translated = EXTRA_FIELD_TRANSLATIONS[node.tag].get(original)
                    else:
                        translated = translations[FIELDS[node.tag]].get(original)
                    if translated is None and r"\n" in original:
                        translated = translations[FIELDS[node.tag]].get(
                            original.replace(r"\n", "\n")
                        )
                    if translated is None:
                        missing.append({
                            "modId": mod_id,
                            "mod": mod_name,
                            "defName": def_name,
                            "field": node.tag,
                            "source": original,
                        })
                        continue
                    translated = translated.replace("\n", r"\n")
                    xpath = f"{definition_xpath}/{relative_path}"
                    if "__AYA_FIELD_ID__" in xpath:
                        xpath = xpath.replace(
                            "__AYA_FIELD_ID__",
                            f"[{node.tag}={xpath_literal(original)}]",
                        )
                    operations.append(
                        (
                            definition.tag,
                            def_name,
                            definition_xpath,
                            node.tag,
                            original,
                            xpath,
                            translated,
                        )
                    )

        patch_path = package / "Patches" / OUTPUT_NAME
        if not operations:
            if patch_path.exists():
                patch_path.unlink()
            continue

        patch = ET.Element("Patch")
        for (
            def_type,
            def_name,
            _definition_xpath,
            field,
            original,
            xpath,
            translated,
        ) in operations:
            conditional = ET.SubElement(
                patch, "Operation", {"Class": "PatchOperationConditional"}
            )
            ET.SubElement(conditional, "success").text = "Always"
            ET.SubElement(conditional, "xpath").text = xpath
            operation = ET.SubElement(
                conditional, "match", {"Class": "PatchOperationReplace"}
            )
            ET.SubElement(operation, "xpath").text = xpath
            value = ET.SubElement(operation, "value")
            ET.SubElement(value, field).text = translated
            generated.append({
                "modId": mod_id,
                "mod": mod_name,
                "sourcePackageId": source_package_id,
                "defType": def_type,
                "defName": def_name,
                "field": field,
                "source": original,
                "xpath": xpath,
                "translation": translated,
            })
        patch_path.parent.mkdir(parents=True, exist_ok=True)
        xml_write(patch_path, patch)

    report = {
        "generatedOperations": len(generated),
        "missingTranslations": missing,
        "operations": generated,
    }
    Path("SKILL-COMMAND-PATCH-REPORT.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if missing:
        raise SystemExit(
            f"missing {len(missing)} command translations; see "
            "SKILL-COMMAND-PATCH-REPORT.json"
        )
    print(json.dumps({
        "generatedOperations": len(generated),
        "missingTranslations": 0,
        "report": "SKILL-COMMAND-PATCH-REPORT.json",
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
