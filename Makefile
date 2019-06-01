export PYTHONPATH:=.:$(PYTHONPATH)

test: test_postgresql test_mysql test_oracle test_sqlite

test_%:
	DJANGO_SETTINGS_MODULE=sequences.$@_settings django-admin test sequences
