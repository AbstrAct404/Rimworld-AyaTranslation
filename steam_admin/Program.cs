using Steamworks;
using System.Text.Json;

// Deliberately has no SetItemContent/Title/Description/Preview call.
// Only the 21 standalones listed by the integrated pack can be hidden.
var reportPath = args[0];
var hide = args.Contains("--hide");
using var input = JsonDocument.Parse(File.ReadAllText(reportPath));
var ids = input.RootElement.GetProperty("includedPackages").EnumerateArray()
    .Select(x => ulong.Parse(x.GetProperty("translationWorkshopId").GetString())).ToArray();
if(ids.Length != 21 || ids.Contains(3770548798UL) || ids.Distinct().Count() != 21)
    throw new Exception("Unexpected standalone ID list");
File.WriteAllText(Path.Combine(AppContext.BaseDirectory,"steam_appid.txt"),"294100");
if (!SteamAPI.Init()) throw new Exception("SteamAPI.Init failed");
try {
    var before = Query(ids.Append(3770548798UL).ToArray());
    File.WriteAllText("STEAM-VISIBILITY-BEFORE.json",JsonSerializer.Serialize(before));
    foreach(var d in before) Console.WriteLine($"QUERY {d.id} {d.title} visibility={d.visibility} ownerMatches={d.owned}");
    if(!hide) return;
    if(before.Any(x=>!x.owned)) throw new Exception("Owner mismatch; no writes performed");
    foreach(var id in ids) {
        var d=before.Single(x=>x.id==id);
        if(d.visibility==2) { Console.WriteLine($"ALREADY_PRIVATE {id}"); continue; }
        var handle=SteamUGC.StartItemUpdate(new AppId_t(294100),new PublishedFileId_t(id));
        if(!SteamUGC.SetItemVisibility(handle,ERemoteStoragePublishedFileVisibility.k_ERemoteStoragePublishedFileVisibilityPrivate))
            throw new Exception($"SetItemVisibility failed {id}");
        bool done=false; EResult result=EResult.k_EResultNone;
        using var cb=CallResult<SubmitItemUpdateResult_t>.Create((r,failed)=>{ if(!failed) result=r.m_eResult; done=true; });
        cb.Set(SteamUGC.SubmitItemUpdate(handle,"Hide standalone localization; integrated pack remains available."));
        Pump(()=>done);
        if(result!=EResult.k_EResultOK) throw new Exception($"Submit failed {id}: {result}");
        Console.WriteLine($"SET_PRIVATE {id}");
    }
    var after=Query(ids.Append(3770548798UL).ToArray());
    File.WriteAllText("STEAM-VISIBILITY-AFTER.json",JsonSerializer.Serialize(after));
    if(after.Any(x=>x.id!=3770548798UL && x.visibility!=2)) throw new Exception("Read-back mismatch");
    if(after.Single(x=>x.id==3770548798UL).visibility != before.Single(x=>x.id==3770548798UL).visibility)
        throw new Exception("Integrated visibility changed unexpectedly");
    Console.WriteLine("VERIFIED all 21 standalone items private; integrated unchanged; no content uploaded");
} finally { SteamAPI.Shutdown(); }

static void Pump(Func<bool> ready) {
    var deadline=DateTime.UtcNow.AddSeconds(45);
    while(!ready()) { SteamAPI.RunCallbacks(); if(DateTime.UtcNow>deadline) throw new TimeoutException(); Thread.Sleep(20); }
}
static List<Item> Query(ulong[] ids) {
    var handle=SteamUGC.CreateQueryUGCDetailsRequest(ids.Select(i=>new PublishedFileId_t(i)).ToArray(),(uint)ids.Length);
    SteamUGC.SetAllowCachedResponse(handle,0);
    bool done=false; EResult result=EResult.k_EResultNone;
    using var cb=CallResult<SteamUGCQueryCompleted_t>.Create((r,failed)=>{ if(!failed) result=r.m_eResult; done=true; });
    cb.Set(SteamUGC.SendQueryUGCRequest(handle)); Pump(()=>done);
    if(result!=EResult.k_EResultOK) throw new Exception($"Query failed {result}");
    var rows=new List<Item>();
    for(uint i=0;i<ids.Length;i++) {
        if(!SteamUGC.GetQueryUGCResult(handle,i,out var d) || d.m_eResult!=EResult.k_EResultOK || d.m_nConsumerAppID.m_AppId!=294100)
            throw new Exception("Invalid query item");
        rows.Add(new Item(d.m_nPublishedFileId.m_PublishedFileId,d.m_rgchTitle,(int)d.m_eVisibility,d.m_ulSteamIDOwner==SteamUser.GetSteamID().m_SteamID));
    }
    SteamUGC.ReleaseQueryUGCRequest(handle); return rows;
}
record Item(ulong id,string title,int visibility,bool owned);
