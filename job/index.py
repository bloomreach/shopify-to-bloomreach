# job/index.py
import logging
import polling
import requests
from os import getenv

logger = logging.getLogger(__name__)


def hostname_from_environment(environment="staging"):
    hostnames = {
        "staging": "api-staging.connect.bloomreach.com",
        "production": "api.connect.bloomreach.com"
    }

    if environment not in hostnames:
        raise Exception("Invalid environment: %s" % environment)
    return hostnames[environment]


def trigger_index(account_id="", environment_name="", catalog_name="", token=""):
    """
    Trigger an indexing job for the catalog using v1 API.

    Returns:
        str: Job ID of the indexing job
    """
    dc_endpoint = "dataconnect/api/v1"
    hostname = hostname_from_environment(environment_name)

    url = f"https://{hostname}/{dc_endpoint}/accounts/{account_id}/catalogs/{catalog_name}/indexes"

    headers = {
        "Authorization": "Bearer " + token,
        "Content-Type": "application/json"
    }

    logger.info("Triggering index job: %s", url)
    response = requests.post(url, headers=headers)
    response.raise_for_status()

    job_id = response.json()["jobId"]
    logger.info("Index job triggered successfully. Job ID: %s", job_id)

    return job_id


def check_index_status(job_id="", environment_name="", token=""):
    """
    Check the status of an indexing job using v1 API.

    Returns:
        bool: True if job completed successfully, False if still running
    """
    dc_endpoint = "dataconnect/api/v1"
    hostname = hostname_from_environment(environment_name)

    url = f"https://{hostname}/{dc_endpoint}/jobs/{job_id}"

    headers = {
        "Authorization": "Bearer " + token
    }

    logger.info("Checking index job status: %s", url)
    response = requests.get(url, headers=headers)
    response.raise_for_status()

    status = response.json()["status"]
    logger.info("Index job status: %s", status)

    if status == "success":
        return True

    if status in ["failed", "killed"]:
        logger.error("Index job failed: %s, %s", job_id, status)
        raise ValueError("Index job did not complete successfully")

    return False


def run_index(account_id="", environment_name="", catalog_name="", token=""):
    """
    Trigger an index job and wait for completion using v1 API.
    """
    logger.info("Starting index operation for catalog: %s", catalog_name)

    # Trigger the index job
    job_id = trigger_index(account_id, environment_name, catalog_name, token)

    # Poll for completion
    polling.poll(
        lambda: check_index_status(job_id, environment_name, token),
        step=10,
        timeout=7200
    )

    logger.info("Index operation completed successfully")


if __name__ == '__main__':
    import argparse
    from sys import stdout

    # Define logger
    loglevel = getenv('LOGLEVEL', 'INFO').upper()
    logging.basicConfig(
        stream=stdout,
        level=loglevel,
        format="%(name)-12s %(asctime)s %(levelname)-8s %(filename)s:%(funcName)s %(message)s"
    )

    parser = argparse.ArgumentParser(
        description="Triggers an indexing job for a Bloomreach Discovery catalog using v1 API."
    )

    parser.add_argument(
        "--br-environment",
        help="Which Bloomreach Account environment to use",
        type=str,
        default=getenv("BR_ENVIRONMENT_NAME"),
        required=not getenv("BR_ENVIRONMENT_NAME")
    )

    parser.add_argument(
        "--br-account-id",
        help="Which Bloomreach Account ID to use",
        type=str,
        default=getenv("BR_ACCOUNT_ID"),
        required=not getenv("BR_ACCOUNT_ID")
    )

    parser.add_argument(
        "--br-catalog-name",
        help="Which Bloomreach Catalog Name to index",
        type=str,
        default=getenv("BR_CATALOG_NAME"),
        required=not getenv("BR_CATALOG_NAME")
    )

    parser.add_argument(
        "--br-api-token",
        help="The BR API bearer token",
        type=str,
        default=getenv("BR_API_TOKEN"),
        required=not getenv("BR_API_TOKEN")
    )

    args = parser.parse_args()

    run_index(
        account_id=args.br_account_id,
        environment_name=args.br_environment,
        catalog_name=args.br_catalog_name,
        token=args.br_api_token
    )