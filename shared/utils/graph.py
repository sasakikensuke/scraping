import pandas as pd
import logging
import os

logging.getLogger("matplotlib.font_manager").setLevel(logging.WARNING)
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import japanize_matplotlib
from datetime import datetime, timedelta
import matplotlib.dates as mdates

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(filename)s:%(lineno)d - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    force=True,
)
logger = logging.getLogger(__name__)


class TrendGraph:
    """
    Generate comparative trend graphs from CSV data.
    """

    def __init__(self, csv_file_path, output_graph_path, csv_header):
        """
        Initialize graph generation parameters.

        Args:
            csv_file_path (str): Path to source CSV file.
            output_graph_path (str): Output image path.
            csv_header (str): Target CSV column name.

        Returns:
            None
        """
        self.csv_file_path = csv_file_path
        self.output_graph_path = output_graph_path
        self.csv_header = csv_header

    def create(self):
        """
        Create and save a yearly comparison trend graph.

        Args:
            None

        Returns:
            None
        """
        df = pd.read_csv(self.csv_file_path)

        df["date"] = pd.to_datetime(df["date"], format="%Y/%m/%d")

        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)

        df_this_year = df[(df["date"] >= start_date) & (df["date"] <= end_date)]

        start_date_last_year = start_date - timedelta(days=365)
        df_last_year = df[
            (df["date"] >= start_date_last_year) & (df["date"] < start_date)
        ]

        df_this_year = df_this_year.dropna(subset=[self.csv_header])
        df_last_year = df_last_year.dropna(subset=[self.csv_header])

        if df_this_year.empty:
            logger.warning(
                f"No data for '{self.csv_header}' between {start_date.date()} and {end_date.date()}."
            )
            return

        if df_last_year.empty:
            logger.warning(
                f"No last year data for '{self.csv_header}' between "
                f"{start_date_last_year.date()} and {start_date.date()}."
            )
            return

        start_axis = end_date - timedelta(days=365)
        end_axis = end_date

        plt.figure(figsize=(10, 6))

        df_last_year_shifted = df_last_year.copy()
        df_last_year_shifted["date"] = df_last_year_shifted["date"] + timedelta(
            days=365
        )

        plt.plot(
            df_last_year_shifted["date"],
            pd.to_numeric(df_last_year_shifted[self.csv_header], errors="coerce"),
            label="last year",
            color="#80b0d4",
        )

        plt.plot(
            df_this_year["date"],
            pd.to_numeric(df_this_year[self.csv_header], errors="coerce"),
            label="this year",
            color="#0d6fc7",
        )
        plt.xlim(start_axis, end_axis)

        latest_date = df_this_year["date"].iloc[-1]
        latest_value = pd.to_numeric(
            df_this_year[self.csv_header].iloc[-1], errors="coerce"
        )
        latest_value = pd.to_numeric(latest_value, errors="coerce")

        plt.annotate(
            f"Latest:\n{latest_value:,.0f}\n({latest_date.strftime('%Y/%m/%d')})",
            xy=(latest_date, latest_value),
            xytext=(-4, 20),
            textcoords="offset points",
            ha="right",
            va="center",
            fontsize=9,
            zorder=5,
            clip_on=False,
            bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.7),
        )

        combined_df = pd.concat(
            [
                df_last_year_shifted.assign(source="last"),
                df_this_year.assign(source="this"),
            ]
        )

        combined_df[self.csv_header] = pd.to_numeric(
            combined_df[self.csv_header], errors="coerce"
        )
        combined_df = combined_df.dropna(subset=[self.csv_header])
        combined_df = combined_df[
            (combined_df["date"] >= start_axis) & (combined_df["date"] <= end_axis)
        ]

        max_idx = combined_df[self.csv_header].idxmax()
        min_idx = combined_df[self.csv_header].idxmin()

        max_date = combined_df.loc[max_idx, "date"]
        max_value = combined_df.loc[max_idx, self.csv_header]
        min_date = combined_df.loc[min_idx, "date"]
        min_value = combined_df.loc[min_idx, self.csv_header]

        plt.scatter([max_date], [max_value], s=20, zorder=6, color="green")
        plt.scatter([min_date], [min_value], s=20, zorder=6, color="green")
        plt.scatter(latest_date, latest_value, s=20, zorder=6, color="green")

        def get_edge_annotation_settings(point_date):
            x_fraction = (point_date - start_axis).total_seconds() / (
                end_axis - start_axis
            ).total_seconds()
            if x_fraction > 0.85:
                return dict(xytext=(-6, -4), ha="right")
            if x_fraction < 0.15:
                return dict(xytext=(6, -4), ha="left")
            return dict(xytext=(6, -4), ha="left")

        max_annot_settings = get_edge_annotation_settings(max_date)
        min_annot_settings = get_edge_annotation_settings(min_date)

        plt.annotate(
            f"Max: {max_value:,.0f} ({max_date.strftime('%Y/%m/%d')})",
            xy=(max_date, max_value),
            textcoords="offset points",
            va="bottom",
            fontsize=9,
            zorder=5,
            clip_on=True,
            bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.7),
            **max_annot_settings,
        )

        plt.annotate(
            f"Min: {min_value:,.0f} ({min_date.strftime('%Y/%m/%d')})",
            xy=(min_date, min_value),
            textcoords="offset points",
            va="top",
            fontsize=9,
            zorder=5,
            clip_on=True,
            bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.7),
            **min_annot_settings,
        )

        plt.title(f"{self.csv_header}")
        plt.xticks(rotation=45)
        plt.gca().xaxis.set_major_locator(mdates.MonthLocator(interval=1))
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter("%m"))
        plt.gca().yaxis.set_major_formatter(
            ticker.FuncFormatter(lambda x, _: f"{x:,.0f}")
        )
        plt.grid(False)
        plt.legend()
        plt.subplots_adjust(left=0.08, bottom=0.15, right=0.95, top=0.95)
        plt.savefig(self.output_graph_path)
        return


def debug_on_colab(
    csv_path: str = "./results_sample.csv", output_folder: str = "./graphs"
):
    """
    Create trend graphs from results_sample.csv.

    Usage:
    1. Upload `results_sample.csv` to the `/content` directory in Google Colab.
    2. Run `!pip -q install japanize-matplotlib` in a code cell to install the required library.
    3. Paste this code into a code cell in Google Colab.
    4. Run the cell (Shift + Enter).
    """

    os.makedirs(output_folder, exist_ok=True)
    df = pd.read_csv(csv_path, nrows=0)
    columns = [c for c in df.columns if c != "date"]
    for column in columns:
        output_path = os.path.join(output_folder, f"{column}.png")
        graph = TrendGraph(
            csv_file_path=csv_path,
            output_graph_path=output_path,
            csv_header=column,
        )
        graph.create()


if __name__ == "__main__":
    debug_on_colab()
