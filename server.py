import os
from elasticsearch import Elasticsearch
from flask import Flask, render_template, request
from elastic import PhotoSearch, Cluster
from elasticsearch_dsl import connections, Search, A
from argparse import ArgumentParser

app = Flask(__name__, static_url_path='')


def update_cluster(cluster):
    q = {
        "script": {
            "inline": "ctx._source.person=params.person",
            "lang": "painless",
            "params": {
                "person": cluster.person
            }
        },
        "query": {
            "terms": {
                "_id": cluster.faces
            }
        }
    }
    es = Elasticsearch()
    es.update_by_query(body=q, doc_type='doc', index='faces', conflicts='proceed')


@app.errorhandler(500)
def internal_server_error(e):
    return str(e), 500


@app.route('/clusters', methods=["GET", "POST"])
def display_clusters():
    if request.method == "POST":
        cluster = Cluster.get(id=request.values.get('cluster_id'))
        cluster.person = request.values.get('person')
        cluster.save(refresh=True)
        update_cluster(cluster)

    a = A("terms", field="person.raw", size=10000)
    ps = Search()
    ps.aggs.bucket("persons", a)
    psr = ps.execute()

    persons = [b.key for b in psr.aggs['persons']]

    s = Cluster.search().exclude("exists", field="person").sort("-face_count")
    results = s[0:100].execute()

    return render_template('clusters.html', clusters=results, persons=persons)


@app.route('/', methods=["GET", "POST"])
def display_main():
    q = request.values.get('q')
    pc = {"persons": request.values.getlist("person"),
          "person_count": [int(x) for x in request.values.getlist("count")]}

    s = PhotoSearch(query=q, filters=pc)

    print(s._s.to_dict())
    results = s[0:100].execute()
    images = []
    for photo in results:
        images.append(os.path.splitdrive(photo.file_name)[1])
    persons = results.facets.persons
    counts = results.facets.person_count

    return render_template('main.html', images=images, q=q,
                           persons=persons, counts=counts, total_count=results.hits.total)


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("-es", "--elastic", dest="elastic",
                        help="Elasticsearch address, default is localhost", metavar="ADDRESS", default='localhost')
    args = parser.parse_args()

    connections.create_connection(hosts=[args.elastic])
    app.run(debug=False)
