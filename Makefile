.PHONY: clean

all: data out

data:
	mkdir -p data
	python bin/convert.py > data/all.ttl

out:
	mkdir -p out
	sparql --data=data/all.ttl --query=queries/bestFood.sparql > out/bestFood.txt
	sparql --data=data/all.ttl --query=queries/itemsNeeded.sparql > out/base.txt

clean:
	rm -rf data/
	rm -rf out/

