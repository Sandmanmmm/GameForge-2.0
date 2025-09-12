$errors = @()
$ast = [System.Management.Automation.Language.Parser]::ParseFile('.\phase1-prebuild-hygiene.ps1', [ref]$null, [ref]$errors)
if ($errors) {
    Write-Host 'Parse Errors Found:' -ForegroundColor Red
    $errors | ForEach-Object { 
        Write-Host "Line $($_.Extent.StartLineNumber): $($_.Message)" -ForegroundColor Yellow 
    }
} else {
    Write-Host 'No parse errors found' -ForegroundColor Green
}
