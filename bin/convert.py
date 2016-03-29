"""
This converts the XML files in the Config/ directory into .ttl
files that can be queried with SPARQL
"""
from rdflib import Namespace, Literal, Graph, URIRef
from rdflib.namespace import RDFS, RDF
import xml.etree.ElementTree as etree
from fp.monads.maybe import Maybe
from itertools import imap, chain
from csv import reader
from collections import namedtuple

L8nKey = namedtuple('L8nKey', ['key', 'source'])
L8nRow = namedtuple('L8nRow', ['en', 'fr', 'de'])

class Source(namedtuple('SourceBase', ['key', 'type'])):
    def __init__(self, *args, **kwargs):
        super(Source, self).__init__(*args, **kwargs)
        self.ns = Namespace(
            "http://7daystodie.com/#{key}/".format(key=self.key)
        )
        self.rdf_type = self.ns[self.type]

SEVEN_NS = Namespace("http://7daystodie.com/#")

BLOCKS_SOURCE = Source('blocks', 'Block')
MATERIALS_SOURCE = Source('materials', 'Material')
ITEMS_SOURCE = Source('items', 'Item')
RECIPES_SOURCE = Source('recipes', 'Recipe')

def localization_table(reader):
    reader.next() # pop the header
    table = {}
    for row in reader:
        key = L8nKey(*row[0:2])
        row = L8nRow(*row[4:7])
        table[key] = row
    return table

LOCALIZATION_TABLE = localization_table(
    reader(open('Config/Localization.txt'))
)

def local_lookup(source, key):
    return LOCALIZATION_TABLE.get(L8nKey(key, source.key))


def tag_uri(source, key):
    return source.ns[key]

def source_uri(source, key):
    return source.ns[key]    

def prop_class_uri(uri, class_name):
    return uri_join(uri, class_name)


def uri_join(uri, part):
    return URIRef(unicode(uri) + u'/' + part)


def el_uri_label(source, el):
    if el.tag in {'block', 'item', 'recipe'}:
        key = el.attrib['name']
        return (tag_uri(source, key), key) 
    elif el.tag == 'material':
        key = el.attrib['id']
        return (tag_uri(source, key), key)

def cast_pred(source, name):
    if name == 'Material':
        return SEVEN_NS.Material
    elif name == 'Item':
        return SEVEN_NS.Item
    else:
        return source.ns[name]


def cast_number(val):
    try:
        return int(val)
    except:
        pass

    try:
        return float(val)
    except:
        pass

    return val


def cast_value(source, name, value):
    if name == 'Material':
        return tag_uri(MATERIALS_SOURCE, value)
    elif name == 'Item':
        return tag_uri(ITEMS_SOURCE, value)
    elif name in {'ToBlock', 'UpgradeRated.ToBlock'}:
        return tag_uri(ITEMS_SOURCE, value)
    elif name == 'Extends':
        # The Extends property uses the same source
        return tag_uri(source, value)
    elif name == 'Texture':
        return Literal(value)
    else:
        value = cast_number(value)
        return Literal(value)

def kv_prop_to_triple(source, uri, name, value):
    return (uri, cast_pred(source, name), cast_value(source, name, value))
    

def parent_label(uri, source, key):
    loc_row = local_lookup(source, key)
    if loc_row:
        yield (uri, RDFS.label,
               Literal(loc_row.en, lang='en'))
        yield (uri, RDFS.label,
               Literal(loc_row.fr, lang='fr'))
        yield (uri, RDFS.label,
               Literal(loc_row.de, lang='de'))
    yield (uri, RDFS.label, Literal(key))


def _prop_to_triples(source, uri, prop):
    if 'name' in prop.attrib and 'value' in prop.attrib:
        name = prop.attrib['name']
        value = prop.attrib['value']
        
        triple = kv_prop_to_triple(source, uri, name, value)
        if triple:
            yield triple
                
    elif 'class' in prop.attrib:
        class_name = prop.attrib['class']
        class_uri = prop_class_uri(uri, class_name)
        
        yield (uri, source.ns[class_name], class_uri)
        
        for child_prop in prop.iterfind("property"):
            for triple in _prop_to_triples(source, class_uri, child_prop):
                yield triple


def prop_to_triples(parent_source, source, parent, prop):
    uri_label = el_uri_label(parent_source, parent)
    if uri_label:
        uri, label = uri_label
        for triple in parent_label(uri, source, label):
            yield triple 

        yield (uri, RDF.type, source.rdf_type)
        
        for triple in _prop_to_triples(source, uri, prop):
            yield triple


def etree_to_triples(parent_source, source, etree):
    for parent in etree.iterfind('./*/property/..'):
        for prop in parent.iterfind('property'):
            for triple in prop_to_triples(parent_source, source, parent, prop):
                yield triple


def attrib_to_triples(source, uri, attrib):
    for name, value in attrib.items():
        yield(uri, cast_pred(source, name), cast_value(source, name, value))

def recipe_etree_to_triples(source, etree):
    for recipe in etree.iterfind("recipe"):
        key = recipe.attrib['name']
        uri_label = el_uri_label(source, recipe)
        if uri_label:
            uri, label = uri_label
            item_uri = tag_uri(ITEMS_SOURCE, key)

            # give it a type 
            yield (uri, RDF.type, source.rdf_type)

            # link the item to it's recipe
            yield (item_uri, source.ns['recipe'], uri)

            for triple in parent_label(uri, source, label):
                yield triple
            
            for triple in attrib_to_triples(source, uri, recipe.attrib):
                yield triple
            
            
            for ingredient in recipe.iterfind("ingredient"):
                name = ingredient.attrib['name']
                
                ingredient_uri = uri_join(uri, u"ingredient/{name}".format(name=name))
                yield (uri, source.ns['ingredient'], ingredient_uri)

                item_uri = source_uri(ITEMS_SOURCE, name)
                yield (ingredient_uri, SEVEN_NS['Item'], item_uri)
                yield (ingredient_uri, SEVEN_NS['count'], Literal(int(ingredient.attrib['count'])))
                
                
def main():
    g = Graph()
    g.bind('s', SEVEN_NS)
    
    sources = [
        (BLOCKS_SOURCE, ITEMS_SOURCE, "Config/blocks.xml"),
        (ITEMS_SOURCE, ITEMS_SOURCE, "Config/items.xml"),        
        (MATERIALS_SOURCE, MATERIALS_SOURCE, "Config/materials.xml"),
    ]
    for (source, parent_source, filename) in sources:
        g.bind(source.key, source.ns)
        for t in etree_to_triples(parent_source, source, etree.parse(filename)):
            g.add(t)

    g.bind('recipes', RECIPES_SOURCE.ns)
    for t in recipe_etree_to_triples(RECIPES_SOURCE,
                                     etree.parse("Config/recipes.xml")):
        g.add(t)
    print g.serialize(format='turtle')
    
if __name__ == '__main__':
    main()
