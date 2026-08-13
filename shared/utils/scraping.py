import requests
from bs4 import BeautifulSoup
import re
import pandas as pd
from io import StringIO
import time
import logging
from typing import Dict
import yaml

HTTP_TIMEOUT = (10, 30)

time.tzset()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(filename)s:%(lineno)d - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    force=True,
)
logger = logging.getLogger(__name__)


class TableNotFoundError(ValueError):
    """
    Raised when the target table cannot be found.
    """

    pass


class ValueNotFoundError(ValueError):
    """
    Raised when the target value cannot be found.
    """

    pass


class Scraping:
    """
    Scrape configured market values from HTML tables.
    """

    def get_whole(self, url):
        """
        Fetch and parse a page by URL.

        Args:
            url (str): Target page URL.

        Returns:
            BeautifulSoup: Parsed HTML content.
        """
        response = requests.get(url, timeout=HTTP_TIMEOUT)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")
        return soup

    def get_table(self, soup: BeautifulSoup, table_caption: str, url):
        """
        Find a table element by caption text pattern.

        Args:
            soup (BeautifulSoup): Parsed HTML document.
            table_caption (str): Caption text pattern.
            url (str): Source URL.

        Returns:
            Tag: Matched table element.
        """
        caption = soup.find("caption", string=re.compile(table_caption))
        if caption is None:
            raise TableNotFoundError()
        table = caption.find_parent("table")
        if table is None:
            raise TableNotFoundError()
        return table

    def convert_table(self, table_soup, header):
        """
        Convert an HTML table element into a dataframe.

        Args:
            table_soup: HTML table element.
            header (str): Header text used to identify header row.

        Returns:
            pd.DataFrame: Parsed table data.
        """
        table_str = str(table_soup)
        table_io = StringIO(table_str)
        table_df = pd.read_html(table_io, header=None)[0]
        header_row_index = None
        for i in range(min(2, len(table_df))):
            if header in table_df.iloc[i].astype(str).tolist():
                header_row_index = i
                break
        if header_row_index is not None:
            table_df.columns = table_df.iloc[header_row_index]
            table_df = table_df[(header_row_index + 1) :].reset_index(drop=True)
        return table_df

    def get_value(self, df, ref, header):
        """
        Extract a single value from dataframe by row filter and column.

        Args:
            df (pd.DataFrame): Source table data.
            ref (Dict[str, str]): Row filter conditions.
            header (str): Target column name.

        Returns:
            Any: Extracted value from the first matched row.
        """
        query = pd.Series(True, index=df.index)
        for key, value in ref.items():
            query &= df[key] == value
        filtered_df = df[query]

        if filtered_df.empty:
            raise ValueNotFoundError()

        if header not in filtered_df.columns:
            raise ValueNotFoundError()

        return filtered_df[header].values[0]

    def scrape_single_day(self, config: Dict, target_date, DATE_PATTERN):
        """
        Scrape all configured items for one target date.

        Args:
            config (Dict): Loaded configuration.
            target_date (str): URL date segment.
            DATE_PATTERN (str): Regex pattern for date replacement in URLs.

        Returns:
            Dict[str, str]: Scraped values keyed by csv_header.
        """
        seasonal_foods = config["seasonal_foods"]
        results = {}
        retry_interval = config["misc"]["interval_seconds"]

        for delicacy in seasonal_foods:
            conditions = delicacy["conditions"]
            sample_url = delicacy["url"]
            for table in conditions:
                time.sleep(retry_interval)
                ref = table["ref"]
                hd = table["subject_header"]
                table_name = table["table_name"]
                csv_header = table["csv_header"]
                retry_count = 0
                max_retries = 1

                while retry_count <= max_retries:
                    try:
                        url = re.sub(DATE_PATTERN, target_date, sample_url)
                        soup = self.get_whole(url=url)
                        table_bs = self.get_table(
                            soup=soup, table_caption=table_name, url=url
                        )
                        df = self.convert_table(table_soup=table_bs, header=hd)
                        val = self.get_value(df=df, ref=ref, header=hd)
                        results[csv_header] = val
                        if isinstance(val, (int, float)):
                            logger.info(
                                f"Scraped '{val:,}' for {csv_header} from {url}"
                            )
                        else:
                            logger.info(f"Scraped '{val}' for {csv_header} from {url}")
                        break

                    except requests.exceptions.ConnectionError as conn_err:
                        retry_count += 1
                        logger.warning(
                            f"Connection error for {csv_header}: {conn_err}. Retry {retry_count}/{max_retries}"
                        )
                        time.sleep(retry_interval)
                        if retry_count > max_retries:
                            logger.warning(
                                f"Max retries exceeded for {csv_header}. Skipping."
                            )
                            results[csv_header] = ""
                            break

                    except requests.exceptions.HTTPError as http_err:
                        logger.warning(f"HTTP error for {csv_header}: {http_err}")
                        results[csv_header] = ""
                        break
                    except TableNotFoundError:
                        logger.warning(
                            f"Failed to find table {table_name} for {csv_header} from {url}"
                        )
                        results[csv_header] = ""
                        break
                    except ValueNotFoundError:
                        logger.warning(f"Value not found for {csv_header}")
                        results[csv_header] = ""
                        break
                    except Exception as e:
                        logger.error(f"General error for {csv_header}: {e}")
                        results[csv_header] = ""
                        break

        return results


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
    config_path: str = "./config.yaml", target_date: str = "202502/20250204"
):
    """
    Scrape a single day based on the settings in config.yaml.

    Usage:
    1. Upload `config.yaml` to the `/content` directory in Google Colab.
    2. Paste this code into a code cell in Google Colab.
    3. Run the cell (Shift + Enter).
    """

    DATE_PATTERN = r"(\d{6})/(\d{8})"

    sc = Scraping()
    results = sc.scrape_single_day(
        config=_full_load_config(config_path=config_path),
        target_date=target_date,
        DATE_PATTERN=DATE_PATTERN,
    )
    results_formatted = ", ".join(f"{k}: {v}" for k, v in results.items())
    print(f"Scraped results: {results_formatted}")


if __name__ == "__main__":
    debug_on_colab()
