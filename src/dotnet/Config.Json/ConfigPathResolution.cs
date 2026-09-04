using System.Text.Json;

namespace ConfigJson.DotNet;

public static class ConfigPathResolution
{
    public static IEnumerable<string> EnumerateSearchRoots(int maxDepth = 4)
    {
        var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        var current = Environment.CurrentDirectory;

        for (var depth = 0; depth < maxDepth && !string.IsNullOrWhiteSpace(current); depth++)
        {
            var full = Path.GetFullPath(current);
            if (seen.Add(full))
            {
                yield return full;
            }

            current = Directory.GetParent(current)?.FullName ?? string.Empty;
        }
    }

    public static bool TryReadJsonPointer(string pointerPath, out string configPath)
    {
        return TryReadJsonPointer(pointerPath, out configPath, out _);
    }

    public static bool TryReadJsonPointer(string pointerPath, out string configPath, out string error)
    {
        configPath = string.Empty;
        error = string.Empty;
        try
        {
            var json = File.ReadAllText(pointerPath);
            using var doc = JsonDocument.Parse(json);
            if (!doc.RootElement.TryGetProperty("configPath", out var configPathElement))
            {
                error = "Missing 'configPath' property.";
                return false;
            }

            if (TryResolvePath(pointerPath, configPathElement.GetString(), out configPath, out error))
            {
                return true;
            }

            if (string.IsNullOrWhiteSpace(error))
            {
                error = "configPath target not found.";
            }

            return false;
        }
        catch (Exception ex)
        {
            error = ex.Message;
            return false;
        }
    }

    public static bool TryReadTextPointer(string pointerPath, out string configPath)
    {
        return TryReadTextPointer(pointerPath, out configPath, out _);
    }

    public static bool TryReadTextPointer(string pointerPath, out string configPath, out string error)
    {
        configPath = string.Empty;
        error = string.Empty;
        try
        {
            foreach (var line in File.ReadLines(pointerPath))
            {
                var trimmed = line.Trim();
                if (string.IsNullOrWhiteSpace(trimmed) || trimmed.StartsWith('#'))
                {
                    continue;
                }

                if (TryResolvePath(pointerPath, trimmed, out configPath, out error))
                {
                    return true;
                }

                if (string.IsNullOrWhiteSpace(error))
                {
                    error = "Pointer target not found.";
                }

                return false;
            }
        }
        catch (Exception ex)
        {
            error = ex.Message;
            return false;
        }

        error = "Pointer file has no active entry.";
        return false;
    }

    public static bool TryReadTextFirstValue(string pointerPath, out string value)
    {
        value = string.Empty;
        try
        {
            foreach (var line in File.ReadLines(pointerPath))
            {
                var trimmed = line.Trim();
                if (string.IsNullOrWhiteSpace(trimmed) || trimmed.StartsWith('#'))
                {
                    continue;
                }

                value = trimmed;
                return true;
            }
        }
        catch
        {
            return false;
        }

        return false;
    }

    public static bool TryResolvePath(string pointerPath, string? rawPath, out string resolvedPath)
    {
        return TryResolvePath(pointerPath, rawPath, out resolvedPath, out _);
    }

    public static bool TryResolvePath(string pointerPath, string? rawPath, out string resolvedPath, out string error)
    {
        resolvedPath = string.Empty;
        error = string.Empty;
        if (string.IsNullOrWhiteSpace(rawPath))
        {
            error = "Path value is empty.";
            return false;
        }

        var expanded = Environment.ExpandEnvironmentVariables(rawPath.Trim());
        var candidates = EnumerateResolutionCandidates(pointerPath, expanded).ToArray();
        foreach (var candidate in candidates)
        {
            if (!File.Exists(candidate))
            {
                continue;
            }

            resolvedPath = candidate;
            return true;
        }

        var display = candidates.Length > 0 ? candidates[0] : expanded;
        error = $"Resolved path not found: {display}";
        return false;
    }

    private static IEnumerable<string> EnumerateResolutionCandidates(string pointerPath, string expandedPath)
    {
        var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);

        if (Path.IsPathRooted(expandedPath))
        {
            var rooted = Path.GetFullPath(expandedPath);
            if (seen.Add(rooted))
            {
                yield return rooted;
            }

            yield break;
        }

        var pointerDirectory = Path.GetDirectoryName(pointerPath) ?? Environment.CurrentDirectory;
        var anchor = Path.GetFullPath(pointerDirectory);
        while (!string.IsNullOrWhiteSpace(anchor))
        {
            var candidate = Path.GetFullPath(Path.Combine(anchor, expandedPath));
            if (seen.Add(candidate))
            {
                yield return candidate;
            }

            var parent = Directory.GetParent(anchor)?.FullName;
            if (string.IsNullOrWhiteSpace(parent) || parent.Equals(anchor, StringComparison.OrdinalIgnoreCase))
            {
                break;
            }

            anchor = parent;
        }

        foreach (var root in EnumerateSearchRoots())
        {
            var candidate = Path.GetFullPath(Path.Combine(root, expandedPath));
            if (seen.Add(candidate))
            {
                yield return candidate;
            }
        }
    }
}
