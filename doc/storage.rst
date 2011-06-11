Storage
=======

Currently, we expect storage to be managed by parties interested in
publishing imagery to OpenAerialMap. For processed imagery, it is
expected that providers publish appropriately optimized imagery before
indexing it in the OpenAerialMap imagery index. 

.. _optimized:

OpenAerialMap Archive Image
+++++++++++++++++++++++++++

In order to make OAM images easy to access for remote clients, the OAM
project is looking to have processed images fulfill a certain set of 
requirements to limit the network traffic needed by OAM tools / intelligent
clients to fetch the data they need where possible.

Generally, what this means is that the image is:

* A Geographic TIFF
* Projected in EPSG:4326
* With internal tiling at 512px x 512px
* Has overviews to provide easy access to lower levels of detail
  without reading the entire image.
* Uses YCbCr JPEG compression at quality setting 75

Archive images will be read by the OpenAerialMap server to gather additional
metadata -- the metadata of the file is presumed to override the metadata
passed in by a user, where available.

OpenAerialMap imagery will be accessed over the network -- either directly,
or via client tools. As a result, one of the important aspects of processed
OpenAerialMap imagery is to minimize the amount of network bandwidth 
consumed. As a result, we have attempted to identify the best option for
saving space for storage as well as minimizing potential network bandwidth
while not compromising image quality. 

Archive Image Creation
----------------------

To create an archive image, it is possible to use GDAL. The basic steps are:
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
  nearblack  -co TILED=YES -setmask -near 3 -nb 0 -white -of GTiff -o ./prewarp.tif ./your_image.tif
  gdalwarp -co TILED=YES -dstalpha  -t_srs EPSG:4326 prewarp.tif warped.tif
  gdal_translate -co TILED=YES -co JPEG_QUALITY=80 -co COMPRESS=JPEG -co PHOTOMETRIC=YCBCR  -b 1 -b 2 -b 3 -mask 4 warped.tif final.tif 
    
If you need to use this imagery in a tool that is not GDAL, and does not 
correctly support TIFF mask bands, you can convert it back to a normal 4-band
image with alpha using:

::

  gdal_translate -b 1 -b 2 -b 3 -b mask final.tif myimage.tif

This will flatten the mask back into a 'normal' alpha band.    

Note that, depending on your image, you may need to adjust some parameters
in the nearblack and gdalwarp commands; once you have an uncompressed image in
EPSG:4326 with alpha as a fourth band, you should be able to just use the 
last gdal_translate command to create an OAM image.

Imagery Availability
++++++++++++++++++++

One of the consistent problems of distributed storage without
replication is that any point of failure becomes a single point of
failure. As a result, OpenAerialMap will begin life in a position where
failure of a single imagery host may create a situation where some
imagery becomes unavailable for a time.

However, overall this effect is less of a problem early on than it might
otherwise be for a couple reasons:

1. Imagery from OAM is not needed to maintain products, in general. In 
   order to produce a product from OAM, the producer will likely need to
   replicate the content in OAM locally, creating a somewhat redundant
   storage of that content for the purposes of that product. For
   example, if someone wishes to make a tiled mosaic available for a
   given area, they will need to download the source data from the
   distributed nodes, and keep them locally; in this way, a failure at
   some other time from a storage host will not affect the functionality
   of the product.
2. By working with high-quality imagery hosts, we hope to be able to
   provide somewhat stable homes for imagery storage, and maintain those
   relationships as a group. 

However, as the project grows, it is expected that this solution will
grow untenable; as such, investigating fault-tolerant distributed
storage options to help prevent this kind of failure will likely be a
goal of the project.
