$ErrorActionPreference = 'Stop'
$sourceFolder = Join-Path $PSScriptRoot 'assets\fonts'
$fontFolder = Join-Path $env:LOCALAPPDATA 'Microsoft\Windows\Fonts'
New-Item -ItemType Directory -Path $fontFolder -Force | Out-Null
$registry = 'HKCU:\Software\Microsoft\Windows NT\CurrentVersion\Fonts'
New-Item -Path $registry -Force | Out-Null
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public class SunonsaFontInstall {
 [DllImport("gdi32.dll", CharSet=CharSet.Unicode)] public static extern int AddFontResourceEx(string file, uint flags, IntPtr reserved);
 [DllImport("user32.dll", CharSet=CharSet.Auto)] public static extern IntPtr SendMessageTimeout(IntPtr hwnd, uint msg, UIntPtr wparam, IntPtr lparam, uint flags, uint timeout, out UIntPtr result);
}
'@
foreach ($font in Get-ChildItem -LiteralPath $sourceFolder -Filter '*.ttf') {
    $targetFont = Join-Path $fontFolder $font.Name
    if (-not (Test-Path -LiteralPath $targetFont)) { Copy-Item -LiteralPath $font.FullName -Destination $targetFont }
    New-ItemProperty -Path $registry -Name ($font.BaseName + ' (TrueType)') -Value $targetFont -PropertyType String -Force | Out-Null
    [SunonsaFontInstall]::AddFontResourceEx($targetFont, 0, [IntPtr]::Zero) | Out-Null
    Write-Host ('Installed: ' + $font.Name)
}
$fontMessageResult = [UIntPtr]::Zero
[SunonsaFontInstall]::SendMessageTimeout([IntPtr]0xffff,0x001D,[UIntPtr]::Zero,[IntPtr]::Zero,2,1000,[ref]$fontMessageResult) | Out-Null
Write-Host 'Fonts are ready. Restart Premiere / After Effects if they were open.'
