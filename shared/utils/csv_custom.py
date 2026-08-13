import logging
import csv
import os
from typing import Dict
import pandas as pd
from datetime import datetime, timedelta
import yaml

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(filename)s:%(lineno)d - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    force=True,
)

logger = logging.getLogger(__name__)


class CsvParseError(Exception):
    """Raised when the CSV is unreadable and has been backed up."""


class CsvHandler:
    """
    Read and write scraped market values in CSV format.
    """

    def __init__(self, config: Dict, csv_file_path) -> None:
        """
        Initialize CSV handler and configured headers.

        Args:
            config (Dict): Loaded configuration.
            csv_file_path (str): Path to the target CSV file.

        Returns:
            None
        """
        self.csv_file_path = csv_file_path
        self._config = config

        headers = []
        for entry in config["seasonal_foods"]:
            url = entry["url"]
            for table in entry.get("conditions", []):
                csv_header = table["csv_header"]
                headers.append(csv_header)
        self._headers = headers

    def save_to_csv(self, date: str, values: Dict[str, str]) -> None:
        """
        Append one date row and scraped values to CSV.

        Args:
            date (str): Date in YYYY/MM/DD format.
            values (Dict[str, str]): Scraped values keyed by csv_header.

        Returns:
            None
        """
        csv_file = self.csv_file_path
        file_exists = os.path.isfile(csv_file)

        fieldnames = ["date"] + self._headers

        with open(csv_file, mode="a", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()

            row = {"date": date}
            row.update(values)
            writer.writerow(row)

    def read_csv(self):
        """
        Read the latest recorded date from CSV.

        Args:
            None

        Returns:
            str | None: Latest date in URL format, or None when empty.
        """
        fieldnames = ["date"] + self._headers
        try:
            if not os.path.exists(self.csv_file_path):
                df = pd.DataFrame(columns=fieldnames)
                df.to_csv(self.csv_file_path, index=False)
                logger.info(f"Created CSV file: {self.csv_file_path}")
                return None
            else:
                try:
                    df = pd.read_csv(self.csv_file_path)
                    if df.empty or len(df) == 0:
                        df = pd.DataFrame(columns=fieldnames)
                        df.to_csv(self.csv_file_path, index=False)
                        return None
                    else:
                        last_date = df.iloc[-1, 0]
                        return self.from_csv_to_url(last_date)
                except pd.errors.EmptyDataError:
                    df = pd.DataFrame(columns=fieldnames)
                    df.to_csv(self.csv_file_path, index=False)

                except pd.errors.ParserError as e:
                    logger.error(f"CSV parse error: {e}")
                    raise CsvParseError(str(e)) from e

        except CsvParseError:
            raise

        except Exception as e:
            logger.error(e)

    @staticmethod
    def from_csv_to_url(csv_date):
        """
        Convert CSV date format into URL date format.

        Args:
            csv_date (str): Date in YYYY/MM/DD format.

        Returns:
            str: Date in YYYYMM/YYYYMMDD format.
        """
        year_month_day = csv_date.split("/")
        year_month = f"{year_month_day[0]}{year_month_day[1]}"
        full_date = f"{year_month_day[0]}{year_month_day[1]}{year_month_day[2]}"
        return f"{year_month}/{full_date}"

    def two_years_of_data_all(self):
        """
        Return all rows from the most recent two years.

        Args:
            None

        Returns:
            pd.DataFrame: Filtered and date-sorted dataframe.
        """
        df = pd.read_csv(self.csv_file_path)
        df["date"] = pd.to_datetime(df["date"], format="%Y/%m/%d", errors="coerce")

        end_date = datetime.now()
        start_date = end_date - timedelta(days=2 * 365)

        df_filtered = df[(df["date"] >= start_date) & (df["date"] <= end_date)]

        df_filtered = df_filtered.sort_values("date")

        return df_filtered

    def two_years_of_data_solo(self, target_cols):
        """
        Return selected columns from the most recent two years.

        Args:
            target_cols (str | list[str]): Target column name(s).

        Returns:
            pd.DataFrame: Filtered dataframe with date and selected columns.
        """
        df = pd.read_csv(self.csv_file_path)
        df["date"] = pd.to_datetime(df["date"], format="%Y/%m/%d", errors="coerce")
        end_date = datetime.now()
        start_date = end_date - timedelta(days=2 * 365)
        logger.info(start_date)
        df_filtered = df[(df["date"] >= start_date) & (df["date"] <= end_date)]
        df_filtered = df_filtered.sort_values("date")

        if isinstance(target_cols, str):
            target_cols = [target_cols]

        df_filtered = df_filtered[["date"] + target_cols]
        df_filtered = df_filtered.loc[:, ~df_filtered.columns.duplicated()]
        return df_filtered


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
    config_path: str = "config.yaml",
    date: str = "2024/04/01",
    output_path: str = "csv_custom_debug_output.csv",
    sample_values: dict = {
        "まぐろ生鮮（キロ）": 1000,
        "ぶり・わらさ（キロ）": 2000,
        "かつお（キロ）": 3000,
        "ブロッコリー（キロ）": 4000,
    },
) -> None:
    """
    Create CSV with headers from config.yaml and date and values you provide.

    Usage:
    1. Update `sample_values` defined above if needed.
    2. Upload `config.yaml` to the `/content` directory in Google Colab.
    3. Paste this code into a code cell in Google Colab.
    4. Run the cell (Shift + Enter).
    """

    ch = CsvHandler(_full_load_config(config_path), output_path)
    last_date = ch.read_csv()
    if last_date is not None:
        print(f"Found result csv file. Last date: {last_date}")

    try:
        ch.save_to_csv(date=date, values=sample_values)
        df = pd.read_csv(output_path)
        print(f"CSV includes data below.\n{df.tail()}")
    except Exception as e:
        print(e)


if __name__ == "__main__":
    debug_on_colab()
