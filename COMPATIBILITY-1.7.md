# RimWorld 1.7 兼容性检查

检查日期：2026-10-19。

## 官方更新说明

[Announcing the Waylith Engine and Update 1.7](https://store.steampowered.com/news/app/294100/view/672882362547178633)

- 1.7 从 Unity 切换到 Waylith；公告称玩法保持一致，主要改善性能。
- 公告发布时 1.7 位于 Steam unstable 分支，正式分支仍为 1.6。
- 官方说明 1.6 与 1.7 存档可互相加载，大多数模组无需修改；建议作者测试后补充兼容版本声明。

## 本仓库检查结果

- 21 个独立汉化包与整合包共 22 个 About.xml 均保留 1.6，并新增 1.7 supportedVersions。
- 翻译与补丁位于根目录 Languages、Patches，不存在仅允许 1.6 的 LoadFolders.xml；无需复制一份 1.7 目录。
- XML 翻译与补丁未因引擎切换而作无依据的字段迁移；原有直接标签和组件 Class 定向补丁全部保留。
- Outerm 与整合包携带相同的 AyaRuntimeLocalization.dll，并非全部是纯 XML。对应源码只使用 Verse、Harmony 和标准库，无直接 UnityEngine 调用；按类型名查找目标方法，缺少目标时跳过。不在缺乏 1.7 程序集的情况下盲目重新编译。
- 通用校验通过：659 个 XML、8316 条游戏文本；2080 个运行时 XPath 对现有 1.6 原模组数据全部命中。

## 验证边界

本次是静态兼容性检查与版本声明更新，未启动 1.7 实机测试；不代表已验证所有原种族程序集、Character Editor 或 Harmony 在 1.7 的运行行为。现有 XPath 校验仍以本地 1.6 原模组为基准，不将其宣称为 1.7 实测结果。原模组后续变更 Def、组件类型或方法签名时仍需复核。

Steam 创意工坊简介、标题及必需物品由用户维护，本次不上传、不生成覆盖这些字段的清单。
