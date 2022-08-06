"""Generate mediation reports."""

from datetime import date
from googleapiclient.discovery import Resource

import google.oauth2.credentials
from googleapiclient.discovery import build


def generate_mediation_report(
    service: Resource, publisher_id: str, start_date: date, end_date: date
) -> list[dict]:
    """Generate and print a mediation report.

    Args:
      service: An AdMob Service Object.
      publisher_id: An ID that identifies the publisher.
    """

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
    dimensions = ["APP", "PLATFORM"]

    # Set metrics.
    metrics = ["ESTIMATED_EARNINGS", "AD_REQUESTS", "MATCHED_REQUESTS"]

    # Set sort conditions.
    sort_conditions = [{"dimension": "APP", "order": "ASCENDING"}]

    # Create mediation report specifications.
    report_spec = {
        "date_range": date_range,
        "dimensions": dimensions,
        "metrics": metrics,
        "sort_conditions": sort_conditions,
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
    credentials: google.oauth2.credentials,
    publisher_id: str,
    start_date: date,
    end_date: date,
) -> list[dict]:
    """Create Admob API client and get mediation report."""
    service = build("admob", "v1", credentials=credentials)
    return generate_mediation_report(service, publisher_id, start_date, end_date)
