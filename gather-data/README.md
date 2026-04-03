# Data Gather - ClinicalTrials.gov API Client

A UV-based Python application for querying the ClinicalTrials.gov REST API, specifically designed to search for Stargardt disease clinical trials.

## Installation

```bash
# Install dependencies with UV
uv sync
```

## Quick Start

Run the application:

```bash
# Using UV
uv run data-gather

# Or using Python directly
uv run python main.py
```

This will search for recruiting Stargardt disease trials and save results to `stargardt_trials.json`.

## Usage Examples

### Using as a Library

```python
from main import ClinicalTrialsClient

client = ClinicalTrialsClient()

# Search for Stargardt disease trials
response = client.search_stargardt(page_size=10)
studies = response.get('studies', [])

for study in studies:
    client.print_study_summary(study)
```

### Filter by Status

```python
# Search only recruiting trials
response = client.search_stargardt(status="RECRUITING")

# Other status options: COMPLETED, ACTIVE_NOT_RECRUITING, ENROLLING_BY_INVITATION, etc.
```

### Get All Trials

```python
# Get all Stargardt trials (handles pagination automatically)
all_trials = client.get_all_stargardt_trials()

print(f"Found {len(all_trials)} total trials")
```

### Get Study Details

```python
# Get detailed information for a specific trial
details = client.get_study_details("NCT12345678")
```

### Search Other Conditions

```python
# The client can search for any condition
response = client.search_condition(
    condition="Macular Degeneration",
    page_size=20,
    status="RECRUITING"
)
```

## Development

```bash
# Install with UV
uv sync

# Run the app
uv run data-gather

# Run directly with Python
uv run python main.py
```

## API Response Structure

The API returns JSON with the following structure:

```json
{
  "totalCount": 123,
  "studies": [
    {
      "protocolSection": {
        "identificationModule": {
          "nctId": "NCT12345678",
          "briefTitle": "Study Title"
        },
        "statusModule": {
          "overallStatus": "RECRUITING"
        }
      }
    }
  ],
  "nextPageToken": "..."
}
```

## Features

- ✅ Search for Stargardt disease trials
- ✅ Filter by study status
- ✅ Automatic pagination handling
- ✅ Get detailed study information
- ✅ Export results to JSON
- ✅ Search any medical condition
- ✅ UV-based dependency management

## API Reference

For more information about the ClinicalTrials.gov API v2, visit:
- [API Documentation](https://clinicaltrials.gov/data-api/api)
- [Study Data Structure](https://clinicaltrials.gov/data-api/about-api/study-data-structure)

## Common Study Statuses

- `RECRUITING` - Currently recruiting participants
- `ACTIVE_NOT_RECRUITING` - Active but not recruiting
- `COMPLETED` - Study has concluded
- `ENROLLING_BY_INVITATION` - Enrolling by invitation only
- `NOT_YET_RECRUITING` - Not yet recruiting
- `SUSPENDED` - Temporarily halted
- `TERMINATED` - Prematurely terminated
- `WITHDRAWN` - Withdrawn prior to enrollment
