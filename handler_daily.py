import yaml
from typing import Dict
import logging
import requests
import time
import argparse

from shared.utils.scraping import Scraping
from shared.utils.csv_custom import CsvHandler
from shared.utils.url import UrlHandler

CONFIG_PATH = "./config.yaml"
RESULTS_PATH = "./record/results.csv"

DATE_PATTERN = r"(\d{6})/(\d{8})"
DATE_FORMAT_FIRST = "%Y%m"
DATE_FORMAT_SECOND = "%Y%m%d"

time.tzset()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(filename)s:%(lineno)d - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    force=True,
)

logger = logging.getLogger(__name__)


class DailyScraping:
    """
    Handle daily scraping and CSV persistence.
    """

    def __init__(self, config: Dict, csv_file_path) -> None:
        """
        Initialize daily scraping state.

        Args:
            config (Dict): Loaded configuration including URLs and conditions.
            csv_file_path (str): Path to the CSV file storing results.

        Returns:
            None
        """
        self._config = config
        self.csv_file_path = csv_file_path
        self.ch = CsvHandler(csv_file_path=csv_file_path, config=config)

    def scrape_today(self):
        """
        Scrape current-day market data and append it to the CSV.

        Args:
            None

        Returns:
            None
        """
        today = UrlHandler.get_current_date()

        try:
            ss = Scraping()
            results = ss.scrape_single_day(
                config=self._config, target_date=today, DATE_PATTERN=DATE_PATTERN
            )
            csv_date = UrlHandler.from_url_to_csv(today)
            self.ch.save_to_csv(date=csv_date, values=results)
            formatted = ", ".join(f"{k}: {v}" for k, v in results.items())
            logger.info(f"Saved:{csv_date}, {formatted}")
        except requests.exceptions.HTTPError as http_err:
            logger.info("Url not found.")
        except Exception as e:
            logger.warning(e)

        return


def main():
    """
    Run daily scraping once.

    Args:
        None

    Returns:
        None
    """

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--csv-file-path",
        default=RESULTS_PATH,
        help="Path to the CSV file storing results.",
    )
    args = parser.parse_args()

    try:
        config = _full_load_config(config_path=CONFIG_PATH)
        ds = DailyScraping(
            config,
            csv_file_path=args.csv_file_path,
        )
        ds.scrape_today()
    except Exception as e:
        logger.error(e)


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


if __name__ == "__main__":
    main()
