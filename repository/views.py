from bson.errors import InvalidId

from rest_framework.response import Response
from rest_framework import exceptions

from django.conf import settings
from django.core.files.storage import default_storage

from dlkit_django.errors import PermissionDenied, InvalidArgument, IllegalState,\
    NotFound, NoAccess
from dlkit_django.primordium import Id, Type
from dlkit_django.proxy_example import TestRequest
from dlkit.mongo.records.types import EDX_COMPOSITION_GENUS_TYPES,\
    COMPOSITION_RECORD_TYPES, REPOSITORY_GENUS_TYPES

from utilities import general as gutils
from utilities import repository as rutils
from producer.receivers import RabbitMQReceiver
from producer.tasks import import_file
from producer.views import ProducerAPIViews
from producer_main.celery import app as celery_app

EDX_COMPOSITION_RECORD_TYPE = Type(**COMPOSITION_RECORD_TYPES['edx-composition'])
EDX_COMPOSITION_GENUS_TYPES_STR = [str(Type(**genus_type))
                                   for k, genus_type in EDX_COMPOSITION_GENUS_TYPES.iteritems()]


class AssetDetails(ProducerAPIViews):
    """
    Get asset details
    api/v1/repository/assets/<asset_id>/

    GET, PUT, DELETE
    PUT to modify an existing asset (name or contents). Include only the changed parameters.
        If files are included, all current files are deleted / replaced.
    DELETE to remove from the repository.

    Note that for RESTful calls, you need to set the request header
    'content-type' to 'application/json'

    Example (note the use of double quotes!!):
       {"name" : "an updated item"}
    """

    def delete(self, request, asset_id, format=None):
        try:
            repository = rutils.get_object_repository(self.rm,
                                                      asset_id,
                                                      'asset')

            # need to manually delete the asset contents
            asset = repository.get_asset(gutils.clean_id(asset_id))
            for asset_content in asset.get_asset_contents():
                repository.delete_asset_content(asset_content.ident)

            repository.delete_asset(gutils.clean_id(asset_id))
            return gutils.DeletedResponse()
        except (PermissionDenied, IllegalState, InvalidId) as ex:
            gutils.handle_exceptions(ex)

    def get(self, request, asset_id, format=None):
        try:
            repository = rutils.get_object_repository(self.rm,
                                                      asset_id,
                                                      'asset')
            asset = repository.get_asset(gutils.clean_id(asset_id))
            asset_map = rutils.update_asset_urls(repository, asset)

            gutils.update_links(request, asset_map)

            return Response(asset_map)
        except (PermissionDenied, NotFound, InvalidId) as ex:
            gutils.handle_exceptions(ex)

    def put(self, request, asset_id, format=None):
        try:
            gutils.verify_at_least_one_key_present(self.data,
                                                   ['displayName', 'description', 'files'])

            repository = rutils.get_object_repository(self.rm,
                                                      asset_id,
                                                      'asset')
            original_asset = repository.get_asset(gutils.clean_id(asset_id))

            if 'files' in self.data:
                # delete current assets
                for asset_content in original_asset.get_asset_contents():
                    repository.delete_asset_content(asset_content.ident)

                # create the new contents
                for asset in self.data['files'].items():
                    rutils.attach_asset_content_to_asset({
                        'asset': original_asset,
                        'data': asset[1],
                        'repository': repository
                    })

            if 'displayName' in self.data or 'description' in self.data:
                form = repository.get_asset_form_for_update(gutils.clean_id(asset_id))
                form = gutils.set_form_basics(form, self.data)
                updated_asset = repository.update_asset(form)
            else:
                updated_asset = original_asset

            data = updated_asset.object_map
            return gutils.UpdatedResponse(data)
        except (PermissionDenied, InvalidArgument, NoAccess, InvalidId, KeyError) as ex:
            gutils.handle_exceptions(ex)


class AssetsList(ProducerAPIViews):
    """
    Get or add assets to a repository
    api/v1/repository/assets/

    GET, POST
    GET to view current assets
    POST to create a new asset

    Note that for RESTful calls, you need to set the request header
    'content-type' to 'application/json'

    Example (note the use of double quotes!!):
       {"assetLabel" : <file object>}
    """

    def get(self, request, repository_id=None, format=None):
        try:
            if repository_id is None:
                asset_lookup_session = rutils.get_session(self.rm, 'asset', 'lookup')
                asset_query_session = rutils.get_session(self.rm, 'asset', 'query')

                asset_lookup_session.use_federated_repository_view()
                asset_query_session.use_federated_repository_view()
            else:
                asset_query_session = asset_lookup_session = self.rm.get_repository(
                    gutils.clean_id(repository_id))

            if len(self.data) == 0:
                assets = asset_lookup_session.get_assets()
            else:
                allowable_query_terms = ['displayName', 'description']
                if any(term in self.data for term in allowable_query_terms):
                    querier = asset_query_session.get_asset_query()
                    querier = gutils.config_osid_object_querier(querier, self.data)
                    assets = asset_query_session.get_assets_by_query(querier)
                else:
                    assets = asset_lookup_session.get_assets()

            data = gutils.extract_items(request, assets)

            # need to replace each URL here with CloudFront URL...
            for asset in data['data']['results']:
                asset = rutils.update_asset_urls(asset_lookup_session, asset)

            return Response(data)
        except (PermissionDenied, NotFound) as ex:
            gutils.handle_exceptions(ex)

    def post(self, request, format=None):
        try:
            gutils.verify_keys_present(self.data, ['repositoryId'])
            repository_id = self.data['repositoryId']
            repository = self.rm.get_repository(gutils.clean_id(repository_id))

            gutils.verify_keys_present(self.data, ['files'])

            return_data = {}
            for asset in self.data['files'].items():
                # asset should be a tuple of (asset_label, asset_file_object)
                created_asset = rutils.create_asset(repository, asset)
                return_data[created_asset[0]] = created_asset[1]  # (asset_label: asset_id)

            return gutils.CreatedResponse(return_data)
        except (PermissionDenied, InvalidArgument, KeyError) as ex:
            gutils.handle_exceptions(ex)


class CompositionAssetsList(ProducerAPIViews):
    """
    Get or add assets to a repository
    api/v1/repository/compositions/<composition_id>/assets/

    GET, PUT
    GET to view a composition's current assets
    PUT to append one or more assets to the composition. The assets / assessments must already
        exist elsewhere in the system.

    Note that for RESTful calls, you need to set the request header
    'content-type' to 'application/json'

    Example (note the use of double quotes!!):
       {"assetIds" : ["asset:1@MIT", "assessment:25@MIT"]}
    """

    def get(self, request, composition_id, format=None):
        try:
            repository = rutils.get_object_repository(self.rm,
                                                      composition_id,
                                                      'composition')
            try:
                assets = repository.get_composition_assets(gutils.clean_id(composition_id))
            except NotFound:
                assets = []

            data = gutils.extract_items(request, assets)
            # need to replace each URL here with CloudFront URL...
            for asset in data['data']['results']:
                asset_repo = rutils.get_object_repository(self.rm,
                                                          asset['id'],
                                                          'asset')
                asset = rutils.update_asset_urls(asset_repo, asset)

            return Response(data)
        except (PermissionDenied, NotFound) as ex:
            gutils.handle_exceptions(ex)

    def put(self, request, composition_id, format=None):
        try:
            repository = rutils.get_object_repository(self.rm,
                                                      composition_id,
                                                      'composition')

            gutils.verify_keys_present(self.data, ['assetIds'])

            # remove current assets first, if they exist
            try:
                for asset in repository.get_composition_assets(gutils.clean_id(composition_id)):
                    repository.remove_asset(asset.ident,
                                            gutils.clean_id(composition_id))
            except NotFound:
                pass

            if not isinstance(self.data['assetIds'], list):
                self.data['assetIds'] = [self.data['assetIds']]

            for asset_id in self.data['assetIds']:
                repository.add_asset(gutils.clean_id(asset_id),
                                     gutils.clean_id(composition_id))
            assets = repository.get_composition_assets(gutils.clean_id(composition_id))
            data = gutils.extract_items(request, assets)

            return gutils.UpdatedResponse(data)
        except (PermissionDenied, InvalidArgument, KeyError) as ex:
            gutils.handle_exceptions(ex)


class CompositionDetails(ProducerAPIViews):
    """
    Get asset details
    api/v1/repository/compositions/<composition_id>/

    GET, PUT, DELETE
    PUT to modify an existing composition (name, description, or children).
        Include only the changed parameters.
        If children are included, all current ones are deleted / replaced.
        The order in which children are provided persists, so to change the
        order, PUT them back in the desired order.
    DELETE to remove from the repository. Does NOT remove the children objects.

    Note that for RESTful calls, you need to set the request header
    'content-type' to 'application/json'

    Example (note the use of double quotes!!):
       {"name" : "an updated composition",
        "childIds": ["asset1", "asset2"]}
    """

    def delete(self, request, composition_id, format=None):
        try:
            repository = rutils.get_object_repository(self.rm,
                                                      composition_id,
                                                      'composition')

            repository.delete_composition(gutils.clean_id(composition_id))
            return gutils.DeletedResponse()
        except (PermissionDenied, IllegalState, InvalidId) as ex:
            gutils.handle_exceptions(ex)

    def get(self, request, composition_id, format=None):
        try:
            repository = rutils.get_object_repository(self.rm,
                                                      composition_id,
                                                      'composition')

            composition = repository.get_composition(gutils.clean_id(composition_id))
            composition_map = composition.object_map
            gutils.update_links(request, composition_map)

            return Response(composition_map)
        except (PermissionDenied, NotFound, InvalidId) as ex:
            gutils.handle_exceptions(ex)

    def put(self, request, composition_id, format=None):
        try:
            gutils.verify_at_least_one_key_present(self.data,
                                                   ['displayName', 'description', 'childIds',
                                                    'startDate', 'endDate', 'visibleToStudents',
                                                    'draft'])

            repository = rutils.get_object_repository(self.rm,
                                                      composition_id,
                                                      'composition')

            form = repository.get_composition_form_for_update(gutils.clean_id(composition_id))
            if 'childIds' in self.data:
                form.clear_children()
                self.data['childIds'] = rutils.convert_to_id_list(self.data['childIds'])
                form.set_children(self.data['childIds'])

            form = gutils.set_form_basics(form, self.data)

            composition = repository.get_composition(gutils.clean_id(composition_id))

            if str(composition.genus_type) in EDX_COMPOSITION_GENUS_TYPES_STR:
                if 'startDate' in self.data:
                    form = rutils.update_edx_composition_date(form, 'start', self.data['startDate'])

                if 'endDate' in self.data:
                    form = rutils.update_edx_composition_date(form, 'end', self.data['endDate'])

                if 'visibleToStudents' in self.data:
                    form = rutils.update_edx_composition_boolean(form,
                                                                 'visible_to_students',
                                                                 bool(self.data['visibleToStudents']))

                if 'draft' in self.data:
                    form = rutils.update_edx_composition_boolean(form,
                                                                 'draft',
                                                                 bool(self.data['draft']))

            composition = repository.update_composition(form)

            return gutils.UpdatedResponse(composition.object_map)
        except (PermissionDenied, InvalidArgument, InvalidId, KeyError) as ex:
            gutils.handle_exceptions(ex)


class CompositionsList(ProducerAPIViews):
    """
    Get or add compositions to a repository
    api/v1/repository/compositions/

    GET, POST
    GET to view current compositions; can filter by type, i.e. ?course&vertical
    POST to create a new composition

    Note that for RESTful calls, you need to set the request header
    'content-type' to 'application/json'

    Example (note the use of double quotes!!):
       {"name": "a vertical",
        "description": "high",
        "childIds": ["abc@1:MIT"]}
    """
    def _get_map_with_children(self, obj):
        obj_map = obj.object_map
        obj_map['children'] = []
        for child in obj.get_children():
            obj_map['children'].append(self._get_map_with_children(child))
        return obj_map

    def get(self, request, repository_id=None, format=None):
        try:
            if repository_id is None:
                composition_lookup_session = rutils.get_session(self.rm, 'composition', 'lookup')
                composition_query_session = rutils.get_session(self.rm, 'composition', 'query')

                composition_lookup_session.use_federated_repository_view()
                composition_query_session.use_federated_repository_view()
            else:
                composition_query_session = composition_lookup_session = self.rm.get_repository(
                    gutils.clean_id(repository_id))

            if len(self.data) == 0:
                compositions = composition_lookup_session.get_compositions()
            elif ((len(self.data) == 1 and 'nested' in self.data) or
                  (len(self.data) == 2 and 'nested' in self.data and 'page' in self.data)):
                compositions = []
                chapters = composition_query_session.get_compositions_by_genus_type(
                    str(Type(**EDX_COMPOSITION_GENUS_TYPES['chapter'])))
                for chapter in chapters:
                    compositions.append(self._get_map_with_children(chapter))
                # hack...
                compositions = sorted(compositions, key=lambda k: k['id'])
            else:
                allowable_query_terms = ['displayName', 'description', 'course', 'chapter',
                                         'sequential', 'split_test', 'vertical']
                if any(term in self.data for term in allowable_query_terms):
                    compositions = []
                    if any(term in self.data for term in ['displayName', 'description']):
                        querier = composition_query_session.get_composition_query()
                        querier = gutils.config_osid_object_querier(querier, self.data)
                        compositions += list(composition_query_session.get_compositions_by_query(querier))
                    for genus_val, empty in self.data.iteritems():
                        if genus_val not in ['page', 'displayName', 'description', 'nested']:
                            try:
                                compositions += list(
                                    composition_query_session.get_compositions_by_genus_type(
                                        str(Type(**EDX_COMPOSITION_GENUS_TYPES[genus_val]))))
                            except KeyError:
                                raise IllegalState('Invalid query genus type provided. Only "course", ' +
                                                   '"chapter", "sequential", "split_test", and "vertical" ' +
                                                   'are allowed.')
                else:
                    compositions = composition_lookup_session.get_compositions()

            data = gutils.extract_items(request, compositions)

            return Response(data)
        except (PermissionDenied, NotFound, IllegalState) as ex:
            gutils.handle_exceptions(ex)

    def post(self, request, format=None):
        try:
            gutils.verify_keys_present(self.data, ['repositoryId'])
            repository_id = self.data['repositoryId']

            repository = self.rm.get_repository(gutils.clean_id(repository_id))
            gutils.verify_keys_present(self.data, ['displayName', 'description'])

            if 'genusTypeId' in self.data and 'edx' in self.data['genusTypeId']:
                form = repository.get_composition_form_for_create([EDX_COMPOSITION_RECORD_TYPE])
                edx_type = self.data['genusTypeId']  # assumes type is full genusType string
                try:
                    if edx_type not in EDX_COMPOSITION_GENUS_TYPES_STR:
                        raise KeyError
                    form.set_genus_type(Type(edx_type))

                    if 'startDate' in self.data:
                        form = rutils.update_edx_composition_date(form, 'start', self.data['startDate'])

                    if 'endDate' in self.data:
                        form = rutils.update_edx_composition_date(form, 'end', self.data['endDate'])

                    if 'visibleToStudents' in self.data:
                        form = rutils.update_edx_composition_boolean(form,
                                                                     'visible_to_students',
                                                                     bool(self.data['visibleToStudents']))

                    if 'draft' in self.data:
                        form = rutils.update_edx_composition_boolean(form,
                                                                     'draft',
                                                                     bool(self.data['draft']))

                except KeyError:
                    raise InvalidArgument('Bad genus type provided.')
            else:
                form = repository.get_composition_form_for_create([])
            form = gutils.set_form_basics(form, self.data)

            if 'childIds' in self.data:
                self.data['childIds'] = rutils.convert_to_id_list(self.data['childIds'])
                form.set_children(self.data['childIds'])

            composition = repository.create_composition(form)
            return gutils.CreatedResponse(composition.object_map)
        except (PermissionDenied, InvalidArgument, IllegalState, KeyError) as ex:
            gutils.handle_exceptions(ex)


class RepositoryDetails(ProducerAPIViews):
    """
    Shows details for a specific repository.
    api/v1/repository/repositories/<repository_id>/

    GET, PUT, DELETE
    PUT will update the repository. Only changed attributes need to be sent.
    DELETE will remove the repository.

    Note that for RESTful calls, you need to set the request header
    'content-type' to 'application/json'

    Example (note the use of double quotes!!):
       {"name" : "a new repository"}
    """
    def delete(self, request, repository_id, format=None):
        try:
            self.rm.delete_repository(gutils.clean_id(repository_id))
            return gutils.DeletedResponse()
        except (PermissionDenied, NotFound, InvalidId) as ex:
            gutils.handle_exceptions(ex)
        except IllegalState as ex:
            modified_ex = type(ex)('Repository is not empty.')
            gutils.handle_exceptions(modified_ex)

    def get(self, request, repository_id, format=None):
        try:
            repository = self.rm.get_repository(gutils.clean_id(repository_id))
            repository = gutils.convert_dl_object(repository)
            gutils.update_links(request, repository)
            return Response(repository)
        except (PermissionDenied, InvalidId, NotFound) as ex:
            gutils.handle_exceptions(ex)

    def put(self, request, repository_id, format=None):
        try:
            form = self.rm.get_repository_form_for_update(gutils.clean_id(repository_id))
            gutils.verify_at_least_one_key_present(self.data, ['displayName', 'description'])

            form = gutils.set_form_basics(form, self.data)

            updated_repository = self.rm.update_repository(form)
            updated_repository = gutils.convert_dl_object(updated_repository)

            return gutils.UpdatedResponse(updated_repository)
        except (PermissionDenied, KeyError, InvalidArgument, InvalidId, NotFound) as ex:
            gutils.handle_exceptions(ex)


class RepositoriesList(ProducerAPIViews):
    """
    List all available repositories.
    api/v1/repository/repositories/

    POST allows you to create a new repository, requires two parameters:
      * name
      * description

    Alternatively, if you provide an assessment bank ID,
    the repository will be orchestrated to have a matching internal identifier.
    The name and description will be set for you.
      * bankId
      * name (optional)
      * description (optional)

    Note that for RESTful calls, you need to set the request header
    'content-type' to 'application/json'

    Example (note the use of double quotes!!):
      {"name" : "a new repository",
       "description" : "this is a test"}

       OR
       {"bankId": "assessment.Bank%3A5547c37cea061a6d3f0ffe71%40cs-macbook-pro"}
    """

    def get(self, request, format=None):
        """
        List all available repositories
        """
        try:
            repositories = self.rm.repositories
            repositories = gutils.extract_items(request, repositories)
            return Response(repositories)
        except PermissionDenied:
            raise exceptions.AuthenticationFailed('Permission denied. You do not have '
                                                  'rights to view repositories.')

    def post(self, request, format=None):
        """
        Create a new repository, if authorized

        """
        try:
            if 'bankId' not in self.data:
                form = self.rm.get_repository_form_for_create([])
                gutils.verify_keys_present(self.data, ['displayName', 'description'])
                finalize_method = self.rm.create_repository
            else:
                repository = self.rm.get_repository(gutils.clean_id(self.data['bankId']))
                form = self.rm.get_repository_form_for_update(repository.ident)
                finalize_method = self.rm.update_repository

            form = gutils.set_form_basics(form, self.data)

            new_repo = gutils.convert_dl_object(finalize_method(form))

            return gutils.CreatedResponse(new_repo)
        except (PermissionDenied, InvalidArgument, NotFound, KeyError) as ex:
            gutils.handle_exceptions(ex)


class RepositoryChildrenList(ProducerAPIViews):
    """
    List all child repositories.
    api/v1/repository/<repository_id>/children

    PUT allows you to over-write the list of children (NOT append)

    Note that for RESTful calls, you need to set the request header
    'content-type' to 'application/json'

    Example (note the use of double quotes!!):
      {"childIds": ["repository.Repository%3A5547c37cea061a6d3f0ffe71%40cs-macbook-pro"]}
    """

    def get(self, request, repository_id, format=None):
        """
        List all child repositories
        """
        try:
            repositories = self.rm.get_child_repositories(gutils.clean_id(repository_id))
            repositories = gutils.extract_items(request, repositories)
            return Response(repositories)
        except PermissionDenied:
            raise exceptions.AuthenticationFailed('Permission denied. You do not have '
                                                  'rights to view repositories.')

    def put(self, request, repository_id, format=None):
        """
        Appends child repositories, removing all existing children repos

        """
        try:
            gutils.verify_keys_present(self.data, ['childIds'])
            self.rm.remove_child_repositories(gutils.clean_id(repository_id))
            for child_id in self.data['childIds']:
                self.rm.add_child_repository(gutils.clean_id(repository_id),
                                             gutils.clean_id(child_id))
            return gutils.UpdatedResponse()
        except (PermissionDenied, InvalidArgument, NotFound, KeyError) as ex:
            gutils.handle_exceptions(ex)


@celery_app.task()
def _upload_error_simple(uuid):
    print uuid
    import pdb
    pdb.set_trace()
    result = celery_app.AsyncResult(uuid)
    result.get()
    print type(result)
    print result.backend
    print result.state
    print result.result
    print result.traceback
    msg = 'Task {0} raised exception: {1!r}\n{2!r}'.format(uuid,
                                                           result.result,
                                                           result.traceback)


class UploadNewClassFile(ProducerAPIViews):
    """Uploads and imports a given class file"""
    def post(self, request, repository_id, format=None):
        """
        Create a new repository, if authorized
        """
        try:
            if 'files' not in self.data:
                raise InvalidArgument('You must include a file with your POST data.')
            if len(self.data['files']) > 1:
                raise InvalidArgument('You can only upload a single course at one time.')

            domain_repo = self.rm.get_repository(gutils.clean_id(repository_id))
            if str(domain_repo.genus_type) != str(Type(**REPOSITORY_GENUS_TYPES['domain-repo'])):
                raise InvalidArgument('You cannot upload classes to a non-domain repository.')

            uploaded_file = self.data['files'][self.data['files'].keys()[0]]
            self.path = default_storage.save('{0}/{1}'.format(settings.MEDIA_ROOT,
                                                              uploaded_file.name),
                                             uploaded_file)
            self.async_result = import_file.apply_async((self.path, domain_repo, request.user))
            return Response()
        except (PermissionDenied, TypeError, InvalidArgument, NotFound, KeyError) as ex:
            gutils.handle_exceptions(ex)