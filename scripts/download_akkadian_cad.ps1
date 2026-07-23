param(
    [string]$Destination = (
        Join-Path (Split-Path -Parent $PSScriptRoot) "Resources\akkadian\cad"
    )
)

$ErrorActionPreference = "Stop"
$root = [IO.Path]::GetFullPath((Split-Path -Parent $PSScriptRoot))
$destinationPath = [IO.Path]::GetFullPath($Destination)
if (-not $destinationPath.StartsWith($root, [StringComparison]::OrdinalIgnoreCase)) {
    throw "CAD destination escaped the workspace: $destinationPath"
}

$base = "https://isac.uchicago.edu"
$catalogUrl = "$base/research/publications/chicago-assyrian-dictionary"
$termsUrl = "$base/research/electronic-publications-initiative-institute-study-ancient-cultures"
New-Item -ItemType Directory -Force -Path $destinationPath | Out-Null

$catalog = Invoke-WebRequest -Uri $catalogUrl -UseBasicParsing
$links = $catalog.Links.href |
    Where-Object { $_ -match "/cad_.*\.pdf$" } |
    Select-Object -Unique
if ($links.Count -ne 26) {
    throw "Expected 26 CAD volume links, found $($links.Count)"
}

$records = foreach ($href in $links) {
    $url = $base + $href
    $name = [IO.Path]::GetFileName($href)
    $target = Join-Path $destinationPath $name
    $temporary = $target + ".download"
    $head = Invoke-WebRequest -Uri $url -Method Head -UseBasicParsing
    $expected = [long]($head.Headers["Content-Length"] | Select-Object -First 1)

    if ((Test-Path -LiteralPath $target) -and
        (Get-Item -LiteralPath $target).Length -eq $expected) {
        Write-Host "EXISTS $name $expected"
    }
    else {
        & curl.exe --silent --show-error --location --fail --retry 5 `
            --continue-at - --output $temporary $url
        if ($LASTEXITCODE -ne 0) {
            throw "Download failed: $name"
        }
        $actual = (Get-Item -LiteralPath $temporary).Length
        if ($actual -ne $expected) {
            throw "Size mismatch: $name expected=$expected actual=$actual"
        }
        $stream = [IO.File]::OpenRead($temporary)
        try {
            $header = New-Object byte[] 5
            $read = $stream.Read($header, 0, $header.Length)
        }
        finally {
            $stream.Dispose()
        }
        if ($read -ne 5) {
            throw "Downloaded object is too short to be a PDF: $name"
        }
        $signature = [Text.Encoding]::ASCII.GetString($header)
        if ($signature -ne "%PDF-") {
            throw "Downloaded object is not PDF: $name"
        }
        Move-Item -LiteralPath $temporary -Destination $target -Force
        Write-Host "DOWNLOADED $name $actual"
    }

    $file = Get-Item -LiteralPath $target
    [ordered]@{
        file = $name
        url = $url
        bytes = $file.Length
        sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $target).Hash.ToLower()
    }
}

$manifest = [ordered]@{
    schema = "akkadian-cad-local-manifest-v1"
    generated_at = (Get-Date).ToUniversalTime().ToString("o")
    catalog = $catalogUrl
    terms = $termsUrl
    distribution = "local personal-use copy; ignored by git; do not redistribute"
    volume_count = $records.Count
    total_bytes = ($records | ForEach-Object { $_.bytes } | Measure-Object -Sum).Sum
    volumes = $records
}
$manifestPath = Join-Path $destinationPath "manifest.local.json"
$temporaryManifest = $manifestPath + ".tmp"
$manifest | ConvertTo-Json -Depth 5 |
    Set-Content -LiteralPath $temporaryManifest -Encoding utf8
Move-Item -LiteralPath $temporaryManifest -Destination $manifestPath -Force

Write-Output (
    "CAD COMPLETE volumes={0} bytes={1} manifest={2}" -f
    $manifest.volume_count, $manifest.total_bytes, $manifestPath
)
