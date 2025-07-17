# script.py
import logging
from datetime import datetime
from os import getenv
from sys import stdout
import argparse
import gzip

from bloomreach_generics import main as brGenerics
from bloomreach_products import main as brProducts
from feed import patch_catalog, patch_catalog_delta
from shopify_products import main as shopifyProducts
from patch import main as brPatch
from graphql import get_shopify_jsonl_fp
from index import run_index

# Define logger
loglevel = getenv('LOGLEVEL', 'INFO').upper()
logging.basicConfig(
  stream=stdout,
  level=loglevel,
  format="%(name)-12s %(asctime)s %(levelname)-8s %(filename)s:%(funcName)s %(message)s"
)

def main(shopify_url="",
         shopify_pat="",
         br_account_id="",
         br_catalog_name="",
         br_environment="",
         br_api_token="",
         output_dir="/export",
         multi_market=False,
         shopify_market=None,
         shopify_language=None,
         auto_index=False,
         delta_mode=False,
         start_date=None,
         market_cache_enabled=False,
         market_cache_max_age_hours=24):

  run_num = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
  api_version = '2025-04'

  # Add timezone debugging - fix the datetime usage
  now_utc = datetime.utcnow()  # Remove the extra .datetime
  now_local = datetime.now()   # Remove the extra .datetime

  logging.info(f"Container UTC time: {now_utc}")
  logging.info(f"Container local time: {now_local}")
  logging.info(f"Time difference: {(now_local - now_utc).total_seconds()} seconds")

  # Log delta mode info
  if delta_mode:
    logging.info(f"Running in DELTA mode with start_date: {start_date}")
    # Parse and log the start_date for verification
    try:
      parsed_start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
      logging.info(f"Parsed start_date as UTC: {parsed_start}")
      logging.info(f"Time since start_date: {(now_utc - parsed_start.replace(tzinfo=None)).total_seconds()} seconds")
    except Exception as e:
      logging.error(f"Failed to parse start_date: {e}")
  else:
    logging.info("Running in FULL mode")

  logging.info(f"run_num: {run_num}")
  logging.info(f"api_version: {api_version}")
  logging.info(f"shopify_url: {shopify_url}")
  logging.info(f"shopify_pat: {'*' * len(shopify_pat) if shopify_pat else 'not set'}")
  logging.info(f"br_account_id: {br_account_id}")
  logging.info(f"br_catalog_name: {br_catalog_name}")
  logging.info(f"br_environment: {br_environment}")
  logging.info(f"br_api_token: {'*' * len(br_api_token) if br_api_token else 'not set'}")
  logging.info(f"output_dir: {output_dir}")
  logging.info(f"multi_market: {multi_market}")
  if multi_market:
    logging.info(f"shopify_market: {shopify_market}")
    logging.info(f"shopify_language: {shopify_language}")

  if multi_market:
    shopify_jsonl_fp, market_jsonl_fp, job_id = get_shopify_jsonl_fp(
      shopify_url, api_version, shopify_pat, output_dir,
      run_num=run_num, multiMarket=True,
      shopify_market=shopify_market,
      shopify_language=shopify_language,
      start_date=start_date if delta_mode else None,
      market_cache_enabled=market_cache_enabled,
      market_cache_max_age_hours=market_cache_max_age_hours
    )
  else:
    shopify_jsonl_fp, job_id = get_shopify_jsonl_fp(
      shopify_url, api_version, shopify_pat, output_dir,
      run_num=run_num,
      start_date=start_date if delta_mode else None
    )

  try:
    with gzip.open(shopify_jsonl_fp, 'rb') as f:
      first_line = f.readline()
      if not first_line:
        logging.info("No products to process in delta feed, exiting successfully")
        return
  except Exception as e:
    logging.error("Failed to check if products file is empty: %s", e)
    return

  shopify_products_fp = f"{output_dir}/{run_num}_{job_id}_1_shopify_products.jsonl"
  generic_products_fp = f"{output_dir}/{run_num}_{job_id}_2_generic_products.jsonl"
  br_products_fp = f"{output_dir}/{run_num}_{job_id}_3_br_products.jsonl"
  br_patch_fp = f"{output_dir}/{run_num}_{job_id}_4_br_patch.jsonl"

  shopifyProducts(shopify_jsonl_fp, shopify_products_fp)
  brGenerics(shopify_products_fp,
             generic_products_fp,
             pid_props="handle",
             vid_props="sku,id")
  if multi_market:
    brProducts(generic_products_fp, br_products_fp, shopify_url,
               market_data_fp=market_jsonl_fp,
               shopify_market=shopify_market,
               shopify_language=shopify_language)
  else:
    brProducts(generic_products_fp, br_products_fp, shopify_url)

  # Use PATCH for delta mode, PUT for full mode
  if delta_mode:
    # Import patch_catalog_delta if we need different behavior
    # For now, patch_catalog should work for both
    pass

  brPatch(br_products_fp, br_patch_fp)

  if delta_mode:
    logging.info("Using PATCH for delta feed")
    patch_catalog_delta(br_patch_fp,
                        account_id=br_account_id,
                        environment_name=br_environment,
                        catalog_name=br_catalog_name,
                        token=br_api_token)
  else:
    logging.info("Using PUT for full feed")
    patch_catalog(br_patch_fp,
                  account_id=br_account_id,
                  environment_name=br_environment,
                  catalog_name=br_catalog_name,
                  token=br_api_token)

  # Add auto-indexing after successful feed upload
  if auto_index:
      logging.info("Auto-index enabled, triggering index job...")
      run_index(
          account_id=br_account_id,
          environment_name=br_environment,
          catalog_name=br_catalog_name,
          token=br_api_token
      )

# Update the validate_required_vars function:
def validate_required_vars():
  required_vars = {
    'SHOPIFY_URL': 'Shopify URL is required',
    'SHOPIFY_PAT': 'Shopify PAT token is required',
    'BR_ENVIRONMENT_NAME': 'Bloomreach environment is required',
    'BR_ACCOUNT_ID': 'Bloomreach account ID is required',
    'BR_CATALOG_NAME': 'Bloomreach catalog name is required',
    'BR_API_TOKEN': 'Bloomreach API token is required',
    'BR_OUTPUT_DIR': 'Output directory is required'
  }

  # Check if multi-market is enabled
  multi_market = getenv('BR_MULTI_MARKET')
  if multi_market and multi_market.lower() == 'true':
    required_vars.update({
      'SHOPIFY_MARKET': 'Shopify market is required when multi-market is enabled',
      'SHOPIFY_LANGUAGE': 'Shopify language is required when multi-market is enabled'
    })

  missing_vars = []
  for var, message in required_vars.items():
    if not getenv(var):
      missing_vars.append(f"{var}: {message}")

  if missing_vars:
    for msg in missing_vars:
      logging.error(msg)
    raise SystemExit(1)

    # Validate BR_ENVIRONMENT_NAME value
  br_env = getenv('BR_ENVIRONMENT_NAME')
  valid_environments = ['staging', 'production']
  if br_env.lower() not in valid_environments:
    logging.error(f"BR_ENVIRONMENT_NAME must be one of: {', '.join(valid_environments)}")
    raise SystemExit(1)

  # Validate BR_ACCOUNT_ID format
  account_id = getenv('BR_ACCOUNT_ID')
  if not account_id.isdigit() or len(account_id) != 4:
    logging.error("BR_ACCOUNT_ID must be exactly 4 digits")
    raise SystemExit(1)

if __name__ == '__main__':
  # Validate environment variables first
  validate_required_vars()

  parser = argparse.ArgumentParser(
    description="Extracts a full set of products and their categories from the shopify store and runs a full feed into a Bloomreach Discovery catalog.\n \nUses Shopify's GraphQL Bulk Operation API.\n \nDuring processing, it will save the Shopify bulk operation output jsonl file locally named with the BulkOperation ID value.\n \n From there, the file will run through different transforms to create a Bloomreach patch that is then run in full feed mode via the BR Feed API.\n \nEach transform step will save its intermediate output locally as well for debugging purposes prefixed with a step number.\n \nFor example:\n23453245234_0.jsonl\n23453245234_1_shopify_products.jsonl\n23453245234_2_generic_products.jsonl\n23453245234_3_br_products.jsonl\n23453245234_4_br_patch.jsonl"
  )

  parser.add_argument(
    "--multi-market",
    help="Enable multi-market product data export",
    action="store_true",
    default=False
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
    "--br-environment",
    help="Which Bloomreach Account environment to send catalog data to",
    type=str,
    default=getenv("BR_ENVIRONMENT_NAME"),
    required=not getenv("BR_ENVIRONMENT_NAME")
  )

  parser.add_argument(
    "--br-account-id",
    help="Which Bloomreach Account ID to send catalog data to",
    type=str,
    default=getenv("BR_ACCOUNT_ID"),
    required=not getenv("BR_ACCOUNT_ID")
  )

  parser.add_argument(
    "--br-catalog-name",
    help="Which Bloomreach Catalog Name to send catalog data to.\nThis is the same as the value of domain_key parameter in Search API requests.",
    type=str,
    default=getenv("BR_CATALOG_NAME"),
    required=not getenv("BR_CATALOG_NAME")
  )

  parser.add_argument(
    "--br-api-token",
    help="The BR Feed API bearer token",
    type=str,
    default=getenv("BR_API_TOKEN"),
    required=not getenv("BR_API_TOKEN")
  )

  parser.add_argument(
    "--output-dir",
    help="Directory path to store the output files to",
    type=str,
    default=getenv("BR_OUTPUT_DIR"),
    required=not getenv("BR_OUTPUT_DIR")
  )

  # New arguments for multi-market support
  parser.add_argument(
    "--shopify-market",
    help="Shopify market code (required when --multi-market is used)",
    type=str,
    default=getenv("SHOPIFY_MARKET")
  )

  parser.add_argument(
    "--shopify-language",
    help="Shopify language code (required when --multi-market is used)",
    type=str,
    default=getenv("SHOPIFY_LANGUAGE")
  )

  parser.add_argument(
    "--auto-index",
    help="Automatically trigger index job after successful feed upload",
    action="store_true",
    default=False
  )

  parser.add_argument(
    "--delta-mode",
    help="Run in delta mode for incremental updates",
    action="store_true",
    default=False
  )

  parser.add_argument(
    "--start-date",
    help="Start date for delta mode (ISO format)",
    type=str,
    default=None
  )

  parser.add_argument(
    "--market-cache-enabled",
    help="Enable market data caching for delta feeds",
    action="store_true",
    default=False
  )

  parser.add_argument(
    "--market-cache-max-age-hours",
    help="Maximum age of market data cache in hours",
    type=int,
    default=24
  )

  args = parser.parse_args()
  shopify_url = args.shopify_url
  shopify_pat = args.shopify_pat
  environment = args.br_environment
  account_id = args.br_account_id
  catalog_name = args.br_catalog_name
  api_token = args.br_api_token
  output_dir = args.output_dir
  multi_market = args.multi_market  # New argument
  delta_mode = getenv("DELTA_MODE", "false").lower() == "true" or args.delta_mode
  start_date = getenv("START_DATE") or args.start_date
  auto_index = getenv("AUTO_INDEX", "false").lower() == "true" or args.auto_index
  market_cache_enabled = getenv("MARKET_CACHE_ENABLED", "false").lower() == "true" or args.market_cache_enabled
  market_cache_max_age_hours = int(getenv("MARKET_CACHE_MAX_AGE_HOURS", "24")) or args.market_cache_max_age_hours

  if args.multi_market:
    if not args.shopify_market:
      parser.error("--shopify-market is required when --multi-market is enabled")
    if not args.shopify_language:
      parser.error("--shopify-language is required when --multi-market is enabled")

  main(shopify_url=shopify_url,
       shopify_pat=shopify_pat,
       br_environment=environment,
       br_account_id=account_id,
       br_catalog_name=catalog_name,
       br_api_token=api_token,
       output_dir=output_dir,
       multi_market=multi_market,
       shopify_market=args.shopify_market,
       shopify_language=args.shopify_language,
       auto_index=auto_index,
       delta_mode=delta_mode,
       start_date=start_date,
       market_cache_enabled=market_cache_enabled,
       market_cache_max_age_hours=market_cache_max_age_hours)