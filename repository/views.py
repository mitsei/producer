import sys

from bson.errors import InvalidId

from django.template import RequestContext
from django.shortcuts import render_to_response


from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, exceptions
from rest_framework.permissions import AllowAny

from dlkit_django.errors import PermissionDenied, InvalidArgument, IllegalState,\
    NotFound, NoAccess
from dlkit_django.primordium import Id, Type
from dlkit.mongo.records.types import EDX_COMPOSITION_GENUS_TYPES, COMPOSITION_RECORD_TYPES

EDX_COMPOSITION_GENUS_TYPES_STR = [str(Type(**genus_type))
                                   for k, genus_type in EDX_COMPOSITION_GENUS_TYPES.iteritems()]

from utilities import general as gutils
from utilities import repository as rutils


EDX_COMPOSITION_RECORD_TYPE = Type(**COMPOSITION_RECORD_TYPES['edx-composition'])


class CreatedResponse(Response):
    def __init__(self, *args, **kwargs):
        super(CreatedResponse, self).__init__(status=status.HTTP_201_CREATED, *args, **kwargs)


class DeletedResponse(Response):
    def __init__(self, *args, **kwargs):
        super(DeletedResponse, self).__init__(status=status.HTTP_204_NO_CONTENT, *args, **kwargs)


class UpdatedResponse(Response):
    def __init__(self, *args, **kwargs):
        super(UpdatedResponse, self).__init__(status=status.HTTP_202_ACCEPTED, *args, **kwargs)



class DLKitSessionsManager(APIView):
    """ base class to handle all the dlkit session management
    """
    def initial(self, request, *args, **kwargs):
        """set up the repository manager"""
        super(DLKitSessionsManager, self).initial(request, *args, **kwargs)
        gutils.set_user(request)
        rutils.activate_managers(request)
        self.rm = gutils.get_session_data(request, 'rm')

    def finalize_response(self, request, response, *args, **kwargs):
        """save the updated repository manager"""
        try:
            gutils.set_session_data(request, 'rm', self.rm)
        except AttributeError:
            pass  # with an exception, the RM may not be set
        return super(DLKitSessionsManager, self).finalize_response(request,
                                                                   response,
                                                                   *args,
                                                                   **kwargs)


class Documentation(DLKitSessionsManager):
    """
    Shows the user documentation for talking to the RESTful service
    """
    permission_classes = (AllowAny,)

    def get(self, request, format=None):
        return render_to_response('repository/documentation.html',
                                  {},
                                  RequestContext(request))


class RepositoriesList(DLKitSessionsManager):
    """
    List all available repositories.
    api/v2/repository/repositories/

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
            data = gutils.get_data_from_request(request)

            if 'bankId' not in data:
                form = self.rm.get_repository_form_for_create([])
                gutils.verify_keys_present(data, ['name', 'description'])
                finalize_method = self.rm.create_repository
            else:
                repository = self.rm.get_repository(Id(data['bankId']))
                form = self.rm.get_repository_form_for_update(repository.ident)
                finalize_method = self.rm.update_repository

            if 'name' in data:
                form.display_name = data['name']
            if 'description' in data:
                form.description = data['description']

            new_repo = gutils.convert_dl_object(finalize_method(form))

            return CreatedResponse(new_repo)
        except (PermissionDenied, InvalidArgument, NotFound, KeyError) as ex:
            gutils.handle_exceptions(ex)


class RepositoryAssetDetails(DLKitSessionsManager):
    """
    Get asset details
    api/v2/repository/repositories/<repository_id>/assets/<asset_id>/

    GET, PUT, DELETE
    PUT to modify an existing asset (name or contents). Include only the changed parameters.
        If files are included, all current files are deleted / replaced.
    DELETE to remove from the repository.

    Note that for RESTful calls, you need to set the request header
    'content-type' to 'application/json'

    Example (note the use of double quotes!!):
       {"name" : "an updated item"}
    """

    def delete(self, request, repository_id, asset_id, format=None):
        try:
            repository = self.rm.get_repository(gutils.clean_id(repository_id))

            # need to manually delete the asset contents
            asset = repository.get_asset(gutils.clean_id(asset_id))
            for asset_content in asset.get_asset_contents():
                repository.delete_asset_content(asset_content.ident)

            repository.delete_asset(gutils.clean_id(asset_id))
            return DeletedResponse()
        except (PermissionDenied, IllegalState, InvalidId) as ex:
            gutils.handle_exceptions(ex)

    def get(self, request, repository_id, asset_id, format=None):
        try:
            repository = self.rm.get_repository(gutils.clean_id(repository_id))
            asset = repository.get_asset(gutils.clean_id(asset_id))
            asset_map = rutils.update_asset_urls(repository, asset)

            asset_map.update({
                '_links': {
                    'self': gutils.build_safe_uri(request),
                }
            })

            return Response(asset_map)
        except (PermissionDenied, NotFound, InvalidId) as ex:
            gutils.handle_exceptions(ex)

    def put(self, request, repository_id, asset_id, format=None):
        try:
            data = gutils.get_data_from_request(request)

            gutils.verify_at_least_one_key_present(data,
                                                   ['name', 'description', 'files'])

            repository = self.rm.get_repository(gutils.clean_id(repository_id))
            original_asset = repository.get_asset(gutils.clean_id(asset_id))

            if 'files' in data:
                # delete current assets
                for asset_content in original_asset.get_asset_contents():
                    repository.delete_asset_content(asset_content.ident)

                # create the new contents
                for asset in data['files'].items():
                    rutils.attach_asset_content_to_asset({
                        'asset': original_asset,
                        'data': asset[1],
                        'repository': repository
                    })

            if 'name' in data or 'description' in data:
                form = repository.get_asset_form_for_update(gutils.clean_id(asset_id))

                if 'name' in data:
                    form.display_name = data['name']
                if 'description' in data:
                    form.description = data['description']

                updated_asset = repository.update_asset(form)
            else:
                updated_asset = original_asset

            data = {
                updated_asset.display_name.text: str(updated_asset.ident)
            }

            return UpdatedResponse(data)
        except (PermissionDenied, InvalidArgument, NoAccess, InvalidId, KeyError) as ex:
            gutils.handle_exceptions(ex)


class RepositoryAssetsList(DLKitSessionsManager):
    """
    Get or add assets to a repository
    api/v2/repository/repositories/<repository_id>/assets/

    GET, POST
    GET to view current assets
    POST to create a new asset

    Note that for RESTful calls, you need to set the request header
    'content-type' to 'application/json'

    Example (note the use of double quotes!!):
       {"assetLabel" : <file object>}
    """

    def get(self, request, repository_id, format=None):
        try:
            repository = self.rm.get_repository(gutils.clean_id(repository_id))
            assets = repository.get_assets()
            data = gutils.extract_items(request, assets)

            # need to replace each URL here with CloudFront URL...
            for asset in data['data']['results']:
                asset = rutils.update_asset_urls(repository, asset)

            return Response(data)
        except (PermissionDenied, NotFound) as ex:
            gutils.handle_exceptions(ex)

    def post(self, request, repository_id, format=None):
        try:
            repository = self.rm.get_repository(gutils.clean_id(repository_id))

            data = gutils.get_data_from_request(request)

            gutils.verify_keys_present(data, ['files'])

            return_data = {}
            for asset in data['files'].items():
                # asset should be a tuple of (asset_label, asset_file_object)
                created_asset = rutils.create_asset(repository, asset)
                return_data[created_asset[0]] = created_asset[1]  # (asset_label: asset_id)

            return CreatedResponse(return_data)
        except (PermissionDenied, InvalidArgument, KeyError) as ex:
            gutils.handle_exceptions(ex)


class RepositoryCompositionAssetsList(DLKitSessionsManager):
    """
    Get or add assets to a repository
    api/v2/repository/repositories/<repository_id>/compositions/<composition_id>/assets/

    GET, PUT
    GET to view a composition's current assets
    PUT to append one or more assets to the composition. The assets / assessments must already
        exist elsewhere in the system.

    Note that for RESTful calls, you need to set the request header
    'content-type' to 'application/json'

    Example (note the use of double quotes!!):
       {"assetIds" : ["asset:1@MIT", "assessment:25@MIT"]}
    """

    def get(self, request, repository_id, composition_id, format=None):
        try:
            repository = self.rm.get_repository(gutils.clean_id(repository_id))
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

    def put(self, request, repository_id, composition_id, format=None):
        try:
            repository = self.rm.get_repository(gutils.clean_id(repository_id))

            data = gutils.get_data_from_request(request)

            gutils.verify_keys_present(data, ['assetIds'])

            # remove current assets first, if they exist
            try:
                for asset in repository.get_composition_assets(Id(composition_id)):
                    repository.remove_asset(asset.ident, Id(composition_id))
            except NotFound:
                pass

            if not isinstance(data['assetIds'], list):
                data['assetIds'] = [data['assetIds']]

            for asset_id in data['assetIds']:
                repository.add_asset(Id(asset_id), Id(composition_id))

            return UpdatedResponse()
        except (PermissionDenied, InvalidArgument, KeyError) as ex:
            gutils.handle_exceptions(ex)



class RepositoryCompositionDetails(DLKitSessionsManager):
    """
    Get asset details
    api/v2/repository/repositories/<repository_id>/compositions/<composition_id>/

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

    def delete(self, request, repository_id, composition_id, format=None):
        try:
            repository = self.rm.get_repository(gutils.clean_id(repository_id))

            repository.delete_composition(gutils.clean_id(composition_id))
            return DeletedResponse()
        except (PermissionDenied, IllegalState, InvalidId) as ex:
            gutils.handle_exceptions(ex)

    def get(self, request, repository_id, composition_id, format=None):
        try:
            repository = self.rm.get_repository(gutils.clean_id(repository_id))
            composition = repository.get_composition(gutils.clean_id(composition_id))
            composition_map = composition.object_map

            composition_map.update({
                '_links': {
                    'self': gutils.build_safe_uri(request),
                    'assets': gutils.build_safe_uri(request) + 'assets/'
                }
            })

            return Response(composition_map)
        except (PermissionDenied, NotFound, InvalidId) as ex:
            gutils.handle_exceptions(ex)

    def put(self, request, repository_id, composition_id, format=None):
        try:
            data = gutils.get_data_from_request(request)

            gutils.verify_at_least_one_key_present(data,
                                                   ['name', 'description', 'childIds',
                                                    'startDate', 'endDate', 'visibleToStudents',
                                                    'draft'])

            repository = self.rm.get_repository(gutils.clean_id(repository_id))

            form = repository.get_composition_form_for_update(gutils.clean_id(composition_id))
            if 'childIds' in data:
                form.clear_children()
                data['childIds'] = rutils.convert_to_id_list(data['childIds'])
                form.set_children(data['childIds'])

            if 'name' in data:
                form.display_name = data['name']

            if 'description' in data:
                form.description = data['description']

            composition = repository.get_composition(gutils.clean_id(composition_id))

            if str(composition.genus_type) in EDX_COMPOSITION_GENUS_TYPES_STR:
                if 'startDate' in data:
                    form = rutils.update_edx_composition_date(form, 'start', data['startDate'])

                if 'endDate' in data:
                    form = rutils.update_edx_composition_date(form, 'end', data['endDate'])

                if 'visibleToStudents' in data:
                    form = rutils.update_edx_composition_boolean(form,
                                                                 'visible_to_students',
                                                                 bool(data['visibleToStudents']))

                if 'draft' in data:
                    form = rutils.update_edx_composition_boolean(form,
                                                                 'draft',
                                                                 bool(data['draft']))

            composition = repository.update_composition(form)

            return UpdatedResponse(composition.object_map)
        except (PermissionDenied, InvalidArgument, InvalidId, KeyError) as ex:
            gutils.handle_exceptions(ex)


class RepositoryCompositionsList(DLKitSessionsManager):
    """
    Get or add compositions to a repository
    api/v2/repository/repositories/<repository_id>/compositions/

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

    def get(self, request, repository_id, format=None):
        try:
            params = gutils.get_data_from_request(request)

            repository = self.rm.get_repository(gutils.clean_id(repository_id))
            repository.use_federated_repository_view()

            query_results = []
            if len(params) > 0:
                gutils.verify_at_least_one_key_present(params, ['course', 'chapter', 'sequential',
                                                                'split_test', 'vertical', 'page'])
            try:
                for genus_val, empty in params.iteritems():
                    if genus_val != 'page':
                        query_results.append(
                            repository.get_compositions_by_genus_type(
                                str(Type(**EDX_COMPOSITION_GENUS_TYPES[genus_val]))))
            except KeyError:
                raise IllegalState('Invalid query genus type provided. Only "course", ' +
                                   '"chapter", "sequential", "split_test", and "vertical" ' +
                                   'are allowed.')

            if len(query_results) > 0:
                compositions = []
                for results in query_results:
                    compositions += list(results)
            else:
                compositions = repository.get_compositions()
            data = gutils.extract_items(request, compositions)

            return Response(data)
        except (PermissionDenied, NotFound, IllegalState) as ex:
            gutils.handle_exceptions(ex)

    def post(self, request, repository_id, format=None):
        try:
            repository = self.rm.get_repository(gutils.clean_id(repository_id))

            data = gutils.get_data_from_request(request)

            gutils.verify_keys_present(data, ['name', 'description'])

            if 'type' in data and 'edx' in data['type']:
                form = repository.get_composition_form_for_create([EDX_COMPOSITION_RECORD_TYPE])
                edx_type = data['type'].split('-')[-1]  # assumes type is edx-course, edx-vertical, etc.
                try:
                    form.set_genus_type(Type(**(EDX_COMPOSITION_GENUS_TYPES[edx_type])))

                    if 'startDate' in data:
                        form = rutils.update_edx_composition_date(form, 'start', data['startDate'])

                    if 'endDate' in data:
                        form = rutils.update_edx_composition_date(form, 'end', data['endDate'])

                    if 'visibleToStudents' in data:
                        form = rutils.update_edx_composition_boolean(form,
                                                                     'visible_to_students',
                                                                     bool(data['visibleToStudents']))

                    if 'draft' in data:
                        form = rutils.update_edx_composition_boolean(form,
                                                                     'draft',
                                                                     bool(data['draft']))

                except KeyError:
                    raise InvalidArgument('Bad genus type provided.')
            else:
                form = repository.get_composition_form_for_create([])
            form.display_name = data['name']
            form.description = data['description']

            if 'childIds' in data:
                data['childIds'] = rutils.convert_to_id_list(data['childIds'])
                form.set_children(data['childIds'])

            composition = repository.create_composition(form)
            return CreatedResponse(composition.object_map)
        except (PermissionDenied, InvalidArgument, IllegalState, KeyError) as ex:
            gutils.handle_exceptions(ex)


class RepositoryDetails(DLKitSessionsManager):
    """
    Shows details for a specific repository.
    api/v2/repository/repositories/<repository_id>/

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
            return DeletedResponse()
        except (PermissionDenied, NotFound, InvalidId) as ex:
            gutils.handle_exceptions(ex)
        except IllegalState as ex:
            modified_ex = type(ex)('Repository is not empty.')
            gutils.handle_exceptions(modified_ex)

    def get(self, request, repository_id, format=None):
        try:
            repository = self.rm.get_repository(gutils.clean_id(repository_id))
            repository = gutils.convert_dl_object(repository)
            repository = gutils.add_links(request,
                                          repository,
                                          {
                                              'assets': 'assets/',
                                              'compositions': 'compositions/'
                                          })
            return Response(repository)
        except (PermissionDenied, InvalidId, NotFound) as ex:
            gutils.handle_exceptions(ex)

    def put(self, request, repository_id, format=None):
        try:
            form = self.rm.get_repository_form_for_update(gutils.clean_id(repository_id))

            data = gutils.get_data_from_request(request)

            gutils.verify_at_least_one_key_present(data, ['name', 'description'])

            # should work for a form or json data
            if 'name' in data:
                form.display_name = data['name']
            if 'description' in data:
                form.description = data['description']

            updated_repository = self.rm.update_repository(form)
            updated_repository = gutils.convert_dl_object(updated_repository)
            updated_repository = gutils.add_links(request,
                                                  updated_repository,
                                                  {
                                                      'assets': 'assets/'
                                                  })

            return UpdatedResponse(updated_repository)
        except (PermissionDenied, KeyError, InvalidArgument, InvalidId, NotFound) as ex:
            gutils.handle_exceptions(ex)


class RepositoryService(DLKitSessionsManager):
    """
    List all available repository services.
    api/v2/repository/
    """

    def get(self, request, format=None):
        """
        List all available repository services. For now, just 'repositories'
        """
        data = {}
        data = gutils.add_links(request,
                                data,
                                {
                                    'repositories': 'repositories/',
                                    'documentation': 'docs/'
                                })
        return Response(data)

