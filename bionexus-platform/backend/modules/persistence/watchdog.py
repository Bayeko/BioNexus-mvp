"""BioNexus Watchdog — Service health monitor.

Watches Collector and SyncEngine processes.
Auto-restarts them if they crash.
"""

import logging
import subprocess
import sys
import time

logger = logging.getLogger("persistence.watchdog")

SERVICES = [
    "bionexus-collector",
    "bionexus-sync",
]

CHECK_INTERVAL = 30


def check_service(name: str) -> bool:
    result = subprocess.run(
        ["systemctl", "is-active", name],
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() == "active"


def restart_service(name: str) -> None:
    logger.warning("Service %s is down — restarting...", name)
    subprocess.run(["systemctl", "restart", name])
    time.sleep(5)
    if check_service(name):
        logger.info("Service %s restarted successfully", name)
    else:
        logger.error("Service %s failed to restart", name)


def run_watchdog() -> None:
    logger.info("BioNexus Watchdog starting...")
    while True:
        for service in SERVICES:
            if not check_service(service):
                restart_service(service)
        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_watchdog()
