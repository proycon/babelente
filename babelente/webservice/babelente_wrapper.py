#!/usr/bin/env python
#-*- coding:utf-8 -*-

###############################################################
# CLAM: Computational Linguistics Application Mediator
# -- CLAM Wrapper script Template --
#       by Maarten van Gompel (proycon)
#       https://proycon.github.io/clam
#       Centre for Language and Speech Technology
#       Radboud University Nijmegen
#
#       (adapt or remove this header for your own code)
#
#       Licensed under GPLv3
#
###############################################################

#This is a template wrapper which you can use a basis for writing your own
#system wrapper script. The system wrapper script is called by CLAM, it's job it
#to call your actual tool.

#This script will be called by CLAM and will run with the current working directory set to the specified project directory

#This wrapper script uses Python and the CLAM Data API.
#We make use of the XML settings file that CLAM outputs, rather than
#passing all parameters on the command line.


#If we run on Python 2.7, behave as much as Python 3 as possible
from __future__ import print_function, unicode_literals, division, absolute_import

#import some general python modules:
import sys
import os

#import CLAM-specific modules. The CLAM API makes a lot of stuff easily accessible.
import clam.common.data
import clam.common.status

#When the wrapper is started, the current working directory corresponds to the project directory, input files are in input/ , output files should go in output/ .

#make a shortcut to the shellsafe() function
shellsafe = clam.common.data.shellsafe

#this script takes three arguments from CLAM: $DATAFILE $STATUSFILE $OUTPUTDIRECTORY
#(as configured at COMMAND= in the service configuration file, there you can
#reconfigure which arguments are passed and in what order.
datafile = sys.argv[1]
statusfile = sys.argv[2]
outputdir = sys.argv[3]

#If you make use of CUSTOM_FORMATS, you need to import your service configuration file here and set clam.common.data.CUSTOM_FORMATS
#Moreover, you can import any other settings from your service configuration file as well:

#from yourserviceconf import CUSTOM_FORMATS

#Obtain all data from the CLAM system (passed in $DATAFILE (clam.xml)), always pass CUSTOM_FORMATS as second argument if you make use of it!
clamdata = clam.common.data.getclamdata(datafile)

#You now have access to all data. A few properties at your disposition now are:
# clamdata.system_id , clamdata.project, clamdata.user, clamdata.status , clamdata.parameters, clamdata.inputformats, clamdata.outputformats , clamdata.input , clamdata.output

clam.common.status.write(statusfile, "Starting...")
print("Starting...", file=sys.stderr)

if 'BABELNET_API_KEY' in os.environ:
    BABELNET_API_KEY = os.environ['BABELNET_API_KEY']
else:
    print("No BabelNet API key found in environment variable BABELNET_API_KEY!",file=sys.stderr)
    sys.exit(2)


#=========================================================================================================================


#-- EXAMPLE B: Iterate over all input files? --

# This example iterates over all input files, it can be a simpler
# method for setting up your wrapper:
evalsource = evaltarget = None


options = "-k " + BABELNET_API_KEY + " --recall -o " + shellsafe(outputdir,'"') + " --cache " + shellsafe(outputdir + "/cache",'"')
if 'overlap' in clamdata and clamdata['overlap']:
    options += " --overlap " + str(clamdata['overlap'])
if 'anntype' in clamdata and clamdata['anntype']:
    options += " --anntype " + str(clamdata['anntype'])
if 'annres' in clamdata and clamdata['annres'] and clamdata['annres'] != "ALL":
    options += " --annres " + str(clamdata['annres'])
if 'th' in clamdata and clamdata['th']:
    options += " --th " + str(clamdata['th'])
if 'cands' in clamdata and clamdata['cands']:
    options += " --cands " + str(clamdata['cands'])
if 'match' in clamdata and clamdata['match']:
    options += " --match " + str(clamdata['match'])
if 'mcs' in clamdata and clamdata['mcs']:
    options += " --mcs " + str(clamdata['mcs'])
if 'postag' in clamdata and clamdata['postag']:
    options += " --postag " + str(clamdata['postag'])
if 'extaida' in clamdata and clamdata['extaida']:
    options += " --extaida"
if 'dens' in clamdata and clamdata['dens']:
    options += " --dens"
if 'nodup' in clamdata and clamdata['nodup']:
    options += " --nodup"

for inputfile in clamdata.input:
    inputtemplate = inputfile.metadata.inputtemplate
    inputfilepath = str(inputfile)
    encoding = inputfile.metadata['encoding'] #Example showing how to obtain metadata parameters
    if inputtemplate == "inputtext":
        msg = "Processing text document " + os.path.basename(inputfilepath)
        clam.common.status.write(statusfile, msg) # status update
        print(msg, file=sys.stderr)
        outputjson = os.path.join(outputdir, os.path.basename(inputfilepath[:-4]) + '.json') #remove .txt extension, add .json
        cmd = "babelente " + options + " -s " + shellsafe(clamdata['lang'],'"') + " -S " + shellsafe(inputfilepath,'"') + " > " + shellsafe(outputjson,'"')
        print(cmd.replace(BABELNET_API_KEY,"###REDACTED###"), file=sys.stderr)
        os.system(cmd) == 0 or sys.exit(2)
    elif inputtemplate == "inputfolia":
        msg = "Processing FoLiA document " + os.path.basename(inputfilepath) # status update
        clam.common.status.write(statusfile, msg) # status update
        print(msg, file=sys.stderr)
        outputjson = os.path.join(outputdir, os.path.basename(inputfilepath[:-10]) + '.json') #remove .folia.xml extension, add .json
        cmd = "babelente " + options + " -s " + shellsafe(clamdata['lang'],'"') + " " + shellsafe(inputfilepath,'"') + " > " + shellsafe(outputjson,'"')
        print(cmd.replace(BABELNET_API_KEY,"###REDACTED###"), file=sys.stderr)
        os.system(cmd) == 0 or sys.exit(2)
    elif inputtemplate == "evalsource":
        evalsource = inputfilepath
    elif inputtemplate == "evaltarget":
        evaltarget = inputfilepath

if evalsource and evaltarget:
    #Implicit Evaluation pipeline (TraMOOC)
    clam.common.status.write(statusfile, "Conducting Implicit Translation Evaluation...") # status update
    outputjson = os.path.join(outputdir, 'evaluation.json') #remove .folia.xml extension, add .json
    os.system("babelente " + options + " -s en -t " + shellsafe(clamdata['lang'],'"') + " -S " + shellsafe(evalsource,'"') + " -T " + shellsafe(evaltarget,'"') + " > " + shellsafe(outputjson,'"')) == 0 or sys.exit(2)



clam.common.status.write(statusfile, "Done",100) # status update
print("Done",file=sys.stderr)

sys.exit(0) #non-zero exit codes indicate an error and will be picked up by CLAM as such!
