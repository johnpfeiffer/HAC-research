#!/usr/bin/env python3
"""
ClinicalTrials.gov API Client for querying Stargardt disease trials.
"""

import requests
from typing import Optional, Dict, List, Any
import json


class ClinicalTrialsClient:
    """Client for querying ClinicalTrials.gov REST API."""

    BASE_URL = "https://clinicaltrials.gov/api/v2/studies"

    def __init__(self):
        """Initialize the ClinicalTrials.gov API client."""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Python-ClinicalTrials-Client/1.0'
        })

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
        page_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Search for clinical trials by condition.

        Args:
            condition: The medical condition to search for
            page_size: Number of results per page (default: 10)
            status: Filter by study status (e.g., 'RECRUITING', 'COMPLETED')
            format: Response format, 'json' or 'csv' (default: 'json')
            page_token: Token for pagination (optional)

        Returns:
            Dict containing the API response with studies
        """
        params = {
            'query.cond': condition,
            'pageSize': page_size,
            'format': format,
            'countTotal': 'true'
        }

        if status:
            params['filter.overallStatus'] = status

        if page_token:
            params['pageToken'] = page_token

        try:
            response = self.session.get(self.BASE_URL, params=params)
            response.raise_for_status()

            if format == "json":
                return response.json()
            else:
                return {"data": response.text}

        except requests.exceptions.RequestException as e:
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
        url = f"{self.BASE_URL}/{nct_id}"

        try:
            response = self.session.get(url)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
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
    client = ClinicalTrialsClient()

    print("Searching for Stargardt disease clinical trials...")
    print("=" * 80)

    # Search for recruiting trials
    response = client.search_stargardt(page_size=5, status="RECRUITING")

    if "error" in response:
        print(f"Error: {response['error']}")
        return

    total_count = response.get('totalCount', 0)
    studies = response.get('studies', [])

    print(f"\nTotal Stargardt disease trials found: {total_count}")
    print(f"Showing first {len(studies)} recruiting trials:\n")

    for study in studies:
        client.print_study_summary(study)

    # Save results to file
    with open('stargardt_trials.json', 'w') as f:
        json.dump(response, f, indent=2)

    print(f"\nFull results saved to stargardt_trials.json")


if __name__ == "__main__":
    main()
