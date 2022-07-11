"""Fetch reports"""
from datetime import date, timedelta
import logging
import os
from typing import Any

from google.cloud import storage
from appstoreconnect_BPHvZ import Api

import pandas as pd

from .admob.generate_mediation_report import get_mediation_report
from .const import (
    SENSOR_ADMOB_REVENUE_MONTH,
    SENSOR_ADMOB_REVENUE_TODAY,
    SENSOR_ANDROID_CURRENT_ACTIVE_INSTALLS,
    SENSOR_IOS_TOTAL_INSTALLS,
)

from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


class ReportApi:
    """Fetch reports"""

    def __init__(
        self,
        hass: HomeAssistant,
        play_service_account_path: str,
        bucket_name: str,
        play_bundle_id: str,
        ios_bundle_id: str,
        ios_key_id: str,
        ios_key_path: str,
        ios_issuer_id: str,
        admob_client_path: str,
        admob_publisher_id: str,
    ) -> None:
        self.hass = hass
        self.bucket_name = bucket_name
        self.play_bundle_id = play_bundle_id
        self.ios_bundle_id = ios_bundle_id
        self.ios_key_id = ios_key_id
        self.ios_key_path = ios_key_path
        self.ios_issuer_id = ios_issuer_id
        self.admob_client_path = admob_client_path
        self.admob_publisher_id = admob_publisher_id

        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = play_service_account_path

    def get_report_from_bucket(
        self,
    ) -> None:
        """Downloads a blob from the bucket."""

        result = {
            SENSOR_ANDROID_CURRENT_ACTIVE_INSTALLS: 0,
        }

        # The ID of your GCS bucket
        bucket_name = self.bucket_name

        # The ID of your GCS object
        source_blob_dir = "stats/installs/"
        source_blob_name = (
            "installs_"
            + self.play_bundle_id
            + "_"
            + str(date.today().year)
            + str(date.today().month).zfill(2)
            + "_overview.csv"
        )
        source_blob_full_path = source_blob_dir + source_blob_name

        # The path to which the file should be downloaded
        destination_file_name = "app_statistics/reports/android/" + source_blob_name
        os.makedirs("app_statistics/reports/android", exist_ok=True)

        storage_client = storage.Client()

        bucket = storage_client.bucket(bucket_name)

        # Construct a client side representation of a blob.
        # Note `Bucket.blob` differs from `Bucket.get_blob` as it doesn't retrieve
        # any content from Google Cloud Storage. As we don't need additional data,
        # using `Bucket.blob` is preferred here.
        blob = bucket.blob(source_blob_full_path)
        blob.download_to_filename(destination_file_name)

        _LOGGER.debug(
            "Downloaded storage object %s from bucket %s to local file %s",
            source_blob_full_path,
            bucket_name,
            destination_file_name,
        )

        _df = pd.read_csv(destination_file_name, sep=",", encoding="utf-16")
        _LOGGER.debug(_df.to_string())
        df_units = _df.loc[_df["Package Name"] == self.play_bundle_id]
        result[SENSOR_ANDROID_CURRENT_ACTIVE_INSTALLS] = df_units[
            "Active Device Installs"
        ].iloc[-1]

        return result

    def ios_reporting_dates(self, start_date: date) -> list:
        """Get all reporting dates between a starting date and today."""
        result = []
        today = date.today()
        year_difference = today.year - start_date.year
        while year_difference > 0:
            result.append(
                {
                    "frequency": "YEARLY",
                    "reportDate": date(today.year - year_difference, 1, 1).strftime(
                        "%Y"
                    ),
                }
            )
            year_difference -= 1
        month_difference = today.month - 1
        while month_difference > 0:
            result.append(
                {
                    "frequency": "MONTHLY",
                    "reportDate": date(today.year, month_difference, 1).strftime(
                        "%Y-%m"
                    ),
                }
            )
            month_difference -= 1

        current_month = date(today.year, today.month, 1)
        while current_month.month == today.month:
            # every sunday that has passed of the current month except if today is monday
            # the week report isn't ready yet on monday, so use the daily reports of the pas week instead
            if (
                current_month.weekday() == 6
                and today.day > current_month.day
                and current_month.day != today.day - 1
            ):
                result.append(
                    {
                        "frequency": "WEEKLY",
                        "reportDate": current_month.strftime("%Y-%m-%d"),
                    }
                )
                # print(current_month, "week completed")
            current_month += timedelta(days=1)

        monday_this_week = date(today.year, today.month, today.day - today.weekday())
        if current_month.day != today.day - 1:
            # use monday last week is today is monday and the last week report is not ready yet
            monday_this_week = date(today.year, today.month, today.day - 7)

        while monday_this_week.day < today.day:
            result.append(
                {
                    "frequency": "DAILY",
                    "reportDate": monday_this_week.strftime("%Y-%m-%d"),
                }
            )
            # print(monday_this_week, "days completed")
            monday_this_week += timedelta(days=1)
        _LOGGER.debug(result)
        return result

    def get_report_from_app_store_connect(self) -> dict:
        """Download sales report from app store connect."""
        result = {
            SENSOR_IOS_TOTAL_INSTALLS: 0,
        }

        # https://help.apple.com/app-store-connect/en.lproj/static.html#dev63c6f4502
        product_identifiers_installs = ["1", "1F", "1T", "F1"]

        api = Api(
            key_id=self.ios_key_id,
            key_file=self.ios_key_path,
            issuer_id=self.ios_issuer_id,
        )

        reporting_dates = self.ios_reporting_dates(start_date=date(2021, 1, 1))
        os.makedirs("app_statistics/reports/ios", exist_ok=True)

        # get all reports
        for reporting_date in reporting_dates:
            frequency = reporting_date["frequency"]
            report_date = reporting_date["reportDate"]
            file_path = "app_statistics/reports/ios/{}-{}-report.csv".format(
                frequency, report_date
            )

            # only download new reports
            if not os.path.isfile(file_path):
                try:
                    _LOGGER.debug("download report %s %s", frequency, report_date)
                    api.download_sales_and_trends_reports(
                        filters={
                            "vendorNumber": "87483853",
                            "frequency": frequency,
                            "reportDate": report_date,
                        },
                        save_to=file_path,
                    )
                except Exception as err:
                    _LOGGER.error(err)

            if os.path.isfile(file_path):
                try:
                    _df = pd.read_csv(file_path, sep="\t")
                    _LOGGER.debug(_df.to_string())

                    # bought app install and no app updates
                    df_units = _df.loc[
                        (_df["SKU"] == self.ios_bundle_id)
                        & (
                            _df["Product Type Identifier"].isin(
                                product_identifiers_installs
                            )
                        )
                    ]
                    _LOGGER.debug(
                        "total: %s, plus: %s",
                        result[SENSOR_IOS_TOTAL_INSTALLS],
                        df_units["Units"].sum(),
                    )
                    result[SENSOR_IOS_TOTAL_INSTALLS] = (
                        result[SENSOR_IOS_TOTAL_INSTALLS] + df_units["Units"].sum()
                    )
                except Exception as err:
                    _LOGGER.error(err)

        return result

    def clean_mediation_report(self, report: list) -> dict:
        """remove headers and sort earnings"""
        clean = {"DATE": [], "ESTIMATED_EARNINGS": []}
        del report[0]
        del report[-1]
        for _r in report:
            _dates: list = clean.get("DATE")
            _earnings: list = clean.get("ESTIMATED_EARNINGS")

            _dates.append(_r["row"]["dimensionValues"]["DATE"]["value"])
            _earnings.append(
                round(
                    int(_r["row"]["metricValues"]["ESTIMATED_EARNINGS"]["microsValue"])
                    / 1000000,
                    2,
                )
            )

            clean.update({"DATE": _dates})
            clean.update({"ESTIMATED_EARNINGS": _earnings})
        _LOGGER.debug(clean)
        return clean

    def get_admob_report(self) -> dict:
        """AdMob get mediation report"""
        result = {
            SENSOR_ADMOB_REVENUE_TODAY: 0,
            SENSOR_ADMOB_REVENUE_MONTH: 0,
        }
        today = date.today()
        start_of_month = date(today.year, today.month, 1)

        try:
            report = get_mediation_report(
                self.admob_client_path,
                self.admob_publisher_id,
                start_of_month,
                today,
            )
            clean_report = self.clean_mediation_report(report=report)
            result[SENSOR_ADMOB_REVENUE_TODAY] = clean_report["ESTIMATED_EARNINGS"][-1]
            result[SENSOR_ADMOB_REVENUE_MONTH] = sum(clean_report["ESTIMATED_EARNINGS"])
        except Exception as err:
            _LOGGER.error(err)

        return result

    async def update_data(self) -> dict:
        """Download reports from Google Play and App Store Connect."""
        result = {}

        admob_data = await self.hass.async_add_executor_job(self.get_admob_report)
        result.update(admob_data)
        _LOGGER.debug(admob_data)

        android_data = await self.hass.async_add_executor_job(
            self.get_report_from_bucket
        )
        result.update(android_data)
        _LOGGER.debug(android_data)

        ios_data = await self.hass.async_add_executor_job(
            self.get_report_from_app_store_connect
        )
        result.update(ios_data)
        _LOGGER.debug(ios_data)
        return result
