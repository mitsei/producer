import time

from dlkit.records.registry import COMPOSITION_GENUS_TYPES,\
    COMPOSITION_RECORD_TYPES, REPOSITORY_GENUS_TYPES, REPOSITORY_RECORD_TYPES

from dlkit.runtime import RUNTIME, PROXY_SESSION
from dlkit.runtime.primordium import DataInputStream, DateTime
from dlkit.runtime.errors import IllegalState, AlreadyExists

from dysonx.dysonx import get_or_create_user_repo, get_enclosed_object_asset,\
    _get_or_create_root_repo

from .general import *

EDX_COMPOSITION_RECORD_TYPE = Type(**COMPOSITION_RECORD_TYPES['edx-composition'])
LORE_REPOSITORY = Type(**REPOSITORY_RECORD_TYPES['lore-repo'])
DOMAIN_REPO_GENUS = Type(**REPOSITORY_GENUS_TYPES['domain-repo'])


def _get_genus_type(type_label):
    return Type(**COMPOSITION_GENUS_TYPES[type_label])


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

def append_child_composition(repository, parent, child):
    repository.use_unsequestered_composition_view()
    parent = repository.get_composition(parent.ident)
    current_children_ids = parent.get_children_ids()
    child_ids_str = [str(i) for i in current_children_ids]
    child_ids_str.append(str(child.ident))
    current_children_ids = [clean_id(i) for i in child_ids_str]
    form = repository.get_composition_form_for_update(parent.ident)
    form.set_children(current_children_ids)
    repository.update_composition(form)
    return repository.get_composition(child.ident)

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

def clean_up_dangling_references(rm, composition_id):
    # check all repositories for references to this composition, and remove
    # the composition_id from child_ids
    # may not work for all parent compositions, depending on authorizations
    if rm._proxy is not None:
        cqs = rm.get_composition_query_session(proxy=rm._proxy)
    else:
        cqs = rm.get_composition_query_session()
    cqs.use_federated_repository_view()
    cqs.use_unsequestered_composition_view()
    querier = cqs.get_composition_query()
    querier.match_contained_composition_id(clean_id(composition_id), True)
    compositions = cqs.get_compositions_by_query(querier)
    for composition in compositions:
        repo = get_object_repository(rm, composition.ident, 'composition')
        try:
            current_child_ids = composition.get_child_ids()
            current_child_idstrs = [str(i) for i in current_child_ids]
            current_child_idstrs.remove(str(clean_id(composition_id)))
            form = repo.get_composition_form_for_update(composition.ident)
            updated_child_ids = [clean_id(i) for i in current_child_idstrs]
            form.set_children(updated_child_ids)
            repo.update_composition(form)
        except (PermissionDenied, NotFound, IllegalState):
            pass

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

def create_domain_repo(rm, name, description):
    """
    Create a new domain repository.

    Args:
        name (unicode): Repository (Domain) name
        description (unicode): Repository description
        user_id (int): User ID of repository creator
    Returns:
        repo (learningresources.Repository): Newly-created repository
    """
    # check to see if there is a parent "course" repository repo, for managing
    # repo hierarchies. If not, create it.
    course_repo = _get_or_create_root_repo(rm, 'courses')
    form = rm.get_repository_form_for_create([LORE_REPOSITORY])
    form.display_name = str(name)
    form.description = '{0}'.format(str(description))
    form.set_provider(rm.effective_agent_id)
    form.set_genus_type(DOMAIN_REPO_GENUS)
    repo = rm.create_repository(form)
    rm.add_child_repository(course_repo.ident, repo.ident)
    return repo

def create_resource_wrapper(repository, resource):
    form = repository.get_composition_form_for_create([EDX_COMPOSITION_RECORD_TYPE])
    form.display_name = 'Wrapper for {0}'.format(resource.display_name.text)
    form.description = 'A sequestered wrapper'
    form.set_genus_type(_get_genus_type('resource-node'))
    form.set_sequestered(True)
    return repository.create_composition(form)
    # repository.add_asset(resource.ident, composition.ident)
    # return repository.get_composition(composition.ident)

def get_asset_content_type_from_runtime(repository):
    type_list = []
    try:
        config = repository._catalog._runtime.get_configuration()
        parameter_id = Id('parameter:assetContentRecordTypeForFiles@mongo')
        type_list.append(
            config.get_value_by_parameter(parameter_id).get_type_value())
    except AttributeError:
        pass
    return type_list

def get_course_node(repository):
    try:
        course_node = repository.course_node
    except AttributeError:
        form = repository.get_composition_form_for_create([EDX_COMPOSITION_RECORD_TYPE])
        form.display_name = 'Phantom course composition node'
        form.description = ''
        form.set_genus_type(_get_genus_type('course'))
        form.set_file_name('/xbundle/course')
        form.set_sequestered(True)
        course_node = repository.create_composition(form)
    return course_node

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

def get_object_repository(manager, object_id, object_type='asset', repository_id=None):
    """Get the object's repository even without the repositoryId"""
    # primarily used for Asset
    if repository_id is None:
        lookup_session = get_session(manager, object_type, 'lookup')
        try:
            lookup_session.use_unsequestered_composition_view()
        except AttributeError:
            pass
        if isinstance(object_id, basestring):
            object_id = clean_id(object_id)
        object_ = getattr(lookup_session, 'get_{0}'.format(object_type))(object_id)
        repository_id = object_.object_map['repositoryId']
    return manager.get_repository(clean_id(repository_id))

def get_session(manager, object_type, session_type):
    """get session type for object, using the manager"""
    if manager._proxy is not None:
        session = getattr(manager, 'get_{0}_{1}_session'.format(object_type, session_type))(proxy=manager._proxy)
    else:
        session = getattr(manager, 'get_{0}_{1}_session'.format(object_type, session_type))()
    session.use_federated_repository_view()
    return session

def set_enclosed_object_provider_id(request, catalog, enclosed_object, provider_id_str):
    activate_managers(request)
    rm = get_session_data(request, 'rm')
    repo = rm.get_repository(catalog.ident)
    form = repo.get_asset_form_for_update(enclosed_object.ident)
    form.set_provider(clean_id(provider_id_str))
    asset = repo.update_asset(form)
    return asset

def update_asset_urls(repository, asset, params=None):
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

    for index, asset_content in enumerate(asset_object.get_asset_contents()):
        try:
            cloudfront_url_map[str(asset_content.ident)] = asset_content.get_url()
        except IllegalState:
            # does not have
            pass
        try:
            if params is not None:
                if 'renderable_edxml' in params:
                    asset_map['assetContents'][index]['text']['text'] = asset_content.get_edxml_with_aws_urls()
        except AttributeError:
            pass

    for index, asset_content in enumerate(asset_map['assetContents']):
        if asset_content['id'] in cloudfront_url_map:
            asset_content['url'] = cloudfront_url_map[asset_content['id']]
            asset_map['assetContents'][index]['url'] = cloudfront_url_map[asset_content['id']]

    return asset_map

def update_composition_assets(am, rm, username, repository, composition_id, asset_ids):
    # remove current assets first, if they exist
    try:
        for asset in repository.get_composition_assets(clean_id(composition_id)):
            repository.remove_asset(asset.ident,
                                    clean_id(composition_id))
    except NotFound:
        pass

    if not isinstance(asset_ids, list):
        asset_ids = [asset_ids]

    # TODO: assign assets / items to the orchestrated repos / banks,
    # if necessary

    for asset_id in asset_ids:
        if 'assessment.Item' in asset_id:
            # repository == for the run
            # make sure the item is assigned to repository's orchestrated bank
            run_bank = am.get_bank(repository.ident)
            try:
                run_bank.get_item(clean_id(asset_id))
            except NotFound:
                am.assign_item_to_bank(clean_id(asset_id), run_bank.ident)

            # need to find the assessment associated with this item from user_bank
            user_repo = get_or_create_user_repo(username)
            user_bank = am.get_bank(user_repo.ident)
            querier = user_bank.get_assessment_query()
            querier.match_item_id(clean_id(asset_id), True)
            assessment = user_bank.get_assessments_by_query(querier).next()  # assume only one??
            enclosed_asset = get_enclosed_object_asset(user_repo, assessment)
            try:
                rm.assign_asset_to_repository(enclosed_asset.ident, repository.ident)
            except AlreadyExists:
                pass

            # finally, add the enclosure asset to the run repository composition
            repository.add_asset(enclosed_asset.ident,
                                 clean_id(composition_id))
        else:
            repository.add_asset(clean_id(asset_id),
                                 clean_id(composition_id))
    try:
        return repository.get_composition_assets(clean_id(composition_id))
    except NotFound:
        return []

def update_composition_children(repository, composition_id, children_ids,
                                am=None, rm=None, username=None):
    # in addition to clearing children, if a composition is of the sequestered resource-node
    # type that is NOT assigned to another repo, we need to delete it to prevent clutter...
    # Also, don't DELETE a composition unless it has no parents.
    # TODO
    if isinstance(composition_id, basestring):
        composition_id = clean_id(composition_id)
    repository.use_unsequestered_composition_view()
    composition = repository.get_composition(composition_id)
    original_children_ids = composition.get_child_ids()
    for original_child_id in original_children_ids:
        try:
            child = repository.get_composition(original_child_id)
            if child.is_sequestered():
                repository.delete_composition(child.ident)
        except NotFound:
            pass

    form = repository.get_composition_form_for_update(clean_id(composition_id))
    form.clear_children()

    # if an assetId or itemId is part of the childrenIds, then need to
    # make sure they are in the right orchestrated bank, as well as
    # add them to this composition as children of a sequestered composition..
    unified_list = []
    for child_id in children_ids:
        id_obj = clean_id(child_id)
        if 'repository.Composition' in child_id:
            # TODO:
            # Should be assigning the composition to THIS repository as well as
            # appending it as a childId.
            # DEPRECATED
            # Do not assign something to this repository automatically...keep
            # a separate action. This way we can do authz by checking
            # where the item belongs to...
            # try:
            #     rm.assign_composition_to_repository(id_obj, repository.ident)
            # except AlreadyExists:
            #     pass
            unified_list.append(id_obj)
        elif 'repository.Asset' in child_id:
            # DEPRECATED
            # Do not assign something to this repository automatically...keep
            # a separate action. This way we can do authz by checking
            # where the item belongs to...
            # try:
            #     rm.assign_asset_to_repository(id_obj, repository.ident)
            # except AlreadyExists:
            #     pass

            user_repo = get_or_create_user_repo(username)
            try:
                asset = repository.get_asset(id_obj)
            except NotFound:
                asset = user_repo.get_asset(id_obj)
            # Create a new sequestered, resource-node composition...
            wrapper_composition = create_resource_wrapper(repository, asset)

            user_repo.add_asset(asset.ident, wrapper_composition.ident)
            unified_list.append(wrapper_composition.ident)
        elif 'assessment.Item' in child_id:
            # repository == for the run
            # make sure the item is assigned to repository's orchestrated bank'
            item_id = id_obj
            run_bank = am.get_bank(repository.ident)
            try:
                run_bank.get_item(item_id)
            except NotFound:
                am.assign_item_to_bank(item_id, run_bank.ident)

            # need to find the assessment associated with this item from user_bank
            user_repo = get_or_create_user_repo(username)
            user_bank = am.get_bank(user_repo.ident)

            item = user_bank.get_item(item_id)

            querier = user_bank.get_assessment_query()
            querier.match_item_id(item_id, True)
            try:
                assessment = user_bank.get_assessments_by_query(querier).next()  # assume only one??
            except StopIteration:
                # make an assessment
                assessment_form = user_bank.get_assessment_form_for_create([])
                assessment_form.display_name = 'Assessment for {0}'.format(item.display_name.text)
                assessment = user_bank.create_assessment(assessment_form)
                user_bank.add_item(assessment.ident, item_id)

            # Create a new sequestered, resource-node composition...
            wrapper_composition = create_resource_wrapper(repository, assessment)
            user_repo.add_asset(assessment.ident, wrapper_composition.ident)

            enclosed_asset = get_enclosed_object_asset(user_repo, assessment)
            try:
                rm.assign_asset_to_repository(enclosed_asset.ident, repository.ident)
            except AlreadyExists:
                pass

            unified_list.append(wrapper_composition.ident)

    form.set_children(unified_list)
    return repository.update_composition(form)

def update_edx_composition_boolean(form, bool_type, bool_value):
    if bool_type == 'visible_to_students':
        form.set_visible_to_students(bool(bool_value))
    elif bool_type == 'draft':
        form.set_draft(bool(bool_value))
    return form


def update_edx_composition_date(form, date_type, date_dict):
    verify_keys_present(date_dict, ['year', 'month', 'day'])
    if date_type == 'end':
        form.set_end_date(DateTime(**date_dict))
    elif date_type == 'start':
        form.set_start_date(DateTime(**date_dict))
    return form


def update_repository_compositions(rm, repository, children_ids):
    # update the "root" course composition's children, here
    course_node = get_course_node(repository)
    update_composition_children(repository, course_node.ident, children_ids, rm=rm)
