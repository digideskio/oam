import os, sys, tempfile, re, StringIO
from xml.etree.ElementTree import ElementTree
try:
    from hashlib import md5
    md5 # pyflakes
except ImportError:
    from md5 import md5
try:
    from osgeo import gdal
    gdal # pyflakes
except ImportError:
    try:
        import gdal
        gdal # pyflakes
    except ImportError:
        gdal = None

def requires_gdal(method):
    def f(*args, **kwargs):
        if not gdal:
            raise ImportError("Method %s requires GDAL Python." % method)
        return method(*args, **kwargs)
    return f

class ImageException(Exception):
    pass

class Image(object):
    __fields__ = ("path", "left", "bottom", "right", "top", "width", "height", "crs", "file_format", "license", "vrt")

    def __init__(self, url="", bbox=[], width=0, height=0, **kwargs):
        self.path = url
        self.left, self.bottom, self.right, self.top = bbox
        self.width, self.height = width, height
        for field in ("file_format", "crs", "vrt", "license"):
            setattr(self, field, kwargs.get(field))
        assert self.path
        assert self.left < self.right
        assert self.bottom < self.top
        assert self.width > 0
        assert self.height > 0

    @property
    def px_width(self):
        return (self.right - self.left) / float(self.width)

    @property
    def px_height(self):
        return -(self.top - self.bottom) / float(self.height)

    @property
    def transform(self):
        return (self.left, self.px_width, 0.0, self.top, 0.0, self.px_height)

    @property
    def bbox(self):
        return (self.left, self.bottom, self.right, self.top)

    def window(self, (left, bottom, right, top)):
        """convert bbox to image pixel window"""
        xoff = int((left - self.left) / self.px_width + 0.0001)
        yoff = int((top - self.top) / self.px_height + 0.0001)
        width = int((right - self.left) / self.px_width + 0.5) - xoff
        height = int((bottom - self.top) / self.px_height + 0.5) - yoff
        #if width < 1 or height < 1: return ()
        return (xoff, yoff, width, height)

    def intersection(self, (left, bottom, right, top)):
        # figure out intersection region
        left = max(left, self.left)
        right = min(right, self.right)
        top = min(top, self.top)
        bottom = max(bottom, self.bottom)
        # do they even intersect?
        if left >= right or top <= bottom: return ()
        return (left, bottom, right, top)

    def union(self, (left, bottom, right, top)):
        left = min(left, self.left)
        right = max(right, self.right)
        top = max(top, self.top)
        bottom = min(bottom, self.bottom)
        return (left, bottom, right, top)

    def to_dict(self):
        data = dict((field, getattr(self, field)) for field in self.__fields__)
        data["url"] = data.pop("path")
        data["bbox"] = [data.pop(field) for field in ("left", "bottom", "right", "top")]
        data["file_size"] = data["hash"] = None
        return data

    @requires_gdal
    def load_vrt(self, dataset=None):
        if not dataset:
            dataset = self.open(self.path)
        _, tmp = tempfile.mkstemp()
        try:
            gdal.GetDriverByName('VRT').CreateCopy(tmp, dataset)
            self.vrt = file(tmp).read()
        finally:
            os.unlink(tmp)
        return self.vrt

    @property
    @requires_gdal
    def bands(self):
        bands = {}
        tree = ElementTree()
        if not self.vrt: self.load_vrt()
        tree.parse(StringIO.StringIO(self.vrt))
        for band in tree.findall("VRTRasterBand"):
            interp = band.find("ColorInterp").text
            props = band.find("SimpleSource/SourceProperties").attrib
            idx = band.find("SimpleSource/SourceBand").text
            bands[interp] = [int(idx), props["DataType"], int(props["BlockXSize"]), int(props["BlockYSize"])]
        return bands

    def compute_md5(self, blocksize=(1<<20)):
        filesize = os.path.getsize(self.path)
        f = file(self.path, "rb")
        h = md5()
        print >>sys.stderr, ""
        for i in range(0, filesize, blocksize):
            h.update(f.read(blocksize)) 
            print >>sys.stderr, "\rComputing MD5... %d%%" % (float(i)/filesize*100),
        print >>sys.stderr, "\rComputing MD5... done."
        return h.hexdigest()

    @classmethod
    @requires_gdal
    def open(cls, path, mode=None):
        if re.match(r'\w+://', path):
            path = "/vsicurl/" + path # use the VSI curl driver
        if mode is None:
            mode = gdal.GA_ReadOnly
        dataset = gdal.Open(path, mode)
        if dataset is None:
            raise ImageException("Cannot open %s" % path)
        return dataset

    @classmethod
    @requires_gdal
    def load(cls, url):
        #self.notify("? %s ", url.split("/")[-1])
        dataset = cls.open(url)
        xform = dataset.GetGeoTransform()
        bbox = [
           xform[0] + dataset.RasterYSize * xform[2],
           xform[3] + dataset.RasterYSize * xform[5],  
           xform[0] + dataset.RasterXSize * xform[1],
           xform[3] + dataset.RasterXSize * xform[4]
        ]
        record = {
            "url": url,
            "file_format": dataset.GetDriver().ShortName,
            "width": dataset.RasterXSize,
            "height": dataset.RasterYSize,
            "crs": dataset.GetProjection(),
            "file_size": None,
            "hash": None,
            "bbox": bbox
        }
        # record["file_size"] = os.path.getsize(filename)
        # record["hash"] = compute_md5(filename)
        # record["filename"] = filename.split("/")[-1]
        # self.debug("OK")
        image = cls(**record)
        image.load_vrt(dataset)
        return image
