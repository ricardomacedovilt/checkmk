#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Service status

The service status provides the service's "health" information.

A service (for example, a file system or a process) is a property of a certain host that
is monitored by Checkmk.

For a more detailed description please have a look at the
[Querying Status Data](#section/Querying-Status-Data) section.
"""
from cmk.gui import sites
from cmk.gui.plugins.openapi import fields
from cmk.gui.plugins.openapi.livestatus_helpers.queries import Query
from cmk.gui.plugins.openapi.livestatus_helpers.tables import Services
from cmk.gui.plugins.openapi.restful_objects import (
    Endpoint,
    constructors,
    response_schemas,
)
from cmk.gui.plugins.openapi.restful_objects.parameters import HOST_NAME, OPTIONAL_HOST_NAME

PARAMETERS = [{
    'sites': fields.List(
        fields.SiteField(),
        description="Restrict the query to this particular site.",
        missing=list,
    ),
    'query': fields.query_field(
        Services,
        required=False,
        example='{"op": "=", "left": "host_name", "right": "example.com"}',
    ),
    'columns': fields.column_field(
        Services,
        mandatory=[
            Services.host_name,
            Services.description,
        ],
    )
}]


@Endpoint(constructors.domain_object_collection_href('host', '{host_name}', 'services'),
          '.../collection',
          method='get',
          path_params=[HOST_NAME],
          query_params=PARAMETERS,
          tag_group='Monitoring',
          blacklist_in=['swagger-ui'],
          response_schema=response_schemas.DomainObjectCollection)
def _list_host_services(param):
    """Show the monitored services of a host

    This list is filterable by various parameters."""
    return _list_services(param)


@Endpoint(
    constructors.collection_href('service'),
    '.../collection',
    method='get',
    query_params=[OPTIONAL_HOST_NAME, *PARAMETERS],
    tag_group='Monitoring',
    response_schema=response_schemas.DomainObjectCollection,
)
def _list_all_services(param):
    """Show all monitored services

    This list is filterable by various parameters."""
    return _list_services(param)


def _list_services(param):
    live = sites.live()

    q = Query(param['columns'])

    host_name = param.get('host_name')
    if host_name is not None:
        q = q.filter(Services.host_name == host_name)

    query_expr = param.get('query')
    if query_expr:
        q = q.filter(query_expr)

    result = q.iterate(live)

    return constructors.serve_json(
        constructors.collection_object(
            domain_type='service',
            value=[
                constructors.domain_object(
                    domain_type='service',
                    title=f"{entry['description']} on {entry['host_name']}",
                    identifier=entry['description'],
                    editable=False,
                    deletable=False,
                    extensions=entry,
                ) for entry in result
            ],
        ))
