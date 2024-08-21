import argparse
import logging
import os
from pathlib import Path
from argparse import ArgumentParser
from typing import List

import yaml
from PIL import Image

from lep_image_preprocessor import log, log_formatter
from lep_image_preprocessor.image import extract_tags, tile_image


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

    log.debug("Using output path '%s' and ensuring path exists", args.output.resolve())
    args.output.mkdir(parents=True, exist_ok=True)

    # Assemble list of files to process
    file_queue: List[Path] = []
    if args.file is not None:
        file_queue.append(args.file)
    extensions = ["jpg", "jpeg", "JPEG", "JPG"]
    if args.folder is not None:
        for extension in extensions:
            if args.recursive:
                file_queue.extend(args.folder.glob(f"**/*.{extension}"))
            else:
                file_queue.extend(args.folder.glob(f"*.{extension}"))

    log.debug("Collected %d files to process: %s", len(file_queue), list(map(lambda path: path.as_posix(), file_queue)))

    for path in file_queue:
        log.info("Processing file '%s'...", path.as_posix())
        try:
            with Image.open(path) as image:
                tiles_destination = args.output / path.stem
                image_sidecar_data = {
                    "tags": extract_tags(image),
                    "filezize": os.stat(path).st_size,
                    "dimensions": {
                        "width": image.width,
                        "height": image.height
                    },
                    "tiles": tile_image(image, tiles_destination, args.tile_size)
                }
            with open(tiles_destination / "sidecar.yaml", "w") as sidecar_file:
                log.debug("Writing sidecar file for '%s' to '%s'", path, tiles_destination / "sidecar.yaml")
                yaml.dump(image_sidecar_data, sidecar_file)

            log.debug("Finished processing file '%s'", path.as_posix())

        except BaseException as e:
            if args.ignore_errors:
                log.warn("Encountered %s error while processing file '%s', skipping file and continuing", e, path.as_posix())
                log.debug(e)
            else:
                log.critical("Encountered %s error while processing file '%s', aborting processing!", e, path.as_posix())
                log.debug(e)
                break


if __name__ == '__main__':
    main()
