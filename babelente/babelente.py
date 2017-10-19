#!/usr/bin/env python3

# Maarten van Gompel (proycon)
# Centre for Language and Speech Technology
# Radboud University Nijmegen
# GNU Public License v3

import sys
import os
import argparse
import requests
import json
import pickle
from babelpy.babelfy import BabelfyClient


def gettextchunks(lines, maxchunksize=4096):
    """Partition lines into text chunks"""
    offsetmap = {} #(begin, end) tuple for the line
    firstlinenr = 0
    lastlinenr = 0
    text = ""
    for i, line in enumerate(lines):
        if len(text) + len(line) + 1 >= maxchunksize:
            #yield the current chunk
            if text:
                yield text, firstlinenr, lastlinenr, offsetmap

            #start a new chunk
            offsetmap = {i: (0,len(line))}
            text = line
            firstlinenr = i
            lastlinenr = i
        else:
            if text:
                begin = len(text) + 1
                text = "\n" + line
            else:
                begin = 0
                text = line
            lastlinenr = i
            offsetmap[i] = (begin, begin+len(line))

    #don't forget last one:
    if text:
        yield text, firstlinenr, lastlinenr, offsetmap

def resolveoffset(offsetmap, offset):
    """Convert a relative character offset in a chunk to an absolute line number"""
    for linenr, (begin, end) in offsetmap.items():
        if offset >= begin and offset < end:
            return linenr
    raise ValueError("Unable to resolve offset " + str(offset))

def findentities(lines, lang, apikey):
    """Find entities using BabelFy given a set of input lines"""
    babelclient = BabelfyClient(apikey, {'lang': lang.upper()})
    for text, firstlinenr, lastlinenr, offsetmap in gettextchunks(lines, maxchunksize=4096):
        babelclient.babelfy(text)
        for entity in babelclient.entities:
            entity['linenr'] = resolveoffset(entity['start'])
            yield entity

def findtranslations(synset_id, lang, apikey, cache=None):
    """Translate entity to target language (current not used!)"""
    if cache is not None:
        if synset_id in cache and lang in cache[synset_id]:
            for lemma in cache[synset_id][lang]:
                yield lemma
            return

    params = {
        'id': synset_id,
        'filterLangs': lang,
        'key': apikey,
    }
    r = requests.get("https://babelnet.io/v4/getSynset", params=params)
    data = r.json()
    #print("DEBUG getsynset id="+synset_id+",filterLangs=" + lang,file=sys.stderr)
    #print(json.dumps(data,indent=4, ensure_ascii=False),file=sys.stderr)
    for sense in data['senses']:
        yield sense['lemma']
        if cache is not None:
            if synset_id not in cache: cache[synset_id] = {}
            if lang not in cache[synset_id]: cache[synset_id][lang] = set()
            cache[synset_id][lang].add(sense['lemma'])

def main():
    parser = argparse.ArgumentParser(description="BabelEnte: Entity extractioN, Translation and Evaluation using BabelFy and Babelnet.org", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-k','--apikey', type=str,help="Babelnet API key", action='store',default="",required=True)
    parser.add_argument('-f','--sourcelang', type=str,help="Source language code", action='store',default="",required=True)
    parser.add_argument('-t','--targetlang', type=str,help="Target language code", action='store',default="",required=True)
    parser.add_argument('-S','--source', type=str,help="Source sentences (plain text, one per line, utf-8)", action='store',default="",required=True)
    parser.add_argument('-T','--target', type=str,help="Target sentences (plain text, one per line, utf-8)", action='store',default="",required=True)
    parser.add_argument('-c','--cache', type=str,help="Cache file", action='store',required=False)
    args = parser.parse_args()

    if args.cache:
        if os.path.exists(args.cache):
            with open(args.cache,'rb') as f:
                cache = pickle.load(f)
        else:
            print("Cache does not exist yet, creating new one",file=sys.stderr)
            cache = {}

    with open(args.source, 'r',encoding='utf-8') as f:
        sourcelines = [ l.strip() for l in f.readlines() ]
    with open(args.target, 'r',encoding='utf-8') as f:
        targetlines = [ l.strip() for l in f.readlines() ]

    if len(sourcelines) != len(targetlines):
        print("ERROR: Expected the same number of line in source and target files, but got " + str(len(sourcelines)) + " vs " + str(len(targetlines)) ,file=sys.stderr)
        sys.exit(2)

    sourceentities = [ (entity, linenr) for  entity, linenr in findentities(sourcelines, args.sourcelang, args.apikey) if entity['isEntity'] and 'babelSynsetID' in entity ] #with sanity check
    targetentities = [ (entity, linenr) for  entity, linenr in findentities(targetlines, args.targetlang, args.apikey) if entity['isEntity'] and 'babelSynsetID' in entity ] #with sanity check
    print(json.dumps({'sourceentities':sourceentities, 'targetentities': targetentities}, indent=4,ensure_ascii=False))
    if args.cache:
        with open(args.cache,'wb') as f:
            pickle.dump(cache, f)

if __name__ == '__main__':
    main()
