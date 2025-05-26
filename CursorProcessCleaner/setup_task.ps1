# Sets up a scheduled task to clean Cursor Python processes
# This script requires administrator privileges

$scriptPath = Join-Path -Path $PSScriptRoot -ChildPath "clean_python.ps1"
$taskName = "CursorPythonCleaner"
$triggerFrequency = 30 # minutes

# Ensure script path exists
if (-not (Test-Path $scriptPath)) {
    Write-Error "Cleaning script not found: $scriptPath"
    exit 1
}

# Create scheduled task
$action = New-ScheduledTaskAction -Execute "PowerShell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$scriptPath`""
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes $triggerFrequency) -RepetitionDuration (New-TimeSpan -Days 3650)
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RunOnlyIfIdle:$false

# Register or update task
$existingTask = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue

if ($existingTask) {
    # Update existing task
    Set-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings
    Write-Output "Updated scheduled task '$taskName'"
} else {
    # Create new task
    try {
        Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -RunLevel Highest -User $env:USERNAME
        Write-Output "Created scheduled task '$taskName'"
    } catch {
        Write-Output "Error creating task: $_"
        Write-Output "Trying alternate method..."
        # Try with a simpler trigger
        $simpleTrigger = New-ScheduledTaskTrigger -Daily -At (Get-Date).AddMinutes(1)
        Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $simpleTrigger -Settings $settings -RunLevel Highest -User $env:USERNAME
        Write-Output "Created daily scheduled task '$taskName'"
        
        # Then try to modify it to add repetition
        try {
            $task = Get-ScheduledTask -TaskName $taskName
            $taskDefinition = $task.TaskDefinition
            $taskDefinition.Triggers[0].Repetition.Interval = "PT${triggerFrequency}M"  # XML format for duration
            $taskDefinition.Triggers[0].Repetition.Duration = "P3650D"                  # 10 years
            $taskDefinition.Triggers[0].Repetition.StopAtDurationEnd = $false
            Set-ScheduledTask -TaskName $taskName -InputObject $taskDefinition
            Write-Output "Updated task with repetition interval"
        } catch {
            Write-Output "Could not set repetition interval: $_"
            Write-Output "Task will run daily instead of every $triggerFrequency minutes"
        }
    }
}

Write-Output "Scheduled task '$taskName' set to run every $triggerFrequency minutes"
Write-Output "Cleaning script path: $scriptPath" 