if HAVE_EPYDOC

EPYDOC_HTML = html
EPYDOC_ARGS = -q --no-frames --html --ignore-param-mismatch

MODULES = $(subst /,.,$(patsubst %.py,%, $(MODULE_FILES:/__init__.py=)))

# misc is in builddir
pypath = $(top_builddir):$(top_srcdir):$(PYTHONPATH)

html/index.html: $(patsubst %, $(top_srcdir)/%, $(MODULE_FILES)) $(top_srcdir)/common/gendoc.py
	@echo Generating HTML documentation...
	@PYTHONPATH=$(pypath) $(PYTHON) $(top_srcdir)/common/gendoc.py $(EPYDOC_ARGS) $(MODULES)

all-local-epydoc: html/index.html

check-local-epydoc:
	@PYTHONPATH=$(pypath) $(PYTHON) $(top_srcdir)/common/gendoc.py --check $(MODULES)

clean-local-epydoc:
	rm -rf html
else
EPYDOC_HTML =
all-local-epydoc:
	true

check-local-epydoc:
	true

clean-local-epydoc:
	true
endif
