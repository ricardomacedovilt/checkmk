#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from livestatus import lqencode
from cmk.utils.render import date_and_time
from cmk.gui.type_defs import HTTPVariables
import cmk.gui.sites as sites
from cmk.gui.i18n import _
from cmk.gui.globals import html, request
from cmk.gui.visuals import get_filter_headers
from cmk.gui.pages import page_registry, AjaxPage
from cmk.gui.plugins.dashboard import dashlet_registry, ABCFigureDashlet
from cmk.gui.plugins.dashboard.utils import dashlet_http_variables
from cmk.gui.plugins.dashboard.bar_chart_dashlet import BarBarChartDataGenerator
from cmk.gui.exceptions import MKTimeout, MKGeneralException
from cmk.gui.valuespec import Dictionary, DropdownChoice, CascadingDropdown
from cmk.gui.utils.urls import makeuri_contextless


#   .--Base Classes--------------------------------------------------------.
#   |       ____                    ____ _                                 |
#   |      | __ )  __ _ ___  ___   / ___| | __ _ ___ ___  ___  ___         |
#   |      |  _ \ / _` / __|/ _ \ | |   | |/ _` / __/ __|/ _ \/ __|        |
#   |      | |_) | (_| \__ \  __/ | |___| | (_| \__ \__ \  __/\__ \        |
#   |      |____/ \__,_|___/\___|  \____|_|\__,_|___/___/\___||___/        |
#   |                                                                      |
#   +----------------------------------------------------------------------+
class ABCEventBarChartDataGenerator(BarBarChartDataGenerator):
    """ Generates the data for host/service alert/notifications bar charts """
    @classmethod
    def log_type(cls):
        raise NotImplementedError()

    @classmethod
    def log_class(cls):
        raise NotImplementedError()

    @classmethod
    def filter_infos(cls):
        return ["host", "service"]

    def vs_parameters(self):
        # Specifies the properties for this data generator
        return Dictionary(
            title=_("Properties"),
            render="form",
            optional_keys=[],
            elements=[
                ("render_mode",
                 CascadingDropdown(choices=[
                     ("bar_chart", _("Bar chart"),
                      Dictionary(
                          elements=self.bar_chart_vs_components(),
                          optional_keys=[],
                      )),
                 ])),
                ("log_target",
                 DropdownChoice(
                     title=_("Host or service %ss" % self.log_type()),
                     choices=[
                         ("both", _("Show %ss for hosts and services" % self.log_type())),
                         ("host", _("Show %ss for hosts" % self.log_type())),
                         ("service", _("Show %ss for services" % self.log_type())),
                     ],
                     default_value="both",
                 )),
            ],
        )

    @classmethod
    def generate_response_data(cls, properties, context, settings):
        """Toggle between the data of the different render modes"""
        # TODO: Would be better to have independent data generators for the various render modes,
        # but that is not possible with the current mechanic. Once we spread the toggling of render
        # modes, we should restructure this.
        if properties["render_mode"][0] == "bar_chart":
            return super().generate_response_data(properties, context, settings)
        raise NotImplementedError()

    # TODO: Possible performance optimization: We only need to count events. Especially in case of
    # render_mode != "bar_char" we only need a single number. This could improve the performance of
    # the dashlets signifcantly.
    @classmethod
    def _get_data(cls, properties, context):
        mode_properties = properties["render_mode"][1]
        time_range = cls._int_time_range_from_rangespec(mode_properties["time_range"])
        filter_headers, only_sites = get_filter_headers("log", cls.filter_infos(), context)

        if properties["log_target"] != "both":
            object_type_filter = ("Filter: log_type ~ %s .*\n" %
                                  lqencode(properties["log_target"].upper()))
        else:
            object_type_filter = ""

        query = ("GET log\n"
                 "Columns: log_state host_name service_description log_type log_time\n"
                 "Filter: class = %d\n"
                 "Filter: log_time >= %f\n"
                 "Filter: log_time <= %f\n"
                 "%s"
                 "%s" % (cls.log_class(), time_range[0], time_range[1], object_type_filter,
                         lqencode(filter_headers)))

        with sites.only_sites(only_sites):
            try:
                return sites.live().query(query)
            except MKTimeout:
                raise
            except Exception:
                raise MKGeneralException(_("The query returned no data."))

    @classmethod
    def _forge_tooltip_and_url(cls, time_frame, properties, context):
        mode_properties = properties["render_mode"][1]
        time_range = cls._int_time_range_from_rangespec(mode_properties["time_range"])
        ending_timestamp = min(time_frame["ending_timestamp"], time_range[1])
        from_time_str = date_and_time(time_frame["timestamp"])
        to_time_str = date_and_time(ending_timestamp)
        # TODO: Can this be simplified by passing a list as argument to html.render_table()?
        tooltip = html.render_table(
            html.render_tr(html.render_td(_("From:")) + html.render_td(from_time_str)) +
            html.render_tr(html.render_td(_("To:")) + html.render_td(to_time_str)) + html.render_tr(
                html.render_td("%ss:" % properties["log_target"].capitalize()) +
                html.render_td(time_frame["value"])))

        args: HTTPVariables = []
        # Generic filters
        args.append(("filled_in", "filter"))
        args.append(("view_name", "events"))
        args.append(("logtime_from", str(time_frame["timestamp"])))
        args.append(("logtime_from_range", "unix"))
        args.append(("logtime_until", str(ending_timestamp)))
        args.append(("logtime_until_range", "unix"))
        args.append(("logclass%d" % cls.log_class(), "on"))

        # Target filters
        if properties["log_target"] == "host":
            args.append(("logst_h0", "on"))
            args.append(("logst_h1", "on"))
            args.append(("logst_h2", "on"))
        elif properties["log_target"] == "service":
            args.append(("logst_s0", "on"))
            args.append(("logst_s1", "on"))
            args.append(("logst_s2", "on"))
            args.append(("logst_s3", "on"))

        # Context
        for fil in context.values():
            for k, f in fil.items():
                args.append((k, f))

        return tooltip, makeuri_contextless(request, args, filename="view.py")


class ABCEventBarChartDashlet(ABCFigureDashlet):
    @classmethod
    def data_generator(cls) -> ABCEventBarChartDataGenerator:
        raise NotImplementedError()

    def show(self):
        args = dashlet_http_variables(self)
        args.append(("log_type", self.data_generator().log_type()))
        body = html.urlencode_vars(args)

        fetch_url = "ajax_%s_dashlet.py" % self.type_name()
        div_id = "%s_dashlet_%d" % (self.type_name(), self._dashlet_id)

        html.div("", id_=div_id)
        html.javascript(
            """
            let bar_chart_class_%(dashlet_id)d = cmk.figures.figure_registry.get_figure("timeseries");
            let %(instance_name)s = new bar_chart_class_%(dashlet_id)d(%(div_selector)s);
            %(instance_name)s.lock_zoom_y = true;
            %(instance_name)s.initialize();
            %(instance_name)s.set_post_url_and_body(%(url)s, %(body)s);
            %(instance_name)s.scheduler.set_update_interval(%(update)d);
            %(instance_name)s.scheduler.enable();
            """ % {
                "dashlet_id": self._dashlet_id,
                "instance_name": self.instance_name,
                "div_selector": json.dumps("#%s" % div_id),
                "url": json.dumps(fetch_url),
                "body": json.dumps(body),
                "update": self.update_interval,
            })


#   .--Notifications-------------------------------------------------------.
#   |       _   _       _   _  __ _           _   _                        |
#   |      | \ | | ___ | |_(_)/ _(_) ___ __ _| |_(_) ___  _ __  ___        |
#   |      |  \| |/ _ \| __| | |_| |/ __/ _` | __| |/ _ \| '_ \/ __|       |
#   |      | |\  | (_) | |_| |  _| | (_| (_| | |_| | (_) | | | \__ \       |
#   |      |_| \_|\___/ \__|_|_| |_|\___\__,_|\__|_|\___/|_| |_|___/       |
#   |                                                                      |
#   +----------------------------------------------------------------------+
@dashlet_registry.register
class NotificationsBarChartDashlet(ABCEventBarChartDashlet):
    """Dashlet that displays a bar chart for host and service notifications"""
    @classmethod
    def type_name(cls):
        return "notifications_bar_chart"

    @classmethod
    def title(cls):
        return _("Notification timeline")

    @classmethod
    def description(cls):
        return _("Displays a bar chart for host and service notifications.")

    @classmethod
    def data_generator(cls) -> 'NotificationsBarChartDataGenerator':
        return NotificationsBarChartDataGenerator()


class NotificationsBarChartDataGenerator(ABCEventBarChartDataGenerator):
    @classmethod
    def log_type(cls):
        return "notification"

    @classmethod
    def log_class(cls):
        return 3

    @classmethod
    def default_bar_chart_title(cls, properties, context):
        log_target_to_title = {
            "both": _("Host and service"),
            "host": _("Host"),
            "service": _("Service"),
        }
        return _("%s notifications") % log_target_to_title[properties["log_target"]]


@page_registry.register_page("ajax_notifications_bar_chart_dashlet")
class NotificationsDataPage(AjaxPage):
    def page(self):
        return NotificationsBarChartDataGenerator().generate_response_from_request()


#   .--Alerts--------------------------------------------------------------.
#   |                        _    _           _                            |
#   |                       / \  | | ___ _ __| |_ ___                      |
#   |                      / _ \ | |/ _ \ '__| __/ __|                     |
#   |                     / ___ \| |  __/ |  | |_\__ \                     |
#   |                    /_/   \_\_|\___|_|   \__|___/                     |
#   |                                                                      |
#   +----------------------------------------------------------------------+
@dashlet_registry.register
class AlertsBarChartDashlet(ABCEventBarChartDashlet):
    """Dashlet that displays a bar chart for host and service alerts"""
    @classmethod
    def type_name(cls):
        return "alerts_bar_chart"

    @classmethod
    def title(cls):
        return _("Alert timeline")

    @classmethod
    def description(cls):
        return _("Displays a bar chart for host and service alerts.")

    @classmethod
    def data_generator(cls) -> 'AlertBarChartDataGenerator':
        return AlertBarChartDataGenerator()


class AlertBarChartDataGenerator(ABCEventBarChartDataGenerator):
    @classmethod
    def log_type(cls):
        return "alert"

    @classmethod
    def log_class(cls):
        return 1

    @classmethod
    def default_bar_chart_title(cls, properties, context):
        log_target_to_title = {
            "both": _("Host and service"),
            "host": _("Host"),
            "service": _("Service"),
        }
        return _("%s alerts") % log_target_to_title[properties["log_target"]]


@page_registry.register_page("ajax_alerts_bar_chart_dashlet")
class AlertsDataPage(AjaxPage):
    def page(self):
        return AlertBarChartDataGenerator().generate_response_from_request()
