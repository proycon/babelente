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

See ``babelente -h`` for usage for now.

To evaluate a translation (english to portuguese in this example), output wil be JSON to stdout:

```
$ babelente -k "YOUR-API-KEY" -f en -t pt -S sentences.en.txt -T sentences.pt.txt > output.json
```

To re-evaluate:

```
$ babelente --evalfile output.json > newoutput.json
```

You can also use BabelEnte to just extract entities a single language, without evaluation:

```
$ babelente -k "YOUR-API-KEY" -f en -S sentences.en.txt > output.json
```


Evaluation
-----------

The evaluation produces two metrics, computer per sentence/line pair and final score aggregated as macro-average:
* **Precision** -How many of the target synsets are correct? (``|matchingsynsets| / |targetsynsets|``)
* **Recall** - How many of the source synsets are found? (``|matchingsynsets| / |sourcesynsets|``)


License
-----------

GNU - GPL 3.0
