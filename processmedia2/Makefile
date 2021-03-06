.PHONY: help
help:
	# Usage: make <target>, where target is
	# install        -- Install os dependencys and setup python virtualenv
	# install_env    --   just install python virtualenv
	# run            -- Alias for 'scan + encode + import_media'
	#
	# scan           -- Scan source media folder + create metadata cache
	# encode         -- Perform video encoding on required items
	# import_media   -- Import processed media into currently active website
	# cleanup        -- Remove unassociated processed files
	#
	# upgrade        -- Upgrade os + python dependencys
	# test           -- Run integration tests
	# clean          -- Reset to clean checkout


# Variables --------------------------------------------------------------------

OS:=$(shell uname -s)
LINUX_DISTRO:=$(shell lsb_release -a 2> /dev/null | grep "Distributor ID:" | sed 's|.*:.\(.*\)|\1|')

PYTHON_VERSION:=3.6
DEPENDENCIES_PYTHON:=dependencies.python.txt
DEPENDENCIES_APT:=dependencies.apt.txt
DEPENDENCIES_BREW:=dependencies.brew.txt

ENV:=_env
PYTHON:=$(ENV)/bin/python$(PYTHON_VERSION)
PIP:=$(ENV)/bin/pip$(PYTHON_VERSION)
PYTEST:=$(ENV)/bin/py.test


# Installation -----------------------------------------------------------------
.PHONY: install install_env
install: install_$(OS) install_env
install_env: $(ENV) libs config.json logging.json logs

# OSX ----
.PHONY: has-brew install_Darwin upgrade_Darwin
has-brew:
	which brew
install_Darwin: has-brew
	brew update
	cat $(DEPENDENCIES_BREW) |xargs  brew install
upgrade_Darwin: has-brew
	cat $(DEPENDENCIES_BREW) |xargs  brew upgrade

# Linux ----
.PHONY: install_Linux install_Debian install_Ubuntu apt-installation upgrade_Linux upgrade_Debian upgrade_Ubuntu apt-upgrade
install_Linux: install_$(LINUX_DISTRO)
install_Debian: apt-installation
install_Ubuntu: apt-installation
apt-installation:
	cat $(DEPENDENCIES_APT) |xargs  sudo apt-get install -y
upgrade_Linux: upgrade_$(LINUX_DISTRO)
upgrade_Debian: apt-upgrade
upgrade_Ubuntu: apt-upgrade
apt-upgrade:
	sudo apt-get update
	# TODO: install upgraded apt versions

# Python/Virtualenv ----
.PHONY: has-python3
has-python3:
	which python3
	which virtualenv
.PRECIOUS: $(ENV)
$(ENV):
	virtualenv --no-site-packages -p python$(PYTHON_VERSION) $(ENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r $(DEPENDENCIES_PYTHON)
.PHONY: upgrade
upgrade:
	$(PIP) install -r $(DEPENDENCIES_PYTHON) --upgrade

# Link local libs ----
libs:
	mkdir -p libs
	touch libs/__init__.py
	cd libs && \
	if [ -d ../../../libs/ ] ; then \
		ln -s ../../../libs/python3/lib/misc.py                            misc.py                  ;\
		ln -s ../../../libs/python3/lib/file.py                            file.py                  ;\
	else \
		wget -cq https://raw.githubusercontent.com/calaldees/libs/master/python3/lib/misc.py        ;\
		wget -cq https://raw.githubusercontent.com/calaldees/libs/master/python3/lib/file.py        ;\
	fi


# Config -----------------------------------------------------------------------

config.json:
	cp config.json.dist config.json

logging.json:
	cp logging.json.dist logging.json

logs:
	mkdir -p logs


# Run --------------------------------------------------------------------------
.PHONY: scan encode import_media cleanup run

scan:
	$(PYTHON) scan_media.py
encode:
	$(PYTHON) encode_media.py --process_order_function random
import_media:
	$(PYTHON) import_media.py --force
cleanup:
	$(PYTHON) cleanup_media.py
run: install_env scan encode import_media

# temp addition to document event import step
import_media_production_api:
	$(PYTHON) import_media.py --force --api_host int.karakara.org.uk

# Test -------------------------------------------------------------------------
.PHONY: test
test:
	$(MAKE) all --directory tests/source
	PYTHONPATH=./ $(PYTEST) processmedia_libs libs tests --doctest-modules --pdb

.PHONY: cloc
cloc:
	cloc --exclude-dir=$(ENV),libs ./

# Clean ------------------------------------------------------------------------

.PHONY: clean
clean:
	rm -rf .cache .pytest_cache __pycache__ $(ENV) libs config.json logging.json logs mtimes.json
	$(MAKE) clean --directory tests/source
