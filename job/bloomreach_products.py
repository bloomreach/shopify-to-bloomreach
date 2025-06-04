import logging
import gzip
import json
import jsonlines
import re
import unicodedata
from os import getenv
from collections import defaultdict

logger = logging.getLogger(__name__)

PRODUCT_MAPPINGS = [
  ["sp.vendor", "brand", lambda x: x],
  ["sp.descriptionHtml", "description", lambda x: x.strip()],
  ["sp.title", "title", lambda x: x]
]

def normalize_key(key):
  """
  Normalize key to match Bloomreach requirements:
  - Alphanumeric, space, or underscore only
  - Cannot start with digit or space
  - De-accentize special characters
  - Convert unsupported chars to underscore
  - Remove multiple consecutive underscores
  """
  # First, de-accentize the string
  normalized = unicodedata.normalize('NFKD', key).encode('ASCII', 'ignore').decode('ASCII')

  # Replace any non-alphanumeric characters with underscore
  normalized = re.sub(r'[^a-zA-Z0-9\s]', '_', normalized)

  # Replace spaces with underscore
  normalized = normalized.replace(' ', '_')

  # Remove multiple consecutive underscores
  normalized = re.sub(r'_+', '_', normalized)

  # Remove leading/trailing underscores
  normalized = normalized.strip('_')

  # If starts with digit, prepend with underscore
  if normalized and normalized[0].isdigit():
    normalized = f"_{normalized}"

  # If empty or None, use fallback
  if not normalized:
    normalized = "attribute"

  return normalized

def is_empty_value(value):
  """Check if a value should be considered empty."""
  if value is None:
    return True
  if isinstance(value, str) and value.strip() == "":
    return True
  if isinstance(value, (list, dict)) and not value:
    return True
  return False

def extract_id_from_gid(gid):
  """Extract numeric ID from Shopify GID."""
  if gid and isinstance(gid, str) and "gid://" in gid:
    try:
      return gid.split('/')[-1]
    except IndexError:
      return gid
  return gid

def convert_to_float(value):
  """Convert string price to float, handling None values."""
  if value is None:
    return None
  try:
    return float(value)
  except (ValueError, TypeError):
    return None

def flatten_dict(d, parent_key='', sep='_'):
  items = []
  for k, v in d.items():
    new_key = f"{parent_key}{sep}{k}" if parent_key else k
    new_key = normalize_key(new_key)

    if isinstance(v, dict):
      flattened = flatten_dict(v, new_key, sep=sep)
      # Only add non-empty flattened values
      items.extend((normalize_key(key), value) for key, value in flattened.items()
                   if not is_empty_value(value))
    elif isinstance(v, list):
      if len(v) > 0 and isinstance(v[0], dict):
        # Create a dictionary to hold grouped values
        grouped_values = defaultdict(list)
        for item in v:
          if isinstance(item, dict):
            for field_key, field_value in item.items():
              if not is_empty_value(field_value):
                grouped_values[field_key].append(field_value)

        # Add each grouped array to items if not empty
        for field_key, field_values in grouped_values.items():
          if field_values:  # Only add if the array is not empty
            normalized_key = normalize_key(f"{new_key}_{field_key}")
            items.append((normalized_key, field_values))
      elif v:  # Only add non-empty arrays
        items.append((new_key, v))
    else:
      # Convert price-related fields to float
      if isinstance(v, str) and any(price_key in new_key for price_key in ['amount', 'price']):
        v = convert_to_float(v)

      # Only add non-empty values
      if not is_empty_value(v):
        items.append((new_key, v))

  return dict(items)

def clean_attributes(attrs):
  """Remove empty values from attributes dictionary and normalize keys."""
  return {normalize_key(k): v for k, v in attrs.items() if not is_empty_value(v)}

def create_products(fp, shopify_url, market_data=None, shopify_market=None, shopify_language=None):
  """
  Modified create_products function that incorporates market data in the required format.
  Also uses specific market and language when provided to set the base URL.
  """
  products = []

  with gzip.open(fp, 'rb') as file:
    for line in file:
      product = create_product(json.loads(line), shopify_url)

      # If we have market data, try to merge it
      if market_data is not None:
        # Get the full GID format product ID
        product_id = product['attributes'].get('sp_id')
        if product_id and product_id in market_data:
          # Extract market data
          markets_info = market_data[product_id]['markets']

          # Create arrays of market names and handles
          product['attributes']['sp_markets'] = [market['name'] for market in markets_info]
          product['attributes']['sp_markets_handle'] = [market['handle'] for market in markets_info]

          # Add URL attributes for each market/locale combination
          product_handle = product['attributes'].get('sp_handle')
          if product_handle:
            for market in markets_info:
              market_handle = market['handle']
              if 'rootUrls' in market:
                for root_url in market['rootUrls']:
                  locale = root_url.get('locale')
                  url = root_url.get('url')
                  if locale and url:
                    # Create the attribute with the specified format
                    attr_name = f"sp_market_{market_handle}_{locale}_url"
                    product['attributes'][attr_name] = f"{url}products/{product_handle}"

          # If specific market and language are provided, update the main URL
          if shopify_market and shopify_language:
            for market in markets_info:
              if market['handle'] == shopify_market and 'rootUrls' in market:
                for root_url in market['rootUrls']:
                  if root_url.get('locale') == shopify_language:
                    base_url = root_url.get('url', '').rstrip('/')
                    if base_url:
                      product['attributes']['url'] = f"{base_url}/products/{product_handle}"
                      break

          logger.debug(f"Added market data for product {product_id}")
        else:
          logger.debug(f"No market data found for product {product_id}")

      products.append(product)

  return products

def create_product(product, shopify_url):
  out_product = {
    "id": product["id"],
    "attributes": product["attributes"].copy(),
    "variants": {}
  }

  # Flatten all attributes at the product level
  flattened_attributes = flatten_dict(out_product["attributes"])
  out_product["attributes"] = flattened_attributes

  # container for input product attributes
  in_pa = product["attributes"]

  # container for the transformed product attributes and variants
  out_pa = out_product["attributes"]

  # Set URL
  out_pa["url"] = f"https://{shopify_url}/products/" + in_pa["sp.handle"]

  # Set availability
  if in_pa["sp.status"] == "ACTIVE" and "sp.totalInventory" in in_pa and in_pa["sp.totalInventory"] > 0:
    out_pa["availability"] = True
  else:
    out_pa["availability"] = False

  # Set thumb_image from featured image
  featured_image_key = normalize_key("sp.featuredImage.url")
  if featured_image_key in out_pa:
    out_pa["thumb_image"] = out_pa[featured_image_key]

  # Process product level mappings
  for mapping in PRODUCT_MAPPINGS:
    source, dest, func = mapping[0], mapping[1], mapping[2]
    normalized_source = normalize_key(source)
    if normalized_source in out_pa:
      value = func(out_pa[normalized_source])
      if not is_empty_value(value):
        out_pa[normalize_key(dest)] = value

  # Process variants
  if "variants" in product and product["variants"]:
    processed_variants = {}
    for v_id, variant in product["variants"].items():
      # Determine variant key (prefer SKU, fallback to cleaned ID)
      variant_attrs = variant["attributes"]
      if "sv.sku" in variant_attrs and variant_attrs["sv.sku"]:
        variant_key = variant_attrs["sv.sku"]
      else:
        variant_key = extract_id_from_gid(variant_attrs.get("sv.id"))

      # Flatten variant attributes
      flattened_variant_attrs = flatten_dict(variant_attrs)
      if not flattened_variant_attrs:  # Skip variants with no attributes
        continue

      processed_variants[variant_key] = {
        "attributes": flattened_variant_attrs
      }

      # Handle variant-specific logic
      variant_attrs = processed_variants[variant_key]["attributes"]

      # Price handling with float conversion
      compare_price_key = normalize_key("sv.compareAtPrice")
      price_key = normalize_key("sv.price")

      if compare_price_key in variant_attrs and variant_attrs[compare_price_key]:
        compare_price = convert_to_float(variant_attrs[compare_price_key])
        variant_price = convert_to_float(variant_attrs[price_key])

        if compare_price and variant_price:  # Only process if both prices are valid
          if compare_price == variant_price:
            variant_attrs["price"] = compare_price
          else:
            variant_attrs["price"] = compare_price
            variant_attrs["sale_price"] = variant_price
      elif price_key in variant_attrs:
        price = convert_to_float(variant_attrs[price_key])
        if price:  # Only add if price is valid
          variant_attrs["price"] = price

      # Set thumb_image for variant
      image_url_key = normalize_key("sv.image.url")
      if image_url_key in variant_attrs:
        variant_attrs["thumb_image"] = variant_attrs[image_url_key]

      # Availability
      available_key = normalize_key("sv.availableForSale")
      variant_attrs["availability"] = False
      if available_key in variant_attrs and variant_attrs[available_key]:
        variant_attrs["availability"] = True

      # Clean empty values from variant attributes
      variant_attrs = clean_attributes(variant_attrs)
      if not variant_attrs:  # Skip variant if no attributes remain
        continue
      processed_variants[variant_key]["attributes"] = variant_attrs

    # Only add non-empty variants
    out_product["variants"] = {k: v for k, v in processed_variants.items()
                               if v["attributes"]}

    # Set root level price range if available
    min_price = None
    max_price = None
    for variant in out_product["variants"].values():
      variant_price = variant["attributes"].get("price")
      if variant_price is not None:
        if min_price is None or variant_price < min_price:
          min_price = variant_price
        if max_price is None or variant_price > max_price:
          max_price = variant_price

    if min_price is not None:
      out_pa["price"] = min_price
    if max_price is not None and max_price != min_price:
      out_pa["price_range_max"] = max_price

  # Final cleanup of product attributes
  out_product["attributes"] = clean_attributes(out_pa)

  return out_product

def load_market_data(input_file):
  """
  Load and process market data from the JSONL file.
  """
  # Initialize data structures
  products = defaultdict(lambda: {"handle": "", "title": "", "markets": []})
  markets_by_publication = {}
  urls_by_market = {}

  try:
    # First pass: collect all markets and URLs
    with gzip.open(input_file, 'r') as file:
      for line in file:
        data = json.loads(line.strip())

        # Handle market entries
        if data.get("id", "").startswith("gid://shopify/Market/"):
          markets_by_publication[data["__parentId"]] = {
            "id": data["id"],
            "handle": data["handle"],
            "name": data["name"]
          }

        # Handle rootUrl entries
        elif "rootUrls" in data:
          urls_by_market[data["__parentId"]] = data["rootUrls"]

    # Second pass: process products
    with gzip.open(input_file, 'r') as file:
      for line in file:
        data = json.loads(line.strip())

        # Handle product entries
        if data.get("id", "").startswith("gid://shopify/Product/"):
          product_id = data["id"]
          publication_id = data["__parentId"]

          # Update basic product info
          products[product_id]["handle"] = data["handle"]
          products[product_id]["title"] = data.get("title", "")

          # Get market info for this publication
          market_info = markets_by_publication.get(publication_id)
          if market_info:
            market_id = market_info["id"]
            market_data = {
              "handle": market_info["handle"],
              "name": market_info["name"]
            }

            # Add rootUrls if available
            urls = urls_by_market.get(market_id)
            if urls:
              market_data["rootUrls"] = urls

            # Check if we already have this market
            if not any(m["handle"] == market_data["handle"] for m in products[product_id]["markets"]):
              products[product_id]["markets"].append(market_data)

    # Create final result
    result = {}
    for product_id, info in products.items():
      if info["markets"]:  # Only include products with markets
        # Sort markets by handle
        info["markets"].sort(key=lambda x: x["handle"])
        result[product_id] = info

    return result

  except Exception as e:
    logger.error(f"Error processing market data: {str(e)}")
    raise

def main(fp_in, fp_out, shopify_url, market_data_fp=None, shopify_market=None, shopify_language=None):
  """
  Modified main function that handles optional market data processing.

  Args:
      fp_in: Input file path for generic products
      fp_out: Output file path for processed products
      shopify_url: Shopify shop URL
      market_data_fp: Optional file path for market data
  """
  # Load market data if provided
  market_data = None
  if market_data_fp:
    logger.info(f"Loading market data from {market_data_fp}")
    try:
      market_data = load_market_data(market_data_fp)
    except Exception as e:
      logger.error(f"Failed to load market data: {str(e)}")
      # Continue without market data if loading fails
      pass

  # Process products with optional market data
  patch = create_products(fp_in, shopify_url, market_data, shopify_market, shopify_language)

  # Write processed products to output file
  with gzip.open(fp_out, "wb") as file:
    writer = jsonlines.Writer(file)
    for object in patch:
      writer.write(object)
    writer.close()

  logger.info(f"Processed {len(patch)} products")

if __name__ == '__main__':
  import argparse
  from os import getenv
  from sys import stdout

  # Define logger
  loglevel = getenv('LOGLEVEL', 'INFO').upper()
  logging.basicConfig(
    stream=stdout,
    level=loglevel,
    format="%(name)-12s %(asctime)s %(levelname)-8s %(filename)s:%(funcName)s %(message)s"
  )

  parser = argparse.ArgumentParser(
    description="Transforms generic products with custom logic specific to an individual catalog."
  )

  parser.add_argument(
    "--input-file",
    help="File path of Generic Products jsonl",
    type=str,
    default=getenv("BR_INPUT_FILE"),
    required=not getenv("BR_INPUT_FILE")
  )

  parser.add_argument(
    "--output-file",
    help="Filename of output jsonl file",
    type=str,
    default=getenv("BR_OUTPUT_FILE"),
    required=not getenv("BR_OUTPUT_FILE")
  )

  parser.add_argument(
    "--shopify-url",
    help="Hostname of the shopify Shop, e.g. xyz.myshopify.com.",
    type=str,
    default=getenv("BR_SHOPIFY_URL"),
    required=not getenv("BR_SHOPIFY_URL")
  )

  parser.add_argument(
    "--market-data",
    help="Optional: File path to market data JSONL file",
    type=str,
    default=None
  )

  args = parser.parse_args()
  fp_in = args.input_file
  fp_out = args.output_file
  shopify_url = args.shopify_url
  market_data_fp = args.market_data

  main(fp_in, fp_out, shopify_url, market_data_fp)