from elasticsearch_dsl import DocType, InnerDoc, Integer, Text, Field, Object, Keyword, \
    analyzer, tokenizer, FacetedSearch, TermsFacet, connections

path_tokenizer = tokenizer('path_tokenizer', type='path_hierarchy', delimiter='\\')
path_analyzer = analyzer('path_analyzer', tokenizer=path_tokenizer)


class Binary(Field):
    name = 'binary'


class Position(InnerDoc):
    top = Integer()
    left = Integer()
    bottom = Integer()
    right = Integer()


class Face(DocType):
    file_name = Text(analyzer=path_analyzer,
                     fields={'raw': Keyword()})
    features = Binary()

    position = Object(Position)
    person = Text(
        fields={'raw': Keyword()}
    )

    class Index:
        name = 'faces'


class Photo(DocType):
    file_name = Text(fields={'raw': Keyword()})

    persons = Text(
        fields={'raw': Keyword()}
    )

    person_count = Integer()

    class Index:
        name = 'photos'

    def __init__(self, file_name=None, persons=None, meta=None):
        super(Photo, self).__init__(meta)
        self.file_name = file_name
        self.persons = persons
        if persons:
            self.person_count = len(persons)


class Cluster(DocType):
    faces = Keyword()
    face_count = Integer()
    person = Keyword()

    class Index:
        name = 'clusters'

    def __init__(self, faces=None, person=None, meta=None):
        super(Cluster, self).__init__(meta)
        if faces:
            self.faces = faces
            self.face_count = len(faces)
            if person:
                self.person = person

    def update_faces_index(self):
        q = {
            "script": {
                "inline": "ctx._source.person=params.person",
                "lang": "painless",
                "params": {
                    "person": self.person
                }
            },
            "query": {
                "terms": {
                    "_id": self.faces
                }
            }
        }
        es = connections.get_connection()
        es.update_by_query(body=q, doc_type='doc', index='faces', conflicts='proceed')


class PhotoSearch(FacetedSearch):
    index = 'photos'
    doc_types = [Photo, ]
    fields = ['persons', 'file_name']

    facets = {
        'persons': TermsFacet(field='persons.raw', size=200),
        'person_count': TermsFacet(field='person_count', size=200)
    }

    def query(self, search, query):
        if query:
            return search.query("simple_query_string", fields=self.fields, query=query, default_operator='and')
        return search

    def highlight(self, search):
        return search
