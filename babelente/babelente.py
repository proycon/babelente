#!/usr/bin/env python3

# Maarten van Gompel (proycon)
# Centre for Language and Speech Technology
# Radboud University Nijmegen
# GNU Public License v3

import sys
import argparse
import requests
import json
from babelpy.babelfy import BabelfyClient


def findentities(text, lang, apikey):
    babelclient = BabelfyClient(apikey, {'lang': lang.upper()})
    babelclient.babelfy(text)
    for entity in babelclient.entities:
        yield entity

def findtranslations(synset_id, lang, apikey):
    #translate entity to target language
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

def main():
    parser = argparse.ArgumentParser(description="BabelEnte: Entity Extractor and Trannslator using BabelFy and Babelnet.org", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-k','--apikey', type=str,help="Babelnet API key", action='store',default="",required=True)
    parser.add_argument('-f','--sourcelang', type=str,help="Source language code", action='store',default="",required=True)
    parser.add_argument('-t','--targetlang', type=str,help="Target language code", action='store',default="",required=True)
    parser.add_argument('-i','--input', type=str,help="Input sentences (plain text, one per line, utf-8)", action='store',default="",required=True)
    parser.add_argument('--eval', type=str,help="Evaluate against specified file with output sentences", action='store',default="",required=False)
    args = parser.parse_args()

    with open(args.input, 'r',encoding='utf-8') as f:
        text = f.read()

    entities = []
    for entity in findentities(text, args.sourcelang,args.apikey):
        if entity['isEntity'] and 'babelSynsetID' in entity: #sanity check
            entity['translations'] = []
            for translatedlemma in findtranslations(entity['babelSynsetID'], args.targetlang.upper(), args.apikey):
                entity['translations'].append(translatedlemma.replace('_',' '))
                entities.append(entity)
    print(json.dumps({'entities':entities}, indent=4,ensure_ascii=False))


if __name__ == '__main__':
    main()
