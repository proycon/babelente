#!/usr/bin/env python3

# Maarten van Gompel (proycon)
# Centre for Language and Speech Technology
# Radboud University Nijmegen
# GNU Public License v3

import sys
import argparse
import json
import requests
import numpy as np
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
            return linenr, offset - begin
    raise ValueError("Unable to resolve offset " + str(offset))

def findentities(lines, lang, args):
    """Find entities using BabelFy given a set of input lines"""
    babelfy_params = dict()
    babelfy_params['lang'] = lang.upper()
    if args.cands is not None:
        babelfy_params['cands'] = args.cands
    if args.anntype is not None:
        babelfy_params['annType'] = args.anntype
    if args.annres is not None:
        babelfy_params['annres'] = args.annres
    if args.th is not None:
        babelfy_params['th'] = args.th
    if args.match is not None:
        babelfy_params['match'] = args.match
    if args.mcs is not None:
        babelfy_params['MCS'] = args.mcs
    if args.dens:
        babelfy_params['dens'] = "true"
    if args.extaida:
        babelfy_params['extAida'] = "true"
    if args.postag is not None:
        babelfy_params['posTag'] = args.postag
    babelclient = BabelfyClient(args.apikey, babelfy_params)
    #babelclient = BabelfyClient(apikey, {'lang': lang.upper()})
    for text, firstlinenr, lastlinenr, offsetmap in gettextchunks(lines, maxchunksize=4096):
        if args.dryrun:
            print("Would run query for firstlinenr=" + str(firstlinenr) + ", lastlinenr=" + str(lastlinenr), " text=" + text,file=sys.stderr)
            print("Offsetmap:", repr(offsetmap), file=sys.stderr)
        else:
            babelclient.babelfy(text)
            for entity in babelclient.entities:
                entity['linenr'], entity['offset'] = resolveoffset(offsetmap, entity['start'])
                yield entity

def compute_coverage_line(line, linenr, entities):
    """Computes coverage of entities; expresses as ratio of characters covered; for a single line"""
    charmask = np.zeros(len(line), dtype=np.int8)
    for entity in entities:
        if entity['linenr'] == linenr:
            for i in range( entity['offset'], entity['offset'] + (entity['end'] - entity['start'])+1):
                charmask[i] = 1
        elif entity['linenr'] > linenr: #they are returned in order
            break
    coverage = charmask.sum()
    print(coverage,file=sys.stderr)
    if coverage: coverage = coverage / len(charmask)
    return float(coverage)

def compute_coverage(lines, entities):
    """Computes coverage of entities; expresses as ratio of characters covered; averaged over all lines"""
    coverage = np.zeros(len(lines), dtype=np.int8)
    for i, line in enumerate(lines):
        coverage[i] = compute_coverage_line(line, i, entities)
    coverage = coverage.sum()
    if coverage: coverage = coverage / len(coverage)
    return float(coverage)


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

def evaluate(sourceentities, targetentities, sourcelines, targetlines):
    evaluation = {'perline':{} }
    overallprecision = []
    overallrecall = []
    overalltargetcoverage = []
    overallsourcecoverage = []
    linenumbers = sorted( ( entity['linenr'] for entity in sourceentities) )
    for linenr in  linenumbers:
        #check for each synset ID whether it is present in the target sentence
        sourcesynsets = set( entity['babelSynsetID'] for entity in sourceentities if entity['linenr'] == linenr  )
        targetsynsets = set( entity['babelSynsetID'] for entity in targetentities if entity['linenr'] == linenr  )
        matches = sourcesynsets & targetsynsets #intersection

        evaluation['perline'][linenr] = {'matches': len(matches), 'sources': len(sourcesynsets), 'targets': len(targetsynsets) }
        #precision (how many of the target synsets are correct?)
        #TODO: alternative precision only on the basis of source synsets?
        if targetsynsets:
            precision = len(matches)/len(targetsynsets)
            overallprecision.append(precision)
            evaluation['perline'][linenr]['precision'] = precision
            coverage = compute_coverage_line(targetlines[linenr], linenr, targetentities)
            evaluation['perline'][linenr]['targetcoverage'] = coverage
            overalltargetcoverage.append(coverage)
        else:
            evaluation['perline'][linenr]['targetcoverage'] = 0.0
            overalltargetcoverage.append(0.0)

        #recall (how many of the source synsets are found?)
        if sourcesynsets:
            recall = len(matches)/len(sourcesynsets)
            overallrecall.append(recall)
            evaluation['perline'][linenr]['recall'] = recall
            coverage = compute_coverage_line(sourcelines[linenr], linenr, sourceentities)
            evaluation['perline'][linenr]['sourcecoverage'] = coverage
            overallsourcecoverage.append(coverage)
        else:
            evaluation['perline'][linenr]['sourcecoverage'] = 0.0
            overallsourcecoverage.append(0.0)

    #macro averages of precision and recall
    if overallprecision:
        evaluation['precision'] = sum(overallprecision) / len(overallprecision)
    else:
        evaluation['precision'] = 0
    if overallrecall:
        evaluation['recall'] = sum(overallrecall) / len(overallrecall)
    else:
        evaluation['recall'] = 0
    if overallsourcecoverage:
        evaluation['overallsourcecoverage'] = sum(overallsourcecoverage) / len(overallsourcecoverage)
    else:
        evaluation['overallsourcecoverage'] = 0
    if overalltargetcoverage:
        evaluation['overalltargetcoverage'] = sum(overalltargetcoverage) / len(overalltargetcoverage)
    else:
        evaluation['overalltargetcoverage'] = 0
    return evaluation

def main():
    parser = argparse.ArgumentParser(description="BabelEnte: Entity extractioN, Translation and Evaluation using BabelFy", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-k','--apikey','--key', type=str,help="Babelnet API key", action='store',default="",required=False)
    parser.add_argument('-s','--sourcelang', type=str,help="Source language code", action='store',default="EN",required=False)
    parser.add_argument('-t','--targetlang', type=str,help="Target language code", action='store',default="",required=False)
    parser.add_argument('-S','--source', type=str,help="Source sentences (plain text, one per line, utf-8)", action='store',default="",required=False)
    parser.add_argument('-T','--target', type=str,help="Target sentences (plain text, one per line, utf-8)", action='store',default="",required=False)
    parser.add_argument('--evalfile', type=str,help="(Re)evaluate the supplied json file (output of babelente)", action='store',default="",required=False)
    parser.add_argument('--anntype', type=str,help="Annotation Type: Allows to restrict the disambiguated entries to only named entities (NAMED_ENTITIES), word senses (CONCEPTS) or both (ALL).", action='store',required=False)
    parser.add_argument('--annres', type=str,help="Annotation Resource: Allows to restrict the disambiguated entries to only WordNet (WN), Wikipedia (WIKI) or BabelNet (BN)", action='store',required=False)
    parser.add_argument('--th', type=float,help="Cutting Threshold (BabelFy)", action='store',required=False)
    parser.add_argument('--match', type=str,help="select the candidate extraction strategy, i.e., either only exact matching (EXACT_MATCHING) or both exact and partial matching (PARTIAL_MATCHING)", action='store',required=False)
    parser.add_argument('--mcs', type=str,help="Use this to enable or disable the most common sense backoff strategy for BabelFy (values: ON, OFF, ON_WITH_STOPWORDS)", action='store',required=False)
    parser.add_argument('--dens', help="Enable the densest subgraph heuristic during the disambiguation pipeline.", action='store_true',required=False)
    parser.add_argument('--cands', type=str,help="Use this parameter to obtain as a result of the disambiguation procedure a scored list of candidates (ALL) or only the top ranked one (TOP); if ALL is selected then --mcs and --th parameters will not be taken into account).", action='store',required=False)
    parser.add_argument('--postag', type=str,help="Use this parameter to change the tokenization and pos-tagging pipeline for your input text. Values: STANDARD, NOMINALIZE_ADJECTIVES, INPUT_FRAGMENTS_AS_NOUNS, CHAR_BASED_TOKENIZATION_ALL_NOUN", action='store',required=False)
    parser.add_argument('--extaida', help="Extend the candidates sets with the aida_means relations from YAGO.", action='store_true',required=False)
    parser.add_argument('--dryrun', help="Do not query", action='store_true',required=False)
    args = parser.parse_args()

    if not args.source and not args.target and not args.evalfile:
        print("ERROR: Specify either --source/-S (with or without --target/-T) or --evalfile. See babelente -h for usage instructions.",file=sys.stderr)
        sys.exit(2)
    if args.target and not args.source:
        print("ERROR: Specify --source/-S as well when --target/-T is used . See babelente -h for usage instructions.",file=sys.stderr)
        sys.exit(2)
    if (args.target or args.source) and not args.apikey:
        print("ERROR: Specify an API key (--apikey). Get one on http://babelnet.org/",file=sys.stderr)
        sys.exit(2)
    if args.target and not args.targetlang:
        print("ERROR: Specify a target language (-t).",file=sys.stderr)
        sys.exit(2)

    with open(args.source, 'r',encoding='utf-8') as f:
        sourcelines = [ l.strip() for l in f.readlines() ]
    if args.target:
        with open(args.target, 'r',encoding='utf-8') as f:
            targetlines = [ l.strip() for l in f.readlines() ]

        if len(sourcelines) != len(targetlines):
            print("ERROR: Expected the same number of line in source and target files, but got " + str(len(sourcelines)) + " vs " + str(len(targetlines)) ,file=sys.stderr)
            sys.exit(2)

    if args.evalfile:
        with open(args.evalfile,'rb') as f:
            data = json.load(f)
        sourceentities = data['sourceentities']
        targetentities = data['targetentities']

        print("Evaluating...",file=sys.stderr)
        evaluation = evaluate(sourceentities, targetentities, sourcelines, targetlines)
        print(json.dumps({'sourceentities':sourceentities, 'targetentities': targetentities, 'evaluation': evaluation}, indent=4,ensure_ascii=False))
        print("PRECISION=" + str(evaluation['precision']), "RECALL=" + str(evaluation['recall']), file=sys.stderr) #summary
    else:
        print("Extracting source entities...",file=sys.stderr)
        sourceentities = [ entity for  entity in findentities(sourcelines, args.sourcelang, args) if entity['isEntity'] and 'babelSynsetID' in entity ] #with sanity check

        if args.target:
            print("Extracting target entities...",file=sys.stderr)
            targetentities = [ entity for  entity in findentities(targetlines, args.targetlang, args) if entity['isEntity'] and 'babelSynsetID' in entity ] #with sanity check

            print("Evaluating...",file=sys.stderr)
            evaluation = evaluate(sourceentities, targetentities, sourcelines, targetlines)
            print(json.dumps({'sourceentities':sourceentities, 'targetentities': targetentities, 'evaluation': evaluation}, indent=4,ensure_ascii=False))
            print("PRECISION=" + str(evaluation['precision']), "RECALL=" + str(evaluation['recall']), file=sys.stderr) #summary
        else:
            print(json.dumps({'entities':sourceentities}, indent=4,ensure_ascii=False)) #MAYBE TODO: add coverage?

if __name__ == '__main__':
    main()
