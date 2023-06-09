# --------------------------------------------------------------------------- #
# Filename: data_handler.py
# Created Date: Monday, May 8th 2023, 10:55:29 am
# Author: Ivan Ruiz Manuel
# Email: ivanruizmanuel@gmail.com
# Copyright (C) 2023 Ivan Ruiz Manuel and University of Geneva
# Apache License 2.0
# https://www.apache.org/licenses/LICENSE-2.0
# --------------------------------------------------------------------------- #
"""Generic functions to deal with RESTORE configuration files."""
from typing import Any
from numbers import Number

import pandas as pd
import numpy as np

from data.zenodo_to_cnf import CNF_INDEX


def get_flow_entity_dict(io_df: pd.DataFrame, by_entity=False) -> dict[str, list]:
    """Create a dictionary with the flows as keys, and the connected processes as the item (in list)."""
    flows = io_df.columns
    io_dict = {f: [] for f in flows}  # type: dict[str, list]
    index_tuples = list(io_df.stack().index) if not by_entity else list(io_df.T.stack().index)
    for p, f in index_tuples:
        io_dict.setdefault(f, []).append(p)
    return {k: v for k, v in io_dict.items() if v}  # Get rid of empty flows


def merge_dicts(dict1: dict, dict2: dict) -> dict:
    """Combine two dictionaries, keeping the values of both.

    Args:
        dict1 (dict): input 1
        dict2 (dict): input 2

    Returns:
        dict: merged dictionary
    """
    keys = set(dict1.keys()) | set(dict2.keys())
    out_dict = {k: [] for k in keys}  # type: dict[str, list]
    for d in [dict1, dict2]:
        for k, i in d.items():
            out_dict[k].extend(i)

    return out_dict


def get_lf_vre(country: str) -> dict:
    """Get a dictionary with load factors for variable renewables (PV, OnshoreWind, OffshoreWind).

    Args:
        country (str): country ISO 3166-1 alpha-2 code

    Returns:
        dict: LF data, indexed by [Tech][year (1980-2019), timeslice (0-23)]
    """
    path = "data/zenodo/_common/renewables_ninja"
    solar_pv = pd.read_csv(
        f"{path}/ninja_pv_country_{country}_merra-2_corrected.csv",
        header=2,
        index_col=0,
    )
    wind = pd.read_csv(
        f"{path}/ninja_wind_country_{country}_current-merra-2_corrected.csv",
        header=2,
        index_col=0,
    )

    if len(wind.columns) > 1:
        wind.rename({"offshore": "OffshoreWind", "onshore": "OnshoreWind"}, axis=1, inplace=True)
        wind.drop("national", axis=1, inplace=True)
    else:
        wind.rename({"national": "OnshoreWind"}, axis=1, inplace=True)
        wind["OffshoreWind"] = 0

    solar_pv.index = pd.DatetimeIndex(solar_pv.index)
    wind.index = pd.DatetimeIndex(wind.index)
    solar_pv.columns = ["PV"]

    vre_df = pd.concat([solar_pv, wind], axis=1)
    result = vre_df.groupby([vre_df.index.year, vre_df.index.hour]).mean()

    col_fix = {
        "PV": "conv_elec_pv",
        "OnshoreWind": "conv_elec_onshorewind",
        "OffshoreWind": "conv_elec_offshorewind",
    }
    new_col = [col_fix[i] for i in result.columns]

    result.columns = new_col

    return result.to_dict()


class DataHandler:
    """Configuration file reading and extraction."""

    def __init__(self, path) -> None:
        """Initialise ConfigHandler object.

        Args:
            path (str): path to the configuration file.
        """
        # Get model configuration
        excel_file = pd.ExcelFile(path)

        fxe = {}
        params = {}

        # Convert configuration to dictionaries to improve speed
        for group in excel_file.sheet_names:
            if group in ["FiE", "FoE"]:
                fxe[group] = pd.read_excel(path, group, index_col=0)
            else:
                sheet_df = pd.read_excel(path, sheet_name=group)
                for entity_id in sheet_df.columns.drop(CNF_INDEX):
                    if entity_id in params:
                        raise ValueError("Found duplicate id", entity_id, "in sheet", group)
                    params[entity_id] = {}
                    id_cnf = sheet_df.loc[:, CNF_INDEX + [entity_id]]
                    for data_type in id_cnf["Type"].unique():
                        entity_df = id_cnf.loc[id_cnf["Type"] == data_type].copy()
                        if data_type in ["constant", "configuration"]:
                            entity_df.drop(["Type", "Flow", "Year"], axis=1, inplace=True)
                            entity_df.set_index(["Parameter"], inplace=True)
                        elif data_type in ["constant_fxe", "configuration_fxe"]:
                            entity_df.drop(["Type", "Year"], axis=1, inplace=True)
                            entity_df.set_index(["Parameter", "Flow"], inplace=True)
                        elif data_type == "annual":
                            entity_df.drop(["Type", "Flow"], axis=1, inplace=True)
                            entity_df.set_index(["Parameter", "Year"], inplace=True)
                        elif data_type == "annual_fxe":
                            entity_df.drop(["Type"], axis=1, inplace=True)
                            entity_df.set_index(["Parameter", "Flow", "Year"], inplace=True)
                        else:
                            raise ValueError("Invalid Data Type", data_type, "in", group, entity_id)

                        params[entity_id][data_type] = entity_df.to_dict()[entity_id]

        self.fxe = fxe
        self.params = params

    # ------------------------------------------------------------- #
    # Specific gets (stringent)
    # ------------------------------------------------------------- #
    def check_cnf(self, entity_id, parameter):
        """Evaluate if a configuration option is set.

        Turns functionality on/off. Empty values cause deactivation, not failure.
        """
        try:
            value = self.params[entity_id]["configuration"][parameter]
        except KeyError as exc:
            raise KeyError("Invalid key for", entity_id, parameter) from exc

        assert np.isnan(value) or isinstance(value, Number), f"Invalid: {entity_id}, {parameter}"
        return None if np.isnan(value) else value

    def get_const(self, entity_id: str, parameter: str) -> Any:
        """Return configuration constants.

        Empty values return None.
        """
        try:
            value = self.params[entity_id]["constant"][parameter]
        except KeyError as exc:
            raise KeyError("Invalid key for", entity_id, parameter) from exc

        assert isinstance(value, Number) or np.isnan(value), f"Invalid: {entity_id}, {parameter}"
        return None if np.isnan(value) else value

    def get_const_fxe(self, entity_id, parameter, flow):
        """Return flow-specific constants.

        Empty values return None.
        """
        try:
            value = self.params[entity_id]["constant_fxe"][(parameter, flow)]
        except KeyError as exc:
            raise KeyError("Invalid key for", entity_id, parameter, flow) from exc

        assert isinstance(value, Number) or np.isnan(value), f"Invalid: {entity_id}, {parameter}, {flow}"
        return None if np.isnan(value) else value

    def get_annual(self, entity_id, parameter, year):
        """Return historic values."""
        value = self.params[entity_id]["annual"][(parameter, year)]

        assert isinstance(value, Number) or np.isnan(value), f"Invalid: {entity_id}, {parameter}, {year}"
        return None if np.isnan(value) else value

    def get_annual_fxe(self, entity_id, parameter, flow, year):
        """Return flow-specific historic values."""
        # Trying to read empty annual data should cause an error to minimise bugs.
        value = self.params[entity_id]["annual_fxe"][(parameter, flow, year)]

        assert isinstance(value, Number) or np.isnan(value), f"Invalid: {entity_id}, {parameter}, {flow}, {year}"
        return None if np.isnan(value) else value

    # ------------------------------------------------------------- #
    # Generic gets  #TODO: needs rework. Should be a single dictionary with (Type, Param, Entity, Flow, Year)
    # ------------------------------------------------------------- #
    def get(self, entity_id, parameter, year, trigger_error=False):
        """Get a parameter, checking constants first."""
        value = None
        found = False
        if "annual" in self.params[entity_id] and (parameter, year) in self.params[entity_id]["annual"]:
            found = True
            value = self.get_annual(entity_id, parameter, year)
        if value is None and "constant" in self.params[entity_id] and parameter in self.params[entity_id]["constant"]:
            found = True
            value = self.get_const(entity_id, parameter)
        if not found and trigger_error:
            raise KeyError("Parameter", parameter, "not found for", entity_id)
        return value

    def get_fxe(self, entity_id, parameter, flow, year, trigger_error=False):
        """Get a FxE parameter, checking constants first."""
        value = None
        found = False
        if "annual_fxe" in self.params[entity_id] and (parameter, flow, year) in self.params[entity_id]["annual_fxe"]:
            found = True
            value = self.get_annual_fxe(entity_id, parameter, flow, year)
        if value is None:
            if "constant_fxe" in self.params[entity_id] and (parameter, flow) in self.params[entity_id]["constant_fxe"]:
                found = True
                value = self.get_const_fxe(entity_id, parameter, flow)
        if not found and trigger_error:
            raise KeyError("Parameter", parameter, "not found for", entity_id, "and", flow)
        return value

    # Configuration sets
    def build_cnf_set(self, entity_set: set, parameter: str):
        """Create a set where the given configuration is enabled."""
        config_enabled = set()
        config_enabled = [i for i in entity_set if self.check_cnf(i, parameter) == 1]

        return set(config_enabled)
