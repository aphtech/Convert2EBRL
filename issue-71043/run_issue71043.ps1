<#
.SYNOPSIS
    Convert the issue-71043 NFB Braille Monitor samples from the command line and
    compare them with the target eBraille files. Also runs the BANA no-change check.

.DESCRIPTION
    For each sample zip in this folder (07-26.zip, 08-26.zip, 10-26.zip) the script:
      1. Extracts the zip into out\<issue>\source (once; use -Clean to redo).
      2. Runs:  uv run --all-packages brf2ebrl --parser <Parser> --no-running-heads
                [-pl <layout>] -o <output>.ebrl <bm*.brf ...>
         The BRFs are converted from their own folder, so the NFB plugin finds the
         print HTML next to them. With -NoPrint they are copied into a folder
         without the .htm first.
      3. Unzips the result and the target .ebrl that came in the sample zip.
      4. Writes compare.txt (element counts, ours vs target), links_ours.txt and
         links_target.txt, and the converter log.

    -BanaCheck Baseline|Compare runs the BANA safety check from section 7 of
    nfb_plugin_newsletter_plan.md over work\ebrl-test-files\books instead.

.PARAMETER Issue
    Which issues to convert, for example 10-26. The default is every *.zip in this folder.

.PARAMETER Parser
    Parser plugin id. The default is NFB. Use BANA to run today's converter.

.PARAMETER PageLayout
    CLI page layout standard (interpoint or single-side). The default passes none: the CLI default
    is used, and the NFB plugin always sets its own page number positions (odd pages top right).

.PARAMETER NoPrint
    Convert from a copy of the BRFs without the print HTML (tests the BRF-only path).

.PARAMETER Clean
    Delete and re-extract this issue's out folder before converting.

.PARAMETER BanaCheck
    Baseline: convert the BANA test books and save the HTML as the baseline.
    Compare:  convert them again and compare with the baseline; exits 1 on any difference.

.PARAMETER BanaLimit
    Only use the first N books for -BanaCheck (0 = all). Use the same value for Baseline and Compare.

.EXAMPLE
    .\issue-71043\run_issue71043.ps1
.EXAMPLE
    .\issue-71043\run_issue71043.ps1 -Issue 10-26 -NoPrint
.EXAMPLE
    .\issue-71043\run_issue71043.ps1 -Parser BANA
.EXAMPLE
    .\issue-71043\run_issue71043.ps1 -BanaCheck Baseline -BanaLimit 10
#>
[CmdletBinding()]
param(
    [string[]]$Issue = @(),
    [string]$Parser = "NFB",
    [string]$PageLayout = "",
    [switch]$NoPrint,
    [switch]$Clean,
    [ValidateSet("", "Baseline", "Compare")]
    [string]$BanaCheck = "",
    [int]$BanaLimit = 0
)

$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.IO.Compression.FileSystem

$IssueDir = $PSScriptRoot
$RepoRoot = Split-Path $IssueDir -Parent
$OutRoot = Join-Path $IssueDir "out"
New-Item -ItemType Directory -Force $OutRoot | Out-Null

function Expand-ZipTo([string]$ZipPath, [string]$Destination) {
    # .ebrl files are zips; Expand-Archive refuses non-.zip extensions, so use .NET.
    if (Test-Path $Destination) { Remove-Item -Recurse -Force $Destination }
    [System.IO.Compression.ZipFile]::ExtractToDirectory($ZipPath, $Destination)
}

function Invoke-Brf2Ebrl([string[]]$Arguments, [string]$LogPath) {
    # The CLI logs INFO lines to stderr; don't let PowerShell treat them as errors.
    Push-Location $RepoRoot
    $oldPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        & uv run --all-packages brf2ebrl @Arguments 2>&1 |
            ForEach-Object { "$_" } |
            Out-File -FilePath $LogPath -Encoding utf8
        $exitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $oldPreference
        Pop-Location
    }
    return $exitCode
}

function Get-AvailableParsers {
    Push-Location $RepoRoot
    $oldPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $listing = & uv run --all-packages brf2ebrl --list-parsers 2>&1 | ForEach-Object { "$_" }
    }
    finally {
        $ErrorActionPreference = $oldPreference
        Pop-Location
    }
    return $listing | Where-Object { $_ -match '^\s+(\S+) - ' } | ForEach-Object { $Matches[1] }
}

function Get-HtmlText([string]$EbrlFolder) {
    $files = Get-ChildItem -Path (Join-Path $EbrlFolder "ebraille") -File -ErrorAction SilentlyContinue |
        Where-Object { $_.Extension -in ".html", ".xhtml" } | Sort-Object Name
    return ($files | ForEach-Object { Get-Content -Raw -Encoding utf8 $_.FullName }) -join "`n"
}

$CountPatterns = [ordered]@{
    "article titles (h1.article-title)" = '<h1\b[^>]*class="article-title"'
    "h1 (any)"                          = '<h1\b'
    "h2"                                = '<h2\b'
    "h3"                                = '<h3\b'
    "title page lines"                  = 'class="titlepage"'
    "separators"                        = 'class="separator"'
    "captions"                          = 'class="caption"'
    "figure (should be 0 for NFB)"      = '<figure\b'
    "bylines"                           = 'class="byline"'
    "dialogue"                          = 'class="dialogue"'
    "dialogue-cont"                     = 'class="dialogue-cont"'
    "paragraphs (all p)"                = '<p\b'
    "list items"                        = '<li\b'
    "web/email links"                   = '<a\b[^>]*href="(https?:|mailto:)'
    "internal links (TOC)"              = '<a\b[^>]*href="[^"]*#'
    "pre blocks"                        = '<pre\b'
    "braille page breaks"               = 'role="doc-pagebreak"'
}

function Write-Comparison([string]$OursFolder, [string]$TargetFolder, [string]$IssueOut) {
    $ours = Get-HtmlText $OursFolder
    $target = if ($TargetFolder) { Get-HtmlText $TargetFolder } else { "" }
    $rows = foreach ($name in $CountPatterns.Keys) {
        $pattern = $CountPatterns[$name]
        [pscustomobject]@{
            Element = $name
            Ours    = [regex]::Matches($ours, $pattern).Count
            Target  = if ($TargetFolder) { [regex]::Matches($target, $pattern).Count } else { "n/a" }
        }
    }
    $table = $rows | Format-Table -AutoSize | Out-String
    $table | Out-File -FilePath (Join-Path $IssueOut "compare.txt") -Encoding utf8
    Write-Host $table

    $hrefPattern = '<a\b[^>]*href="((?:https?:|mailto:)[^"]*)"'
    [regex]::Matches($ours, $hrefPattern) | ForEach-Object { $_.Groups[1].Value } |
        Out-File -FilePath (Join-Path $IssueOut "links_ours.txt") -Encoding utf8
    if ($TargetFolder) {
        [regex]::Matches($target, $hrefPattern) | ForEach-Object { $_.Groups[1].Value } |
            Out-File -FilePath (Join-Path $IssueOut "links_target.txt") -Encoding utf8
    }
}

function Invoke-IssueConversion([string]$IssueName, [string]$LayoutName) {
    $zip = Join-Path $IssueDir "$IssueName.zip"
    if (-not (Test-Path $zip)) { throw "Sample zip not found: $zip" }
    $issueOut = Join-Path $OutRoot $IssueName
    if ($Clean -and (Test-Path $issueOut)) { Remove-Item -Recurse -Force $issueOut }
    New-Item -ItemType Directory -Force $issueOut | Out-Null

    $sourceRoot = Join-Path $issueOut "source"
    if (-not (Test-Path $sourceRoot)) {
        Write-Host "Extracting $zip"
        Expand-ZipTo $zip $sourceRoot
    }
    # The zip holds one folder (for example 10-26) with the BRFs, the print HTML and the target .ebrl.
    $sourceFolder = Get-ChildItem -Path $sourceRoot -Directory | Select-Object -First 1
    if (-not $sourceFolder) { throw "No folder inside $zip" }
    $brfs = Get-ChildItem -Path $sourceFolder.FullName -File -Filter "*.brf" | Sort-Object Name
    if (-not $brfs) { throw "No BRF files in $($sourceFolder.FullName)" }
    $print = Get-ChildItem -Path $sourceFolder.FullName -File |
        Where-Object { $_.Extension -in ".htm", ".html" }

    $suffix = "_$Parser" + $(if ($NoPrint) { "_noprint" } else { "" })
    if ($NoPrint) {
        $brfFolder = Join-Path $issueOut "brf_only"
        if (Test-Path $brfFolder) { Remove-Item -Recurse -Force $brfFolder }
        New-Item -ItemType Directory -Force $brfFolder | Out-Null
        $brfs | Copy-Item -Destination $brfFolder
        $brfs = Get-ChildItem -Path $brfFolder -File -Filter "*.brf" | Sort-Object Name
        $printNote = "no (-NoPrint)"
    }
    else {
        $printNote = if ($print) { ($print | ForEach-Object Name) -join ", " } else { "none found" }
    }

    $outputEbrl = Join-Path $issueOut "$IssueName$suffix.ebrl"
    $logPath = Join-Path $issueOut "$IssueName$suffix.log.txt"
    if (Test-Path $outputEbrl) { Remove-Item -Force $outputEbrl }

    Write-Host ""
    Write-Host "=== $IssueName  parser=$Parser  layout=$LayoutName  print=$printNote" -ForegroundColor Cyan
    Write-Host ("BRFs: " + (($brfs | ForEach-Object Name) -join ", "))

    $cliArgs = @("--parser", $Parser, "--no-running-heads")
    # The option really is named "-pl, --page-layout" (one string) in the current CLI.
    if ($LayoutName -ne "default") { $cliArgs += @("-pl, --page-layout", $LayoutName) }
    $cliArgs += @("-o", $outputEbrl) + ($brfs | ForEach-Object FullName)
    $exitCode = Invoke-Brf2Ebrl $cliArgs $logPath
    Get-Content $logPath | Where-Object { $_ -match '^(WARNING|ERROR)|Low-confidence|print file|print:' } |
        Select-Object -First 25 | ForEach-Object { Write-Host "  $_" }
    if ($exitCode -ne 0 -or -not (Test-Path $outputEbrl)) {
        Write-Host "Conversion failed (exit $exitCode). Full log: $logPath" -ForegroundColor Red
        return $false
    }

    $oursFolder = Join-Path $issueOut "$IssueName${suffix}_ebrl"
    Expand-ZipTo $outputEbrl $oursFolder

    # The target is the top-level .ebrl that does not come from a single bm*.brf.
    $targetEbrl = Get-ChildItem -Path $sourceFolder.FullName -File -Filter "*.ebrl" |
        Where-Object { $_.Name -notmatch '^bm' } | Sort-Object Length -Descending | Select-Object -First 1
    $targetFolder = $null
    if ($targetEbrl) {
        $targetFolder = Join-Path $issueOut "target_ebrl"
        if (-not (Test-Path $targetFolder)) { Expand-ZipTo $targetEbrl.FullName $targetFolder }
        Write-Host "Target: $($targetEbrl.Name)"
    }
    else {
        Write-Host "No target .ebrl found; showing our counts only." -ForegroundColor Yellow
    }

    Write-Comparison $oursFolder $targetFolder $issueOut
    Write-Host "Output: $oursFolder"
    Write-Host "Log:    $logPath"
    return $true
}

function Invoke-BanaCheck([string]$Mode) {
    $booksDir = Join-Path $RepoRoot "work\ebrl-test-files\books"
    if (-not (Test-Path $booksDir)) { throw "BANA test books not found: $booksDir" }
    $books = Get-ChildItem -Path $booksDir -Directory |
        Where-Object { $_.Name -match '^A-B\d{4}-00$' -and (Test-Path (Join-Path $_.FullName "Brf Files")) } |
        Sort-Object Name
    if ($BanaLimit -gt 0) { $books = $books | Select-Object -First $BanaLimit }
    if (-not $books) { throw "No A-B####-00 books with a 'Brf Files' folder in $booksDir" }

    $checkRoot = Join-Path $OutRoot "bana"
    $runRoot = Join-Path $checkRoot $(if ($Mode -eq "Baseline") { "baseline" } else { "current" })
    if (Test-Path $runRoot) { Remove-Item -Recurse -Force $runRoot }
    New-Item -ItemType Directory -Force $runRoot | Out-Null
    $baselineRoot = Join-Path $checkRoot "baseline"
    if ($Mode -eq "Compare" -and -not (Test-Path $baselineRoot)) {
        throw "No baseline. Run with -BanaCheck Baseline on main before making changes."
    }

    $failures = 0
    foreach ($book in $books) {
        $brfs = Get-ChildItem -Path (Join-Path $book.FullName "Brf Files") -File |
            Where-Object { $_.Extension -ieq ".brf" } | Sort-Object Name
        $pdfDir = Join-Path $book.FullName "Graphic Files\PDF"
        $bookOut = Join-Path $runRoot $book.Name
        New-Item -ItemType Directory -Force $bookOut | Out-Null
        $ebrl = Join-Path $bookOut "$($book.Name).ebrl"
        # Same options as work\loop.ps1, with the parser named explicitly.
        $cliArgs = @("--parser", "BANA", "-o", $ebrl)
        if (Test-Path $pdfDir) { $cliArgs += @("-i", $pdfDir) }
        $cliArgs += ($brfs | ForEach-Object FullName)
        Write-Host "[$Mode] $($book.Name) ($($brfs.Count) BRF)"
        $exitCode = Invoke-Brf2Ebrl $cliArgs (Join-Path $bookOut "log.txt")
        if ($exitCode -ne 0 -or -not (Test-Path $ebrl)) {
            Write-Host "  conversion failed (exit $exitCode)" -ForegroundColor Red
            $failures++
            continue
        }
        $unzipped = Join-Path $bookOut "ebrl"
        Expand-ZipTo $ebrl $unzipped
        # Keep only the HTML that the conversion produces; package.opf has a timestamp.
        Remove-Item -Force $ebrl
        Get-ChildItem -Path $unzipped -Recurse -File |
            Where-Object { $_.Extension -notin ".html", ".xhtml" } | Remove-Item -Force
    }

    if ($Mode -eq "Baseline") {
        Write-Host ""
        Write-Host "Baseline saved to $runRoot ($($books.Count) books, $failures failed)." -ForegroundColor Green
        if ($failures) { exit 1 }
        return
    }

    $differences = 0
    foreach ($book in $books) {
        $base = Join-Path $baselineRoot "$($book.Name)\ebrl"
        $current = Join-Path $runRoot "$($book.Name)\ebrl"
        if (-not (Test-Path $base)) { Write-Host "  $($book.Name): not in baseline" -ForegroundColor Yellow; $differences++; continue }
        if (-not (Test-Path $current)) { Write-Host "  $($book.Name): no current output" -ForegroundColor Red; $differences++; continue }
        $baseFiles = Get-ChildItem -Path $base -Recurse -File | ForEach-Object { $_.FullName.Substring($base.Length) }
        $currentFiles = Get-ChildItem -Path $current -Recurse -File | ForEach-Object { $_.FullName.Substring($current.Length) }
        foreach ($rel in ($baseFiles + $currentFiles | Sort-Object -Unique)) {
            $a = Join-Path $base $rel
            $b = Join-Path $current $rel
            if (-not (Test-Path $a) -or -not (Test-Path $b)) {
                Write-Host "  DIFF $($book.Name)$rel (missing on one side)" -ForegroundColor Red
                $differences++
            }
            elseif ((Get-FileHash $a).Hash -ne (Get-FileHash $b).Hash) {
                Write-Host "  DIFF $($book.Name)$rel" -ForegroundColor Red
                $differences++
            }
        }
    }
    Write-Host ""
    if ($differences -or $failures) {
        Write-Host "BANA output CHANGED: $differences differing files, $failures failed conversions." -ForegroundColor Red
        Write-Host "Compare folders: $baselineRoot  vs  $runRoot"
        exit 1
    }
    Write-Host "BANA output unchanged for $($books.Count) books." -ForegroundColor Green
}

# ---- main ----
if ($BanaCheck) {
    Invoke-BanaCheck $BanaCheck
    exit 0
}

$available = @(Get-AvailableParsers)
if ($available -notcontains $Parser) {
    Write-Host "Parser '$Parser' is not installed. Available: $($available -join ', ')" -ForegroundColor Red
    if ($Parser -eq "NFB") {
        Write-Host "The NFB plugin is not built yet. Use -Parser BANA to run today's converter on the samples."
    }
    exit 2
}
$layout = if ($PageLayout) { $PageLayout } else { "default" }

if (-not $Issue -or $Issue.Count -eq 0) {
    $Issue = Get-ChildItem -Path $IssueDir -File -Filter "*.zip" | Sort-Object Name | ForEach-Object BaseName
}

$allOk = $true
foreach ($name in $Issue) {
    if (-not (Invoke-IssueConversion $name $layout)) { $allOk = $false }
}
if (-not $allOk) { exit 1 }
