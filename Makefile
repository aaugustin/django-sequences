test: test_postgresql test_mysql test_oracle test_sqlite

test_%:
	python -m django test --settings=tests.$*_settings

clean:
	rm -rf dist src/django_sequences.egg-info
