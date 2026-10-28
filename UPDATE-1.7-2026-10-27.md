# Aya 汉化 1.7 本地更新记录（2026-10-27）

## 结果与发布状态

- 依据 GitHub `master` 基线 `6b50df2`，完成 21 个原模组的本地汉化更新；Steam 最新更新时间与本地安装记录全部一致，源文件哈希见 `SOURCE-1.7-DELTA.json`。
- 整合包现有 3896 条 DefInjected/Keyed 唯一条目，另含直接 XML 补丁和 1.7 专用界面文本程序集；条目数不把直接补丁重复计入。
- 本轮没有上传任何创意工坊内容，也没有更新工坊标题、简介或图片。`steam_upload` 内生成的是待发布清单。
- 21 个独立汉化项目已按用户要求设为隐藏（Private，仅自己可见），通过同账号 Steam API 回读确认；整合包 `3770548798` 仍为公开。记录见 `WORKSHOP-VISIBILITY-AUDIT.json`。
- 新内容已部署到 `D:\MODS\Rimworld` 的 22 个包，以及游戏 `Mods/0000000000 - Aya Integrated Chinese`；整合包 141 个文件哈希完全一致。旧版保存在 `D:\MODS\Rimworld\local-backups\aya-before-20261027`，见 `LOCAL-DEPLOYMENT.json`。
- 尚未推送 GitHub；本次维护源码位于 `D:\MODS\Rimworld\AyaTranslation-work`。本轮未启动游戏，不能将静态模拟等同于实机画面测试。

## 反馈核查与原因

工坊 10 月 19—21 日反馈涉及大部分技能、身体部件及 Outerm 新内容。

1. 生成器与全量审计原先优先读取 1.6，即使 About 标注 1.7，也不能证明新版覆盖完整。现统一优先 1.7，审计可用 `AYA_SOURCE_VERSION=1.6` 明确回查旧版。
2. 1.7 将多个种族的技能迁移到 `Aya_Common.Aya_CompProperties_Skill`，旧组件 XPath 条件静默失配。现重新生成新版目标，并保留 166 个独立的 1.6 回退目标，总计 417 个条件操作；新版有效目标为 251 个（含使用按钮）。
3. 共有 22 处技能字段需要补充对照（包括一处重复原文）。范围、冷却、资源条件的变化已按当前原文更新，例如克里提亚斯范围由 80 格改为 30 格，部分火焰/EMP 范围由 10 格改为 5 格，部分伊娃莉特说明删除旧发动门槛。
4. 身体名称漏译真实存在：英文 `BodyDef/customLabel`、`BodyPartDef/label` 原先未得到全面覆盖。补齐全系列 964 处自定义身体名称，含 Outerm 的“光晕”、翅膀和左右器官名称；普通解剖词沿用游戏官方简中资料。
5. **不能确认“1.7 新增身体定义”这一推断**：对当前安装的 1.6、1.7 逐 Def 对照，Outerm 及本轮其他种族未新增或修改 BodyDef/BodyPartDef。此次身体漏译属于原来未覆盖的显示字段，不能把反馈推断写成已证实的新增器官。
6. 补齐 Outerm 装备、祭坛、黄金之冠状态、虚空之剑及 12 条设置文本；恢复旧版女王种兵力补充单元的两条兼容译文。
7. 新版共用技能程序集仍硬编码 4 处日文：取消按钮前缀、取消施放说明、发动条件不足、资源不足。编译 1.7 专用 Harmony 补丁，并用 LoadFolders 隔离，1.6 不加载该 .NET 10 程序集。
8. 额外补齐 139 处嵌套攻击名称/饮用/交换等操作文本，以及身体部件、生命阶段、死亡信息等英文漏译。
9. 已核查本地 7 个 EX/UC 扩展：仅含启用开关，无独立 Defs/Patches，条件种族内容已随本体审计。

## 新译名

翻译前已核查 `terminology.json`、`canonical_source_translations.json`、`manual_review_overrides.json`、技能词库和已有游戏汉化。没有找到固定对照的项目采用上下文意译或专名音译，并写入维护文件：

| 原文 | 本轮译文 | 说明 |
|---|---|---|
| アポリアオブシディアン | 阿波里亚黑曜饰 | 专名音译 + 黑曜石发饰用途 |
| アポリアドレス | 阿波里亚礼服 | 同系列专名统一 |
| クリュソステマ | 黄金之冠 | 描述明确提到神赐黄金王冠 |
| アポリュオン | 阿波利翁 | 虚空之剑专名音译 |
| 蘇りし厄災 | 复苏的灾厄 | 伊迪安新增状态名称意译 |

“埃维德拉万”“光晕”“救济的血杯”“固态药材”“粉末药材”“高位使徒”等沿用现有对照。逐条技能原文与译文见 `REVIEW-1.7-NEW-TRANSLATIONS.json`。原作者 `ウペレテス` 的技能说明与设置对功能的描述不完全一致；这里分别忠实翻译原文，没有擅自改变技能机制。

## 验证结果

- 1.7 实际 XML 补丁执行模拟：5612 项可见文本，漏译 0；1653 次替换、9 次添加；166 个未命中条件为保留的旧版回退。
- 1.6 同样模拟：5605 项，漏译 0。
- 技能/基因审计：264 项，缺失 0、日文残留 0。
- 全量日文/汉字来源覆盖审计：缺失 0。
- XML/术语验证：713 个 XML、8539 个游戏语言值，通过。
- XPath 验证：1.7 检查 3454 项，1.6 检查 3448 项，均通过。
- 整合包保留原先 33 处已存在的合并译文差异；本轮没有新增合并冲突。

`audit_effective_localization.py` 会执行条件、序列、替换和添加，再读取 DefInjected 结果，避免仅凭补丁字符串存在就误报通过。该静态审计覆盖 XML 中枚举的可见字段；代码文本另对新版共用技能程序集反编译核查。未验证其他模组在游戏启动后再次改写文本的情况。

## 后续重建

在仓库根目录，设置 `PYTHONUTF8=1`，依次执行：

```powershell
python build_translations.py --destination Mods
python build_skill_command_patches.py
python build_scenario_patches.py
python build_health_stage_patches.py
python build_body_part_patches.py
python build_nested_text_patches.py
.\runtime\build.ps1
python optimize_runtime_patches.py
python build_integrated_pack.py --mods-root Mods --steam-vdf-dir steam_upload --steam-content-root D:\MODS\Rimworld
python validate_runtime_patch_targets.py
python audit_skills_genes.py
python audit_summon_equipment_translations.py
python audit_effective_localization.py
python validate_translations.py Mods
```

`runtime/build.ps1` 使用已安装 1.7 游戏的程序集编译，仅用于其 1.7 文件夹。1.6 复查只对审计设置 `AYA_SOURCE_VERSION=1.6`，不要带此设置重新生成 1.7 发布文件。

## 每日反馈追踪

已建立自动化 `aya`，每天纽约时间（America/New_York）09:30 检查整合包评论和讨论；从 `FEEDBACK-TRACKING.json` 去重，发现可执行问题后核查源文件、制定并执行本地修复。无变化时保持安静。不自动回复评论，不上传内容，不重新公开独立包。
