"""Fetch reports"""
from datetime import date, timedelta
import logging
import os

from google.cloud import storage
from appstoreconnect_BPHvZ import Api

import pandas as pd
from .const import (
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
    ) -> None:
        self.hass = hass
        self.bucket_name = bucket_name
        self.play_bundle_id = play_bundle_id
        self.ios_bundle_id = ios_bundle_id
        self.ios_key_id = ios_key_id
        self.ios_key_path = ios_key_path
        self.ios_issuer_id = ios_issuer_id

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
        destination_file_name = "./" + source_blob_name

        storage_client = storage.Client()

        bucket = storage_client.bucket(bucket_name)

        # Construct a client side representation of a blob.
        # Note `Bucket.blob` differs from `Bucket.get_blob` as it doesn't retrieve
        # any content from Google Cloud Storage. As we don't need additional data,
        # using `Bucket.blob` is preferred here.
        blob = bucket.blob(source_blob_full_path)
        blob.download_to_filename(destination_file_name)

        print(
            "Downloaded storage object {} from bucket {} to local file {}.".format(
                source_blob_full_path, bucket_name, destination_file_name
            )
        )

        df = pd.read_csv(destination_file_name, sep=",", encoding="utf-16")
        _LOGGER.debug(df.to_string())
        df_units = df.loc[df['Package Name'] == self.play_bundle_id]
        result[SENSOR_ANDROID_CURRENT_ACTIVE_INSTALLS] = df_units["Active Device Installs"].iloc[-1]

        return result

    def ios_reporting_dates(self, start_date: date) -> list[dict[str, str]]:
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
            if current_month.weekday() == 6 and today.day > current_month.day:
                result.append(
                    {
                        "frequency": "WEEKLY",
                        "reportDate": current_month.strftime("%Y-%m-%d"),
                    }
                )
                # print(current_month, "week completed")
            current_month += timedelta(days=1)

        monday_this_week = date(today.year, today.month, today.day - today.weekday())
        while monday_this_week.day < today.day:
            result.append(
                {
                    "frequency": "DAILY",
                    "reportDate": monday_this_week.strftime("%Y-%m-%d"),
                }
            )
            # print(monday_this_week, "days completed")
            monday_this_week += timedelta(days=1)
        print(result)
        return result

    def get_report_from_app_store_connect(self) -> dict[str, int]:
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

        # get all reports
        for reporting_date in reporting_dates:
            frequency = reporting_date["frequency"]
            report_date = reporting_date["reportDate"]
            file_path = "./{}-{}-report.csv".format(frequency, report_date)

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
                    df = pd.read_csv(file_path, sep="\t")
                    _LOGGER.debug(df.to_string())

                    # bought app install and no app updates
                    df_units = df.loc[
                        (df["SKU"] == self.ios_bundle_id)
                        & (
                            df["Product Type Identifier"].isin(
                                product_identifiers_installs
                            )
                        )
                    ]
                    _LOGGER.debug("total: %s, plus: %s", result[SENSOR_IOS_TOTAL_INSTALLS], df_units["Units"].sum())
                    result[SENSOR_IOS_TOTAL_INSTALLS] = (
                        result[SENSOR_IOS_TOTAL_INSTALLS] + df_units["Units"].sum()
                    )
                except Exception as err:
                    _LOGGER.error(err)

        return result

    async def update_data(self) -> dict[str, int]:
        """Download reports from Google Play and App Store Connect."""
        result = {}
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
