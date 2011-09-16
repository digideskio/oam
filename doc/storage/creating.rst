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
  gdaladdo final.tif 2 4 8 16 32 64 128 256
    
If you need to use this imagery in a tool that is not GDAL, and does not 
correctly support TIFF mask bands, you can convert it back to a normal 4-band
image with alpha using:

::

  gdal_translate -b 1 -b 2 -b 3 -b mask final.tif myimage.tif

This will flatten the mask back into a 'normal' alpha band.    

Using EC2
---------

There is now an EC2 AMI available which has the tools installed to do simple
image processing. Simply deploy ami-07db196e, and you will have a server
which has a single script in it: "simple_convert_image.sh". With this 
in place, you can do a conversion on any file as easily as:

:: 
  
  wget http://archive.publiclaboratory.org/portland/2011-3-11-oregon-portland-eastburnside-65th/geotiff/2011-3-11-oregon-portland-eastburnside-65th.tif
  ./simple_convert_image.sh 2011-3-11-oregon-portland-eastburnside-65th.tif

The end result of this will be a new file::

    -rw-r--r-- 1 ubuntu ubuntu 413M 2011-08-24 07:09 2011-3-11-oregon-portland-eastburnside-65th.tif
    -rw-r--r-- 1 ubuntu ubuntu  13M 2011-09-16 21:40 2011-3-11-oregon-portland-eastburnside-65th.tif_converted.tif

This runs by default on an EC2 small instance. This instance costs ~8 cents
per CPU hour in the US/East region. Incoming bandwidth is not charged for 
in this region, so the large image download to pull an image in will be free;
you will only pay for the imagery you transfer out, at 12cents/GB (first 
gigabyte is free).

A simple tutorial on getting started with EC2 is available on many websites;
I was able to use the instructions in a blog post by Paul Stamatiou: 

http://paulstamatiou.com/how-to-getting-started-with-amazon-ec2

Image Format Support
++++++++++++++++++++

GDAL supports a wide variety of formats, including both open and proprietary
formats. Many aerial imagery providers use a proprietary format called MrSID
to make their imagery available; this format can be added to GDAL on a number
of platforms, but is generally not available by default on open platforms.

To install MrSID, you can refer to:

* http://trac.osgeo.org/gdal/wiki/MrSID -- GDAL's webpage on compiling GDAL with MrSID support
* http://trac.osgeo.org/ubuntugis/wiki/TutorialMrSid -- UbuntuGIS's page on how to compile MrSID support as a plugin for an already-compiled GDAL.
* http://www.kyngchaos.com/software/frameworks -- KyngChaos compiles the MrSID plugin for the GDAL frameworks he makes available.

Once you have MrSID support, you should also be able to read large JPEG2000
images without problems; the open source (Jasper) JPEG2000 implementation is
somewhat lacking in dealing with large images.

MrSID and JPEG2000 should provide support for the majority of aerial imagery
data. 

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
