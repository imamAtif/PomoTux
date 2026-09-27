# Lets COPR build an SRPM straight from this repo (make_srpm method).
VERSION := $(shell sed -n 's/^Version:[[:space:]]*//p' pomotux.spec)

srpm:
	rm -rf /tmp/pomotux-srpm
	mkdir -p /tmp/pomotux-srpm $(outdir)
	git archive --format=tar.gz --prefix=pomotux-$(VERSION)/ HEAD > /tmp/pomotux-srpm/pomotux-$(VERSION).tar.gz
	rpmbuild -bs --define "_sourcedir /tmp/pomotux-srpm" --define "_srcrpmdir $(outdir)" pomotux.spec
