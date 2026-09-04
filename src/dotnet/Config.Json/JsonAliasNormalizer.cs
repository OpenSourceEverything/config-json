using System.Text.Json.Nodes;

namespace ConfigJson.DotNet;

public static class JsonAliasNormalizer
{
    public static void CopyAliasesIfMissing(JsonObject root, IEnumerable<JsonAliasRule> rules)
    {
        foreach (var rule in rules)
        {
            if (JsonObjectHelpers.TryGetValueIgnoreCase(root, rule.DestinationKey, out _))
            {
                continue;
            }

            if (!JsonObjectHelpers.TryGetPathValueIgnoreCase(root, rule.SourcePath, out var sourceNode))
            {
                continue;
            }

            if (rule.RequireObject && sourceNode is not JsonObject)
            {
                continue;
            }

            root[rule.DestinationKey] = sourceNode?.DeepClone();
        }
    }
}
