# --------------------------------------------------------------------------- #
# Filename: initialisation.py
# Created Date: Tuesday, May 16th 2023, 5:39:57 pm
# Author: Ivan Ruiz Manuel
# Email: ivanruizmanuel@gmail.com
# Copyright (C) 2023 Ivan Ruiz Manuel and University of Geneva
# Apache License 2.0
# https://www.apache.org/licenses/LICENSE-2.0
# --------------------------------------------------------------------------- #
"""Contains all necessary functionality needed to initialise the model.

Must only contain functionality applicable to the entire model.

Rules:
- No sector-specific Sets.
- No global constants. Those go in configuration.py.
- This module shall not be used by sector files.
- Only include constraints that are essential to the model architecture.
"""
import numpy as np
import pyomo.environ as pyo
from model_utils import configuration as cnf
from model_utils import data_handler
from model_generic import generic_expressions as gen_expr


def _c_io_balance(model: pyo.ConcreteModel, flow_id: str, y: int, d: int, h: int):
    """Balance inputs and outputs at every flow bus."""
    outflows_prev = sum(model.fout[f, e, y, d, h] for (f, e) in model.FoE if f == flow_id)
    inflows_next = sum(model.fin[f, e, y, d, h] for (f, e) in model.FiE if f == flow_id)
    return outflows_prev == inflows_next


def _discount_rates(model, y):
    discount = cnf.DATA.get_const("country", "discount_factor")
    return 1 / np.power(1 + discount, (y - model.Y0.first()))


def _day_share(model: pyo.ConcreteModel, y, d):  # TODO: Placeholder. This should be obtained from the K-means file
    return 365 / len(model.D)


def _init_sets(model: pyo.ConcreteModel) -> pyo.ConcreteModel:
    # Temporal (1xN)
    model.Y = pyo.Set(initialize=cnf.YEARS, ordered=True)
    model.Y0 = pyo.Set(initialize=[cnf.YEARS[0]], ordered=True)
    model.YALL = pyo.Set(initialize=range(model.Y.first(), model.Y.last()+1), ordered=True)
    model.D = pyo.Set(initialize=cnf.DAYS, ordered=True)
    model.DALL = pyo.Set(initialize=range(365), ordered=True)
    model.H = pyo.Set(initialize=cnf.HOURS, ordered=True)
    model.H0 = pyo.Set(initialize=[cnf.HOURS[0]], ordered=True)

    # Structural (1xN)
    entities = set(cnf.ENTITIES)
    flows = set(cnf.FLOWS)
    model.E = pyo.Set(initialize=entities, ordered=False)
    model.F = pyo.Set(initialize=flows, ordered=False)

    # Entity groupings (1xN)
    demands = set(cnf.ENTITIES[cnf.ENTITIES.str.startswith("dem_")])
    processes = entities - demands
    model.Pros = pyo.Set(initialize=processes, ordered=False)  # TODO: eliminate
    capacity = cnf.DATA.build_cnf_set(processes, "enable_capacity")
    model.Caps = pyo.Set(initialize=capacity, ordered=False)

    # Connections (FxE), using cartesian subsets
    # See https://github.com/brentertainer/pyomo-tutorials/blob/master/intermediate/05-indexed-sets.ipynb
    f_in = data_handler.get_flow_entity_dict(cnf.DATA.fxe["FiE"])  # Must not contain Extractions
    f_out = data_handler.get_flow_entity_dict(cnf.DATA.fxe["FoE"])  # Must not contain Demands
    fxe = model.F * model.E
    model.FiE = pyo.Set(within=fxe, ordered=False, initialize={(f, e) for f in flows for e in f_in[f]})
    model.FoE = pyo.Set(within=fxe, ordered=False, initialize={(f, e) for f in flows for e in f_out[f]})

    return model


def _init_variables(model: pyo.ConcreteModel) -> pyo.ConcreteModel:
    model.ctot = pyo.Var(model.Caps, model.Y, domain=pyo.NonNegativeReals, initialize=0)
    model.cnew = pyo.Var(model.Caps, model.Y, domain=pyo.NonNegativeReals, initialize=0)

    # Process activity
    model.a = pyo.Var(model.E, model.Y, model.D, model.H, domain=pyo.NonNegativeReals, initialize=0)

    # Flows
    model.fin = pyo.Var(model.FiE, model.Y, model.D, model.H, domain=pyo.NonNegativeReals, initialize=0)
    model.fout = pyo.Var(model.FoE, model.Y, model.D, model.H, domain=pyo.NonNegativeReals, initialize=0)

    return model


def _init_parameters(model: pyo.ConcreteModel) -> pyo.ConcreteModel:
    model.YL = pyo.Param(initialize=cnf.YEARSLICE, doc="Length of a year-slice in the model, in years")
    model.DL = pyo.Param(model.Y, model.D, initialize=_day_share, mutable=True, doc="Number of days represented")
    model.HL = pyo.Param(initialize=cnf.TIMESLICE, doc="Length of an hour-slice in the model, in hours")
    model.DISC = pyo.Param(model.YALL, initialize=_discount_rates, doc="Discount Rates")

    return model


def _init_expressions(model: pyo.ConcreteModel) -> pyo.ConcreteModel:
    model.e_TotalAnnualInflow = pyo.Expression(model.FiE, model.Y, rule=gen_expr.e_total_annual_inflow)
    model.e_TotalAnnualOutflow = pyo.Expression(model.FoE, model.Y, rule=gen_expr.e_total_annual_outflow)

    model.e_TotalAnnualActivity = pyo.Expression(model.E, model.Y, rule=gen_expr.e_total_annual_activity)
    model.e_HourlyC2A = pyo.Expression(model.Caps, model.Y, rule=gen_expr.e_hourly_capacity_to_activity)

    model.e_CostInv = pyo.Expression(model.E, rule=gen_expr.e_cost_investment)
    model.e_CostFixedOM = pyo.Expression(model.E, rule=gen_expr.e_cost_fixed_om)
    model.e_CostVarOM = pyo.Expression(model.E, rule=gen_expr.e_cost_variable_om)
    return model


def init_model() -> pyo.ConcreteModel:
    """Create model structure."""
    # Initialise model
    model = pyo.ConcreteModel()
    model = _init_sets(model)
    model = _init_variables(model)
    model = _init_parameters(model)
    model = _init_expressions(model)

    model.c_io_balance = pyo.Constraint(model.F, model.Y, model.D, model.H, rule=_c_io_balance)

    return model


def run(model: pyo.ConcreteModel, objective: pyo.Expression):
    """Run the model with a given objective function."""
    model.cost = pyo.Objective(expr=objective, sense=pyo.minimize)
    model.dual = pyo.Suffix(direction=pyo.Suffix.IMPORT)

    opt = pyo.SolverFactory("gurobi", solver_io="python")
    opt.options["MIPGap"] = 1e-2
    opt.options["Timelimit"] = 1800
    try:
        opt_result = opt.solve(model, tee=False)
        print(opt_result)
    except ValueError:
        model.write("debug.lp", format="lp", io_options={"symbolic_solver_labels": True})

    return model
