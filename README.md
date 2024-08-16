```
usage: LEP Image Preprocessor [-h] [-o OUTPUT] [-r] [-v] [-s TILE_SIZE]
                              [--overwrite] [--log LOG]
                              folder

Program for extracting EXIF data from images, creating tag + image sidecars,
and tiling images

positional arguments:
  folder                Folder with JPEGs to process

options:
  -h, --help            show this help message and exit
  -o OUTPUT, --output OUTPUT
                        Output folder
  -r, --recursive       Recursively find images
  -v, --verbose         Enable debug logging
  -s TILE_SIZE, --tile-size TILE_SIZE
                        Image tile size (all tiles are squares)
  --overwrite           Overwrite existing outputs
  --log LOG             Optional log file

Written for Steven Kazlowski's LeftEyePro.com photography website
```