# include this snippet for the pychecker stuff
# Makefile.am needs to define
# PYCHECKER_WHITELIST
# and
# PYCHECKER_BLACKLIST

pychecker_setup = `ls $(top_srcdir)/misc/setup.py 2> /dev/null`
pychecker_help = `ls $(top_srcdir)/misc/pycheckerhelp.py 2> /dev/null`
pychecker =					\
	pychecker -Q -F misc/pycheckerrc	\
	$(pychecker_setup)			\
	$(pychecker_help)

# during distcheck, we get executed from $(NAME)-$(VERSION)/_build, while
# our python sources are one level up.  Figure this out and set a OUR_PATH
# this uses Makefile syntax, so we need to protect it from automake
thisdir = $(shell basename `pwd`)
OUR_PATH = $(if $(subst _build,,$(thisdir)),$(shell pwd),$(shell pwd)/..)

# TODO: This looks a little confusing because our 0.10 files are named
# blah010.py
pychecker_all_files = $(filter-out $(PYCHECKER_BLACKLIST),$(wildcard $(PYCHECKER_WHITELIST)))
pychecker_08_files = $(filter %08.py,$(pychecker_all_files))
pychecker_010_files = $(filter %010.py,$(pychecker_all_files))
pychecker_indep_files = $(filter-out $(pychecker_08_files) $(pychecker_010_files),$(pychecker_all_files))

pychecker_indep = PYTHONPATH=$(OUR_PATH) $(pychecker)
pychecker_08 = PYTHONPATH=$(PYGST_08_DIR):$(OUR_PATH) FLU_GST_VERSION=0.8 $(pychecker)
pychecker_010 = PYTHONPATH=$(PYGST_010_DIR):$(OUR_PATH) FLU_GST_VERSION=0.10 $(pychecker)

pychecker_if_08 = if test "x$(GST_08_SUPPORTED)" = "xyes"; then 
pychecker_if_010 = if test "x$(GST_010_SUPPORTED)" = "xyes"; then 
pychecker_fi = else echo "passing, gstreamer version not supported"; fi

# we redirect stderr so we don't get messages like
# warning: couldn't find real module for class SSL.Error (module name: SSL)
# which can't be turned off in pychecker
pycheckersplit:
	@echo running pychecker on each file ...
	@for file in $(pychecker_all_files)
	do \
		$(pychecker) $$file > /dev/null 2>&1			\
		if test $$? -ne 0; then 				\
			echo "Error on $$file";				\
			$(pychecker) $$file; break			\
		fi							\
	done

pychecker: pychecker08 pychecker010 pycheckerindep
	@true

pycheckerindep: 
	@echo running pychecker, gstreamer-agnostic files ...
	@$(pychecker_indep) $(pychecker_indep_files) 2>/dev/null || make pycheckerverboseindep

pychecker08:
	@echo running pychecker, gstreamer 0.8-specific code ...
	@$(pychecker_if_08) $(pychecker_08) $(pychecker_08_files) 2>/dev/null \
	  || make pycheckerverbose08; $(pychecker_fi)

pychecker010:
	@echo running pychecker, gstreamer 0.10-specific code ...
	@$(pychecker_if_010) $(pychecker_010) $(pychecker_010_files) 2>/dev/null \
	  || make pycheckerverbose010; $(pychecker_fi)

pycheckerverbose: pycheckerverbose08 pycheckerverbose010 pycheckerverboseindep

pycheckerverboseindep:
	@echo "running pychecker, gstreamer-agnostic files (verbose) ..."
	$(pychecker_indep) $(pychecker_indep_files)

pycheckerverbose08:
	@echo "running pychecker, gstreamer 0.8-specific code (verbose) ..."
	$(pychecker_if_08) $(pychecker_08) $(pychecker_08_files); $(pychecker_fi)

pycheckerverbose010:
	@echo "running pychecker, gstreamer 0.10-specific code (verbose) ..."
	$(pychecker_if_010) $(pychecker_010) $(pychecker_010_files); $(pychecker_fi)
