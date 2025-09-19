upload:
	python setup.py sdist build
	twine upload dist/*

test:
	python tests/test_connect_capture.py