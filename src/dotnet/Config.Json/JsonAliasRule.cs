namespace ConfigJson.DotNet;

public sealed record JsonAliasRule(string DestinationKey, IReadOnlyList<string> SourcePath, bool RequireObject = false)
{
    public static JsonAliasRule Value(string destinationKey, params string[] sourcePath)
    {
        return new JsonAliasRule(destinationKey, sourcePath, RequireObject: false);
    }

    public static JsonAliasRule Object(string destinationKey, params string[] sourcePath)
    {
        return new JsonAliasRule(destinationKey, sourcePath, RequireObject: true);
    }
}
