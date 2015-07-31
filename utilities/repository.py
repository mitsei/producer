import time

from dlkit_django import RUNTIME, PROXY_SESSION
from dlkit_django.primordium import DataInputStream, DateTime
from dlkit_django.errors import IllegalState

from .general import *


def activate_managers(request):
    """
    Create an initial assessment manager and store it in the user session
    """
    if 'rm' not in request.session:
        condition = PROXY_SESSION.get_proxy_condition()
        condition.set_http_request(request)
        proxy = PROXY_SESSION.get_proxy(condition)
        set_session_data(request, 'rm', RUNTIME.get_service_manager('REPOSITORY', proxy=proxy))

    return request

def attach_asset_content_to_asset(bundle):
    repository = bundle['repository']
    asset = bundle['asset']
    data = bundle['data']

    asset_content_types = get_asset_content_type_from_runtime(repository)

    content_form = repository.get_asset_content_form_for_create(asset.ident,
                                                                asset_content_types)

    # timestamp the file name, so that people don't accidentally overwrite
    # someone else's file by naming it the same, i.e. photo.jpg
    blob = DataInputStream(data)
    filename = data.name.split('/')[-1]
    extension = filename.split('.')[-1]
    label = filename.split('.')[0]
    blob.name = label + '_' + str(int(time.time())) + '.' + extension

    content_form.set_data(blob)

    repository.create_asset_content(content_form)

def convert_to_id_list(str_list):
    """convert a list of string ids to a list of OSID Ids"""
    if not isinstance(str_list, list):
        str_list = [str_list]
    return [Id(i) for i in str_list]

def create_asset(repository, asset):
    """asset is a tuple of (asset_label, asset_file_object)
    expected to return a tuple of (asset_label, asset_id)
    """
    form = repository.get_asset_form_for_create([])

    form.display_name = asset[0]
    form.description = 'Asset container for: ' + asset[0]

    new_asset = repository.create_asset(form)

    attach_asset_content_to_asset({
        'asset': new_asset,
        'data': asset[1],
        'repository': repository
    })

    return asset[0], str(new_asset.ident)


def get_asset_content_type_from_runtime(repository):
    type_list = []
    try:
        config = repository._runtime.get_configuration()
        parameter_id = Id('parameter:assetContentRecordTypeForFiles@mongo')
        type_list.append(
            config.get_value_by_parameter(parameter_id).get_type_value())
    except AttributeError:
        pass
    return type_list

def get_enclosed_object_provider_id(request, catalog, enclosed_object):
    activate_managers(request)
    rm = get_session_data(request, 'rm')
    repo = rm.get_repository(catalog.ident)
    query_form = repo.get_asset_query()
    query_form.match_enclosed_object_id(enclosed_object.ident)
    query_result = repo.get_assets_by_query(query_form)
    if query_result.available() > 0:
        asset = query_result.next()
        return str(asset.provider_id)
    else:
        return None

def get_object_repository(manager, object_id, object_type='item', repository_id=None):
    """Get the object's repository even without the repositoryId"""
    # primarily used for Asset
    if repository_id is None:
        lookup_session = getattr(manager, 'get_{0}_lookup_session'.format(object_type))()
        lookup_session.use_federated_repository_view()
        object_ = getattr(lookup_session, 'get_{0}'.format(object_type))(clean_id(object_id))
        repository_id = object_.object_map['repositoryId']
    return manager.get_repository(clean_id(repository_id))

def set_enclosed_object_provider_id(request, catalog, enclosed_object, provider_id_str):
    activate_managers(request)
    rm = get_session_data(request, 'rm')
    repo = rm.get_repository(catalog.ident)
    form = repo.get_asset_form_for_update(enclosed_object.ident)
    form.set_provider(clean_id(provider_id_str))
    asset = repo.update_asset(form)
    return asset

def update_asset_urls(repository, asset):
    """update the asset URLs on assetContents with CloudFront URLs
    asset can be either the dlkit Asset or it's object map
    """
    if isinstance(asset, dict):
        asset_object = repository.get_asset(Id(asset['id']))
        asset_map = asset
    else:
        asset_object = asset
        asset_map = asset.object_map

    cloudfront_url_map = {}
    for asset_content in asset_object.get_asset_contents():
        try:
            cloudfront_url_map[str(asset_content.ident)] = asset_content.get_url()
        except IllegalState:
            # does not have
            pass

    for index, asset_content in enumerate(asset_map['assetContents']):
        if asset_content['id'] in cloudfront_url_map:
            asset_content['url'] = cloudfront_url_map[asset_content['id']]
            asset_map['assetContent'][index]['url'] = cloudfront_url_map[asset_content['id']]

    return asset_map

def update_edx_composition_boolean(form, bool_type, bool_value):
    if bool_type == 'visible_to_students':
        form.set_visible_to_students(bool(bool_value))
    elif bool_type == 'draft':
        form.set_draft(bool(bool_value))
    return form


def update_edx_composition_date(form, date_type, date_dict):
    verify_keys_present(date_dict, ['year', 'month', 'day'])
    if date_type == 'end':
        form.set_end_date(DateTime(year=date_dict['year'],
                                   month=date_dict['month'],
                                   day=date_dict['day']))
    elif date_type == 'start':
        form.set_start_date(DateTime(year=date_dict['year'],
                                     month=date_dict['month'],
                                     day=date_dict['day']))
    return form
