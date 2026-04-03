#!/usr/bin/env python3
"""
Exa API Client for web search queries.
"""

import argparse
import json
import logging
import os
import re

from dotenv import load_dotenv
from exa_py import Exa

logger = logging.getLogger(__name__)


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

    parser = argparse.ArgumentParser(
        description='Search the web using the Exa API.'
    )
    parser.add_argument(
        'query',
        type=str,
        help='The search query string'
    )
    parser.add_argument(
        '--num-results',
        type=int,
        default=10,
        help='Number of results to return (default: 10)'
    )

    args = parser.parse_args()

    api_key = os.environ.get('EXA_API_KEY')
    if not api_key:
        logger.error("EXA_API_KEY not found in environment")
        print("Error: EXA_API_KEY not found in environment. Check your .env file.")
        return

    exa = Exa(api_key=api_key)

    logger.info("Searching Exa: query=%r, num_results=%d", args.query, args.num_results)
    print(f"Searching Exa for: {args.query}")
    print("=" * 80)

    result = exa.search(
        args.query,
        type="auto",
        num_results=args.num_results,
    )
    logger.info("Exa returned %d results", len(result.results))

    print(f"\nResults ({len(result.results)}):\n")
    for i, r in enumerate(result.results, 1):
        print(f"{i}. {r.title}")
        print(f"   {r.url}")
        if r.score is not None:
            print(f"   Score: {r.score:.4f}")
        print()

    os.makedirs('SAVED', exist_ok=True)
    safe_query_name = re.sub(r'[^a-z0-9]+', '_', args.query.lower()).strip('_')
    filename = os.path.join('SAVED', f"exa_{safe_query_name}.json")
    with open(filename, 'w') as f:
        json.dump([{
            "title": r.title,
            "url": r.url,
            "score": r.score,
        } for r in result.results], f, indent=2)

    print(f"Results saved to {filename}")


if __name__ == "__main__":
    main()
