#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import (
    Any,
    Dict,
    Literal,
    Iterable,
    Mapping,
    Optional,
    Sequence,
    Tuple,
    TypedDict,
    Union,
)

from cmk.utils.type_defs import Seconds

################################################################################


# Horrible ValueSpec...
class UseSNMPTrapTranslation(TypedDict, total=False):
    add_description: Literal[True]


SNMPTrapTranslation = Union[Literal[False], Tuple[Literal[True], UseSNMPTrapTranslation]]

################################################################################


class EMailActionConfig(TypedDict):
    to: str
    subject: str
    body: str


class EMailAction(TypedDict):
    id: str
    title: str
    hidden: bool
    disabled: bool
    action: Tuple[Literal['email'], EMailActionConfig]


class ScriptActionConfig(TypedDict):
    script: str


class ScriptAction(TypedDict):
    id: str
    title: str
    hidden: bool
    disabled: bool
    action: Tuple[Literal['script'], ScriptActionConfig]


Action = Union[EMailAction, ScriptAction]

################################################################################


class EventLimit(TypedDict):
    action: str
    limit: int


class EventLimits(TypedDict):
    by_host: EventLimit
    by_rule: EventLimit
    overall: EventLimit


class HostnameTranslation(TypedDict, total=False):
    case: Union[Literal['lower'], Literal['upper']]
    drop_domain: bool
    mapping: Iterable[Tuple[str, str]]
    regex: Iterable[Tuple[str, str]]


LogLevel = int

LogConfig = TypedDict(
    'LogConfig', {
        'cmk.mkeventd': LogLevel,
        'cmk.mkeventd.EventServer': LogLevel,
        'cmk.mkeventd.EventServer.snmp': LogLevel,
        'cmk.mkeventd.EventStatus': LogLevel,
        'cmk.mkeventd.StatusServer': LogLevel,
        'cmk.mkeventd.lock': LogLevel,
    })


class ReplicationBase(TypedDict):
    connect_timeout: int
    interval: int
    master: Tuple[str, int]


class Replication(ReplicationBase, total=False):
    fallback: int
    disabled: Literal['true']
    logging: Literal['true']
    takeover: int


class ContactGroups(TypedDict):
    groups: Iterable[str]
    notify: bool
    precedence: Union[Literal['host'], Literal['rule']]


class Expect(TypedDict):
    merge: Union[Literal['open'], Literal['acked'], Literal['never']]


class ServiceLevel(TypedDict):
    value: int
    precedence: Union[Literal['message'], Literal['rule']]


StatePatterns = TypedDict('StatePatterns', {
    '0': str,
    '1': str,
    '2': str,
}, total=False)

State = Union[Literal[-1], Literal[0], Literal[1], Literal[2], Literal[3],
              Tuple[Literal['text_pattern'], StatePatterns]]


# TODO: This is only a rough approximation.
class Rule(TypedDict, total=False):
    actions: Iterable[Tuple[str, str]]
    actions_in_downtime: bool
    autodelete: bool
    cancel_application: str
    cancel_priority: Tuple[int, int]
    contact_groups: ContactGroups
    expect: Expect
    id: str
    invert_matching: bool
    livetime: Tuple[Seconds, Iterable[Union[Literal['open'], Literal['ack']]]]
    match: str
    match_application: str
    match_facility: int
    match_host: str
    match_ipaddress: str
    match_ok: str
    match_priority: Tuple[int, int]
    match_site: Iterable[str]
    match_sl: Tuple[int, int]
    match_timeperiod: str
    pack: str
    set_application: str
    set_comment: str
    set_contact: str
    set_host: str
    set_text: str
    sl: ServiceLevel
    state: State


AuthenticationProtocol = Union[Literal['md5'], Literal['sha'], Literal['SHA-224'],
                               Literal['SHA-256'], Literal['SHA-384'], Literal['SHA-512']]

PrivacyProtocol = Union[Literal['DES'], Literal['AES'], Literal['3DES-EDE'], Literal['AES-192'],
                        Literal['AES-256'], Literal['AES-192-Blumenthal'],
                        Literal['AES-256-Blumenthal']]

SNMPV1V2Credentials = str
SNMPV3NoAuthNoPrivCredentials = Tuple[Literal['noAuthNoPriv'], str]
SNMPV3AuthNoPrivCredentials = Tuple[Literal['authNoPriv'], AuthenticationProtocol, str, str]
SNMPV3AuthPrivCredentials = Tuple[Literal['authPriv'], AuthenticationProtocol, str, str,
                                  PrivacyProtocol, str]
SNMPCredentials = Union[SNMPV1V2Credentials, SNMPV3NoAuthNoPrivCredentials,
                        SNMPV3AuthNoPrivCredentials, SNMPV3AuthPrivCredentials]


class SNMPCredentialBase(TypedDict):
    description: str
    credentials: SNMPCredentials


class SNMPCredential(SNMPCredentialBase, total=False):
    engine_ids: Iterable[str]


# This is what we get from the outside.
class ConfigFromWATO(TypedDict):
    actions: Sequence[Action]
    archive_mode: Union[Literal['file'], Literal['mongodb']]
    archive_orphans: bool
    debug_rules: bool
    event_limit: EventLimits
    eventsocket_queue_len: int
    history_lifetime: int
    history_rotation: Union[Literal['daily'], Literal['weekly']]
    hostname_translation: HostnameTranslation  # TODO: Mutable???
    housekeeping_interval: int
    log_level: LogConfig  # TODO: Mutable???
    log_messages: bool
    log_rulehits: bool
    mkp_rule_packs: Mapping[Any, Any]  # TODO: Move to Config (not from WATO!). TypedDict
    remote_status: Optional[Tuple[int, bool, Optional[Sequence[str]]]]
    replication: Optional[Replication]
    retention_interval: int
    rule_optimizer: bool
    rule_packs: Sequence[Dict[str, Any]]  # TODO: Mutable??? TypedDict
    rules: Iterable[Rule]
    snmp_credentials: Iterable[SNMPCredential]
    socket_queue_len: int
    statistics_interval: int
    translate_snmptraps: SNMPTrapTranslation


# After loading, we add two fields: 'action' for more efficient access to actions plus a timestamp
# used for replication.
class Config(ConfigFromWATO):
    action: Mapping[str, Action]
    last_reload: int
