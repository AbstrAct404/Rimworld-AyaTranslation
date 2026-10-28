# RimWorld Aya 人工种族简体中文汉化

本仓库收录 Aya 人工种族系列的独立简体中文汉化包。每个目录均可单独作为 RimWorld 模组使用；加载时请将原模组置于对应汉化包之前。

同时提供一个覆盖全部已维护项目的整合包：
[Aya 人工种族简体中文整合汉化包](https://steamcommunity.com/sharedfiles/filedetails/?id=3770548798)。
整合包不强制依赖所有原模组，只需安装实际游玩的原模组，并将整合包置于它们之后加载；
不要再同时启用对应的独立汉化包。

各模组目录中的 `README.md` 由 `About/About.xml` 生成，使用与 Steam 创意工坊上传 VDF 相同的标题、简介、兼容版本及依赖元数据。

`Mods/BUILD-REPORT.json` 记录了本次构建的模组列表和翻译条目数。`build_translations.py` 用于从本地创意工坊源目录增量重建本仓库内容；不包含原模组的资源或程序集。

## 统一种族名称

- 飞蛾姬（Saclean）
- 幽灵姬（Idhale）
- 亚人兽娘（Silkiera / Sikiera）
- 魅魔（Nearmare）
- 混沌灵（Chaoura）
- 牧菌妖姬（Neclose）
- 涅克萨迦（Nexaga）
- 奥特姆（Outerm）
- 索拉克（龙姬，Solark）
- 人鱼姬（Xenoorca）
- 伪神族（Littluna）
- 伊娃莉特（Eveliet）
- 库莉菈（Qualeela）
- 锢魂魔（Zoichor）
- 伊迪安（Idearn）
- 女王种（Requeen Boss）

## 本次新增独立汉化

- [Canaan Intellect](https://steamcommunity.com/sharedfiles/filedetails/?id=3770548028)
- [Chaoura UB](https://steamcommunity.com/sharedfiles/filedetails/?id=3770548439)
- [Enforcer Boss](https://steamcommunity.com/sharedfiles/filedetails/?id=3770548499)
- [Nexaga Race](https://steamcommunity.com/sharedfiles/filedetails/?id=3770548562)
- [Outerm Race](https://steamcommunity.com/sharedfiles/filedetails/?id=3770548625)
- [Zoichor Race](https://steamcommunity.com/sharedfiles/filedetails/?id=3770548688)

特殊形态名称以各模组目录中的 README 和游戏内文本为准。

重新构建翻译包后运行 `python3 apply_race_names.py`，可按
`terminology.json` 的规则同步游戏文本、About 元数据与全部模组 README。

## RimWorld 1.7 兼容性

已为全部 22 个汉化包（含整合包）声明支持 1.6 / 1.7。检查说明见 [COMPATIBILITY-1.7.md](COMPATIBILITY-1.7.md)。本次仅本地元数据更新，不改写 Steam 上手动维护的简介和必需物品。


## 2026-10-27 本地维护更新

已适配 1.7 共用技能组件，补齐身体自定义名称和 Outerm 新维护内容，并保留 1.6 兼容分支。验证、固定译名和未发布状态详见 [本轮更新记录](UPDATE-1.7-2026-10-27.md)。

## 翻译安全检查

[白眼反馈排查与修正说明](WHITE-EYE-INVESTIGATION.md)：汉化不包含原模组贴图，不改写渲染配置或机制。身体名称使用标准 DefInjected，保留原始身份缓存；构建时通过 `audit_translation_safety.py` 拒绝危险覆盖。
