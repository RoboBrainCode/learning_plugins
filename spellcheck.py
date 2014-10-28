#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Simple grammar checker

This grammar checker will fix grammar mistakes using Ginger. This code is 
borrowed from:

https://github.com/zoncoen/python-ginger/blob/master/ginger_python2.py

but has been modified for our purpose.
"""

import sys
import urllib
import urlparse
from urllib2 import HTTPError
from urllib2 import URLError
import json
import traceback

def get_ginger_url(text):
    """Get URL for checking grammar using Ginger.
    @param text English text
    @return URL
    """
    API_KEY = "6ae0c3a0-afdc-4532-a810-82ded0054236"

    scheme = "http"
    netloc = "services.gingersoftware.com"
    path = "/Ginger/correct/json/GingerTheText"
    params = ""
    query = urllib.urlencode([
        ("lang", "US"),
        ("clientVersion", "2.0"),
        ("apiKey", API_KEY),
        ("text", text)])
    fragment = ""

    return(urlparse.urlunparse((scheme, netloc, path, params, query, fragment)))


def get_ginger_result(text):
    """Get a result of checking grammar.
    @param text English text
    @return result of grammar check by Ginger, None in case of error
    """
    url = get_ginger_url(text)

    try:
        response = urllib.urlopen(url)
    except HTTPError as e:
        print("HTTP Error:", e.code)
        return None
    except URLError as e:
        print("URL Error:", e.reason)
        return None
    except IOError, (errno, strerror):
        print("I/O error (%s): %s" % (errno, strerror))
        return None
    except Exception:
        print("Generic Exception: " + traceback.format_exc())
        return None

    try:
        result = json.loads(response.read().decode('utf-8'))
    except ValueError:
        print("Value Error: Invalid server response.")
        return None

    return(result)


def correct(text):
    """
    Takes a string and returns the spell corrected one. text could be a single 
    word or an entire sentence.
    """
    original_text = text.strip()
    if len(original_text) > 600:
        print("You can't check more than 600 characters at a time.")
        quit()
    fixed_text = original_text
    results = get_ginger_result(original_text)

    # Correct grammar
    if(not results or not results["LightGingerTheTextResult"]):
        return original_text

    # Incorrect grammar
    fixed_gap = 0
    for result in results["LightGingerTheTextResult"]:
        if(result["Suggestions"]):
            from_index = result["From"]
            to_index = result["To"] + 1
            suggest = result["Suggestions"][0]["Text"]

            fixed_text = fixed_text[:from_index-fixed_gap] + suggest + fixed_text[to_index-fixed_gap:]

            fixed_gap += to_index-from_index-len(suggest)

    return fixed_text

if __name__ == '__main__':
    print correct(" ".join(sys.argv[1:]))