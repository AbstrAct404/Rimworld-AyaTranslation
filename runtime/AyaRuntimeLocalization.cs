using System;
using System.Collections.Generic;
using System.Reflection;
using HarmonyLib;
using Verse;

namespace AyaRaceZhRuntime
{
    // Outerm hard-codes English release-condition messages in its assembly.
    // The normal XML patch already supplies the Chinese condition in the
    // command description, so suppress only that redundant hard-coded line.
    [StaticConstructorOnStartup]
    public static class AyaRuntimeLocalization
    {
        private static readonly string[] OutermSkillTypes =
        {
            "HAR_OT_Comp_Skill_a", "HAR_OT_Comp_Skill_b", "HAR_OT_Comp_Skill_c",
            "HAR_OT_Comp_Skill_d", "HAR_OT_Comp_Skill_e", "HAR_OT_Comp_Skill_f",
            "HAR_OT_Comp_Skill_g", "HAR_OT_Comp_Skill_h", "HAR_OT_Comp_Skill_i",
            "HAR_OT_Comp_Skill_j"
        };

        static AyaRuntimeLocalization()
        {
            var harmony = new Harmony("abstract404.aya.race.zh.runtime");
            var postfix = new HarmonyMethod(typeof(AyaRuntimeLocalization), "FilterReleaseCondition");
            foreach (var typeName in OutermSkillTypes)
            {
                var type = AccessTools.TypeByName(typeName);
                var method = type == null ? null : AccessTools.Method(type, "CompGetGizmosExtra");
                if (method != null)
                    harmony.Patch(method, postfix: postfix);
            }
            var shared = AccessTools.TypeByName("Aya_Common.Aya_Comp_Skill");
            var sharedGizmos = shared == null ? null : AccessTools.Method(shared, "CompGetGizmosExtra");
            if (sharedGizmos != null)
                harmony.Patch(sharedGizmos, postfix: postfix);
        }

        public static void FilterReleaseCondition(ref IEnumerable<Gizmo> __result)
        {
            if (__result != null)
                __result = RemoveRedundantCondition(__result);
        }

        private static IEnumerable<Gizmo> RemoveRedundantCondition(IEnumerable<Gizmo> source)
        {
            foreach (var gizmo in source)
            {
                var command = gizmo as Command;
                if (command != null)
                {
                    if (command.defaultLabel != null && command.defaultLabel.StartsWith("キャンセル: ", StringComparison.Ordinal))
                        command.defaultLabel = "取消：" + command.defaultLabel.Substring("キャンセル: ".Length);
                    if (command.defaultDesc == "スキル発動の準備をキャンセルします。")
                        command.defaultDesc = "取消技能的施放准备。";
                    if (command.disabledReason != null)
                        command.disabledReason = command.disabledReason
                            .Replace("条件が不足しています: ", "未满足发动条件：")
                            .Replace("コストが不足しています: ", "所需资源不足：");
                }
                if (command != null && command.disabledReason != null &&
                    command.disabledReason.StartsWith("Release Conditions:", StringComparison.Ordinal))
                {
                    command.disabledReason = string.Empty;
                }
                yield return gizmo;
            }
        }
    }
}
