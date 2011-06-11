Creating OpenAerialMap Imagery
==============================

Archive imagery has some special properties that are different from the way
most imagery is currently stored. This document describes how archive imagery
can be made.

Using GDAL
----------

The basic steps are:
 1. If your image has non-data areas, and was converted from a lossy format
    like SID, first convert the edges to black.
 2. Use gdalwarp to embed the mask into the image as an alpha band, and 
    reproject the image to EPSG:4326
 3. Use gdal_translate to convert the warped, alpha image to a 3-band mask
    image with a YCbCr JPEG mask at 80% quality.

(**Note**: Internal masks, a key component of OAM imagery, require GDAL 1.8+.)

You can use the following: 

::

  export GDAL_TIFF_INTERNAL_MASK=YES
  nearblack  -co TILED=YES -setmask -nb 0 -of GTiff -o ./prewarp.tif ./your_image.tif
  gdalwarp -co TILED=YES -dstalpha  -t_srs EPSG:4326 prewarp.tif warped.tif
  gdal_translate -co TILED=YES -co JPEG_QUALITY=80 -co COMPRESS=JPEG -co PHOTOMETRIC=YCBCR  -b 1 -b 2 -b 3 -mask 4 warped.tif final.tif 
    
If you need to use this imagery in a tool that is not GDAL, and does not 
correctly support TIFF mask bands, you can convert it back to a normal 4-band
image with alpha using:

::

  gdal_translate -b 1 -b 2 -b 3 -b mask final.tif myimage.tif

This will flatten the mask back into a 'normal' alpha band.    


Tweaking nearblack parameters
+++++++++++++++++++++++++++++

Nearblack has 3 parameters to tweak to ensure proper setup.

 1. **-near**: This parameter determines how far from black a pixel can be
    and be considered close enough to mark as transparent. For non-lossy
    imagery, this should be set explicitly to 0. For lossy imagery -- that
    is, imagery which has been converted from a JPG or MrSID -- this can
    sometimes leave images with 'ragged' edges. For lossy imagery, it is
    generally best to use the default for this value, which is 15. If
    your image was very heavily compressed, it is possible you may have
    to bump this number slightly higher -- but this has the possibility of
    marking edge areas as transparent if they are close to white or 
    black, so use with caution.
 2. **-nb**: This determines how many pixels can be 'non-black' on edges
    but still be removed. If you have leftover pixels from compression 
    when using -near 15, setting this to 1 or 2 may help remove them.
 3. **-white**: If the image you are converting uses white, instead of
    black, as a nodata color, then you can add the -white parameter, to
    use nearblack to mark white areas on edges as transparent.

The best way to check your nearblack parameters is to open a single resulting
TIFF after the gdalwarp step in an image viewer that supports alpha bands
in TIFFs (most of them); you will then be able to examine your edges and look
for missed pixels.
