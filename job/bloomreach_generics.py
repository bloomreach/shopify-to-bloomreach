import gzip
import json
import jsonlines
import logging
from os import getenv

logger = logging.getLogger(__name__)


def create_products_iteratively(fp_in, fp_out, pid_identifiers=None, vid_identifiers=None):
  """
  Memory-efficient version that processes one product at a time and writes directly to output.
  Does not store all products in memory.

  Args:
      fp_in: Input file path (gzipped JSONL)
      fp_out: Output file path (gzipped JSONL)
      pid_identifiers: Product identifier property names (comma-separated string)
      vid_identifiers: Variant identifier property names (comma-separated string)

  Returns:
      int: Number of products processed
  """
  product_count = 0

  # Process one line at a time and write directly to output
  with gzip.open(fp_in, 'rb') as file_in, gzip.open(fp_out, 'wb') as file_out:
    writer = jsonlines.Writer(file_out)

    for line in file_in:
      # Process each product individually
      try:
        shopify_product = json.loads(line)
        product = create_product(shopify_product, pid_identifiers, vid_identifiers)
        writer.write(product)
        product_count += 1

        # Log progress for every 100 products
        if product_count % 100 == 0:
          logger.info(f"Processed {product_count} products")

      except Exception as e:
        # Log error but continue processing
        logger.error(f"Error processing product: {str(e)}")

    writer.close()

  logger.info(f"Finished processing {product_count} products")
  return product_count


# Legacy function - kept for backward compatibility
def create_products(fp, pid_identifiers=None, vid_identifiers=None):
  """
  Legacy function that loads all products into memory.
  WARNING: This can cause memory issues with large files.
  Consider using create_products_iteratively instead.
  """
  logger.warning("Using memory-intensive create_products. Consider switching to create_products_iteratively.")
  products = []

  # stream over file and index each object in bulk output
  with gzip.open(fp, 'rb') as file:
    for line in file:
      products.append(create_product(json.loads(line), pid_identifiers, vid_identifiers))

  return products


def create_product(shopify_product, pid_identifiers=None, vid_identifiers=None):
  """
  Create a Bloomreach product from a Shopify product.

  Args:
      shopify_product: Shopify product data
      pid_identifiers: Product identifier properties
      vid_identifiers: Variant identifier properties

  Returns:
      dict: Bloomreach product structure
  """
  return {
    "id": create_id(shopify_product, identifiers=pid_identifiers),
    "attributes": create_attributes(shopify_product, "sp"),
    "variants": create_variants(shopify_product, identifiers=vid_identifiers)
  }


def create_id(shopify_object, identifiers=None):
  """
  Create an ID for a Shopify object.

  Args:
      shopify_object: Shopify object data
      identifiers: Comma-separated list of identifier properties to try

  Returns:
      str: ID value
  """
  id = "NOIDENTIFIERFOUND"
  # setup default identifiers based on common Shopify patterns
  if identifiers is None:
    identifiers = ["id"]
  else:
    identifiers = identifiers.split(",")

  for identifier in identifiers:
    if identifier in shopify_object and shopify_object[identifier]:
      id = shopify_object[identifier]
      break
    elif "id" in shopify_object:
      # If `id` isn't supplied as custom identifier, use `id` as it should always be present
      id = shopify_object["id"]

  return id


def create_variants(shopify_product, identifiers=None):
  """
  Create variants for a Bloomreach product.

  Args:
      shopify_product: Shopify product data
      identifiers: Variant identifier properties

  Returns:
      dict: Variants map
  """
  variants = {}
  if "variants" in shopify_product and shopify_product["variants"]:
    for variant in shopify_product["variants"]:
      variant = create_variant(variant, identifiers)
      variants[variant["id"]] = {"attributes": variant["attributes"]}
  return variants


def create_variant(shopify_variant, identifiers=None):
  """
  Create a Bloomreach variant from a Shopify variant.

  Args:
      shopify_variant: Shopify variant data
      identifiers: Variant identifier properties

  Returns:
      dict: Variant data with ID and attributes
  """
  return {
    "id": create_id(shopify_variant, identifiers),
    "attributes": create_attributes(shopify_variant, "sv")
  }


def create_attributes(shopify_object, namespace):
  """
  Create attributes for a Bloomreach product or variant.

  Args:
      shopify_object: Shopify object data
      namespace: Namespace prefix for attributes

  Returns:
      dict: Attributes map
  """
  # TODO: Handle all the different types of metafield value types like arrays, etc
  attributes = {}
  for k, v in shopify_object.items():
    if "variants" in k:
      continue
    if "metafields" in k:
      for metafield in v:
        # each metafield key/value added to attributes with namespace
        attribute_name = namespace + "m." + metafield["namespace"] + "." + metafield["key"]
        # This is a hacky way of doing this to cover all the list use cases
        # however, more robust value type mapping should occur based on metafield["type"]
        if "list" in metafield["type"]:
          attributes[attribute_name] = json.loads(metafield["value"])
        else:
          attributes[attribute_name] = metafield["value"]
    elif "collections" in k:
      attributes["category_paths"] = create_category_paths(v)
    else:
      # each object property added as attribute with namespace
      attributes[namespace + "." + k] = v
  return attributes


def create_category_paths(collections):
  """
  Create category paths from collections.

  Args:
      collections: Collections data

  Returns:
      list: Category paths
  """
  paths = []
  for collection in collections:
    paths.append([{"id": collection["handle"], "name": collection["title"]}])

  return paths


def main(fp_in, fp_out, pid_props, vid_props):
  """
  Main function - uses the memory-efficient processing method.

  Args:
      fp_in: Input file path
      fp_out: Output file path
      pid_props: Product identifier properties
      vid_props: Variant identifier properties
  """
  logger.info(f"Starting iterative processing from {fp_in} to {fp_out}")

  # Process products iteratively without loading all into memory
  product_count = create_products_iteratively(fp_in, fp_out,
                                              pid_identifiers=pid_props,
                                              vid_identifiers=vid_props)

  logger.info(f"Successfully processed {product_count} products from {fp_in} to {fp_out}")


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
    description="Transforms Shopify aggregated products into Bloomreach Product model with no reserved attribute mappings, apart from setting product and variant identifiers. The product and variant identifiers may be specified prior to running, however, they default to `handle` for the product identifier and `sku` for the variant identifier. All other shopify properties are prefixed with a namespace to prevent collisions with any Bloomreach reserved attributes. Product properties are prefixed with `sp.`, Product metafield properties are prefixed with `spm.`, Variant properties are prefixed with `sv.`, and Variant metafield properties are prefixed with `svm.`. This output may be loaded directly into a Bloomreach Discovery catalog as is."
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
    "--pid-props",
    help="Comma separated property names to use to resolve a shopify product property to Bloomreach product identifier. Usually set to the string 'handle'.",
    type=str,
    default="handle",
    required=False
  )

  parser.add_argument(
    "--vid-props",
    help="Comma separated property names to use to resolve a shopify variant property to Bloomreach variant identifier. Usually set to the string 'sku'.",
    type=str,
    default="sku",
    required=False
  )

  parser.add_argument(
    "--legacy-mode",
    help="Use the legacy, memory-intensive processing method (not recommended for large files)",
    action="store_true",
    default=False
  )

  args = parser.parse_args()
  fp_in = args.input_file
  fp_out = args.output_file
  pid_props = args.pid_props
  vid_props = args.vid_props

  if args.legacy_mode:
    logger.warning("Using legacy mode with memory-intensive processing. Not recommended for large files.")
    products = create_products(fp_in, pid_identifiers=pid_props, vid_identifiers=vid_props)

    with gzip.open(fp_out, 'wb') as out:
      writer = jsonlines.Writer(out)
      for product in products:
        writer.write(product)
      writer.close()

    logger.info(f"Successfully processed {len(products)} products in legacy mode")
  else:
    main(fp_in, fp_out, pid_props, vid_props)