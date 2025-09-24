upload:
	rm -rf dist/*.tar.gz
	python setup.py sdist build
	twine upload dist/*