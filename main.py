"""
The script will query a PRISMA endpoint and return the active egress IP addresses in use for each region.
The regions being NORTH WEST, CENTRAL, EAST, SOUTH and SOUTE EAST.
"""

__author__ = "Steve Graesart"
__email__ = "steve.graesart@ascension.org"
__date__ = "2026/10/21"
__maintainer__ = "Steve Graesart"
__version__ = "1.0"

import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import requests
from dotenv import load_dotenv

# 1. Create a custom logger
logger = logging.getLogger("prisma_logger")
logger.setLevel(logging.DEBUG)  # Capture everything from DEBUG level and up

# 2. Define the log message format (Timestamp - Name - Severity Level - Message)
formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
)

# 3. Create a Console Handler (outputs logs to the terminal)
console_handler = logging.StreamHandler(sys.stderr)
console_handler.setLevel(
    logging.INFO
)  # Terminal only shows INFO, WARNING, ERROR, CRITICAL
console_handler.setFormatter(formatter)

# 4. Create a File Handler (saves logs to a text file)
file_handler = logging.FileHandler("app.log", mode="a", encoding="utf-8")
file_handler.setLevel(logging.DEBUG)  # File captures deeper details (including DEBUG)
file_handler.setFormatter(formatter)

# 5. Add handlers to the logger
logger.addHandler(console_handler)
logger.addHandler(file_handler)


def prisma_endpoint_query() -> dict[str, Any]:

    prisma_endpoint = "https://api.prod6.datapath.prismaaccess.com/getPrismaAccessIP/v2"
    custom_headers = {"header-api-key": os.getenv("api_key")}
    options = {"serviceType": "gp_gateway", "addrType": "all", "location": "all"}

    response = requests.post(prisma_endpoint, headers=custom_headers, json=options, timeout=30)
    response.raise_for_status()

    logger.info(f"Prisma endpoint returned {response.status_code}")

    return response.json()


def endpoint_print(gway_list: dict[str, Any]) -> None:

    logger.info("Creating endpoint json file with egress IPs")

    gateway_list = gway_list

    gw_list = [
        {gateway.get("zone", "Unknown Zone"): gateway.get("addresses", [])}
        for gateway in gateway_list.get("result", [])
    ]

    # Create a timezone object and automatically adjust for DST
    est_tz = ZoneInfo("America/New_York")

    now = datetime.now(est_tz)
    current_date_time = now.strftime("%Y-%m-%d_%H-%M-%S")

    policy_results_dir = Path("gateway_results")
    policy_results_dir.mkdir(parents=True, exist_ok=True)
    file_path = policy_results_dir / f"gateways-{current_date_time}.json"

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(gw_list, f, indent=4)

    logger.info(f"Json file created at {file_path}")


def main():

    load_dotenv()

    # Fail-fast pattern: Verify environment variables exist before running actions
    # api_key = os.getenv("api_key")
    if not os.getenv("api_key"):
        logger.critical(
            "Environment configuration failed: 'api_key' variable not found."
        )
        sys.exit(1)

    try:
        logger.info("Querying prisma endpoint for details")
        gateways = prisma_endpoint_query()
    except requests.exceptions.Timeout:
        logger.critical("[ERROR] TIMEOUT EXCEEDED")
        sys.exit(1)
    except requests.exceptions.ConnectionError:
        logger.critical("[ERROR] CONNECTION ERROR: CHECK INET, DNS")
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code if e.response is not None else "Unknown"
        logger.critical(f"[ERROR] SERVER ERROR | Status Code: {status_code}")
        sys.exit(1)
    except requests.exceptions.RequestException as e:
        logger.critical(f"{e}")
        sys.exit(1)

    endpoint_print(gateways)


if __name__ == "__main__":
    main()
