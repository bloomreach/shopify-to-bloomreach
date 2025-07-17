import gzip
import json
import logging
import polling
import requests
import shopify
import shutil
from os import getenv
from pathlib import Path
from datetime import datetime, timedelta
import os

logger = logging.getLogger(__name__)


def export_jsonl(context, language=None, start_date=None):
  """
  Attempts to run a Bulk Operation query to initiate a job
  that will extract a JSONL file with all of a Shop's product information.

  Args:
      context: Dictionary to store job information
      language: Optional language code for translations
      start_date: Optional start date for delta queries (ISO format)

  Returns:
      bool: True if job was submitted successfully, False otherwise
  """
  if language:
    logger.info("ExportDataJob using language: %s", language)

  # Choose which query file to use based on parameters - handle all combinations
  if start_date and language:
    query_file = 'export_data_job_delta_translations.graphql'
    logger.info("ExportDataJob using delta mode with translations, start_date: %s, language: %s", start_date, language)
  elif start_date:
      query_file = 'export_data_job_delta.graphql'
      logger.info("ExportDataJob using delta mode with start_date: %s", start_date)
  elif language:
      query_file = 'export_data_job_translations.graphql'
      logger.info("ExportDataJob using translations with language: %s", language)
  else:
      query_file = 'export_data_job.graphql'
      logger.info("ExportDataJob using standard mode")

  query = Path(f'./graphql_queries/{query_file}').read_text()

  # Replace template variables
  if language:
    query = query.replace("{language}", language)
  if start_date:
    query = query.replace("{start_date}", start_date)

  logger.info("ExportDataJob graph ql query:\n %s", query)
  logger.info("ExportDataJob attempt using query file: %s", query_file)

  result = shopify.GraphQL().execute(query=query, operation_name="ExportDataJob")
  result_json = json.loads(result)

  if 'errors' in result_json:
    raise RuntimeError("Errors encountered while running ExportDataJob query")

  bulkOperation = result_json["data"]["bulkOperationRunQuery"]["bulkOperation"]

  # If bulkOperation object is None, then the job wasn't submitted successfully
  if bulkOperation is not None:
    job_id = bulkOperation['id']
    logger.info("GraphQL Bulk Operation submitted successfully. Job id: %s", job_id)
    context["job_id"] = job_id
    return True
  elif "already in progress" in result:
    logger.info("GraphQL Bulk Operation not submitted, trying again after delay. Another operation already in progress: %s", result_json)
    return False
  else:
    logger.error(result_json)
    raise RuntimeError("Unable to start ExportDataJob")


def export_market_jsonl(context):
  """
  Similar to export_jsonl but specifically for market data.
  Uses a different GraphQL query to fetch market-specific product mappings.
  """
  query = Path('./graphql_queries/market_products_job.graphql').read_text()
  logger.info("MarketProductsJob attempt")
  try:
    result = shopify.GraphQL().execute(query=query,
                                       operation_name="MarketProductsJob")
    result_json = json.loads(result)

    # Log the full error response for debugging
    if 'errors' in result_json:
      logger.error("GraphQL Errors:")
      for error in result_json['errors']:
        logger.error(f"Error: {json.dumps(error, indent=2)}")
      raise RuntimeError(f"Errors encountered while running MarketProductsJob query: {result_json['errors']}")

    bulkOperation = result_json["data"]["bulkOperationRunQuery"]["bulkOperation"]

    if bulkOperation is not None:
      job_id = bulkOperation['id']
      logger.info("GraphQL Market Bulk Operation submitted successfully. Job id: %s", job_id)
      context["market_job_id"] = job_id
      return True
    elif "already in progress" in result:
      logger.info("GraphQL Market Bulk Operation not submitted, trying again after delay. Another operation already in progress: %s", result_json)
      return False
    else:
      logger.error(f"Unexpected response: {json.dumps(result_json, indent=2)}")
      raise RuntimeError("Unable to start MarketProductsJob")

  except Exception as e:
    logger.error(f"Exception in export_market_jsonl: {str(e)}")
    logger.error(f"Query being executed: {query}")
    raise

def get_jsonl_url(job_id, context):
  """
  Given a Bulk Operation job id, polls for status and objectCount.

  Executes GraphQL Bulk Operation queries for a given job.

  If job is still in progress, returns False.

  If job is completed successfully, returns True with jsonl url added to context.

  If job does not complete successfully, raises a RuntimeError.

  https://shopify.dev/api/usage/bulk-operations/queries#option-b-poll-a-running-bulk-operation
  """
  query = Path('./graphql_queries/get_job.graphql').read_text()
  logger.info("GetJob query for job_id: %s" % job_id)
  result = shopify.GraphQL().execute(query=query,
                                     operation_name="GetJob",
                                     variables={"job_id": job_id})
  result_json = json.loads(result)

  if 'errors' in result_json:
    raise RuntimeError("Errors encountered while running ExportDataJob query")

  node = result_json["data"]["node"]
  state = node["status"]
  object_count = node["objectCount"]
  url = node["url"]

  logger.info("GraphQL Bulk Operation current state: %s", state)
  logger.info("GraphQL Bulk Operation objectCount: %s", object_count)

  # https://shopify.dev/api/admin-graphql/2023-01/enums/bulkoperationstatus
  if state == "COMPLETED":
    # Handle case where no products were found (url will be None)
    if object_count == 0 or url is None:
      logger.warning("GraphQL Bulk Operation completed but found no products (objectCount: %s, url: %s)", object_count, url)
      context["url"] = None
      context["object_count"] = object_count
    else:
      logger.info("GraphQL Bulk Operation completed successfully, jsonl at url: %s", url)
      logger.info("GraphQL Bulk Operation objectCount: %s", object_count)
      context["url"] = url
      context["object_count"] = object_count
    return True

  if state in ["CANCELED", "CANCELING", "EXPIRED", "FAILED"]:
    logger.error("GraphQL Bulk Operation did not complete successfully: %s, %s", job_id, state)
    raise RuntimeError("Full feed job did not complete successfully")

  logger.info("GraphQL Bulk Operation current objectCount: %s", object_count)

  return False


def download_file(url, local_filename):
  with requests.get(url, stream=True) as r:
    r.raise_for_status()
    with gzip.open(local_filename, 'wb') as f:
      for chunk in r.iter_content(chunk_size=8192):  # Stream in small chunks
        f.write(chunk)
  return local_filename

def get_market_cache_path(output_dir):
  return f"{output_dir}/market_data_cache.json"

def is_market_cache_valid(cache_path, max_age_hours=24):
  """Check if market data cache is still valid."""
  if not os.path.exists(cache_path):
    return False

  cache_age = datetime.now() - datetime.fromtimestamp(os.path.getmtime(cache_path))
  return cache_age < timedelta(hours=max_age_hours)

def save_market_cache_info(cache_path, market_file_path):
  """Save metadata about the cached market data."""
  cache_info = {
    "cached_at": datetime.now().isoformat(),
    "market_file": os.path.basename(market_file_path)
  }
  info_path = cache_path.replace('.json', '_info.json')
  with open(info_path, 'w') as f:
    json.dump(cache_info, f)

def get_cached_market_file(output_dir, max_age_hours=24):
  """Get the path to cached market data if it exists and is valid."""
  cache_path = get_market_cache_path(output_dir)
  if is_market_cache_valid(cache_path, max_age_hours):
    return cache_path
  return None

def get_shopify_jsonl_fp(shop_url, api_version, token, output_dir, run_num="",
                         multiMarket=False, shopify_market=None, shopify_language=None,
                         start_date=None, market_cache_enabled=True, market_cache_max_age_hours=24):
  """
  Downloads product data from Shopify using bulk operations.
  For delta feeds with multiMarket, uses cached market data if available and caching is enabled.

  Args:
      shop_url: Shopify shop URL
      api_version: Shopify API version
      token: Shopify access token
      output_dir: Directory to save output files
      run_num: Optional run number for file naming
      multiMarket: If True, also downloads market-specific product data
      shopify_market: Optional market code (required if multiMarket is True)
      shopify_language: Optional language code (required if multiMarket is True)
      start_date: Optional start date for delta queries (ISO format string)
      market_cache_enabled: Whether to use market data caching
      market_cache_max_age_hours: Maximum age of cached market data in hours

  Returns:
      If multiMarket is False:
          Tuple of (products_file_path, job_id)
      If multiMarket is True:
          Tuple of (products_file_path, market_file_path, job_id)
  """
  session = shopify.Session(shop_url, api_version, token)
  shopify.ShopifyResource.activate_session(session)

  # Submit job for main product export
  context = {}
  polling.poll(
    lambda: export_jsonl(context, language=shopify_language if multiMarket else None, start_date=start_date),
    step=20,
    timeout=7200
  )
  job_id = context["job_id"]

  # Get main product jsonl url
  context = {}
  polling.poll(lambda: get_jsonl_url(job_id, context), step=20, timeout=7200)
  jsonl_url = context["url"]
  logger.info("products jsonl url: %s", jsonl_url)
  object_count = context.get("object_count", 0)
  job_id_short = job_id.split('/')[-1]

  # Download main product file with run_num
  products_jsonl_fp = f"{output_dir}/{run_num}_shopify_bulk_op.jsonl.gz"

  if jsonl_url is None or object_count == 0:
    logger.info("No products found for query, creating empty file: %s", products_jsonl_fp)
    # Create an empty gzipped JSONL file
    with gzip.open(products_jsonl_fp, 'wb') as f:
      pass  # Create empty file
  else:
    logger.info("Saving products jsonl file to: %s", products_jsonl_fp)
    download_file(jsonl_url, products_jsonl_fp)

  market_jsonl_fp = None
  if multiMarket:
      # Check if we can use cached market data (for delta feeds and if caching is enabled)
      cached_market_file = None
      if start_date and market_cache_enabled:  # This is a delta feed and caching is enabled
        cached_market_file = get_cached_market_file(output_dir, market_cache_max_age_hours)

      if cached_market_file:
          # Use cached market data
          market_jsonl_fp = f"{output_dir}/{run_num}_shopify_market_bulk_op.jsonl.gz"
          # Copy cached file to new filename
          shutil.copy2(cached_market_file, market_jsonl_fp)
          logger.info("Using cached market data: %s (age: %.1f hours)",
                     cached_market_file,
                     (datetime.now() - datetime.fromtimestamp(os.path.getmtime(cached_market_file))).total_seconds() / 3600)
      else:
          # Fetch fresh market data
          if start_date and market_cache_enabled:
            logger.info("Market data cache miss or expired, fetching fresh data")
          elif start_date:
            logger.info("Market data caching disabled, fetching fresh data")
          else:
            logger.info("Full feed mode, fetching fresh market data")

          # Submit job for market data export
          market_context = {}
          polling.poll(lambda: export_market_jsonl(market_context), step=20, timeout=7200)
          market_job_id = market_context["market_job_id"]

          # Get market data jsonl url
          market_context = {}
          polling.poll(lambda: get_jsonl_url(market_job_id, market_context), step=20, timeout=7200)
          market_jsonl_url = market_context["url"]
          market_object_count = market_context.get("object_count", 0)

          # Download market data file with run_num
          market_jsonl_fp = f"{output_dir}/{run_num}_shopify_market_bulk_op.jsonl.gz"

          if market_jsonl_url is None or market_object_count == 0:
            logger.info("No market data found, creating empty file: %s", market_jsonl_fp)
            with gzip.open(market_jsonl_fp, 'wb') as f:
              pass  # Create empty file
          else:
            logger.info("Saving market jsonl file to: %s", market_jsonl_fp)
            download_file(market_jsonl_url, market_jsonl_fp)

            # Cache the market data for future delta feeds (if caching is enabled)
            if market_cache_enabled:
              try:
                cache_path = get_market_cache_path(output_dir)
                shutil.copy2(market_jsonl_fp, cache_path)
                save_market_cache_info(cache_path, market_jsonl_fp)
                logger.info("Cached market data for future delta feeds: %s (valid for %d hours)",
                            cache_path, market_cache_max_age_hours)
              except Exception as e:
                logger.warning("Failed to cache market data: %s", e)

  shopify.ShopifyResource.clear_session()

  if multiMarket:
    return products_jsonl_fp, market_jsonl_fp, job_id_short
  return products_jsonl_fp, job_id_short


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
    description="Extracts a full set of products and their categories from the shopify store and runs a full feed into a Bloomreach Discovery catalog.\n \n"
                "Uses Shopify's GraphQL Bulk Operation API.\n \n"
                "During processing, it will save the Shopify bulk operation output jsonl file locally named with the BulkOperation ID value.\n \n"
                "From there, the file will run through different transforms to create a Bloomreach patch that is then run in full feed mode via the BR Feed API.\n \n"
                "Each transform step will save its intermediate output locally as well for debugging purposes prefixed with a step number.\n \n"
                "For example:\n"
                "23453245234_0.jsonl\n"
                "23453245234_1_shopify_products.jsonl\n"
                "23453245234_2_generic_products.jsonl\n"
                "23453245234_3_br_products.jsonl\n"
                "23453245234_4_br_patch.jsonl"
  )

  parser.add_argument(
    "--shopify-url",
    help="Hostname of the shopify Shop, e.g. xyz.myshopify.com.",
    type=str,
    default=getenv("BR_SHOPIFY_URL"),
    required=not getenv("BR_SHOPIFY_URL")
  )

  parser.add_argument(
    "--shopify-pat",
    help="Shopify PAT token, e.g shpat_casdcaewras82342dczasdf3",
    type=str,
    default=getenv("BR_SHOPIFY_PAT"),
    required=not getenv("BR_SHOPIFY_PAT")
  )

  parser.add_argument(
    "--output-dir",
    help="Directory path to store the output files to",
    type=str,
    default=getenv("BR_OUTPUT_DIR"),
    required=not getenv("BR_OUTPUT_DIR")
  )

  parser.add_argument(
    "--multi-market",
    help="Enable multi-market product data export",
    action="store_true",
    default=False
  )

  args = parser.parse_args()
  shopify_url = args.shopify_url
  shopify_pat = args.shopify_pat
  output_dir = args.output_dir
  multi_market = args.multi_market

  result = get_shopify_jsonl_fp(shopify_url, '2025-04', shopify_pat, output_dir,
                                multiMarket=multi_market)