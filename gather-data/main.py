#!/usr/bin/env python3
"""
ClinicalTrials.gov API Client for querying clinical trials by disease.
"""

import argparse
import json
import logging
import os
import re
from typing import Optional, Dict, List, Any

import requests

logger = logging.getLogger(__name__)


class ClinicalTrialsClient:
    """Client for querying ClinicalTrials.gov REST API."""

    BASE_URL = "https://clinicaltrials.gov/api/v2/studies"

    def __init__(self):
        """Initialize the ClinicalTrials.gov API client."""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Python-ClinicalTrials-Client/1.0'
        })
        logger.info("ClinicalTrialsClient initialized")

    def search_stargardt(
        self,
        page_size: int = 10,
        status: Optional[str] = None,
        format: str = "json"
    ) -> Dict[str, Any]:
        """
        Search for Stargardt disease clinical trials.

        Args:
            page_size: Number of results per page (default: 10)
            status: Filter by study status (e.g., 'RECRUITING', 'COMPLETED')
            format: Response format, 'json' or 'csv' (default: 'json')

        Returns:
            Dict containing the API response with studies
        """
        return self.search_condition(
            condition="Stargardt disease",
            page_size=page_size,
            status=status,
            format=format
        )

    def search_condition(
        self,
        condition: str,
        page_size: int = 10,
        status: Optional[str] = None,
        format: str = "json",
        page_token: Optional[str] = None,
        start_date_min: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Search for clinical trials by condition.

        Args:
            condition: The medical condition to search for
            page_size: Number of results per page (default: 10)
            status: Filter by study status (e.g., 'RECRUITING', 'COMPLETED')
            format: Response format, 'json' or 'csv' (default: 'json')
            page_token: Token for pagination (optional)
            start_date_min: Minimum study start date in YYYY-MM-DD format (optional)

        Returns:
            Dict containing the API response with studies
        """
        logger.info("Searching condition=%r, page_size=%d, status=%s", condition, page_size, status)
        params = {
            'query.cond': condition,
            'pageSize': page_size,
            'format': format,
            'countTotal': 'true'
        }

        if start_date_min:
            params['query.term'] = f'AREA[StartDate]RANGE[{start_date_min},MAX]'

        if status:
            params['filter.overallStatus'] = status

        if page_token:
            params['pageToken'] = page_token

        try:
            response = self.session.get(self.BASE_URL, params=params)
            response.raise_for_status()

            if format == "json":
                data = response.json()
                logger.info("Search returned %d studies", len(data.get("studies", [])))
                return data
            else:
                return {"data": response.text}

        except requests.exceptions.RequestException as e:
            logger.error("API request failed: %s", e)
            return {"error": str(e)}

    def get_all_stargardt_trials(
        self,
        status: Optional[str] = None,
        max_results: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all Stargardt disease trials, handling pagination automatically.

        Args:
            status: Filter by study status (optional)
            max_results: Maximum number of results to return (optional)

        Returns:
            List of all studies found
        """
        all_studies = []
        page_token = None
        page_size = 100  # Use larger page size for efficiency

        while True:
            response = self.search_stargardt(
                page_size=page_size,
                status=status
            )

            if "error" in response:
                print(f"Error: {response['error']}")
                break

            studies = response.get('studies', [])
            all_studies.extend(studies)

            # Check if we've hit max_results
            if max_results and len(all_studies) >= max_results:
                all_studies = all_studies[:max_results]
                break

            # Check for next page
            next_page_token = response.get('nextPageToken')
            if not next_page_token:
                break

            page_token = next_page_token

        return all_studies

    def get_study_details(self, nct_id: str) -> Dict[str, Any]:
        """
        Get detailed information for a specific study by NCT ID.

        Args:
            nct_id: The NCT ID of the study (e.g., 'NCT12345678')

        Returns:
            Dict containing study details
        """
        logger.info("Fetching study details: %s", nct_id)
        url = f"{self.BASE_URL}/{nct_id}"

        try:
            response = self.session.get(url)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error("Failed to fetch study %s: %s", nct_id, e)
            return {"error": str(e)}

    def print_study_summary(self, study: Dict[str, Any]) -> None:
        """
        Print a formatted summary of a study.

        Args:
            study: Study data dictionary
        """
        protocol = study.get('protocolSection', {})
        identification = protocol.get('identificationModule', {})
        status_module = protocol.get('statusModule', {})

        nct_id = identification.get('nctId', 'N/A')
        title = identification.get('briefTitle', 'N/A')
        status = status_module.get('overallStatus', 'N/A')

        print(f"\nNCT ID: {nct_id}")
        print(f"Title: {title}")
        print(f"Status: {status}")
        print("-" * 80)


def main():
    """Example usage of the ClinicalTrials client."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    parser = argparse.ArgumentParser(
        description='Search ClinicalTrials.gov for clinical trials by disease condition.'
    )
    parser.add_argument(
        '--disease',
        type=str,
        default='Stargardt disease',
        help='Disease or condition to search for (default: Stargardt disease)'
    )
    parser.add_argument(
        '--status',
        type=str,
        default='RECRUITING',
        help='Filter by study status (e.g., RECRUITING, COMPLETED, ALL) (default: RECRUITING)'
    )
    parser.add_argument(
        '--page-size',
        type=int,
        default=5,
        help='Number of results to retrieve (default: 5)'
    )
    parser.add_argument(
        '--start-date-min',
        type=str,
        default=None,
        help='Minimum study start date in YYYY-MM-DD format (e.g., 2020-01-01)'
    )

    args = parser.parse_args()

    client = ClinicalTrialsClient()

    print(f"Searching for {args.disease} clinical trials...")
    print("=" * 80)

    # Search for trials
    status_filter = None if args.status.upper() == 'ALL' else args.status
    response = client.search_condition(
        condition=args.disease,
        page_size=args.page_size,
        status=status_filter,
        start_date_min=args.start_date_min
    )

    if "error" in response:
        print(f"Error: {response['error']}")
        return

    total_count = response.get('totalCount', 0)
    studies = response.get('studies', [])

    status_text = args.status if args.status.upper() != 'ALL' else 'all'
    print(f"\nTotal {args.disease} trials found: {total_count}")
    print(f"Showing first {len(studies)} {status_text} trials:\n")

    for study in studies:
        client.print_study_summary(study)

    # Save results to file with disease name in SAVED subdirectory
    os.makedirs('SAVED', exist_ok=True)
    safe_disease_name = re.sub(r'[^a-z0-9]+', '_', args.disease.lower()).strip('_')
    filename = os.path.join('SAVED', f"{safe_disease_name}_trials.json")
    with open(filename, 'w') as f:
        json.dump(response, f, indent=2)

    print(f"\nFull results saved to {filename}")


if __name__ == "__main__":
    main()
