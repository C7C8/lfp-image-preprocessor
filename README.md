```
usage: LEP Image Preprocessor [-h] [--file FILE | --folder FOLDER] [-o OUTPUT]
                              [-r] [-v] [-s TILE_SIZE] [--overwrite]
                              [--log LOG]

Program for extracting EXIF data from images, creating tag + image sidecars,
and tiling images

options:
  -h, --help            show this help message and exit
  --file FILE           JPEG to process
  --folder FOLDER       Folder with JPEGs to process
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