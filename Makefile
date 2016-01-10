export PYTHONPATH:=.:$(PYTHONPATH)

test: test_postgresql

test_%:
	DJANGO_SETTINGS_MODULE=sequences.$@_settings django-admin test sequences
