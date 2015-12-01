import os
import stat

from bson.errors import InvalidId

from rest_framework.response import Response
from rest_framework import exceptions

from django.conf import settings
from django.core.files.storage import default_storage
from django.http import HttpResponse

from dlkit.abstract_osid.assessment.objects import Item
from dlkit.abstract_osid.repository.objects import Asset
from dlkit_django.errors import PermissionDenied, InvalidArgument, IllegalState,\
    NotFound, NoAccess, AlreadyExists
from dlkit_django.primordium import Type
from dlkit.mongo.records.types import EDX_COMPOSITION_GENUS_TYPES,\
    COMPOSITION_RECORD_TYPES, REPOSITORY_GENUS_TYPES, OSID_OBJECT_RECORD_TYPES,\
    EDX_ASSET_CONTENTS_GENUS_TYPES, EDX_ASSESSMENT_ITEM_GENUS_TYPES, REPOSITORY_RECORD_TYPES

from dysonx.dysonx import get_or_create_user_repo, _get_genus_type,\
    _get_asset_content_genus_type

from utilities import general as gutils
from utilities import repository as rutils
from producer.tasks import import_file
from producer.views import ProducerAPIViews

LORE_REPO_RECORD_TYPE = Type(**REPOSITORY_RECORD_TYPES['lore-repo'])
COURSE_REPO_RECORD_TYPE = Type(**REPOSITORY_RECORD_TYPES['course-repo'])
COURSE_RUN_REPO_RECORD_TYPE = Type(**REPOSITORY_RECORD_TYPES['run-repo'])

DOMAIN_REPO_GENUS = Type(**REPOSITORY_GENUS_TYPES['domain-repo'])
COURSE_REPO_GENUS = Type(**REPOSITORY_GENUS_TYPES['course-repo'])
COURSE_RUN_REPO_GENUS = Type(**REPOSITORY_GENUS_TYPES['course-run-repo'])
USER_REPO_GENUS = Type(**REPOSITORY_GENUS_TYPES['user-repo'])
COURSE_NODE_GENUS_TYPE = Type(**EDX_COMPOSITION_GENUS_TYPES['course'])

EDX_COMPOSITION_RECORD_TYPE = Type(**COMPOSITION_RECORD_TYPES['edx-composition'])
USER_OFFERING_COMPOSITION_RECORD_TYPE = Type(**COMPOSITION_RECORD_TYPES['edx-course-run'])
EDX_COMPOSITION_GENUS_TYPES_STR = [str(Type(**genus_type))
                                   for k, genus_type in EDX_COMPOSITION_GENUS_TYPES.iteritems()]
EDX_COMPOSITION_TYPES = EDX_COMPOSITION_GENUS_TYPES.keys()
EDX_COMPOSITION_GENUS_TYPES_FOR_FACETS = [str(Type(**genus_type))
    for k, genus_type in EDX_COMPOSITION_GENUS_TYPES.iteritems()
    if k in ['chapter', 'sequential', 'split_test', 'vertical']]
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
    end_index = (page * limit)  # because python list slice ends at this [0:10] gets indices 0...9
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
    def _get_map_with_children(self, obj, renderable=False, repository=None):
        obj_map = obj.object_map
        obj_map['children'] = []
        for child_tuple in obj.all_children(repository=repository):
            child = child_tuple[0]
            can_edit = child_tuple[1]
            if isinstance(child, Item):
                child_map = child.object_map
                if renderable:
                    child_map['texts']['edxml'] = child.get_edxml_with_aws_urls()
            elif isinstance(child, Asset):
                if renderable:
                    asset_repo = self.rm.get_repository(gutils.clean_id(child.object_map['repositoryId']))
                    child_map = rutils.update_asset_urls(asset_repo,
                                                         child,
                                                         {'renderable_edxml': True})
                else:
                    child_map = child.object_map
            else:
                child_map = self._get_map_with_children(child,
                                                        renderable=renderable,
                                                        repository=repository)
            child_map.update({
                'canEdit': can_edit
            })
            obj_map['children'].append(child_map)
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
                                                   ['displayName', 'description', 'files',
                                                    'learningObjectiveIds'])

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

            if 'learningObjectiveIds' in self.data:
                form = repository.get_asset_form_for_update(gutils.clean_id(asset_id))
                form.set_learning_objective_ids([gutils.clean_id(i)
                                                 for i in self.data['learningObjectiveIds']])
                updated_asset = repository.update_asset(form)

            data = updated_asset.object_map
            return gutils.UpdatedResponse(data)
        except (PermissionDenied, InvalidArgument, NoAccess, InvalidId, KeyError) as ex:
            gutils.handle_exceptions(ex)


class AssetDownload(ProducerAPIViews):
    """
    Download a single asset.
    api/v1/repository/assets/<asset_id>/download/

    GET
    """
    def get(self, request, asset_id, format=None):
        try:
            repository = rutils.get_object_repository(self.rm,
                                                      asset_id,
                                                      'asset')
            asset = repository.get_asset(gutils.clean_id(asset_id))

            filename, olx = asset.export_standalone_olx()

            response = HttpResponse(content_type="application/tar")
            response['Content-Disposition'] = 'attachment; filename=%s' % filename
            olx.seek(0, os.SEEK_END)
            response.write(olx.getvalue())
            olx.close()

            return response
        except (PermissionDenied, InvalidArgument, NotFound) as ex:
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


class AssetObjectives(ProducerAPIViews):
    """
    Get asset learning objectives
    api/v1/repository/assets/<asset_id>/objectives/

    GET

    Note that for RESTful calls, you need to set the request header
    'content-type' to 'application/json'

    Example (note the use of double quotes!!):
       {"name" : "an updated item"}
    """
    def get(self, request, asset_id, format=None):
        try:
            repo = rutils.get_object_repository(self.rm,
                                                asset_id,
                                                object_type='asset',
                                                repository_id=None)

            asset = repo.get_asset(gutils.clean_id(asset_id))

            ols = self.lm._instantiate_session(method_name='get_objective_lookup_session',
                                               proxy=self.lm._proxy)
            objectives = []
            # TODO: may need to manually add the field into MongoDB?
            # instead of this hack?
            try:
                for obj_id in asset.get_learning_objective_ids():
                    objectives.append(ols.get_objective(obj_id))
            except KeyError:  # this means the asset was not initialized with learningObjectId in its map
                pass

            data = gutils.extract_items(request, objectives)
            return Response(data)
        except (PermissionDenied, NotFound) as ex:
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


class CompositionChildrenList(ProducerAPIViews):
    """
    Get a composition's children...if the child is sequestered, get its assets
    api/v1/repository/compositions/<composition_id>/children

    GET
    """
    def get(self, request, composition_id, repository_id=None, format=None):
        try:
            if repository_id is None:
                repository = get_or_create_user_repo(request.user.username)
            else:
                repository = self.rm.get_repository(gutils.clean_id(repository_id))

            repository.use_unsequestered_composition_view()

            try:
                composition = repository.get_composition(gutils.clean_id(composition_id))
            except NotFound:
                composition_repository = rutils.get_object_repository(self.rm,
                                                                      composition_id,
                                                                      'composition')
                composition_repository.use_unsequestered_composition_view()
                composition = composition_repository.get_composition(gutils.clean_id(composition_id))

            children = gutils.extract_items(request,
                                            composition.all_children(repository=repository))

            return Response(children)
        except (PermissionDenied, InvalidArgument, NotFound, InvalidId) as ex:
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
            user_repository = get_or_create_user_repo(request.user.username)
            user_repository.use_federated_repository_view()
            user_repository.use_unsequestered_composition_view()

            composition = user_repository.get_composition(gutils.clean_id(composition_id))
            # if not in a sub-repo, the above line should throw a NotFound exception

            if 'withChildren' in self.data:
                # remove children compositions too
                for child_id in composition.get_child_ids():
                    # use this instead of get_children() because sequestered
                    # compositions don't show up with get_children()
                    try:
                        child = user_repository.get_composition(child_id)

                        # if the child is found in a sub-repo
                        sub_repo = rutils.get_object_repository(self.rm,
                                                                child_id,
                                                                'composition')
                        sub_repo.delete_composition(child_id)
                    except NotFound:
                        pass  # not unlocked / cloned into the target repo

            sub_repo = rutils.get_object_repository(self.rm,
                                                    composition_id,
                                                    'composition')
            sub_repo.delete_composition(gutils.clean_id(composition_id))

            # have to remove references to it in other repo / compositions
            # that may not have cloned it locally
            rutils.clean_up_dangling_references(self.rm, composition_id)

            return gutils.DeletedResponse()
        except (PermissionDenied, IllegalState, InvalidId, NotFound, KeyError) as ex:
            gutils.handle_exceptions(ex)

    def get(self, request, composition_id, format=None):
        try:
            repository = rutils.get_object_repository(self.rm,
                                                      composition_id,
                                                      'composition')
            repository.use_unsequestered_composition_view()
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
                                                    'draft', 'assetIds', 'genusTypeId',
                                                    'learningObjectiveIds'])

            repository = rutils.get_object_repository(self.rm,
                                                      composition_id,
                                                      'composition')
            repository.use_unsequestered_composition_view()

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

            if 'learningObjectiveIds' in self.data:
                try:
                    form.set_learning_objective_ids([gutils.clean_id(i)
                                                     for i in self.data['learningObjectiveIds']])
                except (AttributeError, IllegalState):
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


class CompositionDownload(ProducerAPIViews):
    """
    Download a user course RUN.
    api/v1/repository/compositions/<composition_id>/download/

    GET
    """
    def get(self, request, composition_id, format=None):
        try:
            repository = rutils.get_object_repository(self.rm,
                                                      composition_id,
                                                      'composition')
            repository.use_unsequestered_composition_view()
            composition = repository.get_composition(gutils.clean_id(composition_id))

            if str(composition.genus_type) != str(Type(**EDX_COMPOSITION_GENUS_TYPES['offering'])):
                # raise InvalidArgument('You can only download run repositories.')
                filename, olx = composition.export_standalone_olx()
            else:
                filename, olx = composition.export_run_olx()

            response = HttpResponse(content_type="application/tar")
            response['Content-Disposition'] = 'attachment; filename=%s' % filename
            olx.seek(0, os.SEEK_END)
            response.write(olx.getvalue())
            olx.close()

            return response
        except (PermissionDenied, InvalidArgument, NotFound) as ex:
            gutils.handle_exceptions(ex)


class CompositionObjectives(ProducerAPIViews):
    """
    Get a composition's learning objectives
    api/v1/repository/compositions/<composition_id>/objectives/

    GET

    Note that for RESTful calls, you need to set the request header
    'content-type' to 'application/json'

    Example (note the use of double quotes!!):
       {"name" : "an updated item"}
    """
    def get(self, request, composition_id, format=None):
        try:
            repo = rutils.get_object_repository(self.rm,
                                                composition_id,
                                                object_type='composition',
                                                repository_id=None)

            composition = repo.get_composition(gutils.clean_id(composition_id))

            ols = self.lm._instantiate_session(method_name='get_objective_lookup_session',
                                               proxy=self.lm._proxy)
            objectives = []
            try:
                for obj_id in composition.get_learning_objective_ids():
                    objectives.append(ols.get_objective(obj_id))
            except (AttributeError, IllegalState, KeyError):
                pass

            data = gutils.extract_items(request, objectives)
            return Response(data)
        except (PermissionDenied, NotFound) as ex:
            gutils.handle_exceptions(ex)


class CompositionOfferingsList(ProducerAPIViews):
    """
    Get a course node's offerings
    api/v1/repository/compositions/<composition_id>/offerings

    GET
    """
    def get(self, request, composition_id, format=None):
        try:
            repository = rutils.get_object_repository(self.rm,
                                                      composition_id,
                                                      'composition')
            repository.use_unsequestered_composition_view()
            composition = repository.get_composition(gutils.clean_id(composition_id))

            if composition.genus_type != COURSE_NODE_GENUS_TYPE:
                raise InvalidArgument('Can only get offerings on course nodes.')

            offerings = []
            offering_ids = composition.get_child_ids()
            # because they are sequestered
            for offering_id in offering_ids:
                offerings.append(repository.get_composition(gutils.clean_id(offering_id)))

            offerings = gutils.extract_items(request, offerings)

            return Response(offerings)
        except (PermissionDenied, InvalidArgument, NotFound, InvalidId) as ex:
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
                if repository_id is not None:
                    compositions.append(self._get_map_with_children(course_node,
                                                                    repository=composition_lookup_session))
                else:
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
                                if genus_val == 'course':
                                    composition_query_session.use_unsequestered_composition_view()
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
                edx_type = self.data['genusTypeId']  # assumes type is full genusType string

                if 'offering' in edx_type:
                    form = repository.get_composition_form_for_create([EDX_COMPOSITION_RECORD_TYPE,
                                                                       USER_OFFERING_COMPOSITION_RECORD_TYPE])
                else:
                    form = repository.get_composition_form_for_create([EDX_COMPOSITION_RECORD_TYPE])
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

                    if 'course' in edx_type or 'offering' in edx_type:
                        form.set_sequestered(True)

                    if 'course' in edx_type:
                        form.set_org('MITx')
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
            if 'parentId' not in self.data and repository.genus_type != USER_REPO_GENUS:
                course_node = rutils.get_course_node(repository)
                rutils.append_child_composition(repository, course_node, composition)
            elif 'parentId' in self.data:
                repository.use_unsequestered_composition_view()
                parent_composition = repository.get_composition(gutils.clean_id(self.data['parentId']))
                rutils.append_child_composition(repository, parent_composition, composition)
            else:
                # do nothing (is user repo, just let the composition be created)
                pass

            # Should be assigning the composition to THIS repository as well as
            # appending it as a childId.
            # TODO: we may not want to do this for authz purposes...
            # the unlocking / editing issue as discussed with Jeff
            repository.use_unsequestered_composition_view()
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
            if 'domains' in self.data:
                domain_repo_genus = Type(**REPOSITORY_GENUS_TYPES['domain-repo'])
                querier = self.rm.get_repository_query()
                querier.match_genus_type(domain_repo_genus, True)
                repositories = list(self.rm.get_repositories_by_query(querier))

                # now add the user's own domain
                repositories.append(get_or_create_user_repo(request.user.username))
            else:
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
                    gutils.verify_keys_present(self.data, ['displayName', 'description', 'genusTypeId'])
                    if self.data['genusTypeId'] == str(COURSE_RUN_REPO_GENUS):
                        # is a run
                        form = self.rm.get_repository_form_for_create([LORE_REPO_RECORD_TYPE,
                                                                       COURSE_RUN_REPO_RECORD_TYPE])
                        gutils.verify_keys_present(self.data, ['parentId'])
                    else:
                        # is a course
                        form = self.rm.get_repository_form_for_create([LORE_REPO_RECORD_TYPE,
                                                                       COURSE_REPO_RECORD_TYPE])
                        form.set_org('MITx')
                    finalize_method = self.rm.create_repository
                else:
                    repository = self.rm.get_repository(gutils.clean_id(self.data['bankId']))
                    form = self.rm.get_repository_form_for_update(repository.ident)
                    finalize_method = self.rm.update_repository

                form = gutils.set_form_basics(form, self.data)
                repo = finalize_method(form)

                if 'genusTypeId' in self.data:
                    if self.data['genusTypeId'] == str(COURSE_RUN_REPO_GENUS):
                        self.rm.add_child_repository(gutils.clean_id(self.data['parentId']),
                                                     repo.ident)
                    elif self.data['genusTypeId'] == str(COURSE_REPO_GENUS):
                        self.rm.add_child_repository(get_or_create_user_repo(request.user.username).ident,
                                                     repo.ident)

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


class QueryHelpersMixin(object):
    def _get_current_los(self, repo):
        bank = self.am.get_bank(repo.ident)
        bank.use_federated_bank_view()
        repo.use_federated_repository_view()
        repo.use_unsequestered_composition_view()

        asset_querier = repo.get_asset_query()
        composition_querier = repo.get_composition_query()
        item_querier = bank.get_item_query()

        asset_querier.match_any_learning_objective(True)
        composition_querier.match_any_learning_objective(True)
        item_querier.match_any_learning_objective(True)

        assets = repo.get_assets_by_query(asset_querier)
        compositions = repo.get_compositions_by_query(composition_querier)
        items = bank.get_items_by_query(item_querier)

        los = [str(lo) for a in assets for lo in a.get_learning_objective_ids()]
        los += [str(lo) for c in compositions for lo in c.get_learning_objective_ids()]
        los += [str(lo) for i in items for lo in i.get_learning_objective_ids()]

        los = list(set(los))

        ols = self.lm._instantiate_session(method_name='get_objective_lookup_session',
                                           proxy=self.lm._proxy)

        results = ols.get_objectives_by_ids([gutils.clean_id(i) for i in los])

        return results

    def _construct_count_queries(self, repo, composition_id=None, with_los=False, with_types=False):
        bank = self.am.get_bank(repo.ident)
        bank.use_federated_bank_view()

        asset_querier = repo.get_asset_query()
        composition_querier = repo.get_composition_query()
        item_querier = bank.get_item_query()

        if self.query_params is not None and self.query_params != ['']:
            for term in self.query_params:
                asset_querier.match_keyword(term, gutils.WORDIGNORECASE_STRING_MATCH_TYPE, True)
                composition_querier.match_keyword(term, gutils.WORDIGNORECASE_STRING_MATCH_TYPE, True)
                item_querier.match_keyword(term, gutils.WORDIGNORECASE_STRING_MATCH_TYPE, True)

        # match learning objectives
        if with_los:
            if self.facet_learning_objectives is not None and self.facet_learning_objectives != ['']:
                for objective_id in self.facet_learning_objectives:
                    asset_querier.match_learning_objective(objective_id, True)
                    composition_querier.match_learning_objective(objective_id, True)
                    item_querier.match_learning_objective_id(objective_id, True)

        # match the selected genus types:
        if with_types:
            if self.facet_resource_types is not None:
                for resource_type in self.facet_resource_types:
                    resource_genus_type = Type(resource_type)
                    if resource_type in EDX_COMPOSITION_GENUS_TYPES_STR:
                        composition_querier.match_genus_type(resource_genus_type, True)
                    elif resource_type == 'edx-assessment-item%3Aproblem%40EDX.ORG':
                        pass  # already have an item query from above
                    else:
                        asset_querier.match_asset_content_genus_type(resource_genus_type, True)

        if composition_id is not None:
            # match the composition descendants
            asset_querier.match_composition_descendants(composition_id, repo.ident, True)
            composition_querier.match_composition_descendants(composition_id, repo.ident, True)
            item_querier.match_composition_descendants(composition_id, repo.ident, True)

        return asset_querier, composition_querier, item_querier

    def _count_by_learning_objectives(self, run_identifier, lo_counts, domain_repo):
        if isinstance(run_identifier, basestring):
            run_identifier = gutils.clean_id(run_identifier)
        if 'repository.Repository' in str(run_identifier):
            repo = self.rm.get_repository(gutils.clean_id(run_identifier))
            composition_id = None
        else:
            repo = domain_repo
            composition_id = run_identifier

        bank = self.am.get_bank(repo.ident)
        bank.use_federated_bank_view()

        asset_querier, composition_querier, item_querier = self._construct_count_queries(repo,
                                                                                         composition_id,
                                                                                         with_types=True)

        self._count_los(lo_counts,
                        self.current_los,
                        asset_querier,
                        repo,
                        'clear_match_learning_objective',
                        'match_learning_objective',
                        'get_assets_by_query')

        self._count_los(lo_counts,
                        self.current_los,
                        composition_querier,
                        repo,
                        'clear_match_learning_objective',
                        'match_learning_objective',
                        'get_compositions_by_query')

        self._count_los(lo_counts,
                        self.current_los,
                        item_querier,
                        bank,
                        'clear_learning_objective_id_terms',
                        'match_learning_objective_id',
                        'get_items_by_query')

    def _count_los(self, counts, iterator, querier, catalog, clear_method, match_method, get_method):
        for objective in iterator:
            objective_id = objective.ident
            objective_name = objective.display_name.text
            if self.facet_learning_objectives is not None and self.facet_learning_objectives != ['']:
                if str(objective_id) in self.facet_learning_objectives:
                    getattr(querier, clear_method)()
                    getattr(querier, match_method)(objective_id, True)
                    if str(objective_id) not in counts:
                        counts.update({
                            str(objective_id): [getattr(catalog, get_method)(querier).available(), str(objective_name)]
                        })
                    else:
                        counts[str(objective_id)][0] += getattr(catalog, get_method)(querier).available()
                else:
                    if str(objective_id) not in counts:
                        counts[str(objective_id)] = [0, str(objective_name)]
            else:
                getattr(querier, clear_method)()
                getattr(querier, match_method)(objective_id, True)
                if str(objective_id) not in counts:
                    counts.update({
                        str(objective_id): [getattr(catalog, get_method)(querier).available(), str(objective_name)]
                    })
                else:
                    counts[str(objective_id)][0] += getattr(catalog, get_method)(querier).available()

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

    def _count_objects(self, run_identifier, asset_counts, domain_repo):
        if isinstance(run_identifier, basestring):
            run_identifier = gutils.clean_id(run_identifier)
        if 'repository.Repository' in str(run_identifier):
            repo = self.rm.get_repository(gutils.clean_id(run_identifier))
            composition_id = None
        else:
            repo = domain_repo
            composition_id = run_identifier

        bank = self.am.get_bank(repo.ident)
        bank.use_federated_bank_view()

        asset_genus_types = EDX_ASSET_CONTENT_GENUS_TYPES_FOR_FACETS
        composition_genus_types = EDX_COMPOSITION_GENUS_TYPES_FOR_FACETS
        item_genus_types = EDX_ASSESSMENT_GENUS_TYPES_FOR_FACETS

        asset_querier, composition_querier, item_querier = self._construct_count_queries(repo,
                                                                                         composition_id,
                                                                                         with_los=True)

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

    def _get_all_items(self, run_id, repository=None):
        if isinstance(run_id, basestring):
            run_id = gutils.clean_id(run_id)
        if 'repository.Repository' in str(run_id):
            repo = self.rm.get_repository(run_id)
            assets, compositions, items = self._get_all_items_by_repo(repo)
        else:
            # is a composition run
            repository.use_unsequestered_composition_view()
            composition = repository.get_composition(run_id)
            assets, compositions, items = self._get_all_items_by_composition(composition, repository)
        return assets, compositions, items

    def _get_all_items_by_composition(self, composition, repo):
        # these items / assets / compositions must be children
        # of the descendants of the passed-in composition
        # So add in a query filter for them all
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

        # match the composition descendants
        if asset_querier is not None:
            asset_querier.match_composition_descendants(composition.ident, repo.ident, True)
        if composition_querier is not None:
            composition_querier.match_composition_descendants(composition.ident, repo.ident, True)
        if item_querier is not None:
            item_querier.match_composition_descendants(composition.ident, repo.ident, True)

        # match query terms
        if self.query_params is not None and self.query_params != ['']:
            for term in self.query_params:
                if asset_querier is not None:
                    asset_querier.match_keyword(term, gutils.WORDIGNORECASE_STRING_MATCH_TYPE, True)
                if composition_querier is not None:
                    composition_querier.match_keyword(term, gutils.WORDIGNORECASE_STRING_MATCH_TYPE, True)
                if item_querier is not None:
                    item_querier.match_keyword(term, gutils.WORDIGNORECASE_STRING_MATCH_TYPE, True)

        # match learning objectives
        if self.facet_learning_objectives is not None and self.facet_learning_objectives != ['']:
            for objective_id in self.facet_learning_objectives:
                if asset_querier is not None:
                    asset_querier.match_learning_objective(objective_id, True)
                if composition_querier is not None:
                    composition_querier.match_learning_objective(objective_id, True)
                if item_querier is not None:
                    item_querier.match_learning_objective_id(objective_id, True)

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

        # match learning objectives
        if self.facet_learning_objectives is not None and self.facet_learning_objectives != ['']:
            for objective_id in self.facet_learning_objectives:
                if asset_querier is not None:
                    asset_querier.match_learning_objective(objective_id, True)
                if composition_querier is not None:
                    composition_querier.match_learning_objective(objective_id, True)
                if item_querier is not None:
                    item_querier.match_learning_objective_id(objective_id, True)

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

    def _get_run_map(self, repository):
        # if repository.genus_type == DOMAIN_REPO_GENUS:
        repo_nodes = self.rm.get_repository_nodes(repository_id=gutils.clean_id(repository.ident),
                                                  ancestor_levels=0,
                                                  descendant_levels=2,
                                                  include_siblings=False)
        repo_nodes = repo_nodes.get_object_node_map()
        runs = [(r['id'], '{0}, {1}'.format(course['displayName']['text'],
                                        r['displayName']['text']))
            for course in repo_nodes['childNodes']
            for r in course['childNodes']]
        # else:
        #     repository.use_unsequestered_composition_view()
        #     querier = repository.get_composition_query()
        #     querier.match_genus_type(Type(**EDX_COMPOSITION_GENUS_TYPES['course']), True)
        #     course_compositions = repository.get_compositions_by_query(querier)
        #     runs = []
        #     for course in course_compositions:
        #         run_composition_ids = course.get_child_ids()
        #         for run_id in run_composition_ids:
        #             run_composition = repository.get_composition(run_id)
        #             runs.append((str(run_composition.ident), '{0}, {1}'.format(course.display_name.text,
        #                                                                        run_composition.display_name.text)))

        run_map = {}
        for run in runs:
            run_map[run[0]] = run[1]

        return run_map


class RepositoryQueryPlansAvailable(ProducerAPIViews, QueryHelpersMixin):
    """
    Get set of queryable options plus their object counts
    api/v1/repository/repositories/<repository_id>/queryplans/

    GET
    """
    def get(self, request, repository_id, format=None):
        try:
            self.facet_resource_types = get_facets_values(self.data, 'resource_type_exact')
            self.facet_course_runs = get_facets_values(self.data, 'course_exact')
            self.facet_learning_objectives = get_facets_values(self.data, 'learning_objective_exact')
            self.query_params = get_query_values(self.data.get('q', None))

            facets = {
                'course': [],
                'learning_objective': [],
                'resource_type': []
            }

            course_run_counts = {}
            learning_objective_counts = {}
            asset_counts = {}

            domain_repo = self.rm.get_repository(gutils.clean_id(repository_id))

            if domain_repo.genus_type not in [DOMAIN_REPO_GENUS, USER_REPO_GENUS]:
                raise InvalidArgument('You can only get query plans for domains or user repos.')

            self.current_los = list(self._get_current_los(domain_repo))

            run_map = self._get_run_map(domain_repo)

            # first for each repository, get count of its total objects that
            # meet the keyword filter requirement and other facet requirements
            for run_identifier, run_name in run_map.iteritems():
                course_run_counts[run_name] = [0, run_identifier]
                if self.facet_course_runs is None:
                    # do all courses
                    run_id = gutils.clean_id(run_identifier)
                    assets, compositions, items = self._get_all_items(run_id, domain_repo)

                    for obj in [assets, compositions, items]:
                        if obj is not None:
                            course_run_counts[run_name][0] += obj.available()

                    self._count_objects(run_id,
                                        asset_counts,
                                        domain_repo)

                    if settings.ENABLE_OBJECTIVE_FACETS:
                        self._count_by_learning_objectives(run_id,
                                                           learning_objective_counts,
                                                           domain_repo)
                else:
                    # only do courses that have been selected
                    if any(run_identifier in course for course in self.facet_course_runs):
                        run_id = gutils.clean_id(run_identifier)
                        assets, compositions, items = self._get_all_items(run_id, domain_repo)

                        for obj in [assets, compositions, items]:
                            if obj is not None:
                                course_run_counts[run_name][0] += obj.available()

                        self._count_objects(run_id,
                                            asset_counts,
                                            domain_repo)

                        if settings.ENABLE_OBJECTIVE_FACETS:
                            self._count_by_learning_objectives(run_id,
                                                               learning_objective_counts,
                                                               domain_repo)

            count_cases = [(asset_counts, 'resource_type', False),
                           (course_run_counts, 'course', False),
                           (learning_objective_counts, 'learning_objective', True)]
            for case in count_cases:
                _counts = []
                for k, v in case[0].iteritems():
                    if isinstance(v, tuple) or isinstance(v, list):
                        if case[2]:  # flip the order of v[1] and k
                            _counts.append((v[1], v[0], k))
                        else:
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


class RepositorySearch(ProducerAPIViews, QueryHelpersMixin):
    """
    Search interface for a specific (domain) repository.
    api/v1/repository/repositories/<repository_id>/search/

    GET
    ?selected_facets=course_exact:<id>&selected_facets=resource_type_exact:problem&....
    """
    def get(self, request, repository_id, format=None):
        try:
            self.facet_resource_types = get_facets_values(self.data, 'resource_type_exact')
            self.facet_course_runs = get_facets_values(self.data, 'course_exact')
            self.facet_learning_objectives = get_facets_values(self.data, 'learning_objective_exact')

            self.query_params = get_query_values(self.data.get('q', None))
            self.cursor_limits = get_page_and_limits(self.data)
            object_list = []

            domain_repo = self.rm.get_repository(gutils.clean_id(repository_id))

            if domain_repo.genus_type not in [DOMAIN_REPO_GENUS, USER_REPO_GENUS]:
                raise InvalidArgument('You can only get query results for domains or user repos.')

            asset_lists = []
            composition_lists = []
            item_lists = []

            run_map = self._get_run_map(domain_repo)
            # first for each repository, get OsidLists of total objects that
            # meet the keyword filter requirement and other facet requirements
            for run_identifier, run_name in run_map.iteritems():
                if self.facet_course_runs is None:
                    # do all courses
                    run_id = gutils.clean_id(run_identifier)
                    assets, compositions, items = self._get_all_items(run_id, domain_repo)

                    for obj in [(assets, asset_lists),
                                (compositions, composition_lists),
                                (items, item_lists)]:
                        if obj[0] is not None:
                            if obj[0] == assets:
                                non_enclosed_assets = [a for a in assets if
                                                       a.get_asset_contents().available() > 0]
                                list_to_add = non_enclosed_assets
                                number = len(list_to_add)
                            else:
                                list_to_add = obj[0]
                                number = list_to_add.available()
                            obj[1].append((list_to_add, number))
                else:
                    # only do courses that have been selected
                    if any(run_identifier in course for course in self.facet_course_runs):
                        run_id = gutils.clean_id(run_identifier)
                        assets, compositions, items = self._get_all_items(run_id, domain_repo)

                        for obj in [(assets, asset_lists),
                                    (compositions, composition_lists),
                                    (items, item_lists)]:
                            if obj[0] is not None:
                                if obj[0] == assets:
                                    non_enclosed_assets = [a for a in assets if
                                                           a.get_asset_contents().available() > 0]
                                    list_to_add = non_enclosed_assets
                                    number = len(list_to_add)
                                else:
                                    list_to_add = obj[0]
                                    number = list_to_add.available()
                                obj[1].append((list_to_add, number))

            # slice / paginate from assets first...
            lower_index = self.cursor_limits[0]
            upper_index = self.cursor_limits[1]

            counter = 0
            list_index = 0
            compiled_lists = asset_lists + composition_lists + item_lists
            if len(compiled_lists) > 0:
                while counter < upper_index:
                    active_list = compiled_lists[list_index][0]
                    active_list_len = compiled_lists[list_index][1]

                    if (counter + active_list_len) <= lower_index:
                        # the page we need is not part of this list.
                        # skip it and move on
                        counter += active_list_len
                    elif (counter <= lower_index and
                            (counter + active_list_len) >= upper_index):
                        # we only need this list -- yay
                        start_index = lower_index - counter
                        num_skip = start_index
                        end_index = upper_index - counter
                        if num_skip > 0:
                            try:
                                active_list.skip(num_skip)
                            except AttributeError:
                                del active_list[0:num_skip]
                            counter += num_skip
                        num_added = 0
                        for obj in active_list:
                            object_list.append(obj.object_map)
                            start_index += 1
                            num_added += 1
                            if start_index == end_index:
                                break
                        counter += num_added
                    elif (counter <= lower_index and
                              (counter + active_list_len) < upper_index):
                        # need this list + at least one more
                        # so append the items from this list, and keep
                        # going through the loop
                        start_index = lower_index - counter
                        num_skip = start_index
                        if num_skip > 0:
                            try:
                                active_list.skip(num_skip)
                            except AttributeError:
                                del active_list[0:num_skip]
                            counter += num_skip
                        num_added = 0
                        for obj in active_list:
                            object_list.append(obj.object_map)
                            num_added += 1
                        counter += num_added
                    else:
                        # counter > lower_index...so we just need to check
                        # the upper_index to see what we need from this list
                        if (counter + active_list_len) < upper_index:
                            # take this entire list and go to the next one
                            num_added = 0
                            for obj in active_list:
                                object_list.append(obj.object_map)
                                num_added += 1
                            counter += num_added
                        else:
                            # take only a portion of this list
                            end_index = upper_index - counter
                            num_added = 0
                            for obj in active_list:
                                object_list.append(obj.object_map)
                                num_added += 1
                                if num_added == end_index:
                                    break
                            counter += num_added

                    list_index += 1
                    if list_index == len(compiled_lists):
                        # no results...break
                        break

            return_data = {
                'objects': object_list,
                'runMap': run_map
            }
            return Response(return_data)
        except (PermissionDenied, InvalidId, NotFound) as ex:
            gutils.handle_exceptions(ex)


class UnlockComposition(ProducerAPIViews):
    """
    Unlock a composition and assign it to the specified parent
    api/v1/repository/compositions/<composition_id>/unlock/

    POST
    """
    def post(self, request, composition_id, repository_id=None, format=None):
        try:
            repository = rutils.get_object_repository(self.rm,
                                                      composition_id,
                                                      'composition')
            repository.use_unsequestered_composition_view()

            composition = repository.get_composition(gutils.clean_id(composition_id))

            if repository_id is not None:
                target_repository = self.rm.get_repository(gutils.clean_id(repository_id))
            else:
                target_repository = get_or_create_user_repo(request.user.username)

            if 'parentId' in self.data and self.data['parentId'] != '':
                target_repository.use_unsequestered_composition_view()
                parent_composition = target_repository.get_composition(gutils.clean_id(self.data['parentId']))
            elif str(target_repository.genus_type) == str(COURSE_RUN_REPO_GENUS):
                parent_composition = rutils.get_course_node(target_repository)
            else:
                parent_composition = None
            clone = composition.clone_to(target_repo=target_repository,
                                         target_parent=parent_composition)

            for child_id in clone.get_child_ids():
                child = repository.get_composition(child_id)
                if child.is_sequestered():
                    # clone the resource nodes that point to the assets / items
                    child_clone = child.clone_to(target_repo=target_repository,
                                                 target_parent=clone)

            return gutils.CreatedResponse(clone.object_map)
        except (PermissionDenied, InvalidArgument, InvalidId, KeyError) as ex:
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
            if str(domain_repo.genus_type) not in [str(Type(**REPOSITORY_GENUS_TYPES['domain-repo'])),
                                                   str(Type(**REPOSITORY_GENUS_TYPES['user-repo']))]:
                raise InvalidArgument('You cannot upload classes to a non-domain / non-user repository.')

            uploaded_file = self.data['files'][self.data['files'].keys()[0]]
            self.path = default_storage.save('{0}/{1}'.format(settings.MEDIA_ROOT,
                                                              uploaded_file.name),
                                             uploaded_file)
            os.chmod(self.path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IWGRP)
            self.async_result = import_file.apply_async((self.path, domain_repo, request.user))
            return Response()
        except (PermissionDenied, TypeError, InvalidArgument, NotFound, KeyError) as ex:
            gutils.handle_exceptions(ex)