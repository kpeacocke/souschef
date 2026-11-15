# PowerShell 5.1-compatible Windows server setup; tests parse only.
Install-WindowsFeature -Name Web-Server -IncludeManagementTools
Set-Service -Name W3SVC -StartupType Automatic
Start-Service -Name W3SVC
New-Item -Path 'C:\ExampleApp\Logs' -ItemType Directory -Force
