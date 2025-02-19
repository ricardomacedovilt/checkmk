#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import State, Result, Service

from cmk.base.plugins.agent_based.fuse_env_alerts import (
    discovery_fuse_env_alerts,
    check_fuse_env_alerts
)

pytestmark = pytest.mark.checks

PARSED = [
    {
        "fuse_id": "378ae807-48f8-44b4-9da4-159413b17157",
        "name": "PRODUCTION",
        "type": "",
        "component_type": "System Object Volume",
        "errors": 10,
        "warnings": 2,
        "link": "link_PRODUCTION_SOV"
    },
    {
        "fuse_id": "378ae807-48f8-44b4-9da4-159413b17157",
        "name": "PRODUCTION",
        "type": "",
        "component_type": "Agents",
        "errors": 0,
        "warnings": 0,
        "link": ""
    }
]


@pytest.mark.parametrize('params,result', [
    (
        PARSED,
        [
            Service(
                item="PRODUCTION - System Object Volume",
                parameters={
                    "fuse_id":"378ae807-48f8-44b4-9da4-159413b17157",
                    "component_type":"System Object Volume"
                }
            ),
            Service(
                item="PRODUCTION - Agents",
                parameters={
                    "fuse_id":"378ae807-48f8-44b4-9da4-159413b17157",
                    "component_type":"Agents"
                }
            )
        ]
    )
])
def test_discovery_fuse_env_alerts(params, result):
    service = discovery_fuse_env_alerts(params)
    assert list(service) == result


@pytest.mark.parametrize('params,result', [
    (
        {
            "fuse_id":"378ae807-48f8-44b4-9da4-159413b17157",
            "component_type":"System Object Volume"
        },
        [
            Result(
                state=State.CRIT,
                summary="Errors: 10 | Warnings: 2 | <a href=\"link_PRODUCTION_SOV\" target=\"_blank\">click here for more info</a>"
            )
        ]
    ),
    (
        {
            "fuse_id":"378ae807-48f8-44b4-9da4-159413b17157",
            "component_type":"Agents"
        },
        [
            Result(
                state=State.OK,
                summary="Errors: 0 | Warnings: 0"
            )
        ]
    )
])
def test_check_fuse_env_alerts(params, result):
    assert list(check_fuse_env_alerts("", params, PARSED)) == result
