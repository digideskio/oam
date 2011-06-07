import os
import urllib
import json
import gdal
import Image
import gdal
import math
from StringIO import StringIO
import cgi
import redis
import settings

OAM_HOST = "oam.osgeo.org"

# The following two functions were provided by 
# Michael Migurski, as part of the OpenAerialMap 
# server code.

def image_size_small(im_width, im_height, size):
    """ Determine a good thumbnail size based on desired named size.
    """
    aspect = float(im_width) / float(im_height)

    if size == 'thumbnail':
        if aspect > 1.6:
            return 440, int(440 / aspect)
        elif aspect < .3:
            return 98, int(98 / aspect)
        else:
            return 196, int(196 / aspect)
    
    elif size == 'preview':
        area = 320 * 320
    elif size == 'large':
        area = 640 * 640
    else:
        raise Exception('Don\'t know about "%s"' % size)
    
    th_height = int(math.sqrt(area / aspect))
    th_width = int(aspect * th_height)
    
    return th_width, th_height

def image_made_smaller(im, size="preview"):
    """
    """
    os.environ['GDAL_DISABLE_READDIR_ON_OPEN'] = 'YES'
    #environ['CPL_DEBUG'] = 'On'

    ds = gdal.Open('/vsicurl/' + im)
    th_width, th_height = image_size_small(ds.RasterXSize, ds.RasterYSize, size)
    
    #
    # Extract the best-sized overview from the source image
    #
    interps = dict([(getattr(gdal, gci), gci[4:-4]) for gci in dir(gdal) if gci.startswith('GCI')])
    bands = dict([(interps[ds.GetRasterBand(i).GetColorInterpretation()], ds.GetRasterBand(i)) for i in range(1, 1 + ds.RasterCount)])
    chans = []
    
    for (chan, interp) in enumerate(('Red', 'Green', 'Blue')):
        assert interp in bands, '%s missing from bands - bad news.' % interp

        band = bands[interp]
        overviews = [band.GetOverview(i) for i in range(band.GetOverviewCount())]
        overviews = [(ov.XSize, ov.YSize, ov) for ov in overviews]
        
        for (ov_width, ov_height, overview) in sorted(overviews):
            if ov_width > th_width:
                data = overview.ReadRaster(0, 0, ov_width, ov_height)
                chan = Image.fromstring('L', (ov_width, ov_height), data)
                chan = chan.resize((th_width, th_height), Image.ANTIALIAS)

                chans.append(chan)
                break
    
    #
    # Return an image
    #
    thumb = Image.merge('RGB', chans)

    return thumb


def application(environ, start_response):
    red = redis.Redis(host=settings.redis_host, port=settings.redis_port, db=0, password=settings.redis_password)
    form = cgi.FieldStorage(fp=environ['wsgi.input'], 
                        environ=environ)
    if 'id' in form:
        id = form["id"].value
        if 'size' in form:
            size = form['size'].value
        else:
            size = 'thumbnail'
        output = red.get("%s-%s" % (id, size))
        if not output:
            image = urllib.urlopen("http://%s/api/image/%s/" % (OAM_HOST, id))
            data = json.loads(image.read())
            preview = image_made_smaller(data['url'], size)
            buffer = StringIO()
            preview.save(buffer, 'JPEG')
            output = buffer.getvalue()
            red.set("%s-%s" % (id, size), output)
        status = '200 OK'
        response_headers = [('Content-type', 'image/jpeg'),
                            ('Content-Length', str(len(output)))]
        start_response(status, response_headers)
    else:
        output = "OAM Thumbnailing code."
        response_headers = [('Content-type', 'text/plain'),
                            ('Content-Length', str(len(output)))]
        start_response(status, response_headers)

    return [output]
