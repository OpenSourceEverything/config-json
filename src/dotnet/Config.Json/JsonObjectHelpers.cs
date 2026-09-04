using System.Text.Json;
using System.Text.Json.Nodes;

namespace ConfigJson.DotNet;

public static class JsonObjectHelpers
{
    public static JsonObject ParseObject(string json, string path, string displayName)
    {
        var node = JsonNode.Parse(json, null, new JsonDocumentOptions
        {
            AllowTrailingCommas = true,
            CommentHandling = JsonCommentHandling.Skip
        }) as JsonObject;
        if (node == null)
        {
            throw new InvalidOperationException($"{displayName} is not an object: '{path}'.");
        }

        return node;
    }

    public static bool HasKeyIgnoreCase(JsonObject obj, string key)
    {
        return TryGetValueIgnoreCase(obj, key, out _);
    }

    public static bool TryGetObjectIgnoreCase(JsonObject obj, string key, out JsonObject value)
    {
        value = null!;
        if (!TryGetValueIgnoreCase(obj, key, out var node) || node is not JsonObject result)
        {
            return false;
        }

        value = result;
        return true;
    }

    public static bool TryGetValueIgnoreCase(JsonObject obj, string key, out JsonNode? value)
    {
        foreach (var pair in obj)
        {
            if (string.Equals(pair.Key, key, StringComparison.OrdinalIgnoreCase))
            {
                value = pair.Value;
                return true;
            }
        }

        value = null;
        return false;
    }

    public static bool TryGetPathValueIgnoreCase(JsonObject root, IReadOnlyList<string> path, out JsonNode? value)
    {
        JsonNode? current = root;
        foreach (var rawPart in path)
        {
            if (current is not JsonObject obj)
            {
                value = null;
                return false;
            }

            if (!TryGetValueIgnoreCase(obj, rawPart, out current))
            {
                value = null;
                return false;
            }
        }

        value = current;
        return true;
    }
}
