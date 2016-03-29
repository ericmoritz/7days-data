.PHONY: clean

all: data out

data:
	mkdir -p data
	python bin/convert.py > data/all.ttl

out:
	mkdir -p out
	sparql --data=data/all.ttl --query=queries/bestFood.sparql > out/bestFood.txt

clean:
	rm -rf data/
	rm -rf out/
