$ErrorActionPreference = "Stop"
$Installer = Join-Path $PSScriptRoot "install.py"
$Py = Get-Command py -ErrorAction SilentlyContinue
if ($Py) {
    & $Py.Source -3 $Installer @args
    exit $LASTEXITCODE
}
$Python = Get-Command python -ErrorAction SilentlyContinue
if ($Python) {
    & $Python.Source $Installer @args
    exit $LASTEXITCODE
}
Write-Error "Python 3 is required to run the installer."
exit 127
