# Create your views here.
from django.http import HttpResponse, HttpResponseRedirect
import simplejson
import urllib
from django.forms import ModelForm
from main.models import Layer, Image, User, License, Mirror
from django.db.models import Count
from django.contrib.gis.geos import Polygon
from django.shortcuts import render_to_response, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.core.cache import cache
from main.helpers import *
from StringIO import StringIO
from django.conf import settings

@logged_in_or_basicauth()
def image_layer(request, image=None, layer=None):
    image = get_object_or_404(Image, pk=image)
    layer = get_object_or_404(Layer, pk=layer)
    if request.method == "POST":
        image.layers.add(layer)
        return json_response(request, image.to_json())
    elif request.method == "DELETE":
        image.layers.remove(layer)
        return json_response(request, image.to_json())
    else:
        raise Exception("Only POST or DELETE to this resource.")

from main.helpers import \
    jsonexception, jsonexception, json_response, logged_in_or_basicauth, \
    image_made_smaller, image_cache_key, image_size_small

@jsonexception
def layer(request, id=None):
    @logged_in_or_basicauth()
    def handle_update(request, layer):
        data = simplejson.loads(request.raw_post_data)
        warnings = []
        layer.from_json(data, request.user)
        layer.save()
        return json_response(request, layer)
    if id == None and request.method == "POST":
        l = Layer()
        return handle_update(request, l)
    elif id != None and request.method == "POST":
        l = Layer.objects.get(pk=id)
        return handle_update(request, l)
    elif id != None:
        l = Layer.objects.get(pk=id)
        if request.method == "DELETE":
            i.delete()
            return json_response(request, "")
        return json_response(request, l)
    else:
        layers = Layer.objects.all()
        if 'q' in request.GET:
            for term in request.GET['q'].split(" "):
                layers = layers.filter(name__icontains=term)
        if request.GET.get('output') == "simple":
            layers = layers.annotate(Count('image'))
            data = {'layers': 
             [dict(x) for x in layers.values("id", "name", "description", "image__count")]
            }
            for l in data['layers']:
                l['image_count'] = l['image__count']
                del l['image__count']

        else:    
            data = {'layers': [
                l.to_json() for l in layers
                ]
            }    
        return json_response(request, data)

@jsonexception
def license(request, id=None):
    @logged_in_or_basicauth()
    def handle_update(request, license):
        data = simplejson.loads(request.raw_post_data)
        warnings = []
        if not license.id:
            if 'url' in data:
                ls = License.objects.filter(url=data['url'])
                if ls.count():
                    license = ls[0]
                    warnings.append("URL of license matched existing license %s; updating that license instead of creating a new license." % ls[0].id) 
        license.from_json(data)
        license.save()
        return json_response(request, license, warnings=warnings)
    if id == None and request.method == "POST":
        l = License()
        return handle_update(request, l)
    elif id != None:
        l = License.objects.get(pk=id)
        if request.method == "DELETE":
            l.delete()
            return json_response(request, "")
        if request.method == "POST":
            return handle_update(request, l)
        return json_response(request, l)
    else:
        licenses = License.objects.all()
        data = {'licenses': [
            l.to_json() for l in licenses 
            ]
        }   
        return json_response(request, data)

@jsonexception
def mirror(request, id=None):
    @logged_in_or_basicauth()
    def handle_update(request, mirror):
        data = simplejson.loads(request.raw_post_data)
        mirror.from_json(data, request.user)
        mirror.save()
        return json_response(request, mirror)
    if id == None and request.method == "POST":
        m = Mirror()
        return handle_update(request, m)
    elif id != None:
        m = Mirror.objects.get(pk=id)
        if request.method == "DELETE":
            m.delete()
            return json_response(request, "")
        elif request.method == "POST":
            return handle_update(request, m)
        return json_response(request, m)
    else:
        mirrors = Mirror.objects.all()
        if 'image' in request.GET:
            mirrors = mirrors.filter(image__id=request.GET['image'])
        data = {'mirrors': [mirror.to_json() for mirror in mirrors]}   
        return json_response(request, data) 

@jsonexception
def image(request, id=None):
    @logged_in_or_basicauth()
    def handle_update(request, image):
        data = simplejson.loads(request.raw_post_data)
        image.from_json(data, request.user)
        image.save()
        return json_response(request, image)
        
    if id == None and request.method == "POST":
        i = Image()
        return handle_update(request,i)
    elif id != None:
        i = Image.objects.get(pk=id)
        if request.method == "DELETE":
            i.delete()
            return json_response(request, "")
        elif request.method == "POST":
            return handle_update(request, i)
        return json_response(request, i)
    else:
        images = Image.objects.all().select_related()
        output = request.GET.get('output', 'simple')
        if 'archive' in request.GET and request.GET['archive'].lower() in ("true", "t", "1"):
            images = images.filter(archive=True)
        else:
            images = images.filter(archive=False)
        if 'layer' in request.GET:
            images = images.filter(layers__id=request.GET['layer'])
        if 'bbox' in request.GET:
            left, bottom, right, top = map(float, request.GET['bbox'].split(","))
            box = Polygon.from_bbox([left, bottom, right, top])
            images = images.filter(bbox__intersects=box)
        limit = min(int(request.GET.get("limit", 1000)), 10000)
        start = int(request.GET.get("start", 0))    
        end = start + limit
        images = images.order_by("-id") 

        # Instantiating full image objects for thousands of images is slow;
        # instead, just use .values and make our own dict here. Adding more 
        # properties here should be done with consideration.
        if output == 'simple':
           data = {'images': 
            [dict(x) for x in images[start:end].values("id", "width", "height", "url", "bbox")]
           } 
           for i in data['images']:
            i['bbox'] = list(i['bbox'].extent)
        
        else:
            data = {'images': [
                i.to_json(output=output) for i in images[start:end]
                ]
            }   
        return json_response(request, data)

def home(request):
    """
    """
    images = []
    
    for img in Image.objects.order_by("-id")[0:30]:
        width, height = image_size_small(img.width, img.height, 'thumbnail')
        columns = (width < 240) and 'single' or 'double'
        
        image = {'id': img.id, 'image': img, 'thumb_size': [width, height], 'columns': columns}
        images.append(image)
    
    return render(request, "home.html", {'images': images})

def license_browse(request, id):
    l = License.objects.get(pk=id)
    images = l.image_set.order_by("-id")[0:5]
    return render(request, "license.html", {'license': l, 'recent_images': images})

def layer_list(request):
    item_list = Layer.objects.all().order_by("id")
    start = int(request.GET.get('start', 0))
    max = 25
    if 'q' in request.GET:
        for term in request.GET['q'].split(" "):
            item_list = item_list.filter(name__icontains=term)
    total = item_list.count()
    sublist = item_list[start:start+max]
    end = min(start+max, total)

    next_args = None
    prev_args = None
    if (start + max) < total:
        next_args = { 'start': end }
        if 'q' in request.GET:
            next_args['q'] = request.GET['q']
        next_args = urllib.urlencode(next_args)
    if (start - max) >= 0:
        prev_args = { 'start': start-max }
        if 'q' in request.GET:
            prev_args['q'] = request.GET['q']
        prev_args = urllib.urlencode(prev_args)
    return render(request, "layer_list.html", {'layers': sublist, 'total': total, 
                                                  'start': start + 1, 'end': end,
                                                  'next_args': next_args, 'prev_args': prev_args})

@login_required
def layer_create(request):
    class LayerForm(ModelForm):
        class Meta:
            model = Layer
            fields = ('name', 'description')

    if request.method == "POST":
        f = LayerForm(request.POST)
        layer = f.save(commit=False)
        layer.owner = request.user
        layer.save()
        return HttpResponseRedirect(layer.get_absolute_url())
    else:
        f = LayerForm()
    return render(request, "layer_new.html", {'form': f})    

def layer_browse(request, id):
    l = get_object_or_404(Layer, pk=id)
    next = Layer.objects.filter(id__gt=id).order_by("id")
    if next.count(): next = next[0]
    else: next = None
    prev = Layer.objects.filter(id__lt=id).order_by("-id")
    if prev.count(): prev = prev[0]
    else: prev = None
    image_ids = l.image_set.values("id")
    return render(request, "layer.html", {'layer': l, 'image_ids': image_ids, 'next': next, 'prev': prev})

def image_browse(request, id):
    i = Image.objects.get(pk=id)
    next = Image.objects.filter(id__gt=id).order_by("id")
    if next.count(): next = next[0]
    else: next = None
    prev = Image.objects.filter(id__lt=id).order_by("-id")
    if prev.count(): prev = prev[0]
    else: prev = None
    return render(request, "image.html", {'image': i, 'next': next, 'prev': prev})

def profile(request):
    return HttpResponseRedirect("/")
    return render_to_response("image.html", {'image': i})

def image_preview(request, id, size):
    """
    """
    if settings.OAM_THUMBNAIL_URL:
        return HttpResponseRedirect(settings.OAM_THUMBNAIL_URL % (id, size))
    image = Image.objects.get(pk=id)

    key = image_cache_key(image, size)
    val = cache.get(key)
    
    if val is None:
        preview = image_made_smaller(image, size)
        buffer = StringIO()
    
        preview.save(buffer, 'JPEG')
        val = buffer.getvalue()
        
        cache.set(key, val, 86400)
    
    return HttpResponse(val, mimetype='image/jpeg')
