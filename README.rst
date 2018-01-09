BabelEnte: Entity extractioN, Translation and implicit Evaluation using BabelFy
===================================================================================

This is an entity extractor, translator and evaluator that uses `BabelFy <http://babelfy.org>`_ . Initially developed
for the TraMOOC project. It is written in Python 3.

.. image:: https://github.com/proycon/babelente/blob/master/logo.jpg?raw=true
    :align: center

Installation
---------------

::

    pip3 install babelente

or clone this github repository and run ``python3 setup.py install``, optionally prepend the commands with ``sudo`` for
global installation.

Usage
-------

You will need a BabelFy API key, get it from `BabelNet.org <http://babelnet.org>`_ .

See ``babelente -h`` for extensive usage instructions, explaining all the options.

For simple entity recognition/linking on plain text documents, invoke BabelEnte as follows. This will produce JSON output with all entities found:

``$ babelente -k "YOUR-API-KEY" -s en -S sentences.en.txt > output.json``

BabelEnte comes with `FoLiA <https://github.com/proycon/folia>`_ support. Allowing you to read FoLiA documents and
producing enriched FoLiA documents that include the detected/linked entities. To this end, simply specify the language
of your FoLiA document(s) and pass them to babelente as follows, multiple documents are allowed:

``$ babelente -k "YOUR-API-KEY" -s en yourdocument.folia.xml``

Each FoLiA document will be outputted to a new file, which includes all the entities. Entities will be explicitly linked to BabelNet
and DBpedia where possible. At the same time, the ``stdout`` output again consists of a JSON object containing all found
entities.

Note that this method does currently not do any translation of entities yet (I'm open to feature request
if you want this).

If you start from plain text but want to produce FoLiA output, then first use for instance `ucto
<https://github.com/LanguageMachines/ucto>`_ to tokenise your document and convert it to FoLiA, prior to passing it to
BabelEnte.


Usage for TraMOOC
--------------------

This sofware can be used for implicit evaluation of translations, as it was designed in the scope of the TraMOOC
project.

To evaluate a translation (english to portuguese in this example), output wil be JSON to stdout:

``$ babelente -k "YOUR-API-KEY" -s en -t pt -S sentences.en.txt -T sentences.pt.txt > output.json``

To re-evaluate:

``$ babelente --evalfile output.json -S sentences.en.txt -T sentences.pt.txt > newoutput.json``



Evaluation
~~~~~~~~~~~~~

The evaluation produces several metrics.

* source coverage number of characters covered by found source entities divided by the total number of characters in the source text
* target coverage number of characters covered by found target entities divided by the total number of characters in the target text

Precision and Recall
~~~~~~~~~~~~~~~~~~~~~~

In the standard scoring method we count each entity and compute scores
We also implemented the option to compute the scores


* **micro precision** sum of found equivalent entities in target and source texts divided by the total sum of found entities in target language
* **macro precision** sum of found equivalent entities in target and source texts divided by the number of target sentences
* **micro recall** sum of found equivalent entities in target and source divided by the total sum of found entities in source language  for which a equivalent link existed in the target language. In other words, how many of the hypothetical possible matches that were found?
Note that this is intensive computation and needs to be specified as command line parameter —recall.
* **macro recall** sum of found equivalent entities in target and source texts divided by the number of source sentences.

**Computing recall and precision over entity sets**

Instead of counting every occurring entity (“tokens”), we can also count each entity once (“types” or “sets”). This can be a more useful indicator of the performance measure when the input texts contains many repetitions or slight variations of the same sentences.
This option is activated with the parameter —nodup (no duplicates) .



License
-----------

GNU - GPL 3.0
