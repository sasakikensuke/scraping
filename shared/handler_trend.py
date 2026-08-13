from typing import Dict
import yaml
import logging
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, ".."))

sys.path.append(BASE_DIR)
from utils.mail import EmailSender
from utils.graph import TrendGraph

CONFIG_PATH = os.path.join(PROJECT_ROOT, "config.yaml")
SECRET_PATH = os.path.join(PROJECT_ROOT, "secret.yaml")
CSV_PATH = os.path.join(PROJECT_ROOT, "record", "results.csv")
GRAPH_PATH = os.path.join(PROJECT_ROOT, "record", "{title}_trend.png")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(filename)s:%(lineno)d - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    force=True,
)

logger = logging.getLogger(__name__)


class DailyTrend:
    """
    Handle trend graph generation and notification email delivery.
    """

    def __init__(self, config: Dict, secret, graph_path, csv_path) -> None:
        """
        Initialize trend summary state.

        Args:
            config (Dict): Loaded configuration including target CSV headers.
            secret (Dict): Loaded secret values including mail settings.
            graph_path (str): Output path template for generated graph images.
            csv_path (str): Path to the CSV file storing scraped values.

        Returns:
            None
        """
        self._config = config
        self._secret = secret
        self._graph = graph_path
        self._csv = csv_path

    def summarize(self):
        """
        Generate trend graphs and send them as email attachments.

        Args:
            None

        Returns:
            None
        """
        mail_config = self._secret["mail"]
        smtp_server = mail_config["smtp_server"]
        smtp_port = mail_config["smtp_port"]
        email_address = mail_config["from"]
        email_password = mail_config["password"]
        to_email = mail_config["to"]
        seasonal_foods = self._config["seasonal_foods"]
        graph_paths = []

        for delicacy in seasonal_foods:
            conditions = delicacy["conditions"]
            for table in conditions:
                csv_header = table["csv_header"]
                graph_path = self._graph.format(title=csv_header)
                graph = TrendGraph(
                    csv_file_path=self._csv,
                    output_graph_path=graph_path,
                    csv_header=csv_header,
                )
                graph.create()
                graph_paths.append(graph_path)

        logger.info(f"Graphs have been saved: {graph_paths}")
        subject = "[Trend] Food market notifier"
        body = "Two-year trend graphs are attached."
        sender = EmailSender(smtp_server, smtp_port, email_address, email_password)
        try:
            sender.send_email(to_email, subject, body, attachment_paths=graph_paths)
        finally:
            for path in graph_paths:
                try:
                    os.remove(path)
                    logger.info(f"Deleted file: {path}")
                except Exception as e:
                    logger.warning(f"Failed to delete {path}: {e}")


def run_trend():
    """
    Run trend summary generation once.

    Args:
        None

    Returns:
        None
    """
    config = _full_load_config(config_path=CONFIG_PATH)
    secrets = load_secrets(secret_path=SECRET_PATH)
    trend_obj = DailyTrend(
        config=config,
        secret=secrets,
        csv_path=CSV_PATH,
        graph_path=GRAPH_PATH,
    )
    trend_obj.summarize()
    logger.info("Trend report has been sent.")


def main():
    """
    Run trend summary generation once as a CLI entry point.

    Args:
        None

    Returns:
        None
    """
    try:
        run_trend()
    except Exception:
        logger.exception("Trend handler failed.")
        sys.exit(1)


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
