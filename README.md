```
usage: LEP Image Preprocessor [-h] [--file FILE | --folder FOLDER] [-o OUTPUT]
                              [-r] [-v] [-s TILE_SIZE] [-t THUMBNAIL_SIZE]
                              [--resize RESIZE] [--ignore-errors]
                              [--overwrite] [--log LOG]

Program for extracting EXIF data from images, creating tag + image sidecars,
and tiling images

options:
  -h, --help            show this help message and exit
  --file FILE           JPEG to process
  --folder FOLDER       Folder with JPEGs to process
  -o OUTPUT, --output OUTPUT
                        Output folder
  -r, --recursive       Recursively find images if a target folder was
                        provided
  -v, --verbose         Enable debug logging
  -s TILE_SIZE, --tile-size TILE_SIZE
                        Image tile size (all tiles are squares)
  -t THUMBNAIL_SIZE, --thumbnail-size THUMBNAIL_SIZE
                        Image thumbnail max dimension along either axis
  --resize RESIZE       Resize images so that no dimension is longer than this
                        measurement
  --ignore-errors       Ignore errors during processing and continue
                        processing the queue
  --overwrite           Overwrite existing outputs
  --log LOG             Optional log file

Written for Steven Kazlowski's LeftEyePro.com photography website
```