# script.py
import logging
from datetime import datetime
from os import getenv
from sys import stdout
import argparse

from bloomreach_generics import main as brGenerics
from bloomreach_products import main as brProducts
from feed import patch_catalog
from shopify_products import main as shopifyProducts
from patch import main as brPatch
from graphql import get_shopify_jsonl_fp

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
         shopify_language=None):


  run_num = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
  api_version = '2025-04'
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
      shopify_language=shopify_language
    )
  else:
    shopify_jsonl_fp, job_id = get_shopify_jsonl_fp(
      shopify_url, api_version, shopify_pat, output_dir,
      run_num=run_num
    )

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

  brPatch(br_products_fp, br_patch_fp)
  patch_catalog(br_patch_fp,
                account_id=br_account_id,
                environment_name=br_environment,
                catalog_name=br_catalog_name,
                token=br_api_token)

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

  args = parser.parse_args()
  shopify_url = args.shopify_url
  shopify_pat = args.shopify_pat
  environment = args.br_environment
  account_id = args.br_account_id
  catalog_name = args.br_catalog_name
  api_token = args.br_api_token
  output_dir = args.output_dir
  multi_market = args.multi_market  # New argument

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
       shopify_language=args.shopify_language)