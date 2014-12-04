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
MAX_BRAIN_FEED_SCORE = 1000

def logistic_function(x):
  return 1.0 / (1.0 + math.exp(-x))

def set_params():
    global project_weights, username_weights, node_weight_vector, \
        edge_weight_vector, smoothing_param

    project_weights = {
        'http://robobrain.me' : 0.6, 
        'hallucinating humans' : 0.8, 
        'http://wordnet.princeton.edu/' : 0.5, 
        'http://tellmedave.cs.cornell.edu' : 0.6,
        'http://pr.cs.cornell.edu/anticipation/' : 0.8,
        'http://pr.cs.cornell.edu/sceneunderstanding/' : 0.8,
        'http://pr.cs.cornell.edu/hallucinatinghumans/' : 0.8,
        'http://h2r.cs.brown.edu/projects/grounded-language-understanding/' : 0.8,
        'http://sw.opencyc.org': 0.5
    }

    username_weights = {
        "hcaseyal": 0.6,
        "dipendra misra": 0.7,
        "hemakoppula": 0.8,
        "ozanSener": 0.8,
        "stefie10": 0.6
    }

    node_weight_vector = np.array([1, -1, 0.1, 0.5])
    edge_weight_vector = np.array([1, -1, 0.1, 0.3, 0.3, 0.3])
    smoothing_param = 10

def get_edge_type(edge_record):
    return str(edge_record.type)

def normalize_feature_vector(feature_vector):
    upvotes, downvotes = feature_vector[0], feature_vector[1]
    denom = float(upvotes + downvotes + (smoothing_param * 2))
    feature_vector[0] = (upvotes + smoothing_param) / denom
    feature_vector[1] = (downvotes + smoothing_param) / denom
    feature_vector[5] /= MAX_BRAIN_FEED_SCORE # normalize score to [0, 1]

def extract_node_features(brain_feed, node_record):
    feature_array = []
    feature_array.append(brain_feed['upvotes'])
    feature_array.append(brain_feed['downvotes'])
    feature_array.append(brain_feed['log_normalized_feed_show'])
    feature_array.append(project_weights.get(brain_feed['source_url'], 0.01))
    return np.array(feature_array)

def extract_edge_features(brain_feed, edge_record):
    feature_array = []
    feature_array.append(brain_feed['upvotes'])
    feature_array.append(brain_feed['downvotes'])
    feature_array.append(brain_feed['log_normalized_feed_show'])
    feature_array.append(project_weights.get(brain_feed['source_url'], 0.01))
    feature_array.append(username_weights.get(brain_feed['username'], 0.3))
    feature_array.append(brain_feed['score'])
    return np.array(feature_array)  

def get_belief_score(record, is_node=True):
    extract_features = extract_node_features if is_node else extract_edge_features
    weight_vector = node_weight_vector if is_node else edge_weight_vector
    feature_vector = np.array([0] * len(weight_vector))
    if 'feed_ids' not in record:
        print "Record doesn't have feed_ids:"
        print str(record)
        return 0.0
    for feed_id in record['feed_ids']:
        brain_feed = BRAIN_FEEDS.find_one({ 'jsonfeed_id': feed_id })
        if brain_feed:
            feature_vector = np.add(
                extract_features(brain_feed, record), feature_vector)
    normalize_feature_vector(feature_vector)
    return logistic_function(np.inner(feature_vector, weight_vector))

def set_node_belief(belief_score, node_id):
    print node_id, belief_score
    q = neo4j.CypherQuery(GRAPH_DB, 
        "MATCH (n { id: {nid}}) SET n.belief = {b_score}")
    q.run(nid=node_id, b_score=belief_score)

def set_edge_belief(belief_score, node_a_id, node_b_id):
    print node_a_id, '->', node_b_id, ':', belief_score
    q = neo4j.CypherQuery(GRAPH_DB, 
        "MATCH (a {id: {aid}})-[r]->(b {id: {bid}}) SET r.belief = {b_score}")
    q.run(aid=node_a_id, bid=node_b_id, b_score=belief_score)

def crawl_nodes():
    query = neo4j.CypherQuery(GRAPH_DB, "START n=node(*) RETURN n")
    for record in query.stream():
        belief = get_belief_score(record[0])
        set_node_belief(belief, record[0]['id'])

def crawl_edges():
    query = neo4j.CypherQuery(GRAPH_DB, "MATCH (a)-[r]->(b) RETURN a, r, b")
    for record in query.stream():
        belief = get_belief_score(record[1], is_node=False)
        set_edge_belief(belief, record[0]['id'], record[2]['id'])

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