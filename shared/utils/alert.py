import pandas as pd
import sys
import os
import yaml
from typing import Dict

base_dir = os.path.dirname(__file__) if "__file__" in globals() else os.getcwd()
sys.path.append(base_dir)

from csv_custom import CsvHandler


class Alert:
    """
    Provide threshold comparison helpers for alert evaluation.
    """

    @staticmethod
    def is_above_upper_abs_threshold(upper_abs, latest_value) -> bool:
        """
        Check whether a value exceeds the configured upper threshold.

        Args:
            upper_abs: Upper threshold value.
            latest_value: Latest observed value.

        Returns:
            bool: True when latest_value is greater than upper_abs.
        """
        if latest_value > upper_abs:
            return True
        else:
            return False

    @staticmethod
    def is_below_lower_abs_threshold(lower_abs, latest_value) -> bool:
        """
        Check whether a value is below the configured lower threshold.

        Args:
            lower_abs: Lower threshold value.
            latest_value: Latest observed value.

        Returns:
            bool: True when latest_value is lower than lower_abs.
        """
        if latest_value < lower_abs:
            return True
        else:
            return False


def _full_load_config(config_path: str = "config.yaml") -> Dict:
    """
    Load full configuration from YAML.

    Args:
        config_path (str): Path to config YAML.

    Returns:
        Dict: Parsed config.
    """
    with open(config_path) as file:
        return yaml.full_load(file)


def debug_on_colab(
    config_path: str = "config.yaml", csv_path: str = "results_sample.csv"
) -> None:
    """
    Apply alert rules from config.yaml to results_sample.csv.

    Usage:
    1. Upload `results_sample.csv`, `config.yaml`, and `csv_custom.py` to the `/content` directory in Google Colab.
    2. Paste this code into a code cell in Google Colab.
    3. Run the cell (Shift + Enter).
    """

    alert = Alert()

    config = _full_load_config(config_path=config_path)
    csv_handler = CsvHandler(config, csv_path)
    df = csv_handler.two_years_of_data_all()

    latest_values = {}
    for column in df.columns:
        if column == "date":
            continue
        last_valid = df[column].dropna().iloc[-1]
        latest_values[column] = last_valid

    seasonal_foods = config["seasonal_foods"]
    for delicacy in seasonal_foods:
        conditions = delicacy["conditions"]
        for table in conditions:
            if "alerts" in table:
                csv_header = table["csv_header"]
                alerts = table["alerts"]
                upper_abs = alerts["upper_abs"]
                lower_abs = alerts["lower_abs"]
                upper_result = False
                lower_result = False
                if upper_abs is not None:
                    upper_result = alert.is_above_upper_abs_threshold(
                        upper_abs=upper_abs, latest_value=latest_values[csv_header]
                    )
                if lower_abs is not None:
                    lower_result = alert.is_below_lower_abs_threshold(
                        lower_abs=lower_abs, latest_value=latest_values[csv_header]
                    )
                print(f"Alert of {csv_header}:")
                print(
                    f"upper_result: {upper_result} (latest: {latest_values[csv_header]}, setting:{upper_abs}), lower_result: {lower_result} (latest: {latest_values[csv_header]}, setting{lower_abs})"
                )

            else:
                print(f"No alerts defined for table: {table['table_name']}")


if __name__ == "__main__":
    debug_on_colab()
