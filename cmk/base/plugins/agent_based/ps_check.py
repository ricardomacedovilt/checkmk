#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Dict, List, Mapping, Optional, Tuple
from .agent_based_api.v1.type_defs import CheckResult

from .agent_based_api.v1 import register
from .utils import cpu
from .utils import memory
from .utils import ps


def check_ps(
    item: str,
    params: Mapping[str, Any],
    section_ps: Optional[ps.Section],
    section_mem: Optional[memory.SectionMem],
    section_mem_used: Optional[memory.SectionMem],
    section_cpu: Optional[cpu.Section],
) -> CheckResult:
    if not section_ps:
        return

    cpu_cores, lines = section_ps
    if section_cpu:
        cpu_cores = section_cpu.num_cpus or cpu_cores

    total_ram = (section_mem or section_mem_used or {}).get("MemTotal")

    yield from ps.check_ps_common(
        label="Processes",
        item=item,
        params=params,
        # no cluster in this function -> Node name is None:
        process_lines=[(None, ps_info, cmd_line) for ps_info, cmd_line in lines],
        cpu_cores=cpu_cores,
        total_ram=total_ram,
    )


def cluster_check_ps(
        item: str,
        params: Mapping[str, Any],
        section_ps: Dict[str, ps.Section],
        section_mem: Dict[str, memory.SectionMem],  # unused
        section_mem_used: Dict[str, memory.SectionMem],  # unused
        section_cpu: Dict[str, cpu.Section],  # unused
) -> CheckResult:
    # introduce node name
    process_lines: List[Tuple[Optional[str], ps.PsInfo, List[str]]] = [
        (node_name, ps_info, cmd_line)
        for node_name, (_cpu_cores, node_lines) in section_ps.items()
        for (ps_info, cmd_line) in node_lines
    ]

    core_counts = set(cpu_cores for (cpu_cores, _node_lines) in section_ps.values())
    if len(core_counts) == 1:
        cpu_cores = core_counts.pop()
    else:
        # inconsistent cpu counts, what can we do? There's no 'None' option.
        cpu_cores = 1

    yield from ps.check_ps_common(
        label="Processes",
        item=item,
        params=params,
        process_lines=process_lines,
        cpu_cores=cpu_cores,
        total_ram=None,
    )


register.check_plugin(
    name="ps",
    service_name="Process %s",
    sections=["ps", "mem", "mem_used", "cpu"],
    discovery_function=ps.discover_ps,
    discovery_ruleset_name="inventory_processes_rules",
    discovery_default_parameters={},
    discovery_ruleset_type=register.RuleSetType.ALL,
    check_function=check_ps,
    check_default_parameters={
        "levels": (1, 1, 99999, 99999),
    },
    check_ruleset_name="ps",
    cluster_check_function=cluster_check_ps,
)
