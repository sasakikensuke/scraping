from datetime import datetime, timedelta
import logging

DATE_FORMAT_FIRST = "%Y%m"
DATE_FORMAT_SECOND = "%Y%m%d"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(filename)s:%(lineno)d - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    force=True,
)

logger = logging.getLogger(__name__)


class UrlHandler:
    @staticmethod
    def from_url_to_csv(url_date):
        """
        Convert URL date format to CSV date format.

        Args:
            url_date (str): Date in YYYYMM/YYYYMMDD format.

        Returns:
            str: Date in YYYY/MM/DD format.
        """
        year_month, full_date = url_date.split("/")
        new_date = f"{full_date[:4]}/{full_date[4:6]}/{full_date[6:]}"
        return new_date

    @staticmethod
    def calc_start_date(date, years_back=2):
        """
        Calculate historical start date by subtracting years from goal date.

        Args:
            date (str): Goal date in YYYYMM/YYYYMMDD format.
            years_back (int): Number of years to go back.

        Returns:
            str: Start date in YYYYMM/YYYYMMDD format.
        """
        date_part = date.split("/")[1]
        date_obj = datetime.strptime(date_part, DATE_FORMAT_SECOND)
        try:
            previous_date = date_obj.replace(year=date_obj.year - years_back)
        except ValueError:
            previous_date = date_obj.replace(year=date_obj.year - years_back, day=28)
        result_date = previous_date + timedelta(days=1)
        return result_date.strftime(f"{DATE_FORMAT_FIRST}/{DATE_FORMAT_SECOND}")

    @staticmethod
    def increment_date(current):
        """
        Increment URL date format by one day.

        Args:
            current (str): Date in YYYYMM/YYYYMMDD format.

        Returns:
            str: Incremented date in YYYYMM/YYYYMMDD format.
        """
        year_month, full_date = current.split("/")
        date_obj = datetime.strptime(full_date, DATE_FORMAT_SECOND)
        next_date_obj = date_obj + timedelta(days=1)
        next_date_str = next_date_obj.strftime(DATE_FORMAT_SECOND)
        next_year_month = next_date_obj.strftime(DATE_FORMAT_FIRST)
        return f"{next_year_month}/{next_date_str}"

    @staticmethod
    def is_end_date(end_date, current_date):
        """
        Check whether current_date reached or passed end_date.

        Args:
            end_date (str): Date in YYYYMM/YYYYMMDD format.
            current_date (str): Date in YYYYMM/YYYYMMDD format.

        Returns:
            bool: True when current_date is equal to or after end_date.
        """
        _, end_full_date = end_date.split("/")
        _, current_full_date = current_date.split("/")

        end_dt = datetime.strptime(end_full_date, DATE_FORMAT_SECOND)
        current_dt = datetime.strptime(current_full_date, DATE_FORMAT_SECOND)

        return current_dt >= end_dt

    @staticmethod
    def get_current_date():
        """
        Return current date in URL format.

        Args:
            None

        Returns:
            str: Date in YYYYMM/YYYYMMDD format.
        """
        today = datetime.today()
        formatted_date = today.strftime("%Y%m/%Y%m%d")
        return formatted_date


def debug_on_colab(
    url: str = "https://www.shijou-nippo.metro.tokyo.lg.jp/SN/202608/20260820/Sui/SN_Sui_Zen_index.html",
):
    """
    Usage:
    1. Update `url` defined above if needed.
    2. Paste this code into a code cell in Google Colab.
    3. Run the cell (Shift + Enter).
    """

    import re

    DATE_PATTERN = r"(\d{6})/(\d{8})"

    goal_url = url
    match = re.search(DATE_PATTERN, goal_url)
    goal_date = match.group(0)
    start_date = UrlHandler.calc_start_date(date=goal_date)
    _start_date = start_date.split("/")[-1]
    if "/" not in _start_date and len(_start_date) == 8:
        _start_date = f"{_start_date[:4]}/{_start_date[4:6]}/{_start_date[6:]}"
    print(f"Calculated start date: {_start_date}")


if __name__ == "__main__":
    debug_on_colab()
