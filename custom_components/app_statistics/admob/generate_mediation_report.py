"""Generate mediation reports."""
# Copyright 2020 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from datetime import date
from .admob_utils import authenticate
from googleapiclient.discovery import Resource

# Set the 'PUBLISHER_ID' which follows the format "pub-XXXXXXXXXXXXXXXX".
# See https://support.google.com/admob/answer/2784578
# for instructions on how to find your publisher ID.
# PUBLISHER_ID = "pub-XXXXXXXXXXXXXXXX"


def generate_mediation_report(
    service: Resource, publisher_id: str, start_date: date, end_date: date
) -> list[dict]:
    """Generates and prints a mediation report.

    Args:
      service: An AdMob Service Object.
      publisher_id: An ID that identifies the publisher.
    """

    # [START main_body]
    # Set date range. AdMob API only supports the account default timezone and
    # "America/Los_Angeles", see
    # https://developers.google.com/admob/api/v1/reference/rest/v1/accounts.networkReport/generate
    # for more information.
    date_range = {
        "start_date": {
            "year": start_date.year,
            "month": start_date.month,
            "day": start_date.day,
        },
        "end_date": {
            "year": end_date.year,
            "month": end_date.month,
            "day": end_date.day,
        },
    }

    # Set dimensions.
    dimensions = ["DATE"]

    # Set metrics.
    metrics = ["ESTIMATED_EARNINGS", "AD_REQUESTS", "MATCHED_REQUESTS"]

    # Set sort conditions.
    sort_conditions = {"dimension": "DATE", "order": "ASCENDING"}

    # Set dimension filters.
    # dimension_filters = {
    #     'dimension': 'COUNTRY',
    #     'matches_any': {
    #         'values': ['US', 'CA']
    #     }
    # }

    # Create mediation report specifications.
    report_spec = {
        "date_range": date_range,
        "dimensions": dimensions,
        "metrics": metrics,
        "sort_conditions": [sort_conditions],
        # 'dimension_filters': [dimension_filters]
    }

    # Create mediation report request.
    request = {"report_spec": report_spec}

    # Execute mediation report request.
    response = (
        service.accounts()
        .mediationReport()
        .generate(parent="accounts/{}".format(publisher_id), body=request)
        .execute()
    )

    return response


def get_mediation_report(
    client_secrets_path: str, publisher_id: str, start_date: date, end_date: date
) -> list[dict]:
    """create Admob API client and get mediation report."""
    service = authenticate(client_secrets_path=client_secrets_path)
    return generate_mediation_report(service, publisher_id, start_date, end_date)
