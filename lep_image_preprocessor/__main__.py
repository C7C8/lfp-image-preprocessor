import argparse
import logging
import os
from pathlib import Path
from argparse import ArgumentParser

from lep_image_preprocessor import log, log_formatter


def dir_path(path: str) -> Path:
    if os.path.isdir(path):
        return Path(path)
    raise NotADirectoryError(path)


def main():
    parser = ArgumentParser(
        prog="LEP Image Preprocessor",
        description="Program for extracting EXIF data from images, creating tag + image sidecars, and tiling images",
        epilog="Written for Steven Kazlowski's LeftEyePro.com photography website"
    )
    parser.add_argument("folder", help="Folder with JPEGs to process")
    parser.add_argument("-o", "--output", help="Output folder", default="out", type=dir_path)
    parser.add_argument("-r", "--recursive", action="store_true", help="Recursively find images")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging")
    parser.add_argument("-s", "--tile-size", default=256, type=int, help="Image tile size (all tiles are squares)")
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


if __name__ == '__main__':
    main()
