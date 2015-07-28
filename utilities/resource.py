from dlkit_django import RUNTIME, PROXY_SESSION
from dlkit_django.errors import IllegalState

#####
# for creating a proxy agent
#####
from dlkit_django.proxy_example import TestRequest

from .general import *


def activate_managers(request):
    """
    Create an initial assessment manager and store it in the user session
    """
    if 'resm' not in request.session:
        condition = PROXY_SESSION.get_proxy_condition()
        condition.set_http_request(request)
        proxy = PROXY_SESSION.get_proxy(condition)
        set_session_data(request, 'resm', RUNTIME.get_service_manager('RESOURCE', proxy=proxy))

    if 'rm' not in request.session:
        condition = PROXY_SESSION.get_proxy_condition()
        condition.set_http_request(request)
        proxy = PROXY_SESSION.get_proxy(condition)
        set_session_data(request, 'rm', RUNTIME.get_service_manager('REPOSITORY', proxy=proxy))

    return request

def get_agent_id(agent_id):
    """Not a great hack...depends too much on internal DLKit knowledge"""
    if '@' not in agent_id:
        agent_id += '@mit.edu'
    test_request = TestRequest(agent_id)
    condition = PROXY_SESSION.get_proxy_condition()
    condition.set_http_request(test_request)
    proxy = PROXY_SESSION.get_proxy(condition)
    resm = RUNTIME.get_service_manager('RESOURCE', proxy=proxy)
    return resm.effective_agent_id

def update_resource_avatar_urls(bin_, resource):
    """update the resource avatar URLs with CloudFront URLs
    """
    if isinstance(resource, dict):
        resource_object = bin_.get_resource(Id(resource['id']))
        resource_map = resource
    else:
        resource_object = resource
        resource_map = resource.object_map

    try:
        avatar_asset = resource_object.get_avatar()

        for asset_content in avatar_asset.get_asset_contents():
            # should only be one
            resource_map['avatarURL'] = asset_content.get_url()
    except IllegalState:
        pass  # no avatar for that user

    return resource_map