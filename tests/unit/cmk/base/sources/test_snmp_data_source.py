#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access

import pytest  # type: ignore[import]

from testlib.base import Scenario  # type: ignore[import]

from cmk.utils.exceptions import MKIPAddressLookupError
from cmk.utils.type_defs import CheckPluginName, ParsedSectionName, result, SourceType

from cmk.core_helpers.type_defs import Mode, NO_SELECTION

import cmk.base.config as config
import cmk.base.ip_lookup as ip_lookup
from cmk.base.api.agent_based.checking_classes import CheckPlugin
from cmk.base.sources.agent import AgentHostSections
from cmk.base.sources.snmp import SNMPSource


@pytest.fixture(name="mode", params=Mode)
def mode_fixture(request):
    return request.param


@pytest.fixture(name="hostname")
def hostname_fixture():
    return "hostname"


@pytest.fixture(name="ipaddress")
def ipaddress_fixture():
    return "1.2.3.4"


@pytest.fixture(name="scenario")
def scenario_fixture(hostname, monkeypatch):
    Scenario().add_host(hostname).apply(monkeypatch)


@pytest.fixture(name="source")
def source_fixture(scenario, hostname, ipaddress):
    return SNMPSource.snmp(
        hostname,
        ipaddress,
        selected_sections=NO_SELECTION,
        on_scan_error="raise",
        force_cache_refresh=False,
    )


def test_snmp_ipaddress_from_mgmt_board_unresolvable(hostname, monkeypatch):
    def fake_lookup_ip_address(*_a, **_kw):
        raise MKIPAddressLookupError("Failed to ...")

    Scenario().add_host(hostname).apply(monkeypatch)
    monkeypatch.setattr(ip_lookup, "lookup_ip_address", fake_lookup_ip_address)
    monkeypatch.setattr(config, "host_attributes", {
        "hostname": {
            "management_address": "lolo"
        },
    })
    host_config = config.get_config_cache().get_host_config(hostname)
    assert config.lookup_mgmt_board_ip_address(host_config) is None


def test_attribute_defaults(source, hostname, ipaddress, monkeypatch):
    assert source.hostname == hostname
    assert source.ipaddress == ipaddress
    assert source.id == "snmp"
    assert source._on_snmp_scan_error == "raise"


def test_description_with_ipaddress(source, monkeypatch):
    default = "SNMP (Community: 'public', Bulk walk: no, Port: 161, Backend: Classic)"
    assert source.description == default


class TestSNMPSource_SNMP:
    def test_attribute_defaults(self, monkeypatch):
        hostname = "testhost"
        ipaddress = "1.2.3.4"

        Scenario().add_host(hostname).apply(monkeypatch)

        source = SNMPSource.snmp(
            hostname,
            ipaddress,
            selected_sections=NO_SELECTION,
            on_scan_error="raise",
            force_cache_refresh=False,
        )
        assert source.description == (
            "SNMP (Community: 'public', Bulk walk: no, Port: 161, Backend: Classic)")


class TestSNMPSource_MGMT:
    def test_attribute_defaults(self, monkeypatch):
        hostname = "testhost"
        ipaddress = "1.2.3.4"

        ts = Scenario()
        ts.add_host(hostname)
        ts.set_option("management_protocol", {hostname: "snmp"})
        ts.set_option(
            "host_attributes",
            {
                hostname: {
                    "management_address": ipaddress
                },
            },
        )
        ts.apply(monkeypatch)

        source = SNMPSource.management_board(
            hostname,
            ipaddress,
            force_cache_refresh=False,
            selected_sections=NO_SELECTION,
            on_scan_error="raise",
        )
        assert source.description == (
            "Management board - SNMP "
            "(Community: 'public', Bulk walk: no, Port: 161, Backend: Classic)")


class TestSNMPSummaryResult:
    @pytest.fixture
    def hostname(self):
        return "testhost"

    @pytest.fixture
    def scenario(self, hostname, monkeypatch):
        ts = Scenario()
        ts.add_host(hostname)
        ts.apply(monkeypatch)
        return ts

    @pytest.fixture
    def source(self, hostname):
        return SNMPSource(
            hostname,
            "1.2.3.4",
            force_cache_refresh=False,
            selected_sections=NO_SELECTION,
            source_type=SourceType.HOST,
            id_="snmp_id",
            title="snmp title",
            on_scan_error="raise",
        )

    @pytest.mark.usefixtures("scenario")
    def test_defaults(self, source, mode):
        assert source.summarize(result.OK(AgentHostSections()), mode=mode) == (0, "Success")

    @pytest.mark.usefixtures("scenario")
    def test_with_exception(self, source, mode):
        assert source.summarize(result.Error(Exception()), mode=mode) == (3, "(?)")


@pytest.fixture(name="check_plugin")
def fixture_check_plugin(monkeypatch):
    return CheckPlugin(
        CheckPluginName("unit_test_check_plugin"),
        [ParsedSectionName("norris")],
        "Unit Test",
        None,  # type: ignore[arg-type]  # irrelevant for test
        None,  # type: ignore[arg-type]  # irrelevant for test
        None,  # type: ignore[arg-type]  # irrelevant for test
        None,  # type: ignore[arg-type]  # irrelevant for test
        None,  # type: ignore[arg-type]  # irrelevant for test
        None,  # type: ignore[arg-type]  # irrelevant for test
        None,  # type: ignore[arg-type]  # irrelevant for test
        None,  # type: ignore[arg-type]  # irrelevant for test
        None,  # type: ignore[arg-type]  # irrelevant for test
    )
