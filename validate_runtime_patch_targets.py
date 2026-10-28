"""Validate generated Aya runtime-patch XPath targets against active source defs."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from lxml import etree

from build_translations import MODS, WORKSHOP, active_defs


MODS_ROOT = Path("Mods")


def merged_active_defs() -> etree._Element:
    document = etree.Element("root")
    merged = etree.SubElement(document, "Defs")
    for mod_id, _mod_name in MODS:
        defs = active_defs(WORKSHOP / mod_id)
        if defs is None:
            continue
        for file in sorted(defs.rglob("*.xml")):
            try:
                root = etree.parse(str(file)).getroot()
            except etree.XMLSyntaxError:
                continue
            if root.tag != "Defs":
                continue
            for child in root:
                merged.append(child)
    return document


def main() -> None:
    defs = merged_active_defs()
    checked = 0
    missing: list[tuple[str, str]] = []
    find_mod_files: list[str] = []

    def validate_operation(file: Path, node: ET.Element) -> None:
        """Follow the branch RimWorld would execute and validate its write target.

        Conditional XPath expressions are allowed not to resolve: that is the
        purpose of their ``nomatch`` branch.  The old flat scan incorrectly
        reported those tests (and inactive branches) as missing patch targets.
        """
        nonlocal checked
        operation_class = node.get("Class", "")

        if operation_class == "PatchOperationConditional":
            xpath = node.findtext("xpath") or ""
            checked += 1
            branch_name = "match" if defs.xpath(xpath) else "nomatch"
            branch = node.find(branch_name)
            if branch is not None and branch.get("Class"):
                validate_operation(file, branch)
            return

        if operation_class == "PatchOperationSequence":
            operations = node.find("operations")
            if operations is not None:
                for child in operations:
                    if child.get("Class"):
                        validate_operation(file, child)
            return

        if operation_class in {"PatchOperationAdd", "PatchOperationReplace"}:
            xpath = node.findtext("xpath") or ""
            checked += 1
            if not defs.xpath(xpath):
                missing.append((str(file), xpath))

    for package in sorted(MODS_ROOT.glob("* - * Chinese")):
        if package.name.startswith("0000000000"):
            continue
        patch_root = package / "Patches"
        if not patch_root.is_dir():
            continue
        for file in sorted(patch_root.glob("*.xml")):
            root = ET.parse(file).getroot()
            if root.findall('.//Operation[@Class="PatchOperationFindMod"]'):
                find_mod_files.append(str(file))
            for operation in root.findall("./Operation"):
                validate_operation(file, operation)

    if find_mod_files or missing:
        for file in find_mod_files:
            print(f"unexpected PatchOperationFindMod: {file}")
        for file, xpath in missing:
            print(f"missing target: {file}: {xpath}")
        raise SystemExit(1)

    print(
        f"validated {checked} runtime-patch XPath targets; "
        "all resolve against selected active source defs"
    )


if __name__ == "__main__":
    main()
