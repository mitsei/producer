import re
import json
import pickle
import random
import string
import traceback

from bson.errors import InvalidId
from copy import deepcopy

from django.http import QueryDict
from django.db import IntegrityError
from django.utils.http import unquote, quote
# http://www.django-rest-framework.org/api-guide/pagination
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.contrib.auth.models import User
from django.conf import settings

from dlkit.abstract_osid.assessment import objects as abc_assessment_objects
from dlkit.abstract_osid.learning import objects as abc_learning_objects
from dlkit.abstract_osid.repository import objects as abc_repository_objects
from dlkit.abstract_osid.type import objects as abc_type_objects
from dlkit.abstract_osid.grading import objects as abc_grading_objects
from dlkit.abstract_osid.resource import objects as abc_resource_objects
from dlkit.mongo.locale.types import String

from dlkit_django import PROXY_SESSION, RUNTIME
from dlkit_django.primordium import Id, Type
from dlkit_django.errors import (
    PermissionDenied, InvalidArgument, NotFound, NoAccess, Unsupported, IllegalState
)
from dlkit_django.proxy_example import TestRequest

from dysonx.dysonx import DysonXUtil, ABS_PATH

from inflection import underscore

from rest_framework import exceptions, status
from rest_framework.pagination import (
    PaginationSerializer, DefaultObjectSerializer
)
from rest_framework.views import APIView
from rest_framework.response import Response


WORDIGNORECASE_STRING_MATCH_TYPE = Type(**String().get_type_data('WORDIGNORECASE'))


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
        set_user(request)
        try:
            self.data = get_data_from_request(request)
        except InvalidArgument as ex:
            handle_exceptions(ex)


class DLSerializer(DefaultObjectSerializer):
    def to_native(self, obj):
        results = []
        for item in obj:
            try:
                if isinstance(item, tuple):
                    item_map = item[0].object_map
                    item_map.update({
                        'canEdit': item[1]
                    })
                else:
                    item_map = item.object_map
                results.append(item_map)
            except:
                results.append(item)
        return results

class DLPaginationSerializer(PaginationSerializer):
    """To return an object's object_map instead of the __dict__ or dir() values that
    the built-in serializer returns

    """
    class Meta:
        object_serializer_class = DLSerializer

def activate_managers(request):
    """
    Create initial managers and store them in the user session
    """
    managers = [('am', 'ASSESSMENT'),
        ('cm', 'COMMENTING'),
        ('gm', 'GRADING'),
        ('lm', 'LEARNING'),
        ('rm', 'REPOSITORY')]

    for manager in managers:
        nickname = manager[0]
        service_name = manager[1]
        if nickname not in request.session:
            condition = PROXY_SESSION.get_proxy_condition()
            condition.set_http_request(request)
            proxy = PROXY_SESSION.get_proxy(condition)
            set_session_data(request, nickname, RUNTIME.get_service_manager(service_name,
                                                                            proxy=proxy))
    return request

def append_slash(url):
    if url[-1] != '/':
        url += '/'
    return url

def build_safe_uri(request):
    """
    because Django's request.build_absolute_uri() does not url-escape the
    IDs, it leaves in : and @. Which means that the URIs are not compatible
    with the data stored in the Mongo impl. For example, deleting
    an assessment bank should confirm that there are no assessments, first.
    But the bankId attribute of assessments is stored url-escaped.
    So none will be found, if we rely on the non-url-escaped URIs
    generated by Django.
    """
    uri = ''
    if request.is_secure():
        uri += 'https://'
    else:
        uri += 'http://'
    uri += request.get_host()
    uri += quote(request.get_full_path())

    return append_slash(uri)

def clean_id(_id):
    """
    Django seems to un-url-safe the IDs passed in to the rest framework views,
    so we need to url-safe them, then convert them to OSID IDs
    """
    if isinstance(_id, basestring):
        if _id.find('@') >= 0:
            return Id(quote(_id))
        else:
            return Id(_id)
    else:
        return _id

def clean_up_dl_objects(data):
    """
    Because dl objects need to be parsed out of any dict into json format
    before they can be rendered in the browser, yet we cannot just do
    json dumps because then they'll be strings...but they need
    to be objects to be rendered properly.
    """
    if isinstance(data, dict):
        results = {}
        for key, value in data.iteritems():
            if (isinstance(value, abc_assessment_objects.Bank) or
                isinstance(value, abc_assessment_objects.Assessment)):
                results[key] = convert_dl_object(value)
            else:
                results[key] = value
        return results
    else:
        return data

def clean_up_post(bank, item):
    if bank and item:
        if isinstance(item, abc_assessment_objects.Item):
            bank.delete_item(item.ident)
        elif isinstance(item, abc_assessment_objects.Assessment):
            bank.delete_assessment(item.ident)
        elif isinstance(item, abc_assessment_objects.Answer):
            bank.delete_answer(item.ident)

def clean_up_path(path):
    return path.replace('//', '/')

def config_osid_object_querier(querier, params):
    for param, value in params.iteritems():
        try:
            method_name = 'match_{0}'.format(underscore(param))
            if hasattr(querier, method_name):
                if param in ['displayName', 'description']:
                    getattr(querier, method_name)(str(value),
                                                  WORDIGNORECASE_STRING_MATCH_TYPE,
                                                  True)
                elif param in ['learningObjectiveId', 'genusType']:
                    if '@' in value:
                        value = quote(value)
                    getattr(querier, method_name)(str(value),
                                                  True)
                else:
                    getattr(querier, method_name)(float(value),
                                                  True)
        except AttributeError:
            pass
    return querier

def convert_dl_object(obj):
    """
    convert a DLKit object into a "real" json-able object
    """
    try:
        #return json.loads(json.loads(json.dumps(obj, cls=DLEncoder)))
        return obj.object_map 
    except:
        return obj

def convert_to_osid_id(id):
    if isinstance(id, basestring):
        return Id(id)
    else:
        return id

def dl_dumps(obj):
    try:
        clean_obj = strip_object_ids(obj)
        return json.dumps(clean_obj)
    except:
        return pickle.dumps(obj)

def extract_items(request, a_list, bank=None, section=None):
    from .assessment import get_question_status  # import here to prevent circular imports

    results = {
        '_links': {
            'self'      : build_safe_uri(request)
        },
        'data'  : []
    }

    if (not isinstance(a_list, list) and
        not isinstance(a_list, abc_type_objects.TypeList) and
        not isinstance(a_list, abc_assessment_objects.AssessmentList) and
        not isinstance(a_list, abc_assessment_objects.BankList) and
        not isinstance(a_list, abc_assessment_objects.ItemList) and
        not isinstance(a_list, abc_assessment_objects.AnswerList) and
        not isinstance(a_list, abc_assessment_objects.QuestionList) and
        not isinstance(a_list, abc_assessment_objects.AssessmentOfferedList) and
        not isinstance(a_list, abc_assessment_objects.AssessmentTakenList) and
        not isinstance(a_list, abc_assessment_objects.ResponseList) and
        not isinstance(a_list, abc_repository_objects.RepositoryList) and
        not isinstance(a_list, abc_repository_objects.AssetList) and
        not isinstance(a_list, abc_repository_objects.CompositionList) and
        not isinstance(a_list, abc_resource_objects.BinList) and
        not isinstance(a_list, abc_resource_objects.ResourceList) and
        not isinstance(a_list, abc_grading_objects.GradebookList) and
        not isinstance(a_list, abc_grading_objects.GradeSystemList) and
        not isinstance(a_list, abc_grading_objects.GradebookColumnList) and
        not isinstance(a_list, abc_grading_objects.GradeEntryList) and
        not isinstance(a_list, abc_learning_objects.ObjectiveList)):
        a_list = [a_list]
    try:
        list_len = a_list.available()
    except AttributeError:
        list_len = len(a_list)
    if list_len > 0:
        paginated = paginate(list(a_list), request)

        #for item in a_list:
        results.update({
            'data': paginated
        })
        for index, item in enumerate(paginated['results']):
            # for questions, need to add in their status
            if (isinstance(item, abc_assessment_objects.Question) or
                (isinstance(item, dict) and
                'Question' in item['type'])):
                if isinstance(item, dict):
                    item_id = Id(item['id'])
                else:
                    item_id = item.ident
                status = get_question_status(bank, section, item_id)
                # item_json.update(status)
                results['data']['results'][index].update(status)

            # results['data'].append(item_json)

        root_url_base = append_slash(
            request.build_absolute_uri().split('?')[0].replace('/query', ''))
        root_url_offered_or_taken = append_slash(
            request.build_absolute_uri().split('?page')[0])

        #for item in serialized_data['results']:
        for index, item in enumerate(paginated['results']):
            item_id = item['id']
            # make assessment offerings point two levels back, to just
            # <bank_id>/offerings/<offering_id>
            if (isinstance(item, abc_assessment_objects.AssessmentOffered) or
                    item['type'] == 'AssessmentOffered'):
                results['data']['results'][index]['_link'] = root_url_offered_or_taken + \
                                                             '../../../assessmentsoffered/' + \
                                                             my_unquote(item_id) + '/'
            elif (isinstance(item, abc_assessment_objects.AssessmentTaken) or
                  item['type'] == 'AssessmentTaken'):
                results['data']['results'][index]['_link'] = root_url_offered_or_taken + \
                                                             '../../../assessmentstaken/' + \
                                                             my_unquote(item_id) + '/'
            elif ((isinstance(item, abc_repository_objects.Asset) or
                    item['type'] == 'Asset') and
                    '/compositions/' in root_url_base):
                results['data']['results'][index]['_link'] = root_url_base + '../../../assets/' + \
                                                             my_unquote(item_id) + '/'
            elif ((isinstance(item, abc_grading_objects.GradeEntry) or
                    item['type'] == 'GradeEntry') and
                    '/columns/' in root_url_base):
                results['data']['results'][index]['_link'] = '{0}../../../entries/{1}/'.format(root_url_base,
                                                                                               my_unquote(item_id))
            else:
                results['data']['results'][index]['_link'] = root_url_base + my_unquote(item_id) + '/'
    else:
        results['data'] = {'count': 0, 'next': None, 'results': [], 'previous': None}
    return results

def get_data_from_request(request):
    """
    Because data might be in bad JSON form, might be in a string...
    need to return an object, always
    """
    try:
        try:
            if len(request.POST) > 0:
                if '_content_type' in request.POST:
                    data = request.DATA
                else:
                    data = request.POST
            else:
                body = request.body
                try:
                    # total hack...not sure why sometimes a request with
                    # no files throws ParseError on request.FILES
                    files = request.FILES
                except:
                    files = ''
                if len(body) > 0 and len(files) == 0:
                    data = body
                    if data == '':
                        raise Exception
                    else:
                        try:
                            data = json.loads(data)
                        except:
                            data = re.sub(r"([^\\])'", r'\1"', data)  # replace all non-escaped single quotes with double quote, to make JSON compatible
                        # data = data.replace("'", '"')
                else:
                    data = request.DATA
        except:
            data = request.DATA
    except:
        raise InvalidArgument()

    if isinstance(data, basestring):
        try:
            data = json.loads(data)

            if (not isinstance(data, dict) and
                not isinstance(data, list)):
                raise InvalidArgument()
        except:
            raise InvalidArgument()

    if len(data) == 0:
        data = request.GET

    if isinstance(data, QueryDict):
        data = deepcopy(data)

    if len(request.FILES) > 0:
        data['files'] = request.FILES  # yes, overwrite whatever is there...

    # unpack any nested objects
    if (isinstance(data, dict) or
        isinstance(data, QueryDict)):
        for key, val in data.iteritems():
            if isinstance(val, basestring):
                try:
                    data[key] = json.loads(val)
                except:
                    pass

    return data

def get_session_data(request, item_type):
    # get a manager
    try:
        if item_type in request.session:
            return pickle.loads(str(request.session[item_type]))
        else:
            return None
    except Exception as ex:
        log_error('utilities.get_session_data()', ex)

def handle_exceptions(ex):
    log_error(traceback.format_exc(10), ex)
    if isinstance(ex, PermissionDenied):
        raise exceptions.AuthenticationFailed('Permission denied.')
    elif isinstance(ex, InvalidArgument):
        if len(ex.args) == 0:
            raise exceptions.APIException('Poorly formatted input data.')
        else:
            raise exceptions.APIException(ex.args)
    # elif isinstance(ex, KeyError):
    #     raise exceptions.APIException(ex.args)
    elif isinstance(ex, NotFound):
        raise exceptions.APIException('Object not found.')
    elif isinstance(ex, InvalidId):
        raise exceptions.APIException('Invalid ID.')
    elif isinstance(ex, NoAccess):
        raise exceptions.APIException('You cannot edit those fields.')
    elif isinstance(ex, Unsupported):
        raise exceptions.APIException('That is an unsupported genus or record type.')
    elif isinstance(ex, exceptions.NotAcceptable):
        raise exceptions.NotAcceptable(ex.args)
    elif isinstance(ex, IllegalState):
        if len(ex.args) == 0:
            raise exceptions.APIException('Illegal state: you cannot do that because '
                                          'system conditions have changed. For example, '
                                          'the assessment has already been taken, or you '
                                          'have exceeded the number of allowed attempts.')
        else:
            raise exceptions.APIException(ex.args)
    else:
        raise exceptions.APIException(ex.args)

def id_generator(size=8, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for x in range(size))

def log_error(module, ex):
    import logging
    template = "An exception of type {0} occurred in {1}. Arguments:\n{2!r}"
    message = template.format(type(ex).__name__, module, ex.args)
    logging.info(message)
    return message

def manage_lti_headers(request):
    if ('HTTP_LTI_USER_ID' in request.META and
        'HTTP_LTI_TOOL_CONSUMER_INSTANCE_GUID' in request.META and
        'HTTP_LTI_USER_ROLE' in request.META and
        'HTTP_LTI_BANK' in request.META):
        store_lti_user(request)

def my_unquote(str):
    if '%40' in str:
        return unquote(str)
    else:
        return str

def paginate(data, request, items_per_page=10):
    # http://www.django-rest-framework.org/api-guide/pagination
    try:
        page_num = request.QUERY_PARAMS.get('page')
    except (AttributeError, KeyError):
        page_num = 'all'
    if page_num == 'all':
        items_per_page = len(data)
        page_num = 1
    paginator = Paginator(data, items_per_page)
    try:
        page = paginator.page(page_num)
    except PageNotAnInteger:
        page = paginator.page(1)
    except EmptyPage:
        page = paginator.page(paginator.num_pages)

    serializer = DLPaginationSerializer(instance=page, context={'request': request})
    # serializer = PaginationSerializer(instance=page, context={'request': request})

    return serializer.data

def set_form_basics(form, data):
    if 'displayName' in data:
        if isinstance(data['displayName'], basestring):
            form.display_name = data['displayName']
        elif isinstance(data['displayName'], dict):
            form.display_name = data['displayName']['text']
        else:
            form.display_name = str(data['displayName'])

    if 'description' in data:
        if isinstance(data['description'], basestring):
            form.description = data['description']
        elif isinstance(data['description'], dict):
            form.description = data['description']['text']
        else:
            form.description = str(data['description'])

    if 'genusTypeId' in data:
        form.set_genus_type(Type(data['genusTypeId']))

    return form

def set_session_data(request, item_type, data):
    request.session[item_type] = pickle.dumps(data)
    request.session.modified = True

def set_user(request):
    """
    Users can either be authenticated via session or RESTful API
    with HTTP Signature. DLKit only handles users who are
    authenticated via sessions, so we need to create a session
    for remote users who are authenticated via HTTP Signature.
    Session-authenticated users just need to pass through.
    HTTP Signature users need to have a session created.
    * NOT sure this is the best way to do it, but currently
        seems like the only way without heavy modification of DLKit

    Also check for LTI Headers. If they are present, store the
    user data / role / GUID in the LTI table.
    """
    from django.contrib.auth import authenticate, login, logout
    from dlkit.authz_adapter.osid.osid_errors import PermissionDenied
    username = request.META.get('HTTP_X_API_PROXY', request.user.username)

    if username == request.user.username:
        # User is authenticated via Django session
        # pass them into the proxy
        # still need to check for LTI headers
        manage_lti_headers(request)
    else:
        # some app is making a request via the RESTful API
        # log in this user and clear out all other users
        logout(request)
        # create the proxied user as a student, if they do not exist
        try:
            User.objects.get(username=username)
        except User.DoesNotExist:
            User.objects.create_user(username)

        remote_user = authenticate(remote_user=username)
        if remote_user is not None:
            # if remote_user.is_active and remote_user.is_staff:
            if remote_user.is_active:  # kind of weak...ideally would check this against each bank authz...for Touchstone, will always be True
                manage_lti_headers(request)
                login(request, remote_user)
            else:
                raise PermissionDenied()
        else:
            raise PermissionDenied()

def strip_object_ids(obj):
    """
    Recursively strip out the _id attribute from Mongo...replace it with 'id' = str(_id)
    Otherwise it breaks json.dumps()
    """
    results = {}
    for key, value in obj.iteritems():
        if isinstance(value, list):
            results[key] = []
            for ele in value:
                if isinstance(ele, dict):
                    results[key].append(strip_object_ids(ele))
                else:
                    results[key].append(ele)
        elif isinstance(value, dict):
            results[key] = strip_object_ids(value)
        else:
            if key == '_id':
                results['id'] = str(value)
            else:
                results[key] = value
    return results


def update_links(request, obj):
    """add links for browsable API"""
    def uri(term):
        return build_safe_uri(request) + term + '/'

    obj.update({
        '_links': {
            'self': build_safe_uri(request)
        }
    })

    if obj['type'] == 'Bank':  # assessmentBank
        obj['_links'].update({
            'items': uri('items')
        })
    elif obj['type'] == 'Item':  # assessmentItem
        obj['_links'].update({
            'answers': uri('answers'),
            'edxml': uri('edxml'),
            'files': uri('files'),
            'question': uri('question')
        })
    elif obj['type'] == 'Composition':  # repositoryComposition
        obj['_links'].update({
            'assets': uri('assets')
        })
    elif obj['type'] == 'Repository':  # repositoryRepository
        obj['_links'].update({
            'assets': uri('assets'),
            'compositions': uri('compositions')
        })
    elif obj['type'] == 'Gradebook':  # gradingGradebook
        obj['_links'].update({
            'gradeSystems': uri('gradesystems'),
            'gradebookColumns': uri('columns')
        })
    elif obj['type'] == 'GradebookColumn':  # gradebookColumn
        obj['_links'].update({
            'entries': uri('entries'),
            'summary': uri('summary')
        })

def upload_class(path, domain_repo, user):
    """use DysonX to parse and upload the class"""
    request = TestRequest(username=user.username)

    if not settings.TEST and settings.MEDIA_ROOT not in path:
        if '/' != path[0]:
            path = '/' + path
        path = ABS_PATH + path
    path = clean_up_path(path)
    dyson = DysonXUtil(request=request)
    return dyson.vacuum(path, domain_repo=domain_repo, user=user)

def verify_at_least_one_key_present(_data, _keys_list):
    """
    at least one of the keys is present
    """
    present = False

    for key in _keys_list:
        if key in _data:
            present = True

    if not present:
        raise KeyError('At least one of the following must be passed in: ' + json.dumps(_keys_list))


def verify_keys_present(my_dict, list_of_keys):
    if not isinstance(list_of_keys, list):
        list_of_keys = [list_of_keys]
    for key in list_of_keys:
        if key not in my_dict:
            raise KeyError('"' + key + '" required in input parameters but not provided.')


def verify_min_length(my_dict, list_of_keys, expected_len):
    for key in list_of_keys:
        if not isinstance(my_dict[key], list):
            raise TypeError('"' + key + '" is not a list.')
        else:
            if len(my_dict[key]) < int(expected_len):
                raise IntegrityError('"' + key + '" is shorter than ' + str(expected_len) + '.')
