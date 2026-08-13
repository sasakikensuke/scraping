import sys
import os
import yaml
from typing import Dict
import logging
import re
import requests
import time

from shared.utils.scraping import Scraping
from shared.utils.csv_custom import CsvHandler, CsvParseError
from shared.utils.url import UrlHandler
from shared.handler_trend import run_trend
from shared.handler_alert import run_alert

CONFIG_PATH = "./config.yaml"
RESULTS_PATH = "./record/results.csv"
LOG_PATH = "./record/historical.log"

DATE_PATTERN = r"(\d{6})/(\d{8})"
DATE_FORMAT_FIRST = "%Y%m"
DATE_FORMAT_SECOND = "%Y%m%d"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(filename)s:%(lineno)d - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    force=True,
)

logger = logging.getLogger(__name__)

# Persist historical run logs to disk in addition to stdout.
os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)

file_handler = logging.FileHandler(LOG_PATH, encoding="utf-8")
file_handler.setLevel(logging.INFO)

formatter = logging.Formatter(
    "%(asctime)s [%(levelname)s] %(filename)s:%(lineno)d - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
file_handler.setFormatter(formatter)

root_logger = logging.getLogger()
root_logger.addHandler(file_handler)


class HistoricalReportError(Exception):
    """Raised when the final trend/alert phase fails."""


class TwoYearsScraping:
    """
    Handle historical scraping and incremental CSV updates.
    """

    def __init__(self, config: Dict, csv_file_path) -> None:
        """
        Initialize historical scraping state.

        Args:
            config (Dict): Loaded configuration including URLs and conditions.
            csv_file_path (str): Path to the CSV file storing results.

        Returns:
            None
        """
        self._config = config
        self.csv_file_path = csv_file_path
        self.ch = CsvHandler(csv_file_path=csv_file_path, config=config)

    def scrape_two_years(self) -> bool:
        """
        Scrape and persist one target day per invocation.

        Args:
            None

        Returns:
            bool: True when historical scraping is completed; otherwise False.
        """
        goal_url = self._config["seasonal_foods"][0]["url"]
        match = re.search(DATE_PATTERN, goal_url)
        goal_date = match.group(0)

        last_date = self.ch.read_csv()
        next_date = ""

        if last_date is None:
            start_date = UrlHandler.calc_start_date(date=goal_date)
            _start_date = start_date.split("/")[-1]
            if "/" not in _start_date and len(_start_date) == 8:
                _start_date = f"{_start_date[:4]}/{_start_date[4:6]}/{_start_date[6:]}"
            logger.info(f"Started the job from {_start_date}.")
            next_date = start_date

        elif UrlHandler.is_end_date(goal_date, last_date):
            self._run_report_process()
            return True

        else:
            next_date = UrlHandler.increment_date(current=last_date)

        while True:
            try:
                sc = Scraping()
                results = sc.scrape_single_day(
                    config=self._config,
                    target_date=next_date,
                    DATE_PATTERN=DATE_PATTERN,
                )
                csv_date = UrlHandler.from_url_to_csv(next_date)
                self.ch.save_to_csv(date=csv_date, values=results)
                formatted = ", ".join(f"{k}: {v}" for k, v in results.items())
                logger.info(f"Saved:{csv_date}, {formatted}")
                break

            except requests.exceptions.HTTPError:
                # Skip unavailable dates and continue with the next day.
                logger.info("URL not found.")
                current_date = self.ch.read_csv()
                next_date = UrlHandler.increment_date(current=current_date)

            except Exception as e:
                # Back off before the next loop iteration in main().
                logger.warning(e)
                time.sleep(self._config["misc"]["interval_seconds"])
                break

        return False

    def _run_report_process(self) -> None:
        """
        Run final report generation after historical scraping completes.

        Args:
            None

        Returns:
            None
        """
        try:
            run_trend()
            run_alert()
        except Exception as e:
            raise HistoricalReportError(str(e)) from None


def load_secrets(secret_path) -> Dict:
    """
    Load secret values from YAML.

    Args:
        secret_path (str): Path to the secret YAML file.

    Returns:
        Dict: Parsed secrets.
    """
    with open(secret_path, "r", encoding="utf-8") as file:
        secrets = yaml.safe_load(file)
    return secrets


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


def main():
    """
    Run the historical scraping loop until completion or fatal error.

    Args:
        None

    Returns:
        None
    """
    try:
        config = _full_load_config(config_path=CONFIG_PATH)
        loop_interval_seconds = config["misc"]["interval_seconds"]
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        sys.exit(1)

    while True:
        try:
            tys = TwoYearsScraping(
                config,
                csv_file_path=RESULTS_PATH,
            )
            completed = tys.scrape_two_years()
            if completed:
                logger.info("Completed the job.")
                break
        except CsvParseError as e:
            logger.error(f"CSV parse error detected. Stopping main loop: {e}")
            break
        except HistoricalReportError as e:
            logger.error(e)
            break
        except Exception as e:
            logger.error(e)

        time.sleep(loop_interval_seconds)


if __name__ == "__main__":
    main()
