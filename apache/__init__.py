import envoy

# set the python path to include the parent directory, so that
# mongo connector recognizes our custom dlkit doc manager
envoy.run("export PYTHONPATH=../")
envoy.run("mongo-connector  -m localhost:27017 -t localhost:9200 -d dlkit_elastic_search_doc_manager &")

