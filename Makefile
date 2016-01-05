export PYTHONPATH:=.:$(PYTHONPATH)
export DJANGO_SETTINGS_MODULE:=sequences.test_settings

test:
	django-admin test sequences
