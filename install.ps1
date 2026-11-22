param(
    [string]$SkillsDir,
    [switch]$Dependencies,
    [switch]$InstallBrowser,
    [string]$Browser,
    [string]$NpmCli,
    [switch]$CheckOnly
)
$ErrorActionPreference = 'Stop'
$doctor = Join-Path $PSScriptRoot 'doctor.py'
$flags = @()
if (!$CheckOnly) { $flags += '--install' }
if ($Dependencies) { $flags += '--dependencies' }
if ($InstallBrowser) { $flags += '--install-browser' }
if ($SkillsDir) { $flags += @('--skills-dir', $SkillsDir) }
if ($Browser) { $flags += @('--browser', $Browser) }
if ($NpmCli) { $flags += @('--npm-cli', $NpmCli) }
if (Get-Command py.exe -ErrorAction SilentlyContinue) {
    & py.exe -3 $doctor @flags
} elseif (Get-Command python.exe -ErrorAction SilentlyContinue) {
    & python.exe $doctor @flags
} else {
    throw 'Install Python 3.10 or newer from https://www.python.org/downloads/'
}
exit $LASTEXITCODE
