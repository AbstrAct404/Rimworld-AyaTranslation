"""Build standalone Chinese translation mods for the local Aya race Workshop mods.

The script intentionally reads source mods only and writes translation overlays.  It
uses RimWorld's DefInjected format, so it neither copies nor changes game assets.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import re
import shutil
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path
from workshop_descriptions_zh import WORKSHOP_DESCRIPTION_OVERRIDES

LOCAL_WORKSHOP = Path("original_mods/steamapps/workshop/content/294100")
WINDOWS_WORKSHOP = Path(r"D:\SteamLibrary\steamapps\workshop\content\294100")
WORKSHOP = LOCAL_WORKSHOP if LOCAL_WORKSHOP.is_dir() else WINDOWS_WORKSHOP

MODS = [
    ("2946679071", "Chaoura Race"), ("3505571618", "Aya Premise Core"),
    ("3153539856", "Eveliet Race"), ("2954714860", "Idea Storyteller"),
    ("2871413100", "Idearn Race"), ("2227425882", "Idhale Race"),
    ("2569091688", "Littluna Race"), ("2198830432", "Nearmare Race"),
    ("2394460334", "Neclose Race"), ("2763078885", "Qualeela Race"),
    ("2504657401", "Requeen Boss"), ("2676302514", "Saclean Race"),
    ("2233666290", "Silkiera Race"), ("2608237489", "Solark Race"),
    ("2216916011", "Xenoorca Race"),
    ("3750626266", "Canaan Intellect"), ("3489429571", "Chaoura UB"),
    ("2729712799", "Enforcer Boss"), ("2706009136", "Nexaga Race"),
    ("3675887482", "Outerm Race"), ("3477749439", "Zoichor Race"),
]

# Optional Aya extension switches load after their base races and can initialize
# upper-race comps late in startup.  Translation overlays for those base races
# must therefore be ordered after the corresponding extension as well.
OPTIONAL_LOAD_AFTER = {
    "2227425882": ["Ayameduki.HARIdhaleEX"],
    "2569091688": ["Ayameduki.HARLittlunaEX"],
    "2198830432": ["Ayameduki.HARNearmareEX"],
    "2394460334": ["Ayameduki.HARNecloseEX", "Ayameduki.HARNecloseUC"],
    "2233666290": ["Ayameduki.HARSilkieraEX"],
    "2608237489": ["Ayameduki.HARSolarkEX"],
    "2216916011": ["Ayameduki.HARXenoorcaEX"],
}

FIELDS = {
    "label", "labelNoun", "labelMale", "labelFemale", "description", "jobString",
    "gerundLabel", "pawnSingular", "pawnPlural", "pawnsPlural", "customLabel", "letterLabel",
    "letterText", "deathMessage", "beginLetter", "endLetter", "reportString",
    "ingestCommandString", "ingestReportString", "gerundLabel", "labelShort",
    "title", "titleShort", "fixedName",
}

# Proper nouns used consistently across this family.  General Japanese text is
# translated remotely when --translate-google is requested.
GLOSSARY = {
    "チャウラ": "混沌灵", "エヴェリエット": "伊娃莉特", "イデアーン": "伊迪安",
    "イデール": "幽灵姬", "リトルナ": "伪神族", "ニアメア": "魅魔",
    "ネクロース": "牧菌妖姬", "クアリーラ": "库莉菈", "リクイーン": "女王种",
    "サクリーン": "飞蛾姬", "シルキエラ": "亚人兽娘", "ソラーク": "索拉克",
    "ゼノオルカ": "人鱼姬", "人工種族": "人工种族", "種族": "种族",
    "服": "服装", "武器": "武器", "防具": "护甲", "作業": "工作",
}

# The machine translation service often leaves romanised race names in otherwise
# Chinese descriptions.  These are display terms, not identifiers: normalize
# them after translation while leaving XML keys, package IDs and placeholders
# untouched.
DISPLAY_NAME_REPLACEMENTS = {
    "Idoher": "幽灵姬", "Idhale": "幽灵姬", "Avonruach": "阿冯·鲁阿赫",
    "Evelito": "伊娃莉特", "Eveliet": "伊娃莉特",
    "Ritoruna": "伪神族", "Littluna": "伪神族",
    "Xenooka": "人鱼姬", "Xenoorca": "人鱼姬",
    "Ideaan": "伊迪安", "Idearn": "伊迪安",
    "Qualilla": "库莉菈", "Qualeela": "库莉菈", "Quorilla": "库莉菈",
    "Silkyra": "亚人兽娘", "Silkiera": "亚人兽娘",
    "Necros": "牧菌妖姬", "Neclose": "牧菌妖姬",
    "Solark": "索拉克（龙姬）", "Saclean": "飞蛾姬", "Chaoura": "混沌灵",
    # Machine-translated aliases of Idhale seen in Chinese output.
    "伊达尔": "幽灵姬", "伊达勒": "幽灵姬", "艾德哈尔": "幽灵姬",
    "伊多哈尔": "幽灵姬", "伊多赫尔": "幽灵姬", "伊多哈勒": "幽灵姬",
    "伊德哈勒": "幽灵姬", "阿文鲁阿哈": "阿冯·鲁阿赫",
    "阿冯鲁阿赫": "阿冯·鲁阿赫", "阿冯鲁阿哈": "阿冯·鲁阿赫",
}

# Workshop prose should use exactly the same Chinese race names that players
# see in-game.  Some earlier machine translations and older glossary values
# used different transliterations, so normalize both the English source names
# and those legacy Chinese renderings here.
# The shared terminology file is the single source of truth for the visible
# proper nouns used by both game text and Workshop descriptions.
TERMINOLOGY = json.loads((Path(__file__).with_name("terminology.json")).read_text(encoding="utf-8"))
REVIEWED_GAME_TRANSLATIONS = json.loads(
    (Path(__file__).with_name("reviewed_game_translations.json")).read_text(encoding="utf-8")
)
ACCEPTED_GAME_TRANSLATIONS = json.loads(
    (Path(__file__).with_name("accepted_game_translations.json")).read_text(encoding="utf-8")
)
MANUAL_REVIEW_OVERRIDES = json.loads(
    (Path(__file__).with_name("manual_review_overrides.json")).read_text(encoding="utf-8")
)
CANONICAL_SOURCE_TRANSLATIONS = json.loads(
    (Path(__file__).with_name("canonical_source_translations.json")).read_text(encoding="utf-8")
)
WORKSHOP_RACE_DISPLAY_REPLACEMENTS = TERMINOLOGY["race_names"]
EXTERNAL_MOD_NAMES = set(TERMINOLOGY["external_mod_names"])
EXTERNAL_MOD_NAME_REPLACEMENTS = TERMINOLOGY["external_mod_name_replacements"]

# Shared prose used verbatim in several original About.xml files.  Keep these
# translations natural and explicit instead of retaining the source ellipsis.
COMMON_WORKSHOP_DESCRIPTION_REPLACEMENTS = {
    "以下任意一个是佩戴头部装备时防止头发消失的MOD。":
        "以下两款 MOD 均可防止佩戴头部装备时头发消失，任选其一即可。",
    "这是一个以高质量显示以下内容之一的 MOD。":
        "以下两款 MOD 均可提高角色贴图的显示质量，任选其一即可。",
    "・规格可能会因更新而改变。":
        "・模组机制可能随原模组更新而调整。",
}

# Human-reviewed Workshop prose fixes.  These correct contextual mistakes that
# cannot be solved safely by replacing one term everywhere.
WORKSHOP_DESCRIPTION_REPLACEMENTS = {
    "2946679071": {
        "[由于亮度而导致的性能变化]": "【亮度对能力的影响】",
        "[亮度：100]身体机能下降": "[亮度：100%]身体能力降低",
        "[亮度：100]受到的伤害增加": "[亮度：100%]受到的伤害增加",
        "[亮度：0]身体机能增强": "[亮度：0%]身体能力增强",
        "[亮度：0]受到的伤害减少": "[亮度：0%]受到的伤害减少",
        "[亮度：0]恢复力增强": "[亮度：0%]恢复能力增强",
        "[亮度：0] 禁止拍摄": "[亮度：0%]射击伤害无效",
        "[仅限敌人，亮度：0]中概率向敌人射击并造成伤害。":
            "[仅限敌方，亮度：0%]受到射击时，有中等概率传送至攻击者身边并对其造成伤害。",
        "[亮度：0%]身体能力增强\n[亮度：0%]受到的伤害减少\n[亮度：0%]恢复能力增强\n"
        "[亮度：0%]身体能力增强\n[亮度：0%]射击伤害无效":
            "[亮度：0%]身体能力增强\n[亮度：0%]受到的伤害减少\n"
            "[亮度：0%]恢复能力增强\n[亮度：0%]射击伤害无效",
        "・拥有夜鹰特性的概率极高。": "・极高概率拥有“夜猫子”特性。",
        "・即使看到黑暗或尸体，我的心也不会下降。": "・身处黑暗或看到尸体时不会产生心情惩罚。",
    },
    "2569091688": {
        "利托鲁纳": "伪神族",
        "伪神族会靠近你的殖民地，几个小时后它就会崩溃，所以你可以捕获它。":
            "伪神族会来到殖民地附近，并在数小时后因体力不支而倒下；届时可将其俘获。",
    },
    "2954714860": {
        "创意C.乌鸦": "伊迪安 C.乌鸦",
        "“伊迪安·C.乌鸦”": "“理念 C.乌鸦”",
        "自称是人造种族一员的神秘女性。":
            "一名自称人工种族的神秘女性。",
        "他建议永久居住并与大家庭一起玩，并且会确保即使有很多定居者，也不会很难攻击（通常）。":
            "她适合永久定居、人口众多的玩法；通常会控制袭击规模，避免殖民者较多时压力过高。",
        "然而，他对那些离开这个星球的人（对于那些想经历地狱的人）毫不留情。":
            "但若试图离开这颗星球，她将毫不留情——适合想体验高难度终局的玩家。",
        "・有可能发生事件": "・各类事件更容易发生。",
        "・六个月后发生人类疾病爆发事件":
            "・游戏开始半年后，可能触发人类疾病暴发事件。",
    },
    "2227425882": {
        "- 无法战斗，因为我没有武器": "・无法持有武器，因此不能进行常规战斗。",
        "- 高度敏感，容易受到影响": "・心灵敏感度较高，更容易受到灵能影响。",
        "・不依赖技能的工作进展缓慢": "・不受技能等级影响的基础工作速度较慢。",
        "・不会受到伤害（但可能会受到 MOD 附加的伤害）":
            "・免疫原版伤害；其他 MOD 新增的伤害类型仍可能生效。",
        "・移动速度更快": "・移动速度比人类更快。",
    },
    "2608237489": {
        "这个MOD是一个增加了新的种族、派系、特殊装备的MOD。":
            "本 MOD 新增一个种族、一个派系及其专属装备。",
        "如果索拉克是定居者之一，那么维持这个殖民地就会很困难。":
            "索拉克加入后会显著增加殖民地的资源负担。",
        "等到你的资产稳定、充裕之后，再把它们带到你身边。":
            "建议待物资供应稳定且充足后，再招募索拉克。",
        "您可以穿戴各个种族的装备。":
            "安装后，索拉克可穿戴这些种族的部分装备。",
        "你将能够以12的速度在海里游泳。":
            "安装后，索拉克可在海面以 12 格/秒的速度移动。",
        "-寿命是人类的3倍": "・寿命约为人类的 3 倍。",
        "・饥饿程度是人类的5倍，容易饥饿":
            "・体型庞大、饥饿速度快，食物消耗远高于人类。",
        "・资产价值15000": "・单个索拉克的市场价值为 15000 银。",
        "-无法持有武器": "・无法持有武器，只能依靠自身能力战斗。",
        "・医疗、研究、培育、施工、训练、铺装、拆卸等作业速度非常慢。":
            "・医疗、研究、种植、建造、驯兽、平整地面及拆除等专业工作速度很慢。",
        "・比人类更快": "・移动速度明显快于人类（基础移动速度为 8 格/秒）。",
        "- 有很多抵抗力，但对火的抵抗能力较弱。反物质被禁用":
            "・对枪弹、爆炸及多数物理伤害具有较高抗性，但受到的火焰伤害加倍；免疫反物质爆炸伤害。",
        "・随着岁月的流逝，“人工种族”的等级不断提高并变得更强。":
            "・年龄增长时，“人工种族”等级会随之提升，能力也会逐渐增强。",
        "・我不介意看到尸体（新鲜）或吃尸体（新鲜）":
            "・看到新鲜尸体或食用新鲜尸体不会产生心情惩罚。",
        "・无法抵抗露营、雨天和黑暗":
            "・露宿、淋雨或身处黑暗时不会产生相应的心情惩罚。",
        "- 可以使用反物质技能，可以使用以下技能":
            "・可主动施放以下两项反物质能力：",
        "拉姆耀斑：以自身为中心产生小型反物质爆炸，冷却时间为3天。":
            "拉姆耀斑：以自身为中心引发小范围反物质爆炸，冷却时间为 3 天。",
        "冥界耀斑：产生以自身为中心的大规模反物质爆炸，冷却时间为1个赛季。":
            "冥界耀斑：以自身为中心引发大范围反物质爆炸，冷却时间为 1 个象限。",
        "他们是中立派系，都装备了坚固的铠甲。":
            "这是一个中立派系，其成员均装备强力护甲。",
    },
    "3153539856": {
        "艾维利托": "伊娃莉特",
        "【伊娃莉特加盟图】": "【伊娃莉特招募流程】",
        "・将伊娃莉特的研究进行到底，制造“艾泽雷姆”。":
            "1. 完成伊娃莉特研究，解锁并建造孵化设施“埃尔泽莱姆”。",
        "・从商家处购买以下商品。":
            "2. 从商人处购买全部五份重设计数据：",
        "“肖像类型：重新设计数据：A” “肖像类型：重新设计数据：B”":
            "“肖像种：重设计数据 A”“肖像种：重设计数据 B”",
        "“肖像类型：重新设计数据：C” “肖像类型：重新设计数据：D” “肖像类型：重新设计数据：E”":
            "“肖像种：重设计数据 C”“肖像种：重设计数据 D”“肖像种：重设计数据 E”",
        "・使用上述物品作为材料，在“艾泽雷姆”中制作“伊娃莉特 胶囊”。":
            "3. 将五份重设计数据作为材料，在“埃尔泽莱姆”中制作“伊娃莉特封装胶囊”。",
        "・使用“伊娃莉特封装”。":
            "4. 使用“伊娃莉特封装胶囊”，即可让一名伊娃莉特加入殖民地。",
        "- 在其基本状态下，除了一些事情外，它与人类没有太大区别。":
            "・基础状态下，除少数特殊机制外，身体能力与人类相近。",
        "・从对手身上收集血液可以增加技能成本。":
            "・从敌人身上收集血液，可以补充施放能力所需的血液储量。",
        "・费用用于技能，技能有“使用条件”和“消耗”。":
            "・每项能力都有各自的使用条件，并会消耗一定血液储量。",
        "-可以装备一些魅魔和亚人兽娘衣服。":
            "・可以穿戴部分 Nearmare Race 与 Silkiera Race 的种族装备。",
    },
}

# Shared source prose must keep one reviewed rendering across inherited or
# duplicated Defs.
ENFORCER_METEOR_DESCRIPTION = (
    "随陨石一同降临的神秘生命体。它体型与质量惊人，几乎无法以物理手段摧毁。"
    "\\n行动本身虽然迟缓，但其超大质量所爆发的攻击足以媲美陨石撞击，"
    "贸然接近绝非明智之举。\\n\\n这种生物已经近似于兵器，但似乎无法适应"
    "这颗星球的环境，活动时间极短；不足一天便会自行崩解消失。若无力将其破坏，"
    "也可设法拖延并阻止它接近殖民地，等待其自行消亡。\\n\\n大型个体各自拥有"
    "不同的特殊能力，可能对殖民者造成严重负面影响，请务必留意。"
)
ZOICHOR_ARRIVAL_TEXT = (
    "一名笼罩着阴郁气息的人工种族——锢魂魔加入了你的殖民地。"
    "\\n她不愿说明加入的原因，不过似乎无需担心她会背叛。"
    "\\n\\n她目前的力量正处于封印状态；推进相关研究，"
    "或许能够找到帮助她取回力量的契机。"
)

# A deliberately obfuscated source label cannot be translated reliably by an
# automatic service; use the established race name and a readable designation.
KEY_OVERRIDES = {
    # Faction proper names. These are key-specific because several source
    # strings are also used as pawn-kind labels or ordinary lore terms.
    "Nearmaere_Faction_NPC.fixedName": "魅魔氏族",
    "Nearmaere_Faction_NPC_b.label": "魅魔战团",
    "Nearmaere_Faction_NPC_b.fixedName": "魅魔战团",
    "Nearmaere_Faction_NPC_c.label": "真理教会",
    "Nearmaere_Faction_NPC_c.fixedName": "真理教会",
    "Nearmaere_Faction_NPC_e.label": "边境行星保全机构-ETHOS-",
    "Nearmaere_Faction_NPC_e.fixedName": "边境行星保全机构-ETHOS-",
    "Xenoorca_Faction_NPC.label": "逆戟鲸旅团",
    "Xenoorca_Faction_NPC.fixedName": "逆戟鲸旅团",
    "Xenoorca_Faction_NPC_b.label": "虎鲸佣兵团",
    "Xenoorca_Faction_NPC_b.fixedName": "虎鲸佣兵团",
    "Silkiera_Faction_NPC.label": "亚人工业",
    "Silkiera_Faction_NPC.fixedName": "亚人工业",
    "Neclose_Faction_NPC.label": "牧菌战团",
    "Neclose_Faction_NPC.fixedName": "牧菌战团",
    "Neclose_Faction_NPC_b.label": "昏暗之物",
    "Neclose_Faction_NPC_b.fixedName": "昏暗之物",
    "Littluna_Faction_NPC.label": "伪神族同盟",
    "Littluna_Faction_NPC.fixedName": "伪神族同盟",
    "Saclean_Faction_NPC.label": "丝织同盟",
    "Saclean_Faction_NPC.fixedName": "丝织同盟",
    "Nexaga_Faction_NPC.label": "混血种同盟",
    "Nexaga_Faction_NPC.fixedName": "混血种同盟",
    "Qualeela_Faction_NPC_c.label": "恩特雷凯亚王国",
    "Qualeela_Faction_NPC_c.fixedName": "恩特雷凯亚王国",
    "Chaoura_Faction_NPC.label": "死影会",
    "Chaoura_Faction_NPC.fixedName": "死影会",
    "Chaoura_Faction_NPC_b.label": "自有永有教团",
    "Chaoura_Faction_NPC_b.fixedName": "自有永有教团",
    "HAR_CO_UB_Hediff_Promise.label": "古老的约定",
    "Outerm_Faction.label": "混沌辛迪加",
    "Outerm_Faction.fixedName": "混沌辛迪加",
    # Canaan Intellect: the reference pack still leaves this newly expanded
    # description in Japanese.
    "Aya_CI_Permit_a.description": "“真棒！太厉害了！做得很好！这个印章就奖励给你啦！”\\n——神子\n\n向少年消耗交涉点数后获得的神秘许可证。委托其制造特殊道具时必须出示。\n\n造物主曾因“毫无节制地大量制造特殊道具并不妥当”而受到神子劝诫，于是制作了这种许可证。据说在古迦南，生产由神子管理，人们凭此证向造物主领取道具。印章图案采用了造物主的爱女——伪神族·杜娜米丝的形象。",
    # Enforcer Boss.
    "BOSS_EF_M_race_Base.label": "执行者",
    "BOSS_EF_B_M_race_Base.description": ENFORCER_METEOR_DESCRIPTION,
    "BOSS_EF_B_M_race_a.description": ENFORCER_METEOR_DESCRIPTION,
    "BOSS_EF_B_M_race_b.description": ENFORCER_METEOR_DESCRIPTION,
    "BOSS_EF_B_M_race_c.description": ENFORCER_METEOR_DESCRIPTION,
    "BOSS_EF_B_M_race_d.description": ENFORCER_METEOR_DESCRIPTION,
    "BOSS_EF_B_M_race_e.description": ENFORCER_METEOR_DESCRIPTION,
    "BOSS_EF_M_race_a.description": ENFORCER_METEOR_DESCRIPTION,
    # Keep these named gameplay entries aligned with the canonical race-name
    # terminology even when their source mod ships an older local translation.
    "HAR_IA_Item_spawn_Critias.label": "伊迪安·克里提亚斯（焚书模型）",
    "HAR_Xenoorca_NPC_Leader.label": "人鱼姬·渊丛主",
    # Zoichor repeats the same arrival letter in IncidentDef and Keyed data.
    "HAR_ZC_Incident_a.letterText": ZOICHOR_ARRIVAL_TEXT,
    "Letter_HAR_ZC_Zoichor_a": ZOICHOR_ARRIVAL_TEXT,
    # Nexaga is a proper race name; 混血种 remains its setting category.
    "HAR_Nexaga_KindBase_NPC.label": "涅克萨迦居民",
    # The shared Japanese source is also used for pawn kinds. A faction name
    # needs an explicit collective suffix in natural Chinese.
    "Littluna_Faction_NPC_b.label": "狂乱少女众",
    "Littluna_Faction_NPC_b.fixedName": "狂乱少女众",
    # Outerm additions introduced after the reference language pack was made.
    "HAR_OT_BaseMeleeWeapon_a.description": "奥特姆使用的神秘武器，仿佛活物般鲜明地搏动着。据说每杀死一个敌人，刀锋便会变得更加锐利。\n\n这把武器恶名昭彰，许多持有者最终都走上了大肆杀戮的歧途。\n\n\n\n\n杀吧，服从你的欲望。堆起尸骸，还要更加残酷。\n吾主渴求■■。以鲜烈血色，为那倦怠褪色的故事重新着彩。\n无底虚空正注视着你——无论何时，永远、永远。",
    "HAR_OT_Weapon_Idea.label": "噬魂邪枪",
    "HAR_OT_Weapon_Idea.description": "由“虚空■■■”赐予的邪异长枪。它蕴含虚空之力，每次挥动都能攻击周围 5 格内的所有敌人；杀死的生物越多，其锋利程度便越会无止境地增长。\n\n构成它的物质与“远渡星海之鸟·克里提亚斯”的外壳极其相似。它如同活物般散发热量并不断蠕动。\n\n据说其中吸纳了亿万灵魂，侧耳倾听时还能听见受苦灵魂的呻吟。\n\n\n\n\n\n这是曾经的我的一部分，请随意使用吧。",
    "HAR_OT_Hediff_Bed_a.label": "贪食爱欲的雌鸟",
    "HAR_OT_Hediff_Bed_a.description": "奥特姆陷入肉欲后的状态。肉体得到激活，身体能力暂时提升。\n\n奥特姆在遗传层面有着强烈性欲，一两次远远无法满足。她们如吞食猎物的肉食兽般贪婪，只会不断追求欢愉。\n\n此状态将在半天后结束。",
    "HAR_OT_Hediff_Bed_b.label": "沉溺欢愉的猎物",
    "HAR_OT_Hediff_Bed_b.description": "遭奥特姆以情欲尽情索取后的状态。\n\n奥特姆丝毫不顾及对方体力的攻势会彻底瓦解其理智。想与她们结为伴侣，就必须做好相应的心理准备。\n\n此状态会在数小时内完全恢复。",
    "HAR_Outerm_KindBase_NPC.label": "奥特姆",
    "Outerm.SpawnLevelLimit": "生成奥特姆时人工种族等级的上限：{0}",
    "Outerm.SpawnLevelBoost": "生成奥特姆时人工种族等级的额外加值（不会超过上限）：{0}",
    "Outerm.DisableNpcSkillF": "禁止 NPC 使用提丰纳斯【待核译名】",
    "Outerm.DisableNpcSkillF_Desc": "启用后，NPC 奥特姆将不再使用提丰纳斯（跳跃能力）。",
    "Outerm.DisableNpcSkillG": "禁止 NPC 使用埃莫拉吉亚【待核译名】",
    "Outerm.DisableNpcSkillG_Desc": "启用后，NPC 奥特姆将不再使用埃莫拉吉亚（扇形冲击波能力）。",
    "Outerm.DisableNpcSkillH": "禁止 NPC 使用提西福涅【待核译名】",
    "Outerm.DisableNpcSkillH_Desc": "启用后，NPC 奥特姆将不再使用提西福涅（反射能力）。",
    "Outerm.DisableNpcSkillI": "禁止 NPC 使用哈帕克提科【待核译名】",
    "Outerm.DisableNpcSkillI_Desc": "启用后，NPC 奥特姆将不再使用哈帕克提科（吞食尸体能力）。",
    "Outerm.DisableNpcSkillJ": "禁止 NPC 使用凯吕福斯【待核译名】",
    "Outerm.DisableNpcSkillJ_Desc": "启用后，NPC 奥特姆将不再使用凯吕福斯（觉醒能力）。",
    # Zoichor current 1.6 additions.
    "HAR_ZC_Incident_a.label": "古老的约定",
    "HAR_ZC_Incident_a.letterLabel": "古老的约定",
    "HAR_ZC_Incident_a.letterText": "一名笼罩着阴郁气息的人工种族——锢魂魔加入了你的殖民地。\\n她不愿说明加入的原因，不过似乎无需担心她会背叛。\\n\\n她目前的力量正处于封印状态；推进相关研究，或许能够找到帮助她取回力量的契机。",
    "Zoichor_Artificial.description": "锢魂魔是由人工种族的神子——伪神族·杜娜米丝创造的人工种族。她们在人工种族中地位特殊，获得力量的方式也与众不同：不会随时间自然变强，必须借助“苍阳果”逐步强化自身。\n\n她们拥有强大的再生能力，只要肉体没有彻底灰飞烟灭，就会缓慢恢复至完好状态。\n\n\n她们是在监狱行星担任狱卒的地狱恶魔。在忠实履行职责的同时，也与盟友持续开展着自己的计划。一切皆为实现夙愿；她们不会在现世谈论此事，只是默默推进。\n\n“请你一定要帮助那些被虚假命运玩弄的人。”\n\n与神子缔结的约定，至今仍深深刻在锢魂魔的灵魂之中。",
    "HAR_ZC_BMOT_Building_Incubator.description": "制造锢魂魔相关物品所需的设备。在梅拉夫也设置有许多同类装置，主要用于生成苍阳果。\n\n\n这套设备由人工种族的神子——伪神族·杜娜米丝亲手设计。技术极为先进，但运行需要消耗大量资源。",
    "HAR_LL_Hive_Critias.label": "伪神族蜂巢·克里蒂亚斯",
    # Idhale EX: Tzvaot Shekinah — divine presence/glory of the hosts.
    "HAR_IH_Hediff_EX_a.label": "万军神临",
    "HAR_IH_Hediff_EX_b.label": "万军神临",
    "HAR_IH_Hediff_EX_c.label": "万军神临",
    "HAR_IH_Hediff_EX_d.label": "万军神临",
    "HAR_IH_Hediff_EX_e.label": "万军神临",
    # Idhale relic names: use their source-language meanings instead of katakana.
    "HAR_IH_Item_a.label": "辉耀之石",
    "HAR_IH_Archotech_a.label": "天穹之钥",
    # Biotech terminology: translate the concepts rather than preserving the
    # Japanese katakana names (Bereshit / Ishmutit / Akasha Wear).
    "Aya_Race_Gene_a.label": "创世基因",
    "Aya_Race_Xenotype.label": "人工族",
    "HAR_IH_AT_z.label": "以太礼装",
    "HAR_IH_AT_z.description": "为幽灵姬·罪孽灵量身定制的礼装，但似乎没有特殊效果。",
    "HAR_CO_UB_Recipe_a.label": "异象之书",
    "HAR_CO_UB_Recipe_a.description": "从地行者生成异象之书。",
    "HAR_CO_UB_Recipe_b.label": "盟约灵晶",
    "HAR_CO_UB_Recipe_b.description": "从地行者生成盟约灵晶。",
    "HAR_CO_Apparel_Tops_a.label": "斯基亚礼装 A",
    "HAR_CO_Apparel_Tops_b.label": "斯基亚礼装 B",
    "HAR_CO_Apparel_Tops_c.label": "斯基亚礼装 C",
    "HAR_CO_Apparel_Tops_z.label": "米什帕提姆礼装",
    # Named apparel: keep invented series names as stable transliterations and
    # translate only the item category/type.
    "HAR_EL_Apparel_Armor_a.label": "埃利昂护甲",
    "HAR_EL_Apparel_onskin_a.label": "伊沙芭长袜",
    "HAR_EL_Apparel_Head_a.label": "伊沙芭头冠",
    "HAR_EL_Apparel_Head_b.label": "伊沙芭头饰",
    "HAR_EL_Apparel_Head_c.label": "伊沙芭宝石",
    "HAR_EL_Apparel_Head_d.label": "埃利昂头盔",
    "HAR_EL_Apparel_Head_e.label": "伊沙芭面纱",
    "HAR_EL_Apparel_Shell_a.label": "伊沙芭夹克 A",
    "HAR_EL_Apparel_Shell_b.label": "伊沙芭夹克 B",
    "HAR_EL_Apparel_Shell_c.label": "伊沙芭夹克 C",
    "HAR_EL_Apparel_Shell_d.label": "伊沙芭长袍",
    "HAR_EL_Apparel_Tops_a.label": "伊沙芭连衣裙 A",
    "HAR_EL_Apparel_Tops_a.description": "专为伊娃莉特设计的礼装，仍在调整中，因此没有特殊效果。",
    "HAR_EL_Apparel_Tops_b.label": "伊沙芭连衣裙 B",
    "HAR_EL_Apparel_Tops_b.description": "专为伊娃莉特设计的礼装，仍在调整中，因此没有特殊效果。",
    "HAR_EL_Apparel_Tops_c.label": "伊沙芭连衣裙 C",
    "HAR_EL_Apparel_Tops_c.description": "专为伊娃莉特设计的礼装，仍在调整中，因此没有特殊效果。",
    "HAR_EL_Apparel_Tops_d.label": "伊沙芭连衣裙 D",
    "HAR_EL_Apparel_Tops_d.description": "专为伊娃莉特设计的礼装，仍在调整中，因此没有特殊效果。",
    "HAR_EL_Apparel_Tops_e.label": "伊沙芭连衣裙 E",
    "HAR_EL_Apparel_Tops_e.description": "专为伊娃莉特设计的礼装，仍在调整中，因此没有特殊效果。",
    "HAR_EL_Item_a.label": "肖像种：重设计数据 A",
    "HAR_EL_Item_b.label": "肖像种：重设计数据 B",
    "HAR_EL_Item_c.label": "肖像种：重设计数据 C",
    "HAR_EL_Item_d.label": "肖像种：重设计数据 D",
    "HAR_EL_Item_e.label": "肖像种：重设计数据 E",
    "HAR_EL_Material_a.label": "伊娃莉特血晶矿",
    "HAR_EL_Spawn_a.label": "伊娃莉特封装胶囊",
    "HAR_IA_Armor_a.label": "艾提翁护甲",
    "HAR_IA_Armor_b.label": "奥尔芬礼装",
    "HAR_IA_AH_a.label": "艾提翁头盔 A",
    "HAR_IA_AH_b.label": "艾提翁头盔 B",
    "HAR_IA_tops_a.label": "梅卡涅礼装 A",
    "HAR_IA_tops_b.label": "梅卡涅礼装 B",
    "HAR_IA_tops_c.label": "梅卡涅礼装 C",
    # Requeen had one English-only summon description in the source.
    "BOSS_RQ_Monster_race_Summon_h.description": "女王种的后裔，拥有生物与机械混合的特殊结构；为排除威胁而被调整为生命体，并被剥除了情感与自我。\n\n“侦察型”是以迅捷行动为代价牺牲部分耐久的先锋单位：它会借助光学迷彩隐蔽接近敌人，再以匕首发动攻击。",
    # Idhale terminology: keep race/faction display names consistent, including
    # fixedName (which RimWorld displays instead of the FactionDef label).
    "HAR_Idhale.label": "幽灵姬",
    "HAR_Idhale_Player.label": "幽灵姬",
    "HAR_Idhale_b.label": "幽灵姬·罪孽灵",
    "HAR_Idhale_b_Player.label": "幽灵姬·罪孽灵",
    "HAR_Idhale_Body.label": "幽灵姬",
    "HAR_Idhale_KindBase_NPC.label": "幽灵姬幸存者",
    "HAR_Idhale_NPC_Resident.label": "幽灵姬幸存者",
    "Category_Idhale.label": "幽灵姬服装",
    "Idhale_P_Faction.label": "幽灵姬隐居地",
    "Idhale_Faction_NPC.label": "幽灵姬隐居地",
    "Idhale_P_Faction.pawnSingular": "幽灵姬人",
    "Idhale_Faction_NPC.pawnSingular": "幽灵姬人",
    "Idhale_Faction_NPC_b.pawnSingular": "幽灵姬人",
    "Idhale_Faction_NPC_b.fixedName": "苍穹之魂",
    "HAR_Idhale_KindBase_NPC_b.label": "苍穹之魂之民",
    "HAR_IH_Cultures_b.label": "苍穹之魂教义",
    # PawnKind labels are shown after a pawn's age in the inspect panel.
    "HAR_Idhale_NPC_b_Player.label": "罪灵",
    "HAR_Idhale_NPC_b_Leader.label": "罪灵",
    "HAR_IH_Backstory_b_C1.title": "造物主遗物",
    "HAR_IH_Backstory_b_C1.titleShort": "造物主遗物",
    "HAR_IH_Backstory_b_A1.title": "旧世神灵",
    "HAR_IH_Backstory_b_A1.titleShort": "旧世神灵",
}
MISSING_STUBS = {"3223844717": ("Ayameduki.HARNecloseEX", ["1.5", "1.6"])}
EXCLUDED_OUTPUT_IDS = {
    "3223844717", "3223846919", "3223847068", "3223847242",
    "3223847402", "3223847562", "3223847765",
}

# Published Steam Workshop item IDs for the maintained translation packages.
# They are kept separately from the original workshop IDs so a rebuild never
# risks creating a new Workshop page instead of updating the intended one.
PUBLISHED_FILE_IDS = {
    "2198830432": "3769646709", "2216916011": "3769645281",
    "2227425882": "3769645740", "2233666290": "3769650937",
    "2394460334": "3769646881", "2504657401": "3769649735",
    "2569091688": "3769646243", "2608237489": "3769651652",
    "2676302514": "3769650099", "2763078885": "3769649414",
    "2871413100": "3769645094", "2946679071": "3769644534",
    "2954714860": "3769644933", "3153539856": "3769644777",
    "3505571618": "3769644292",
    "3750626266": "3770548028", "3489429571": "3770548439",
    "2729712799": "3770548499", "2706009136": "3770548562",
    "3675887482": "3770548625", "3477749439": "3770548688",
}


def text(element: ET.Element | None) -> str:
    return (element.text or "").strip() if element is not None else ""


def package_id(mod: Path) -> str:
    about = mod / "About" / "About.xml"
    root = ET.parse(about).getroot()
    return text(root.find("packageId"))


def versions(mod: Path) -> list[str]:
    return sorted(p.name for p in mod.iterdir() if p.is_dir() and re.fullmatch(r"1\.\d+", p.name))


def active_defs(mod: Path) -> Path | None:
    available = versions(mod)
    if not available:
        return mod / "Defs" if (mod / "Defs").is_dir() else None
    latest = "1.6" if "1.6" in available else available[-1]
    folder = mod / latest / "Defs"
    return folder if folder.is_dir() else None


def is_japanese(value: str) -> bool:
    return bool(re.search(r"[\u3040-\u30ff\u31f0-\u31ff]", value))


def local_translate(value: str) -> str:
    for source, target in GLOSSARY.items():
        value = value.replace(source, target)
    for source, target in WORKSHOP_RACE_DISPLAY_REPLACEMENTS.items():
        value = value.replace(source, target)
    return value


def normalize_display_names(value: str) -> str:
    # Keep Solark's established display form atomic.  ``龙姬`` is also an
    # alias in the terminology table; applying that alias inside the
    # parenthesized canonical name on every rebuild previously produced
    # recursive forms such as ``索拉克（龙姬）（索拉克……）``.
    solark_token = "XQAYA_SOLARK_DRAGON_PRINCESS_QX"
    protected_solark = "索拉克（龙姬）"
    value = value.replace(protected_solark, solark_token)

    def replace_term(current: str, source: str, target: str) -> str:
        # ASCII names need word-like guards so "Solark" is not replaced inside
        # an identifier. Chinese/Japanese aliases should be replaced directly:
        # RimWorld descriptions store line breaks as the literal characters
        # "\\n", whose trailing ASCII "n" otherwise blocks a valid match.
        if re.search(r"[A-Za-z]", source):
            pattern = rf"(?<![A-Za-z]){re.escape(source)}(?![A-Za-z])"
            return re.sub(pattern, target, current, flags=re.I)
        return current.replace(source, target)

    for source, target in DISPLAY_NAME_REPLACEMENTS.items():
        value = replace_term(value, source, target)
    for source, target in WORKSHOP_RACE_DISPLAY_REPLACEMENTS.items():
        value = replace_term(value, source, target)
    for source, target in TERMINOLOGY["proper_names"].items():
        value = replace_term(value, source, target)
    for source, target in TERMINOLOGY["game_terms"].items():
        value = replace_term(value, source, target)
    value = value.replace(solark_token, protected_solark)
    return "\n".join(line.rstrip() for line in value.splitlines()).strip()


def reviewed_game_translation(mod_id: str, key: str, original: str) -> str:
    """Return only a checked-in translation for Japanese game-facing text.

    The machine-translation cache remains useful while discovering new source
    strings, but it must never be a release-time source of truth.  A newly
    added Japanese key therefore fails the build until it has been reviewed
    and checked in.
    """
    # Canonical key overrides are global consistency rules and must win over
    # older per-package review caches. Otherwise rebuilding a downloaded
    # source mod can silently resurrect superseded terminology.
    if key in KEY_OVERRIDES:
        return KEY_OVERRIDES[key]
    sources = (
        MANUAL_REVIEW_OVERRIDES,
        REVIEWED_GAME_TRANSLATIONS,
        ACCEPTED_GAME_TRANSLATIONS,
    )
    for source in sources:
        value = source.get(mod_id, {}).get(key)
        if value is not None:
            return CANONICAL_SOURCE_TRANSLATIONS.get(original, value)
    # FactionDef uses `pawnsPlural`; Chinese race names normally do not
    # inflect, so reuse the reviewed singular term rather than falling back
    # to the source language in quest and letter text.
    if key.endswith(".pawnsPlural"):
        singular_key = key[:-len("pawnsPlural")] + "pawnSingular"
        for source in sources:
            value = source.get(mod_id, {}).get(singular_key)
            if value is not None:
                return value
    if is_japanese(original):
        raise RuntimeError(
            f"Unreviewed Japanese game text: mod={mod_id} key={key} value={original!r}"
        )
    return CANONICAL_SOURCE_TRANSLATIONS.get(original, original)


def protect_external_mod_names(value: str) -> tuple[str, dict[str, str]]:
    """Replace external mod names with translation-safe placeholders."""
    names = set(EXTERNAL_MOD_NAMES)
    names.update(re.findall(r"\b[A-Za-z][A-Za-z0-9]*(?:[+!][A-Za-z0-9+!]*)\b", value))
    protected = value
    replacements: dict[str, str] = {}
    for index, name in enumerate(sorted(names, key=len, reverse=True)):
        if name not in protected:
            continue
        token = f"XQAYAMODNAME{index:03d}QX"
        protected = protected.replace(name, token)
        replacements[token] = name
    return protected, replacements


def translate_workshop_description(value: str, cache: dict[str, str]) -> str:
    """Translate a source About.xml description while preserving a cache."""
    if not value:
        return "原模组未提供简介。"
    protected_value, replacements = protect_external_mod_names(value)
    if protected_value not in cache:
        query = urllib.parse.urlencode({"client": "gtx", "sl": "auto", "tl": "zh-CN", "dt": "t", "q": protected_value})
        try:
            with urllib.request.urlopen("https://translate.googleapis.com/translate_a/single?" + query, timeout=12) as response:
                data = json.load(response)
            cache[protected_value] = "".join(part[0] for part in data[0] if part and part[0]) or protected_value
        except Exception:
            cache[protected_value] = protected_value
    # Normalize game text while external mod names are still protected tokens.
    # Restoring them afterwards prevents "Xenoorca Race" from being partly
    # changed into a Chinese race name by the terminology pass.
    translated = normalize_display_names(cache[protected_value])
    for token, name in replacements.items():
        translated = translated.replace(token, name)
    for source, target in EXTERNAL_MOD_NAME_REPLACEMENTS.items():
        translated = translated.replace(source, target)
    return "\n".join(line.rstrip() for line in translated.splitlines()).strip()


def google_translate(values: list[str], cache: dict[str, str]) -> dict[str, str]:
    """Translate unique Japanese values concurrently with a conservative worker cap."""
    pending = [v for v in values if v not in cache and is_japanese(v)]
    def request(value: str) -> tuple[str, str]:
        query = urllib.parse.urlencode({"client": "gtx", "sl": "ja", "tl": "zh-CN", "dt": "t", "q": value})
        url = "https://translate.googleapis.com/translate_a/single?" + query
        try:
            with urllib.request.urlopen(url, timeout=12) as response:
                data = json.load(response)
            translated = "".join(part[0] for part in data[0] if part and part[0])
            return value, translated or local_translate(value)
        except Exception:
            return value, local_translate(value)
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        for index, (value, translated) in enumerate(executor.map(request, pending), 1):
            cache[value] = translated
            if index % 100 == 0:
                print(f"  translated {index}/{len(pending)}")
    return cache


def xml_write(path: Path, root: ET.Element) -> None:
    ET.indent(root, space="  ")
    ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)


def add_workshop_dependency(
    about: ET.Element,
    package_id_value: str,
    display_name: str,
    workshop_id: str,
) -> None:
    """Add complete dependency metadata accepted by RimWorld 1.6."""
    dependencies = ET.SubElement(about, "modDependencies")
    dependency = ET.SubElement(dependencies, "li")
    ET.SubElement(dependency, "packageId").text = package_id_value
    ET.SubElement(dependency, "displayName").text = display_name
    ET.SubElement(dependency, "steamWorkshopUrl").text = (
        f"steam://url/CommunityFilePage/{workshop_id}"
    )


def vdf_quote(value: str) -> str:
    """Escape a Steam Workshop VDF string without altering Chinese text."""
    # KeyValues accepts quoted strings spanning physical lines.  SteamCMD does
    # not expand a literal ``\\n`` sequence, so preserve real newlines for
    # correctly formatted Workshop descriptions.
    return value.replace("\r\n", "\n").replace("\r", "\n").replace('"', '\\"')


def vdf_path(path: Path) -> str:
    """SteamCMD reliably accepts forward-slash absolute paths on Windows."""
    return str(path.resolve()).replace("\\", "/")


def write_readme(package: Path, mod_id: str, about: ET.Element) -> None:
    """Write the repository README from the same metadata used for Workshop VDFs."""
    title = text(about.find("name"))
    description = text(about.find("description"))
    versions = [text(item) for item in about.findall("./supportedVersions/li")]
    dependency = text(about.find("./modDependencies/li/packageId"))
    workshop_id = PUBLISHED_FILE_IDS[mod_id]
    workshop_text = workshop_id if workshop_id != "0" else "待首次上传后回填"
    version_text = "、".join(f"RimWorld {version}" for version in versions)
    package_text = text(about.find("packageId"))
    content = "\n".join([
        f"# {title}",
        "",
        description,
        "",
        "---",
        f"- 原模组创意工坊 ID：{mod_id}",
        f"- 本汉化创意工坊 ID：{workshop_text}",
        f"- 兼容版本：{version_text}",
        f"- packageId：`{package_text}`",
        f"- 前置 packageId：`{dependency}`",
        "- 加载顺序：原模组在前，本汉化在后。",
        "",
    ])
    (package / "README.md").write_text(content, encoding="utf-8")


def write_steam_vdfs(destination: Path, vdf_dir: Path) -> None:
    """Generate explicit SteamCMD update manifests for every maintained item."""
    vdf_dir.mkdir(parents=True, exist_ok=True)
    for mod_id, fallback_name in MODS:
        package = destination / f"{mod_id} - {fallback_name} Chinese"
        about = ET.parse(package / "About" / "About.xml").getroot()
        title = text(about.find("name"))
        description = text(about.find("description"))
        content = "\n".join([
            '"workshopitem"', '{',
            '\t"appid"\t\t"294100"',
            f'\t"publishedfileid"\t\t"{PUBLISHED_FILE_IDS[mod_id]}"',
            f'\t"contentfolder"\t\t"{vdf_quote(vdf_path(package))}"',
            f'\t"previewfile"\t\t"{vdf_quote(vdf_path(package / "About" / "Preview.png"))}"',
            f'\t"title"\t\t"{vdf_quote(title)}"',
            f'\t"description"\t\t"{vdf_quote(description)}"',
            '\t"changenote"\t\t"合并重复的运行时翻译补丁，统一装备、家具与 Character Editor 的标签覆盖；补齐并修复部分游戏文本。"',
            '}', '',
        ])
        (vdf_dir / f"{mod_id}-{PUBLISHED_FILE_IDS[mod_id]}.vdf").write_text(content, encoding="utf-8")
        # Steam assumes English when no update language is supplied. Keep the
        # default manifest above, and generate a separate Simplified Chinese
        # metadata manifest so the localized Workshop branch can be synced
        # without changing the default-language maintenance workflow.
        schinese_content = "\n".join([
            '"workshopitem"', '{',
            '\t"appid"\t\t"294100"',
            f'\t"publishedfileid"\t\t"{PUBLISHED_FILE_IDS[mod_id]}"',
            '\t"language"\t\t"schinese"',
            f'\t"contentfolder"\t\t"{vdf_quote(vdf_path(package))}"',
            f'\t"previewfile"\t\t"{vdf_quote(vdf_path(package / "About" / "Preview.png"))}"',
            f'\t"title"\t\t"{vdf_quote(title)}"',
            f'\t"description"\t\t"{vdf_quote(description)}"',
            '\t"changenote"\t\t"合并重复的运行时翻译补丁，统一装备、家具与 Character Editor 的标签覆盖；补齐并修复部分游戏文本。"',
            '}', '',
        ])
        (vdf_dir / f"{mod_id}-{PUBLISHED_FILE_IDS[mod_id]}-schinese.vdf").write_text(
            schinese_content, encoding="utf-8"
        )
    commands = [
        "@ShutdownOnFailedCommand 1",
        "@NoPromptForPassword 0",
        *[
            f'workshop_build_item "{vdf_path(vdf_dir / f"{mod_id}-{PUBLISHED_FILE_IDS[mod_id]}.vdf")}"'
            for mod_id, _ in MODS
        ],
        "",
    ]
    (vdf_dir / "steamcmd_commands.txt").write_text("\n".join(commands), encoding="utf-8")


def build_one(mod_id: str, fallback_name: str, destination: Path, translate_google: bool, cache: dict[str, str]) -> dict:
    source = WORKSHOP / mod_id
    if not source.is_dir():
        original_id, supported_versions = MISSING_STUBS[mod_id]
        out = destination / f"{mod_id} - {fallback_name} Chinese"
        if out.exists():
            shutil.rmtree(out)
        (out / "About").mkdir(parents=True)
        about = ET.Element("ModMetaData")
        for tag, value in [
            ("name", f"[ZH] {fallback_name}"),
            ("author", "AbstrAct404 / Chinese localization"),
            ("packageId", f"abstract404.aya.{mod_id}.zh"),
            ("description", f"[Aya] {fallback_name} 的简体中文本地化占位包。需加载原模组。"),
        ]:
            ET.SubElement(about, tag).text = value
        supported = ET.SubElement(about, "supportedVersions")
        for version in supported_versions:
            ET.SubElement(supported, "li").text = version
        add_workshop_dependency(about, original_id, fallback_name, mod_id)
        load_after = ET.SubElement(about, "loadAfter")
        ET.SubElement(load_after, "li").text = original_id
        xml_write(out / "About" / "About.xml", about)
        (out / "README.md").write_text(
            "源创意工坊目录当前未安装；此空壳 EX 模组没有可提取的 Def。\\n"
            "依赖 packageId 根据同系列命名规则预填，安装源模组后请进行一次游戏内验证。\\n",
            encoding="utf-8",
        )
        return {"id": mod_id, "name": fallback_name, "status": "stub built (source unavailable)", "entries": 0, "path": str(out)}
    original_id = package_id(source)
    source_meta = ET.parse(source / "About" / "About.xml").getroot()
    if mod_id in WORKSHOP_DESCRIPTION_OVERRIDES:
        chinese_description = WORKSHOP_DESCRIPTION_OVERRIDES[mod_id].strip()
    else:
        chinese_description = translate_workshop_description(text(source_meta.find("description")), cache)
        for old_text, new_text in COMMON_WORKSHOP_DESCRIPTION_REPLACEMENTS.items():
            chinese_description = chinese_description.replace(old_text, new_text)
        for old_text, new_text in WORKSHOP_DESCRIPTION_REPLACEMENTS.get(mod_id, {}).items():
            chinese_description = chinese_description.replace(old_text, new_text)
    out_name = f"[Aya] {fallback_name}_zh 人工种族汉化 v1.6"
    out = destination / f"{mod_id} - {fallback_name} Chinese"
    if out.exists():
        shutil.rmtree(out)
    (out / "About").mkdir(parents=True)
    about = ET.Element("ModMetaData")
    for tag, value in [
        ("name", out_name), ("author", "AbstrAct404 / Chinese localization"),
        ("packageId", f"abstract404.aya.{mod_id}.zh"),
        ("description", f"{chinese_description}\n\n——\n兼容版本：RimWorld 1.6\n前置：原模组（请置于本汉化之前加载）\n本模组仅含翻译文件，不包含原模组资源。"),
    ]:
        ET.SubElement(about, tag).text = value
    supported = ET.SubElement(about, "supportedVersions")
    ET.SubElement(supported, "li").text = "1.6"
    add_workshop_dependency(about, original_id, fallback_name, mod_id)
    load_after = ET.SubElement(about, "loadAfter")
    ET.SubElement(load_after, "li").text = original_id
    ordering_dependencies = [original_id, *OPTIONAL_LOAD_AFTER.get(mod_id, [])]
    for optional_dependency in ordering_dependencies[1:]:
        ET.SubElement(load_after, "li").text = optional_dependency
    force_load_after = ET.SubElement(about, "forceLoadAfter")
    for ordering_dependency in ordering_dependencies:
        ET.SubElement(force_load_after, "li").text = ordering_dependency
    xml_write(out / "About" / "About.xml", about)
    preview_source = source / "About" / "Preview.png"
    if preview_source.is_file():
        shutil.copy2(preview_source, out / "About" / "Preview.png")
    write_readme(out, mod_id, about)

    defs = active_defs(source)
    collected: dict[str, list[tuple[str, str, str]]] = defaultdict(list)
    # Some Aya summon races expose a concrete def with no local label or
    # description, inheriting a Japanese field from an abstract parent.  A
    # regular DefInjected pass only sees fields physically present on the
    # child, so those values used to leak through in Character Editor and item
    # tooltips.  Track the parent key that supplied an inherited display field
    # so the child can reuse the reviewed parent translation verbatim.
    inherited_translation_keys: dict[tuple[str, str, str], str] = {}
    keyed: dict[str, list[tuple[str, str]]] = defaultdict(list)
    if defs:
        definitions: list[ET.Element] = []
        for file in defs.rglob("*.xml"):
            try:
                root = ET.parse(file).getroot()
            except ET.ParseError:
                continue
            for definition in root:
                definitions.append(definition)
                # A few UI-visible abstract parent defs intentionally omit
                # defName and use Name instead; they still need a DefInjected
                # label override for descendants that inherit their label.
                def_name = text(definition.find("defName")) or definition.get("Name", "")
                if not def_name:
                    continue
                for child in definition:
                    if child.tag in FIELDS and text(child):
                        collected[definition.tag].append((def_name, child.tag, text(child)))

        parents: dict[str, tuple[ET.Element, str]] = {}
        for definition in definitions:
            def_name = text(definition.find("defName"))
            source_name = definition.get("Name", "")
            for identifier in (def_name, source_name):
                if identifier:
                    parents[identifier] = (definition, def_name or source_name)

        def inherited_display_field(definition: ET.Element, field: str) -> tuple[str, str] | None:
            parent_name = definition.get("ParentName", "")
            seen: set[str] = set()
            while parent_name and parent_name not in seen:
                seen.add(parent_name)
                parent = parents.get(parent_name)
                if parent is None:
                    return None
                parent_definition, parent_def_name = parent
                value = text(parent_definition.find(field))
                if value:
                    return parent_def_name, value
                parent_name = parent_definition.get("ParentName", "")
            return None

        for definition in definitions:
            def_name = text(definition.find("defName"))
            if not def_name:
                continue
            for field in ("label", "labelNoun", "labelMale", "labelFemale", "description"):
                if text(definition.find(field)):
                    continue
                inherited = inherited_display_field(definition, field)
                if inherited is None:
                    continue
                parent_def_name, original = inherited
                if not is_japanese(original):
                    continue
                collected[definition.tag].append((def_name, field, original))
                inherited_translation_keys[(definition.tag, def_name, field)] = (
                    f"{parent_def_name}.{field}"
                )
    # Some releases keep UI messages under Languages directly (rather than in
    # Defs). Include every supplied Keyed XML file as a Chinese keyed overlay.
    for file in source.rglob("*.xml"):
        parts = {part.lower() for part in file.parts}
        if "languages" not in parts or "keyed" not in parts:
            continue
        try:
            root = ET.parse(file).getroot()
        except ET.ParseError:
            continue
        for child in root:
            if text(child):
                keyed[file.name].append((child.tag, text(child)))
    values = [value for entries in collected.values() for _, _, value in entries]
    values += [value for entries in keyed.values() for _, value in entries]
    if translate_google:
        google_translate(list(dict.fromkeys(values)), cache)
    written = 0
    for def_type, entries in collected.items():
        language = ET.Element("LanguageData")
        seen = set()
        for def_name, field, original in entries:
            key = f"{def_name}.{field}"
            if key in seen:
                continue
            seen.add(key)
            translation_key = inherited_translation_keys.get(
                (def_type, def_name, field), key
            )
            translated = normalize_display_names(
                reviewed_game_translation(mod_id, translation_key, original)
            )
            # Do not write an English duplicate: the base game can supply it.
            if translated == original and not is_japanese(original):
                continue
            ET.SubElement(language, key).text = translated
            written += 1
        if len(language):
            folder = out / "Languages" / "ChineseSimplified" / "DefInjected" / def_type
            folder.mkdir(parents=True, exist_ok=True)
            xml_write(folder / "Aya_Translated.xml", language)
    for file_name, entries in keyed.items():
        language = ET.Element("LanguageData")
        seen = set()
        for key, original in entries:
            if key in seen:
                continue
            seen.add(key)
            translated = normalize_display_names(
                reviewed_game_translation(mod_id, key, original)
            )
            if translated == original and not is_japanese(original):
                continue
            ET.SubElement(language, key).text = translated
            written += 1
        if len(language):
            folder = out / "Languages" / "ChineseSimplified" / "Keyed"
            folder.mkdir(parents=True, exist_ok=True)
            xml_write(folder / file_name, language)
    supplemental = Path(__file__).with_name("supplemental") / mod_id
    if supplemental.is_dir():
        shutil.copytree(supplemental, out, dirs_exist_ok=True)
        for file in supplemental.rglob("*.xml"):
            try:
                written += sum(
                    1 for child in ET.parse(file).getroot() if text(child)
                )
            except ET.ParseError:
                continue
    return {"id": mod_id, "name": fallback_name, "status": "built", "entries": written, "path": str(out)}


def main() -> None:
    global WORKSHOP
    parser = argparse.ArgumentParser()
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument(
        "--workshop-root",
        type=Path,
        default=WORKSHOP,
        help="RimWorld Workshop content/294100 directory containing source mods",
    )
    parser.add_argument(
        "--mod-id",
        action="append",
        dest="mod_ids",
        help="Build only the selected original Workshop ID (repeatable)",
    )
    parser.add_argument("--translate-google", action="store_true")
    parser.add_argument("--steam-vdf-dir", type=Path)
    args = parser.parse_args()
    WORKSHOP = args.workshop_root
    args.destination.mkdir(parents=True, exist_ok=True)
    for mod_id in EXCLUDED_OUTPUT_IDS:
        for folder in args.destination.glob(f"{mod_id} - * Chinese"):
            shutil.rmtree(folder)
    cache_file = args.destination / ".translation-cache.json"
    cache = json.loads(cache_file.read_text(encoding="utf-8")) if cache_file.exists() else {}
    # Earlier generator revisions used a failed batch format.  Remove those
    # Japanese fallbacks so they are translated correctly on this run.
    cache = {source: target for source, target in cache.items() if not is_japanese(target)}
    selected_mods = [
        (mid, name) for mid, name in MODS
        if not args.mod_ids or mid in set(args.mod_ids)
    ]
    report = [
        build_one(mid, name, args.destination, args.translate_google, cache)
        for mid, name in selected_mods
    ]
    if args.steam_vdf_dir:
        write_steam_vdfs(args.destination, args.steam_vdf_dir)
    cache_file.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
    (args.destination / "BUILD-REPORT.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
