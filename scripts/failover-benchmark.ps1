param(
    [int]$Iterations = 10,
    [string]$Namespace = "myflix",
    [string]$DbUser = "backend_user",
    [string]$DbName = "Django_DB",
    [string]$DbPassword = "backend_user_password",
    [string]$OutputCsv = "docs/failover-benchmark.csv"
)

$ErrorActionPreference = "Stop"

function Invoke-RoleProbe {
    param([string]$Tag)

    $name = "psql-$Tag-" + (Get-Random -Maximum 99999)
    $cmd = "psql -h postgres-ha-0.postgres-ha-headless.myflix.svc.cluster.local -U $DbUser -d $DbName -tAc 'select pg_is_in_recovery();'; psql -h postgres-ha-1.postgres-ha-headless.myflix.svc.cluster.local -U $DbUser -d $DbName -tAc 'select pg_is_in_recovery();'"

    kubectl run $name -n $Namespace --restart=Never --image=postgres:17 --env="PGPASSWORD=$DbPassword" --command -- sh -lc $cmd | Out-Null

    $phase = ""
    $deadline = (Get-Date).AddSeconds(120)
    while ((Get-Date) -lt $deadline) {
        $phase = (kubectl get pod -n $Namespace $name -o jsonpath='{.status.phase}' 2>$null).Trim()
        if ($phase -in @("Succeeded", "Failed")) {
            break
        }
        Start-Sleep -Seconds 1
    }

    $lines = (kubectl logs -n $Namespace $name 2>$null) -split "`n" | ForEach-Object { $_.Trim() } | Where-Object { $_ -in @("f", "t") }
    kubectl delete pod -n $Namespace $name --ignore-not-found=true | Out-Null
    return ,$lines
}

function Get-CurrentRoles {
    for ($try = 1; $try -le 3; $try++) {
        $roles = Invoke-RoleProbe -Tag "pre$try"
        if ($roles.Count -eq 2) {
            return $roles
        }
        Start-Sleep -Seconds 2
    }
    throw "Could not determine current roles from probe output."
}

function Get-PostRoles {
    for ($try = 1; $try -le 3; $try++) {
        $roles = Invoke-RoleProbe -Tag "post$try"
        if ($roles.Count -eq 2) {
            return $roles
        }
        Start-Sleep -Seconds 2
    }
    throw "Could not determine post-failover roles from probe output."
}

function Measure-FailoverOnce {
    param([int]$Index)

    $pre = Get-CurrentRoles
    if ($pre[0] -eq "f" -and $pre[1] -eq "t") {
        $primaryOrdinal = 0
        $standbyOrdinal = 1
    } elseif ($pre[0] -eq "t" -and $pre[1] -eq "f") {
        $primaryOrdinal = 1
        $standbyOrdinal = 0
    } else {
        throw "Unexpected role state before failover: $($pre -join ',')"
    }

    $primaryPod = "postgres-ha-$primaryOrdinal"
    $standbyPod = "postgres-ha-$standbyOrdinal"

    $t0 = Get-Date
    $since = $t0.ToString("o")
    $sw = [System.Diagnostics.Stopwatch]::StartNew()

    kubectl delete pod -n $Namespace $primaryPod | Out-Null

    $detectSec = $null
    $promoteSec = $null
    $maxPollSec = 150
    while ($sw.Elapsed.TotalSeconds -lt $maxPollSec) {
        $logs = kubectl logs -n $Namespace $standbyPod --since-time="$since" 2>$null
        if (-not $detectSec -and $logs -match "this node is the winner, will now promote itself") {
            $detectSec = [math]::Round($sw.Elapsed.TotalSeconds, 2)
        }
        if (-not $promoteSec -and ($logs -match "STANDBY PROMOTE successful" -or $logs -match "standby promoted to primary")) {
            $promoteSec = [math]::Round($sw.Elapsed.TotalSeconds, 2)
        }
        if ($detectSec -and $promoteSec) {
            break
        }
        Start-Sleep -Seconds 1
    }

    kubectl wait --for=condition=ready "pod/$primaryPod" -n $Namespace --timeout=300s | Out-Null
    $rejoinSec = [math]::Round($sw.Elapsed.TotalSeconds, 2)

    $post = Get-PostRoles
    $isHealthy = (($post.Count -eq 2) -and (($post[0] -eq "f" -and $post[1] -eq "t") -or ($post[0] -eq "t" -and $post[1] -eq "f")))

    $promotionLatency = $null
    if ($detectSec -and $promoteSec) {
        $promotionLatency = [math]::Round($promoteSec - $detectSec, 2)
    }

    return [PSCustomObject]@{
        run = $Index
        status = $(if ($isHealthy) { "ok" } else { "split_or_probe_error" })
        deleted_primary = $primaryPod
        promoted_node = $standbyPod
        detection_seconds = $detectSec
        promotion_seconds = $promoteSec
        promotion_latency_seconds = $promotionLatency
        old_primary_rejoin_seconds = $rejoinSec
        post_roles = ($post -join "/")
    }
}

function Heal-ClusterIfNeeded {
    param([string]$Reason)

    Write-Host "  healing cluster: $Reason"
    kubectl rollout restart statefulset/postgres-ha -n $Namespace | Out-Null
    kubectl rollout status statefulset/postgres-ha -n $Namespace --timeout=420s | Out-Null
}

$all = @()
for ($i = 1; $i -le $Iterations; $i++) {
    Write-Host "Running failover benchmark $i/$Iterations..."
    try {
        $result = Measure-FailoverOnce -Index $i
    } catch {
        $result = [PSCustomObject]@{
            run = $i
            status = "error"
            deleted_primary = ""
            promoted_node = ""
            detection_seconds = $null
            promotion_seconds = $null
            promotion_latency_seconds = $null
            old_primary_rejoin_seconds = $null
            post_roles = "n/a"
        }
        Heal-ClusterIfNeeded -Reason $_.Exception.Message
    }

    if ($result.status -ne "ok") {
        Heal-ClusterIfNeeded -Reason "post_roles=$($result.post_roles)"
    }

    $all += $result
    Write-Host ("  status={0} detect={1}s promote={2}s rejoin={3}s roles={4}" -f $result.status, $result.detection_seconds, $result.promotion_seconds, $result.old_primary_rejoin_seconds, $result.post_roles)
}

$dir = Split-Path -Parent $OutputCsv
if ($dir -and -not (Test-Path $dir)) {
    New-Item -ItemType Directory -Path $dir | Out-Null
}

$all | Export-Csv -NoTypeInformation -Encoding UTF8 -Path $OutputCsv

$okOnly = $all | Where-Object { $_.status -eq "ok" }
$detectAvg = [math]::Round((($okOnly | Where-Object { $_.detection_seconds } | Measure-Object -Property detection_seconds -Average).Average), 2)
$promoteAvg = [math]::Round((($okOnly | Where-Object { $_.promotion_seconds } | Measure-Object -Property promotion_seconds -Average).Average), 2)
$latencyAvg = [math]::Round((($okOnly | Where-Object { $_.promotion_latency_seconds } | Measure-Object -Property promotion_latency_seconds -Average).Average), 2)
$rejoinAvg = [math]::Round((($okOnly | Where-Object { $_.old_primary_rejoin_seconds } | Measure-Object -Property old_primary_rejoin_seconds -Average).Average), 2)
$successCount = ($okOnly | Measure-Object).Count

Write-Host ""
Write-Host "Benchmark complete."
Write-Host "CSV: $OutputCsv"
Write-Host ("Success runs: {0}/{1}" -f $successCount, $Iterations)
Write-Host ("AVG detect={0}s promote={1}s promote-latency={2}s rejoin={3}s" -f $detectAvg, $promoteAvg, $latencyAvg, $rejoinAvg)
