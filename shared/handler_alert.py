import pandas as pd
import yaml
import logging
from typing import Dict
from collections import defaultdict
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, ".."))

sys.path.append(BASE_DIR)
from utils.mail import EmailSender
from utils.alert import Alert
from utils.csv_custom import CsvHandler

CONFIG_PATH = os.path.join(PROJECT_ROOT, "config.yaml")
SECRET_PATH = os.path.join(PROJECT_ROOT, "secret.yaml")
CSV_PATH = os.path.join(PROJECT_ROOT, "record", "results.csv")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(filename)s:%(lineno)d - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    force=True,
)
logger = logging.getLogger(__name__)


class DailyAlert:
    def __init__(self, config: Dict, secret, csv_path) -> None:
        """
        Initialize alert checking state.

        Args:
            config (Dict): Loaded configuration including alert thresholds.
            secret (Dict): Loaded secret values including mail settings.
            csv_path (str): Path to the CSV file storing scraped values.

        Returns:
            None
        """
        self._config = config
        self._secret = secret
        self._csv_path = csv_path

    def check_alert(self):
        """
        Evaluate alert thresholds and send an alert email when triggered.

        Args:
            None

        Returns:
            None
        """
        mail_config = self._secret["mail"]
        alert = Alert()
        smtp_server = mail_config["smtp_server"]
        smtp_port = mail_config["smtp_port"]
        email_address = mail_config["from"]
        email_password = mail_config["password"]
        to_email = mail_config["to"]
        email_sender = EmailSender(
            smtp_server, smtp_port, email_address, email_password
        )
        csv_handler = CsvHandler(self._config, self._csv_path)
        df = csv_handler.two_years_of_data_all()
        latest_values = {}
        for column in df.columns:
            if column == "date":
                continue
            last_valid = df[column].dropna().iloc[-1]
            latest_values[column] = last_valid

        alerts_results = defaultdict(dict)
        seasonal_foods = self._config["seasonal_foods"]
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
                        alerts_results[csv_header]["alert_upper"] = upper_result
                    if lower_abs is not None:
                        lower_result = alert.is_below_lower_abs_threshold(
                            lower_abs=lower_abs, latest_value=latest_values[csv_header]
                        )
                        alerts_results[csv_header]["alert_lower"] = lower_result
                    alerts_results[csv_header]["setting_upper"] = upper_abs
                    alerts_results[csv_header]["setting_lower"] = lower_abs
                    alerts_results[csv_header]["latest"] = latest_values[csv_header]

                else:
                    logger.info(f"No alerts defined for table: {table['table_name']}")

        alert_lines = []
        for item_name, result in alerts_results.items():
            if result.get("alert_upper"):
                alert_lines.append(
                    f"{item_name}（{format_number(result['latest'])}） "
                    f"は設定した値（{format_number(result['setting_upper'])}）を上回りました"
                )
            if result.get("alert_lower"):
                alert_lines.append(
                    f"{item_name}（{format_number(result['latest'])}） "
                    f"は設定した値（{format_number(result['setting_lower'])}）を下回りました"
                )

        if alert_lines:
            subject = "[Alert] Food market notifier"
            body = "\n".join(
                ["Latest food market value exceeded threshold."]
                + [f"- {line}" for line in alert_lines]
            )
            email_sender.send_email(to_email, subject, body)
            logger.info(f"Alert has been sent.")
        else:
            logger.info("No value exceeded threshold.")


def format_number(val):
    """
    Format numeric values with comma separators.

    Args:
        val: Value to format.

    Returns:
        str: Formatted value.
    """
    if isinstance(val, (int, float)) and pd.notna(val):
        return f"{val:,.0f}"
    return str(val)


def main():
    """
    Run alert evaluation once as a CLI entry point.

    Args:
        None

    Returns:
        None
    """
    try:
        run_alert()
    except Exception:
        logger.exception("Alert handler failed.")
        sys.exit(1)


def run_alert():
    """
    Run alert evaluation once.

    Args:
        None

    Returns:
        None
    """
    config = _full_load_config(config_path=CONFIG_PATH)
    secrets = load_secrets(secret_path=SECRET_PATH)
    ds = DailyAlert(config, secret=secrets, csv_path=CSV_PATH)
    ds.check_alert()


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


def load_secrets(secret_path) -> Dict:
    """
    Load secret values from YAML.

    Args:
        secret_path (str): Path to secret YAML.

    Returns:
        Dict: Parsed secrets.
    """
    with open(secret_path, "r", encoding="utf-8") as file:
        secrets = yaml.safe_load(file)
    return secrets


if __name__ == "__main__":
    main()
