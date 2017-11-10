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
                text += "\n" + line
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

def findentities(lines, lang, apikey, dryrun=False):
    """Find entities using BabelFy given a set of input lines"""
    babelfy_params = dict()
    babelfy_params['lang'] = lang.upper()
    babelfy_params['cands'] = "TOP"
    babelclient = BabelfyClient(API_KEY, babelfy_params)
    #babelclient = BabelfyClient(apikey, {'lang': lang.upper()})
    for text, firstlinenr, lastlinenr, offsetmap in gettextchunks(lines, maxchunksize=4096):
        if dryrun:
            print("Would run query for firstlinenr=" + str(firstlinenr) + ", lastlinenr=" + str(lastlinenr), " text=" + text,file=sys.stderr)
            print("Offsetmap:", repr(offsetmap), file=sys.stderr)
        else:
            babelclient.babelfy(text)
            for entity in babelclient.entities:
                entity['linenr'] = resolveoffset(offsetmap, entity['start'])
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

def evaluate(sourceentities, targetentities):
    evaluation = {'perline':{} }
    overallprecision = []
    overallrecall = []
    linenumbers = sorted( ( entity['linenr'] for entity in sourceentities) )
    for linenr in  linenumbers:
        #check for each synset ID whether it is present in the target sentence
        sourcesynsets = set( entity['babelSynsetID'] for entity in sourceentities if entity['linenr'] == linenr  )
        targetsynsets = set( entity['babelSynsetID'] for entity in targetentities if entity['linenr'] == linenr  )
        matches = sourcesynsets & targetsynsets #intersection

        evaluation['perline'][linenr] = {'matches': len(matches), 'sources': len(sourcesynsets), 'targets': len(targetsynsets) }
        #precision (how many of the target synsets are correct?)
        #TODO: alternative precision only on the basis of source synsets?
        if len(targetsynsets):
            precision = len(matches)/len(targetsynsets)
            overallprecision.append(precision)
            evaluation['perline'][linenr]['precision'] = precision

        #recall (how many of the source synsets are found?)
        if len(sourcesynsets):
            recall = len(matches)/len(sourcesynsets)
            overallrecall.append(recall)
            evaluation['perline'][linenr]['recall'] = recall

    #macro averages of precision and recall
    if overallprecision:
        evaluation['precision'] = sum(overallprecision) / len(overallprecision)
    else:
        evaluation['precision'] = 0
    if overallrecall:
        evaluation['recall'] = sum(overallrecall) / len(overallrecall)
    else:
        evaluation['recall'] = 0
    return evaluation

def main():
    parser = argparse.ArgumentParser(description="BabelEnte: Entity extractioN, Translation and Evaluation using BabelFy", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-k','--apikey', type=str,help="Babelnet API key", action='store',default="",required=False)
    parser.add_argument('-s','--sourcelang', type=str,help="Source language code", action='store',default="EN",required=False)
    parser.add_argument('-t','--targetlang', type=str,help="Target language code", action='store',default="",required=False)
    parser.add_argument('-S','--source', type=str,help="Source sentences (plain text, one per line, utf-8)", action='store',default="",required=False)
    parser.add_argument('-T','--target', type=str,help="Target sentences (plain text, one per line, utf-8)", action='store',default="",required=False)
    parser.add_argument('--evalfile', type=str,help="(Re)evaluate the supplied json file (output of babelente)", action='store',default="",required=False)
    parser.add_argument('--dryrun', help="Do not query", action='store_true',required=False)
    args = parser.parse_args()

    if not args.source and not args.target and not args.evalfile:
        print("ERROR: Specify either --source/-S (with or without --target/-T) or --evalfile. See babelente -h for usage instructions.",file=sys.stderr)
        sys.exit(2)
    if args.target and not args.source:
        print("ERROR: Specify --source/-S as well when --target/-T is used . See babelente -h for usage instructions.",file=sys.stderr)
        sys.exit(2)
    if args.target or args.source and not args.apikey:
        print("ERROR: Specify an API key (--apikey). Get one on http://babelnet.org/",file=sys.stderr)
        sys.exit(2)
    if args.target and not args.targetlang:
        print("ERROR: Specify a target language (-t).",file=sys.stderr)
        sys.exit(2)

    if args.evalfile:
        with open(args.evalfile,'rb') as f:
            data = json.load(f)
        sourceentities = data['sourceentities']
        targetentities = data['targetentities']

        print("Evaluating...",file=sys.stderr)
        evaluation = evaluate(sourceentities, targetentities)
        print(json.dumps({'sourceentities':sourceentities, 'targetentities': targetentities, 'evaluation': evaluation}, indent=4,ensure_ascii=False))
        print("PRECISION=" + str(evaluation['precision']), "RECALL=" + str(evaluation['recall']), file=sys.stderr) #summary
    else:
        with open(args.source, 'r',encoding='utf-8') as f:
            sourcelines = [ l.strip() for l in f.readlines() ]
        if args.target:
            with open(args.target, 'r',encoding='utf-8') as f:
                targetlines = [ l.strip() for l in f.readlines() ]

            if len(sourcelines) != len(targetlines):
                print("ERROR: Expected the same number of line in source and target files, but got " + str(len(sourcelines)) + " vs " + str(len(targetlines)) ,file=sys.stderr)
                sys.exit(2)

        print("Extracting source entities...",file=sys.stderr)
        sourceentities = [ entity for  entity in findentities(sourcelines, args.sourcelang, args.apikey, args.dryrun) if entity['isEntity'] and 'babelSynsetID' in entity ] #with sanity check

        if args.target:
            print("Extracting target entities...",file=sys.stderr)
            targetentities = [ entity for  entity in findentities(targetlines, args.targetlang, args.apikey, args.dryrun) if entity['isEntity'] and 'babelSynsetID' in entity ] #with sanity check

            print("Evaluating...",file=sys.stderr)
            evaluation = evaluate(sourceentities, targetentities)
            print(json.dumps({'sourceentities':sourceentities, 'targetentities': targetentities, 'evaluation': evaluation}, indent=4,ensure_ascii=False))
            print("PRECISION=" + str(evaluation['precision']), "RECALL=" + str(evaluation['recall']), file=sys.stderr) #summary
        else:
            print(json.dumps({'entities':sourceentities}, indent=4,ensure_ascii=False))

if __name__ == '__main__':
    main()
