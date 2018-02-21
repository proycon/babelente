#!/usr/bin/env python3

# Maarten van Gompel (proycon)
# Centre for Language and Speech Technology
# Radboud University Nijmegen
# GNU Public License v3

import sys
import os.path
import argparse
import json
import requests
import numpy as np
import pickle
import random
from collections import Counter, defaultdict
from babelpy.babelfy import BabelfyClient
from pynlpl.formats import folia


def gettextchunks(lines, maxchunksize=4096):
    """Partition lines into text chunks"""
    offsetmap = {} #(begin, end) tuple for the line
    firstlinenr = 0
    lastlinenr = 0
    text = ""
    for i, line in enumerate(lines):
        s = text + line
        s = s.encode('utf-8')
        if len(s) + 1 >= maxchunksize:
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

def resolveoffset(offsetmap, offset, lines, entity):
    """Convert a relative character offset in a chunk to an absolute line number"""
    assert offset == entity['start']
    minoffset = maxoffset = None
    for linenr, (begin, end) in offsetmap.items():
        if offset >= begin and offset <= end:
            offset = offset-begin
            try:
                if lines[linenr][offset:offset+len(entity['text'])] != entity['text']:
                    if offset+len(entity['text']) > len(lines[linenr]):
                        print("NOTICE: Entity '" + entity['text'] + "' exceeds line boundary; marking as invalid",file=sys.stderr)
                        entity['ignore'] = True
                    else:
                        print("--ERROR--",file=sys.stderr)
                        print("Line #" + str(linenr) + ": " + lines[linenr],file=sys.stderr)
                        print("Got '" +   lines[linenr][offset:offset+len(entity['text'])] + "', expected: '" + entity['text'] + "'",file=sys.stderr)
                        raise ValueError("Resolved offset does not match text " + str(offset) + "; minoffset=" + str(minoffset) + ", maxoffset=" + str(maxoffset) + ", lines=" + str(len(offsetmap)) )
            except IndexError:
                print("--ERROR--",file=sys.stderr)
                print("Line #" + str(linenr) + ": " + lines[linenr],file=sys.stderr)
                print("Out of bounds, expected: '" + entity['text'] + "'",file=sys.stderr)
                raise ValueError("Resolved offset does not match text " + str(offset) + "; minoffset=" + str(minoffset) + ", maxoffset=" + str(maxoffset) + ", lines=" + str(len(offsetmap)) )
            return linenr, offset
        if minoffset is None or begin < minoffset: minoffset = begin
        if maxoffset is None or end > maxoffset: maxoffset = end
    raise ValueError("Unable to resolve offset " + str(offset) + "; minoffset=" + str(minoffset) + ", maxoffset=" + str(maxoffset) + ", lines=" + str(len(offsetmap)) )

def findentities(lines, lang, args, cache=None):
    """Find entities using BabelFy given a set of input lines"""
    babelfy_params = dict()
    babelfy_params['lang'] = lang.upper()
    if args.cands is not None:
        babelfy_params['cands'] = args.cands
    if args.anntype is not None:
        babelfy_params['annType'] = args.anntype
    if args.annres is not None:
        babelfy_params['annRes'] = args.annres
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
    for i, (text, firstlinenr, lastlinenr, offsetmap) in enumerate(gettextchunks(lines, maxchunksize=4096)):
        if args.dryrun:
            print("---\nCHUNK #" + str(i) + ". Would run query for firstlinenr=" + str(firstlinenr) + ", lastlinenr=" + str(lastlinenr), " text=" + text,file=sys.stderr)
            print("Offsetmap:", repr(offsetmap), file=sys.stderr)
        elif cache is not None and text in cache:
            entities = cache[text]
            print("chunk #" + str(i) + " -- retrieved from cache",file=sys.stderr)
        else:
            print("chunk #" + str(i) + " -- querying BabelFy",file=sys.stderr)
            babelclient.babelfy(text)
            entities = babelclient.entities
            if cache is not None: cache[text] = entities #put in cache
        if not args.dryrun:
            for j, entity in enumerate(resolveoverlap(entities, args.overlap)):
                try:
                    entity['linenr'], entity['offset'] = resolveoffset(offsetmap, entity['start'], lines, entity)
                    if 'ignore' not in entity or not entity['ignore']:
                        yield entity
                except ValueError as e:
                    print("---\nCHUNK #" + str(i) + " ENTITY #" + str(j) + ". Ran query for firstlinenr=" + str(firstlinenr) + ", lastlinenr=" + str(lastlinenr), " text=" + text,file=sys.stderr)
                    print("Entity:", repr(entity), file=sys.stderr)
                    print("Offsetmap:", repr(offsetmap), file=sys.stderr)
                    raise e

def resolveoverlap(entities, overlapstrategy):
    overlapstrategy = overlapstrategy.lower()
    if overlapstrategy in ('allow','yes'):
        for entity in entities:
            yield entity
    else:
        for i, entity in enumerate(entities):
            if 'skip' not in entity:
                best = True
                if overlapstrategy == 'longest':
                    score = entity['end'] - entity['start'] #measure in characters
                elif overlapstrategy == 'score':
                    score = entity['score']
                elif overlapstrategy == 'globalscore':
                    score = entity['globalScore']
                elif overlapstrategy == 'coherencescore':
                    score = entity['coherenceScore']
                else:
                    raise ValueError("Invalid overlap strategy: " + overlapstrategy)

                overlaps = []

                #find overlapping entities for the entity under consideration
                for j, entity2 in enumerate(entities):
                    if i != j:
                        #does this entity overlap?
                        if (entity2['tokenFragment']['start'] >= entity['tokenFragment']['start'] and entity2['tokenFragment']['start'] <=  entity['tokenFragment']['end']) or (entity2['tokenFragment']['end'] >= entity['tokenFragment']['start'] and entity2['tokenFragment']['end'] <=  entity['tokenFragment']['end']):
                            overlaps.append(entity2)
                            if overlapstrategy == 'longest':
                                score2 = entity2['end'] - entity2['start']
                            elif overlapstrategy == 'score':
                                score2 = entity2['score']
                            elif overlapstrategy == 'globalscore':
                                score2 = entity2['globalScore']
                            elif overlapstrategy == 'coherencescore':
                                score2 = entity2['coherenceScore']
                            if score2 > score:
                                best = False

                entity['overlaps'] = len(overlaps)
                if best:
                    yield entity
                    for entity2 in overlaps:
                        entity2['skip'] = True


def compute_coverage_line(line, linenr, entities):
    """Computes coverage of entities; expressed as ratio of characters covered; for a single line"""
    l = len(line)
    charmask = np.zeros(l, dtype=np.int8)
    for entity in entities:
        if entity['linenr'] == linenr:
            for i in range( entity['offset'], entity['offset'] + (entity['end'] - entity['start'])+1):
                if i < l:
                    charmask[i] = 1
                else:
                    print("WARNING: coverage out of range: ",i," in ",l,file=sys.stderr)
        elif entity['linenr'] > linenr: #they are returned in order
            break
    coverage = charmask.sum()
    if coverage: coverage = coverage / len(charmask)
    return float(coverage)

def compute_coverage(lines, entities):
    """Computes coverage of entities; expressed as ratio of characters covered; averaged over all lines"""
    coverage = np.zeros(len(lines), dtype=np.int8)
    for i, line in enumerate(lines):
        coverage[i] = compute_coverage_line(line, i, entities)
    coverage = coverage.sum()
    if coverage: coverage = coverage / len(coverage)
    return float(coverage)


def findtranslations(synset_id, lang, apikey, cache=None, debug=False):
    """Translate entity to target language (used for recall computation only now)"""
    if cache is not None:
        if synset_id in cache and lang in cache[synset_id]:
            for lemma in cache[synset_id][lang]:
                yield lemma
            return

    params = {
        'id': synset_id,
        'filterLangs': lang.upper(),
        'key': apikey,
    }
    r = requests.get("https://babelnet.io/v4/getSynset", params=params)
    data = r.json()
    if debug:
        print("DEBUG getsynset id="+synset_id+",filterLangs=" + lang,file=sys.stderr)
        print(json.dumps(data,indent=4, ensure_ascii=False),file=sys.stderr)
    if 'senses' in data:
        for sense in data['senses']:
            if 'lemma' in sense and 'language' in sense and sense['language'].lower() == lang.lower():
                yield sense['lemma']
                if cache is not None:
                    if synset_id not in cache: cache[synset_id] = {}
                    if lang not in cache[synset_id]: cache[synset_id][lang] = set()
                    cache[synset_id][lang].add(sense['lemma'])

def evaluate(sourceentities, targetentities, sourcelines, targetlines, do_recall, targetlang, apikey, nodup, cache=None, debug=False):
    evaluation = {'perline':{} }
    overallprecision = []
    overallrecall = []
    overalltargetcoverage = []
    overallsourcecoverage = []
    #sets for micro-averages:
    allmatches = Counter()
    alltargetsynsets = Counter()
    alltranslatableentities = Counter()

    for linenr in range(0,len(sourcelines)):
        #check for each synset ID whether it is present in the target sentence
        sourcesynsets = Counter()
        targetsynsets = Counter()
        synset2text = defaultdict(list) #synset => text
        for entity in sourceentities:
            if entity['linenr'] == linenr:
                sourcesynsets[entity['babelSynsetID']] += 1
                if do_recall:
                    synset2text[entity['babelSynsetID']].append(entity['text'])
        for entity in targetentities:
            if entity['linenr'] == linenr:
                targetsynsets[entity['babelSynsetID']] += 1
        matches = sourcesynsets & targetsynsets #intersection

        if nodup:
            #normalize, no duplicates:
            sourcesynsets = Counter({ k:1 for k,v in sourcesynsets.items()})
            targetsynsets = Counter({ k:1 for k,v in targetsynsets.items()})
            matches = Counter({ k:1 for k,v in matches.items()})


        #Besides the scores and the full JSON output, it would be very helpful to get a focused list of the matching pairs like this:
        # purpose:printing a list of all matching items (tab separated):
        # sentence-nr babelsynsetid source-text-id target-text-id
        # example: 684 bn:00019586n classroom Klassenraum
        for match, freq in matches.items():
            sourcetext = "{?}"
            for entity in sourceentities:
                if entity['linenr'] == linenr and entity['babelSynsetID'] == match:
                    sourcetext = entity['text']
                    break
            targettext = "{?}"
            for entity in targetentities:
                if entity['linenr'] == linenr and entity['babelSynsetID'] == match:
                    targettext = entity['text']
                    break
            print("@" + str(linenr) + "\t" + match + "\t" + sourcetext + "\t" + targettext + "\t" + str(freq), file=sys.stderr)


        allmatches += matches
        alltargetsynsets += targetsynsets

        evaluation['perline'][linenr] = {'matches': sum(matches.values()), 'sources': sum(sourcesynsets.values()), 'targets': sum(targetsynsets.values()) }
        #precision (how many of the target synsets are correct?)
        if targetsynsets:
            precision = sum(matches.values())/sum(targetsynsets.values())
            overallprecision.append(precision)
            evaluation['perline'][linenr]['precision'] = precision
            coverage = compute_coverage_line(targetlines[linenr], linenr, targetentities)
            evaluation['perline'][linenr]['targetcoverage'] = coverage
            overalltargetcoverage.append(coverage)
        else:
            evaluation['perline'][linenr]['targetcoverage'] = 0.0
            overalltargetcoverage.append(0.0)
            overallprecision.append(0.0)

        if do_recall:
            #compute how many of the source synsets have corresponding translations in the target language
            #this creates a hypothetical upper bound for recall computation
            #(will query babel.net extensively, hence optional!)
            #print("\tL" + str(linenr+1) + " - Computing recall...",end="", file=sys.stderr)
            translatableentities = Counter()
            translations = {}
            for synset_id, freq in sourcesynsets.items():
                targetlemmas = set(findtranslations(synset_id, targetlang, apikey, cache,debug))
                if len(targetlemmas) > 0:
                    #we have a link
                    translatableentities[synset_id] += freq
                    translations[synset_id] = targetlemmas
                    if synset_id not in matches:
                        print("!" + str(linenr) + "\tMISSED\t"+synset_id+"\t" + ";".join(synset2text[synset_id]) + "\t" + ";".join(translations[synset_id]) + "\t" + str(freq), file=sys.stderr)
            #print(sum(translatableentities.values()),file=sys.stderr)

            if translatableentities:
                recall = sum(matches.values())/sum(translatableentities.values())
                overallrecall.append(recall)
                evaluation['perline'][linenr]['recall'] = recall
                evaluation['perline'][linenr]['translatableentities'] = sum(translatableentities.values())
                alltranslatableentities += translatableentities
            else:
                evaluation['perline'][linenr]['recall'] = 0.0
                overallrecall.append(0.0)

        if sourcesynsets:
            coverage = compute_coverage_line(sourcelines[linenr], linenr, sourceentities)
            evaluation['perline'][linenr]['sourcecoverage'] = coverage
            overallsourcecoverage.append(coverage)
        else:
            evaluation['perline'][linenr]['sourcecoverage'] = 0.0
            overallsourcecoverage.append(0.0)


    #macro averages of precision and recall
    if overallprecision:
        evaluation['precision'] = sum(overallprecision) / len(overallprecision)
        print( "macroprec = sum-overallprec" + str(sum(overallprecision)), "len_overallprecision)" + str(len(overallprecision)), file=sys.stderr)
    else:
        evaluation['precision'] = 0
    if overallrecall:
        evaluation['recall'] = sum(overallrecall) / len(overallrecall)
    else:
        evaluation['recall'] = 0
    if overallsourcecoverage:
        evaluation['sourcecoverage'] = sum(overallsourcecoverage) / len(overallsourcecoverage)
    else:
        evaluation['sourcecoverage'] = 0
    if overalltargetcoverage:
        evaluation['targetcoverage'] = sum(overalltargetcoverage) / len(overalltargetcoverage)
    else:
        evaluation['targetcoverage'] = 0
    if alltargetsynsets:
        evaluation['microprecision'] = sum(allmatches.values()) / sum(alltargetsynsets.values())
        print( "microprec = sum_allmatches " + str(sum(allmatches.values())), " / sum_alltargetsynset " + str(sum(alltargetsynsets.values())), file=sys.stderr)
    else:
        evaluation['microprecision'] = 0
    if alltranslatableentities:
        evaluation['microrecall'] = sum(allmatches.values()) / sum(alltranslatableentities.values())
        print("microrecall=sum_allmatches " + str(sum(allmatches.values())), " / sum_alltranslatableentities " + str(sum(alltranslatableentities.values())), file=sys.stderr)
    else:
        evaluation['microrecall'] = 0
    evaluation['translatableentities'] = sum(alltranslatableentities.values()) #macro
    evaluation['matches'] = sum(allmatches.values())  #macro
    print( "lines:" + str(len(sourcelines)), file=sys.stderr)
    return evaluation

def processfolia(doc, args, cache):
    doc.declare(folia.Entity, set=args.foliaset, annotator='babelente',annotatortype=folia.AnnotatorType.AUTO)
    doc.declare(folia.Alignment, set=args.foliaalignset, annotator='babelente',annotatortype=folia.AnnotatorType.AUTO)
    doc.declare(folia.Metric, set=args.foliametricset, annotator='babelente',annotatortype=folia.AnnotatorType.AUTO)

    processed = set()
    data = []
    for word in doc.words():
        parent = word.ancestor(folia.AbstractStructureElement)
        if not hasattr(parent, '_babelente_processed'):
            parent._babelente_processed = True
            words = list(parent.select(folia.Word))
            data.append( (parent, words, " ".join([ str(word) for word in words]) ) )

    entities = [ entity for  entity in findentities([x[2] for x in data], args.sourcelang, args, None if cache is None else cache['source']) if entity['isEntity'] and 'babelSynsetID' in entity ] #with sanity check

    #add entities to the FoLiA document
    for entity in entities:
        linenr = entity['linenr']
        parent, words, text = data[linenr]
        tokenstart = int(entity['tokenFragment']['start'])
        tokenend = int(entity['tokenFragment']['end'])
        span = words[tokenstart:tokenend+1]
        entity['span'] = [ word.id for word in span ]
        entity['spantext'] = [ str(word) for word in span ]
        entity['docfile'] = doc.filename
        entity['docid'] = doc.id
        print(entity, ",")

        foliaentity = parent.add(folia.Entity, *span, set=args.foliaset, cls=entity['babelSynsetID'].replace('bn:',''), generate_id_in=parent, confidence=float(entity['score']))
        foliaentity.add(folia.Description, value=entity['text'])
        if 'DBpediaURL' in entity and entity['DBpediaURL']:
            url = entity['DBpediaURL'].replace('/resource/','/data/') + '.rdf'
            alignment = foliaentity.add(folia.Alignment, cls="dbpedia", href=url, set=args.foliaalignset, format="application/rdf+xml")
            alignment.add(folia.AlignReference, id=entity['DBpediaURL'])
        if 'BabelNetURL' in entity and entity['BabelNetURL']:
            url = entity['BabelNetURL'].replace('/rdf/','/rdf/data/')
            alignment = foliaentity.add(folia.Alignment, cls="babelnet", href=entity['BabelNetURL'], set=args.foliaalignset, format="application/rdf+xml")
            alignment.add(folia.AlignReference, id=entity['BabelNetURL'])

def stripmultispace(line):
    line = line.strip()
    return " ".join([ w for w in line.split(" ") if w ])

def main():
    parser = argparse.ArgumentParser(description="BabelEnte: Entity extractioN, Translation and Evaluation using BabelFy", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-k','--apikey','--key', type=str,help="Babelnet API key", action='store',default="",required=False)
    parser.add_argument('-s','--sourcelang', type=str,help="Source language code", action='store',default="EN",required=False)
    parser.add_argument('-t','--targetlang', type=str,help="Target language code", action='store',default="",required=False)
    parser.add_argument('-S','--source', type=str,help="Source sentences (plain text, one per line, utf-8)", action='store',default="",required=False)
    parser.add_argument('-T','--target', type=str,help="Target sentences (plain text, one per line, utf-8)", action='store',default="",required=False)
    parser.add_argument('-r', '--recall',help="Compute recall as well using Babel.net (results in many extra queries!)", action='store_true',required=False)
    parser.add_argument('-o', '--outputdir',type=str,help="Output directory when processing FoLiA documents (set to /dev/null to skip output alltogether)", action='store',default="./", required=False)
    parser.add_argument('-d', '--debug',help="Debug", action='store_true',required=False)
    parser.add_argument('--nodup', help="Filter out duplicate entities in evaluation", action='store_true',required=False)
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
    parser.add_argument('--overlap',type=str, help="Resolve overlapping entities, can be set to allow (default), longest, score, globalscore, coherencescore", action='store',default='allow',required=False)
    parser.add_argument('--cache',type=str, help="Cache file, stores queries to prevent excessive querying of BabelFy (warning: not suitable for parallel usage!)", action='store',required=False)
    parser.add_argument('--dryrun', help="Do not query", action='store_true',required=False)
    parser.add_argument('inputfiles', nargs='*', help='FoLiA input documents, use with -s to choose source language. For tramooc style usage: use -S/-T or --evalfile instead of this.')
    #hidden power options:
    parser.add_argument('--foliaset',type=str, help=argparse.SUPPRESS, action='store',default="https://raw.githubusercontent.com/proycon/babelente/master/setdefinitions/babelente.babelnet.ttl", required=False)
    parser.add_argument('--foliaalignset',type=str, help=argparse.SUPPRESS, action='store',default="https://raw.githubusercontent.com/proycon/babelente/master/setdefinitions/babelente.alignments.ttl", required=False)
    parser.add_argument('--foliametricset',type=str, help=argparse.SUPPRESS, action='store',default="https://raw.githubusercontent.com/proycon/babelente/master/setdefinitions/babelente.metrics.ttl", required=False)
    args = parser.parse_args()

    if not args.source and not args.target and not args.evalfile and not args.inputfiles:
        print("ERROR: For Tramooc style usage, specify either --source/-S (with or without --target/-T, or --evalfile.", file=sys.stderr)
        print("       For entity extraction & linking on FoLiA documents, just specify one or more FoLiA documents", file=sys.stderr)
        print("        along with --sourcelang to choose source language.", file=sys.stderr)
        print("       See babelente -h for full usage instructions.",file=sys.stderr)
        sys.exit(2)
    if args.target and not args.source:
        print("ERROR: Specify --source/-S as well when --target/-T is used . See babelente -h for usage instructions.",file=sys.stderr)
        sys.exit(2)
    if (args.target or args.source or args.inputfiles) and not args.apikey:
        print("ERROR: Specify an API key (--apikey). Get one on http://babelnet.org/",file=sys.stderr)
        sys.exit(2)
    if args.target and not args.targetlang:
        print("ERROR: Specify a target language (-t).",file=sys.stderr)
        sys.exit(2)

    if args.inputfiles:
        if not args.sourcelang:
            print("ERROR: Specify a source language (-s)",file=sys.stderr)
            sys.exit(2)
        first = True
        textdoc = False
        for filename in args.inputfiles:
            if not os.path.exists(filename):
                print("ERROR: No such file: " + filename)
                sys.exit(2)
            if filename[-3:].lower() == ".xml":
                #FoLiA based, extraction only
                print("Loading FoLiA document " + filename + " ...",file=sys.stderr)
                doc = folia.Document(file=filename)
                if first:
                    print("[")
                    first = False
                processfolia(doc, args, None)

                if args.outputdir != '/dev/null':
                    outputname = os.path.basename(filename)
                    if outputname.endswith('.folia.xml'):
                        outputname = outputname.replace('.folia.xml','.babelente.folia.xml')
                    elif outputname.endswith('.xml'):
                        outputname = outputname.replace('.xml','.babelente.folia.xml')
                    else:
                        outputname = outputname + '.babelente.folia.xml'
                    doc.save(os.path.join(args.outputdir,outputname))
            else:
                #text-based
                textdoc = True
                print("Loading text document " + filename + " ...",file=sys.stderr)
                args.source = filename
                break

        if not textdoc:
            print("{}")
            print("]")
            return True

    #Tramooc-style extraction, translation and evaluation
    with open(args.source, 'r',encoding='utf-8') as f:
        sourcelines = [ stripmultispace(l) for l in f.readlines() ]

    if args.target:
        with open(args.target, 'r',encoding='utf-8') as f:
            targetlines = [ stripmultispace(l) for l in f.readlines() ]

        if len(sourcelines) != len(targetlines):
            print("ERROR: Expected the same number of line in source and target files, but got " + str(len(sourcelines)) + " vs " + str(len(targetlines)) ,file=sys.stderr)
            sys.exit(2)

    if args.cache:
        if os.path.exists(args.cache):
            print("Loading cache from " + args.cache,file=sys.stderr)
            with open(args.cache, 'rb') as f:
                cache = pickle.load(f)
        else:
            print("Creating new cache " + args.cache,file=sys.stderr)
            cache = {'source':{}, 'target': {}, 'synsets_source': {}, 'synsets_target': {}}
    else:
        cache = None

    evaluation = None
    if args.evalfile:
        with open(args.evalfile,'rb') as f:
            data = json.load(f)
        sourceentities = data['sourceentities']
        targetentities = data['targetentities']

        print("Evaluating...",file=sys.stderr)
        evaluation = evaluate(sourceentities, targetentities, sourcelines, targetlines, args.recall, args.targetlang, args.apikey, args.nodup, None if cache is None else cache['synsets_source'], args.debug)
    else:
        print("Extracting source entities...",file=sys.stderr)
        sourceentities = [ entity for  entity in findentities(sourcelines, args.sourcelang, args, None if cache is None else cache['source']) if entity['isEntity'] and 'babelSynsetID' in entity ] #with sanity check

        if args.target:
            print("Extracting target entities...",file=sys.stderr)
            targetentities = [ entity for  entity in findentities(targetlines, args.targetlang, args, None if cache is None else cache['target']) if entity['isEntity'] and 'babelSynsetID' in entity ] #with sanity check

            print("Evaluating...",file=sys.stderr)
            evaluation = evaluate(sourceentities, targetentities, sourcelines, targetlines, args.recall, args.targetlang, args.apikey, args.nodup, None if cache is None else cache['synsets_target'], args.debug)
        else:
            print(json.dumps({'entities':sourceentities}, indent=4,ensure_ascii=False)) #MAYBE TODO: add coverage?

    if evaluation is not None:
        print(json.dumps({'sourceentities':sourceentities, 'targetentities': targetentities, 'evaluation': evaluation}, indent=4,ensure_ascii=False))
        #output summary to stderr (info is all in JSON stdout output as well)
        print("PRECISION(macro)=" + str(round(evaluation['precision'],3)), "RECALL(macro)=" + str(round(evaluation['recall'],3)), file=sys.stderr)
        print("PRECISION(micro)=" + str(round(evaluation['microprecision'], 3)), "RECALL(micro)=" + str(round(evaluation['microrecall'],3)), file=sys.stderr)
        print("SOURCECOVERAGE=" + str(round(evaluation['sourcecoverage'],3)), "TARGETCOVERAGE=" + str(round(evaluation['targetcoverage'],3)), file=sys.stderr)
        print("SOURCEENTITIES=" + str(len(sourceentities)), "TARGETENTITIES=" + str(len(targetentities)))
        print("MATCHES=" + str(evaluation['matches']), file=sys.stderr)
        print("TRANSLATABLEENTITIES=" + str(evaluation['translatableentities']), file=sys.stderr)

    if cache is not None:
        with open(args.cache,'wb') as f:
            pickle.dump(cache,f)


if __name__ == '__main__':
    main()
    sys.exit(0)
