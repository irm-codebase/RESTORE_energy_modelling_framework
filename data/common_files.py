# --------------------------------------------------------------------------- #
# Filename: common_files.py
# Created Date: Monday, May 8th 2023, 10:55:26 am
# Author: Ivan Ruiz Manuel
# Email: ivanruizmanuel@gmail.com
# Copyright (C) 2023 Ivan Ruiz Manuel and University of Geneva
# Apache License 2.0
# https://www.apache.org/licenses/LICENSE-2.0
# --------------------------------------------------------------------------- #
"""Scripts for creating files in the _common folder."""
import pandas as pd
from gen_utils import file_manager


def deflator_file(world_bank_file_path: str, output_folder_path: str):
    """Generate the deflator file, to be used when converting currencies.

    To be used on the World Bank GDP deflator (linked) dataset.
    ID: NY.GDP.DEFL.ZS.AD
    Link: https://data.worldbank.org/indicator/NY.GDP.DEFL.ZS.AD

    Args:
        world_bank_file_path (str): path to the WB data file, in EXCEL format.
        output_folder_path (str): output folder path.
    """
    deflator_df = pd.read_excel(world_bank_file_path, sheet_name="Data", header=3)
    zenodo_df = pd.DataFrame(columns=file_manager.COLUMNS)

    years_str = [str(y) for y in range(1990, 2022)]
    years_int = list(range(1990, 2022))
    for i in deflator_df.index:
        country_code = deflator_df.loc[i, "Country Code"]
        values = deflator_df.loc[i, years_str].values

        tmp_df = pd.DataFrame(columns=file_manager.COLUMNS)
        tmp_df["Year"] = years_int
        tmp_df["Value"] = values
        tmp_df["Country"] = country_code
        zenodo_df = pd.concat([zenodo_df, tmp_df], ignore_index=True)

    zenodo_df["Entity"] = "deflator"
    zenodo_df["Parameter"] = "gdp_deflator"
    zenodo_df["Reference"] = "World Bank indicator NY.GDP.DEFL.ZS.AD"
    zenodo_df["Link"] = "https://data.worldbank.org/indicator/NY.GDP.DEFL.ZS.AD"

    file_manager.save_excel(zenodo_df, output_folder_path)
