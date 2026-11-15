# Deliberately unfinished block; tests parse/convert only and never execute it.
if ($true) {
    Install-WindowsFeature -Name Web-Server
    Set-Service -Name W3SVC -StartupType 'Automatic
