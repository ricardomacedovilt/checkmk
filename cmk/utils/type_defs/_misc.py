#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import enum
import sys
from collections.abc import Container
from dataclasses import asdict, dataclass
from typing import (
    Any,
    Dict,
    Final,
    List,
    Literal,
    Mapping,
    NamedTuple,
    NewType,
    Optional,
    Sequence,
    Set,
    Tuple,
    TypedDict,
    Union,
)

HostName = str
HostAddress = str
HostgroupName = str
ServiceName = str
ServicegroupName = str
ContactgroupName = str
TimeperiodName = str

AgentTargetVersion = Union[None, str, Tuple[str, str], Tuple[str, Dict[str, str]]]

AgentRawData = NewType("AgentRawData", bytes)

RulesetName = str
RuleValue = Any  # TODO: Improve this type
RuleSpec = Dict[str, Any]  # TODO: Improve this type
Ruleset = List[RuleSpec]  # TODO: Improve this type
CheckPluginNameStr = str
ActiveCheckPluginName = str
Item = Optional[str]
Labels = Dict[str, str]
LabelSources = Dict[str, str]

TagID = str
TaggroupID = str
TaggroupIDToTagID = Mapping[TaggroupID, TagID]
TagIDToTaggroupID = Mapping[TagID, TaggroupID]
TagIDs = Set[TagID]
TagConditionNE = TypedDict(
    'TagConditionNE',
    {
        '$ne': Optional[TagID],
    },
)
TagConditionOR = TypedDict(
    'TagConditionOR',
    {
        '$or': Sequence[Optional[TagID]],
    },
)
TagConditionNOR = TypedDict(
    'TagConditionNOR',
    {
        '$nor': Sequence[Optional[TagID]],
    },
)
TagCondition = Union[Optional[TagID], TagConditionNE, TagConditionOR, TagConditionNOR]
# Here, we have data structures such as
# {'ip-v4': {'$ne': 'ip-v4'}, 'snmp_ds': {'$nor': ['no-snmp', 'snmp-v1']}, 'taggroup_02': None, 'aux_tag_01': 'aux_tag_01', 'address_family': 'ip-v4-only'}
TaggroupIDToTagCondition = Mapping[TaggroupID, TagCondition]

HostNameConditions = Union[None, Dict[str, List[Union[Dict[str, str], str]]],
                           List[Union[Dict[str, str], str]]]
ServiceNameConditions = Union[None, Dict[str, List[Union[Dict[str, str], str]]],
                              List[Union[Dict[str, str], str]]]
CheckVariables = Dict[str, Any]
Seconds = int
Timestamp = int
TimeRange = Tuple[int, int]

ServiceState = int
HostState = int
ServiceDetails = str
ServiceAdditionalDetails = str

MetricName = str
MetricTuple = Tuple[MetricName, float, Optional[float], Optional[float], Optional[float],
                    Optional[float],]

ServiceCheckResult = Tuple[ServiceState, ServiceDetails, List[MetricTuple]]

LegacyCheckParameters = Union[None, Dict, Tuple, List, str]

SetAutochecksTable = Dict[Tuple[str, Item], Tuple[ServiceName, LegacyCheckParameters, Labels,
                                                  List[HostName]]]


@dataclass
class DiscoveryResult:
    self_new: int = 0
    self_removed: int = 0
    self_kept: int = 0
    self_total: int = 0
    self_new_host_labels: int = 0
    self_total_host_labels: int = 0
    clustered_new: int = 0
    clustered_old: int = 0
    clustered_vanished: int = 0

    # None  -> No error occured
    # ""    -> Not monitored (disabled host)
    # "..." -> An error message about the failed discovery
    error_text: Optional[str] = None

    # An optional text to describe the services changed by the operation
    diff_text: Optional[str] = None


@dataclass
class AutomationDiscoveryResponse:
    results: Dict[HostName, DiscoveryResult]

    def serialize(self):
        return {
            "results": {k: asdict(v) for k, v in self.results.items()},
        }

    @classmethod
    def deserialize(cls, serialized: Dict[str, Any]) -> "AutomationDiscoveryResponse":
        return cls(results={k: DiscoveryResult(**v) for k, v in serialized["results"].items()})


UserId = NewType("UserId", str)
EventRule = Dict[str, Any]  # TODO Improve this

LATEST_SERIAL: Final[Literal["latest"]] = "latest"
# TODO(ml): The strings in ConfigSerial look like this: "0", "1", "2"...
#           We should use `int` or even better make a full-blown
#           abstraction out of that.
#           See also: a few of its "methods" are in `cmk.base.core_config`.
ConfigSerial = NewType("ConfigSerial", str)
OptionalConfigSerial = Union[ConfigSerial, Literal["latest"]]

# This def is used to keep the API-exposed object in sync with our
# implementation.
SNMPDetectBaseType = List[List[Tuple[str, str, bool]]]

# TODO: TimeperiodSpec should really be a class or at least a NamedTuple! We
# can easily transform back and forth for serialization.
TimeperiodSpec = Dict[str, Union[str, List[Tuple[str, str]]]]


class SourceType(enum.Enum):
    """Classification of management sources vs regular hosts"""
    HOST = "HOST"
    MANAGEMENT = "MANAGEMENT"


HostKey = NamedTuple("HostKey", [
    ("hostname", HostName),
    ("ipaddress", Optional[HostAddress]),
    ("source_type", SourceType),
])


# TODO: We should really parse our configuration file and use a
# class/NamedTuple, see above.
def timeperiod_spec_alias(timeperiod_spec: TimeperiodSpec, default: str = u"") -> str:
    alias = timeperiod_spec.get("alias", default)
    if isinstance(alias, str):
        return alias
    raise Exception("invalid timeperiod alias %r" % (alias,))


class EvalableFloat(float):
    """Extends the float representation for Infinities in such way that
    they can be parsed by eval"""
    def __str__(self):
        return super().__repr__()

    def __repr__(self) -> str:
        if self > sys.float_info.max:
            return '1e%d' % (sys.float_info.max_10_exp + 1)
        if self < -1 * sys.float_info.max:
            return '-1e%d' % (sys.float_info.max_10_exp + 1)
        return super().__repr__()


class _Everything(Container):
    def __contains__(self, other: object) -> bool:
        return True


EVERYTHING = _Everything()

# Symbolic representations of states in plugin output
# TODO(ml): Should probably be of type enum::int -> str
state_markers = ("", "(!)", "(!!)", "(?)")


class ExitSpec(TypedDict, total=False):
    empty_output: int
    connection: int
    timeout: int
    exception: int
    wrong_version: int
    missing_sections: int
    specific_missing_sections: List[Tuple[str, int]]
    restricted_address_mismatch: int
