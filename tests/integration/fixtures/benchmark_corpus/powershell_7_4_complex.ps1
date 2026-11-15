# PowerShell 7.4 syntax; cmdlets target a managed Windows host.
$featureNames = @('Web-Server', 'Web-Http-Logging')
foreach ($featureName in $featureNames) {
    Install-WindowsFeature -Name $featureName -IncludeManagementTools
}

Set-Service -Name W3SVC -StartupType Automatic
Start-Service -Name W3SVC
New-Item -Path 'C:\ExampleApp\Config' -ItemType Directory -Force
Set-ItemProperty -Path 'HKLM:\SOFTWARE\ExampleApp' -Name 'Channel' -Value 'stable'
Set-Content -Path 'C:\ExampleApp\Config\app.ini' -Value "mode=production`nport=8080"
Write-Output 'Provisioning actions described for conversion only'
