import envoy

# start elastic search

# set the python path to include the parent directory, so that
# mongo connector recognizes our custom dlkit doc manager
envoy.run("export PYTHONPATH=../")
envoy.run("mongo-connector  -m localhost:27017 -t localhost:9200 -d dlkit_elastic_search_doc_manager &")

# start rabbitMQ

# start the node server
envoy.run("node node_modules/server.js &")
