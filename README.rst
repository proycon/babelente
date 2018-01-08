BabelEnte: Entity extractioN, Translation and implicit Evaluation using BabelFy
===================================================================================

This is an entity extractor, translator and evaluator that uses `BabelFy <http://babelfy.org>`_ . Initially developed
for the TraMOOC project. It is written in Python 3.

.. image:: https://github.com/proycon/babelente/blob/master/logo.jpg?raw=true
    :align: center

Installation
---------------

(not yet ready; to appear soonish)

::

    pip3 install babelente

or clone this github repository and run ``python3 setup.py install``, optionally prepend the commands with ``sudo`` for
global installation.

Usage
-------

You will need a BabelFy API key, get it from `BabelNet.org <http://babelnet.org>`_ .

See ``babelente -h`` for usage for now.

To evaluate a translation (english to portuguese in this example), output wil be JSON to stdout:

``$ babelente -k "YOUR-API-KEY" -f en -t pt -S sentences.en.txt -T sentences.pt.txt > output.json``

To re-evaluate:

``$ babelente --evalfile output.json -S sentences.en.txt -T sentences.pt.txt > newoutput.json``

You can also use BabelEnte to just extract entities a single language, without evaluation:

``$ babelente -k "YOUR-API-KEY" -f en -S sentences.en.txt > output.json``


Evaluation
-----------

The evaluation produces several metrics.


source coverage number of characters covered by found source entities divided by the total number of characters in the source text

target coverage number of characters covered by found target entities divided by the total number of characters in the target text

precision and recall
--------------------

In the standard scoring method we count each entity and compute scores
We also implemented the option to compute the scores


**micro precision** sum of found equivalent entities in target and source texts divided by the total sum of found entities in target language

**macro precision** sum of found equivalent entities in target and source texts divided by the number of target sentences

**micro recall** sum of found equivalent entities in target and source divided by the total sum of found entities in source language  for which a equivalent link existed in the target language. In other words, how many of the hypothetical possible matches that were found?
Note that this is intensive computation and needs to be specified as command line parameter —recall.

**macro recall** sum of found equivalent entities in target and source texts divided by the number of source sentences.



**Computing recall and precision over entity sets**

Instead of counting every occurring entity (“tokens”), we can also count each entity once (“types” or “sets”). This can be a more useful indicator of the performance measure when the input texts contains many repetitions or slight variations of the same sentences.
This option is activated with the parameter —nodup (no duplicates) .



License
-----------

GNU - GPL 3.0
