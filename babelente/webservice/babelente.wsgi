import sys
import babelente.webservice.babelente as webservice
import clam.clamservice
application = clam.clamservice.run_wsgi(webservice)
