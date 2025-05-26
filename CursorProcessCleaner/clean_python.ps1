# Cleans idle Cursor Python processes
# This script keeps active Cursor processes and only removes idle ones

# Get all Python processes
$allPythonProcesses = Get-Process -Name python* -ErrorAction SilentlyContinue
Write-Output "Total Python processes found: $($allPythonProcesses.Count)"

# For debugging, list the processes and their paths
Write-Output "Listing all Python processes:"
foreach ($proc in $allPythonProcesses) {
    try {
        $path = $proc.Path
        Write-Output "PID: $($proc.Id), Name: $($proc.ProcessName), Path: $path"
    } catch {
        Write-Output "PID: $($proc.Id), Name: $($proc.ProcessName), Path: [Error accessing path]"
    }
}

# Filter Cursor-related Python processes based on several criteria
$cursorPythonProcesses = $allPythonProcesses | Where-Object {
    try {
        # Look for "cursor" in various properties
        $isCursorProcess = $false
        
        # Check process path
        if ($_.Path -match "cursor") { 
            $isCursorProcess = $true
        }
        
        # Check if process is started by Cursor
        $parentProcess = $null
        try {
            $parentProcess = Get-Process -Id (Get-WmiObject -Class Win32_Process -Filter "ProcessId = $($_.Id)").ParentProcessId -ErrorAction SilentlyContinue
            if ($parentProcess -and ($parentProcess.ProcessName -match "cursor" -or $parentProcess.Path -match "cursor")) {
                $isCursorProcess = $true
            }
        } catch {}
        
        # Return result
        $isCursorProcess
    } catch {
        # If any error occurs, don't include this process
        $false
    }
}

# Count processes before cleaning
$beforeCount = $cursorPythonProcesses.Count
Write-Output "Found $beforeCount Cursor-related Python processes"

# If no Cursor-related processes found, exit
if ($beforeCount -eq 0) {
    Write-Output "No Cursor-related Python processes to clean up."
    exit 0
}

# Get active Cursor processes (with CPU activity or started in last 5 minutes)
$activeProcesses = $cursorPythonProcesses | Where-Object {
    $_.CPU -gt 0 -or
    $_.TotalProcessorTime.TotalMinutes -gt 0 -or
    (Get-Date) - $_.StartTime -lt (New-TimeSpan -Minutes 5)
}

Write-Output "Active processes (will be kept): $($activeProcesses.Count)"

# Get processes to terminate (inactive for over 10 minutes)
$processesToKill = $cursorPythonProcesses | Where-Object {
    $_.Id -notin $activeProcesses.Id -and
    (Get-Date) - $_.StartTime -gt (New-TimeSpan -Minutes 10)
}

Write-Output "Inactive processes to terminate: $($processesToKill.Count)"

# Terminate inactive processes
foreach ($process in $processesToKill) {
    try {
        Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
        Write-Output "Terminated process: $($process.Id) ($($process.ProcessName))"
    } catch {
        Write-Output "Failed to terminate process $($process.Id): $_"
    }
}

# Calculate results
$afterCount = (Get-Process -Name python* | Where-Object {
    try {
        $isCursorProcess = $false
        
        # Check process path
        if ($_.Path -match "cursor") { 
            $isCursorProcess = $true
        }
        
        # Check if process is started by Cursor
        $parentProcess = $null
        try {
            $parentProcess = Get-Process -Id (Get-WmiObject -Class Win32_Process -Filter "ProcessId = $($_.Id)").ParentProcessId -ErrorAction SilentlyContinue
            if ($parentProcess -and ($parentProcess.ProcessName -match "cursor" -or $parentProcess.Path -match "cursor")) {
                $isCursorProcess = $true
            }
        } catch {}
        
        # Return result
        $isCursorProcess
    } catch {
        $false
    }
}).Count

Write-Output "Cleanup complete: Reduced from $beforeCount to $afterCount processes"
Write-Output "Terminated $($beforeCount - $afterCount) idle Python processes" 