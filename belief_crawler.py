#! /usr/bin/env python

from py2neo import cypher, neo4j
import pymongo as pm
import numpy as np
import math
import argparse

GRAPH_DB_URL = "http://ec2-54-187-76-157.us-west-2.compute.amazonaws.com:7474/db/data/"
DB_HOST = 'ec2-54-148-208-139.us-west-2.compute.amazonaws.com'
DB_NAME = 'backend_test_deploy'
DB_PORT = 27017

def logistic_function(x):
  return 1.0 / (1.0 + math.exp(-x))

def set_params():
    global project_weights, weight_vector, smoothing_param

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

    weight_vector = np.array([1, -1, 0.1, 0.5])
    smoothing_param = 10

def normalize_feature_vector(feature_vector):
    upvotes, downvotes = feature_vector[0], feature_vector[1]
    denom = float(upvotes + downvotes + (smoothing_param * 2))
    feature_vector[0] = (upvotes + smoothing_param) / denom
    feature_vector[1] = (downvotes + smoothing_param) / denom

def extract_features(brain_feed, node_record):
    feature_array = []
    feature_array.append(brain_feed['upvotes'])
    feature_array.append(brain_feed['downvotes'])
    feature_array.append(brain_feed['log_normalized_feed_show'])
    feature_array.append(project_weights.get(brain_feed['source_url'], 0.01))
    return np.array(feature_array)  

def get_belief_score(node_record):
    feature_vector = np.array([0] * len(weight_vector))
    if 'feed_ids' not in node_record:
        print "Node record doesn't have feed_ids:"
        print str(node_record)
        return 0.0
    for feed_id in node_record['feed_ids']:
        brain_feed = BRAIN_FEEDS.find_one({ 'jsonfeed_id': feed_id })
        if brain_feed:
            feature_vector = np.add(
                extract_features(brain_feed, node_record), feature_vector)
    normalize_feature_vector(feature_vector)
    return logistic_function(np.inner(feature_vector, weight_vector))

def set_node_belief(belief_score, node_id):
    print node_id, belief_score
    q = neo4j.CypherQuery(GRAPH_DB, 
        "MATCH (n { id: {nid}}) SET n.belief = {b_score}")
    q.run(nid=node_id, b_score=belief_score)

def crawl_nodes():
    query = neo4j.CypherQuery(GRAPH_DB, "START n=node(*) RETURN n")
    for record in query.stream():
        belief = get_belief_score(record[0])
        set_node_belief(belief, record[0]['id'])

def crawl_edges():
    query = neo4j.CypherQuery(GRAPH_DB, "")
    for record in query.stream():
        belief = get_belief_score(record[0])
        set_node_belief(belief, record[0]['id'])

def parse_args():
    """
    :return: arguments passed in on the command line as a dict. For arguments
        that are not specified, default values are inserted into the dict.
    """
    parser = argparse.ArgumentParser(
        description='Crawls nodes or edges of the graph to add beliefs.')
    parser.add_argument('-c', help='entity to crawl - edges (default) or nodes',
        default='edges', type=str)
    args = vars(parser.parse_args())
    return args

def main():
    global BRAIN_FEEDS, GRAPH_DB
    set_params()
    client = pm.MongoClient(DB_HOST, DB_PORT)
    db = client[DB_NAME]
    BRAIN_FEEDS = db['brain_feeds']
    GRAPH_DB = neo4j.GraphDatabaseService(GRAPH_DB_URL)
    if parse_args()['c'] == 'edges':
        crawl_edges()
    else:
        crawl_nodes()

if __name__ == '__main__':
    main()