# --------------------------------------------------------------------------- #
# Filename: restore_plots.py
# Path: /restore_plots.py
# Created Date: Sunday, January 15th 2023, 12:37:50 pm
# Author: Ivan Ruiz Manuel
# Copyright (c) 2023 University of Geneva
# GNU General Public License v3.0 or later
# https://www.gnu.org/licenses/gpl-3.0-standalone.html
# --------------------------------------------------------------------------- #
"""Graph generating utilities for RESTORE model outputs."""
import pandas as pd
import pyomo.environ as pyo

from model_utils.data_handler import DataHandler
from plotting import fig_tools


def _add_historical(axis, model: pyo.ConcreteModel, handler: DataHandler, flow: list):
    historical_data = [handler.get_annual(flow, "actual_flow", y) for y in model.Years]
    historical_ref = pd.Series(data=historical_data, index=model.Years, name="Historical total")
    axis = historical_ref.plot.line(ax=axis, color="black", linestyle="-.")
    return axis


# --------------------------------------------------------------------------- #
# Flow plots
# --------------------------------------------------------------------------- #
def plot_flow_fout(model, handler: DataHandler, flow_ids: list, unit: str = "TWh", hist: str = None):
    """Plot the modelled entity out flows at a flow node."""
    entity_ids = sorted({e for f, e in model.FoE if f in flow_ids})
    value_df = pd.DataFrame(index=model.Years, columns=entity_ids, data=0)

    # Gather values
    for flow in flow_ids:
        for f, e in model.FoE:
            if f == flow:
                for y in model.Years:
                    sum_fout = sum(model.fout[f, e, y, h].value for h in model.Hours)
                    value_df.loc[y, e] += sum_fout * model.TPERIOD  # time correction
    # Plotting
    axis = value_df.plot.area(linewidth=0)
    if hist:
        _add_historical(axis, model, handler, hist)
    title = f"Modelled:flow:{flow_ids}"
    fig_tools.prettify_plot(axis, title, unit)

    return axis


def plot_flow_fin(model, handler: DataHandler, flow_ids: list, unit: str = "TWh", hist: str = None):
    """Plot the modelled entity in flows at a flow node."""
    entity_ids = sorted({e for f, e in model.FiE if f in flow_ids})
    value_df = pd.DataFrame(index=model.Years, columns=entity_ids, data=0)

    # Gather values
    for f, e in model.FiE:
        if f in flow_ids:
            for y in model.Years:
                sum_fout = sum(model.fin[f, e, y, h].value for h in model.Hours)
                value_df.loc[y, e] += sum_fout * model.TPERIOD  # time correction

    # Plotting
    axis = value_df.plot.area(linewidth=0)
    if hist:
        _add_historical(axis, model, handler, hist)
    title = f"Modelled:Input:{flow_ids}"
    fig_tools.prettify_plot(axis, title, unit)

    return axis


# --------------------------------------------------------------------------- #
# Group plots
# --------------------------------------------------------------------------- #
def plot_group_ctot(model, group_ids: list, unit="GW"):
    """Plot the modelled total capacity of the entities in a group."""
    entity_ids = sorted({e for group in group_ids for e in model.Ents if group in e and e in model.Caps})
    cap_df = pd.DataFrame(index=model.Years, columns=entity_ids)

    # Gather values
    for e in entity_ids:
        for y in model.Years:
            cap_df.loc[y, e] = model.ctot[e, y].value

    # Plotting
    axis = cap_df.plot(kind="bar", stacked=True, width=0.8)
    title = f"Modelled:Tot Cap.:{group_ids}"
    fig_tools.prettify_plot(axis, title, unit)

    return axis


def plot_group_cnew(model, group_ids: list, unit="GW"):
    """Plot the modelled new capacity of the entities in a group."""
    entity_ids = sorted({e for group in group_ids for e in model.Ents if group in e and e in model.Caps})
    cap_df = pd.DataFrame(index=model.Years, columns=entity_ids)

    # Gather values
    for e in entity_ids:
        for y in model.Years:
            cap_df.loc[y, e] = model.cnew[e, y].value

    # Plotting
    axis = cap_df.plot(kind="bar", stacked=True, width=0.8)
    title = f"Modelled:New Cap.:{group_ids}"
    fig_tools.prettify_plot(axis, title, unit)

    return axis


def plot_group_cret(model, group_ids: list, unit="GW"):
    """Plot the modelled retired capacity of the entities in a group."""
    entity_ids = sorted({e for group in group_ids for e in model.Ents if group in e and e in model.Caps})
    cap_df = pd.DataFrame(index=model.Years, columns=entity_ids)

    # Gather values
    for e in entity_ids:
        for y in model.Years:
            cap_df.loc[y, e] = model.cret[e, y].value

    # Plotting
    axis = cap_df.plot(kind="bar", stacked=True, width=0.8)
    title = f"Modelled:New Cap.:{group_ids}"
    fig_tools.prettify_plot(axis, title, unit)

    return axis


def plot_group_act(model, group_ids: list, unit="GW"):
    """Plot the activity of the entities in a group."""
    entity_ids = sorted({e for group in group_ids for e in model.Ents if group in e})
    act_df = pd.DataFrame(index=model.Years, columns=entity_ids)

    # Gather values
    for e in entity_ids:
        for y in model.Years:
            act_df.loc[y, e] = model.TPERIOD * sum(model.a[e, y, h].value for h in model.Hours)

    # Plotting
    axis = act_df.plot.area(linewidth=0)
    title = f"Modelled:Activity:{group_ids}"
    fig_tools.prettify_plot(axis, title, unit)

    return axis
