#!/usr/bin/env python
#-*- coding:utf-8 -*-

###############################################################
# CLAM: Computational Linguistics Application Mediator
# -- Service Configuration File (Template) --
#       by Maarten van Gompel (proycon)
#       Centre for Language and Speech Technology / Language Machines
#       Radboud University Nijmegen
#
#       https://proycon.github.io/clam
#
#       Licensed under GPLv3
#
###############################################################

#Consult the CLAM manual for extensive documentation

#If we run on Python 2.7, behave as much as Python 3 as possible
from __future__ import print_function, unicode_literals, division, absolute_import

from clam.common.parameters import *
from clam.common.formats import *
from clam.common.converters import *
from clam.common.viewers import *
from clam.common.data import *
from clam.common.digestauth import pwhash
import clam
import sys
import os
from base64 import b64decode as D

REQUIRE_VERSION = 2.1

CLAMDIR = clam.__path__[0] #directory where CLAM is installed, detected automatically
WEBSERVICEDIR = os.path.dirname(os.path.abspath(__file__)) #directory where this webservice is installed, detected automatically

# ======== GENERAL INFORMATION ===========

# General information concerning your system.


#The System ID, a short alphanumeric identifier for internal use only
SYSTEM_ID = "babelente"
#System name, the way the system is presented to the world
SYSTEM_NAME = "BabelEnte"

#An informative description for this system (this should be fairly short, about one paragraph, and may not contain HTML)
SYSTEM_DESCRIPTION = "This is an entity extractor, translator and evaluator that uses BabelFy. It can be used either for entity recognition and linking of your own input documents, or it can be used for implicit evaluation of translations (as developed for the TraMOOC project)."

CUSTOMHTML_INDEX = "You can read more about BabelEnte and obtain its source code to run it locally <a href=\"https://github.com/proycon/babelente\">here</a>. Note that the number of requests this webservice can make to the BabelFy/BabelNet backend is limited!"

# ======== LOCATION ===========

#Add a section for your host:

# ================ Server specific configuration for CLAM ===============
host = os.uname()[1]
if 'VIRTUAL_ENV' in os.environ:
    # Virtual Environment (LaMachine)
    ROOT = os.environ['VIRTUAL_ENV'] + "/babelente.clam/"
    PORT = 8806

    if host == 'mlp01': #configuration for server in Nijmegen
        HOST = "webservices-lst.science.ru.nl"
        URLPREFIX = 'babelente'

        if not 'CLAMTEST' in os.environ:
            ROOT = "/var/www/webservices-lst/live/writable/babelente/"
            if 'CLAMSSL' in os.environ:
                PORT = 443
            else:
                PORT = 80
        else:
            ROOT = "/var/www/webservices-lst/test/writable/babelente/"
            PORT = 81

        USERS_MYSQL = {
            'host': 'mysql-clamopener.science.ru.nl',
            'user': 'clamopener',
            'password': D(open(os.environ['CLAMOPENER_KEYFILE']).read().strip()),
            'database': 'clamopener',
            'table': 'clamusers_clamusers'
        }
        DEBUG = False
        REALM = "WEBSERVICES-LST"
        DIGESTOPAQUE = open(os.environ['CLAM_DIGESTOPAQUEFILE']).read().strip()
        SECRET_KEY = open(os.environ['CLAM_SECRETKEYFILE']).read().strip()
        os.environ['BABELNET_API_KEY'] = open(os.environ['CLAM_BABELNETAPIKEYFILE']).read().strip()
        ADMINS = ['proycon','antalb','wstoop']
        MAXLOADAVG = 25.0
else:
    raise Exception("I don't know where I'm running from! Got " + host)


# ======== AUTHENTICATION & SECURITY ===========

#Users and passwords

#set security realm, a required component for hashing passwords (will default to SYSTEM_ID if not set)
#REALM = SYSTEM_ID

USERS = None #no user authentication/security (this is not recommended for production environments!)

ADMINS = None #List of usernames that are administrator and can access the administrative web-interface (on URL /admin/)

#If you want to enable user-based security, you can define a dictionary
#of users and (hashed) passwords here. The actual authentication will proceed
#as HTTP Digest Authentication. Although being a convenient shortcut,
#using pwhash and plaintext password in this code is not secure!!

#USERS = { user1': '4f8dh8337e2a5a83734b','user2': pwhash('username', REALM, 'secret') }

#Amount of free memory required prior to starting a new process (in MB!), Free Memory + Cached (without swap!). Set to 0 to disable this check (not recommended)
REQUIREMEMORY = 100



#The amount of diskspace a user may use (in MB), this is a soft quota which can be exceeded, but creation of new projects is blocked until usage drops below the quota again
#USERQUOTA = 100

#The secret key is used internally for cryptographically signing session data, in production environments, you'll want to set this to a persistent value. If not set it will be randomly generated.
#SECRET_KEY = 'mysecret'

#Allow Asynchronous HTTP requests from **web browsers** in following domains (sets Access-Control-Allow-Origin HTTP headers), by default this is unrestricted
#ALLOW_ORIGIN = "*"

# ======== WEB-APPLICATION STYLING =============

#Choose a style (has to be defined as a CSS file in clam/style/ ). You can copy, rename and adapt it to make your own style
STYLE = 'classic'

# ======== ENABLED FORMATS ===========

#In CUSTOM_FORMATS you can specify a list of Python classes corresponding to extra formats.
#You can define the classes first, and then put them in CUSTOM_FORMATS, as shown in this example:

#class MyXMLFormat(CLAMMetaData):
#    attributes = {}
#    name = "My XML format"
#    mimetype = 'text/xml'

# CUSTOM_FORMATS = [ MyXMLFormat ]

# ======= INTERFACE OPTIONS ===========

#Here you can specify additional interface options (space separated list), see the documentation for all allowed options
#INTERFACEOPTIONS = "inputfromweb" #allow CLAM to download its input from a user-specified url

# ======== PREINSTALLED DATA ===========

#INPUTSOURCES = [
#    InputSource(id='sampledocs',label='Sample texts',path=ROOT+'/inputsources/sampledata',defaultmetadata=PlainTextFormat(None, encoding='utf-8') ),
#]

# ======== PROFILE DEFINITIONS ===========

#Define your profiles here. This is required for the project paradigm, but can be set to an empty list if you only use the action paradigm.

PROFILES = [
    Profile(
        InputTemplate('inputtext', PlainTextFormat,"Input text to perform entity recognition/linking on",
            StaticParameter(id='encoding',name='Encoding',description='The character encoding of the file', value='utf-8'), #note that encoding is required if you work with PlainTextFormat
            extension=".txt",
            unique=False,
        ),
        OutputTemplate('outputjson',JSONFormat,'Output JSON with extracted entities',
            removeextensions=['.txt'],
            extension='.json', #set an extension or set a filename:
            unique=False
        ),
    ),
    Profile(
        InputTemplate('inputfolia', FoLiAXMLFormat,"Input document (FoLiA) to perform entity recognition/linking on",
            extension=".folia.xml",
            unique=False,
        ),
        OutputTemplate('outputjson',JSONFormat,'Output JSON with extracted entities',
            removeextensions=['.folia.xml'],
            extension='.json', #set an extension or set a filename:
            unique=False
        ),
        OutputTemplate('outputfolia',FoLiAXMLFormat,'Output document with entities and entity links (FoLiA)',
            removeextensions=['.folia.xml'],
            extension='.babelente.folia.xml', #set an extension or set a filename:
            unique=False
        ),
    ),
    Profile(
        InputTemplate('evalsource', PlainTextFormat,"English source text for implicit translation evaluation (one sentence per line)",
            StaticParameter(id='encoding',name='Encoding',description='The character encoding of the file', value='utf-8'), #note that encoding is required if you work with PlainTextFormat
            filename="source.txt",
            unique=True #set unique=True if the user may only upload a file for this input template once. Set multi=True if you the user may upload multiple of such files
        ),
        InputTemplate('evaltarget', PlainTextFormat,"Translated text for implicit translation evaluation (one sentence per line)",
            StaticParameter(id='encoding',name='Encoding',description='The character encoding of the file', value='utf-8'), #note that encoding is required if you work with PlainTextFormat
            filename="translation.txt",
            unique=True #set unique=True if the user may only upload a file for this input template once. Set multi=True if you the user may upload multiple of such files
        ),
        #------------------------------------------------------------------------------------------------------------------------
        OutputTemplate('evaluation',JSONFormat,'Replace with human label for this output template',
            filename='evaluation.json',
            unique=True
        ),
    )
]

# ======== COMMAND ===========

#The system command for the project paradigm.
#It is recommended you set this to small wrapper
#script around your actual system. Full shell syntax is supported. Using
#absolute paths is preferred. The current working directory will be
#set to the project directory.
#
#You can make use of the following special variables,
#which will be automatically set by CLAM:
#     $INPUTDIRECTORY  - The directory where input files are uploaded.
#     $OUTPUTDIRECTORY - The directory where the system should output
#                        its output files.
#     $TMPDIRECTORY    - The directory where the system should output
#                        its temporary files.
#     $STATUSFILE      - Filename of the .status file where the system
#                        should output status messages.
#     $DATAFILE        - Filename of the clam.xml file describing the
#                        system and chosen configuration.
#     $USERNAME        - The username of the currently logged in user
#                        (set to "anonymous" if there is none)
#     $PARAMETERS      - List of chosen parameters, using the specified flags
#
COMMAND = WEBSERVICEDIR + "/babelente_wrapper.py $DATAFILE $STATUSFILE $OUTPUTDIRECTORY"

#Or if you only use the action paradigm, set COMMAND = None

# ======== PARAMETER DEFINITIONS ===========

#The global parameters (for the project paradigm) are subdivided into several
#groups. In the form of a list of (groupname, parameters) tuples. The parameters
#are a list of instances from common/parameters.py

PARAMETERS =  [
    ('General', [
        ChoiceParameter(id='lang',name="Language",description="The language your input documents (or translation output) are in", choices=[('AR','Arabic'), ('BG','Bulgarian'),('ZH','Chinese'),('CS', 'Czech'),('HR','Croatian'),('NL','Dutch'),('EN','English'),('EO','Esperanto'),('FI','Finnish'),('FR','French'),('DE','German'),('EL','Greek'),('HI','Hindi'), ('IT','Italian'),('JA','Japanese'),('RU','Russian'), ('FA','Persian'),('PT','Portuguese'), ('SR','Serbian'), ('ES','Spanish'),('SW','Swahili'), ('SV','Swedish'),('TR','Turkish')],default='EN',required=True), #not exhaustive yet
    ] ),
    ('BabelEnte Parameters', [
        ChoiceParameter(id='overlap',name="Overlap strategy", description="Resolve overlapping entities?", choices=[('allow','Allow overlap'),('longest','Prefer the longest'), ('score','Prefer the one with the highest score'),('globalscore', 'Prefer the one with the highest global score'), ('coherencescore','Prefer the one with the highest coherence score')], default='allow')
    ]),
    ('BabelFy Parameters', [
        ChoiceParameter(id='anntype',name="Annotation Type",description="Restrict the disambiguated entries by annotation type?", choices=[('NAMED_ENTITIES','Named Entities only'),('CONCEPTS','Concepts only'),('ALL', 'No, use both')], default='ALL', required=False ),
        ChoiceParameter(id='annres',name="Annotation Resource",description="Restrict the disambiguated entries by resource?", choices=[('WN','WordNet only'),('WIKI','Wikipedia only'),('ALL', 'No, use all')], default='ALL', required=False),
        FloatParameter(id='th',name="Cutting Threshold",description="", required=False),
        ChoiceParameter(id='cands', name="Candidate List", description="Returns all candidates or only the top ranked ones? (The next two parameters can only be used with the latter)",choices=[("ALL","All"),("TOP","Top")], default='ALL'),
        ChoiceParameter(id='match',name="Extraction strategy",description="", choices=[('EXACT_MATCHING','Exact matching only'),('PARTIAL_MATCHING','Both exact and partial matching')], default='PARTIAL_MATCHING', required=False),
        ChoiceParameter(id='mcs',name="Most Common Sense Backof Strategy",description="", choices=[('ON','On'),('ON_WITH_STOPWORDS','On (with stopwords)'), ('OFF', 'Off')], default='ON', required=False),
        BooleanParameter(id='dens',name="Densest subgraph",description="Enable the densest subgraph heuristic during the disambiguation pipeline.", required=False),
        ChoiceParameter(id='postag', name="Tokenisation and PoS tagging", description="Use this parameter to change the tokenization and pos-tagging pipeline for your input text.", choices=[ ('STANDARD','Standard'), ('NOMINALIZE_ADJECTIVES', 'Nominalize adjectives'), ('INPUT_FRAGMENTS_AS_NOUNS', 'Input fragments as nouns'), ('CHAR_BASED_TOKENIZATION_ALL_NOUN','Character based tokenisation, all nouns')], default='STANDARD',required=False),
        BooleanParameter(id='extaida',name="aida_means",description="Extend the candidates sets with the aida_means relations from YAGO.", required=False),
    ]),
    ('Implicit Evaluation Parameters (TraMOOC)', [
        BooleanParameter(id='nodup',name="No duplicates",description="Filter out duplicates in evaluation", required=False),
    ]),
]


# ======= ACTIONS =============

#The action paradigm is an independent Remote-Procedure-Call mechanism that
#allows you to tie scripts (command=) or Python functions (function=) to URLs.
#It has no notion of projects or files and must respond in real-time. The syntax
#for commands is equal to those of COMMAND above, any file or project specific
#variables are not available though, so there is no $DATAFILE, $STATUSFILE, $INPUTDIRECTORY, $OUTPUTDIRECTORY or $PROJECT.

ACTIONS = [
    #Action(id='multiply',name='Multiply',parameters=[IntegerParameter(id='x',name='Value'),IntegerParameter(id='y',name='Multiplier'), command=sys.path[0] + "/actions/multiply.sh $PARAMETERS" ])
    #Action(id='multiply',name='Multiply',parameters=[IntegerParameter(id='x',name='Value'),IntegerParameter(id='y',name='Multiplier'), function=lambda x,y: x*y ])
]


# ======== DISPATCHING (ADVANCED! YOU CAN SAFELY SKIP THIS!) ========

#The dispatcher to use (defaults to clamdispatcher.py), you almost never want to change this
#DISPATCHER = 'clamdispatcher.py'

#DISPATCHER_POLLINTERVAL = 30   #interval at which the dispatcher polls for resource consumption (default: 30 secs)
#DISPATCHER_MAXRESMEM = 0    #maximum consumption of resident memory (in megabytes), processes that exceed this will be automatically aborted. (0 = unlimited, default)
#DISPATCHER_MAXTIME = 0      #maximum number of seconds a process may run, it will be aborted if this duration is exceeded.   (0=unlimited, default)
#DISPATCHER_PYTHONPATH = []        #list of extra directories to add to the python path prior to launch of dispatcher

#Run background process on a remote host? Then set the following (leave the lambda in):
#REMOTEHOST = lambda: return 'some.remote.host'
#REMOTEUSER = 'username'

#For this to work, the user under which CLAM runs must have (passwordless) ssh access (use ssh keys) to the remote host using the specified username (ssh REMOTEUSER@REMOTEHOST)
#Moreover, both systems must have access to the same filesystem (ROOT) under the same mountpoint.
