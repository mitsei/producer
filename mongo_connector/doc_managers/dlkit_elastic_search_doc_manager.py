"""Most of this code is copied from the built-in mongo-connector elastic_doc_manager
but adds in some massaging to put repositoryID / run name directly into each asset that is created.
This denormalizes some data, but makes it easier to run faceted search.
"""

# Copyright 2013-2014 MongoDB, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# """Elasticsearch implementation of the DocManager interface.
#
# Receives documents from an OplogThread and takes the appropriate actions on
# Elasticsearch.
# """


import base64
import logging

from threading import Timer

import bson.json_util
from bson import ObjectId

from elasticsearch import Elasticsearch, exceptions as es_exceptions
from elasticsearch.helpers import scan, streaming_bulk

from mongo_connector import errors
from mongo_connector.compat import u
from mongo_connector.constants import (DEFAULT_COMMIT_INTERVAL,
                                       DEFAULT_MAX_BULK)
from mongo_connector.util import exception_wrapper, retry_until_ok
from mongo_connector.doc_managers.doc_manager_base import DocManagerBase
from mongo_connector.doc_managers.formatters import DefaultDocumentFormatter

from django.conf import settings
from producer_main import settings as producer_settings
settings.configure(**producer_settings.__dict__)

from dlkit_django.proxy_example import User
from utilities.general import activate_managers, get_session_data, clean_id


def add_metadata(dictionary, key, value):
    if key not in dictionary:
        dictionary.update({
            key: []
        })
    if value not in dictionary[key]:
        dictionary[key].append(value)

def create_test_request(test_user):
    from django.http import HttpRequest
    from django.conf import settings
    from django.utils.importlib import import_module
    #http://stackoverflow.com/questions/16865947/django-httprequest-object-has-no-attribute-session
    test_request = HttpRequest()
    engine = import_module(settings.SESSION_ENGINE)
    session_key = None
    test_request.user = test_user
    test_request.session = engine.SessionStore(session_key)
    return test_request


wrap_exceptions = exception_wrapper({
    es_exceptions.ConnectionError: errors.ConnectionFailed,
    es_exceptions.TransportError: errors.OperationFailed,
    es_exceptions.NotFoundError: errors.OperationFailed,
    es_exceptions.RequestError: errors.OperationFailed})

LOG = logging.getLogger(__name__)


class DocManager(DocManagerBase):
    """DLKit -> Elasticsearch implementation of the DocManager interface.

    Receives documents from an OplogThread and takes the appropriate actions on
    Elasticsearch. Massages the DLKit data to include repository ID and run info
    for assets
    """

    def __init__(self, url, auto_commit_interval=DEFAULT_COMMIT_INTERVAL,
                 unique_key='_id', chunk_size=DEFAULT_MAX_BULK,
                 meta_index_name="mongodb_meta", meta_type="mongodb_meta",
                 attachment_field="content", **kwargs):
        self.elastic = Elasticsearch(
            hosts=[url], **kwargs.get('clientOptions', {}))
        self.auto_commit_interval = auto_commit_interval
        self.meta_index_name = meta_index_name
        self.meta_type = meta_type
        self.unique_key = unique_key
        self.chunk_size = chunk_size
        if self.auto_commit_interval not in [None, 0]:
            self.run_auto_commit()
        self._formatter = DefaultDocumentFormatter()

        self.has_attachment_mapping = False
        self.attachment_field = attachment_field

    def _index_and_mapping(self, namespace):
        """Helper method for getting the index and type from a namespace."""
        index, doc_type = namespace.split('.', 1)
        return index.lower(), doc_type

    def stop(self):
        """Stop the auto-commit thread."""
        self.auto_commit_interval = None

    def apply_update(self, doc, update_spec):
        if "$set" not in update_spec and "$unset" not in update_spec:
            # Don't try to add ns and _ts fields back in from doc
            return update_spec
        return super(DocManager, self).apply_update(doc, update_spec)

    @wrap_exceptions
    def handle_command(self, doc, namespace, timestamp):
        db = namespace.split('.', 1)[0]
        if doc.get('dropDatabase'):
            dbs = self.command_helper.map_db(db)
            for _db in dbs:
                self.elastic.indices.delete(index=_db.lower())

        if doc.get('renameCollection'):
            raise errors.OperationFailed(
                "elastic_doc_manager does not support renaming a mapping.")

        if doc.get('create'):
            db, coll = self.command_helper.map_collection(db, doc['create'])
            if db and coll:
                self.elastic.indices.put_mapping(
                    index=db.lower(), doc_type=coll,
                    body={
                        "_source": {"enabled": True}
                    })

        if doc.get('drop'):
            db, coll = self.command_helper.map_collection(db, doc['drop'])
            if db and coll:
                self.elastic.indices.delete_mapping(index=db.lower(),
                                                    doc_type=coll)

    @wrap_exceptions
    def update(self, document_id, update_spec, namespace, timestamp):
        """Apply updates given in update_spec to the document whose id
        matches that of doc.
        """
        self.commit()
        index, doc_type = self._index_and_mapping(namespace)
        document = self.elastic.get(index=index, doc_type=doc_type,
                                    id=u(document_id))
        updated = self.apply_update(document['_source'], update_spec)
        # _id is immutable in MongoDB, so won't have changed in update
        updated['_id'] = document['_id']
        self.upsert(updated, namespace, timestamp)

        # cjshaw@mit.edu
        # if the update is to a repository.Composition, make sure the
        # assets listed in assetIds also have a reference to the
        # repositoryId / parent of the given composition.
        if ('edx-composition' in update_spec['genusTypeId'] and
                'assetIds' in update_spec):
            # get repositoryId and it's parent
            app_user = User(username='producer2@mit.edu', authenticated=True)
            dummy_request = create_test_request(app_user)
            activate_managers(dummy_request)
            rm = get_session_data(dummy_request, 'rm')
            run_repo_id = update_spec['repositoryId']
            run_repo = rm.get_repository(clean_id(run_repo_id))
            course_repo = rm.get_parent_repositories(run_repo.ident).next()
            domain_repo = rm.get_parent_repositories(course_repo.ident).next()

            # now get the assets referenced in update_spec['assetIds'] and
            # append the course_run_name to their docs
            for asset_id in update_spec['assetIds']:
                asset_doc_id = ObjectId(clean_id(asset_id).identifier)
                asset_namespace = '{0}.{1}'.format(index, 'Asset')
                asset_document = self.elastic.get(index=index, doc_type='Asset',
                                                  id=u(asset_doc_id))

                denormalized_asset = asset_document['_source'].copy()
                add_metadata(denormalized_asset,
                             'runs',
                             str(run_repo.ident))
                add_metadata(denormalized_asset,
                             'courses',
                             str(course_repo.ident))
                add_metadata(denormalized_asset,
                             'domains',
                             str(domain_repo.ident))

                updated_asset = self.apply_update(asset_document['_source'], denormalized_asset)
                # _id is immutable in MongoDB, so won't have changed in update
                updated_asset['_id'] = asset_document['_id']
                self.upsert(updated_asset, asset_namespace, timestamp)

            # also remove any runs, if asset removed from a composition
            if 'assetIds' in document['_source']:
                removed_assets = [i for i in document['_source']['assetIds']
                                  if i not in update_spec['assetIds']]
                for asset_id in removed_assets:
                    asset_doc_id = ObjectId(clean_id(asset_id).identifier)
                    asset_namespace = '{0}.{1}'.format(index, 'Asset')
                    asset_document = self.elastic.get(index=index, doc_type='Asset',
                                                      id=u(asset_doc_id))

                    denormalized_asset = asset_document['_source'].copy()
                    denormalized_asset['runs'].remove(str(run_repo.ident))
                    denormalized_asset['courses'].remove(str(course_repo.ident))
                    denormalized_asset['domains'].remove(domain_repo.ident)

                    updated_asset = self.apply_update(asset_document['_source'], denormalized_asset)
                    # _id is immutable in MongoDB, so won't have changed in update
                    updated_asset['_id'] = asset_document['_id']
                    self.upsert(updated_asset, asset_namespace, timestamp)

        # upsert() strips metadata, so only _id + fields in _source still here
        return updated

    @wrap_exceptions
    def upsert(self, doc, namespace, timestamp):
        """Insert a document into Elasticsearch."""
        index, doc_type = self._index_and_mapping(namespace)
        # No need to duplicate '_id' in source document
        doc_id = u(doc.pop("_id"))
        metadata = {
            "ns": namespace,
            "_ts": timestamp
        }
        # Index the source document, using lowercase namespace as index name.
        self.elastic.index(index=index, doc_type=doc_type,
                           body=self._formatter.format_document(doc), id=doc_id,
                           refresh=(self.auto_commit_interval == 0))
        # Index document metadata with original namespace (mixed upper/lower).
        self.elastic.index(index=self.meta_index_name, doc_type=self.meta_type,
                           body=bson.json_util.dumps(metadata), id=doc_id,
                           refresh=(self.auto_commit_interval == 0))
        # Leave _id, since it's part of the original document
        doc['_id'] = doc_id

    @wrap_exceptions
    def bulk_upsert(self, docs, namespace, timestamp):
        """Insert multiple documents into Elasticsearch."""
        def docs_to_upsert():
            doc = None
            for doc in docs:
                # Remove metadata and redundant _id
                index, doc_type = self._index_and_mapping(namespace)
                doc_id = u(doc.pop("_id"))
                document_action = {
                    "_index": index,
                    "_type": doc_type,
                    "_id": doc_id,
                    "_source": self._formatter.format_document(doc)
                }
                document_meta = {
                    "_index": self.meta_index_name,
                    "_type": self.meta_type,
                    "_id": doc_id,
                    "_source": {
                        "ns": index,
                        "_ts": timestamp
                    }
                }
                yield document_action
                yield document_meta
            if not doc:
                raise errors.EmptyDocsError(
                    "Cannot upsert an empty sequence of "
                    "documents into Elastic Search")
        try:
            kw = {}
            if self.chunk_size > 0:
                kw['chunk_size'] = self.chunk_size

            responses = streaming_bulk(client=self.elastic,
                                       actions=docs_to_upsert(),
                                       **kw)

            for ok, resp in responses:
                if not ok:
                    LOG.error(
                        "Could not bulk-upsert document "
                        "into ElasticSearch: %r" % resp)
            if self.auto_commit_interval == 0:
                self.commit()
        except errors.EmptyDocsError:
            # This can happen when mongo-connector starts up, there is no
            # config file, but nothing to dump
            pass

    @wrap_exceptions
    def insert_file(self, f, namespace, timestamp):
        doc = f.get_metadata()
        doc_id = str(doc.pop('_id'))
        index, doc_type = self._index_and_mapping(namespace)

        # make sure that elasticsearch treats it like a file
        if not self.has_attachment_mapping:
            body = {
                "properties": {
                    self.attachment_field: {"type": "attachment"}
                }
            }
            self.elastic.indices.put_mapping(index=index,
                                             doc_type=doc_type,
                                             body=body)
            self.has_attachment_mapping = True

        metadata = {
            'ns': namespace,
            '_ts': timestamp,
        }

        doc = self._formatter.format_document(doc)
        doc[self.attachment_field] = base64.b64encode(f.read()).decode()

        self.elastic.index(index=index, doc_type=doc_type,
                           body=doc, id=doc_id,
                           refresh=(self.auto_commit_interval == 0))
        self.elastic.index(index=self.meta_index_name, doc_type=self.meta_type,
                           body=bson.json_util.dumps(metadata), id=doc_id,
                           refresh=(self.auto_commit_interval == 0))

    @wrap_exceptions
    def remove(self, document_id, namespace, timestamp):
        """Remove a document from Elasticsearch."""
        index, doc_type = self._index_and_mapping(namespace)
        self.elastic.delete(index=index, doc_type=doc_type,
                            id=u(document_id),
                            refresh=(self.auto_commit_interval == 0))
        self.elastic.delete(index=self.meta_index_name, doc_type=self.meta_type,
                            id=u(document_id),
                            refresh=(self.auto_commit_interval == 0))

    @wrap_exceptions
    def _stream_search(self, *args, **kwargs):
        """Helper method for iterating over ES search results."""
        for hit in scan(self.elastic, query=kwargs.pop('body', None),
                        scroll='10m', **kwargs):
            hit['_source']['_id'] = hit['_id']
            yield hit['_source']

    def search(self, start_ts, end_ts):
        """Query Elasticsearch for documents in a time range.

        This method is used to find documents that may be in conflict during
        a rollback event in MongoDB.
        """
        return self._stream_search(
            index=self.meta_index_name,
            body={
                "query": {
                    "filtered": {
                        "filter": {
                            "range": {
                                "_ts": {"gte": start_ts, "lte": end_ts}
                            }
                        }
                    }
                }
            })

    def commit(self):
        """Refresh all Elasticsearch indexes."""
        retry_until_ok(self.elastic.indices.refresh, index="")

    def run_auto_commit(self):
        """Periodically commit to the Elastic server."""
        self.elastic.indices.refresh()
        if self.auto_commit_interval not in [None, 0]:
            Timer(self.auto_commit_interval, self.run_auto_commit).start()

    @wrap_exceptions
    def get_last_doc(self):
        """Get the most recently modified document from Elasticsearch.

        This method is used to help define a time window within which documents
        may be in conflict after a MongoDB rollback.
        """
        try:
            result = self.elastic.search(
                index=self.meta_index_name,
                body={
                    "query": {"match_all": {}},
                    "sort": [{"_ts": "desc"}],
                },
                size=1
            )["hits"]["hits"]
            for r in result:
                r['_source']['_id'] = r['_id']
                return r['_source']
        except es_exceptions.RequestError:
            # no documents so ES returns 400 because of undefined _ts mapping
            return None

