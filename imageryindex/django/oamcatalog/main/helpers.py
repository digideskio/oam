from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404, HttpResponse
import django.conf
import sys
import traceback
import base64
from django.shortcuts import render_to_response, get_object_or_404

from os import environ
from urlparse import urlparse
from os.path import basename
from hashlib import md5
from math import sqrt

try:
    import json
except ImportError:
    import simplejson as json

from osgeo import gdal
from PIL import Image

from django.http import HttpResponse
from django.contrib.auth import authenticate, login

class ApplicationError(Exception):
    errors = None
    status_code = 200
    def __init__(self, errors):
        self.errors = errors
    def __str__(self):
        return ", ".join(self.errors)

def text_error_response(error):
    response = []
    response.append("Error Type: %s\n" %  error['type'])
    if error['unexpected']:
        response.append("An unexpected error occurred!\n")

    response.append("Error: %s\n" %  error['error'])
    if error.has_key('traceback'):
        response.append("Traceback:\n\n%s" %  error['traceback'])
    
    
    r = HttpResponse(response)
    r['Content-Type'] = "text/plain"
    return r

def generate_error_response(exception, format="text", status_code=None, request=None, unexpected=False):
    """Generate an error response, used in textexception/jsonexception
       decorators.
       
       >>> try:
       ...     int('a')
       ... except Exception, E:
       ...    response = generate_error_response(E) 
       >>> response.status_code 
       500
       >>> response.content.find("Error Type: ValueError")
       0
       
       >>> try:
       ...     raise ApplicationError("Failed")
       ... except ApplicationError, E:
       ...    response = generate_error_response(E) 
       >>> response.status_code
       200
       >>> "Error: Failed" in response.content
       True

       >>> try:
       ...     raise ApplicationError("Failed")
       ... except ApplicationError, E:
       ...    h = HttpRequest()
       ...    response = generate_error_response(E, format='json', request=h)
       >>> data = json.loads(response.content)
       >>> data['error']
       u'Failed'
       
    """ 
     
    type = sys.exc_type.__name__
    error = {'error': str(exception), 'type': type, 'unexpected':unexpected}
    if django.conf.settings.DEBUG and unexpected:
        error['traceback'] = traceback.format_exc()
    
    if format == "json" and request:
        response = json_response(request, error)
    else:
        response = text_error_response(error)
    
    if hasattr(exception, "status_code"):
        response.status_code = exception.status_code
    elif status_code:
        response.status_code = status_code
    else:
        response.status_code = 500
    
    return response
    

def textexception(func):
    def wrap(request, *args, **kw):
        try:
            return func(request, *args, **kw)
        
        except ObjectDoesNotExist, E:
            return generate_error_response(E, status_code=404)
        
        except Http404, E:
            return generate_error_response(E, status_code=404)
        
        except ApplicationError, E:
            return generate_error_response(E)
            
        except Exception, E:
            return generate_error_response(E, unexpected=True)
    
    return wrap        

def jsonexception(func):
    def wrap(request, *args, **kw):
        try:
            return func(request, *args, **kw)
        
        except ObjectDoesNotExist, E:
            return generate_error_response(E, format="json", request=request, status_code=404)
        
        except Http404, E:
            return generate_error_response(E, format="json", request=request, status_code=404)
        
        except ApplicationError, E:
            return generate_error_response(E, format="json", request=request)
            
        except Exception, E:
            return generate_error_response(E, format="json", request=request, unexpected=True)
    return wrap        

def json_response(request, obj, warnings=None, errors=None):
    """Take an object. If the object has a to_json method, call it, 
       and take either the result or the original object and serialize
       it using json. If a callbakc was sent with the http_request, wrap
       the response up in that and return it, otherwise, just return it."""
    if hasattr(obj, 'to_json'):
        obj = obj.to_json()
    if request.GET.has_key('_sqldebug'):
        import django.db
        obj['sql'] = django.db.connection.queries
    if warnings:
        obj['warnings'] = warnings
    data = json.dumps(obj, indent=2)
    if request.GET.has_key('callback'):
        data = "%s(%s);" % (request.GET['callback'], data)
    elif request.GET.has_key('handler'):
        data = "%s(%s);" % (request.GET['handler'], data)
    
    r = HttpResponse(data)
    r['Access-Control-Allow-Origin'] = "*"
    r['Content-Type'] = "application/json"
    return r

def view_or_basicauth(view, request, test_func, realm = "", *args, **kwargs):
    """
    This is a helper function used by both 'logged_in_or_basicauth' and
    'has_perm_or_basicauth' that does the nitty of determining if they
    are already logged in or if they have provided proper http-authorization
    and returning the view if all goes well, otherwise responding with a 401.
    """
    if test_func(request.user):
        # Already logged in, just return the view.
        #
        return view(request, *args, **kwargs)

    # They are not logged in. See if they provided login credentials
    #
    uname = None
    if 'HTTP_AUTHORIZATION' in request.META:
        auth = request.META['HTTP_AUTHORIZATION'].split()
        if len(auth) == 2:
            # NOTE: We are only support basic authentication for now.
            #
            if auth[0].lower() == "basic":
                uname, passwd = base64.b64decode(auth[1]).split(':')
                user = authenticate(username=uname, password=passwd)
                if user is not None:
                    if user.is_active:
                        login(request, user)
                        request.user = user
                        return view(request, *args, **kwargs)

    # Either they did not provide an authorization header or
    # something in the authorization attempt failed. Send a 401
    # back to them to ask them to authenticate.
    #
    message = "You must be authenticated to use this service.\n"
    if uname:
        message = "You must be authenticated to use this service. (Authentication failed for %s.)\n" % uname
    response = HttpResponse(message)
    response.status_code = 401
    response['WWW-Authenticate'] = 'Basic realm="%s"' % realm
    return response
    
#############################################################################
#
def logged_in_or_basicauth(realm = ""):
    """
    A simple decorator that requires a user to be logged in. If they are not
    logged in the request is examined for a 'authorization' header.

    If the header is present it is tested for basic authentication and
    the user is logged in with the provided credentials.

    If the header is not present a http 401 is sent back to the
    requestor to provide credentials.

    The purpose of this is that in several django projects I have needed
    several specific views that need to support basic authentication, yet the
    web site as a whole used django's provided authentication.

    The uses for this are for urls that are access programmatically such as
    by rss feed readers, yet the view requires a user to be logged in. Many rss
    readers support supplying the authentication credentials via http basic
    auth (and they do NOT support a redirect to a form where they post a
    username/password.)

    Use is simple:

    @logged_in_or_basicauth
    def your_view:
        ...

    You can provide the name of the realm to ask for authentication within.
    """
    def view_decorator(func):
        def wrapper(request, *args, **kwargs):
            return view_or_basicauth(func, request,
                                     lambda u: u.is_authenticated(),
                                     realm, *args, **kwargs)
        return wrapper
    return view_decorator

#############################################################################
#
def has_perm_or_basicauth(perm, realm = ""):
    """
    This is similar to the above decorator 'logged_in_or_basicauth'
    except that it requires the logged in user to have a specific
    permission.

    Use:

    @logged_in_or_basicauth('asforums.view_forumcollection')
    def your_view:
        ...

    """
    def view_decorator(func):
        def wrapper(request, *args, **kwargs):
            return view_or_basicauth(func, request,
                                     lambda u: u.has_perm(perm),
                                     realm, *args, **kwargs)
        return wrapper
    return view_decorator

def render(request, template, args=None):
    if not args:
        args = {'user': request.user}
    else:
        args['user'] = request.user
    
    return render_to_response(template, args)

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
    
    th_height = int(sqrt(area / aspect))
    th_width = int(aspect * th_height)
    
    return th_width, th_height

def image_made_smaller(im, size):
    """
    """
    environ['GDAL_DISABLE_READDIR_ON_OPEN'] = 'YES'
    #environ['CPL_DEBUG'] = 'On'

    ds = gdal.Open('/vsicurl/' + str(im.url))
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

def image_cache_key(image, extra):
    """
    """
    s, host, path, q, p, f = urlparse(image.url)
    hash = md5(image.url).hexdigest()
    name = basename(path)
    
    return '-'.join((host, hash, extra, name))
