BabelEnte: Entity extractioN, Translation and Evaluation using BabelFy
===================================================================================

This is an entity extractor, translator and evaluator that uses `BabelFy <http://babelfy.org>`_ . Initially developed
for the TraMOOC project. It is written in Python 3.

Installation
---------------

::

    pip3 install babelente

or clone this github repository and run ``python3 setup.py install``, optionally prepend the commands with ``sudo`` for
global installation.

Usage
-------

You will need a BabelFy API key, get it from `BabelNet.org <http://babelnet.org>`_ .

See ``babelente -h`` for usage for now; to be documented further later...

Evaluation
-----------

The evaluation produces two metrics, computer per sentence/line pair and final score aggregated as macro-average:
* **Precision** -How many of the target synsets are correct? (``|matchingsynsets| / |targetsynsets|``)
* **Recall** - How many of the source synsets are found? (``|matchingsynsets| / |sourcesynsets|``)


License
-----------

GNU - GPL 3.0
