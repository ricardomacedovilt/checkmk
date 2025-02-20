#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access

import copy
import logging
import time
from collections import defaultdict

import pytest  # type: ignore[import]

from testlib.base import Scenario  # type: ignore[import]

from cmk.utils.type_defs import AgentRawData, SectionName

from cmk.snmplib.type_defs import SNMPRawData, SNMPRawDataSection

from cmk.core_helpers.agent import AgentParser, SectionMarker
from cmk.core_helpers.cache import PersistedSections, SectionStore
from cmk.core_helpers.snmp import SNMPParser
from cmk.core_helpers.type_defs import AgentRawDataSection, NO_SELECTION


class TestAgentParser:
    @pytest.fixture
    def hostname(self):
        return "testhost"

    @pytest.fixture
    def logger(self):
        return logging.getLogger("test")

    @pytest.fixture
    def scenario(self, hostname, monkeypatch):
        ts = Scenario()
        ts.add_host(hostname)
        ts.apply(monkeypatch)

    @pytest.fixture
    def store_path(self, tmp_path):
        return tmp_path / "store"

    @pytest.fixture
    def store(self, store_path, logger):
        return SectionStore[AgentRawDataSection](store_path, logger=logger)

    @pytest.fixture
    def parser(self, hostname, store, logger):
        return AgentParser(
            hostname,
            store,
            check_interval=0,
            keep_outdated=True,
            translation={},
            encoding_fallback="ascii",
            simulation=False,
            logger=logger,
        )

    @pytest.mark.usefixtures("scenario")
    def test_missing_host_header(self, parser):
        raw_data = AgentRawData(b"\n".join((
            b"hey!",
            b"a header",
            b"is missing",
        )))

        ahs = parser.parse(raw_data, selection=NO_SELECTION)
        assert ahs.sections == {}
        assert ahs.cache_info == {}
        assert ahs.piggybacked_raw_data == {}

    @pytest.mark.usefixtures("scenario")
    def test_piggy_name_as_hostname_is_not_piggybacked(self, parser, hostname):
        raw_data = AgentRawData(b"\n".join((
            f"<<<<{hostname}>>>>".encode("ascii"),
            b"line0",
            b"line1",
            b"line2",
        )))

        ahs = parser.parse(raw_data, selection=NO_SELECTION)
        assert ahs.sections == {}
        assert ahs.cache_info == {}
        assert ahs.piggybacked_raw_data == {}

    @pytest.mark.usefixtures("scenario")
    def test_no_section_header_after_piggyback(self, parser):
        raw_data = AgentRawData(b"\n".join((
            b"<<<<piggy>>>>",
            b"line0",
            b"line1",
            b"line2",
        )))

        ahs = parser.parse(raw_data, selection=NO_SELECTION)
        assert ahs.sections == {}
        assert ahs.cache_info == {}
        assert ahs.piggybacked_raw_data == {'piggy': []}

    @pytest.mark.usefixtures("scenario")
    def test_raw_section_populates_sections(self, parser):
        raw_data = AgentRawData(b"\n".join((
            b"<<<a_section>>>",
            b"first line",
            b"second line",
            b"<<<>>>",
            b"<<<another_section>>>",
            b"first line",
            b"second line",
            b"<<<>>>",
        )))

        ahs = parser.parse(raw_data, selection=NO_SELECTION)

        assert ahs.sections == {
            SectionName("a_section"): [["first", "line"], ["second", "line"]],
            SectionName("another_section"): [["first", "line"], ["second", "line"]],
        }
        assert ahs.cache_info == {}
        assert ahs.piggybacked_raw_data == {}

    @pytest.mark.usefixtures("scenario")
    def test_merge_split_raw_sections(self, parser):
        raw_data = AgentRawData(b"\n".join((
            b"<<<a_section>>>",
            b"first line",
            b"second line",
            b"<<<>>>",
            b"<<<another_section>>>",
            b"a line",
            b"b line",
            b"<<<a_section>>>",
            b"third line",
            b"forth line",
            b"<<<>>>",
            b"<<<another_section>>>",
            b"c line",
            b"d line",
            b"<<<>>>",
            b"<<<a_section:sep(124)>>>",
            b"fifth|line",
            b"sixth|line",
            b"<<<>>>",
        )))

        ahs = parser.parse(raw_data, selection=NO_SELECTION)
        assert ahs.sections == {
            SectionName("a_section"): [
                ["first", "line"],
                ["second", "line"],
                ["third", "line"],
                ["forth", "line"],
                ["fifth", "line"],
                ["sixth", "line"],
            ],
            SectionName("another_section"): [
                ["a", "line"],
                ["b", "line"],
                ["c", "line"],
                ["d", "line"],
            ],
        }
        assert ahs.cache_info == {}
        assert ahs.piggybacked_raw_data == {}

    @pytest.mark.usefixtures("scenario")
    def test_piggyback_populates_piggyback_raw_data(self, parser, monkeypatch):
        time_time = 1000
        monkeypatch.setattr(time, "time", lambda: time_time)
        monkeypatch.setattr(parser, "check_interval", 10)

        raw_data = AgentRawData(b"\n".join((
            b"<<<<piggyback header>>>>",  # <- space is OK
            b"<<<section>>>",
            b"first line",
            b"second line",
            b"<<<<>>>>",  # <- omitting this line makes no difference
            b"<<<<piggyback_other>>>>",
            b"<<<other_section>>>",
            b"first line",
            b"second line",
            b"<<<other_other_section>>>",
            b"third line",
            b"forth line",
            b"<<<<>>>>",
            b"<<<<../b:l*a../>>>>",
            b"<<<section>>>",
            b"first line",
            b"<<<</b_l-u/>>>>",
            b"<<<section>>>",
            b"first line",
        )))

        ahs = parser.parse(raw_data, selection=NO_SELECTION)

        assert ahs.sections == {}
        assert ahs.cache_info == {}
        assert ahs.piggybacked_raw_data == {
            "piggyback_header": [
                b"<<<section:cached(1000,900)>>>",
                b"first line",
                b"second line",
            ],
            "piggyback_other": [
                b"<<<other_section:cached(1000,900)>>>",
                b"first line",
                b"second line",
                b"<<<other_other_section:cached(1000,900)>>>",
                b"third line",
                b"forth line",
            ],
            ".._b_l_a.._": [
                b"<<<section:cached(1000,900)>>>",
                b"first line",
            ],
            "_b_l-u_": [
                b"<<<section:cached(1000,900)>>>",
                b"first line",
            ],
        }

    @pytest.mark.usefixtures("scenario")
    def test_merge_split_piggyback_sections(self, parser, monkeypatch):
        time_time = 1000
        monkeypatch.setattr(time, "time", lambda: time_time)
        monkeypatch.setattr(parser, "check_interval", 10)

        raw_data = AgentRawData(b"\n".join((
            b"<<<<piggy>>>>",
            b"<<<a_section>>>",
            b"first line",
            b"second line",
            b"<<<another_section>>>",
            b"a line",
            b"b line",
            b"<<<<>>>>",
            b"<<<<piggy>>>>",
            b"<<<a_section>>>",
            b"third line",
            b"forth line",
            b"<<<another_section>>>",
            b"c line",
            b"d line",
            b"<<<<>>>>",
        )))

        ahs = parser.parse(raw_data, selection=NO_SELECTION)
        assert ahs.sections == {}
        assert ahs.cache_info == {}
        assert ahs.piggybacked_raw_data == {
            "piggy": [
                b"<<<a_section:cached(1000,900)>>>",
                b"first line",
                b"second line",
                b"third line",
                b"forth line",
                b"<<<another_section:cached(1000,900)>>>",
                b"a line",
                b"b line",
                b"c line",
                b"d line",
            ],
        }

    @pytest.mark.usefixtures("scenario")
    def test_persist_option_populates_cache_info(self, parser, mocker, monkeypatch):
        time_time = 1000
        time_delta = 50
        monkeypatch.setattr(time, "time", lambda: time_time)

        raw_data = AgentRawData(b"\n".join((
            b"<<<section:persist(%i)>>>" % (time_time + time_delta),
            b"first line",
            b"second line",
        )))

        ahs = parser.parse(raw_data, selection=NO_SELECTION)

        assert ahs.sections == {SectionName("section"): [["first", "line"], ["second", "line"]]}
        assert ahs.cache_info == {SectionName("section"): (time_time, time_delta)}
        assert ahs.piggybacked_raw_data == {}

    @pytest.mark.usefixtures("scenario")
    def test_persist_option_and_persisted_sections(self, parser, mocker, monkeypatch):
        time_time = 1000
        time_delta = 50
        monkeypatch.setattr(time, "time", lambda: time_time)
        monkeypatch.setattr(
            SectionStore,
            "load",
            lambda self: PersistedSections[AgentRawDataSection]({
                SectionName("persisted"): (42, 69, [["content"]]),
            }),
        )
        # Patch IO:
        monkeypatch.setattr(SectionStore, "store", lambda self, sections: None)

        raw_data = AgentRawData(b"\n".join((
            b"<<<section:persist(%i)>>>" % (time_time + time_delta),
            b"first line",
            b"second line",
        )))

        ahs = parser.parse(raw_data, selection=NO_SELECTION)

        assert ahs.sections == {
            SectionName("section"): [["first", "line"], ["second", "line"]],
            SectionName("persisted"): [["content"]],
        }
        assert ahs.cache_info == {
            SectionName("section"): (time_time, time_delta),
            SectionName("persisted"): (42, 27),
        }
        assert ahs.piggybacked_raw_data == {}

    def test_section_filtering(self, parser, monkeypatch):
        monkeypatch.setattr(time, "time", lambda: 1000)
        raw_data = AgentRawData(b"\n".join((
            b"<<<<piggyback_header>>>>",
            b"<<<deselected>>>",
            b"1st line",
            b"2nd line",
            b"<<<selected>>>",
            b"3rd line",
            b"4th line",
            b"<<<<>>>>",
            b"<<<deselected>>>",
            b"5th line",
            b"6th line",
            b"<<<selected>>>",
            b"7th line",
            b"8th line",
        )))

        ahs = parser.parse(raw_data, selection={SectionName("selected")})

        assert ahs.sections == {
            SectionName("selected"): [["7th", "line"], ["8th", "line"]],
        }
        assert ahs.cache_info == {}
        assert ahs.piggybacked_raw_data == {
            "piggyback_header": [
                b"<<<selected:cached(1000,0)>>>",
                b"3rd line",
                b"4th line",
            ]
        }


class TestSectionMarker:
    def test_options_serialize_options(self):
        section_header = SectionMarker.from_headerline(b"<<<" + b":".join((
            b"section",
            b"cached(1,2)",
            b"encoding(ascii)",
            b"nostrip()",
            b"persist(42)",
            b"sep(124)",
        )) + b">>>")
        assert section_header == SectionMarker.from_headerline(str(section_header).encode("ascii"))

    def test_options_deserialize_defaults(self):
        section_header = SectionMarker.from_headerline(b"<<<section>>>")
        other_header = SectionMarker.from_headerline(str(section_header).encode("ascii"))
        assert section_header == other_header
        assert str(section_header) == str(other_header)

    @pytest.mark.parametrize(
        "headerline, section_name, section_options",
        [
            ("norris", SectionName("norris"), {}),
            ("norris:chuck", SectionName("norris"), {"chuck": None}),
            (
                "my_section:sep(0):cached(23,42)",
                SectionName("my_section"),
                {"sep": "0", "cached": "23,42"},
            ),
            ("my.section:sep(0):cached(23,42)", None, {}),  # invalid section name
            ("", None, {}),  # invalid section name
        ],
    )  # yapf: disable
    def test_options_from_headerline(self, headerline, section_name, section_options):
        try:
            SectionMarker.from_headerline(
                f"<<<{headerline}>>>".encode("ascii")) == (  # type: ignore[comparison-overlap]
                    section_name,
                    section_options,
                )
        except ValueError:
            assert section_name is None

    def test_options_decode_values(self):
        section_header = SectionMarker.from_headerline(b"<<<" + b":".join((
            b"name",
            b"cached(1,2)",
            b"encoding(ascii)",
            b"nostrip()",
            b"persist(42)",
            b"sep(124)",
        )) + b">>>")
        assert section_header.name == SectionName("name")
        assert section_header.cached == (1, 2)
        assert section_header.encoding == "ascii"
        assert section_header.nostrip is True
        assert section_header.persist == 42
        assert section_header.separator == "|"

    def test_options_decode_defaults(self):
        section_header = SectionMarker.from_headerline(b"<<<name>>>")
        assert section_header.name == SectionName("name")
        assert section_header.cached is None
        assert section_header.encoding == "utf-8"
        assert section_header.nostrip is False
        assert section_header.persist is None
        assert section_header.separator is None


class TestSNMPParser:
    @pytest.fixture
    def hostname(self):
        return "hostname"

    @pytest.fixture(autouse=True)
    def scenario_fixture(self, hostname, monkeypatch):
        Scenario().add_host(hostname).apply(monkeypatch)

    @pytest.fixture
    def parser(self, hostname):
        return SNMPParser(
            hostname,
            SectionStore(
                "/tmp/store",
                logger=logging.Logger("test"),
            ),
            check_intervals={},
            keep_outdated=True,
            logger=logging.Logger("test"),
        )

    def test_empty_raw_data(self, parser):
        raw_data: SNMPRawData = {}

        host_sections = parser.parse(raw_data, selection=NO_SELECTION)
        assert host_sections.sections == {}
        assert host_sections.cache_info == {}
        assert not host_sections.piggybacked_raw_data

    @pytest.fixture
    def sections(self):
        # See also the tests to HostSections.
        section_a = SectionName("section_a")
        content_a = [["first", "line"], ["second", "line"]]
        section_b = SectionName("section_b")
        content_b = [["third", "line"], ["forth", "line"]]
        return {section_a: content_a, section_b: content_b}

    def test_no_cache(self, parser, sections):
        host_sections = parser.parse(sections, selection=NO_SELECTION)
        assert host_sections.sections == sections
        assert host_sections.cache_info == {}
        assert not host_sections.piggybacked_raw_data

    def test_with_persisted_sections(self, parser, sections, monkeypatch):
        monkeypatch.setattr(time, "time", lambda: 1000)
        monkeypatch.setattr(parser, "check_intervals", defaultdict(lambda: 33))
        monkeypatch.setattr(
            SectionStore, "load", lambda self: PersistedSections[AgentRawDataSection]({
                SectionName("persisted"): (42, 69, [["content"]]),
            }))
        # Patch IO:
        monkeypatch.setattr(SectionStore, "store", lambda self, sections: None)

        raw_data = sections

        ahs = parser.parse(raw_data, selection=NO_SELECTION)
        all_sections = sections.copy()
        all_sections[SectionName("persisted")] = [["content"]]
        assert ahs.sections == all_sections
        assert ahs.cache_info == {SectionName("persisted"): (42, 27)}
        assert ahs.piggybacked_raw_data == {}


class MockStore(SectionStore):
    # pylint: disable=super-init-not-called, arguments-differ
    def __init__(self, data):
        self._data = data

    def store(self, data):
        self._data = copy.copy(data)

    def load(self):
        return copy.copy(self._data)


class TestAgentPersistentSectionHandling:
    def test_update_with_empty_store_and_persisted(self):
        section_store = MockStore({})
        raw_data = AgentRawData(b"")
        parser = AgentParser(
            "testhost",
            section_store,
            check_interval=0,
            keep_outdated=True,
            translation={},
            encoding_fallback="ascii",
            simulation=False,
            logger=logging.getLogger("test"),
        )

        ahs = parser.parse(raw_data, selection=NO_SELECTION)
        assert ahs.sections == {}
        assert ahs.cache_info == {}
        assert ahs.piggybacked_raw_data == {}
        assert section_store.load() == {}

    def test_update_with_empty_persisted(self):
        section_store = MockStore(PersistedSections[AgentRawDataSection]({
            SectionName("stored"): (0, 0, []),
        }))
        raw_data = AgentRawData(b"")
        parser = AgentParser(
            "testhost",
            section_store,
            check_interval=0,
            keep_outdated=True,
            translation={},
            encoding_fallback="ascii",
            simulation=False,
            logger=logging.getLogger("test"),
        )

        ahs = parser.parse(raw_data, selection=NO_SELECTION)
        assert ahs.sections == {SectionName("stored"): []}
        assert ahs.cache_info == {SectionName("stored"): (0, 0)}
        assert ahs.piggybacked_raw_data == {}
        assert section_store.load() == PersistedSections[AgentRawDataSection]({
            SectionName("stored"): (0, 0, []),
        })

    def test_update_with_empty_store(self):
        raw_data = AgentRawData(b"<<<fresh>>>")
        section_store = MockStore({})
        parser = AgentParser(
            "testhost",
            section_store,
            check_interval=0,
            keep_outdated=True,
            translation={},
            encoding_fallback="ascii",
            simulation=False,
            logger=logging.getLogger("test"),
        )

        ahs = parser.parse(raw_data, selection=NO_SELECTION)
        assert ahs.sections == {SectionName("fresh"): []}
        assert ahs.cache_info == {}
        assert ahs.piggybacked_raw_data == {}
        assert section_store.load() == {}

    def test_update_with_persisted_and_store(self):
        section_store = MockStore(PersistedSections[AgentRawDataSection]({
            SectionName("stored"): (0, 0, []),
        }))
        raw_data = AgentRawData(b"<<<fresh>>>")
        parser = AgentParser(
            "testhost",
            section_store,
            check_interval=0,
            keep_outdated=True,
            translation={},
            encoding_fallback="ascii",
            simulation=False,
            logger=logging.getLogger("test"),
        )

        ahs = parser.parse(raw_data, selection=NO_SELECTION)
        assert ahs.sections == {
            SectionName("fresh"): [],
            SectionName("stored"): [],
        }
        assert ahs.cache_info == {SectionName("stored"): (0, 0)}
        assert ahs.piggybacked_raw_data == {}
        assert section_store.load() == PersistedSections[AgentRawDataSection]({
            SectionName("stored"): (0, 0, []),
        })

    def test_update_store_with_newest(self):
        section_store = MockStore(PersistedSections[AgentRawDataSection]({
            SectionName("section"): (0, 0, [["oldest"]]),
        }))
        raw_data = AgentRawData(b"<<<section>>>\nnewest")
        parser = AgentParser(
            "testhost",
            section_store,
            check_interval=0,
            keep_outdated=True,
            translation={},
            encoding_fallback="ascii",
            simulation=False,
            logger=logging.getLogger("test"),
        )

        ahs = parser.parse(raw_data, selection=NO_SELECTION)
        assert ahs.sections == {SectionName("section"): [["newest"]]}
        assert ahs.cache_info == {}
        assert ahs.piggybacked_raw_data == {}
        assert section_store.load() == PersistedSections[AgentRawDataSection]({
            SectionName("section"): (0, 0, [["oldest"]]),
        })

    # I cannot trigger the `!keep_outdated` feature.  It seems
    # broken:  It is triggered on data that just arrived and can
    # therefore never be outdated.
    def test_keep_outdated_is_noop(self, monkeypatch):
        monkeypatch.setattr(time, "time", lambda: 1000)

        raw_data = AgentRawData(b"<<<section:persist(0)>>>")
        section_store = MockStore(PersistedSections[AgentRawDataSection]({
            SectionName("section"): (500, 100, []),
        }))
        parser = AgentParser(
            "testhost",
            section_store,
            check_interval=0,
            keep_outdated=False,
            translation={},
            encoding_fallback="ascii",
            simulation=False,
            logger=logging.getLogger("test"),
        )

        ahs = parser.parse(raw_data, selection=NO_SELECTION)
        assert ahs.sections == {SectionName("section"): []}
        assert ahs.cache_info == {SectionName("section"): (1000, -1000)}
        assert ahs.piggybacked_raw_data == {}
        assert section_store.load() == PersistedSections[AgentRawDataSection]({
            SectionName("section"): (1000, 0, []),
        })


class TestSNMPPersistedSectionHandling:
    def test_update_with_empty_store_and_persisted(self):
        section_store = MockStore({})
        raw_data: SNMPRawData = {}
        parser = SNMPParser(
            "testhost",
            section_store,
            check_intervals={},
            keep_outdated=True,
            logger=logging.getLogger("test"),
        )

        shs = parser.parse(raw_data, selection=NO_SELECTION)
        assert shs.sections == {}
        assert shs.cache_info == {}
        assert shs.piggybacked_raw_data == {}
        assert section_store.load() == {}

    def test_update_with_empty_persisted(self):
        section_store = MockStore({SectionName("stored"): (0, 0, [["old"]])})
        raw_data: SNMPRawData = {}
        parser = SNMPParser(
            "testhost",
            section_store,
            check_intervals={},
            keep_outdated=True,
            logger=logging.getLogger("test"),
        )

        shs = parser.parse(raw_data, selection=NO_SELECTION)
        assert shs.sections == {SectionName("stored"): [["old"]]}
        assert shs.cache_info == {SectionName("stored"): (0, 0)}
        assert shs.piggybacked_raw_data == {}
        assert section_store.load() == {
            SectionName("stored"): (0, 0, [["old"]]),
        }

    def test_update_with_empty_store(self):
        section_store = MockStore({})
        _new: SNMPRawDataSection = [["new"]]  # For the type checker only
        raw_data: SNMPRawData = {SectionName("fresh"): _new}
        parser = SNMPParser(
            "testhost",
            section_store,
            check_intervals={},
            keep_outdated=True,
            logger=logging.getLogger("test"),
        )

        shs = parser.parse(raw_data, selection=NO_SELECTION)
        assert shs.sections == {SectionName("fresh"): [["new"]]}
        assert shs.cache_info == {}
        assert shs.piggybacked_raw_data == {}
        assert section_store.load() == {}

    def test_update_with_persisted_and_store(self):
        section_store = MockStore({SectionName("stored"): (0, 0, [["old"]])})
        _new: SNMPRawDataSection = [["new"]]  # For the type checker only
        raw_data: SNMPRawData = {SectionName("fresh"): _new}
        parser = SNMPParser(
            "testhost",
            section_store,
            check_intervals={},
            keep_outdated=True,
            logger=logging.getLogger("test"),
        )

        shs = parser.parse(raw_data, selection=NO_SELECTION)
        assert shs.sections == {
            SectionName("stored"): [["old"]],
            SectionName("fresh"): [["new"]],
        }
        assert shs.cache_info == {SectionName("stored"): (0, 0)}
        assert shs.piggybacked_raw_data == {}
        assert section_store.load() == {
            SectionName("stored"): (0, 0, [["old"]]),
        }

    def test_update_store_with_newest_BORKED(self):
        section_store = MockStore({SectionName("section"): (0, 0, [["old"]])})
        _new: SNMPRawDataSection = [["new"]]  # For the type checker only
        raw_data: SNMPRawData = {SectionName("section"): _new}
        parser = SNMPParser(
            "testhost",
            section_store,
            check_intervals={},
            keep_outdated=True,
            logger=logging.getLogger("test"),
        )

        shs = parser.parse(raw_data, selection=NO_SELECTION)
        assert shs.sections == {SectionName("section"): [["new"]]}
        assert shs.cache_info == {}
        assert shs.piggybacked_raw_data == {}
        assert section_store.load() == {
            SectionName("section"): (0, 0, [["old"]]),
        }

    def test_keep_outdated_is_noop(self, monkeypatch):
        monkeypatch.setattr(time, "time", lambda: 1000)

        section_store = MockStore({SectionName("section"): (0, 0, [["old"]])})
        _new: SNMPRawDataSection = [["new"]]  # For the type checker only
        raw_data: SNMPRawData = {SectionName("section"): _new}
        parser = SNMPParser(
            "testhost",
            section_store,
            check_intervals={},
            keep_outdated=False,
            logger=logging.getLogger("test"),
        )
        shs = parser.parse(raw_data, selection=NO_SELECTION)
        assert shs.sections == {SectionName("section"): [["new"]]}
        assert shs.cache_info == {}
        assert shs.piggybacked_raw_data == {}
        assert section_store.load() == {
            SectionName("section"): (0, 0, [["old"]]),
        }
