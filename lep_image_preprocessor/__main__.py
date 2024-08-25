import argparse
import logging
import os
from pathlib import Path
from argparse import ArgumentParser
from typing import List, Dict

import yaml
from PIL import Image, ImageFile

from lep_image_preprocessor import log, log_formatter
from lep_image_preprocessor.image import extract_tags, tile_image, extract_description, extract_date, create_thumbnail


def dir_path(path: str) -> Path:
    """Check if the provided string is in fact a valid path. If so, return it as a Path. Else, return an error"""
    if os.path.isdir(path):
        return Path(path)
    raise NotADirectoryError(path)


def file_path(path: str) -> Path:
    """Check if the provided string is in fact a valid file. If so, return Path to it. Else, return an error"""
    if os.path.isfile(path) and os.access(path, os.R_OK):
        return Path(path)
    raise FileNotFoundError(path)


def main():
    parser = ArgumentParser(
        prog="LEP Image Preprocessor",
        description="Program for extracting EXIF data from images, creating tag + image sidecars, and tiling images",
        epilog="Written for Steven Kazlowski's LeftEyePro.com photography website"
    )

    # Inputs -- either a single image, or a folder
    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument("--file", type=file_path, help="JPEG to process")
    input_group.add_argument("--folder", type=dir_path, help="Folder with JPEGs to process")

    parser.add_argument("-o", "--output", help="Output folder", default="out", type=dir_path)
    parser.add_argument("-r", "--recursive", action="store_true", help="Recursively find images if a target folder was provided")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging")
    parser.add_argument("-s", "--tile-size", default=256, type=int, help="Image tile size (all tiles are squares)")
    parser.add_argument("-t", "--thumbnail-size", default=384, type=int, help="Image thumbnail max dimension along either axis")
    parser.add_argument("--resize", default=None, type=int, help="Resize images so that no dimension is longer than this measurement")
    parser.add_argument("--ignore-errors", action="store_true", help="Ignore errors during processing and continue processing the queue")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing outputs")
    parser.add_argument("--log", type=argparse.FileType("w+"), help="Optional log file")
    args = parser.parse_args()

    # Verbose logging
    if args.verbose:
        log.setLevel(level=logging.DEBUG)
        log.debug("Verbose logging enabled")

    # Write logs to file
    if args.log is not None:
        handler = logging.StreamHandler(args.log)
        handler.setFormatter(log_formatter)
        log.addHandler(handler)

    log.debug("Using output path '%s' and ensuring path exists", args.output)
    try:
        args.output.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        log.critical("Failed to create output path '%s': %s", args.output, e)
        return

    #######################
    # FILE QUEUE ASSEMBLY #
    #######################
    file_queue: List[Path] = []
    if args.file is not None:
        file_queue.append(args.file)
    extensions = ["jpg", "jpeg", "JPEG", "JPG"]
    if args.folder is not None:
        for extension in extensions:
            try:
                if args.recursive:
                    file_queue.extend(args.folder.glob(f"**/*.{extension}"))
                else:
                    file_queue.extend(args.folder.glob(f"*.{extension}"))
            except OSError as e:
                log.error("Failed to extract collect list of files from '%s': %s", args.folder, e)
                if not args.ignore_errors:
                    log.critical("Aborting processing run due to failure to list all files in directory '%s'!", args.folder)
    log.debug("Collected %d files to process: %s", len(file_queue), list(map(lambda path: path.as_posix(), file_queue)))

    ##########################
    # IMAGE TILING & TAGGING #
    ##########################
    all_tags: Dict[str, List[str]] = {}
    all_tile_outputs: List[str] = []
    for i, path in enumerate(file_queue):
        log.info("(%d/%d) Processing file '%s'...", i + 1, len(file_queue), path)
        try:
            with Image.open(path) as image:
                image_output_folder = args.output / path.stem
                image_output_folder.mkdir(parents=True, exist_ok=True)
                img_tags = extract_tags(image)
                thumbnail_path = image_output_folder / f"thumbnail{path.suffix}"
                create_thumbnail(image, thumbnail_path, args.thumbnail_size)

                # Image tiling
                all_tile_outputs.append(image_output_folder.relative_to(args.output))
                if args.resize is not None:
                    image_tile_target = image.copy()
                    image.thumbnail((args.resize, args.resize))
                    log.debug("Resized image '%s' from %dx%d to %dx%d", path, *image.size, *image_tile_target.size)
                else:
                    image_tile_target = image.copy()
                tiles = tile_image(image_tile_target, path, image_output_folder, args.tile_size)

            image_sidecar_data = {
                    "description": extract_description(image),
                    "thumbnail": thumbnail_path.relative_to(image_output_folder).as_posix(),
                    "date": extract_date(image),
                    "filezize": os.stat(path).st_size,
                    "dimensions": {
                        "width": image.width,
                        "height": image.height,
                        "columns": len(tiles[0]),
                        "rows": len(tiles),
                    },
                    "tags": img_tags,
                    "tiles": tiles
                }

            # Write out sidecar file to the directory we stored all our tiles
            sidecar_path = image_output_folder / f"{path.stem}.sidecar.yaml"
            with open(sidecar_path, "w") as sidecar_file:
                log.debug("Writing sidecar file for '%s' to '%s'", path, sidecar_path)
                yaml.dump(image_sidecar_data, sidecar_file)

            # Add all newly-found tags
            prev_tags_count = len(all_tags)
            for tag in img_tags:
                if tag not in all_tags:
                    all_tags[tag] = []
                all_tags[tag].append(path.stem)
            log.debug("Processing '%s' found %d new tags (%d->%d)", path, len(all_tags) - prev_tags_count, prev_tags_count, len(all_tags))
            log.info("(%d/%d) Finished processing file '%s'", i + 1, len(file_queue), path)

        except BaseException as e:
            log.warning("Encountered error while processing file '%s', skipping file and continuing:%e ", path, e)
            if not args.ignore_errors:
                log.critical("Aborting processing run due to error processing file '%s'", path)
                return

    log.info("Finished processing %d files (output written to '%s'); writing out tag sidecar files before finishing up",
             len(file_queue), args.output)

    ################
    # TAG SIDECARS #
    ################
    tags_dir = args.output / "tags"
    if tags_dir.exists():
        log.warning("Tag sidecar directory '%s' already exists; tag sidecar files within will be overwritten!", tags_dir)
    else:
        log.debug("Creating tag sidecar directory '%s'", tags_dir)
        tags_dir.mkdir(exist_ok=True, parents=True)

    tag_index: Dict[str, str] = {}
    for tag, tagged_images in all_tags.items():
        # Save the sidecar path we can build an index later
        tag_sidecar_path = tags_dir / f"{tag.replace(" ", "_")}.sidecar.yaml"
        if tag_sidecar_path.exists():
            log.warning("Tag sidecar file '%s' already exists and will be overwritten", tag_sidecar_path)

        tag_index[tag] = tag_sidecar_path.relative_to(args.output).as_posix()
        try:
            with open(tag_sidecar_path, "w") as sidecar_file:
                yaml.dump({
                    "name": tag,
                    "description": "No description",
                    "images": tagged_images
                }, sidecar_file)
                log.debug("Wrote tag sidecar file '%s'", tag_sidecar_path)
        except OSError as e:
            log.error("Encountered error while writing tag sidecar file '%s': %s", tag_sidecar_path, e)
            if not args.ignore_errors:
                log.critical("Aborting processing run due to failed tag sidecar writing!")
                return

    ##################
    # TAG INDEX FILE #
    ##################
    tag_index_path = args.output / "tags.index.yaml"
    log.debug("Writing tag index file '%s'", tag_index_path)
    if tag_index_path.exists():
        log.warning("Tag index file '%s' already exists and will be overwritten", tag_index_path)
    try:
        with open(tag_index_path, "w") as index_file:
            yaml.dump(tag_index, index_file)
    except OSError as e:
        log.error("Encountered error while writing tag index file '%s': %s", tag_index_path, e)
        if not args.ignore_errors:
            log.critical("Aborting processing run due to failed tag index writing!")
            return

    ####################
    # IMAGE INDEX FILE #
    ####################
    image_index_path = args.output / "images.index.yaml"
    log.debug("Writing image index file '%s'", image_index_path)
    if image_index_path.exists():
        log.warning("Image index file '%s' already exists and will be overwritten", image_index_path)
    try:
        with open(image_index_path, "w") as index_file:
            yaml.dump(list(map(lambda path: path.as_posix(), all_tile_outputs)), index_file)
    except OSError as e:
        log.error("Encountered error while writing image index file '%s': %s", image_index_path, e)
        if not args.ignore_errors:
            log.critical("Aborting processing run due to failed image index writing!")
            return


if __name__ == '__main__':
    main()
