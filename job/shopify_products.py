import gzip
import json
import jsonlines
import logging
from collections import defaultdict
from os import getenv

logger = logging.getLogger(__name__)

def parse_shopify_objects(fp):
  objects = {}
  parent_to_children = defaultdict(list)
  products = []

  with gzip.open(fp, 'rb') as file:
    for line in file:
      index_object(json.loads(line), objects, parent_to_children)

    for k in objects.keys():
      if "/Product/" in k and "/Collection/" not in k:
        product = create_product_from_objects(k, objects, parent_to_children)
        products.append(product)

  return products

def index_object(shopify_object, objects, parent_to_children):
  shopify_id = shopify_object["id"]

  if "/shopify/Collection/" in shopify_id:
    shopify_id = shopify_object["id"] + shopify_object["__parentId"]

  objects[shopify_id] = shopify_object

  if "__parentId" in shopify_object:
    parent_to_children[shopify_object["__parentId"]].append(shopify_id)

def create_product_from_objects(k, objects, parent_to_children):
  collections, variants, metafields = [], [], []

  children_ids = parent_to_children[k]
  for child_id in children_ids:
    if "/Collection/" in child_id:
            collection = objects[child_id].copy()
            if collection.get("translations"):
                locales = set()
                for translation in collection["translations"]:
                    locale = translation["locale"]
                    locales.add(locale)
                    key = translation["key"]
                    value = translation["value"]
                    collection[key] = value

                collection["translation_done"] = "-".join(sorted(locales))
                del collection["translations"]
            collections.append(collection)
    elif "/ProductVariant/" in child_id:
      variants.append(create_variant(child_id, objects, parent_to_children))
    elif "/Metafield/" in child_id:
      if "/Product/" in objects[child_id]["__parentId"]:
        metafields.append(objects[child_id])

  product = objects[k]

  # Handle translations
  if product.get("translations"):
    locales = set()
    for translation in product["translations"]:
      locale = translation["locale"]
      locales.add(locale)
      key = translation["key"]
      value = translation["value"]

      # Map body_html to descriptionHtml, otherwise use the key as is
      if key == "body_html":
        product["descriptionHtml"] = value
      else:
        product[key] = value

    # Add translationDone field and remove translations
    product["translation_done"] = "-".join(sorted(locales))
    del product["translations"]

  product["collections"] = collections
  product["variants"] = variants
  product["metafields"] = metafields

  return product

def create_variant(variant_id, objects, parent_to_children):
  metafields = []

  children_ids = parent_to_children[variant_id]
  for child_id in children_ids:
    if "/Metafield/" in child_id:
      if "/ProductVariant/" in objects[child_id]["__parentId"]:
        metafields.append(objects[child_id])

  variant = objects[variant_id]
  variant["metafields"] = metafields
  return variant

def main(fp_in, fp_out):
  products = parse_shopify_objects(fp_in)

  with gzip.open(fp_out, "wb") as out:
    writer = jsonlines.Writer(out)
    for object in products:
      writer.write(object)
    writer.close()

if __name__ == '__main__':
  import argparse
  from os import getenv
  from sys import stdout

  loglevel = getenv('LOGLEVEL', 'INFO').upper()
  logging.basicConfig(
    stream=stdout,
    level=loglevel,
    format="%(name)-12s %(asctime)s %(levelname)-8s %(filename)s:%(funcName)s %(message)s"
  )

  parser = argparse.ArgumentParser(
    prog="Transform Shopify bulk operation jsonl file into aggregated products jsonl",
    description="Transforms Shopify bulk output of products and their associated objects (metafields, collections, variants, variants metafields) into a single aggregated Shopify product record."
  )

  parser.add_argument(
    "--input-file",
    help="File path of shopify bulk operation jsonl",
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

  args = parser.parse_args()
  fp_in = args.input_file
  fp_out = args.output_file

  main(fp_in, fp_out)