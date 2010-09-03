
import treesoup

tag_to_class = {}

class AutoTypeMeta(type):
    
    def __new__(mcls, name, bases, ns):
        cls = super(AutoTypeMeta, mcls).__new__(mcls, name, bases, ns)
        
        tags = ns.get('__tags__', ())
        for tag in tags:
            AutoType._attr_child_classes[tag] = cls
        
        return cls

class AutoType(treesoup.XML):
    __metaclass__ = AutoTypeMeta
    
    def _wrap_child_element(self, *args):
        obj = super(AutoType, self)._wrap_child_element(*args)
        obj._api = self._api
        return obj
    
    @classmethod
    def make_constructor(cls, api):
        def _func(*args):
            obj = cls(*args)
            obj._api = api
            return obj
        return _func

def autoprop(method, parm_sources, path=None):
    @property
    def _prop(self):
        if not hasattr(self, '__autoprop_cache__'):
            parms = {}
            for key, source in parm_sources.items():
                if source in self.attrib:
                    parms[key] = self[source]
            res = self._api(method, **parms)
            self.__autoprop_cache__ = res
        return self.__autoprop_cache__
    return _prop


class Photo(AutoType):
    __tags__ = ('photo', )
    
    sizes = autoprop('photos.getSizes', {'photo_id': 'id'})
    exif = autoprop('photos.getExif', {'photo_id': 'id', 'secret': 'secret'})

class Tag(AutoType):
    __tags__ = ('tag', )
    
    related = autoprop('tags.getRelated', {'tag': })

if __name__ == '__main__':
    
    from .core import Flickr
    api = Flickr()
    
    photo = api('photos.getInfo', photo_id='4368732797', class_=AutoType.make_constructor(api))
    print photo.perms
    #print photo.exif
    # print photo.sizes[-1]['source']



