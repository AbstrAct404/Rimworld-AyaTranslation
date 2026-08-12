"""Build one optional Aya Simplified Chinese language pack from all standalones.

The integrated package deliberately uses ``loadAfter`` rather than mandatory
Workshop dependencies, matching the reference pack's "install only the races
you use" behavior.  Duplicate language keys are merged deterministically and
reported for review.
"""

from __future__ import annotations

import argparse
import json
import shutil
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

import build_translations as build
from optimize_runtime_patches import package_patch_index


INTEGRATED_FOLDER = "0000000000 - Aya Integrated Chinese"
PACKAGE_ID = "abstract404.aya.integrated.zh"
PUBLISHED_FILE_ID = "3770548798"

# The integrated localization must always load after every official Aya
# package that it can translate.  Keep this baseline independent from which
# standalone localization folders happen to be present during a rebuild:
# otherwise an omitted EX localization folder can silently remove the EX
# ordering rule and place the integrated pack above that EX in a mod manager.
INTEGRATED_LOAD_AFTER = (
    "Ayameduki.AyaRacePremise",
    "Ayameduki.IdeaStoryteller",
    "Ayameduki.AyaCanaanIntellect",
    "Ayameduki.HARChaoura",
    "Ayameduki.HAREveliet",
    "Ayameduki.HARIdearn",
    "Ayameduki.HARIdhale",
    "Ayameduki.HARLittluna",
    "Ayameduki.HARNearmare",
    "Ayameduki.HARNeclose",
    "Ayameduki.HARNexaga",
    "Ayameduki.HAROuterm",
    "Ayameduki.HARQualeela",
    "Ayameduki.HARSaclean",
    "Ayameduki.HARSilkiera",
    "Ayameduki.HARSolark",
    "Ayameduki.HARXenoorca",
    "Ayameduki.HARZoichor",
    "Ayameduki.BOSSRequeen",
    "Ayameduki.BOSSEnforcer",
    "Ayameduki.HARChaouraUB",
    # Optional upper-race switches/extensions.
    "Ayameduki.HARIdhaleEX",
    "Ayameduki.HARLittlunaEX",
    "Ayameduki.HARNearmareEX",
    "Ayameduki.HARNecloseEX",
    "Ayameduki.HARNecloseUC",
    "Ayameduki.HARSilkieraEX",
    "Ayameduki.HARSolarkEX",
    "Ayameduki.HARXenoorcaEX",
    # Mechanoids: Total Warfare incorrectly defines the global GoBack key as
    # “返回目录”.  Load after it so the integrated pack can restore RimWorld's
    # generic “返回” label without modifying that unrelated Workshop mod.
    "Nyar.NCLvsTW",
    # Call A Trader supplies English fallback text for its request button.
    "arakos.callatrader.acat",
)

ORIGINAL_WORKSHOP_TITLES = {
    "2946679071": "[Aya]Chaoura Race",
    "3505571618": "[Aya]Aya Premise Core",
    "3153539856": "[Aya]Eveliet Race",
    "2954714860": "[Aya]Idea Storyteller",
    "2871413100": "[Aya]Idearn Race",
    "2227425882": "[Aya]Idhale Race",
    "2569091688": "[Aya]Littluna Race",
    "2198830432": "[Aya]Nearmare Race",
    "2394460334": "[Aya]Neclose Race",
    "2763078885": "[Aya]Qualeela Race",
    "2504657401": "[Aya]Requeen Boss",
    "2676302514": "[Aya]Saclean Race",
    "2233666290": "[Aya]Silkiera Race",
    "2608237489": "[Aya]Solark Race",
    "2216916011": "[Aya]Xenoorca Race",
    "3750626266": "[Aya]Canaan Intellect",
    "3489429571": "[Aya]Chaoura UB",
    "2729712799": "[Aya]Enforcer Boss",
    "2706009136": "[Aya]Nexaga Race",
    "3675887482": "[Aya]Outerm Race",
    "3477749439": "[Aya]Zoichor Race",
}

DISPLAY_GROUPS = [
    ("核心与叙事", ["3505571618", "2954714860", "3750626266"]),
    (
        "人工种族",
        [
            "2946679071", "3153539856", "2871413100", "2227425882",
            "2569091688", "2198830432", "2394460334", "2706009136",
            "3675887482", "2763078885", "2676302514", "2233666290",
            "2608237489", "2216916011", "3477749439",
        ],
    ),
    ("高难度与首领", ["2504657401", "2729712799", "3489429571"]),
]


def read_about(package: Path) -> tuple[str, str, str]:
    root = ET.parse(package / "About" / "About.xml").getroot()
    original_id = package.name.split(" ", 1)[0]
    dependency = build.text(root.find("./modDependencies/li/packageId"))
    title = build.text(root.find("name"))
    return original_id, dependency, title


def assert_unique_package_patch_targets(package: Path) -> None:
    """Reject accidental legacy/generated overlap before integrating patches."""
    duplicates = {
        xpath: files
        for xpath, files in package_patch_index(package).items()
        if len(files) > 1
    }
    if not duplicates:
        return
    xpath, files = next(iter(duplicates.items()))
    raise RuntimeError(
        f"{package.name}: duplicate runtime patch target {xpath} in "
        + ", ".join(files)
        + "; run optimize_runtime_patches.py before rebuilding the integrated pack"
    )


def markdown_label(value: object) -> str:
    """Escape brackets in Workshop titles used as Markdown link labels."""
    return str(value).replace("[", r"\[").replace("]", r"\]")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mods-root", type=Path, default=Path("Mods"))
    parser.add_argument("--steam-vdf-dir", type=Path)
    parser.add_argument(
        "--steam-content-root",
        type=Path,
        help="Optional ASCII-safe mod root referenced by generated Steam VDF files.",
    )
    args = parser.parse_args()

    mods_root = args.mods_root
    output = mods_root / INTEGRATED_FOLDER
    if output.exists():
        shutil.rmtree(output)
    (output / "About").mkdir(parents=True)

    packages = sorted(
        package
        for package in mods_root.glob("[0-9]* - * Chinese")
        if package.name != INTEGRATED_FOLDER
        and (package / "Languages" / "ChineseSimplified").is_dir()
    )
    # Start with the complete official baseline, then append any newly
    # discovered dependency from standalone packs.  This makes auto-sorting
    # deterministic even when only part of the standalone set is available.
    load_after: list[str] = list(INTEGRATED_LOAD_AFTER)
    package_info: list[dict[str, object]] = []
    # (section, subtype) -> key -> (value, source ID)
    buckets: dict[tuple[str, str], dict[str, tuple[str, str]]] = defaultdict(dict)
    conflicts: list[dict[str, str]] = []
    integrated_patch_signatures: set[str] = set()

    for package in packages:
        assert_unique_package_patch_targets(package)
        original_id, dependency, translation_title = read_about(package)
        if dependency and dependency not in load_after:
            load_after.append(dependency)
        for optional_dependency in build.OPTIONAL_LOAD_AFTER.get(original_id, []):
            if optional_dependency not in load_after:
                load_after.append(optional_dependency)
        entry_count = 0
        language_root = package / "Languages" / "ChineseSimplified"
        for file in sorted(language_root.rglob("*.xml")):
            relative = file.relative_to(language_root)
            if len(relative.parts) < 2:
                continue
            section, subtype = relative.parts[0], relative.parts[1]
            if section not in {"DefInjected", "Keyed"}:
                continue
            if section == "Keyed":
                subtype = "Keyed"
            try:
                root = ET.parse(file).getroot()
            except ET.ParseError:
                continue
            bucket = buckets[(section, subtype)]
            for child in root:
                value = build.text(child)
                if not value:
                    continue
                entry_count += 1
                previous = bucket.get(child.tag)
                if previous and previous[0] != value:
                    conflicts.append({
                        "key": child.tag,
                        "keptValue": previous[0],
                        "keptFrom": previous[1],
                        "ignoredValue": value,
                        "ignoredFrom": original_id,
                    })
                    continue
                bucket[child.tag] = (value, original_id)
        patch_root = package / "Patches"
        if patch_root.is_dir():
            for patch_file in sorted(patch_root.rglob("*.xml")):
                relative_patch = patch_file.relative_to(patch_root)
                # RimWorld patch discovery must not depend on recursive
                # traversal.  Keep every patch immediately under Patches and
                # prefix it with the source Workshop ID to prevent collisions.
                destination_patch = (
                    output
                    / "Patches"
                    / f"{original_id}_{relative_patch.name}"
                )
                # Different standalone packs can carry the same fallback
                # operation for a shared DefName.  Keep one byte-equivalent
                # operation in the integrated pack instead of executing it
                # repeatedly; differing values are retained for conflict
                # review rather than silently changing translation priority.
                try:
                    patch_root_xml = ET.parse(patch_file).getroot()
                    kept_operations = []
                    for operation in list(patch_root_xml):
                        signature = ET.tostring(operation, encoding="unicode")
                        if signature in integrated_patch_signatures:
                            continue
                        integrated_patch_signatures.add(signature)
                        kept_operations.append(operation)
                    if not kept_operations:
                        continue
                    patch_root_xml[:] = kept_operations
                    destination_patch.parent.mkdir(parents=True, exist_ok=True)
                    build.xml_write(destination_patch, patch_root_xml)
                except ET.ParseError:
                    destination_patch.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(patch_file, destination_patch)
        # A small Harmony shim is required only where an original assembly
        # hard-codes UI text that DefInjected/PatchOperation cannot localize.
        # Keep its filename intact: the CLR uses the assembly metadata name,
        # but a stable file name simplifies diagnosis in RimWorld's log.
        assembly_root = package / "Assemblies"
        if assembly_root.is_dir():
            for assembly_file in sorted(assembly_root.glob("*.dll")):
                destination_assembly = output / "Assemblies" / assembly_file.name
                destination_assembly.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(assembly_file, destination_assembly)
        package_info.append({
            "originalWorkshopId": original_id,
            "originalTitle": ORIGINAL_WORKSHOP_TITLES.get(original_id, dependency),
            "translationWorkshopId": build.PUBLISHED_FILE_IDS.get(original_id, "0"),
            "translationTitle": translation_title,
            "folder": package.name,
            "entriesRead": entry_count,
        })

    package_by_id = {
        str(item["originalWorkshopId"]): item for item in package_info
    }

    def workshop_directory() -> str:
        sections = []
        sequence = 1
        for group_name, ids in DISPLAY_GROUPS:
            lines = [f"[h2]{group_name}[/h2]"]
            for original_id in ids:
                item = package_by_id[original_id]
                translation_id = str(item["translationWorkshopId"])
                translation_url = (
                    "https://steamcommunity.com/sharedfiles/filedetails/"
                    f"?id={translation_id}"
                )
                original_url = (
                    "https://steamcommunity.com/sharedfiles/filedetails/"
                    f"?id={original_id}"
                )
                lines.extend([
                    (
                        f"[b]{sequence:02d}｜[url={translation_url}]"
                        f"{item['translationTitle']}[/url][/b]"
                    ),
                    (
                        f"原模组：[url={original_url}]"
                        f"{item['originalTitle']}[/url]"
                    ),
                    "",
                ])
                sequence += 1
            sections.append("\n".join(lines).rstrip())
        return "\n\n".join(sections)

    def plain_directory() -> str:
        sections = []
        sequence = 1
        for group_name, ids in DISPLAY_GROUPS:
            lines = [f"【{group_name}】"]
            for original_id in ids:
                item = package_by_id[original_id]
                lines.extend([
                    f"{sequence:02d}｜{item['translationTitle']}",
                    f"    原模组：{item['originalTitle']}",
                ])
                sequence += 1
            sections.append("\n".join(lines))
        return "\n\n".join(sections)

    def markdown_directory() -> str:
        sections = []
        sequence = 1
        for group_name, ids in DISPLAY_GROUPS:
            lines = [f"### {group_name}"]
            for original_id in ids:
                item = package_by_id[original_id]
                translation_id = str(item["translationWorkshopId"])
                lines.extend([
                    (
                        f"{sequence}. **[{markdown_label(item['translationTitle'])}]"
                        "(https://steamcommunity.com/sharedfiles/filedetails/"
                        f"?id={translation_id})**"
                    ),
                    (
                        f"   - 原模组：[{markdown_label(item['originalTitle'])}]"
                        "(https://steamcommunity.com/sharedfiles/filedetails/"
                        f"?id={original_id})"
                    ),
                ])
                sequence += 1
            sections.append("\n".join(lines))
        return "\n\n".join(sections)

    # Core dialogs used by several Aya mods reference this shared key.  Keep
    # the correction in the generated integrated pack instead of relying on a
    # hand-added file that would disappear on the next rebuild.
    buckets[("Keyed", "Keyed")]["GoBack"] = ("返回", "integrated-fix")
    buckets[("Keyed", "Keyed")]["acat.traderletter.accept"] = (
        "请求派遣：{0}",
        "integrated-fix",
    )

    written = 0
    for (section, subtype), values in sorted(buckets.items()):
        root = ET.Element("LanguageData")
        for key, (value, _source_id) in sorted(values.items()):
            ET.SubElement(root, key).text = value
            written += 1
        if section == "DefInjected":
            destination = (
                output
                / "Languages"
                / "ChineseSimplified"
                / "DefInjected"
                / subtype
                / "Aya_Integrated.xml"
            )
        else:
            destination = (
                output
                / "Languages"
                / "ChineseSimplified"
                / "Keyed"
                / "Aya_Integrated.xml"
            )
        destination.parent.mkdir(parents=True, exist_ok=True)
        build.xml_write(destination, root)

    about = ET.Element("ModMetaData")
    description = (
        "Aya 人工种族系列简体中文整合汉化包。\n\n"
        "可只安装自己使用的原模组，无需安装整合包支持的全部种族。"
        "请将本汉化置于所有 Aya 原模组之后加载；不要与对应的独立汉化包同时启用。\n\n"
        "【EX 扩展说明】\n"
        "Idhale EX、Littluna EX、Nearmare EX、Neclose EX、Silkiera EX、Solark EX、Xenoorca EX "
        "等原作者 EX 模组是上位种内容的启用开关。上位种的 Def、代码与资源位于对应种族本体中；"
        "未安装或未启用 EX 时，这些条件内容不会载入。RimWorld 1.5/1.6 如需使用上位种，"
        "请同时安装并启用对应的原 EX 模组。只有 About/翻译文件的汉化包不能替代原 EX。\n\n"
        f"当前收录 {len(packages)} 个原模组，共合并 {written} 条游戏文本。\n\n"
        "【本次更新】\n"
        "恢复 10 个种族模组被误删的 101 条心境译文，并补齐此前未翻译的 350 余条文本"
        "（近战攻击名、背景故事短标题、身体附加件名称、购物终端按钮、研究信件、"
        "特质与事件标题等）。\n\n"
        "【收录内容】\n"
        + plain_directory()
        + "\n\n"
        "——\n兼容版本：RimWorld 1.6\n"
        "本模组仅含翻译文件，不包含任何原模组资源。"
    )
    workshop_description = (
        "[h1]Aya 人工种族简体中文整合汉化包[/h1]\n"
        f"[b]收录：{len(packages)} 个原模组｜合并：{written} 条游戏文本[/b]\n\n"
        "[h2]使用说明[/h2]\n"
        "[list]\n"
        "[*]只需安装实际使用的 Aya 原模组。\n"
        "[*]将本整合汉化置于所有 Aya 原模组之后加载。\n"
        "[*]不要与下列独立汉化包同时启用。\n"
        "[/list]\n\n"
        "[h2]EX 扩展说明[/h2]\n"
        "Idhale EX、Littluna EX、Nearmare EX、Neclose EX、Silkiera EX、Solark EX、Xenoorca EX "
        "等原作者 EX 模组本身是上位种内容的启用开关。上位种的 Def、代码与资源已经包含在对应种族本体中，"
        "但只有检测到并启用相应 EX 的 packageId 时才会载入。未安装或未启用 EX，不会启用上位种内容。"
        "RimWorld 1.5/1.6 如需使用上位种，请安装并启用对应的原 EX；汉化包不能代替原 EX。\n\n"
        "[h2]本次更新[/h2]\n"
        "[list]\n"
        "[*]恢复被上一版本误删的种族心境译文（101 条）。\n"
        "[*]补齐近战攻击名、背景故事、身体附加件、终端按钮、研究信件等未翻译文本"
        "（350 余条，含 175 条运行时补丁）。\n"
        "[/list]\n\n"
        + workshop_directory()
        + "\n\n[h2]兼容信息[/h2]\n"
        "RimWorld 1.6｜本模组仅含翻译文件，不包含任何原模组资源。"
    )
    for tag, value in [
        ("name", "[Aya]人工种族简体中文整合汉化包 v1.6"),
        ("author", "AbstrAct404 / Chinese localization"),
        ("packageId", PACKAGE_ID),
        ("description", description),
    ]:
        ET.SubElement(about, tag).text = value
    supported = ET.SubElement(about, "supportedVersions")
    ET.SubElement(supported, "li").text = "1.6"
    load_after_node = ET.SubElement(about, "loadAfter")
    for dependency in load_after:
        ET.SubElement(load_after_node, "li").text = dependency
    force_load_after_node = ET.SubElement(about, "forceLoadAfter")
    for dependency in load_after:
        ET.SubElement(force_load_after_node, "li").text = dependency
    build.xml_write(output / "About" / "About.xml", about)
    preview_source = (
        mods_root
        / "3505571618 - Aya Premise Core Chinese"
        / "About"
        / "Preview.png"
    )
    if preview_source.is_file():
        shutil.copy2(preview_source, output / "About" / "Preview.png")

    readme = "\n".join([
        "# [Aya]人工种族简体中文整合汉化包 v1.6",
        "",
        f"> 当前收录 **{len(packages)}** 个原模组，共合并 **{written}** 条游戏文本。",
        "",
        "## 使用说明",
        "- 只需安装实际使用的 Aya 原模组。",
        "- 将本整合汉化放在全部 Aya 原模组之后。",
        "- 不要与对应的独立汉化包同时启用。",
        "",
        "## EX 扩展说明",
        "- Idhale EX、Littluna EX、Nearmare EX、Neclose EX、Silkiera EX、Solark EX、Xenoorca EX 等原作者 EX 模组是上位种内容的启用开关。",
        "- 上位种的 Def、代码与资源位于对应种族本体中；未安装或未启用 EX 时，相关条件内容不会载入。",
        "- RimWorld 1.5/1.6 如需使用上位种，请安装并启用对应的原 EX；汉化包不能代替原 EX。",
        "",
        "## 收录内容与链接",
        "",
        markdown_directory(),
        "",
        "## 兼容信息",
        "- RimWorld 1.6",
        "- 本模组仅含翻译文件，不包含任何原模组资源。",
        "",
    ])
    (output / "README.md").write_text(readme, encoding="utf-8")
    report = {
        "packageId": PACKAGE_ID,
        "includedPackages": package_info,
        "uniqueEntriesWritten": written,
        "conflictCount": len(conflicts),
        "conflicts": conflicts,
    }
    (output / "BUILD-REPORT.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    standalone_report = [
        {
            "id": item["originalWorkshopId"],
            "name": str(item["folder"]).removeprefix(
                f"{item['originalWorkshopId']} - "
            ).removesuffix(" Chinese"),
            "status": "present",
            "entries": item["entriesRead"],
            "path": (mods_root / str(item["folder"])).as_posix(),
        }
        for item in package_info
    ]
    (mods_root / "BUILD-REPORT.json").write_text(
        json.dumps(standalone_report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if args.steam_vdf_dir:
        args.steam_vdf_dir.mkdir(parents=True, exist_ok=True)
        title = build.text(about.find("name"))
        steam_output = (
            args.steam_content_root / INTEGRATED_FOLDER
            if args.steam_content_root
            else output
        )
        for suffix in ("", "-schinese"):
            content = "\n".join([
                '"workshopitem"', "{",
                '\t"appid"\t\t"294100"',
                f'\t"publishedfileid"\t\t"{PUBLISHED_FILE_ID}"',
                f'\t"contentfolder"\t\t"{build.vdf_quote(build.vdf_path(steam_output))}"',
                f'\t"previewfile"\t\t"{build.vdf_quote(build.vdf_path(steam_output / "About" / "Preview.png"))}"',
                f'\t"title"\t\t"{build.vdf_quote(title)}"',
                f'\t"description"\t\t"{build.vdf_quote(workshop_description)}"',
                f'\t"changenote"\t\t"{build.vdf_quote("恢复被误删的 101 条种族心境译文；补齐近战攻击名、背景故事短标题、身体附加件、购物终端按钮、研究信件等 350 余条未翻译文本（含 175 条运行时补丁）。无加载顺序变化。")}"',
                "}", "",
            ])
            (
                args.steam_vdf_dir
                / f"aya-integrated-{PUBLISHED_FILE_ID}{suffix}.vdf"
            ).write_text(content, encoding="utf-8")
    print(json.dumps({
        "output": str(output),
        "packages": len(packages),
        "entries": written,
        "conflicts": len(conflicts),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
