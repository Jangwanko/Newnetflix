#!/usr/bin/env python3
import argparse
import csv
import json
import math
import statistics
import subprocess
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple


NAMESPACE = "myflix"
DB_NAME = "Django_DB"
DB_USER = "backend_user"
DB_PASSWORD = "backend_user_password"
TARGET_ALERTS = {"MyflixDatabaseDown", "MyflixPostgresExporterDown"}
SETTINGS = {
    "poll_interval_seconds": 5,
    "precheck_timeout": 120,
    "role_wait_timeout": 120,
    "primary_watch_timeout": 210,
    "standby_watch_timeout": 120,
    "pod_ready_timeout": 300,
    "pgpool_timeout_primary": 240,
    "pgpool_timeout_standby": 120,
    "readyz_probe_seconds_primary": 90,
    "readyz_probe_seconds_standby": 60,
    "sleep_between_runs": 2,
}


@dataclass
class RunResult:
    scenario: str
    run: int
    success: bool
    fail_reason: str
    detected_seconds: Optional[float]
    promoted_seconds: Optional[float]
    rto_seconds: Optional[float]
    rejoin_seconds: Optional[float]
    pgpool_recovery_seconds: Optional[float]
    split_brain: bool
    primary_count_end: Optional[int]
    standby_count_end: Optional[int]
    integrity_ok: bool
    txid_before: Optional[int]
    txid_after: Optional[int]
    marker_exists_after: Optional[bool]
    readyz_5xx_count: Optional[int]
    readyz_non200_count: Optional[int]
    readyz_avg_ms: Optional[float]
    readyz_p95_ms: Optional[float]
    alert_fired: bool
    alert_cleared_after: bool
    deleted_pod: str
    promoted_pod: str
    started_at: str
    finished_at: str
    precheck_seconds: Optional[float]
    failure_action_seconds: Optional[float]
    recovery_wait_seconds: Optional[float]
    verification_seconds: Optional[float]
    verify_integrity_seconds: Optional[float]
    verify_roles_seconds: Optional[float]
    verify_alert_seconds: Optional[float]
    verify_readyz_seconds: Optional[float]
    wall_seconds: Optional[float]
    core_success: bool
    extended_success: bool
    fail_codes: str


def run(cmd: List[str], check: bool = True, timeout: Optional[int] = None) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, check=check, timeout=timeout)


def kubectl(args: List[str], check: bool = True, timeout: Optional[int] = None) -> str:
    cp = run(["kubectl"] + args, check=check, timeout=timeout)
    return cp.stdout.strip()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def p95(values: List[float]) -> Optional[float]:
    if not values:
        return None
    s = sorted(values)
    idx = max(0, math.ceil(0.95 * len(s)) - 1)
    return round(s[idx], 2)


def safe_float(v: str) -> Optional[float]:
    try:
        return float(v)
    except Exception:
        return None


def safe_int(v: str) -> Optional[int]:
    try:
        return int(v)
    except Exception:
        return None


def configure_settings(args: argparse.Namespace) -> None:
    if args.fast:
        SETTINGS.update(
            {
                "poll_interval_seconds": 3,
                "precheck_timeout": 45,
                "role_wait_timeout": 45,
                "primary_watch_timeout": 75,
                "standby_watch_timeout": 60,
                "pod_ready_timeout": 120,
                "pgpool_timeout_primary": 75,
                "pgpool_timeout_standby": 60,
                "readyz_probe_seconds_primary": 25,
                "readyz_probe_seconds_standby": 20,
                "sleep_between_runs": 0,
            }
        )

    for key in SETTINGS.keys():
        val = getattr(args, key, None)
        if val is not None:
            SETTINGS[key] = val


def get_db_pods() -> List[str]:
    out = kubectl(["get", "pods", "-n", NAMESPACE, "-l", "app=postgres-ha", "-o", "jsonpath={.items[*].metadata.name}"])
    pods = [p for p in out.split() if p.startswith("postgres-ha-")]
    return sorted(pods)


def get_roles() -> Dict[str, str]:
    roles: Dict[str, str] = {}
    for pod in get_db_pods():
        try:
            out = kubectl(
                [
                    "exec",
                    "-n",
                    NAMESPACE,
                    pod,
                    "--",
                    "env",
                    f"PGPASSWORD={DB_PASSWORD}",
                    "/opt/bitnami/postgresql/bin/psql",
                    "-U",
                    DB_USER,
                    "-d",
                    DB_NAME,
                    "-At",
                    "-c",
                    "select case when pg_is_in_recovery() then 'standby' else 'primary' end;",
                ],
                check=True,
            )
            role = out.strip().splitlines()[-1].strip() if out.strip() else ""
            if role in {"primary", "standby"}:
                roles[pod] = role
        except Exception:
            continue
    return roles


def role_counts(roles: Dict[str, str]) -> Tuple[int, int]:
    primary = sum(1 for r in roles.values() if r == "primary")
    standby = sum(1 for r in roles.values() if r == "standby")
    return primary, standby


def wait_until_roles(target_primary: int, target_standby: int, timeout_sec: int = 180) -> Dict[str, str]:
    start = time.time()
    last = {}
    while time.time() - start < timeout_sec:
        roles = get_roles()
        p, s = role_counts(roles)
        last = roles
        if p == target_primary and s == target_standby:
            return roles
        time.sleep(SETTINGS["poll_interval_seconds"])
    return last


def is_pod_ready(pod: str) -> bool:
    out = kubectl(
        [
            "get",
            "pod",
            pod,
            "-n",
            NAMESPACE,
            "-o",
            "jsonpath={.status.conditions[?(@.type=='Ready')].status}",
        ],
        check=False,
    )
    return "True" in out


def get_pod_uid(pod: str) -> Optional[str]:
    out = kubectl(["get", "pod", pod, "-n", NAMESPACE, "-o", "jsonpath={.metadata.uid}"], check=False)
    uid = out.strip()
    return uid if uid else None


def wait_for_recreation_and_roles(
    recreated_pod: str,
    expected_total: int = 3,
    timeout_sec: int = 300,
    previous_uid: Optional[str] = None,
) -> Tuple[Optional[float], Dict[str, str], int]:
    start = time.time()
    last_roles: Dict[str, str] = {}
    last_count = 0
    while time.time() - start < timeout_sec:
        pods = get_db_pods()
        last_count = len(pods)
        last_roles = get_roles()
        p, s = role_counts(last_roles)
        current_uid = get_pod_uid(recreated_pod) if recreated_pod in pods else None
        recreated_uid_ok = current_uid is not None and (previous_uid is None or current_uid != previous_uid)
        recreated_ok = recreated_uid_ok and is_pod_ready(recreated_pod)
        role_ok = last_roles.get(recreated_pod) == "standby"
        if recreated_ok and last_count >= expected_total and p == 1 and s == 2 and role_ok:
            return round(time.time() - start, 2), last_roles, last_count
        time.sleep(SETTINGS["poll_interval_seconds"])
    return None, last_roles, last_count


def ensure_cluster_healthy() -> bool:
    try:
        kubectl(["wait", "--for=condition=ready", "pod", "-l", "app=postgres-ha", "-n", NAMESPACE, "--timeout=300s"], check=True, timeout=320)
    except Exception:
        return False
    roles = wait_until_roles(1, 2, timeout_sec=SETTINGS["precheck_timeout"])
    p, s = role_counts(roles)
    return p == 1 and s == 2


def heal_cluster() -> None:
    try:
        kubectl(["rollout", "restart", "statefulset/postgres-ha", "-n", NAMESPACE], check=False)
        kubectl(["rollout", "status", "statefulset/postgres-ha", "-n", NAMESPACE, "--timeout=420s"], check=False, timeout=440)
        kubectl(["rollout", "restart", "deployment/postgres-proxy", "-n", NAMESPACE], check=False)
        kubectl(["rollout", "status", "deployment/postgres-proxy", "-n", NAMESPACE, "--timeout=240s"], check=False, timeout=260)
    except Exception:
        pass


def get_any_db_pod() -> str:
    pods = get_db_pods()
    if not pods:
        raise RuntimeError("No postgres-ha pods found")
    return pods[0]


def psql_on_pod(pod: str, host: str, sql: str, timeout_sec: int = 10) -> str:
    return kubectl(
        [
            "exec",
            "-n",
            NAMESPACE,
            pod,
            "--",
            "env",
            f"PGPASSWORD={DB_PASSWORD}",
            "/opt/bitnami/postgresql/bin/psql",
            "-h",
            host,
            "-U",
            DB_USER,
            "-d",
            DB_NAME,
            "-At",
            "-c",
            sql,
        ],
        timeout=timeout_sec,
    ).strip()


def psql_via_primary(sql: str, timeout_sec: int = 10, retries: int = 5) -> str:
    last_error = None
    for _ in range(retries):
        roles = get_roles()
        primary_pods = [p for p, r in roles.items() if r == "primary"]
        if not primary_pods:
            time.sleep(2)
            continue
        try:
            return psql_on_pod(primary_pods[0], "127.0.0.1", sql, timeout_sec=timeout_sec)
        except Exception as e:
            last_error = e
            time.sleep(2)
    raise RuntimeError(f"psql_via_primary failed after retries: {last_error}")


def psql_via_pgpool(sql: str, timeout_sec: int = 10, retries: int = 5) -> str:
    last_error = None
    for _ in range(retries):
        pod = get_any_db_pod()
        try:
            return kubectl(
                [
                    "exec",
                    "-n",
                    NAMESPACE,
                    pod,
                    "--",
                    "env",
                    f"PGPASSWORD={DB_PASSWORD}",
                    "/opt/bitnami/postgresql/bin/psql",
                    "-h",
                    "postgres",
                    "-U",
                    DB_USER,
                    "-d",
                    DB_NAME,
                    "-At",
                    "-c",
                    sql,
                ],
                timeout=timeout_sec,
            ).strip()
        except Exception as e:
            last_error = e
            time.sleep(2)
    raise RuntimeError(f"psql_via_pgpool failed after retries: {last_error}")


def ensure_integrity_table() -> None:
    psql_via_primary(
        "create table if not exists ha_drill_integrity("
        "id bigserial primary key,"
        "scenario text not null,"
        "run_no int not null,"
        "marker bigint not null unique,"
        "created_at timestamptz not null default now()"
        ");"
    )


def insert_integrity_marker(scenario: str, run_no: int, marker: int) -> Tuple[Optional[int], Optional[int]]:
    psql_via_primary(f"insert into ha_drill_integrity(scenario,run_no,marker) values ('{scenario}',{run_no},{marker});")
    txid = safe_int(psql_via_primary("select txid_current();"))
    cnt = safe_int(psql_via_primary("select count(*) from ha_drill_integrity;"))
    return txid, cnt


def check_integrity_marker(marker: int) -> Tuple[Optional[int], Optional[int], Optional[bool]]:
    txid = safe_int(psql_via_primary("select txid_current();"))
    cnt = safe_int(psql_via_primary("select count(*) from ha_drill_integrity;"))
    exists = psql_via_primary(f"select exists(select 1 from ha_drill_integrity where marker={marker});").strip().lower()
    return txid, cnt, exists == "t"


def get_alert_firing_names() -> List[str]:
    try:
        out = kubectl(
            [
                "get",
                "--raw",
                "/api/v1/namespaces/monitoring/services/http:prometheus:9090/proxy/api/v1/alerts",
            ]
        )
        data = json.loads(out)
        alerts = data.get("data", {}).get("alerts", [])
        names = []
        for a in alerts:
            if a.get("state") == "firing":
                labels = a.get("labels", {})
                names.append(labels.get("alertname", ""))
        return [n for n in names if n]
    except Exception:
        return []


def start_readyz_probe(name: str, seconds: int = 90) -> None:
    script = (
        f"i=0; while [ $i -lt {seconds} ]; do "
        "i=$((i+1)); ts=$(date +%s%3N); "
        "line=$(curl -s -o /dev/null -w \"%{http_code},%{time_total}\" http://web.myflix.svc.cluster.local:8000/readyz || echo \"000,9\"); "
        "echo \"$ts,$line\"; sleep 1; "
        "done"
    )
    kubectl(
        [
            "run",
            name,
            "-n",
            NAMESPACE,
            "--restart=Never",
            "--image=curlimages/curl:8.12.1",
            "--command",
            "--",
            "sh",
            "-lc",
            script,
        ]
    )


def collect_readyz_probe(name: str) -> Tuple[int, int, Optional[float], Optional[float]]:
    kubectl(["wait", "--for=jsonpath={.status.phase}=Succeeded", f"pod/{name}", "-n", NAMESPACE, "--timeout=180s"], check=False)
    time.sleep(1)
    try:
        logs = kubectl(["logs", "-n", NAMESPACE, name], check=False)
    finally:
        kubectl(["delete", "pod", "-n", NAMESPACE, name, "--ignore-not-found=true"], check=False)
    vals: List[float] = []
    c5xx = 0
    non200 = 0
    for line in logs.splitlines():
        parts = [p.strip() for p in line.strip().split(",")]
        if len(parts) != 3:
            continue
        code = safe_int(parts[1])
        sec = safe_float(parts[2])
        if code is None:
            continue
        if code != 200:
            non200 += 1
        if 500 <= code <= 599:
            c5xx += 1
        if sec is not None and sec < 8:
            vals.append(sec * 1000.0)
    avg_ms = round(statistics.fmean(vals), 2) if vals else None
    p95_ms = p95(vals)
    return c5xx, non200, avg_ms, p95_ms


def query_pgpool_until_success(start_ts: float, timeout_sec: int = 180) -> Optional[float]:
    while time.time() - start_ts < timeout_sec:
        try:
            out = psql_via_pgpool("select 1;")
            if out.strip().endswith("1"):
                return round(time.time() - start_ts, 2)
        except Exception:
            pass
        time.sleep(1)
    return None


def detect_promotion_from_logs(candidate_pods: List[str], since_iso: str) -> Tuple[Optional[float], Optional[float], str]:
    detected = None
    promoted = None
    promoted_pod = ""
    start = time.time()
    while time.time() - start < SETTINGS["primary_watch_timeout"]:
        for pod in candidate_pods:
            out = kubectl(["logs", "-n", NAMESPACE, pod, f"--since-time={since_iso}"], check=False)
            if detected is None and "this node is the winner, will now promote itself" in out:
                detected = round(time.time() - start, 2)
            if promoted is None and ("STANDBY PROMOTE successful" in out or "standby promoted to primary" in out):
                promoted = round(time.time() - start, 2)
                promoted_pod = pod
        if detected is not None and promoted is not None:
            break
        time.sleep(1)
    return detected, promoted, promoted_pod


def scenario_primary_failover(run_no: int) -> RunResult:
    started_at = now_iso()
    t_run_start = time.time()
    fail_reason = ""
    deleted_pod = ""
    promoted_pod = ""
    detected = None
    promoted = None
    rto = None
    rejoin = None
    pgpool_recovery = None
    split_brain = False
    integrity_ok = False
    tx_before = None
    tx_after = None
    marker_exists = None
    readyz_5xx = None
    readyz_non200 = None
    readyz_avg = None
    readyz_p95 = None
    alert_fired = False
    alert_cleared = False
    primary_end = None
    standby_end = None
    precheck_seconds = None
    failure_action_seconds = None
    recovery_wait_seconds = None
    verification_seconds = None
    verify_integrity_seconds = None
    verify_roles_seconds = None
    verify_alert_seconds = None
    verify_readyz_seconds = None
    core_success = False
    extended_success = False
    fail_codes: List[str] = []

    probe_name = f"readyz-pf-{run_no}-{int(time.time())}"
    marker = int(time.time() * 1000) + run_no

    try:
        t_stage = time.time()
        roles = wait_until_roles(1, 2, timeout_sec=SETTINGS["precheck_timeout"])
        p, s = role_counts(roles)
        if p != 1 or s != 2:
            raise RuntimeError(f"precheck roles invalid: primary={p}, standby={s}")
        primary_pod = [k for k, v in roles.items() if v == "primary"][0]
        standby_pods = [k for k, v in roles.items() if v == "standby"]
        deleted_pod = primary_pod
        deleted_uid = get_pod_uid(primary_pod)
        if not deleted_uid:
            raise RuntimeError(f"failed to read pod uid before delete: {primary_pod}")

        tx_before, _ = insert_integrity_marker("primary_failover", run_no, marker)
        start_readyz_probe(probe_name, seconds=SETTINGS["readyz_probe_seconds_primary"])
        precheck_seconds = round(time.time() - t_stage, 2)

        t_stage = time.time()
        since_iso = now_iso()
        t0 = time.time()
        kubectl(["delete", "pod", "-n", NAMESPACE, primary_pod])

        while time.time() - t0 < SETTINGS["primary_watch_timeout"]:
            firing = set(get_alert_firing_names())
            if TARGET_ALERTS & firing:
                alert_fired = True
            roles_now = get_roles()
            p_now, _ = role_counts(roles_now)
            if p_now > 1:
                split_brain = True
                break
            if p_now == 1:
                new_primary = [k for k, v in roles_now.items() if v == "primary"]
                if new_primary and new_primary[0] != primary_pod:
                    rto = round(time.time() - t0, 2)
                    promoted_pod = new_primary[0]
                    break
            time.sleep(1)

        d, pr, lpod = detect_promotion_from_logs(standby_pods, since_iso)
        detected = d
        promoted = pr
        if lpod and not promoted_pod:
            promoted_pod = lpod
        failure_action_seconds = round(time.time() - t_stage, 2)

        t_stage = time.time()
        try:
            rejoin, _, _ = wait_for_recreation_and_roles(
                recreated_pod=primary_pod,
                expected_total=3,
                timeout_sec=SETTINGS["pod_ready_timeout"],
                previous_uid=deleted_uid,
            )
        except Exception:
            pass

        pgpool_recovery = query_pgpool_until_success(t0, timeout_sec=SETTINGS["pgpool_timeout_primary"])
        recovery_wait_seconds = round(time.time() - t_stage, 2)

        t_stage = time.time()
        t_sub = time.time()
        tx_after, _, marker_exists = check_integrity_marker(marker)
        integrity_ok = bool(marker_exists)
        verify_integrity_seconds = round(time.time() - t_sub, 2)

        t_sub = time.time()
        roles_end = get_roles()
        primary_end, standby_end = role_counts(roles_end)
        if primary_end != 1:
            split_brain = True
        verify_roles_seconds = round(time.time() - t_sub, 2)

        t_sub = time.time()
        firing_end = set(get_alert_firing_names())
        alert_cleared = not bool(TARGET_ALERTS & firing_end)
        verify_alert_seconds = round(time.time() - t_sub, 2)

        t_sub = time.time()
        readyz_5xx, readyz_non200, readyz_avg, readyz_p95 = collect_readyz_probe(probe_name)
        verify_readyz_seconds = round(time.time() - t_sub, 2)
        verification_seconds = round(time.time() - t_stage, 2)

        core_success = (
            not split_brain
            and integrity_ok
            and primary_end == 1
            and standby_end == 2
            and rto is not None
            and rejoin is not None
        )
        extended_success = (
            core_success
            and pgpool_recovery is not None
            and alert_cleared
            and (readyz_5xx or 0) == 0
        )

        if split_brain:
            fail_codes.append("FAIL_SPLIT_BRAIN")
        if rto is None:
            fail_codes.append("FAIL_NO_PROMOTION")
        if rejoin is None:
            fail_codes.append("FAIL_REJOIN_TIMEOUT")
        if not integrity_ok:
            fail_codes.append("FAIL_INTEGRITY")
        if primary_end != 1 or standby_end != 2:
            fail_codes.append("FAIL_ROLE_NOT_CONVERGED")
        if pgpool_recovery is None:
            fail_codes.append("FAIL_PGPOOL_RECOVERY_TIMEOUT")
        if not alert_cleared:
            fail_codes.append("FAIL_ALERT_UNCLEARED")
        if (readyz_5xx or 0) > 0:
            fail_codes.append("FAIL_READYZ_5XX")

        success = core_success
        if not success and not fail_reason:
            fail_reason = "|".join(fail_codes) if fail_codes else "postcheck criteria not met"
    except Exception as e:
        success = False
        fail_reason = str(e)
        core_success = False
        extended_success = False
        fail_codes = ["FAIL_EXCEPTION"]
        try:
            readyz_5xx, readyz_non200, readyz_avg, readyz_p95 = collect_readyz_probe(probe_name)
        except Exception:
            pass

    finished_at = now_iso()
    wall_seconds = round(time.time() - t_run_start, 2)
    return RunResult(
        scenario="primary_failover",
        run=run_no,
        success=success,
        fail_reason=fail_reason,
        detected_seconds=detected,
        promoted_seconds=promoted,
        rto_seconds=rto,
        rejoin_seconds=rejoin,
        pgpool_recovery_seconds=pgpool_recovery,
        split_brain=split_brain,
        primary_count_end=primary_end,
        standby_count_end=standby_end,
        integrity_ok=integrity_ok,
        txid_before=tx_before,
        txid_after=tx_after,
        marker_exists_after=marker_exists,
        readyz_5xx_count=readyz_5xx,
        readyz_non200_count=readyz_non200,
        readyz_avg_ms=readyz_avg,
        readyz_p95_ms=readyz_p95,
        alert_fired=alert_fired,
        alert_cleared_after=alert_cleared,
        deleted_pod=deleted_pod,
        promoted_pod=promoted_pod,
        started_at=started_at,
        finished_at=finished_at,
        precheck_seconds=precheck_seconds,
        failure_action_seconds=failure_action_seconds,
        recovery_wait_seconds=recovery_wait_seconds,
        verification_seconds=verification_seconds,
        verify_integrity_seconds=verify_integrity_seconds,
        verify_roles_seconds=verify_roles_seconds,
        verify_alert_seconds=verify_alert_seconds,
        verify_readyz_seconds=verify_readyz_seconds,
        wall_seconds=wall_seconds,
        core_success=core_success,
        extended_success=extended_success,
        fail_codes="|".join(fail_codes),
    )


def scenario_standby_recovery(run_no: int) -> RunResult:
    started_at = now_iso()
    t_run_start = time.time()
    fail_reason = ""
    deleted_pod = ""
    promoted_pod = ""
    split_brain = False
    integrity_ok = False
    tx_before = None
    tx_after = None
    marker_exists = None
    readyz_5xx = None
    readyz_non200 = None
    readyz_avg = None
    readyz_p95 = None
    alert_fired = False
    alert_cleared = False
    primary_end = None
    standby_end = None
    rejoin = None
    pgpool_recovery = None
    precheck_seconds = None
    failure_action_seconds = None
    recovery_wait_seconds = None
    verification_seconds = None
    verify_integrity_seconds = None
    verify_roles_seconds = None
    verify_alert_seconds = None
    verify_readyz_seconds = None
    core_success = False
    extended_success = False
    fail_codes: List[str] = []
    probe_name = f"readyz-sr-{run_no}-{int(time.time())}"
    marker = int(time.time() * 1000) + 100000 + run_no

    try:
        t_stage = time.time()
        roles = wait_until_roles(1, 2, timeout_sec=SETTINGS["precheck_timeout"])
        p, s = role_counts(roles)
        if p != 1 or s != 2:
            raise RuntimeError(f"precheck roles invalid: primary={p}, standby={s}")
        standby_pods = [k for k, v in roles.items() if v == "standby"]
        deleted_pod = standby_pods[0]
        deleted_uid = get_pod_uid(deleted_pod)
        if not deleted_uid:
            raise RuntimeError(f"failed to read pod uid before delete: {deleted_pod}")

        tx_before, _ = insert_integrity_marker("standby_recovery", run_no, marker)
        start_readyz_probe(probe_name, seconds=SETTINGS["readyz_probe_seconds_standby"])
        precheck_seconds = round(time.time() - t_stage, 2)

        t_stage = time.time()
        t0 = time.time()
        kubectl(["delete", "pod", "-n", NAMESPACE, deleted_pod])

        while time.time() - t0 < SETTINGS["standby_watch_timeout"]:
            firing = set(get_alert_firing_names())
            if TARGET_ALERTS & firing:
                alert_fired = True
            roles_now = get_roles()
            p_now, _ = role_counts(roles_now)
            if p_now > 1:
                split_brain = True
                break
            time.sleep(1)
        failure_action_seconds = round(time.time() - t_stage, 2)

        t_stage = time.time()
        try:
            rejoin, _, _ = wait_for_recreation_and_roles(
                recreated_pod=deleted_pod,
                expected_total=3,
                timeout_sec=SETTINGS["pod_ready_timeout"],
                previous_uid=deleted_uid,
            )
        except Exception:
            pass

        # Standby recovery can spend most of the budget on pod ready/rejoin.
        # Measure pgpool recovery from "now" to avoid false failures from elapsed pre-steps.
        pgpool_recovery = query_pgpool_until_success(time.time(), timeout_sec=SETTINGS["pgpool_timeout_standby"])
        recovery_wait_seconds = round(time.time() - t_stage, 2)

        t_stage = time.time()
        t_sub = time.time()
        tx_after, _, marker_exists = check_integrity_marker(marker)
        integrity_ok = bool(marker_exists)
        verify_integrity_seconds = round(time.time() - t_sub, 2)

        t_sub = time.time()
        roles_end = get_roles()
        primary_end, standby_end = role_counts(roles_end)
        if primary_end != 1:
            split_brain = True
        verify_roles_seconds = round(time.time() - t_sub, 2)

        t_sub = time.time()
        firing_end = set(get_alert_firing_names())
        alert_cleared = not bool(TARGET_ALERTS & firing_end)
        verify_alert_seconds = round(time.time() - t_sub, 2)

        t_sub = time.time()
        readyz_5xx, readyz_non200, readyz_avg, readyz_p95 = collect_readyz_probe(probe_name)
        verify_readyz_seconds = round(time.time() - t_sub, 2)
        verification_seconds = round(time.time() - t_stage, 2)

        core_success = (
            not split_brain
            and integrity_ok
            and primary_end == 1
            and standby_end == 2
            and rejoin is not None
        )
        extended_success = (
            core_success
            and pgpool_recovery is not None
            and alert_cleared
            and (readyz_5xx or 0) == 0
        )

        if split_brain:
            fail_codes.append("FAIL_SPLIT_BRAIN")
        if rejoin is None:
            fail_codes.append("FAIL_REJOIN_TIMEOUT")
        if not integrity_ok:
            fail_codes.append("FAIL_INTEGRITY")
        if primary_end != 1 or standby_end != 2:
            fail_codes.append("FAIL_ROLE_NOT_CONVERGED")
        if pgpool_recovery is None:
            fail_codes.append("FAIL_PGPOOL_RECOVERY_TIMEOUT")
        if not alert_cleared:
            fail_codes.append("FAIL_ALERT_UNCLEARED")
        if (readyz_5xx or 0) > 0:
            fail_codes.append("FAIL_READYZ_5XX")

        success = core_success
        if not success and not fail_reason:
            fail_reason = "|".join(fail_codes) if fail_codes else "postcheck criteria not met"
    except Exception as e:
        success = False
        fail_reason = str(e)
        core_success = False
        extended_success = False
        fail_codes = ["FAIL_EXCEPTION"]
        try:
            readyz_5xx, readyz_non200, readyz_avg, readyz_p95 = collect_readyz_probe(probe_name)
        except Exception:
            pass

    finished_at = now_iso()
    wall_seconds = round(time.time() - t_run_start, 2)
    return RunResult(
        scenario="standby_recovery",
        run=run_no,
        success=success,
        fail_reason=fail_reason,
        detected_seconds=None,
        promoted_seconds=None,
        rto_seconds=None,
        rejoin_seconds=rejoin,
        pgpool_recovery_seconds=pgpool_recovery,
        split_brain=split_brain,
        primary_count_end=primary_end,
        standby_count_end=standby_end,
        integrity_ok=integrity_ok,
        txid_before=tx_before,
        txid_after=tx_after,
        marker_exists_after=marker_exists,
        readyz_5xx_count=readyz_5xx,
        readyz_non200_count=readyz_non200,
        readyz_avg_ms=readyz_avg,
        readyz_p95_ms=readyz_p95,
        alert_fired=alert_fired,
        alert_cleared_after=alert_cleared,
        deleted_pod=deleted_pod,
        promoted_pod=promoted_pod,
        started_at=started_at,
        finished_at=finished_at,
        precheck_seconds=precheck_seconds,
        failure_action_seconds=failure_action_seconds,
        recovery_wait_seconds=recovery_wait_seconds,
        verification_seconds=verification_seconds,
        verify_integrity_seconds=verify_integrity_seconds,
        verify_roles_seconds=verify_roles_seconds,
        verify_alert_seconds=verify_alert_seconds,
        verify_readyz_seconds=verify_readyz_seconds,
        wall_seconds=wall_seconds,
        core_success=core_success,
        extended_success=extended_success,
        fail_codes="|".join(fail_codes),
    )


def summarize(results: List[RunResult]) -> Dict[str, Dict[str, object]]:
    out: Dict[str, Dict[str, object]] = {}
    for scenario in sorted(set(r.scenario for r in results)):
        rows = [r for r in results if r.scenario == scenario]
        ok = [r for r in rows if r.success]
        success_rate = round(len(ok) / len(rows), 4) if rows else 0.0
        core_ok = [r for r in rows if r.core_success]
        extended_ok = [r for r in rows if r.extended_success]
        core_success_rate = round(len(core_ok) / len(rows), 4) if rows else 0.0
        extended_success_rate = round(len(extended_ok) / len(rows), 4) if rows else 0.0

        def metric_stats(values: List[float]) -> Dict[str, Optional[float]]:
            if not values:
                return {"max": None, "avg": None, "p95": None}
            return {
                "max": round(max(values), 2),
                "avg": round(statistics.fmean(values), 2),
                "p95": p95(values),
            }

        rto_vals = [r.rto_seconds for r in ok if r.rto_seconds is not None]
        rejoin_vals = [r.rejoin_seconds for r in ok if r.rejoin_seconds is not None]
        pgpool_vals = [r.pgpool_recovery_seconds for r in ok if r.pgpool_recovery_seconds is not None]
        readyz_p95_vals = [r.readyz_p95_ms for r in rows if r.readyz_p95_ms is not None]
        wall_vals = [r.wall_seconds for r in rows if r.wall_seconds is not None]
        precheck_vals = [r.precheck_seconds for r in rows if r.precheck_seconds is not None]
        action_vals = [r.failure_action_seconds for r in rows if r.failure_action_seconds is not None]
        recovery_vals = [r.recovery_wait_seconds for r in rows if r.recovery_wait_seconds is not None]
        verify_vals = [r.verification_seconds for r in rows if r.verification_seconds is not None]
        verify_integrity_vals = [r.verify_integrity_seconds for r in rows if r.verify_integrity_seconds is not None]
        verify_roles_vals = [r.verify_roles_seconds for r in rows if r.verify_roles_seconds is not None]
        verify_alert_vals = [r.verify_alert_seconds for r in rows if r.verify_alert_seconds is not None]
        verify_readyz_vals = [r.verify_readyz_seconds for r in rows if r.verify_readyz_seconds is not None]
        readyz_5xx_total = sum(r.readyz_5xx_count or 0 for r in rows)
        split_brain_count = sum(1 for r in rows if r.split_brain)
        integrity_fail_count = sum(1 for r in rows if not r.integrity_ok)
        alert_fire_count = sum(1 for r in rows if r.alert_fired)
        alert_uncleared_count = sum(1 for r in rows if not r.alert_cleared_after)
        fail_code_counts: Dict[str, int] = {}
        for r in rows:
            for code in [c for c in (r.fail_codes or "").split("|") if c]:
                fail_code_counts[code] = fail_code_counts.get(code, 0) + 1

        out[scenario] = {
            "runs": len(rows),
            "success_runs": len(ok),
            "success_rate": success_rate,
            "core_success_runs": len(core_ok),
            "core_success_rate": core_success_rate,
            "extended_success_runs": len(extended_ok),
            "extended_success_rate": extended_success_rate,
            "rto_seconds": metric_stats([v for v in rto_vals if v is not None]),
            "rejoin_seconds": metric_stats([v for v in rejoin_vals if v is not None]),
            "pgpool_recovery_seconds": metric_stats([v for v in pgpool_vals if v is not None]),
            "readyz_p95_ms": metric_stats([v for v in readyz_p95_vals if v is not None]),
            "wall_seconds": metric_stats([v for v in wall_vals if v is not None]),
            "precheck_seconds": metric_stats([v for v in precheck_vals if v is not None]),
            "failure_action_seconds": metric_stats([v for v in action_vals if v is not None]),
            "recovery_wait_seconds": metric_stats([v for v in recovery_vals if v is not None]),
            "verification_seconds": metric_stats([v for v in verify_vals if v is not None]),
            "verify_integrity_seconds": metric_stats([v for v in verify_integrity_vals if v is not None]),
            "verify_roles_seconds": metric_stats([v for v in verify_roles_vals if v is not None]),
            "verify_alert_seconds": metric_stats([v for v in verify_alert_vals if v is not None]),
            "verify_readyz_seconds": metric_stats([v for v in verify_readyz_vals if v is not None]),
            "readyz_5xx_total": readyz_5xx_total,
            "split_brain_count": split_brain_count,
            "integrity_fail_count": integrity_fail_count,
            "alert_fired_count": alert_fire_count,
            "alert_uncleared_count": alert_uncleared_count,
            "fail_code_counts": fail_code_counts,
        }
    return out


def write_csv(results: List[RunResult], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(asdict(results[0]).keys()))
        writer.writeheader()
        for r in results:
            writer.writerow(asdict(r))


def main() -> None:
    parser = argparse.ArgumentParser(description="HA drill: primary failover + standby recovery")
    parser.add_argument("--iterations", type=int, default=10)
    parser.add_argument("--output-json", default="docs/ha-drill-summary.json")
    parser.add_argument("--output-csv", default="docs/ha-drill-runs.csv")
    parser.add_argument("--fast", action="store_true", help="Use shorter timeouts/probe windows for quick local checks")
    parser.add_argument(
        "--scenarios",
        default="primary_failover,standby_recovery",
        help="Comma-separated scenarios to run: primary_failover,standby_recovery",
    )
    parser.add_argument("--poll-interval-seconds", type=int, default=None)
    parser.add_argument("--precheck-timeout", type=int, default=None)
    parser.add_argument("--role-wait-timeout", type=int, default=None)
    parser.add_argument("--primary-watch-timeout", type=int, default=None)
    parser.add_argument("--standby-watch-timeout", type=int, default=None)
    parser.add_argument("--pod-ready-timeout", type=int, default=None)
    parser.add_argument("--pgpool-timeout-primary", type=int, default=None)
    parser.add_argument("--pgpool-timeout-standby", type=int, default=None)
    parser.add_argument("--readyz-probe-seconds-primary", type=int, default=None)
    parser.add_argument("--readyz-probe-seconds-standby", type=int, default=None)
    parser.add_argument("--sleep-between-runs", type=int, default=None)
    args = parser.parse_args()
    configure_settings(args)

    selected = {s.strip() for s in args.scenarios.split(",") if s.strip()}
    allowed = {"primary_failover", "standby_recovery"}
    if not selected or not selected.issubset(allowed):
        raise SystemExit("Invalid --scenarios value. Use primary_failover,standby_recovery")

    print("[1/4] Ensuring baseline cluster health...")
    if not ensure_cluster_healthy():
        print("Baseline unhealthy, healing once...")
        heal_cluster()
        if not ensure_cluster_healthy():
            raise SystemExit("Cluster not healthy enough to run drill.")

    print("[2/4] Preparing integrity table...")
    ensure_integrity_table()

    all_results: List[RunResult] = []

    if "primary_failover" in selected:
        print("[3/4] Running primary failover scenario...")
        for i in range(1, args.iterations + 1):
            print(f"  - primary_failover run {i}/{args.iterations}")
            res = scenario_primary_failover(i)
            all_results.append(res)
            print(
                f"    core={res.core_success} ext={res.extended_success} "
                f"rto={res.rto_seconds} rejoin={res.rejoin_seconds} reason={res.fail_reason}"
            )
            if not res.success:
                print("    healing after failure...")
                heal_cluster()
            if SETTINGS["sleep_between_runs"] > 0:
                time.sleep(SETTINGS["sleep_between_runs"])

    if "standby_recovery" in selected:
        print("[4/4] Running standby recovery scenario...")
        for i in range(1, args.iterations + 1):
            print(f"  - standby_recovery run {i}/{args.iterations}")
            res = scenario_standby_recovery(i)
            all_results.append(res)
            print(
                f"    core={res.core_success} ext={res.extended_success} "
                f"rejoin={res.rejoin_seconds} reason={res.fail_reason}"
            )
            if not res.success:
                print("    healing after failure...")
                heal_cluster()
            if SETTINGS["sleep_between_runs"] > 0:
                time.sleep(SETTINGS["sleep_between_runs"])

    summary = summarize(all_results)
    write_csv(all_results, Path(args.output_csv))
    Path(args.output_json).write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    print("")
    print("Drill complete.")
    print(f"- CSV: {args.output_csv}")
    print(f"- JSON: {args.output_json}")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
