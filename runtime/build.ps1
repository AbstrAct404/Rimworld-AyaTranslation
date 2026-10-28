$ErrorActionPreference = 'Stop'
$game = 'D:\SteamLibrary\steamapps\common\RimWorld'
$sdk = (dotnet --list-sdks | Select-Object -Last 1).Split(' ')[0]
$compiler = "C:\Program Files\dotnet\sdk\$sdk\Roslyn\bincore\csc.dll"
$output = 'Mods\3505571618 - Aya Premise Core Chinese\1.7\Assemblies\AyaRuntimeLocalization.dll'
New-Item -ItemType Directory -Path (Split-Path $output) -Force | Out-Null
$refs = @('System.Private.CoreLib.dll','System.Runtime.dll','System.Collections.dll','Assembly-CSharp.dll','UnityStubs.dll') | ForEach-Object { "/reference:$game\$_" }
& dotnet $compiler /nologo /noconfig /nostdlib+ /target:library "/out:$output" @refs '/reference:D:\SteamLibrary\steamapps\workshop\content\294100\2009463077\1.7\Assemblies\0Harmony.dll' runtime\AyaRuntimeLocalization.cs
if ($LASTEXITCODE -ne 0) { throw 'Runtime localization compilation failed' }
Copy-Item -LiteralPath $output -Destination 'supplemental\3505571618\1.7\Assemblies\AyaRuntimeLocalization.dll' -Force
