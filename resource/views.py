from bson.errors import InvalidId

from django.template import RequestContext
from django.shortcuts import render_to_response


from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, exceptions
from rest_framework.permissions import AllowAny

from dlkit_django.errors import PermissionDenied, InvalidArgument, IllegalState, NotFound
from dlkit_django.primordium import Id

from utilities import general as gutils
from utilities import repository as rutils
from utilities import resource as resutils


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
        """set up the resource manager"""
        super(DLKitSessionsManager, self).initial(request, *args, **kwargs)
        gutils.set_user(request)
        resutils.activate_managers(request)
        self.resm = gutils.get_session_data(request, 'resm')

    def finalize_response(self, request, response, *args, **kwargs):
        """save the updated repository manager"""
        try:
            gutils.set_session_data(request, 'resm', self.resm)
        except AttributeError:
            pass  # with an exception, the RM may not be set
        return super(DLKitSessionsManager, self).finalize_response(request,
                                                                   response,
                                                                   *args,
                                                                   **kwargs)




class BinDetails(DLKitSessionsManager):
    """
    Shows details for a specific bin.
    api/v2/resource/bins/<bin_id>/

    GET, PUT, DELETE
    PUT will update the bin. Only changed attributes need to be sent.
    DELETE will remove the bin.

    Note that for RESTful calls, you need to set the request header
    'content-type' to 'application/json'

    Example (note the use of double quotes!!):
       PUT {"name" : "a new bin"}
    """
    def delete(self, request, bin_id, format=None):
        try:
            self.resm.delete_bin(gutils.clean_id(bin_id))
            return DeletedResponse()
        except (PermissionDenied, NotFound) as ex:
            gutils.handle_exceptions(ex)
        except IllegalState as ex:
            modified_ex = type(ex)('Bin is not empty.')
            gutils.handle_exceptions(modified_ex)

    def get(self, request, bin_id, format=None):
        try:
            bin_ = self.resm.get_bin(gutils.clean_id(bin_id))
            bin_ = gutils.convert_dl_object(bin_)
            bin_ = gutils.add_links(request,
                                    bin_,
                                    {
                                        'resources': 'resources/'
                                    })
            return Response(bin_)
        except (PermissionDenied, InvalidId, NotFound) as ex:
            gutils.handle_exceptions(ex)

    def put(self, request, bin_id, format=None):
        try:
            form = self.resm.get_bin_form_for_update(gutils.clean_id(bin_id))

            data = gutils.get_data_from_request(request)

            gutils.verify_at_least_one_key_present(data, ['name', 'description'])

            # should work for a form or json data
            if 'name' in data:
                form.display_name = data['name']
            if 'description' in data:
                form.description = data['description']

            updated_bin = self.resm.update_bin(form)
            updated_bin = gutils.convert_dl_object(updated_bin)
            updated_bin = gutils.add_links(request,
                                           updated_bin,
                                           {
                                               'resources': 'resources/'
                                           })

            return UpdatedResponse(updated_bin)
        except (PermissionDenied, KeyError, InvalidArgument, NotFound) as ex:
            gutils.handle_exceptions(ex)


class BinsList(DLKitSessionsManager):
    """
    List all available resource bins.
    api/v2/resource/bins/

    POST allows you to create a new bin, requires two parameters:
      * name
      * description

    Alternatively, if you provide an assessment bank ID,
    the bin will be orchestrated to have a matching internal identifier.
    The name and description will be set for you.
      * bankId
      * name (optional)
      * description (optional)

    Note that for RESTful calls, you need to set the request header
    'content-type' to 'application/json'

    Example (note the use of double quotes!!):
      {"name" : "a new bin",
       "description" : "this is a test"}

       OR
       {"bankId": "assessment.Bank%3A5547c37cea061a6d3f0ffe71%40cs-macbook-pro"}
    """

    def get(self, request, format=None):
        """
        List all available bins
        """
        try:
            bins = self.resm.bins
            bins = gutils.extract_items(request, bins)
            return Response(bins)
        except PermissionDenied:
            raise exceptions.AuthenticationFailed('Permission denied. You do not have '
                                                  'rights to view bins.')

    def post(self, request, format=None):
        """
        Create a new bin, if authorized

        """
        try:
            data = gutils.get_data_from_request(request)

            if 'bankId' not in data:
                gutils.verify_keys_present(data, ['name', 'description'])
                form = self.resm.get_bin_form_for_create([])
                finalize_method = self.resm.create_bin
            else:
                bin_ = self.resm.get_bin(Id(data['bankId']))
                form = self.resm.get_bin_form_for_update(bin_.ident)
                finalize_method = self.resm.update_bin

            if 'name' in data:
                form.display_name = data['name']
            if 'description' in data:
                form.description = data['description']

            new_bin = gutils.convert_dl_object(finalize_method(form))

            return CreatedResponse(new_bin)
        except (PermissionDenied, InvalidArgument, NotFound, KeyError) as ex:
            gutils.handle_exceptions(ex)



class BinResourceDetails(DLKitSessionsManager):
    """
    Get resource details
    api/v2/resource/bins/<bin_id>/resources/<resource_id>/

    GET, PUT, DELETE
    PUT to modify an existing resource (name or contents). Include only the changed parameters.
    DELETE to remove from the bin.

    Note that for RESTful calls, you need to set the request header
    'content-type' to 'application/json'

    Example (note the use of double quotes!!):
       {"name" : "an updated item"}
    """

    def delete(self, request, bin_id, resource_id, format=None):
        try:
            bin_ = self.resm.get_bin(gutils.clean_id(bin_id))
            rm = gutils.get_session_data(request, 'rm')
            repository = rm.get_repository(bin_.ident)

            resource = bin_.get_resource(gutils.clean_id(resource_id))

            # try to delete the resource first, to get permissions check
            bin_.delete_resource(resource.ident)

            # need to manually delete the asset contents now
            avatar_asset = repository.get_asset(resource.get_avatar_id())
            for asset_content in avatar_asset.get_asset_contents():
                repository.delete_asset_content(asset_content.ident)

            repository.delete_asset(avatar_asset.ident)

            return DeletedResponse()
        except (PermissionDenied, IllegalState) as ex:
            gutils.handle_exceptions(ex)

    def get(self, request, bin_id, resource_id, format=None):
        try:
            bin_ = self.resm.get_bin(gutils.clean_id(bin_id))
            resource = bin_.get_resource(gutils.clean_id(resource_id))
            resource_map = resutils.update_resource_avatar_urls(bin_, resource)

            resource_map.update({
                '_links': {
                    'self': gutils.build_safe_uri(request),
                }
            })

            return Response(resource_map)
        except (PermissionDenied, NotFound) as ex:
            gutils.handle_exceptions(ex)

    def put(self, request, bin_id, resource_id, format=None):
        try:
            data = gutils.get_data_from_request(request)

            gutils.verify_at_least_one_key_present(data,
                                                   ['name', 'description', 'files'])

            bin_ = self.resm.get_bin(gutils.clean_id(bin_id))
            original_resource = bin_.get_resource(gutils.clean_id(resource_id))
            updated_resource = original_resource

            if 'files' in data and 'avatar' in data['files']:
                rm = gutils.get_session_data(request, 'rm')
                repo = rm.get_repository(bin_.ident)

                # do this first, to get permissions check
                form = bin_.get_resource_form_for_update(gutils.clean_id(resource_id))

                # allowed to update, so delete current avatar asset
                current_avatar_id = original_resource.get_avatar_id()
                avatar_asset = repo.get_asset(current_avatar_id)
                for content in avatar_asset.get_asset_contents():
                    repo.delete_asset_content(content.ident)
                repo.delete_asset(current_avatar_id)

                # then create the new avatar as an asset
                avatar_label, avatar_asset_id = rutils.create_asset(repo,
                    ('Avatar for ' + request.user.username,
                     data['files']['avatar']))
                form.set_avatar(Id(avatar_asset_id))
                updated_resource = bin_.update_resource(form)

            if 'name' in data or 'description' in data:
                form = bin_.get_resource_form_for_update(gutils.clean_id(resource_id))

                if 'name' in data:
                    form.display_name = data['name']
                if 'description' in data:
                    form.description = data['description']

                updated_resource = bin_.update_resource(form)

            resource_map = resutils.update_resource_avatar_urls(bin_, updated_resource)

            return UpdatedResponse(resource_map)
        except (PermissionDenied, InvalidArgument, KeyError) as ex:
            gutils.handle_exceptions(ex)


class BinResourcesList(DLKitSessionsManager):
    """
    Get or add resources to a bin
    api/v2/resource/bins/<bin_id>/resources/

    GET, POST
    GET to view current resources. Avatar URLs only provided if ?avatar_urls is provided
    POST to create a new resource

    Note that for RESTful calls, you need to set the request header
    'content-type' to 'application/json'

    Example (note the use of double quotes!!):
       {"name" : "Foo Bar", "description": "I like sand."}
    """

    def get(self, request, bin_id, format=None):
        try:
            params = gutils.get_data_from_request(request)

            bin_ = self.resm.get_bin(gutils.clean_id(bin_id))

            if 'agent' in params:
                try:
                    resources = [bin_.get_resource_by_agent(resutils.get_agent_id(params['agent']))]
                except NotFound:
                    resources = []
            else:
                resources = bin_.get_resources()
            data = gutils.extract_items(request, resources)

            # only inject URL if flagged
            if 'avatar_urls' in params:
                # need to inject the avatar URL here, not just give the ID
                for resource in data['data']['results']:
                    resource = resutils.update_resource_avatar_urls(bin_, resource)

            return Response(data)
        except (PermissionDenied, NotFound) as ex:
            gutils.handle_exceptions(ex)

    def post(self, request, bin_id, format=None):
        try:
            data = gutils.get_data_from_request(request)

            gutils.verify_at_least_one_key_present(data,
                                                   ['name', 'description'])
                                                   # avatar file is optional

            if 'files' in data and 'avatar' not in data['files']:
                raise exceptions.APIException('The avatar file must use the field name "avatar".')

            bin_ = self.resm.get_bin(gutils.clean_id(bin_id))

            form = bin_.get_resource_form_for_create([])

            if 'name' in data:
                form.display_name = data['name']

            if 'description' in data:
                form.description = data['description']

            if 'files' in data and 'avatar' in data['files']:
                # create the avatar as an asset, first
                rm = gutils.get_session_data(request, 'rm')
                repo = rm.get_repository(bin_.ident)
                avatar_label, avatar_asset_id = rutils.create_asset(repo,
                    ('Avatar for ' + request.user.username,
                     data['files']['avatar']))
                form.set_avatar(Id(avatar_asset_id))
                inject_avatar_url = True
            else:
                inject_avatar_url = False

            resource = bin_.create_resource(form)

            # now assign the agent to the resource
            bin_.assign_agent_to_resource(bin_.effective_agent_id, resource.ident)

            # inject URL on create
            if inject_avatar_url:
                return_value = resutils.update_resource_avatar_urls(bin_, resource)
            else:
                return_value = resource.object_map

            return CreatedResponse(return_value)
        except (PermissionDenied, InvalidArgument, KeyError) as ex:
            gutils.handle_exceptions(ex)


class Documentation(DLKitSessionsManager):
    """
    Shows the user documentation for talking to the RESTful service
    """
    permission_classes = (AllowAny,)

    def get(self, request, format=None):
        return render_to_response('resource/documentation.html',
                                  {},
                                  RequestContext(request))

class ResourceService(DLKitSessionsManager):
    """
    List all available resource services.
    api/v2/resource/
    """

    def get(self, request, format=None):
        """
        List all available resource services.
        """
        data = {}
        data = gutils.add_links(request,
                                data,
                                {
                                    'bins': 'bins/',
                                    'documentation': 'docs/'
                                })
        return Response(data)

