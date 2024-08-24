import hashlib
import re
import datetime
from functools import reduce
from pathlib import Path
from typing import List

import dateutil.parser
from PIL.ImageFile import ImageFile

from lep_image_preprocessor import log

_tag_regex = re.compile("^[A-z].+")


def extract_tags(image: ImageFile) -> List[str]:
    """Given an [image], return a set of XMP tags contained within it."""
    log.debug("Extracting tags from file '%s'; inspecting for XMP data", image.filename)
    tags = []

    try:
        xmp = reduce(lambda x, y: x | y, image.getxmp()["xmpmeta"]["RDF"]["Description"])
        tags.extend(filter(lambda subject: _tag_regex.match(subject) is not None, xmp["subject"]["Bag"]["li"]))
    except Exception as e:
        log.warn("Encountered error '%s' extracting tags from file '%s'; assuming there are no tags.", e, image.filename)

    log.debug("Extracted %d tags from file '%s': %s", len(tags), image.filename, tags)
    return tags


def extract_description(image: ImageFile) -> str | None:
    log.debug("Extracting description from image '%s'; inspecting for XMP data", image.filename)
    try:
        return (
            reduce(lambda x, y: x | y,
                   image.getxmp()["xmpmeta"]["RDF"]["Description"])
            ["description"]["Alt"]["li"]["text"]
        )
    except Exception as e:
        log.warn("Image '%s' does not have a description!", image.filename)
        return


def extract_date(image: ImageFile) -> datetime.datetime | None:
    log.debug("Extracting date from image '%s'; inspecting for XMP data", image.filename)
    try:
        str_date = reduce(lambda x, y: x | y, image.getxmp()["xmpmeta"]["RDF"]["Description"])["CreateDate"]
        return dateutil.parser.parse(str_date)
    except Exception as e:
        log.warn("Image '%s' does not have a description!", image.filename)
        return


def tile_image(image: ImageFile, containing_folder: Path, tile_size=256) -> List[List[str]]:
    """Tile an [image] into [SIZE]x[SIZE] chunks and write them out to a [containing_folder]. Returns a 2D array of
    image paths representing rows first, then columns. For obfuscation purposes, filenames will be SHA1 hashes of their
    contents."""
    log.debug("Tiling image '%s' into path '%s'; creating dir if it doesn't exist", image.filename, containing_folder)

    try:
        containing_folder.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        log.error("Encountered error creating tile output folder '%s': %s", containing_folder, e)
        raise e

    extension = Path(image.filename).suffix
    edge_width = image.size[0] % tile_size
    edge_height = image.size[1] % tile_size

    if edge_width != 0 or edge_height != 0:
        log.debug("Image '%s' has dimensions %dx%d that are not multiples of %d. Tiles on the edges will have one dimension "
                  "either %d (W) or %d (H)", image.filename,image.size[0], image.size[1], tile_size, edge_width, edge_height)

    # Figure out how many tiles_paths we actually need
    x_count_base = image.size[0] // tile_size
    y_count_base = image.size[1] // tile_size
    x_count = x_count_base + (1 if edge_width > 0 else 0)
    y_count = y_count_base + (1 if edge_height > 0 else 0)
    log.debug("Image '%s' will be tiled into %d columns and %d rows, for %d total tiles_paths", image.filename, x_count, y_count, x_count * y_count)

    # Calculate x coordinate pairs -- used for cropping from one point to another
    x_coordinate_pairs = list(range(0, (x_count_base + 1) * tile_size, tile_size))
    x_coordinate_pairs = [(start, end) for start, end in zip(x_coordinate_pairs, x_coordinate_pairs[1:])]
    if x_count > x_count_base:
        x_coordinate_pairs.append((x_count_base * tile_size, (x_count_base * tile_size) + (image.size[0] % tile_size)))
    log.debug("'%s' (%dx%d) x-coordinate pairs list: %s", image.filename, image.size[0], image.size[1], x_coordinate_pairs)

    # Calculate y coordinate pairs -- used for cropping from one point to another
    y_coordinate_pairs = list(range(0, (y_count_base + 1) * tile_size, tile_size))
    y_coordinate_pairs = [(start, end) for start, end in zip(y_coordinate_pairs, y_coordinate_pairs[1:])]
    if y_count > y_count_base:
        y_coordinate_pairs.append((y_count_base * tile_size, (y_count_base * tile_size) + (image.size[1] % tile_size)))
    log.debug("'%s' (%dx%d) y-coordinate pairs list: %s", image.filename, image.size[0], image.size[1], y_coordinate_pairs)

    # Let's do some tiling!
    tiles_paths: List[List[str]] = []
    tmp_file_path = containing_folder / f"temp{extension}"
    for min_y, max_y in y_coordinate_pairs:
        # Add a new row
        tile_row: List[str] = []
        for min_x, max_x in x_coordinate_pairs:
            tile = image.crop((min_x, min_y, max_x, max_y))
            tile.save(tmp_file_path)

            # Calculate SHA1 hash to use as image filename
            try:
                with open(tmp_file_path, "rb") as f:
                    sha1 = hashlib.file_digest(f, "sha1").hexdigest()
            except OSError as e:
                log.error("Encountered error writing '%s' tile (%d, %d, %d, %d) to file '%s': %s",
                          image.filename, min_x, max_x, min_y, max_y, tmp_file_path, e)
                raise e

            new_path = containing_folder / f"{sha1}{extension}"
            try:
                tmp_file_path.rename(new_path)
            except OSError as e:
                log.error("Encountered error renaming temp file '%s' to '%s': %s", tmp_file_path, new_path, e)
                raise e

            tile_row.append(new_path.name)
            log.debug("Saved tile (%d, %d, %d, %d) of '%s' to file %s", min_x, max_x, min_y, max_y, image.filename, new_path)
        tiles_paths.append(tile_row)

    log.debug("Finished tiling '%s' into a %dx%d grid of tiles; final output directory is %s", image.filename, x_count, y_count, containing_folder)
    return tiles_paths
