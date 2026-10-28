# Aya 人工种族简体中文汉化：交接说明

> 2026-10-27 最新维护状态见 [1.7 本地更新记录](UPDATE-1.7-2026-10-27.md)。已完成本地 1.7 适配和部署，21 个独立工坊项目已隐藏，整合包保持公开；本轮内容未上传工坊，未推送 GitHub。下方 8 月记录属于历史背景。


最后更新：2026-08-07。此文件用于后续维护者或新的 Codex 任务快速恢复上下文。

## 当前发布状态

- 整合包源目录：`Mods/0000000000 - Aya Integrated Chinese`
- Steam 创意工坊物品：`3770548798`
- RimWorld App ID：`294100`
- 当前整合范围：21 个 Aya 原模组、3745 条合并游戏文本。
- 最新内容更新：恢复被上一版本误删的 101 条种族心境译文；补齐此前未翻译的近战攻击名、背景故事短标题、身体附加件名称、购物终端按钮、研究信件、特质与事件标题等 350 余条文本（含 175 条运行时补丁）。全量审计（`audit_summon_equipment_translations.py`）当前缺漏为 0。
- 最新技能与基因审计：265 项已检查，缺失 `0`，翻译残留日文 `0`。

## 重要目录与生成物

- `Mods/`：所有独立汉化包和整合包源。
- `D:\MODS\Rimworld\0000000000 - Aya Integrated Chinese`：SteamCMD 使用的英文发布路径。
- `build_integrated_pack.py`：由独立汉化包重建整合包，并生成整合包 Steam VDF。
- `build_skill_command_patches.py`：为嵌套自定义技能字段生成 RimWorld PatchOperationReplace 补丁。
- `build_scenario_patches.py`：为 5 个种族剧本生成直接补丁和开场信件 Keyed 翻译；将原模组错误复用的 `GameStartDialog` 改为剧本专属文本键。
- `skill_command_translations.json`：217 项自定义技能、自动/手动召唤命令的原文—译文对照；这是此类字段的唯一维护源。
- `audit_skills_genes.py`：审计 GeneDef、XenotypeDef 与嵌套技能字段是否缺失或残留日文；报告写入 `SKILL-GENE-AUDIT.json`。
- `build_health_stage_patches.py`：补齐 `HediffDef/stages/li/label` 中不会被常规生成器提取的健康状态阶段名称，同时生成 DefInjected 与运行时直接兜底；报告写入 `HEALTH-STAGE-AUDIT.json`。
- `validate_runtime_patch_targets.py`：把所有技能与剧本补丁 XPath 对照当前原模组 1.6 Def；必须全部命中。
- `optimize_runtime_patches.py`：清理旧版合并补丁与新版生成补丁的重复执行；只有在其他直接补丁仍覆盖同一 XPath 时才会移除旧文件，绝不以 DefInjected 代替运行时兜底。
- `validate_translations.py`：通用 XML、依赖元数据、术语一致性校验。Patch 的 `xpath` 是原文选择器，不应按游戏显示文本检查。
- `audit_summon_equipment_translations.py`：按全部 Def 类型扫描原模组中日文文本（含纯汉字日文）与中文包的覆盖情况；补丁匹配按 Def 类型 + defName + 字段路径判定，并跨包查找 MayRequire 门控内容的译文。报告写入 `SUMMON-EQUIPMENT-AUDIT.json`。
- `TERMINOLOGY_REFERENCE.md`：面向人工阅读的固定术语表。
- `terminology.json`：机器处理时使用的术语库。
- `manual_review_overrides.json`：逐 Def 键的人工校对覆盖；用于覆盖自动或历史翻译。

## 翻译优先级与规则

按以下顺序处理冲突；靠前的规则不可被靠后的规则覆盖。

1. RimWorld 原版已有的简体中文专名必须逐字沿用，例如 `Psychic sensitivity` 必须为“心灵敏感度”。
2. `terminology.json` 与 `TERMINOLOGY_REFERENCE.md` 的固定种族名、专名、物品名和通用术语。
3. `manual_review_overrides.json` 的 Def 键级人工覆盖。
4. `skill_command_translations.json` 的技能/召唤命令对照。
5. 原文的实际游戏效果与上下文；优先自然意译，无法可靠意译的专名才采用统一音译。
6. 机器翻译只能用于候选草稿，不能直接覆盖上述任何层级。

其他固定规则：

- 同一个原文专名在游戏内文本、模组简介和 Steam 简介中必须使用同一译名。
- Steam 简介中提到的其他模组名、依赖名保留其原名称，不直译或音译，例如 `Camera+`、`HD Pawn Rendering`。
- 服装、武器、基因和技能名称优先意译；音译仅用于无可靠语义的世界观专名，并写入术语库。
- 不翻译 `packageId`、DefName、XPath、文件名、Workshop URL 和代码标识符。
- `translation-cache` 不是游戏加载文件；它不能替代 `Languages/ChineseSimplified` 或 `Patches` 中的正式翻译。
- 调整已有种族名称时必须同时检查 label、description、事件/派系文本、装备名、Steam 简介和术语库。

### 已知术语决议与待统一项

- 技能“影跳び”固定为“影跃”；截图中的该技能由 `Chaoura Race` 补丁覆盖。
- 自动/手动召唤按钮明确写为“（自动）”和“（手动）”，避免仅凭图标造成歧义。
- `救济的血杯`、`苍褪的太阳`、`白银币`等资源名在技能说明中必须与游戏内 Hediff 标签一致。
- 用户曾要求 Requeen 使用“雷奎恩”，但当前仓库历史文本和 `validate_translations.py` 仍普遍使用“女王种”且将“雷奎恩”列为禁用词。若要改名，必须作为一次完整迁移：先修改术语库与验证规则，再同步游戏文本、简介和 Steam 文案；不要只改局部。

## 嵌套技能翻译机制

许多 Aya 模组把可见技能文本置于种族 ThingDef 的自定义 comp 中，例如 `commandLabel`、`commandDesc`、`AutoLabel`、`AutoDesc`、`CommandLabel`、`CommandDesc`。这些不是普通 DefInjected 顶层字段，早期生成器不会提取，因而会在游戏中显示日文。

解决方式：

1. 在 `skill_command_translations.json` 增补原文—中文译文。
2. 运行 `python build_skill_command_patches.py`。
3. 运行 `python validate_runtime_patch_targets.py`，所有 XPath 必须命中。
4. 运行 `python audit_skills_genes.py`，必须得到缺失 `0`、残留日文 `0`。
5. 运行 `python optimize_runtime_patches.py`，确认所有包的 `coveragePreserved` 均为 `true` 且没有重复 XPath。
6. 运行 `python build_integrated_pack.py --mods-root .\Mods`，整合包会复制各独立包的 `Patches` 文件；若独立包仍有重复运行时目标，构建会直接终止。

补丁生成后的整合包必须将 XML 文件直接置于 `Patches/` 根目录，并以原模组 Workshop ID 为文件名前缀。不要用 `PatchOperationFindMod` 匹配 `packageId`：该操作匹配的是显示名，错误使用 `packageId` 会静默跳过补丁。技能和剧本补丁统一使用 `PatchOperationConditional`，按目标 Def 是否存在来执行。

抽象 Def 可能只有 `Name` 属性而没有 `defName`。生成器必须分别使用 `Defs/ThingDef[@Name="..."]` 与 `Defs/ThingDef[defName="..."]`；牧菌妖姬与索拉克技能包含这种情况。

## 剧本翻译与开局规则

- 已覆盖 `Nearmaere_Scenario`、`Xenoorca_Scenario`、`Silkiera_Scenario`、`Neclose_Scenario`、`Chaoura_Scenario`，共 5 个种族剧本。
- 每个剧本均直接修补 `label`、`description`、`scenario.summary` 与 `ScenPart_GameStartDialog.textKey`。
- 原始 Aya 剧本虽配置为 1 名开局角色，却复用了原版 `GameStartDialog`，因此会显示“你们三人”的坠毁求生文案；现在改为各族专属开场信件。
- 维护命令：`python build_scenario_patches.py`；审计结果写入 `SCENARIO-AUDIT.json`，当前 `scenarioCount` 必须为 `5`。

截至本次更新，217 项嵌套技能/召唤文本已覆盖，其中包括：

- 92 个普通自定义技能名称；93 个普通自定义技能说明；
- 8 个自动召唤名称、8 个自动召唤说明；
- 8 个手动召唤名称、8 个手动召唤说明；
- 12 个基因名称、12 个基因说明、12 个异种类型名称、12 个异种类型说明已审计通过。

## 整合包重建与本地验证

在仓库根目录执行：

```powershell
python .\build_skill_command_patches.py
python .\build_scenario_patches.py
python .\build_health_stage_patches.py
python .\optimize_runtime_patches.py
python .\validate_runtime_patch_targets.py
python .\audit_skills_genes.py
python .\build_integrated_pack.py --mods-root .\Mods --steam-vdf-dir .\steam_upload --steam-content-root 'D:\MODS\Rimworld'
$env:PYTHONUTF8='1'; python .\validate_translations.py .\Mods
```

随后至少检查：

- `SKILL-GENE-AUDIT.json` 的 `missingCount` 与 `untranslatedCount` 都为 `0`；
- 所有 XML 都能解析；
- `steam_upload/aya-integrated-3770548798*.vdf` 的 `appid` 为 `294100`、`publishedfileid` 为 `3770548798`；
- VDF 不含 `language` 键，也不含字面量 `\\n`；简介必须使用真实换行。

## Steam 创意工坊发布流程

SteamCMD 只上传内容和默认（英文回退）元数据；简体中文标题与简介必须由 Steamworks 客户端单独写入。不要依赖 VDF 的 `language` 字段。

### macOS（本仓库所在机器）

1. 从仓库根目录登录并执行上传（会提示输入 Steam 密码；若开启 Steam Guard 还需验证码）：

```zsh
cd /Users/studyhard/work/模组/rimworld
./tools/steamcmd/steamcmd.sh +login dead_end404 +runscript steam_upload/steamcmd_commands.txt
```

`steamcmd_commands.txt` 按顺序上传 21 个独立汉化包与整合包 `3770548798`，全部记录 `Upload finished ... : OK` 后进入下一步。

2. 用本地化客户端写标题/简介（工具已编译，位于
`steam-workshop-localize-skill/scripts/SteamWorkshopLocalizer/bin/Release/net9.0`；桌面 Steam 必须已登录）：

```zsh
cd steam-workshop-localize-skill/scripts/SteamWorkshopLocalizer/bin/Release/net9.0
dotnet SteamWorkshopLocalizer.dll --appid 294100 --language english ../../../../../../steam_upload/*.vdf
dotnet SteamWorkshopLocalizer.dll --appid 294100 --language schinese ../../../../../../steam_upload/*-schinese.vdf
```

注意：整合包描述含真实换行；`*-schinese.vdf` 供本地化客户端读取，`language` 键对 SteamCMD 无效。所有条目必须回读 `verified=true`。

1. 先把整合包同步到英文路径 `D:\MODS\Rimworld\0000000000 - Aya Integrated Chinese`，并把两个 VDF 复制到 `C:\Users\AA\Documents\AyaRaceZH\steam_upload`。
2. SteamCMD 上传默认分支及内容：

```powershell
C:\Users\AA\Documents\AyaRaceZH\tools\steamcmd\steamcmd.exe +login <Steam用户名> +workshop_build_item C:\Users\AA\Documents\AyaRaceZH\steam_upload\aya-integrated-3770548798.vdf +quit
```

3. SteamCMD 登录会替换桌面 Steam 的同账号会话。若本地化工具报 `k_EResultNoConnection` 或日志出现 `Session Replaced`，重启桌面 Steam，等待其重新显示 `Logged On`。
4. 从 `steam_localizer/bin/Release/net9.0` 运行本地化客户端；必须获得 API 回读的 `verified=true`：

```powershell
.\SteamWorkshopLocalizer.exe --appid 294100 --language english C:\Users\AA\Documents\AyaRaceZH\steam_upload\aya-integrated-3770548798.vdf
.\SteamWorkshopLocalizer.exe --appid 294100 --language schinese C:\Users\AA\Documents\AyaRaceZH\steam_upload\aya-integrated-3770548798-schinese.vdf
```

语言关键字：简体中文 `schinese`、繁体中文 `tchinese`、英语 `english`、日语 `japanese`、韩语 `koreana`。不要使用 `zh-CN`、`zh-TW` 等网页区域码。

## Workshop 更新说明规则

每次上传必须填写清楚、可验证的 `changenote`，至少包含：

- 本次修复或新增的文本类别；
- 用户可观察到的结果；
- 涉及范围或数量（可给出时）；
- 是否包含兼容性或加载顺序变化。

本次修正版的标准写法为：

> 修复补丁加载条件：上一版本错误地用 packageId 匹配原模组，导致 217 项技能文本、5 个种族剧本标题及其专属开场信件未实际生效；本次改为按目标 Def 是否存在逐项执行，并修复只有 Name 属性的抽象 Def 技能目标。

若当前不能上传，应先将这段说明和未上传原因写入本文件的“待发布”小节，下一次发布前优先处理；不要遗漏更新说明。

## 待发布

- 2026-08-07 已提交并推送 GitHub（`125001e`）：恢复 10 个种族模组被 `68f62e2` 误删的 101 条心境译文（含整合包）；补齐 350 余条未翻译文本（近战攻击名 175 条运行时补丁、背景故事短标题 120 条、身体附加件名称、购物终端按钮、研究信件、特质/事件/状态标题等）。全部校验通过：`SUMMON-EQUIPMENT-AUDIT.json` 缺漏 0、`validate_runtime_patch_targets.py` 1089 个 XPath 全部命中、`SKILL-GENE-AUDIT.json` 缺漏 0、`validate_translations.py` 通过。
- 2026-08-07 创意工坊上传待办：由用户手动执行（SteamCMD 需账号密码登录）。`steam_upload/` 下 21 个独立包 VDF + 整合包 VDF 均已用本次 changenote 重新生成，`steamcmd_commands.txt` 已含整合包条目（共 22 项）。上传后需用 `SteamWorkshopLocalizer` 写 `english`/`schinese` 分支并回读 `verified=true`。本机 macOS 命令见“Steam 创意工坊发布流程（macOS）”。

- 2026-07-25 已完成发布：SteamCMD 内容上传 `Success`；Steamworks 本地化回读均成功：`OK 3770548798 language=english verified=true`、`OK 3770548798 language=schinese verified=true`。
- 2026-07-25 运行时修正版已重新发布：技能与剧本补丁不再用 `packageId` 作为 `PatchOperationFindMod` 显示名，改为 Def 存在性条件；同时修复抽象 Def 的 `Name`/`defName` 定位。277 个 XPath 均对当前 1.6 原模组验证命中。SteamCMD 内容提交 `Success`，Steamworks 回读：`OK 3770548798 language=english verified=true`、`OK 3770548798 language=schinese verified=true`。
- 同类修复已同步上传到 14 个含技能或剧本运行时补丁的独立汉化项目；SteamCMD `workshop_log.txt` 对 14 个项目均记录 `Upload finished ... : OK`。上传后用户正在运行 RimWorld，未强制重启 Steam，因此这些独立项目的 `schinese` 标题/简介分支尚未逐项回读；游戏内内容不受影响，待退出游戏后再运行本地化客户端。
- 本机 `3770548798` 订阅目录曾滞留在 13:50 的旧版本，导致上传后测试仍显示旧文本；现已同步到 14:12 修正版，技能/剧本补丁中 `PatchOperationFindMod=0`、`PatchOperationConditional=19`。必须完全重启 RimWorld 后才能验证。
- 若日志仍显示旧的 `[Aya] …_zh` 独立包依赖警告，它们来自已安装的旧独立包元数据扫描，不是 `translation-cache`，也不是整合包的依赖；`ModsConfig.xml` 只启用 `abstract404.aya.integrated.zh` 时不影响整合包功能。可卸载或删除旧独立包以保持日志整洁。
- Git 推送与 Steam 发布是独立操作；除非用户明确要求，不要因为上传 Steam 而自动推送 Git。

## 2026-07-25 装备标签与 EX 机制补充

- `audit_equipment_translations.py` 会检查 21 个原模组中带日文的标准 `ThingDef.label` 与 `ThingDef.description` 是否均有简中翻译；本次共检查 986 项，缺失 0，日文残留 0，报告为 `EQUIPMENT-ITEM-AUDIT.json`。
- 少数 Aya 装备会在正常 `DefInjected` 注入后被兼容逻辑再次改写标签，表现为说明已汉化但名称退回日文。`build_runtime_label_patches.py` 使用人工审核白名单生成直接标签兜底，报告为 `RUNTIME-LABEL-PATCH-REPORT.json`。
- 当前运行时标签兜底覆盖 7 个 Def：`Gun_AssaultRifle_NM`、`HAR_NM_Wear_y`、`HAR_NC_Armor_b`、`HAR_CO_Apparel_Head_c`、`HAR_CO_Apparel_Shell_a`、`HAR_EL_Apparel_Shell_c`、`HAR_EL_Apparel_Tops_a`；其中 `HAR_CO_Apparel_Shell_a` 固定为“影之斗篷”。
- 所有生成的 `PatchOperationConditional` 都应包含 `<success>Always</success>`，使未安装的可选原模组不会产生预期外的补丁失败警告。
- 原作者的 Idhale EX、Littluna EX、Nearmare EX、Neclose EX、Silkiera EX、Solark EX、Xenoorca EX 是上位种内容的启用开关。上位种 Def、代码和资源在对应种族本体中，通过 `MayRequire="Ayameduki.HAR…EX"` 条件加载；未安装或未启用 EX 时不会载入。汉化包不能代替原 EX。
- 整合包 About、README 与 Steam VDF 简介源均已加入 EX 机制说明。
- 本地游戏实际加载的是 `D:\SteamLibrary\steamapps\common\RimWorld\Mods\0000000000 - Aya Integrated Chinese`，而不是工坊订阅目录。2026-07-25 已用镜像同步清除旧的嵌套 `2946679071/Chaoura_Apparel_Label_Fix.xml`，并同步到发布目录、实际加载目录和本地工坊订阅目录。必须完整退出并重启 RimWorld 才会应用。
- 2026-07-25 15:02 已将本轮装备标签与 EX 说明更新上传至整合包工坊物品 `3770548798`。SteamCMD 内容上传记录：Manifest ID `4319540497122148672`，`Upload finished ... : OK`。Steamworks 元数据回读：`OK 3770548798 language=english verified=true`、`OK 3770548798 language=schinese verified=true`。
- 2026-07-25 15:09 已将运行时装备/武器标签兜底同步到 4 个受影响的独立汉化包：Nearmare `3769646709`（Manifest `3089701596063208146`）、Neclose `3769646881`（Manifest `578580139998864478`）、Chaoura `3769644534`（Manifest `5677180429817240535`）、Eveliet `3769644777`（Manifest `6449624692633167330`）。四项 SteamCMD 日志均为 `Upload finished ... : OK`，且 `english`、`schinese` 两个语言分支均逐项回读为 `verified=true`。
