"""
This converts the XML files in the Config/ directory into .ttl
files that can be queried with SPARQL
"""
from rdflib import Namespace, Literal, Graph
from rdflib.namespace import RDFS
import xml.etree.ElementTree as etree
from fp.monads.maybe import Maybe
from itertools import imap, chain

sevenNS = Namespace("http://7daystodie.com/#")

def blockURI(key):
    return sevenNS['block/' + key]


def materialURI(key):
    return sevenNS['material/' + key]
    

def prop(el, name):
    return Maybe(
        el.find("property[@name='{name}']".format(name=name))
    ).map(lambda x: x.attrib['value'])

def upgradeToProp(el):
    return Maybe(
        el.find("property[@class='UpgradeBlock']/property[@name='ToBlock']")
    ).map(lambda x: x.attrib['value'])
    
def block_el_to_triples(el):
    uri = blockURI(el.attrib['name'])
    materialMaybe = prop(el, "Material")
    extendsMaybe = prop(el, "Extends")
    hpMaybe = prop(el, "MaxDamage").map(int)
    upgradeToMaybe = upgradeToProp(el)


    yield (uri, RDFS.label, Literal(el.attrib['name']))

    if extendsMaybe.is_just:
        yield (uri, sevenNS.extends, blockURI(extendsMaybe.from_just))
        
    if materialMaybe.is_just:
        yield (uri, sevenNS.material, materialURI(materialMaybe.from_just))

    if upgradeToMaybe.is_just:
        yield (uri, sevenNS.upgradeTo, blockURI(upgradeToMaybe.from_just))

    if hpMaybe.is_just:
        yield (uri, sevenNS.hp, Literal(hpMaybe.from_just))        

        
def blocks_etree_to_triples(etree):
    """maps the blocks.xml file to Block tuples"""
    for el in etree.findall("block"):
        for triple in block_el_to_triples(el):
            yield triple


def material_el_to_triples(el):
    uri = materialURI(el.attrib['id'])
    hpMaybe = prop(el, "MaxDamage").map(int)

    yield (uri, RDFS.label, Literal(el.attrib['id']))
    
    if hpMaybe.is_just:
        yield (uri, sevenNS.hp, Literal(hpMaybe.from_just))


def material_etree_to_triples(etree):
    """maps the materials.xml file to Material tuples"""
    for el in etree.findall("material"):
        for triple in material_el_to_triples(el):
            yield triple


def main():
    blocks = blocks_etree_to_triples(etree.parse("Config/blocks.xml"))
    materials = material_etree_to_triples(etree.parse("Config/materials.xml"))

    g = Graph()
    g.bind('s', sevenNS)
    
    for t in blocks:
        g.add(t)

    for t in materials:
        g.add(t)

    print g.serialize(format='turtle')
    
if __name__ == '__main__':
    main()
