check-local: check-local-pychecker check-local-registry

test:
	@make check -C flumotion/test

check-docs:
	@make check -C doc/reference

check-local-registry: locale-uninstalled
	$(top_builddir)/env bash -c "export PYTHONPATH=$(FLUMOTION_DIR)${PYTHONPATH:+:$PYTHONPATH} && $(PYTHON) $(top_srcdir)/common/validate-registry.py"

coverage:
	@trial --temp-directory=_trial_coverage --coverage flumotion.test
	make show-coverage

show-coverage:
	@test ! -z "$(COVERAGE_MODULES)" ||				\
	(echo Define COVERAGE_MODULES in your Makefile.am; exit 1)
	@keep="";							\
	for m in $(COVERAGE_MODULES); do				\
		echo adding $$m;					\
		keep="$$keep `ls _trial_coverage/coverage/$$m*`";	\
	done;								\
	$(PYTHON) common/show-coverage.py $$keep

fixme:
	tools/fixme | less -R

# remove any cache written in distcheck	
dist-hook:
	rm -rf cache

release: dist
	make $(PACKAGE)-$(VERSION).tar.bz2.md5

# generate md5 sum files
%.md5: %
	md5sum $< > $@

# generate a sloc count
sloc:
	sloccount flumotion | grep "(SLOC)" | cut -d = -f 2

.PHONY: test


locale-uninstalled-1:
	if test -d po; then \
	cd po; \
	make datadir=../$(top_builddir) itlocaledir=../$(top_builddir)/locale install; \
	fi

# the locale-uninstalled rule can be replaced with the following lines, 
# once we can depend on a newer intltool than 0.34.2
# 	if test -d po; then \
# 	cd po; \
# 	make datadir=../$(top_builddir) itlocaledir=../$(top_builddir)/locale install; \
# 	fi

locale-uninstalled:
	podir=$(top_srcdir)/po; \
	localedir=$(top_builddir)/locale; \
        make -C $$podir; \
	for file in $$(ls $$podir/*.gmo); do \
	  lang=`basename $$file .gmo`; \
	  dir=$$localedir/$$lang/LC_MESSAGES; \
	  mkdir -p $$dir; \
          echo "installing $$podir/$$lang.gmo as $$dir/$(GETTEXT_PACKAGE).mo"; \
	  install $$podir/$$lang.gmo $$dir/$(GETTEXT_PACKAGE).mo; \
	done;

locale-uninstalled-clean:
	@-rm -rf _trial_temp
	@-rm -rf $(top_builddir)/locale
