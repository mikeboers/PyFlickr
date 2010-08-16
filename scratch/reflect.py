
import os
import collections

import treesoup

tag_to_method = {}
signatures = {}
tag_to_attrs = {}
tag_to_children = {}
tag_to_common = {}
data_to_source = {}
method_to_args = {}

    
for filename in os.listdir('methods'):
    xml = treesoup.parse(open('methods/' + filename).read().decode('utf8'))
    if not xml.response:
        continue
    
    method = xml.method['name']
    
    try:
        response = treesoup.parse(
            '<?xml version="1.0" encoding="utf-8" ?>'
            '<rsp stat="ok">' +
            xml.response.text +
            '</rsp>'
        )[0]
    except SyntaxError as e:
        print xml.response.text
        print
        print e
        exit()
    
    args = response('argument')
    if args is not None:
        method_to_args[method] = tuple(arg['name'] for arg in args if arg['optional'] != '1')
    
    for node in response.iter():
        
        tag = node.tag
        attrs = set(node.keys())
        children = set(x.tag for x in node)
        
        tag_to_method.setdefault(tag, set()).add(method)
        tag_to_attrs.setdefault(tag, set()).update(attrs)
        tag_to_children.setdefault(tag, set()).update(children)
        
        if tag not in tag_to_common:
            tag_to_common[tag] = attrs.union(children)
        else:
            tag_to_common[tag].intersection_update(attrs.union(children))
        
        for type, names in (('attr', attrs), ('child', children)):
            for name in names:
                chain = response.chain_to(node)
                path = tuple(x.tag for x in response.chain_to(node))
                data_to_source.setdefault((tag, name), set()).add((method, path, type))
        
        signatures.setdefault((
            tag,
            tuple(sorted(attrs)),
            tuple(sorted(children)),
        ), set()).add(method)
    
        collision = attrs.intersection(children)
        if collision:
            print 'collision on', method, tag, collision
                
    # print '\t' + ' '.join(sorted(tags))

def print_tag_map(tag_map):
    for tag, values in sorted(tag_map.items()):
        print str(tag) + ':'
        for value in sorted(values):
            print '\t' + str(value)

#for sig, methods in sorted(signatures.items()):
#    print ', '.join(map(str, sig)) + ':\n\t' + '\n\t'.join(sorted(x[7:] for x in methods))

print_tag_map(data_to_source)

#for method, args in sorted(method_to_args.items()):
#    print method, args