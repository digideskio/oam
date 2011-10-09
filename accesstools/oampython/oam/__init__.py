import optparse, os, getpass
from client import Client, ClientException, default_service
from image import Image
Image # pyflakes

def option_parser(usage=None):
    parser = optparse.OptionParser(usage)
    parser.add_option("-U", "--username", dest="user", default=os.environ.get("OAM_USERNAME"), help="OAM username (defaults to $OAM_USERNAME)")
    parser.add_option("-P", "--password", dest="passwd", default=os.environ.get("OAM_PASSWORD"), help="OAM password (defaults to $OAM_PASSWORD)")
    parser.add_option("-S", "--service", dest="service", help="OAM service base URL", default=default_service)
    parser.add_option("-v", "--verbose", dest="verbose", action="store_true", default=False, help="Verbose mode (dump HTTP errors)")
    parser.add_option("-t", "--test", dest="test", action="store_true", default=False, help="Test mode (don't post to server)")
    parser.add_option("--ask", dest="ask", action="store_true", default=False, help="Ask for username and password (using raw_input)")
    return parser

def parse_bbox(args):
    bbox = map(float, args)
    if len(bbox) != 4 or bbox[0] >= bbox[2] or bbox[1] >= bbox[3]:
        raise ClientException("You must provide a proper bounding box!")
    return bbox

def build_client(opts):
    if opts.ask:
        opts.user = raw_input("Username? ")
        opts.passwd = getpass.getpass()

    return Client(opts.user, opts.passwd, opts.service, opts.verbose, opts.test)
