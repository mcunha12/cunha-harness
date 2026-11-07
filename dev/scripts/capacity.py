#!/usr/bin/env python3
"""Quantos workers de task o /dev abre agora, pelos núcleos e pela memória livre da máquina."""
import json
import math
import os
import platform
import subprocess
import sys

RESERVED_CORES = 2  # um para o slot de build, um para o slot de QA
RESERVED_GB = 2.0  # build de produção e navegador headless do QA
GB_PER_WORKER = 0.25  # estimativa sem medição: o agente roda dentro do processo do Claude Code


def task_workers(cores, mem_free_gb):
    by_cpu = cores - RESERVED_CORES
    by_mem = math.floor((mem_free_gb - RESERVED_GB) / GB_PER_WORKER)
    workers = max(1, min(by_cpu, by_mem))
    if workers > min(by_cpu, by_mem):
        limited_by = "piso"
    else:
        limited_by = "cpu" if by_cpu <= by_mem else "memória"
    return {"workers": workers, "cores": cores, "mem_free_gb": round(mem_free_gb, 1), "limited_by": limited_by}


def _sysctl(name):
    return int(subprocess.run(["sysctl", "-n", name], capture_output=True, text=True, check=True).stdout.strip())


def mem_free_gb():
    if platform.system() == "Darwin":
        # kern.memorystatus_level é o percentual livre que o macOS usa para medir a pressão de memória
        return _sysctl("hw.memsize") * _sysctl("kern.memorystatus_level") / 100 / 2 ** 30
    with open("/proc/meminfo") as f:
        for line in f:
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) / 2 ** 20
    raise ValueError("MemAvailable ausente em /proc/meminfo")


def main():
    try:
        free = mem_free_gb()
    except (OSError, ValueError, subprocess.CalledProcessError):
        free = 0.0
    print(json.dumps(task_workers(os.cpu_count() or 1, free), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
