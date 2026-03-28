import psutil
import csv
import time
import os
import random

BASELINE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "data",
    "baseline.csv"
)

HEADERS = [
    "cpu",
    "ram",
    "requests_per_sec",
    "failed_logins",
    "response_time"
]


def collect_metrics():
    cpu = psutil.cpu_percent(interval=1)
    ram = psutil.virtual_memory().percent

    # Correlated synthetic workload metrics
    requests_per_sec = int(8 + (cpu / 100) * 15 + random.uniform(-2, 2))
    failed_logins = random.choices([0, 1], weights=[95, 5])[0]
    response_time = int(110 + (ram / 100) * 80 + random.uniform(-10, 10))

    return {
        "cpu": round(cpu, 2),
        "ram": round(ram, 2),
        "requests_per_sec": max(1, requests_per_sec),
        "failed_logins": failed_logins,
        "response_time": max(80, response_time)
    }


def record_baseline(samples=60, interval=2):
    os.makedirs(os.path.dirname(BASELINE_PATH), exist_ok=True)

    with open(BASELINE_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS)
        writer.writeheader()

        print(f"📡 Recording {samples} baseline samples...")
        for i in range(samples):
            metrics = collect_metrics()
            writer.writerow(metrics)
            print(f"[{i+1}/{samples}] {metrics}")
            time.sleep(interval)

    print(f"\nBaseline saved to: {BASELINE_PATH}")


if __name__ == "__main__":
    record_baseline(samples=50, interval=2)