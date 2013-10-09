from docopt import docopt
from flask import Flask
from math import sin, cos, atan2, sqrt, radians
import os
import re
import time
import urllib
import urllib2


app = Flask(__name__)

# Distance in kms given two (lat, long) coordinates, using Haversine formula
def distance(c1, c2):
    (lat1, lng1), (lat2, lng2) = c1, c2
    [radLat1, radLng1, radLat2, radLng2] = map(radians,
                                               [lat1, lng1, lat2, lng2])
    dlat = radLat2 - radLat1
    dlng = radLng2 - radLng1
    a = (sin(dlat/2) * sin(dlat/2) +
         sin(dlng/2) * sin(dlng/2) * cos(radLat1) * cos(radLat1))
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    return 6371 * c


def mapImage(pivot, entries):
    (plat, plng) = pivot
    markers_str = "markers=color:blue%%7C%f,%f" % (plat, plng)
    for i in xrange(len(entries)):
        ((lat, lng), a, b) = entries[i]
        markers_str += "&markers=color:yellow%%7Clabel:%c%%7C%f,%f" % (
            chr(ord('A')+i), lat, lng)
    return ("http://maps.googleapis.com/maps/api/staticmap?"
            "center=%f,%f&zoom=13&size=400x400&%s&sensor=false" %
            (plat, plng, markers_str))


def pois_from_poi_file(poiFile):
    # Read Points of Interest file
    poislines = []
    with open(poiFile, 'r') as f:
        poislines = [a.strip() for a in f.readlines()]
    return [(poislines[2*i], (float(poislines[2*i+1].split()[0]),
                              float(poislines[2*i+1].split()[1])), [])
            for i in xrange(len(poislines)/2)]


def html(query):
    radius = 0.5
    maxResults = 100
    clprefix = "sfbay"
    poiFile = "geoloc.out"

    # Parameters that will be used to search craigslist
    url_params = {
        'minAsk': 0,
        'maxAsk': 5000,
        'bedrooms': 1,
        'hasPic': 1,
        'query': query,
    }

    pois = pois_from_poi_file(poiFile)

    # Searches results on craigslis
    count = 0
    pages = 0

    while count < maxResults:
        url = 'http://%s.craigslist.org/search/apa?s=%d&%s' % (
            clprefix, pages * 100, urllib.urlencode(url_params))
        response = urllib2.urlopen(url)
        html = response.read()

        hasResults = False

        for entry in re.finditer(
                ('<p class="row" data-latitude="([^"]+)" data-longitude='
                 '"([^"]+)".+?href="([^"]+).+?"date">([^<]+).+?html">([^<]+)'
                 '.+?price">([^<]+).+?small>([^<]+)'), html, re.DOTALL):
            hasResults = True
            latlng = (float(entry.group(1)), float(entry.group(2)))
            obj = (latlng, entry.group(3), " ".join([entry.group(i) for i in xrange(4, 8)]))

            poiToAdd = (None, 1e500)

            for (name, pos, entries) in pois:
                thisDistance = distance(latlng, pos)
                # Using 10-meter tolerance
                if thisDistance < radius + 1e-2:
                    # Make sure an entry is associated only to the closest POI
                    (entryList, dist) = poiToAdd
                    if dist > thisDistance:
                        poiToAdd = (entries, thisDistance)

            (entryList, dist) = poiToAdd

            if entryList is not None:
                entryList.append(obj)

            count += 1

        # Let's not abuse craigslist :)
        time.sleep(1)
        pages += 1

        # Next page is showing no results, finishes the search
        if not hasResults:
            break

    # Output
    output_html = """
    <html>
    <head>
    <style type='text/css'>
    a:link {text-decoration:none; color: blue}
    a:visited {text-decoration:none; color: blue}
    a:hover {text-decoration:none; color: blue; background-color: #c0c0c0}
    a:active {text-decoration:none; color: blue; background-color: #c0c0c0}
    </style>
    </head>
    <body>%d Entries analyzed""" % count

    for (name, pos, entries) in pois:
        if len(entries) == 0:
            continue
        output_html += ("<table style='border:0'><tr><td colspan=2 style="
               "'background-color:grey;font-weight:bold'>%d places "
               "close to %s:</td></tr>" % (len(entries), name))
        output_html += ("<tr><td style='vertical-align: top'><img src=\"%s\"/>"
               "</td><td style='vertical-align: top; font-weight:bold'>" %
               mapImage(pos, entries))
        letter = 'A'
        for (latlng, apid, desc) in entries:
            output_html += ("%c: <a href=\"http://%s.craigslist.org%s\">"
                   "[%.4f km] %s</a><br/>" % (letter, clprefix, apid,
                                              distance(latlng, pos), desc))
            letter = chr(ord(letter)+1)
        output_html += "</td></tr></table><hr/>"

    output_html += "</body></html>"

    return output_html


@app.route('/')
def index():
    return 'Use /q/querycity '


@app.route('/q/<city>')
def query(city):
    return html(city)
