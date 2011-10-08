Creating a Mosaic Using MapServer
=================================

Fetch images locally:

::

  mkdir images
  oam-fetch --bbox '-89.968049715099994 29.246717546700001 -89.946693390999997 29.266403954200001' -d "images"

Build a tile index:

::
  
  cd images
  for i in `ls *.tif | tac`; do gdaltindex oam.shp $i; done

Copy the oam.map file to your images directory::

  cp ~/oam/accesstools/oammapserver/oam.map .
  shp2img -m img.map -o image.jpg -e -89.968049715099994 29.246717546700001 -89.946693390999997 29.266403954200001 -l oam -i image/jpeg -s 4000 4000

This will produce a 4000 x 4000 pixel mosaic.
