# Windows Terminal Unicode Setup Guide

## Quick Setup for Windows Terminal Unicode Support

### 1. Open Windows Terminal Settings
```powershell
# Open Windows Terminal (if not already open)
wt.exe

# Or from PowerShell
Start-Process wt
```

### 2. Configure Font Settings
1. Press `Ctrl + ,` to open Settings
2. Go to `Profiles > Windows PowerShell`
3. Scroll down to `Additional settings > Appearance`
4. Set `Font face` to one of these Unicode-compatible fonts:
   - **Cascadia Code** (best for emojis)
   - **Consolas** (clean monospace)
   - **Segoe UI** (good Unicode support)

### 3. Enable UTF-8 Support
Add this to your PowerShell profile:
```powershell
# Add to: $PROFILE (usually Documents\PowerShell\Microsoft.PowerShell_profile.ps1)
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
```

### 4. Install Cascadia Code Font (Optional)
```powershell
# Download and install Cascadia Code for best emoji support
winget install Microsoft.CascadiaCode --location "D:\Programs\Fonts\"
```

### 5. Test Unicode Support
```powershell
Write-Host "Testing: 🛡️ Security 🔒 Lock ✅ Success ❌ Error 💡 Solution" -ForegroundColor Green
```

## Current Working Script
For now, use the ASCII-compatible version:
```powershell
.\scripts\guardrails-check-simple.ps1
```

## Troubleshooting
- If emojis show as boxes: Change font to Cascadia Code
- If script fails: Use guardrails-check-simple.ps1
- If encoding issues: Run the UTF-8 commands above

## Font Recommendations by Priority:
1. **Cascadia Code** - Best for programming + emojis
2. **JetBrains Mono** - Excellent programming font
3. **Fira Code** - Good ligatures + Unicode
4. **Consolas** - Clean, widely available
5. **Segoe UI** - Good Unicode fallback