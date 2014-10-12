import ConfigParser
import pymongo as pm
from datetime import datetime 
import numpy as np
import importlib
import sys
sys.path.insert(0,'/var/www/Backend/Backend/')
#import settings as setfile

#host = setfile.DATABASES['default']['HOST']
#dbname = setfile.DATABASES['default']['NAME']
#port = int(setfile.DATABASES['default']['PORT'])

def readConfigFile():
    global setfile
    config = ConfigParser.ConfigParser()
    config.read('/tmp/backend_uwsgi_setting')
    env = config.get('uwsgi','env')
    setting_file_name = env.strip().split('.')[1]
    setfile = importlib.import_module(setting_file_name)	

def updatescore():
    set_params()
    client = pm.MongoClient(host,port)
    db = client[dbname]
    brain_feeds = db['brain_feeds']

    feeds_to_update = brain_feeds.find({"update_score" : True})
    for feeds in feeds_to_update:
        project_name = feeds['source_url']
        netvotes = int(feeds['upvotes']) - int(feeds['downvotes'])
        created_at = feeds['created_at']
        inverse_feed_weight = feeds['log_normalized_feed_show']
        new_score = strategy_2(project_name, netvotes, created_at, project_weights, inverse_feed_weight)
        print "old score ",feeds['score']
        print feeds['_id']
        print "new score ",new_score
        print "*************************************"
        brain_feeds.update({'_id':feeds['_id']},{'$set':{'score' : new_score, 'update_score' : False}},upsert=False,multi=False)
        

def set_params():
    global project_weights
    project_weights = {
        'http://robobrain.me' : 0.13, 
        'hallucinating humans' : 0.13, 
        'http://wordnet.princeton.edu/' : 0.09, 
        'http://tellmedave.cs.cornell.edu' : 0.13,
        'http://pr.cs.cornell.edu/anticipation/' : 0.13,
        'http://pr.cs.cornell.edu/sceneunderstanding/' : 0.13,
        'http://pr.cs.cornell.edu/hallucinatinghumans/' : 0.13,
        'http://h2r.cs.brown.edu/projects/grounded-language-understanding/' : 0.13
    }

def strategy_1(project_name, netvotes, created_at, project_weights, inverse_feed_weight = 1.0):
    """
        score = (project_wt / inverse_feed_weight) * (log10(netvotes) + t/45000)
    """
    
    time_since = datetime(2005,1,1,0,0,0,0)
    inverse_feed_weight = 1.0
    timediff = created_at - time_since
    deltatime_in_seconds = timediff.seconds + timediff.days*24*3600

    score = 0.0

    if netvotes > 0:
        score += np.log10(netvotes)

    score += deltatime_in_seconds*1.0/45000.0 

    score *= project_weights[project_name]*score
    
    return score

def strategy_2(project_name, netvotes, created_at, project_weights, inverse_feed_weight):
    """
        score = (project_wt / inverse_feed_weight) * (log10(netvotes) + t/45000)
    """
    
    time_since = datetime(2005,1,1,0,0,0,0)
    timediff = created_at - time_since
    deltatime_in_seconds = timediff.seconds + timediff.days*24*3600

    score = 0.0

    if project_name in project_weights.keys():

        if netvotes > 0:
            score += np.log10(netvotes)

        score += deltatime_in_seconds*1.0/45000.0 

        score *= project_weights[project_name]

        score /= inverse_feed_weight
    
    return score

if __name__ == "__main__":
    global host, dbname, port, setfile
    readConfigFile()
    updatescore()

    host = setfile.DATABASES['default']['HOST']
    dbname = setfile.DATABASES['default']['NAME']
    port = int(setfile.DATABASES['default']['PORT'])
