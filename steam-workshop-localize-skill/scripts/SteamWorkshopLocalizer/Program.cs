using System.Text.RegularExpressions;
using Steamworks;

uint appId = 294100;
string language = "schinese";
bool uploadContent = false;
var manifests = new List<string>();
for (int i = 0; i < args.Length; i++)
{
    switch (args[i])
    {
        case "--upload-content":
            uploadContent = true;
            break;
        case "--appid" when i + 1 < args.Length:
            appId = uint.Parse(args[++i]);
            break;
        case "--language" when i + 1 < args.Length:
            language = args[++i];
            break;
        default:
            manifests.Add(args[i]);
            break;
    }
}

if (manifests.Count < 1)
{
    Console.Error.WriteLine(
        "Usage: SteamWorkshopLocalizer [--appid 294100] " +
        "[--language schinese] <vdf> [<vdf> ...]"
    );
    return 2;
}

File.WriteAllText(Path.Combine(AppContext.BaseDirectory, "steam_appid.txt"), appId.ToString());

if (!SteamAPI.Init())
{
    Console.Error.WriteLine("SteamAPI.Init failed. Ensure Steam is running and the account owns RimWorld.");
    return 3;
}

try
{
    foreach (string manifestPath in manifests)
    {
        var item = ReadManifest(manifestPath);
        if (item.PublishedFileId == 0)
        {
            ulong createdId = CreateWorkshopItem(appId);
            ReplacePublishedFileId(manifestPath, createdId);
            item = item with { PublishedFileId = createdId };
            Console.WriteLine($"CREATED {createdId} manifest={manifestPath}");
        }
        Console.WriteLine($"START {item.PublishedFileId} {item.Title}");

        UGCUpdateHandle_t handle = SteamUGC.StartItemUpdate(
            new AppId_t(appId),
            new PublishedFileId_t(item.PublishedFileId)
        );

        if (uploadContent && !string.IsNullOrWhiteSpace(item.ContentFolder))
        {
            if (!Directory.Exists(item.ContentFolder))
                throw new DirectoryNotFoundException(
                    $"Content folder does not exist: {item.ContentFolder}"
                );
            Require(SteamUGC.SetItemContent(handle, item.ContentFolder), "SetItemContent");
        }
        Require(SteamUGC.SetItemUpdateLanguage(handle, language), "SetItemUpdateLanguage");
        Require(SteamUGC.SetItemTitle(handle, item.Title), "SetItemTitle");
        Require(SteamUGC.SetItemDescription(handle, item.Description), "SetItemDescription");
        Require(
            SteamUGC.SetItemVisibility(
                handle,
                ERemoteStoragePublishedFileVisibility.k_ERemoteStoragePublishedFileVisibilityPublic
            ),
            "SetItemVisibility"
        );
        if (uploadContent && !string.IsNullOrWhiteSpace(item.PreviewFile))
        {
            if (!File.Exists(item.PreviewFile))
                throw new FileNotFoundException(
                    $"Preview file does not exist: {item.PreviewFile}"
                );
            Require(SteamUGC.SetItemPreview(handle, item.PreviewFile), "SetItemPreview");
        }

        SteamAPICall_t apiCall = SteamUGC.SubmitItemUpdate(
            handle,
            item.ChangeNote
        );

        bool finished = false;
        EResult result = EResult.k_EResultNone;
        bool ioFailure = false;
        bool legalAgreementRequired = false;
        using var callResult = CallResult<SubmitItemUpdateResult_t>.Create((data, failed) =>
        {
            result = data.m_eResult;
            ioFailure = failed;
            legalAgreementRequired = data.m_bUserNeedsToAcceptWorkshopLegalAgreement;
            finished = true;
        });
        callResult.Set(apiCall);

        var deadline = DateTime.UtcNow.AddMinutes(2);
        while (!finished && DateTime.UtcNow < deadline)
        {
            SteamAPI.RunCallbacks();
            Thread.Sleep(100);
        }

        if (!finished)
            throw new TimeoutException($"Timed out updating {item.PublishedFileId}.");
        if (ioFailure || result != EResult.k_EResultOK)
            throw new InvalidOperationException(
                $"Steam rejected {item.PublishedFileId}: result={result}, ioFailure={ioFailure}."
            );
        if (legalAgreementRequired)
            throw new InvalidOperationException(
                $"Steam requires a Workshop legal agreement for {item.PublishedFileId}."
            );

        VerifyLocalizedMetadata(item, language);
        Console.WriteLine($"OK {item.PublishedFileId} language={language} verified=true");
    }
}
finally
{
    SteamAPI.Shutdown();
}

return 0;

static void Require(bool success, string operation)
{
    if (!success)
        throw new InvalidOperationException($"{operation} returned false.");
}

static WorkshopItem ReadManifest(string path)
{
    string value = File.ReadAllText(path);
    ulong id = ulong.Parse(Field(value, "publishedfileid"));
    string title = Unescape(Field(value, "title"));
    string description = Unescape(Field(value, "description"));
    string? contentFolder = OptionalField(value, "contentfolder");
    if (contentFolder is not null)
        contentFolder = Unescape(contentFolder);
    string? previewFile = OptionalField(value, "previewfile");
    if (previewFile is not null)
        previewFile = Unescape(previewFile);
    string changeNote = Unescape(Field(value, "changenote"));
    if (string.IsNullOrWhiteSpace(changeNote))
        throw new InvalidDataException("A current update note is required");
    return new WorkshopItem(id, title, description, contentFolder, previewFile, changeNote);
}

static ulong CreateWorkshopItem(uint appId)
{
    bool finished = false;
    EResult result = EResult.k_EResultNone;
    bool ioFailure = false;
    bool legalAgreementRequired = false;
    ulong publishedFileId = 0;
    using var callResult = CallResult<CreateItemResult_t>.Create((data, failed) =>
    {
        result = data.m_eResult;
        ioFailure = failed;
        legalAgreementRequired = data.m_bUserNeedsToAcceptWorkshopLegalAgreement;
        publishedFileId = data.m_nPublishedFileId.m_PublishedFileId;
        finished = true;
    });
    callResult.Set(
        SteamUGC.CreateItem(
            new AppId_t(appId),
            EWorkshopFileType.k_EWorkshopFileTypeCommunity
        )
    );
    var deadline = DateTime.UtcNow.AddSeconds(60);
    while (!finished && DateTime.UtcNow < deadline)
    {
        SteamAPI.RunCallbacks();
        Thread.Sleep(100);
    }
    if (!finished || ioFailure || result != EResult.k_EResultOK || publishedFileId == 0)
        throw new InvalidOperationException(
            $"CreateItem failed: finished={finished}, result={result}, " +
            $"ioFailure={ioFailure}, publishedFileId={publishedFileId}."
        );
    if (legalAgreementRequired)
        throw new InvalidOperationException(
            $"Steam requires a Workshop legal agreement for new item {publishedFileId}."
        );
    return publishedFileId;
}

static void ReplacePublishedFileId(string path, ulong publishedFileId)
{
    string value = File.ReadAllText(path);
    string updated = new Regex(
        "(\"publishedfileid\"\\s*\")0(\")"
    ).Replace(
        value,
        match => match.Groups[1].Value + publishedFileId + match.Groups[2].Value,
        1
    );
    if (updated == value)
        throw new InvalidDataException(
            $"Could not replace zero publishedfileid in manifest: {path}"
        );
    File.WriteAllText(path, updated);
}

static string Field(string value, string key)
{
    var match = Regex.Match(
        value,
        $"\"{Regex.Escape(key)}\"\\s*\"((?:\\\\.|[^\"])*)\"",
        RegexOptions.Singleline
    );
    if (!match.Success)
        throw new InvalidDataException($"Missing VDF field: {key}");
    return match.Groups[1].Value;
}

static string? OptionalField(string value, string key)
{
    var match = Regex.Match(
        value,
        $"\"{Regex.Escape(key)}\"\\s*\"((?:\\\\.|[^\"])*)\"",
        RegexOptions.Singleline
    );
    return match.Success ? match.Groups[1].Value : null;
}

static string Unescape(string value) =>
    value.Replace("\\\"", "\"").Replace("\\\\", "\\");

static void VerifyLocalizedMetadata(WorkshopItem expected, string language)
{
    var ids = new[] { new PublishedFileId_t(expected.PublishedFileId) };
    UGCQueryHandle_t query = SteamUGC.CreateQueryUGCDetailsRequest(ids, 1);
    Require(SteamUGC.SetLanguage(query, language), "SetLanguage");
    Require(SteamUGC.SetAllowCachedResponse(query, 0), "SetAllowCachedResponse");
    Require(SteamUGC.SetReturnLongDescription(query, true), "SetReturnLongDescription");

    bool finished = false;
    EResult result = EResult.k_EResultNone;
    bool ioFailure = false;
    using var callResult = CallResult<SteamUGCQueryCompleted_t>.Create((data, failed) =>
    {
        result = data.m_eResult;
        ioFailure = failed;
        finished = true;
    });
    callResult.Set(SteamUGC.SendQueryUGCRequest(query));

    var deadline = DateTime.UtcNow.AddSeconds(30);
    while (!finished && DateTime.UtcNow < deadline)
    {
        SteamAPI.RunCallbacks();
        Thread.Sleep(100);
    }

    try
    {
        if (!finished || ioFailure || result != EResult.k_EResultOK)
            throw new InvalidOperationException(
                $"Localized metadata query failed for {expected.PublishedFileId}: " +
                $"finished={finished}, result={result}, ioFailure={ioFailure}."
            );
        if (!SteamUGC.GetQueryUGCResult(query, 0, out SteamUGCDetails_t details))
            throw new InvalidOperationException(
                $"GetQueryUGCResult failed for {expected.PublishedFileId}."
            );
        if (details.m_rgchTitle != expected.Title ||
            details.m_rgchDescription != expected.Description)
        {
            throw new InvalidOperationException(
                $"Simplified Chinese metadata mismatch for {expected.PublishedFileId}: " +
                $"titleMatch={details.m_rgchTitle == expected.Title}, " +
                $"descriptionMatch={details.m_rgchDescription == expected.Description}."
            );
        }
    }
    finally
    {
        SteamUGC.ReleaseQueryUGCRequest(query);
    }
}

sealed record WorkshopItem(
    ulong PublishedFileId,
    string Title,
    string Description,
    string? ContentFolder,
    string? PreviewFile,
    string ChangeNote
);
