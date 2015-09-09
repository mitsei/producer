import os

from bson.errors import InvalidId

from rest_framework.response import Response
from rest_framework import exceptions

from django.conf import settings
from django.core.files.storage import default_storage
from django.http import HttpResponse

from dlkit.abstract_osid.assessment.objects import Item
from dlkit_django.errors import PermissionDenied, InvalidArgument, IllegalState,\
    NotFound, NoAccess, AlreadyExists
from dlkit_django.primordium import Type
from dlkit.mongo.records.types import EDX_COMPOSITION_GENUS_TYPES,\
    COMPOSITION_RECORD_TYPES, REPOSITORY_GENUS_TYPES, OSID_OBJECT_RECORD_TYPES,\
    EDX_ASSET_CONTENTS_GENUS_TYPES, EDX_ASSESSMENT_ITEM_GENUS_TYPES

from dysonx.dysonx import get_or_create_user_repo, _get_genus_type,\
    _get_asset_content_genus_type

from utilities import general as gutils
from utilities import repository as rutils
from producer.tasks import import_file
from producer.views import ProducerAPIViews


DOMAIN_REPO_GENUS = Type(**REPOSITORY_GENUS_TYPES['domain-repo'])
EDX_COMPOSITION_RECORD_TYPE = Type(**COMPOSITION_RECORD_TYPES['edx-composition'])
EDX_COMPOSITION_GENUS_TYPES_STR = [str(Type(**genus_type))
                                   for k, genus_type in EDX_COMPOSITION_GENUS_TYPES.iteritems()]
EDX_COMPOSITION_TYPES = EDX_COMPOSITION_GENUS_TYPES.keys()
EDX_COMPOSITION_GENUS_TYPES_FOR_FACETS = [str(Type(**genus_type))
    for k, genus_type in EDX_COMPOSITION_GENUS_TYPES.iteritems()
    if k in ['chapter', 'sequential', 'vertical']]
EDX_ASSET_CONTENT_GENUS_TYPES_FOR_FACETS = [str(Type(**genus_type))
    for k, genus_type in EDX_ASSET_CONTENTS_GENUS_TYPES.iteritems()]
EDX_ASSESSMENT_GENUS_TYPES_FOR_FACETS = [str(Type(**genus_type))
    for k, genus_type in EDX_ASSESSMENT_ITEM_GENUS_TYPES.iteritems()]

ENCLOSURE_TYPE = Type(**OSID_OBJECT_RECORD_TYPES['enclosure'])


def get_facets_values(params, facet_prefix):
    if 'selected_facets' in params or 'selected_facets[]' in params:
        param_list = params.getlist('selected_facets')
        if len(param_list) == 0:
            param_list = params.getlist('selected_facets[]')

        facet_params = [f.split(':')[-1]
                        for f in param_list
                        if '{}:'.format(facet_prefix) in f]
        if len(facet_params) == 0:
            return None
        else:
            return facet_params
    else:
        return None

def get_page_and_limits(params):
    """default of 10 items per page"""
    page = 1
    limit = 10
    if 'page' in params:
        page = params['page']
    if 'limit' in params:
        limit = params['limit']
    start_index = (page - 1) * limit
    end_index = (page * limit) - 1
    return start_index, end_index

def get_query_values(params):
    if params is not None:
        params = params.split(' ')
        if not isinstance(params, list):
            params = [params]
    return params

def increment(dictionary, key):
    if key not in dictionary:
        dictionary[key] = 0
    dictionary[key] += 1


class CompositionMapMixin(object):
    def _get_map_with_children(self, obj, renderable=False):
        obj_map = obj.object_map
        obj_map['children'] = []
        for child_id in obj.get_child_ids():
            # need to use unsequestered view so get a lookup manager separately
            composition_lookup_session = rutils.get_session(self.rm, 'composition', 'lookup')
            composition_lookup_session.use_federated_repository_view()
            composition_lookup_session.use_unsequestered_composition_view()
            child = composition_lookup_session.get_composition(child_id)
            if child.is_sequestered():
                try:
                    asset_repo = self.rm.get_repository(gutils.clean_id(obj_map['repositoryId']))
                    for asset in child.assets:
                        if isinstance(asset, Item):
                            item = asset
                            if renderable:
                                item_map = item.object_map
                                item_map['texts']['edxml'] = item.get_edxml_with_aws_urls()
                                obj_map['children'].append(item_map)
                            else:
                                obj_map['children'].append(item.object_map)
                        else:
                            if renderable:
                                obj_map['children'].append(
                                    rutils.update_asset_urls(asset_repo,
                                                             asset,
                                                             {'renderable_edxml': True}))
                            else:
                                obj_map['children'].append(asset.object_map)
                except NotFound:
                    # no assets
                    pass
            else:
                obj_map['children'].append(self._get_map_with_children(child))
        return obj_map

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
            asset_map = rutils.update_asset_urls(repository, asset, self.data)

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

    DEPRECATED

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

            assets = rutils.update_composition_assets(self.am,
                                                      self.rm,
                                                      request.user.username,
                                                      repository,
                                                      composition_id,
                                                      self.data['assetIds'])
            data = gutils.extract_items(request, assets)

            return gutils.UpdatedResponse(data)
        except (PermissionDenied, InvalidArgument, KeyError) as ex:
            gutils.handle_exceptions(ex)


class CompositionDetails(ProducerAPIViews, CompositionMapMixin):
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

            if self.rm.get_repositories_by_composition(
                    gutils.clean_id(composition_id)).available() > 1:
                gutils.verify_keys_present(self.data, ['repoId'])
                composition = repository.get_composition(gutils.clean_id(composition_id))
                if self.data['repoId'] == composition.object_map['repositoryId']:
                    # by default move the composition to the ownership of the next one
                    raise IllegalState('For now, cannot delete from the owner repository.')
                else:
                    self.rm.unassign_composition_from_repository(composition.ident,
                                                                 gutils.clean_id(self.data['repoId']))
            else:
                if 'withChildren' in self.data:
                    # remove children compositions too
                    composition = repository.get_composition(gutils.clean_id(composition_id))
                    repository.use_unsequestered_composition_view()

                    for child_ids in composition.get_child_ids():
                        # use this instead of get_children() because sequestered
                        # compositions don't show up with get_children()
                        repository.delete_composition(child_ids)

                repository.delete_composition(gutils.clean_id(composition_id))
            return gutils.DeletedResponse()
        except (PermissionDenied, IllegalState, InvalidId, KeyError) as ex:
            gutils.handle_exceptions(ex)

    def get(self, request, composition_id, format=None):
        try:
            repository = rutils.get_object_repository(self.rm,
                                                      composition_id,
                                                      'composition')

            composition = repository.get_composition(gutils.clean_id(composition_id))
            if 'fullMap' in self.data:
                # add in the assets and children compositions, in renderable_edxml format
                composition_map = self._get_map_with_children(composition, renderable=True)
            else:
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
                                                    'draft', 'assetIds', 'genusTypeId'])

            repository = rutils.get_object_repository(self.rm,
                                                      composition_id,
                                                      'composition')

            form = repository.get_composition_form_for_update(gutils.clean_id(composition_id))

            form = gutils.set_form_basics(form, self.data)

            composition = repository.get_composition(gutils.clean_id(composition_id))

            if str(composition.genus_type) in EDX_COMPOSITION_GENUS_TYPES_STR:
                if 'startDate' in self.data:
                    try:
                        form = rutils.update_edx_composition_date(form, 'start', self.data['startDate'])
                    except IllegalState:
                        pass

                if 'endDate' in self.data:
                    try:
                        form = rutils.update_edx_composition_date(form, 'end', self.data['endDate'])
                    except IllegalState:
                        pass

                if 'visibleToStudents' in self.data:
                    try:
                        form = rutils.update_edx_composition_boolean(form,
                                                                     'visible_to_students',
                                                                     bool(self.data['visibleToStudents']))
                    except IllegalState:
                        pass

                if 'draft' in self.data:
                    try:
                        form = rutils.update_edx_composition_boolean(form,
                                                                     'draft',
                                                                     bool(self.data['draft']))
                    except IllegalState:
                        pass

            composition = repository.update_composition(form)

            if 'childIds' in self.data:
                if not isinstance(self.data['childIds'], list):
                    self.data['childIds'] = [self.data['childIds']]

                rutils.update_composition_children(repository,
                                                   composition_id,
                                                   self.data['childIds'],
                                                   am=self.am,
                                                   rm=self.rm,
                                                   username=request.user.username)
                composition = repository.get_composition(composition.ident)

            return gutils.UpdatedResponse(composition.object_map)
        except (PermissionDenied, InvalidArgument, InvalidId, KeyError) as ex:
            gutils.handle_exceptions(ex)


class CompositionsList(ProducerAPIViews, CompositionMapMixin):
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
                course_node = rutils.get_course_node(composition_query_session)
                compositions.append(self._get_map_with_children(course_node))
                compositions = compositions[0]['children']  # remove the phantom course_node
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
                    if 'course' in edx_type:
                        raise KeyError

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

            # add the composition to the root course_node if no parentId supplied
            if 'parentId' not in self.data:
                course_node = rutils.get_course_node(repository)
                rutils.append_child_composition(repository, course_node, composition)
            else:
                parent_composition = repository.get_composition(gutils.clean_id(self.data['parentId']))
                rutils.append_child_composition(repository, parent_composition, composition)

            # Should be assigning the composition to THIS repository as well as
            # appending it as a childId.
            try:
                self.rm.assign_composition_to_repository(composition.ident, repository.ident)
                composition = repository.get_composition(composition.ident)
            except AlreadyExists:
                composition = repository.get_composition(composition.ident)

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
            gutils.verify_at_least_one_key_present(self.data, ['displayName', 'description',
                                                               'childIds'])

            form = gutils.set_form_basics(form, self.data)

            updated_repository = self.rm.update_repository(form)

            if 'childIds' in self.data:
                rutils.update_repository_compositions(self.rm,
                                                      updated_repository,
                                                      self.data['childIds'])
                updated_repository = self.rm.get_repository(updated_repository.ident)

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
            if ('genusTypeId' in self.data and
                    self.data['genusTypeId'] == str(rutils.DOMAIN_REPO_GENUS)):
                repo = rutils.create_domain_repo(self.rm,
                                                 self.data['displayName'],
                                                 self.data['description'])
            else:
                if 'bankId' not in self.data:
                    form = self.rm.get_repository_form_for_create([])
                    gutils.verify_keys_present(self.data, ['displayName', 'description'])
                    finalize_method = self.rm.create_repository
                else:
                    repository = self.rm.get_repository(gutils.clean_id(self.data['bankId']))
                    form = self.rm.get_repository_form_for_update(repository.ident)
                    finalize_method = self.rm.update_repository

                form = gutils.set_form_basics(form, self.data)
                repo = finalize_method(form)

            new_repo = gutils.convert_dl_object(repo)

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
            repository_id = gutils.clean_id(repository_id)
            self.rm.remove_child_repositories(repository_id)
            for child_id in self.data['childIds']:
                self.rm.add_child_repository(repository_id, gutils.clean_id(child_id))
            return gutils.UpdatedResponse()
        except (PermissionDenied, InvalidArgument, NotFound, KeyError) as ex:
            gutils.handle_exceptions(ex)


class RepositoryDownload(ProducerAPIViews):
    """
    Download a RUN.
    api/v1/repository/repositories/<repository_id>/download/

    GET
    """
    def get(self, request, repository_id, format=None):
        try:
            run_repo = self.rm.get_repository(gutils.clean_id(repository_id))
            if str(run_repo.genus_type) != str(Type(**REPOSITORY_GENUS_TYPES['course-run-repo'])):
                raise InvalidArgument('You can only download run repositories.')

            filename, olx = run_repo.export_olx()

            response = HttpResponse(content_type="application/tar")
            response['Content-Disposition'] = 'attachment; filename=%s' % filename
            olx.seek(0, os.SEEK_END)
            response.write(olx.getvalue())
            olx.close()

            return response
        except (PermissionDenied, InvalidArgument, NotFound) as ex:
            gutils.handle_exceptions(ex)


class RepositoryQueryPlansAvailable(ProducerAPIViews):
    """
    Get set of queryable options plus their object counts
    api/v1/repository/repositories/<repository_id>/queryplans/

    GET
    """
    def _count_type(self, counts, iterator, querier, catalog, clear_method, match_method, get_method):
        for genus in iterator:
            genus_type = Type(genus)
            if self.facet_resource_types is not None:
                if genus in self.facet_resource_types:
                    getattr(querier, clear_method)()
                    getattr(querier, match_method)(genus_type, True)
                    if genus_type.identifier not in counts:
                        counts.update({
                            genus_type.identifier: [getattr(catalog, get_method)(querier).available(), str(genus_type)]
                        })
                    else:
                        counts[genus_type.identifier][0] += getattr(catalog, get_method)(querier).available()
                else:
                    if genus_type.identifier not in counts:
                        counts[genus_type.identifier] = [0, str(genus_type)]
            else:
                getattr(querier, clear_method)()
                getattr(querier, match_method)(genus_type, True)
                if genus_type.identifier not in counts:
                    counts.update({
                        genus_type.identifier: [getattr(catalog, get_method)(querier).available(), str(genus_type)]
                    })
                else:
                    counts[genus_type.identifier][0] += getattr(catalog, get_method)(querier).available()


    def _count_objects(self, repo, asset_counts):
        bank = self.am.get_bank(repo.ident)
        bank.use_federated_bank_view()

        asset_genus_types = EDX_ASSET_CONTENT_GENUS_TYPES_FOR_FACETS
        composition_genus_types = EDX_COMPOSITION_GENUS_TYPES_FOR_FACETS
        item_genus_types = EDX_ASSESSMENT_GENUS_TYPES_FOR_FACETS

        asset_querier = repo.get_asset_query()
        composition_querier = repo.get_composition_query()
        item_querier = bank.get_item_query()

        if self.query_params is not None and self.query_params != ['']:
            for term in self.query_params:
                asset_querier.match_keyword(term, gutils.WORDIGNORECASE_STRING_MATCH_TYPE, True)
                composition_querier.match_keyword(term, gutils.WORDIGNORECASE_STRING_MATCH_TYPE, True)
                item_querier.match_keyword(term, gutils.WORDIGNORECASE_STRING_MATCH_TYPE, True)

        self._count_type(asset_counts,
                         asset_genus_types,
                         asset_querier,
                         repo,
                         'clear_match_asset_content_genus_type',
                         'match_asset_content_genus_type',
                         'get_assets_by_query')

        self._count_type(asset_counts,
                         composition_genus_types,
                         composition_querier,
                         repo,
                         'clear_genus_type_terms',
                         'match_genus_type',
                         'get_compositions_by_query')

        self._count_type(asset_counts,
                         item_genus_types,
                         item_querier,
                         bank,
                         'clear_genus_type_terms',
                         'match_genus_type',
                         'get_items_by_query')

    def _get_all_items_by_repo(self, repo):
        if isinstance(repo, dict):
            repo = self.rm.get_repository(gutils.clean_id(repo['id']))
        bank = self.am.get_bank(repo.ident)
        bank.use_federated_bank_view()

        repo.use_sequestered_composition_view()


        asset_querier = None
        composition_querier = None
        item_querier = None

        # match facet selected types
        if self.facet_resource_types is not None:
            for resource_type in self.facet_resource_types:
                if resource_type in EDX_COMPOSITION_GENUS_TYPES_STR:
                    if composition_querier is None:
                        composition_querier = repo.get_composition_query()
                    genus_type = Type(resource_type)
                    composition_querier.match_genus_type(genus_type, True)
                elif resource_type == 'edx-assessment-item%3Aproblem%40EDX.ORG':
                    if item_querier is None:
                        item_querier = bank.get_item_query()
                else:
                    if asset_querier is None:
                        asset_querier = repo.get_asset_query()
                    genus_type = Type(resource_type)
                    asset_querier.match_asset_content_genus_type(genus_type, True)
        else:
            # match all objects
            asset_querier = repo.get_asset_query()
            asset_querier.match_any(True)
            composition_querier = repo.get_composition_query()
            composition_querier.match_any(True)
            item_querier = bank.get_item_query()
            item_querier.match_any(True)

        # match query terms
        if self.query_params is not None and self.query_params != ['']:
            for term in self.query_params:
                if asset_querier is not None:
                    asset_querier.match_keyword(term, gutils.WORDIGNORECASE_STRING_MATCH_TYPE, True)
                if composition_querier is not None:
                    composition_querier.match_keyword(term, gutils.WORDIGNORECASE_STRING_MATCH_TYPE, True)
                if item_querier is not None:
                    item_querier.match_keyword(term, gutils.WORDIGNORECASE_STRING_MATCH_TYPE, True)

        # run query
        if asset_querier is not None:
            all_assets = repo.get_assets_by_query(asset_querier)
        else:
            all_assets = None
        if composition_querier is not None:
            all_compositions = repo.get_compositions_by_query(composition_querier)
        else:
            all_compositions = None
        if item_querier is not None:
            all_items = bank.get_items_by_query(item_querier)
        else:
            all_items = None

        return all_assets, all_compositions, all_items

    def _get_run_map(self, repository_id):
        repo_nodes = self.rm.get_repository_nodes(repository_id=gutils.clean_id(repository_id),
                                                  ancestor_levels=0,
                                                  descendant_levels=2,
                                                  include_siblings=False)
        repo_nodes = repo_nodes.get_object_node_map()

        runs = [(r['id'], '{0}, {1}'.format(course['displayName']['text'],
                                            r['displayName']['text']))
                for course in repo_nodes['childNodes']
                for r in course['childNodes']]

        run_map = {}
        for run in runs:
            run_map[run[0]] = run[1]

        return run_map

    def get(self, request, repository_id, format=None):
        try:
            self.facet_resource_types = get_facets_values(self.data, 'resource_type_exact')
            self.facet_course_runs = get_facets_values(self.data, 'course_exact')
            self.query_params = get_query_values(self.data.get('q', None))

            facets = {
                'course': [],
                'resource_type': []
            }

            course_run_counts = {}
            asset_counts = {}

            domain_repo = self.rm.get_repository(gutils.clean_id(repository_id))

            if domain_repo.genus_type != DOMAIN_REPO_GENUS:
                raise InvalidArgument('You can only get query plans for domains.')

            domain_repo.use_federated_repository_view()

            run_map = self._get_run_map(repository_id)
            # first for each repository, get count of its total objects that
            # meet the keyword filter requirement and other facet requirements
            for run_identifier, run_name in run_map.iteritems():
                course_run_counts[run_name] = [0, run_identifier]
                if self.facet_course_runs is None:
                    # do all courses
                    repo = self.rm.get_repository(gutils.clean_id(run_identifier))

                    assets, compositions, items = self._get_all_items_by_repo(repo)

                    for obj in [assets, compositions, items]:
                        if obj is not None:
                            course_run_counts[run_name][0] += obj.available()

                    self._count_objects(repo,
                                        asset_counts)
                else:
                    # only do courses that have been selected
                    if any(run_identifier in course for course in self.facet_course_runs):
                        repo = self.rm.get_repository(gutils.clean_id(run_identifier))

                        assets, compositions, items = self._get_all_items_by_repo(repo)

                        for obj in [assets, compositions, items]:
                            if obj is not None:
                                course_run_counts[run_name][0] += obj.available()

                        self._count_objects(repo,
                                            asset_counts)

            count_cases = [(asset_counts, 'resource_type'),
                           (course_run_counts, 'course')]
            for case in count_cases:
                _counts = []
                for k, v in case[0].iteritems():
                    if isinstance(v, tuple):
                        _counts.append((k, v[0], v[1]))
                    else:
                        _counts.append((k, v))
                facets[case[1]] = sorted(_counts, key=lambda tup: tup[0])

            return_data = {
                'facets': facets
            }
            return Response(return_data)
        except (PermissionDenied, InvalidId, InvalidArgument, NotFound) as ex:
            gutils.handle_exceptions(ex)


class RepositorySearch(ProducerAPIViews):
    """
    Search interface for a specific (domain) repository.
    api/v1/repository/repositories/<repository_id>/search/

    GET
    ?selected_facets=course_exact:<id>&selected_facets=resource_type_exact:problem&....
    """
    def _get_all_items_by_repo(self, repo):
        if isinstance(repo, dict):
            repo = self.rm.get_repository(gutils.clean_id(repo['id']))
        bank = self.am.get_bank(repo.ident)
        bank.use_federated_bank_view()

        repo.use_sequestered_composition_view()

        if self.facet_resource_types is None:
            if self.query_params is None or self.query_params == ['']:
                all_assets = repo.get_assets()
                all_compositions = repo.get_compositions()
                all_items = bank.get_items()
            else:
                asset_querier = repo.get_asset_query()
                composition_querier = repo.get_composition_query()
                item_querier = bank.get_item_query()

                for term in self.query_params:
                    asset_querier.match_keyword(term, gutils.WORDIGNORECASE_STRING_MATCH_TYPE, True)
                    composition_querier.match_keyword(term, gutils.WORDIGNORECASE_STRING_MATCH_TYPE, True)
                    item_querier.match_keyword(term, gutils.WORDIGNORECASE_STRING_MATCH_TYPE, True)

                all_assets = repo.get_assets_by_query(asset_querier)
                all_compositions = repo.get_compositions_by_query(composition_querier)
                all_items = bank.get_items_by_query(item_querier)
        else:
            all_assets = []
            all_compositions = []
            all_items = []
            for resource_type in self.facet_resource_types:
                if resource_type in EDX_COMPOSITION_GENUS_TYPES_STR:
                    genus_type = Type(resource_type)
                    composition_querier = repo.get_composition_query()
                    composition_querier.match_genus_type(genus_type, True)
                    for term in self.query_params:
                        composition_querier.match_keyword(term,
                                                          gutils.WORDIGNORECASE_STRING_MATCH_TYPE,
                                                          True)

                    all_compositions += [c for c in repo.get_compositions_by_query(composition_querier)]
                elif resource_type == 'edx-assessment-item%3Aproblem%40EDX.ORG':
                    item_querier = bank.get_item_query()
                    for term in self.query_params:
                        item_querier.match_keyword(term,
                                                   gutils.WORDIGNORECASE_STRING_MATCH_TYPE,
                                                   True)

                    all_items += [c for c in bank.get_items_by_query(item_querier)]
                else:
                    genus_type = Type(resource_type)
                    asset_querier = repo.get_asset_query()
                    asset_querier.match_asset_content_genus_type(genus_type, True)
                    for term in self.query_params:
                        asset_querier.match_keyword(term,
                                                    gutils.WORDIGNORECASE_STRING_MATCH_TYPE,
                                                    True)

                    all_assets += [a for a in repo.get_assets_by_query(asset_querier)]

        return all_assets, all_compositions, all_items

    def _get_run_map(self, repository_id):
        repo_nodes = self.rm.get_repository_nodes(repository_id=gutils.clean_id(repository_id),
                                                  ancestor_levels=0,
                                                  descendant_levels=2,
                                                  include_siblings=False)
        repo_nodes = repo_nodes.get_object_node_map()

        runs = [(r['id'], '{0}, {1}'.format(course['displayName']['text'],
                                            r['displayName']['text']))
                for course in repo_nodes['childNodes']
                for r in course['childNodes']]

        run_map = {}
        for run in runs:
            run_map[run[0]] = run[1]

        return run_map

    def get(self, request, repository_id, format=None):
        try:
            self.facet_resource_types = get_facets_values(self.data, 'resource_type_exact')
            self.facet_course_runs = get_facets_values(self.data, 'course_exact')
            self.query_params = get_query_values(self.data.get('q', None))
            self.cursor_limits = get_page_and_limits(self.data)
            object_list = []

            run_map = self._get_run_map(repository_id)

            if self.facet_course_runs is None:
                domain_repo = self.rm.get_repository(gutils.clean_id(repository_id))
                domain_repo.use_federated_repository_view()

                all_assets, all_compositions, all_items = self._get_all_items_by_repo(domain_repo)
                non_enclosed_assets = [a for a in all_assets
                                       if a.enclosed_object is None and
                                       a.get_asset_contents().available() > 0]

                object_list += [a.object_map for a in non_enclosed_assets]
                object_list += [c.object_map for c in all_compositions]
                object_list += [i.object_map for i in all_items]
            else:
                for repo_id in self.facet_course_runs:
                    run_repo = self.rm.get_repository(gutils.clean_id(repo_id))
                    run_assets, run_compositions, run_items = self._get_all_items_by_repo(run_repo)
                    non_enclosed_assets = [a for a in run_assets
                                           if a.enclosed_object is None and
                                           a.get_asset_contents().available() > 0]
                    object_list += [a.object_map for a in non_enclosed_assets]
                    object_list += [c.object_map for c in run_compositions]
                    object_list += [i.object_map for i in run_items]

            object_list = sorted(object_list, key=lambda k: k['id'])
            return_data = {
                'objects': object_list,
                'runMap': run_map
            }
            return Response(return_data)
        except (PermissionDenied, InvalidId, NotFound) as ex:
            gutils.handle_exceptions(ex)

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