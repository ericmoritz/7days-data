.PHONY: clean

all: data

data:
	mkdir -p data
	python bin/convert.py > data/all.ttl

out:
	sparql --data=data/all.ttl --query=queries/bestFood.sparql

clean:
	rm -rf data/
