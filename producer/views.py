import zipfile
import cStringIO

from django.conf import settings
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.http import Http404, HttpResponse
from rest_framework.renderers import JSONRenderer, BrowsableAPIRenderer
from rest_framework.permissions import AllowAny

from dlkit_django.errors import *

from bs4 import BeautifulSoup

from utilities.assessment import *
from utilities import general as gutils
from .types import *
from utilities import resource as resutils

# https://stackoverflow.com/questions/20424521/override-jsonserializer-on-django-rest-framework/20426493#20426493
class DLJSONRenderer(JSONRenderer):
    def render(self, data, accepted_media_type=None, renderer_context=None):
        data = gutils.clean_up_dl_objects(data)
        return super(DLJSONRenderer, self).render(data,
                                                  accepted_media_type,
                                                  renderer_context)


class ProducerAPIViews(gutils.DLKitSessionsManager):
    """Set up the managers"""
    def initial(self, request, *args, **kwargs):
        """set up the managers"""
        super(ProducerAPIViews, self).initial(request, *args, **kwargs)
        gutils.activate_managers(request)
        self.am = gutils.get_session_data(request, 'am')
        self.cm = gutils.get_session_data(request, 'cm')
        self.gm = gutils.get_session_data(request, 'gm')
        self.lm = gutils.get_session_data(request, 'lm')
        self.rm = gutils.get_session_data(request, 'rm')
        try:
            self.data = gutils.get_data_from_request(request)
        except InvalidArgument as ex:
            gutils.handle_exceptions(ex)

    def finalize_response(self, request, response, *args, **kwargs):
        """save the updated managers"""
        try:
            gutils.set_session_data(request, 'am', self.am)
            gutils.set_session_data(request, 'cm', self.cm)
            gutils.set_session_data(request, 'gm', self.gm)
            gutils.set_session_data(request, 'lm', self.lm)
            gutils.set_session_data(request, 'rm', self.rm)
        except AttributeError:
            pass  # with an exception, the RM may not be set
        return super(ProducerAPIViews, self).finalize_response(request,
                                                               response,
                                                               *args,
                                                               **kwargs)


# http://www.django-rest-framework.org/tutorial/3-class-based-views
class AssessmentService(ProducerAPIViews):
    """
    List all available assessment services.
    api/v2/assessment/
    """

    def get(self, request, format=None):
        """
        List all available assessment services. For now, just 'banks'
        """
        try:
            set_user(request)
            activate_managers(request)
            data = {
                '_links' : {
                    'banks'         : build_safe_uri(request) + 'banks/',
                    'documentation' : build_safe_uri(request) + 'docs/',
                    'hierarchies'   : build_safe_uri(request) + 'hierarchies/',
                    'itemTypes'     : build_safe_uri(request) + 'types/items/',
                    'self'          : build_safe_uri(request)
                }
            }
            return Response(data)
        except PermissionDenied:
            raise exceptions.AuthenticationFailed('Permission denied. You do '
                                                  'not have rights to use this '
                                                  'service.')
        except Exception as ex:
            log_error('assessmentsv2.views.AssessmentService.get()', ex)
            raise Http404

class AssessmentBanksList(APIView):
    """
    List all available assessment banks.
    api/v2/assessment/banks/

    POST allows you to create a new assessment bank, requires two parameters:
      * name
      * description

    Note that for RESTful calls, you need to set the request header
    'content-type' to 'application/json'

    Example (note the use of double quotes!!):
      {"name" : "a new bank","description" : "this is a test"}
    """
    renderer_classes = (DLJSONRenderer,BrowsableAPIRenderer)

    def get(self, request, format=None):
        """
        List all available assessment banks
        """
        try:
            set_user(request)
            activate_managers(request)
            am = get_session_data(request, 'am')

            params = get_data_from_request(request)

            if len(params) == 0:
                assessment_banks = am.banks
            else:
                querier = am.get_bank_query()

                allowable_query_terms = ['display_name', 'description']
                if any(term in params for term in allowable_query_terms):
                    querier = config_osid_object_querier(querier, params)
                    assessment_banks = am.get_banks_by_query(querier)
                else:
                    assessment_banks = am.banks

            banks = extract_items(request, assessment_banks)
            set_session_data(request, 'am', am)
            return Response(banks)
        except PermissionDenied:
            raise exceptions.AuthenticationFailed('Permission denied. You do not have '
                                                  'rights to view assessment '
                                                  'banks.')
        except Exception as ex:
            log_error('assessmentsv2.views.AssessmentBanksList.get()', ex)
            raise Http404

    def post(self, request, format=None):
        """
        Create a new assessment bank, if authorized
        Create a new group in IS&T Membership service

        """
        try:
            set_user(request)
            activate_managers(request)
            am = get_session_data(request, 'am')


            data = get_data_from_request(request)

            if 'color' in data:
                form = am.get_bank_form_for_create([COLOR_BANK_RECORD_TYPE])
                hex_code = str(data['color'].replace('0x', ''))
                form.set_color_coordinate(RGBColorCoordinate(hex_code))
            else:
                form = am.get_bank_form_for_create([])

            # should work for either a form or a json object
            form.display_name = data['name']
            form.description = data['description']


            new_bank = convert_dl_object(am.create_bank(form))

            # membership.create_group(new_bank['displayName']['text'],
            #                         new_bank['id'])

            set_session_data(request, 'am', am)
            return Response(new_bank)
        except PermissionDenied:
            raise exceptions.AuthenticationFailed('Permission denied. You do not '
                                                  'have rights to create new '
                                                  'assessment banks.')
        except InvalidArgument:
            raise exceptions.APIException('Poorly formatted input data.')
        except Exception as ex:
            log_error('assessmentsv2.views.AssessmentBanksList.post()', ex)
            raise Http404

class AssessmentBanksDetail(APIView):
    """
    Shows details for a specific assessment bank.
    api/v2/assessment/banks/<bank_id>/

    GET, PUT, DELETE
    PUT will update the assessment bank. Only changed attributes need to be sent.
    DELETE will remove the assessment bank.

    Note that for RESTful calls, you need to set the request header
    'content-type' to 'application/json'

    Example (note the use of double quotes!!):
       {"name" : "a new bank"}
    """
    renderer_classes = (DLJSONRenderer,BrowsableAPIRenderer)

    def get(self, request, bank_id, format=None):
        try:
            set_user(request)
            activate_managers(request)
            am = get_session_data(request, 'am')
            assessment_bank = am.get_bank(clean_id(bank_id))
            bank = convert_dl_object(assessment_bank)
            bank.update({
                '_links': {
                    'assessments' : build_safe_uri(request) + 'assessments/',
                    'items'       : build_safe_uri(request) + 'items/',
                    'self'        : build_safe_uri(request)
                }
            })
            set_session_data(request, 'am', am)
            return Response(bank)
        except PermissionDenied:
            raise exceptions.AuthenticationFailed('Permission denied. You do '
                                                  'not have rights to view '
                                                  "this bank's details.")
        except NotFound:
            raise exceptions.APIException('Bank not found.')
        except Exception as ex:
            log_error('assessmentsv2.views.AssessmentBanksDetail.get()', ex)
            raise Http404

    def put(self, request, bank_id, format=None):
        try:
            set_user(request)
            activate_managers(request)
            am = get_session_data(request, 'am')
            form = am.get_bank_form_for_update(clean_id(bank_id))

            data = get_data_from_request(request)

            # should work for a form or json data
            if 'name' in data:
                form.display_name = data['name']
            if 'description' in data:
                form.description = data['description']

            if 'color' in data:
                hex_code = str(data['color'].replace('0x', ''))
                form.set_color_coordinate(RGBColorCoordinate(hexstr=hex_code))

            updated_bank = am.update_bank(form)
            bank = convert_dl_object(updated_bank)
            bank.update({
                '_links': {
                    'assessments' : build_safe_uri(request) + 'assessments/',
                    'items'       : build_safe_uri(request) + 'items/',
                    'self'        : build_safe_uri(request)
                }
            })
            set_session_data(request, 'am', am)
            return Response(bank)
        except PermissionDenied:
            raise exceptions.AuthenticationFailed('Permission denied. You do not '
                                                  'have rights to edit this bank.')
        except InvalidArgument:
            raise exceptions.APIException('Poorly formatted input data.')
        except Exception as ex:
            log_error('assessmentsv2.views.AssessmentBanksDetail.put()', ex)
            raise Http404

    def delete(self, request, bank_id, format=None):
        try:
            set_user(request)
            activate_managers(request)
            am = get_session_data(request, 'am')
            data = am.delete_bank(clean_id(bank_id))
            set_session_data(request, 'am', am)
            return Response(data)
        except PermissionDenied:
            raise exceptions.AuthenticationFailed('Permission denied. You do not have '
                                                  'rights to delete this bank.')
        except IllegalState:
            raise exceptions.NotAcceptable('Bank is not empty. Please delete '
                                                  'its contents first.')
        except Exception as ex:
            log_error('assessmentsv2.views.AssessmentBanksDetail.delete()', ex)
            raise Http404

class AssessmentsList(APIView):
    """
    Get a list of all assessments in the specified bank
    api/v2/assessment/banks/<bank_id>/assessments/

    GET, POST
    POST creates a new assessment

    Note that "times" like duration and startTime for offerings should be
    input as JSON objects when using the RESTful API. Example:
        "startTime":{"year":2015,"month":1,"day":15}

    In this UI, you can put an object into the textarea below, and it will work fine.

    Note that duration only returns days / minutes / seconds

    Note that for RESTful calls, you need to set the request header
    'content-type' to 'application/json'

    POST example (note the use of double quotes!!):
       {"name" : "an assessment","description" : "this is a hard pset","itemIds" : ["assessment.Item%3A539ef3a3ea061a0cb4fba0a3%40birdland.mit.edu"]}
    """
    renderer_classes = (DLJSONRenderer,BrowsableAPIRenderer)

    def get(self, request, bank_id, format=None):
        try:
            set_user(request)
            activate_managers(request)
            am = get_session_data(request, 'am')
            assessment_bank = am.get_bank(clean_id(bank_id))
            params = get_data_from_request(request)
            if len(params) == 0:
                assessments = assessment_bank.get_assessments()
            else:
                allowed_queries = ['display_name', 'description']
                if any(term in params for term in allowed_queries):
                    querier = assessment_bank.get_assessment_query()

                    querier = config_osid_object_querier(querier, params)

                    assessments = assessment_bank.get_assessments_by_query(querier)
                else:
                    assessments = assessment_bank.get_assessments()

            data = extract_items(request, assessments)
            set_session_data(request, 'am', am)
            return Response(data)
        except PermissionDenied:
            raise exceptions.AuthenticationFailed('Permission denied. You do not '
                                                  'have rights to view assessments '
                                                  'in this bank.')
        except Exception as ex:
            log_error('assessmentsv2.views.AssessmentsList.get()', ex)
            raise Http404

    def post(self, request, bank_id, format=None):
        try:
            bank = new_assessment = None
            set_user(request)
            activate_managers(request)
            am = get_session_data(request, 'am')

            data = get_data_from_request(request)

            bank = am.get_bank(clean_id(bank_id))
            form = bank.get_assessment_form_for_create([])
            form.display_name = data['name']
            form.description = data['description']
            new_assessment = bank.create_assessment(form)

            # if item IDs are included in the assessment, append them.
            if 'itemIds' in data:
                if isinstance(data, QueryDict):
                    items = data.getlist('itemIds')
                elif isinstance(data['itemIds'], basestring):
                    items = json.loads(data['itemIds'])
                else:
                    items = data['itemIds']

                if not isinstance(items, list):
                    try:
                        clean_id(items)  # use this as proxy to test if a valid OSID ID
                        items = [items]
                    except:
                        raise InvalidArgument

                for item_id in items:
                    try:
                        bank.add_item(new_assessment.ident, clean_id(item_id))
                    except:
                        raise NotFound()

            # attach any assessment offerings or taken to the new object
            if 'offerings' in data:
                set_assessment_offerings(bank,
                                         data['offerings'],
                                         new_assessment.ident)
            #
            # if 'taken' in data:
            #     for taken in data['taken']:
            #         taken_form = assessment_bank.get_assessment_taken_form_for_create()
            #         taken_form.taker = taken['taker']
            #         assessment_bank.create_assessment_taken(taken_form)

            full_assessment = bank.get_assessment(new_assessment.ident)
            data = convert_dl_object(full_assessment)
            set_session_data(request, 'am', am)
            return Response(data)
        except PermissionDenied:
            if bank and new_assessment:
                clean_up_post(bank, new_assessment)
            raise exceptions.AuthenticationFailed('Permission denied. You do not '
                                                  'have rights to create new '
                                                  'assessments in this bank.')
        except NotFound:
            if bank and new_assessment:
                clean_up_post(bank, new_assessment)
            raise exceptions.APIException('Item ID(s) or bank were not found.')
        except InvalidArgument:
            if bank and new_assessment:
                clean_up_post(bank, new_assessment)
            raise exceptions.APIException('Poorly formatted input data.')
        except Exception as ex:
            if bank and new_assessment:
                clean_up_post(bank, new_assessment)
            log_error('assessmentsv2.views.AssessmentsList.post()', ex)
            raise Http404


class ItemsList(APIView):
    """
    Return list of items in the given assessment bank. Make sure to embed
    the question and answers in the JSON.
    api/v2/assessment/banks/<bank_id>/items/

    GET, POST
    POST creates a new item

    Note that for RESTful calls, you need to set the request header
    'content-type' to 'application/json'

    Example (note the use of double quotes!!):
       This UI: {"name" : "an assessment item","description" : "this is a hard quiz problem","question":{"type":"question-record-type%3Aresponse-string%40ODL.MIT.EDU","questionString":"Where am I?"},"answers":[{"type":"answer-record-type%3Aresponse-string%40ODL.MIT.EDU","responseString":"Here"}]}
   """
    renderer_classes = (DLJSONRenderer,BrowsableAPIRenderer)

    def get(self, request, bank_id, format=None):
        try:
            set_user(request)
            activate_managers(request)

            params = get_data_from_request(request)

            am = get_session_data(request, 'am')
            assessment_bank = am.get_bank(clean_id(bank_id))

            if len(params) == 0 or (len(params) == 1 and params.keys()[0] == 'files'):
                items = assessment_bank.get_items()
            else:
                querier = assessment_bank.get_item_query()

                allowable_query_terms = ['max_difficulty', 'min_difficulty',
                                         'max_discrimination', 'min_discrimination',
                                         'display_name', 'learning_objective',
                                         'description']
                if any(term in params for term in allowable_query_terms):
                    querier = config_item_querier(querier, params)

                    items = assessment_bank.get_items_by_query(querier)
                else:
                    items = assessment_bank.get_items()

            data = extract_items(request, items)
            if 'files' in params:
                for item in data['data']['results']:
                    dlkit_item = assessment_bank.get_item(clean_id(item['id']))

                    if 'fileIds' in item:
                        item['files'] = dlkit_item.get_files()
                    if item['question'] and 'fileIds' in item['question']:
                        item['question']['files'] = dlkit_item.get_question().get_files()

            set_session_data(request, 'am', am)
            return Response(data)
        except PermissionDenied:
            raise exceptions.AuthenticationFailed('Permission denied. You do not '
                                                  'have rights to view items in '
                                                  'this bank.')
        except IntegrityError as ex:
            raise exceptions.APIException('max_' + ex.args[0] + ' cannot be less than min_' + ex.args[0])
        except Exception as ex:
            log_error('assessmentsv2.views.ItemsList.get()', ex)
            raise Http404

    def post(self, request, bank_id, format=None):
        try:
            bank = new_item = None
            set_user(request)
            activate_managers(request)
            am = get_session_data(request, 'am')
            data = get_data_from_request(request)
            expected = ['name', 'description']
            verify_keys_present(data, expected)

            bank = am.get_bank(clean_id(bank_id))
            new_item = create_new_item(bank, data)
            # create questions and answers if they are part of the
            # input data. There must be a better way to figure out
            # which attributes I should set, given the
            # question type?
            if 'question' in data:
                question = data['question']
                if isinstance(question, basestring):
                    question = json.loads(question)
                q_type = Type(question['type'])
                qfc = bank.get_question_form_for_create(item_id=new_item.ident,
                                                        question_record_types=[q_type])
                qfc = update_question_form(request, question, qfc, create=True)

                if 'genus' in question:
                    qfc.genus_type = Type(question['genus'])

                if ('fileIds' in new_item.object_map and
                    len(new_item.object_map['fileIds'].keys()) > 0):
                    # add these files to the question, too
                    file_ids = new_item.object_map['fileIds']
                    qfc = add_file_ids_to_form(qfc, file_ids)

                new_question = bank.create_question(qfc)

            if 'answers' in data:
                answers = data['answers']
                if isinstance(answers, basestring):
                    answers = json.loads(answers)
                for answer in answers:
                    a_types = get_answer_records(answer)

                    afc = bank.get_answer_form_for_create(new_item.ident,
                                                          a_types)

                    if 'multi-choice' in answer['type']:
                        # because multiple choice answers need to match to
                        # the actual MC3 ChoiceIds, NOT the index passed
                        # in by the consumer.
                        if not new_question:
                            raise NullArgument('Question')
                        afc = update_answer_form(answer, afc, new_question)
                    else:
                        afc = update_answer_form(answer, afc)

                    afc = set_answer_form_genus_and_feedback(answer, afc)
                    new_answer = bank.create_answer(afc)

            full_item = bank.get_item(new_item.ident)
            data = convert_dl_object(full_item)
            set_session_data(request, 'am', am)
            return Response(data)
        except KeyError as ex:
            if bank and new_item:
                clean_up_post(bank, new_item)
            raise exceptions.APIException(ex.args[0])
        except IntegrityError as ex:
            if bank and new_item:
                clean_up_post(bank, new_item)
            raise exceptions.APIException(ex.args[0])
        except PermissionDenied:
            if bank and new_item:
                clean_up_post(bank, new_item)
            raise exceptions.AuthenticationFailed('Permission denied. You do not '
                                                  'have rights to create items '
                                                  'in this bank.')
        except Unsupported:
            if bank and new_item:
                clean_up_post(bank, new_item)
            raise exceptions.APIException('Unsupported question or answer type.')
        except InvalidArgument:
            if bank and new_item:
                clean_up_post(bank, new_item)
            raise exceptions.APIException('Poorly formatted input data.')
        except NullArgument as ex:
            if bank and new_item:
                clean_up_post(bank, new_item)
            raise exceptions.APIException(str(ex) + ' attribute(s) required for Ortho-3D items.')
        except Exception as ex:
            if bank and new_item:
                clean_up_post(bank, new_item)
            log_error('assessmentsv2.views.ItemsList.post()', ex)
            raise Http404


class AssessmentDetails(APIView):
    """
    Get assessment details for the given bank
    api/v2/assessment/banks/<bank_id>/assessments/<assessment_id>/

    GET, PUT, DELETE
    PUT to modify an existing assessment. Include only the changed parameters.
    DELETE to remove from the repository.

    Note that for RESTful calls, you need to set the request header
    'content-type' to 'application/json'

    Example (note the use of double quotes!!):
       {"name" : "an updated assessment"}
    """
    renderer_classes = (DLJSONRenderer,BrowsableAPIRenderer)

    def get(self, request, bank_id, sub_id, format=None):
        try:
            set_user(request)
            activate_managers(request)
            am = get_session_data(request, 'am')
            bank = am.get_bank(clean_id(bank_id))
            data = convert_dl_object(bank.get_assessment(clean_id(sub_id)))
            data.update({
                '_links': {
                    'items'     : build_safe_uri(request) + 'items/',
                    'offerings' : build_safe_uri(request) + 'assessmentsoffered/',
                    'self'      : build_safe_uri(request),
                    'takens'    : build_safe_uri(request) + 'assessmentstaken/'
                }
            })
            set_session_data(request, 'am', am)
            return Response(data)
        except PermissionDenied:
            raise exceptions.AuthenticationFailed('Permission denied. You do not '
                                                  'have rights to view assessment '
                                                  'details in this bank.')
        except NotFound:
            raise exceptions.APIException('Assessment or bank not found.')
        except Exception as ex:
            log_error('assessmentsv2.views.AssessmentDetails.get()', ex)
            raise Http404

    def put(self, request, bank_id, sub_id, format=None):
        try:
            set_user(request)
            activate_managers(request)
            am = get_session_data(request, 'am')
            bank = am.get_bank(clean_id(bank_id))
            form = bank.get_assessment_form_for_update(clean_id(sub_id))

            data = get_data_from_request(request)

            # should work for either a form or json
            if 'name' in data:
                form.display_name = data['name']
            if 'description' in data:
                form.description = data['description']

            updated_assessment = bank.update_assessment(form)

            full_assessment = bank.get_assessment(updated_assessment.ident)
            data = convert_dl_object(full_assessment)

            set_session_data(request, 'am', am)
            return Response(data)
        except PermissionDenied:
            raise exceptions.AuthenticationFailed('Permission denied. You do not '
                                                  'have rights to edit assessments '
                                                  'in this bank.')
        except InvalidArgument:
            raise exceptions.APIException('Poorly formatted input data.')
        except Exception as ex:
            log_error('assessmentsv2.views.AssessmentDetails.put()', ex)
            raise Http404

    def delete(self, request, bank_id, sub_id, format=None):
        try:
            set_user(request)
            activate_managers(request)

            params = get_data_from_request(request)

            am = get_session_data(request, 'am')
            bank = am.get_bank(clean_id(bank_id))
            try:
                data = bank.delete_assessment(clean_id(sub_id))
            except IllegalState:
                if 'force' in params:
                    for offered in bank.get_assessments_offered_for_assessment(clean_id(sub_id)):
                        for taken in bank.get_assessments_taken_for_assessment_offered(offered.ident):
                            bank.delete_assessment_taken(taken.ident)
                        bank.delete_assessment_offered(offered.ident)
                    data = bank.delete_assessment(clean_id(sub_id))
                else:
                    raise IllegalState
            set_session_data(request, 'am', am)
            return Response(data)
        except PermissionDenied:
            raise exceptions.AuthenticationFailed('Permission denied. You do not '
                                                  'have rights to delete assessments '
                                                  'in this bank.')
        except IllegalState:
            raise exceptions.NotAcceptable('Assessment still has AssessmentOffered. ' +
                                           'Delete the offerings first.')
        except Exception as ex:
            log_error('assessmentsv2.views.AssessmentDetails.delete()', ex)
            raise Http404

class ItemDetails(APIView):
    """
    Get item details for the given bank
    api/v2/assessment/banks/<bank_id>/items/<item_id>/

    GET, PUT, DELETE
    PUT to modify an existing item. Include only the changed parameters.
    DELETE to remove from the repository.

    Note that for RESTful calls, you need to set the request header
    'content-type' to 'application/json'

    Example (note the use of double quotes!!):
       {"name" : "an updated item"}
    """
    renderer_classes = (DLJSONRenderer,BrowsableAPIRenderer)

    def get(self, request, sub_id, bank_id=None, format=None):
        try:
            set_user(request)
            activate_managers(request)
            am = get_session_data(request, 'am')
            bank = get_object_bank(am, sub_id, object_type='item', bank_id=bank_id)

            item = bank.get_item(clean_id(sub_id))
            data = convert_dl_object(item)

            root_url_base = request.build_absolute_uri().split('?')[0].replace('/query','')
            data.update({
                '_links': {
                    'self'        : build_safe_uri(request),
                }
            })
            if not 'assessment.Assessment' in root_url_base:
                # because for assessmentItemDetails, it points here...but
                # we don't want to link to the same place.
                data['_links'].update({
                    'answers'     : build_safe_uri(request) + 'answers/',
                    'edxml'       : build_safe_uri(request) + 'edxml/',
                    'files'       : build_safe_uri(request) + 'files/',
                    'question'    : build_safe_uri(request) + 'question/'
                })

            if 'fileIds' in data:
                data['files'] = item.get_files()
            if data['question'] and 'fileIds' in data['question']:
                data['question']['files'] = item.get_question().get_files()

            set_session_data(request, 'am', am)
            return Response(data)
        except PermissionDenied:
            raise exceptions.AuthenticationFailed('Permission denied. You do not '
                                                  'have rights to view item '
                                                  'details in this bank.')
        except NotFound:
            raise exceptions.APIException('Item or bank not found.')
        except Exception as ex:
            log_error('assessmentsv2.views.ItemDetails.get()', ex)
            raise Http404

    def put(self, request, sub_id, bank_id=None, format=None):
        try:
            set_user(request)
            activate_managers(request)
            am = get_session_data(request, 'am')
            bank = get_object_bank(am, sub_id, object_type='item', bank_id=bank_id)

            data = get_data_from_request(request)

            if any(attr in data for attr in ['name', 'description', 'learningObjectiveIds',
                                             'attempts', 'markdown', 'rerandomize', 'showanswer',
                                             'weight', 'difficulty', 'discrimination']):
                form = bank.get_item_form_for_update(clean_id(sub_id))

                if 'name' in data:
                    form.display_name = data['name']
                if 'description' in data:
                    form.description = data['description']

                if 'learningObjectiveIds' in data:
                    form = set_item_learning_objectives(data, form)

                # update the item before the questions / answers,
                # because otherwise the old form will over-write the
                # new question / answer data

                # for edX items, update any metadata passed in
                if 'type' not in data:
                    if len(form._my_map['recordTypeIds']) > 0:
                        data['type'] = form._my_map['recordTypeIds'][0]
                    else:
                        data['type'] = ''

                form = update_item_metadata(data, form)

                updated_item = bank.update_item(form)
            else:
                updated_item = bank.get_item(clean_id(sub_id))

            if 'question' in data:
                question = data['question']
                existing_question = updated_item.get_question()
                q_id = existing_question.ident

                if 'type' not in question:
                    question['type'] = existing_question.object_map['recordTypeIds'][0]

                qfu = bank.get_question_form_for_update(q_id)
                qfu = update_question_form(request, question, qfu)
                updated_question = bank.update_question(qfu)

            if 'answers' in data:
                for answer in data['answers']:
                    if 'id' in answer:
                        a_id = clean_id(answer['id'])
                        afu = bank.get_answer_form_for_update(a_id)
                        afu = update_answer_form(answer, afu)
                        bank.update_answer(afu)
                    else:
                        a_types = get_answer_records(answer)
                        afc = bank.get_answer_form_for_create(clean_id(sub_id),
                                                              a_types)
                        afc = set_answer_form_genus_and_feedback(answer, afc)
                        if 'multi-choice' in answer['type']:
                            # because multiple choice answers need to match to
                            # the actual MC3 ChoiceIds, NOT the index passed
                            # in by the consumer.
                            question = updated_item.get_question()
                            afc = update_answer_form(answer, afc, question)
                        else:
                            afc = update_answer_form(answer, afc)
                        bank.create_answer(afc)

            full_item = bank.get_item(clean_id(sub_id))

            data = convert_dl_object(full_item)
            set_session_data(request, 'am', am)
            return Response(data)
        except PermissionDenied:
            raise exceptions.AuthenticationFailed('Permission denied. You do not '
                                                  'have rights to edit item '
                                                  'details in this bank.')
        except Unsupported:
            raise exceptions.APIException('Unsupported question or answer type.')
        except InvalidArgument:
            raise exceptions.APIException('Poorly formatted input data.')
        except Exception as ex:
            log_error('assessmentsv2.views.ItemDetails.put()', ex)
            raise Http404

    def delete(self, request, sub_id, bank_id=None, format=None):
        try:
            set_user(request)
            activate_managers(request)
            am = get_session_data(request, 'am')
            bank = get_object_bank(am, sub_id, object_type='item', bank_id=bank_id)
            data = bank.delete_item(clean_id(sub_id))
            set_session_data(request, 'am', am)
            return Response(data)
        except PermissionDenied:
            raise exceptions.AuthenticationFailed('Permission denied. You do not '
                                                  'have rights to delete items '
                                                  'in this bank.')
        except IllegalState:
            raise exceptions.NotAcceptable('This Item is being used in one or more '
                                           'Assessments. Delink it first, before '
                                           'deleting it.')
        except Exception as ex:
            log_error('assessmentsv2.views.ItemDetails.delete()', ex)
            raise Http404

class SupportedItemTypes(APIView):
    """
    Return list of supported item types with ids
    api/v2/assessment/types/items/

    GET
    """
    renderer_classes = (DLJSONRenderer,BrowsableAPIRenderer)

    def get(self, request, format=None):
        try:
            # Until we have a flushed out type service, hardcode
            # the types to match the four known ones
            # from dlkit.mongo.assessment.records.types import QUESTION_RECORD_TYPES
            # results = []
            # for i_type, bean in QUESTION_RECORD_TYPES.iteritems():
            #     id = bean['namespace'] + ':' + bean['identifier'] + '@' + bean['authority']
            #     results.append({
            #         'displayName'   : {
            #             'text'  : bean['display_name']
            #         },
            #         'description'   : {
            #             'text'  : bean['description']
            #         },
            #         'id'            : quote(id)
            #     })
            results = supported_types()
            return Response(results)
        except PermissionDenied:
            raise exceptions.AuthenticationFailed('Permission denied. You do not '
                                                  'have rights to view item types.')
        except Exception as ex:
            log_error('assessmentsv2.views.SupportedItemTypes.get()', ex)
            raise Http404


class AssessmentItemsList(APIView):
    """
    Get or link items in an assessment
    api/v2/assessment/banks/<bank_id>/assessments/<assessment_id>/items/

    GET, POST
    GET to view currently linked items
    POST to link a new item (appended to the current list)

    Note that for RESTful calls, you need to set the request header
    'content-type' to 'application/json'

    Example (note the use of double quotes!!):
       {"itemIds" : ["assessment.Item%3A539ef3a3ea061a0cb4fba0a3%40birdland.mit.edu"]}
    """
    renderer_classes = (DLJSONRenderer,BrowsableAPIRenderer)

    def get(self, request, bank_id, sub_id, format=None):
        try:
            set_user(request)
            activate_managers(request)

            params = get_data_from_request(request)

            am = get_session_data(request, 'am')
            bank = am.get_bank(clean_id(bank_id))
            items = bank.get_assessment_items(clean_id(sub_id))
            data = extract_items(request, items)

            if 'files' in params:
                for item in data['data']['results']:
                    dlkit_item = bank.get_item(clean_id(item['id']))

                    if 'fileIds' in item:
                        item['files'] = dlkit_item.get_files()
                    if item['question'] and 'fileIds' in item['question']:
                        item['question']['files'] = dlkit_item.get_question().get_files()



            set_session_data(request, 'am', am)
            return Response(data)
        except PermissionDenied:
            raise exceptions.AuthenticationFailed('Permission denied. You do not '
                                                  'have rights to view assessment '
                                                  'items in this bank.')
        except NotFound:
            raise exceptions.APIException('Assessment or bank not found.')
        except Exception as ex:
            log_error('assessmentsv2.views.AssessmentItemsList.get()', ex)
            raise Http404

    def post(self, request, bank_id, sub_id, format=None):
        try:
            set_user(request)
            activate_managers(request)
            am = get_session_data(request, 'am')
            bank = am.get_bank(clean_id(bank_id))

            data = get_data_from_request(request)

            if 'itemIds' in data:
                if isinstance(data, QueryDict):
                    items = data.getlist('itemIds')
                elif isinstance(data['itemIds'], basestring):
                    items = json.loads(data['itemIds'])
                else:
                    items = data['itemIds']

                if not isinstance(items, list):
                    try:
                        clean_id(items)  # use this as proxy to test if a valid OSID ID
                        items = [items]
                    except:
                        raise InvalidArgument

                for item_id in items:
                    bank.add_item(clean_id(sub_id), clean_id(item_id))

            items = bank.get_assessment_items(clean_id(sub_id))
            data = extract_items(request, items)
            set_session_data(request, 'am', am)
            return Response(data)
        except PermissionDenied:
            raise exceptions.AuthenticationFailed('Permission denied. You do not '
                                                  'have rights to assign items to '
                                                  'assessments in this bank.')
        except InvalidArgument:
            raise exceptions.APIException('Poorly formatted input data.')
        except Exception as ex:
            log_error('assessmentsv2.views.AssessmentItemsList.post()', ex)
            raise Http404

    def put(self, request, bank_id, sub_id, format=None):
        """Use put to support full-replacement of the item list"""
        try:
            set_user(request)
            activate_managers(request)
            am = get_session_data(request, 'am')
            bank = am.get_bank(clean_id(bank_id))

            data = get_data_from_request(request)

            if 'itemIds' in data:
                # first clear out existing items
                for item in bank.get_assessment_items(clean_id(sub_id)):
                    bank.remove_item(clean_id(sub_id), item.ident)

                # now add the new ones
                if isinstance(data, QueryDict):
                    items = data.getlist('itemIds')
                elif isinstance(data['itemIds'], basestring):
                    items = json.loads(data['itemIds'])
                else:
                    items = data['itemIds']

                if not isinstance(items, list):
                    try:
                        clean_id(items)  # use this as proxy to test if a valid OSID ID
                        items = [items]
                    except:
                        raise InvalidArgument

                for item_id in items:
                    bank.add_item(clean_id(sub_id), clean_id(item_id))

            items = bank.get_assessment_items(clean_id(sub_id))
            data = extract_items(request, items)
            set_session_data(request, 'am', am)
            return UpdatedResponse(data)
        except PermissionDenied:
            raise exceptions.AuthenticationFailed('Permission denied. You do not '
                                                  'have rights to assign items to '
                                                  'assessments in this bank.')
        except InvalidArgument:
            raise exceptions.APIException('Poorly formatted input data.')
        except Exception as ex:
            log_error('assessmentsv2.views.AssessmentItemsList.post()', ex)
            raise Http404



class AssessmentHierarchiesRootChildDetails(APIView):
    """
    List the bank details for a child bank.
    api/v2/assessment/hierarchies/<bank_id>/children/<child_id>/

    DELETE allows you to remove a child bank.

    Note that for RESTful calls, you need to set the request header
    'content-type' to 'application/json'
    """
    renderer_classes = (DLJSONRenderer,BrowsableAPIRenderer)

    def delete(self, request, bank_id, child_id, format=None):
        """
        Remove bank as child bank
        """
        try:
            set_user(request)
            activate_managers(request)
            am = get_session_data(request, 'am')
            root_bank_ids = am.get_root_bank_ids()
            if clean_id(bank_id) in root_bank_ids:
                ## check that child exists
                children_ids = am.get_child_bank_ids(clean_id(bank_id))
                if clean_id(child_id) in children_ids:
                    am.remove_child_bank(clean_id(bank_id), clean_id(child_id))
                else:
                    raise exceptions.NotAcceptable('That child bank is not a child of the root.')
            else:
                raise exceptions.NotAcceptable('That bank is not a root.')
            set_session_data(request, 'am', am)
            return DeletedResponse()
        except PermissionDenied:
            raise exceptions.AuthenticationFailed('Permission denied. You do not have '
                                                  'rights to remove children assessment '
                                                  'banks.')
        except exceptions.NotAcceptable as ex:
            raise exceptions.NotAcceptable(*ex.args)
        except Exception as ex:
            log_error('assessmentsv2.views.AssessmentHierarchiesRootChildDetails.delete()', ex)
            raise Http404


    def get(self, request, bank_id, child_id, format=None):
        """
        List details of a child bank
        """
        try:
            set_user(request)
            activate_managers(request)
            am = get_session_data(request, 'am')
            root_bank_ids = am.get_root_bank_ids()
            if clean_id(bank_id) in root_bank_ids:
                children_ids = am.get_child_bank_ids(clean_id(bank_id))
                if clean_id(child_id) in children_ids:
                    bank = am.get_bank(clean_id(child_id))
                else:
                    raise exceptions.NotAcceptable('That child does not belong to this root.')
            else:
                raise exceptions.NotAcceptable('That bank is not a root.')
            set_session_data(request, 'am', am)

            data = bank.object_map
            data.update({
                '_links': {
                    'self'        : build_safe_uri(request),
                }
            })

            return Response(data)
        except PermissionDenied:
            raise exceptions.AuthenticationFailed('Permission denied. You do not have '
                                                  'rights to view children assessment '
                                                  'banks.')
        except exceptions.NotAcceptable as ex:
            raise exceptions.NotAcceptable(*ex.args)
        except Exception as ex:
            log_error('assessmentsv2.views.AssessmentHierarchiesRootChildDetails.get()', ex)
            raise Http404



class AssessmentHierarchiesRootChildrenList(APIView):
    """
    List the children for a root bank.
    api/v2/assessment/hierarchies/<bank_id>/children/

    POST allows you to add an existing bank as a child bank in
    the hierarchy.

    Note that for RESTful calls, you need to set the request header
    'content-type' to 'application/json'

    Example (note the use of double quotes!!):
      {"id": "assessment.Bank:54f9e39833bb7293e9da5b44@oki-dev.MIT.EDU"}

    """
    renderer_classes = (DLJSONRenderer,BrowsableAPIRenderer)


    def get(self, request, bank_id, format=None):
        """
        List children of a root bank
        """
        try:
            set_user(request)
            activate_managers(request)
            am = get_session_data(request, 'am')
            root_bank_ids = am.get_root_bank_ids()
            if clean_id(bank_id) in root_bank_ids:
                children = am.get_child_banks(clean_id(bank_id))
                data = extract_items(request, children)
            else:
                raise exceptions.NotAcceptable('That bank is not a root.')
            set_session_data(request, 'am', am)
            return Response(data)
        except PermissionDenied:
            raise exceptions.AuthenticationFailed('Permission denied. You do not have '
                                                  'rights to view children assessment '
                                                  'banks.')
        except exceptions.NotAcceptable as ex:
            raise exceptions.NotAcceptable(*ex.args)
        except Exception as ex:
            log_error('assessmentsv2.views.AssessmentHierarchiesRootChildrenList.get()', ex)
            raise Http404

    def post(self, request, bank_id, format=None):
        """
        add bank as child
        """
        try:
            set_user(request)
            activate_managers(request)
            am = get_session_data(request, 'am')

            data = get_data_from_request(request)
            verify_keys_present(data, 'childId')

            root_bank_ids = am.get_root_bank_ids()
            if clean_id(bank_id) in root_bank_ids:
                try:
                    child_bank = am.get_bank(clean_id(data['childId']))
                    am.add_child_bank(clean_id(bank_id), clean_id(data['childId']))
                except:
                    raise exceptions.NotAcceptable('The child bank does not exist.')
            else:
                raise exceptions.NotAcceptable('That bank is not a root.')
            set_session_data(request, 'am', am)
            return CreatedResponse()
        except PermissionDenied:
            raise exceptions.AuthenticationFailed('Permission denied. You do not have '
                                                  'rights to add children assessment '
                                                  'banks.')
        except exceptions.NotAcceptable as ex:
            raise exceptions.NotAcceptable(*ex.args)
        except KeyError as ex:
            raise exceptions.APIException(*ex.args)
        except Exception as ex:
            log_error('assessmentsv2.views.AssessmentHierarchiesRootChildrenList.post()', ex)
            raise Http404




class AssessmentHierarchiesRootDetails(APIView):
    """
    List the bank details for a root bank.
    api/v2/assessment/hierarchies/<bank_id>/

    DELETE allows you to remove a root bank.

    Note that for RESTful calls, you need to set the request header
    'content-type' to 'application/json'
    """
    renderer_classes = (DLJSONRenderer,BrowsableAPIRenderer)

    def delete(self, request, bank_id, format=None):
        """
        Remove bank as root bank
        """
        try:
            set_user(request)
            activate_managers(request)
            am = get_session_data(request, 'am')
            root_bank_ids = am.get_root_bank_ids()
            if clean_id(bank_id) in root_bank_ids:
                am.remove_root_bank(clean_id(bank_id))
            else:
                raise exceptions.NotAcceptable('That bank is not a root.')
            set_session_data(request, 'am', am)
            return DeletedResponse()
        except PermissionDenied:
            raise exceptions.AuthenticationFailed('Permission denied. You do not have '
                                                  'rights to remove root assessment '
                                                  'banks.')
        except exceptions.NotAcceptable:
            raise exceptions.NotAcceptable('That bank is not a root.')
        except Exception as ex:
            log_error('assessmentsv2.views.AssessmentHierarchiesRootDetails.delete()', ex)
            raise Http404


    def get(self, request, bank_id, format=None):
        """
        List details of a root bank
        """
        try:
            set_user(request)
            activate_managers(request)
            am = get_session_data(request, 'am')
            root_bank_ids = am.get_root_bank_ids()
            if clean_id(bank_id) in root_bank_ids:
                bank = am.get_bank(clean_id(bank_id))
            else:
                raise exceptions.NotAcceptable('That bank is not a root.')
            set_session_data(request, 'am', am)

            data = bank.object_map
            data.update({
                '_links': {
                    'children'    : build_safe_uri(request) + 'children/',
                    'self'        : build_safe_uri(request),
                }
            })

            return Response(data)
        except PermissionDenied:
            raise exceptions.AuthenticationFailed('Permission denied. You do not have '
                                                  'rights to view root assessment '
                                                  'banks.')
        except exceptions.NotAcceptable:
            raise exceptions.NotAcceptable('That bank is not a root.')
        except Exception as ex:
            log_error('assessmentsv2.views.AssessmentHierarchiesRootDetails.get()', ex)
            raise Http404



class AssessmentHierarchiesList(APIView):
    """
    List all available assessment hierarchies.
    api/v2/assessment/hierarchies/

    POST allows you to add an existing bank as a root bank in
    the hierarchy.

    Note that for RESTful calls, you need to set the request header
    'content-type' to 'application/json'

    Example (note the use of double quotes!!):
      {"id": "assessment.Bank:54f9e39833bb7293e9da5b44@oki-dev.MIT.EDU"}
    """
    renderer_classes = (DLJSONRenderer,BrowsableAPIRenderer)

    def get(self, request, format=None):
        """
        List all available root assessment banks
        """
        try:
            set_user(request)
            activate_managers(request)
            am = get_session_data(request, 'am')
            root_banks = am.get_root_banks()
            banks = extract_items(request, root_banks)
            set_session_data(request, 'am', am)
            return Response(banks)
        except PermissionDenied:
            raise exceptions.AuthenticationFailed('Permission denied. You do not have '
                                                  'rights to view root assessment '
                                                  'banks.')
        except Exception as ex:
            log_error('assessmentsv2.views.AssessmentHierarchiesList.get()', ex)
            raise Http404

    def post(self, request, format=None):
        """
        Add a bank as a root to the hierarchy

        """
        try:
            set_user(request)
            activate_managers(request)
            am = get_session_data(request, 'am')

            data = get_data_from_request(request)

            verify_keys_present(data, ['id'])
            try:
                am.get_bank(clean_id(data['id']))
            except:
                raise InvalidArgument()

            am.add_root_bank(clean_id(data['id']))
            set_session_data(request, 'am', am)
            return CreatedResponse()
        except PermissionDenied:
            raise exceptions.AuthenticationFailed('Permission denied. You do not '
                                                  'have rights to add root '
                                                  'assessment banks.')
        except InvalidArgument:
            raise exceptions.APIException('That bank does not exist.')
        except Exception as ex:
            log_error('assessmentsv2.views.AssessmentHierarchiesList.post()', ex)
            raise Http404



class AssessmentItemDetails(APIView):
    """
    Get item details for the given assessment
    api/v2/assessment/banks/<bank_id>/assessments/<assessment_id>/items/<item_id>/

    GET, DELETE
    GET to view the item
    DELETE to remove item from the assessment (NOT from the repo)
    """
    renderer_classes = (DLJSONRenderer,BrowsableAPIRenderer)

    def get(self, request, bank_id, sub_id, item_id, format=None):
        view = ItemDetails.as_view()
        return view(request, bank_id=bank_id, sub_id=item_id, format=format)
        # try:
        #     set_user(request)
        #     activate_managers(request)
        #     am = get_session_data(request, 'am')
        #     bank = am.get_bank(clean_id(bank_id))
        #     item = bank.get_item(clean_id(item_id))
        #     data = convert_dl_object(item)
        #     data.update({
        #         '_links': {
        #             'answers'     : convert_to_items_uri(request, item_id) + 'answers/',
        #             'files'       : convert_to_items_uri(request, item_id) + 'files/',
        #             'question'    : convert_to_items_uri(request, item_id) + 'question/',
        #             'self'        : build_safe_uri(request),
        #         }
        #     })
        #
        #     if 'fileIds' in data:
        #         data['files'] = item.get_files()
        #     if data['question'] and 'fileIds' in data['question']:
        #         data['question']['files'] = item.get_question().get_files()
        #
        #     set_session_data(request, 'am', am)
        #     return Response(data)
        # except PermissionDenied:
        #     raise exceptions.AuthenticationFailed('Permission denied. You do not '
        #                                           'have rights to view assessment '
        #                                           'items in this bank.')
        # except NotFound:
        #     raise exceptions.AuthenticationFailed('Assessment not found.')
        # except Exception as ex:
        #     log_error('assessmentsv2.views.AssessmentItemDetails.get()', ex)
        #     raise Http404

    def delete(self, request, bank_id, sub_id, item_id, format=None):
        try:
            set_user(request)
            activate_managers(request)
            am = get_session_data(request, 'am')
            bank = am.get_bank(clean_id(bank_id))
            data = bank.remove_item(clean_id(sub_id), clean_id(item_id))
            set_session_data(request, 'am', am)
            return Response(data)
        except PermissionDenied:
            raise exceptions.AuthenticationFailed('Permission denied. You do not '
                                                  'have rights to delete an '
                                                  'assessment\'s items '
                                                  'in this bank.')
        except IllegalState as ex:
            return Response(str(ex))
        except Exception as ex:
            log_error('assessmentsv2.views.AssessmentItemDetails.delete()', ex)
            raise Http404


    def put(self, request, bank_id, sub_id, item_id, format=None):
        view = ItemDetails.as_view()
        return view(request, bank_id, item_id, format)

class AssessmentsOffered(APIView):
    """
    Get or create offerings of an assessment
    api/v2/assessment/banks/<bank_id>/assessments/<assessment_id>/assessmentsoffered/

    GET, POST
    GET to view current offerings
    POST to create a new offering (appended to the current offerings)

    Note that for RESTful calls, you need to set the request header
    'content-type' to 'application/json'

    Example (note the use of double quotes!!):
        [{"startTime" : {"year":2015,"month":1,"day":15},"duration": {"days":1}},{"startTime" : {"year":2015,"month":9,"day":15},"duration": {"days":1}}]
    """
    renderer_classes = (DLJSONRenderer,BrowsableAPIRenderer)

    def get(self, request, bank_id, sub_id, format=None):
        try:
            set_user(request)
            activate_managers(request)
            am = get_session_data(request, 'am')
            bank = am.get_bank(clean_id(bank_id))
            offerings = bank.get_assessments_offered_for_assessment(clean_id(sub_id))
            data = extract_items(request, offerings)
            set_session_data(request, 'am', am)
            return Response(data)
        except PermissionDenied:
            raise exceptions.AuthenticationFailed('Permission denied. You do not '
                                                  'have rights to view assessment '
                                                  'offerings in this bank.')
        except NotFound:
            raise exceptions.APIException('Assessment or bank not found.')
        except Exception as ex:
            log_error('assessmentsv2.views.AssessmentsOffered.get()', ex)
            raise Http404

    def post(self, request, bank_id, sub_id, format=None):
        # Cannot create offerings if no items attached to assessment
        try:
            set_user(request)
            activate_managers(request)
            am = get_session_data(request, 'am')
            bank = am.get_bank(clean_id(bank_id))

            data = get_data_from_request(request)

            check_assessment_has_items(bank, clean_id(sub_id))

            if isinstance(data, list):
                return_data = set_assessment_offerings(bank, data, clean_id(sub_id))
                data = extract_items(request, return_data)['data']
            elif isinstance(data, dict):
                return_data = set_assessment_offerings(bank, [data], clean_id(sub_id))
                data = convert_dl_object(return_data[0])
            else:
                raise InvalidArgument()

            set_session_data(request, 'am', am)
            return Response(data)
        except PermissionDenied:
            raise exceptions.AuthenticationFailed('Permission denied. You do not '
                                                  'have rights to create assessment '
                                                  'offerings in this bank.')
        except InvalidArgument:
            raise exceptions.APIException('Poorly formatted input data.')
        except LookupError:
            raise exceptions.APIException('Cannot create an assessment offering for '
                                          'an assessment with no items.')
        except Exception as ex:
            log_error('assessmentsv2.views.AssessmentsOffered.post()', ex)
            raise Http404

class AssessmentOfferedDetails(APIView):
    """
    Get, edit, or delete offerings of an assessment
    api/v2/assessment/banks/<bank_id>/assessmentsoffered/<offered_id>/
    api/v2/assessment/banks/<bank_id>/assessments/<assessment_id>/assessments_offered/<offered_id>/

    GET, PUT, DELETE
    GET to view a specific offering
    PUT to edit the offering parameters
    DELETE to remove the offering

    Note that for RESTful calls, you need to set the request header
    'content-type' to 'application/json'

    Example (note the use of double quotes!!):
        This UI: {"startTime" : {"year":2015,"month":1,"day":15},"duration": {"days":5}}
    """
    renderer_classes = (DLJSONRenderer,BrowsableAPIRenderer)

    def get(self, request, offering_id, bank_id=None, format=None):
        try:
            set_user(request)
            activate_managers(request)
            am = get_session_data(request, 'am')
            bank = get_object_bank(am, offering_id, object_type='assessment_offered', bank_id=bank_id)

            offering = bank.get_assessment_offered(clean_id(offering_id))
            data = convert_dl_object(offering)
            data.update({
                '_links' : {
                    'items'     : build_safe_uri(request) + '../../items/',
                    'self'      : build_safe_uri(request),
                    'takens'    : build_safe_uri(request) + 'assessmentstaken/'
                }
            })
            set_session_data(request, 'am', am)
            return Response(data)
        except PermissionDenied:
            raise exceptions.AuthenticationFailed('Permission denied. You do not '
                                                  'have rights to view assessment '
                                                  'offerings in this bank.')
        except NotFound:
            raise exceptions.APIException('AssessmentOffering not found.')
        except Exception as ex:
            log_error('assessmentsv2.views.AssessmentOfferingDetails.get()', ex)
            raise Http404

    def put(self, request, offering_id, bank_id=None, format=None):
        try:
            set_user(request)
            activate_managers(request)
            am = get_session_data(request, 'am')
            bank = get_object_bank(am, offering_id, object_type='assessment_offered', bank_id=bank_id)

            data = get_data_from_request(request)

            if isinstance(data, list):
                if len(data) == 1:
                    return_data = set_assessment_offerings(bank,
                                                           data,
                                                           clean_id(offering_id),
                                                           update=True)
                    data = extract_items(request, return_data)['data']
                else:
                    raise InvalidArgument('Too many items.')
            elif isinstance(data, dict):
                return_data = set_assessment_offerings(bank,
                                                       [data],
                                                       clean_id(offering_id),
                                                       update=True)
                data = convert_dl_object(return_data[0])
            else:
                raise InvalidArgument()

            set_session_data(request, 'am', am)
            return Response(data)
        except PermissionDenied:
            raise exceptions.AuthenticationFailed('Permission denied. You do not '
                                                  'have rights to edit assessment '
                                                  'offerings in this bank.')
        except InvalidArgument:
            raise exceptions.APIException('Poorly formatted input data.')
        except Exception as ex:
            log_error('assessmentsv2.views.AssessmentOfferingDetails.put()', ex)
            raise Http404

    def delete(self, request, offering_id, bank_id=None, format=None):
        try:
            set_user(request)
            activate_managers(request)
            am = get_session_data(request, 'am')
            bank = get_object_bank(am, offering_id, object_type='assessment_offered', bank_id=bank_id)
            data = bank.delete_assessment_offered(clean_id(offering_id))
            set_session_data(request, 'am', am)
            return Response(data)
        except PermissionDenied:
            raise exceptions.AuthenticationFailed('Permission denied. You do not '
                                                  'have rights to delete assessment '
                                                  'offerings in this bank.')
        except IllegalState as ex:
            raise exceptions.APIException('There are still AssessmentTakens '
                                           'associated with this AssessmentOffered. '
                                           'Delete them first.')
        except Exception as ex:
            log_error('assessmentsv2.views.AssessmentOfferingDetails.delete()', ex)
            raise Http404


class AssessmentsTaken(APIView):
    """
    Get or link takens of an assessment. Input can be from an offering or from an assessment --
    so will have to take that into account in the views.
    api/v2/assessment/banks/<bank_id>/assessments/<assessment_id>/assessmentstaken/
    api/v2/assessment/banks/<bank_id>/assessmentsoffered/<offered_id>/assessmentstaken/

    POST can only happen from an offering (need the offering ID to create a taken)
    GET, POST
    GET to view current assessment takens
    POST to link a new item (appended to the current list) -- ONLY from offerings/<offering_id>/takens/

    Note that for RESTful calls, you need to set the request header
    'content-type' to 'application/json'

    Create example: POST with no data.
    """
    renderer_classes = (DLJSONRenderer,BrowsableAPIRenderer)

    def get(self, request, bank_id, sub_id, format=None):
        try:
            set_user(request)
            activate_managers(request)
            am = get_session_data(request, 'am')
            bank = am.get_bank(clean_id(bank_id))

            params = get_data_from_request(request)

            if len(params) == 0:
                if 'assessment.AssessmentOffered' in sub_id:
                    takens = bank.get_assessments_taken_for_assessment_offered(clean_id(sub_id))
                else:
                    takens = bank.get_assessments_taken_for_assessment(clean_id(sub_id))
            else:
                allowed_query_terms = ['display_name', 'description', 'agent']
                if any(term in params for term in allowed_query_terms):
                    querier = bank.get_assessment_taken_query()
                    querier = config_osid_object_querier(querier, params)

                    if 'agent' in params:
                        if '@mit.edu' not in params['agent']:
                            agent = '{0}@mit.edu'.format(params['agent'])
                        else:
                            agent = params['agent']
                        agent_id = resutils.get_agent_id(agent)
                        querier.match_taking_agent_id(agent_id, match=True)

                    takens = bank.get_assessments_taken_by_query(querier)
                else:
                    if 'assessment.AssessmentOffered' in sub_id:
                        takens = bank.get_assessments_taken_for_assessment_offered(clean_id(sub_id))
                    else:
                        takens = bank.get_assessments_taken_for_assessment(clean_id(sub_id))
            data = extract_items(request, takens)
            set_session_data(request, 'am', am)
            return Response(data)
        except PermissionDenied:
            raise exceptions.AuthenticationFailed('Permission denied. You do not '
                                                  'have rights to view assessment '
                                                  'takens in this bank.')
        except NotFound:
            raise exceptions.APIException('AssessmentOffering or bank not found.')
        except Exception as ex:
            log_error('assessmentsv2.views.AssessmentTakens.get()', ex)
            raise Http404

    def post(self, request, bank_id, sub_id, format=None):
        # when trying to create a taken for a user, check first
        # that a taken does not already exist, using
        # get_assessments_taken_for_taker_and_assessment_offered().
        # If it does exist, return that taken.
        # If one does not exist, create a new taken.
        try:
            # Kind of hokey, but need to get the sub_id type from a string...
            if 'assessment.AssessmentOffered' not in sub_id:
                raise Unsupported()
            set_user(request)
            activate_managers(request)
            am = get_session_data(request, 'am')
            bank = am.get_bank(clean_id(bank_id))

            # first check if a taken exists for the user / offering
            user_id = am.effective_agent_id
            takens = bank.get_assessments_taken_for_taker_and_assessment_offered(user_id,
                                                                                 clean_id(sub_id))

            create_new_taken = False
            if takens.available() > 0:
                # return the first taken ONLY if not finished -- user has attempted this problem
                # before. If finished, create a new one.
                if Id(bank_id).identifier in settings.OPEN_BANKS:
                    create_new_taken = True
                else:
                    first_taken = takens.next()
                    if first_taken.has_ended():
                        # create new one
                        create_new_taken = True
                    else:
                        data = convert_dl_object(first_taken)
            else:
                # create a new taken
                create_new_taken = True

            if create_new_taken:
                # use our new Taken Record object, which has a "can_review_whether_correct()"
                # method.
                form = bank.get_assessment_taken_form_for_create(clean_id(sub_id),
                                                                 [REVIEWABLE_TAKEN])
                data = convert_dl_object(bank.create_assessment_taken(form))

            set_session_data(request, 'am', am)
            return Response(data)
        except MongoPermissionDenied:
            raise exceptions.AuthenticationFailed('You have exceeded the maximum number of '
                                                  'allowed attempts.')
        except PermissionDenied:
            raise exceptions.AuthenticationFailed('Permission denied. You do not '
                                                  'have rights to create assessment '
                                                  'takens in this bank.')
        except InvalidArgument:
            raise exceptions.APIException('Poorly formatted input data.')
        except Unsupported:
            raise exceptions.APIException('Can only create AssessmentTaken from an AssessmentOffered root URL.')
        except Exception as ex:
            log_error('assessmentsv2.views.AssessmentTakens.post()', ex)
            raise Http404


class AssessmentTakenDetails(APIView):
    """
    Get a single taken instance of an assessment. Not used for much
    except to point you towards the /take endpoint...
    api/v2/assessment/banks/<bank_id>/assessmentstaken/<taken_id>/

    GET, DELETE
    GET to view a specific taken
    DELETE to remove the taken

    Note that for RESTful calls, you need to set the request header
    'content-type' to 'application/json'
"""
    renderer_classes = (DLJSONRenderer,BrowsableAPIRenderer)

    def delete(self, request, bank_id, taken_id, format=None):
        try:
            set_user(request)
            activate_managers(request)
            am = get_session_data(request, 'am')
            bank = am.get_bank(clean_id(bank_id))
            data = bank.delete_assessment_taken(clean_id(taken_id))
            set_session_data(request, 'am', am)
            return Response(data)
        except PermissionDenied:
            raise exceptions.AuthenticationFailed('Permission denied. You do not '
                                                  'have rights to delete assessment '
                                                  'takens in this bank.')
        except NotFound:
            raise exceptions.APIException('AssessmentTaken not found.')
        except Exception as ex:
            log_error('assessmentsv2.views.AssessmentTakenDetails.delete()', ex)
            raise Http404

    def get(self, request, bank_id, taken_id, format=None):
        try:
            set_user(request)
            activate_managers(request)
            am = get_session_data(request, 'am')
            bank = am.get_bank(clean_id(bank_id))
            taken = bank.get_assessment_taken(clean_id(taken_id))
            data = convert_dl_object(taken)
            data.update({
                '_links' : {
                    'self'      : build_safe_uri(request),
                    'questions' : build_safe_uri(request) + 'questions/',
                    'finish'    : build_safe_uri(request) + 'finish/',
                    # 'take'    : build_safe_uri(request) + 'take/',
                    # 'files'   : build_safe_uri(request) + 'files/',
                    # 'submit'  : build_safe_uri(request) + 'submit/'
                }
            })
            set_session_data(request, 'am', am)
            return Response(data)
        except PermissionDenied:
            raise exceptions.AuthenticationFailed('Permission denied. You do not '
                                                  'have rights to view assessment '
                                                  'takens in this bank.')
        except NotFound:
            raise exceptions.APIException('AssessmentTaken or bank not found.')
        except Exception as ex:
            log_error('assessmentsv2.views.AssessmentTakenDetails.get()', ex)
            raise Http404


# class ItemQuery(APIView):
#     """Provides a query interface for items in an assessment bank.
#
#     Currently supports query by IRT values only. Difficulty, discrimination, and
#     pseudo-guessing value.
#     This automatically searches all items in a bank (not an assessment).
#     api/v2/assessment/banks/<bank_id>/items/query/?<queryparams>
#
#     GET
#     GET to get the query results
#     """
#     renderer_classes = (DLJSONRenderer,BrowsableAPIRenderer)
#
#     def get(self, request, bank_id, format=None):
#         try:
#             set_user(request)
#             activate_managers(request)
#             am = get_session_data(request, 'am')
#             bank = am.get_bank(clean_id(bank_id))
#
#             querier = bank.get_item_query()
#
#             data = get_data_from_request(request)  # should be GET params
#
#             at_least_one_of = ['max_difficulty','min_difficulty',
#                                'max_discrimination','min_discrimination',
#                                'display_name','learning_objective']
#             verify_at_least_one_key_present(data, at_least_one_of)
#
#             # make sure that max > min
#             for field in ['difficulty','discrimination']:
#                 if 'max_' + field in data and 'min_' + field in data:
#                     if float(data['max_' + field]) < float(data['min_' + field]):
#                         raise IntegrityError(field)
#
#             if 'max_difficulty' in data:
#                 querier.match_maximum_difficulty(float(data['max_difficulty']), True)
#
#             if 'min_difficulty' in data:
#                 querier.match_minimum_difficulty(float(data['min_difficulty']), True)
#
#             if 'max_discrimination' in data:
#                 querier.match_maximum_discrimination(float(data['max_discrimination']), True)
#
#             if 'min_discrimination' in data:
#                 querier.match_minimum_discrimination(float(data['min_discrimination']), True)
#
#             if 'display_name' in data:
#                 querier.match_display_name(str(data['display_name']), WORDIGNORECASE_STRING_MATCH_TYPE, True)
#
#             if 'learning_objective' in data:
#                 if '@' in data['learning_objective']:
#                     search_id = quote(data['learning_objective'])
#                 else:
#                     search_id = data['learning_objective']
#                 querier.match_learning_objective_id(search_id, True)
#
#             results = bank.get_items_by_query(querier)
#             data = extract_items(request, results)
#             set_session_data(request, 'am', am)
#             return Response(data)
#         except PermissionDenied:
#             raise exceptions.AuthenticationFailed('Permission denied. You do not '
#                                                   'have rights to query items '
#                                                   'in this bank.')
#         except KeyError as ex:
#             raise exceptions.APIException(*ex.args)
#         except InvalidArgument:
#             raise exceptions.APIException('Poorly formatted input data.')
#         except IntegrityError as ex:
#             raise exceptions.APIException('max_' + ex.args[0] + ' cannot be less than min_' + ex.args[0])
#         except Exception as ex:
#             log_error('assessmentsv2.views.ItemQuery.get()', ex)
#             raise Http404


class ItemQuestion(APIView):
    """Edit question for an existing item

    api/v2/assessment/banks/<bank_id>/items/<item_id>/question/

    GET, PUT
    GET to get the question.
    PUT to modify the question.

    Note that for RESTful calls, you need to set the request header
    'content-type' to 'application/json'

    Example (note the use of double quotes!!):
       {"questionString" : "What is 1 + 1?"}
    """
    renderer_classes = (DLJSONRenderer,BrowsableAPIRenderer)

    def get(self, request, bank_id, sub_id, format=None):
        try:
            set_user(request)
            activate_managers(request)
            am = get_session_data(request, 'am')
            bank = am.get_bank(clean_id(bank_id))

            item = bank.get_item(clean_id(sub_id))
            existing_question = item.get_question()
            data = convert_dl_object(existing_question)
            if 'fileIds' in data:
                data.update({
                    'files': existing_question.get_files()
                })
            set_session_data(request, 'am', am)
            return Response(data)
        except PermissionDenied:
            raise exceptions.AuthenticationFailed('Permission denied. You do not '
                                                  'have rights to get item questions '
                                                  'in this bank.')
        except InvalidArgument:
            raise exceptions.APIException('Poorly formatted input data.')
        except Exception as ex:
            log_error('assessmentsv2.views.ItemQuestion.get()', ex)
            raise Http404

    def put(self, request, bank_id, sub_id, format=None):
        # TODO: handle updating of question files (manip and ortho view set)
        try:
            set_user(request)
            activate_managers(request)
            am = get_session_data(request, 'am')
            bank = am.get_bank(clean_id(bank_id))

            data = get_data_from_request(request)

            item = bank.get_item(clean_id(sub_id))
            existing_question = item.get_question()

            if 'type' not in data:
                # kind of a hack
                data['type'] = existing_question.object_map['recordTypeIds'][0]

            q_id = existing_question.ident
            qfu = bank.get_question_form_for_update(q_id)
            qfu = update_question_form(request, data, qfu)
            updated_question = bank.update_question(qfu)

            full_item = bank.get_item(clean_id(sub_id))
            data = convert_dl_object(full_item)
            set_session_data(request, 'am', am)
            return Response(data)
        except PermissionDenied:
            raise exceptions.AuthenticationFailed('Permission denied. You do not '
                                                  'have rights to edit item '
                                                  'questions in this bank.')
        except Unsupported:
            raise exceptions.APIException('Unsupported question type.')
        except InvalidArgument:
            raise exceptions.APIException('Poorly formatted input data.')
        except Exception as ex:
            log_error('assessmentsv2.views.ItemQuestion.put()', ex)
            raise Http404



class ItemTextAsFormat(APIView):
    """Request item text in specific format

    Returns the item text in a specific format. For example, edxml, QTI, etc.
    api/v2/assessment/banks/<bank_id>/items/<item_id>/<format>/

    GET
    GET to get the question.
    """
    renderer_classes = (DLJSONRenderer,BrowsableAPIRenderer)

    def get(self, request, bank_id, output_format, sub_id=None, taken_id=None, question_id=None, format=None):
        try:
            supported_item_formats = ['edxml']
            if output_format not in supported_item_formats:
                raise InvalidArgument
            set_user(request)
            activate_managers(request)
            am = get_session_data(request, 'am')
            bank = am.get_bank(clean_id(bank_id))
            if sub_id:
                item = bank.get_item(clean_id(sub_id))
            elif taken_id and question_id:
                # This works because DLKit makes the question and item have the
                # same ID. May not work in the future -- ?? is this guaranteed?
                item = bank.get_item(clean_id(question_id))
            else:
                raise LookupError
            if 'fileIds' in item.object_map:
                #  need to get the right extension onto the files
                file_labels = item.object_map['fileIds']
                files = item.get_files()
                data = {
                    'files' : {}
                }
                for label, content in file_labels.iteritems():
                    file_type_id = clean_id(content['assetContentTypeId'])
                    extension = file_type_id.identifier
                    data['files'][label + '.' + extension] = files[label]
            else:
                data = {}
            if output_format == 'edxml':
                if 'files' in data:
                    raw_edxml = item.get_edxml()
                    soup = BeautifulSoup(raw_edxml, 'xml')
                    labels = []
                    label_filename_map = {}
                    for filename in data['files'].keys():
                        label = filename.split('.')[0]
                        labels.append(label)
                        label_filename_map[label] = filename
                    attrs = {
                        'draggable'             : 'icon',
                        'drag_and_drop_input'   : 'img',
                        'files'                 : 'included_files',
                        'img'                   : 'src'
                    }
                    local_regex = re.compile('[^http]')
                    for key, attr in attrs.iteritems():
                        search = {attr : local_regex}
                        tags = soup.find_all(**search)
                        for item in tags:
                            if key == 'files' or item.name == key:
                                if item[attr] in labels:
                                    item[attr] = label_filename_map[item[attr]]
                    data['data'] = soup.find('problem').prettify()
                else:
                    data['data'] = item.get_edxml()

            set_session_data(request, 'am', am)
            return Response(data)
        except PermissionDenied:
            raise exceptions.AuthenticationFailed('Permission denied. You do not ' +
                                                  'have rights to get item questions ' +
                                                  'in this bank.')
        except LookupError:
            raise exceptions.APIException('How did you get to this URL without specifying either ' +
                                          'an item_id or a taken_id and question_id?')
        except InvalidArgument:
            raise exceptions.APIException('"' + output_format + '" is not a supported item text format.')
        except Exception as ex:
            log_error('assessmentsv2.views.ItemTextAsFormat.get()', ex)
            raise Http404

# class ItemSubmissionCheck(APIView):
#     """
#     Check the answer for an item
#     POST
#     POST to see if the answer is right or wrong.
#
#     TODO: Implement a test for this method
#     NOTE: This only works for Ortho-3D questions, currently
#
#     Note that for RESTful calls, you need to set the request header
#     'content-type' to 'application/json'
#     """
#     renderer_classes = (DLJSONRenderer,BrowsableAPIRenderer)
#
#     def post(self, request, bank_id, sub_id, format=None):
#         try:
#             raise Exception('Deprecated in favor of AssessmentSession')
#             set_user(request)
#             activate_managers(request)
#             am = get_session_data(request, 'am')
#             bank = am.get_bank(clean_id(bank_id))
#
#             item = bank.get_item(clean_id(sub_id))
#
#             submission = get_data_from_request(request)['answer']
#
#             answers = item.get_answers()
#             response = {
#                 'correct'   : False
#             }
#
#             for answer in answers:
#                 ans_type = answer.object_map['recordTypeIds'][0]
#                 if ans_type == 'answer-record-type%3Alabel-ortho-faces%40ODL.MIT.EDU':
#                     if (int(answer.get_front_face()) == int(submission['frontFaceEnum']) and
#                         int(answer.get_side_face()) == int(submission['sideFaceEnum']) and
#                         int(answer.get_top_face()) == int(submission['topFaceEnum'])):
#                         response['correct'] = True
#                         break
#
#             set_session_data(request, 'am', am)
#             return Response(response)
#         except PermissionDenied:
#             raise exceptions.AuthenticationFailed('Permission denied. You do not '
#                                                   'have rights to submit item answers '
#                                                   'in this bank.')
#         except InvalidArgument:
#             raise exceptions.APIException('Poorly formatted input data.')
#         except Exception as ex:
#             log_error('assessmentsv2.views.ItemSubmissionCheck.post()', ex)
#             raise Http404


class ItemFile(APIView):
    """
    Download the given item file for an existing item
    api/v2/assessment/banks/<bank_id>/items/<item_id>/files/<file_name>

    GET
    GET to get the file (manipulatable, ortho viewset).

    TODO: Will need to modify this to fit a generic "file" record type
    """
    renderer_classes = (DLJSONRenderer,BrowsableAPIRenderer)

    def get(self, request, bank_id, sub_id, file_key, format=None):
        try:
            set_user(request)
            activate_managers(request)
            am = get_session_data(request, 'am')
            bank = am.get_bank(clean_id(bank_id))
            item = bank.get_item(clean_id(sub_id))
            question = item.get_question()

            if file_key == 'manip':
                file_content_type = 'application/vnd.unity'
                filename = file_key + '.unity3d'
                file = question.manip
            elif file_key == 'front' or file_key == 'side' or file_key == 'top':
                file_content_type = 'image/jpeg'
                filename = file_key + '.jpg'
                view_key = file_key + '_view'
                file = getattr(question, view_key)
            elif file_key == 'all':
                filename = '3dfiles_' + re.sub(r'[^\w\d]', '', item.display_name.text) + '.zip'
                file = cStringIO.StringIO()
                file_content_type = 'application/zip'
                zf = zipfile.ZipFile(file, 'w')
                zf.writestr('manip.unity3d', question.manip.read())
                if question.has_ortho_view_set():
                    zf.writestr('front_view.jpg', question.front_view.read())
                    zf.writestr('side_view.jpg', question.side_view.read())
                    zf.writestr('top_view.jpg', question.top_view.read())
                zf.close()
            else:
                raise Exception()
            response = HttpResponse(content_type=file_content_type)
            response["Content-Disposition"] = "attachment; filename=" + filename
            try:
                # if it is a zip file, should use this
                response.write(file.getvalue())
            except:
                response.write(file.read())
            set_session_data(request, 'am', am)
            return response
        except PermissionDenied:
            raise exceptions.AuthenticationFailed('Permission denied. You do not '
                                                  'have rights to get item files '
                                                  'in this bank.')
        except InvalidArgument:
            raise exceptions.APIException('Poorly formatted input data.')
        except Exception as ex:
            log_error('assessmentsv2.views.ItemFile.get()', ex)
            raise Http404


class ItemFilesList(APIView):
    """
    Get a list of available files for this item
    api/v2/assessment/banks/<bank_id>/items/<item_id>/files/

    GET
    GET to get the file list (manipulatable, ortho viewset).

    TODO: Will need to modify this to fit a generic "file" record type
    """
    renderer_classes = (DLJSONRenderer,BrowsableAPIRenderer)

    def get(self, request, bank_id, sub_id, format=None):
        try:
            set_user(request)
            activate_managers(request)
            am = get_session_data(request, 'am')
            bank = am.get_bank(clean_id(bank_id))
            item = bank.get_item(clean_id(sub_id))
            question = item.get_question()

            data = {
                '_links' : {
                    'self' : build_safe_uri(request)
                },
                'data': []
            }
            question_obj = convert_dl_object(question)
            question_files = question.get_files()
            for label, link in question_files.iteritems():
                if 'View' in label and 'ortho' in question.object_map['recordTypeIds'][0]:
                    # for ortho3D questions, remove the View name
                    label = label.replace('View', '')
                data['_links'][label] = link
                data['data'].append({
                    label : link
                })

            return Response(data)
        except PermissionDenied:
            raise exceptions.AuthenticationFailed('Permission denied. You do not '
                                                  'have rights to get item files '
                                                  'in this bank.')
        except InvalidArgument:
            raise exceptions.APIException('Poorly formatted input data.')
        except Exception as ex:
            log_error('assessmentsv2.views.ItemFilesList.get()', ex)
            raise Http404


class ItemAnswers(APIView):
    """
    Edit answers for an existing item
    api/v2/assessment/banks/<bank_id>/items/<item_id>/answers/

    GET, POST
    GET to get current list of answers
    POST to add a new answer

    Note that for RESTful calls, you need to set the request header
    'content-type' to 'application/json'

    Example (note the use of double quotes!!):
       {"responseString" : "2"}
    """
    renderer_classes = (DLJSONRenderer,BrowsableAPIRenderer)

    def get(self, request, bank_id, sub_id, format=None):
        try:
            set_user(request)
            activate_managers(request)
            am = get_session_data(request, 'am')
            bank = am.get_bank(clean_id(bank_id))

            item = bank.get_item(clean_id(sub_id))
            existing_answers = item.get_answers()

            data = extract_items(request, existing_answers)
            set_session_data(request, 'am', am)
            return Response(data)
        except PermissionDenied:
            raise exceptions.AuthenticationFailed('Permission denied. You do not '
                                                  'have rights to get item answers '
                                                  'in this bank.')
        except Exception as ex:
            log_error('assessmentsv2.views.ItemAnswers.get()', ex)
            raise Http404

    def post(self, request, bank_id, sub_id, format=None):
        try:
            bank = new_item = None
            set_user(request)
            activate_managers(request)
            am = get_session_data(request, 'am')
            bank = am.get_bank(clean_id(bank_id))

            data = get_data_from_request(request)

            item = bank.get_item(clean_id(sub_id))

            if isinstance(data, list):
                for answer in data:
                    a_types = get_answer_records(answer)
                    afc = bank.get_answer_form_for_create(clean_id(sub_id),
                                                          a_types)
                    afc = update_answer_form(answer, afc)
                    afc = set_answer_form_genus_and_feedback(answer, afc)
                    new_answer = bank.create_answer(afc)
            elif isinstance(data, dict):
                a_types = get_answer_records(data)
                afc = bank.get_answer_form_for_create(clean_id(sub_id),
                                                      a_types)
                afc = set_answer_form_genus_and_feedback(data, afc)
                # for multi-choice-ortho, need to send the questions
                if 'multi-choice' in data['type']:
                    question = item.get_question()
                    afc = update_answer_form(data, afc, question)
                else:
                    afc = update_answer_form(data, afc)
                new_answer = bank.create_answer(afc)
            else:
                raise InvalidArgument()

            new_item = bank.get_item(clean_id(sub_id))
            existing_answers = new_item.get_answers()
            data = extract_items(request, existing_answers)['data']
            set_session_data(request, 'am', am)
            return Response(data)
        except PermissionDenied:
            if bank and new_item:
                clean_up_post(bank, new_item)
            raise exceptions.AuthenticationFailed('Permission denied. You do not '
                                                  'have rights to create item answers '
                                                  'in this bank.')
        except Unsupported:
            if bank and new_item:
                clean_up_post(bank, new_item)
            raise exceptions.APIException('Unsupported answer type.')
        except InvalidArgument:
            if bank and new_item:
                clean_up_post(bank, new_item)
            raise exceptions.APIException('Poorly formatted input data.')
        except Exception as ex:
            if bank and new_item:
                clean_up_post(bank, new_item)
            log_error('assessmentsv2.views.ItemAnswers.post()', ex)
            raise Http404


class Documentation(APIView):
    """
    Shows the user documentation for talking to the RESTful service
    """
    permission_classes = (AllowAny,)

    def get(self, request, format=None):
        try:
            return render_to_response('assessmentsv2/documentation.html',
                                      {'types': supported_types()},
                                      RequestContext(request))
        except Exception as ex:
            log_error('assessmentsv2.views.Documentation.get()', ex)
            raise Http404


class FinishAssessmentTaken(APIView):
    """
    "finish" the assessment to indicate that student has ended his/her attempt
    api/v2/assessment/banks/<bank_id>/assessmentstaken/<taken_id>/finish/

    POST empty data
    """
    def post(self, request, bank_id, taken_id, format=None):
        try:
            set_user(request)
            activate_managers(request)
            am = get_session_data(request, 'am')
            bank = am.get_bank(clean_id(bank_id))
            # "finish" the assessment section
            # bank.finished_assessment_section(first_section.ident)
            bank.finish_assessment(clean_id(taken_id))
            data = {
                'success'   : True
            }
            set_session_data(request, 'am', am)
            return Response(data)
        except PermissionDenied:
            raise exceptions.AuthenticationFailed('Permission denied. You do not '
                                                  'have rights to submit assessment '
                                                  'responses in this bank.')
        except IllegalState:
            raise exceptions.APIException('Assessment already completed.')
        except NotFound:
            raise exceptions.APIException('AssessmentTaken not found.')
        except Exception as ex:
            log_error('assessmentsv2.views.FinishAssessmentTaken.post()', ex)
            raise Http404

class ItemAnswerDetails(APIView):
    """
    Edit answers for an existing item answer
    api/v2/assessment/banks/<bank_id>/items/<item_id>/answers/<answer_id>/

    GET, PUT, DELETE
    GET to get this answer
    PUT to edit this answer
    DELETE to remove this answer

    Note that for RESTful calls, you need to set the request header
    'content-type' to 'application/json'

    Example (note the use of double quotes!!):
       {"responseString" : "2"}
    """
    renderer_classes = (DLJSONRenderer,BrowsableAPIRenderer)

    def get(self, request, bank_id, sub_id, ans_id, format=None):
        try:
            set_user(request)
            activate_managers(request)
            am = get_session_data(request, 'am')
            bank = am.get_bank(clean_id(bank_id))

            item = bank.get_item(clean_id(sub_id))
            answers = item.get_answers() # need to get_answers() and filter out

            existing_answer = None
            for answer in answers:
                if answer.ident == clean_id(ans_id):
                    existing_answer = answer
                    break
            if not existing_answer:
                raise NotFound()

            data = convert_dl_object(existing_answer)
            data.update({
                '_links': {
                    'self'        : build_safe_uri(request),
                }
            })
            set_session_data(request, 'am', am)
            return Response(data)
        except PermissionDenied:
            raise exceptions.AuthenticationFailed('Permission denied. You do not '
                                                  'have rights to get item answers '
                                                  'in this bank.')
        except NotFound:
            raise exceptions.APIException('Answer not found.')
        except Exception as ex:
            log_error('assessmentsv2.views.ItemAnswerDetails.get()', ex)
            raise Http404

    def put(self, request, bank_id, sub_id, ans_id, format=None):
        try:
            set_user(request)
            activate_managers(request)
            am = get_session_data(request, 'am')
            bank = am.get_bank(clean_id(bank_id))

            data = get_data_from_request(request)

            item = bank.get_item(clean_id(sub_id))
            answers = item.get_answers()
            answer = find_answer_in_answers(clean_id(ans_id), answers)

            if 'type' not in data:
                data['type'] = answer.object_map['recordTypeIds'][0]

            a_id = clean_id(ans_id)
            afu = bank.get_answer_form_for_update(a_id)
            afu = update_answer_form(data, afu)

            afu = set_answer_form_genus_and_feedback(data, afu)

            updated_answer = bank.update_answer(afu)

            data = convert_dl_object(updated_answer)
            set_session_data(request, 'am', am)
            return Response(data)
        except PermissionDenied:
            raise exceptions.AuthenticationFailed('Permission denied. You do not '
                                                  'have rights to edit item '
                                                  'answers in this bank.')
        except Unsupported:
            raise exceptions.APIException('Unsupported answer type.')
        except InvalidArgument:
            raise exceptions.APIException('Poorly formatted input data.')
        except Exception as ex:
            log_error('assessmentsv2.views.ItemAnswerDetails.put()', ex)
            raise Http404

    def delete(self, request, bank_id, sub_id, ans_id, format=None):
        try:
            set_user(request)
            activate_managers(request)
            am = get_session_data(request, 'am')
            bank = am.get_bank(clean_id(bank_id))
            data = bank.delete_answer(clean_id(ans_id))
            set_session_data(request, 'am', am)
            return Response(data)
        except PermissionDenied:
            raise exceptions.AuthenticationFailed('Permission denied. You do not '
                                                  'have rights to delete item '
                                                  'answers in this bank.')
        except IllegalState as ex:
            return Response(str(ex))
        except Exception as ex:
            log_error('assessmentsv2.views.ItemAnswerDetails.delete()', ex)
            raise Http404

class TakeAssessment(APIView):
    """
    Get the next question available in the taken...DLkit tracks
    state of what is the next available. If files are included
    in the assessment type, they will be returned with
    the question text.
    api/v2/assessment/banks/<bank_id>/assessmentstaken/<taken_id>/take/

    GET only is supported?
    GET to get the next uncompleted question for the given user

    Note that for RESTful calls, you need to set the request header
    'content-type' to 'application/json'
    """
    renderer_classes = (DLJSONRenderer,BrowsableAPIRenderer)

    def get(self, request, bank_id, taken_id, format=None):
        try:
            set_user(request)
            activate_managers(request)
            am = get_session_data(request, 'am')

            bank = am.get_bank(clean_id(bank_id))
            first_section = bank.get_first_assessment_section(clean_id(taken_id))
            question = bank.get_first_unanswered_question(first_section.ident)
            data = convert_dl_object(question)

            if 'fileIds' in data:
                data.update({
                    'files': question.get_files()
                })

            set_session_data(request, 'am', am)
            return Response(data)
        except PermissionDenied:
            raise exceptions.AuthenticationFailed('Permission denied. You do not '
                                                  'have rights to take assessments '
                                                  'in this bank.')
        except IllegalState:
            raise exceptions.APIException('Assessment already completed.')
        except NotFound:
            raise exceptions.APIException('AssessmentTaken not found.')
        except Exception as ex:
            log_error('assessmentsv2.views.TakeAssessment.get()', ex)
            raise Http404


class TakeAssessmentFiles(APIView):
    """
    Lists the files for the next assessment section, if it has
    any.
    api/v2/assessment/banks/<bank_id>/assessmentstaken/<taken_id>/files/

    GET only is supported
    GET to get a list of files for the next unanswered section
    """
    renderer_classes = (DLJSONRenderer,BrowsableAPIRenderer)

    def get(self, request, bank_id, taken_id, format=None):
        try:
            set_user(request)
            activate_managers(request)
            am = get_session_data(request, 'am')

            bank = am.get_bank(clean_id(bank_id))
            first_section = bank.get_first_assessment_section(clean_id(taken_id))
            question = bank.get_first_unanswered_question(first_section.ident)
            if 'question-record-type%3Alabel-ortho-faces%40ODL.MIT.EDU' in question.object_map['recordTypeIds']:
                question_files = question.get_files()
                data = {
                    'manip' : question_files['manip']
                }
                if question.has_ortho_view_set:
                    data['front'] = question_files['frontView']
                    data['side'] = question_files['sideView']
                    data['top'] = question_files['topView']
            else:
                raise LookupError('No files for this question.')
            set_session_data(request, 'am', am)
            return Response(data)
        except PermissionDenied:
            raise exceptions.AuthenticationFailed('Permission denied. You do not '
                                                  'have rights to take assessments '
                                                  'in this bank.')
        except IllegalState:
            raise exceptions.APIException('Assessment already completed.')
        except NotFound:
            raise exceptions.APIException('AssessmentTaken not found.')
        except LookupError:
            raise exceptions.APIException('No files found for this question.')
        except Exception as ex:
            log_error('assessmentsv2.views.TakeAssessment.get()', ex)
            raise Http404


class SubmitAssessment(APIView):
    """
    POST the student's response to the active item. DLKit
    tracks which question / item the student is currently
    interacting with.
    api/v2/assessment/banks/<bank_id>/assessmentstaken/<taken_id>/submit/

    POST student response

    Note that for RESTful calls, you need to set the request header
    'content-type' to 'application/json'

    Example (for an Ortho3D manipulatable - label type):
        {"responseSet":{
                "frontFaceEnum" : 0,
                "sideFaceEnum"  : 1,
                "topFaceEnum"   : 2
            }
        }
    """
    renderer_classes = (DLJSONRenderer,BrowsableAPIRenderer)

    def post(self, request, bank_id, taken_id, format=None):
        try:
            set_user(request)
            activate_managers(request)
            am = get_session_data(request, 'am')
            bank = am.get_bank(clean_id(bank_id))

            data = get_data_from_request(request)

            first_section = bank.get_first_assessment_section(clean_id(taken_id))
            question = bank.get_first_unanswered_question(first_section.ident)
            response_form = bank.get_response_form(assessment_section_id=first_section.ident,
                                                   item_id=question.ident)

            if 'type' not in data:
                # kind of a hack
                data['type'] = question.object_map['recordTypeIds'][0]
                data['type'] = data['type'].replace('question-record-type',
                                                    'answer-record-type')

            update_form = update_response_form(data, response_form)
            bank.submit_response(first_section.ident, question.ident, update_form)
            # the above code logs the response in Mongo

            # "finish" the assessment section
            # bank.finished_assessment_section(first_section.ident)
            bank.finish_assessment_section(first_section.ident)

            # Now need to actually check the answers against the
            # item answers.
            answers = bank.get_answers(first_section.ident, question.ident)
            # compare these answers to the submitted response
            correct = validate_response(data, answers)

            data = {
                'correct'   : correct
            }

            # should send back if there are more questions, so the
            # client knows
            try:
                bank.get_first_unanswered_question(first_section.ident)
                data['hasNext'] = True
            except:
                data['hasNext'] = False

            set_session_data(request, 'am', am)
            return Response(data)
        except PermissionDenied:
            raise exceptions.AuthenticationFailed('Permission denied. You do not '
                                                  'have rights to submit assessment '
                                                  'responses in this bank.')
        except IllegalState:
            raise exceptions.APIException('Assessment already completed.')
        except NotFound:
            raise exceptions.APIException('AssessmentTaken not found.')
        except Exception as ex:
            log_error('assessmentsv2.views.SubmitAssessment.post()', ex)
            raise Http404


class AssessmentTakenQuestions(APIView):
    """
    Returns all of the questions for a given assessment taken.
    Assumes that only one section per assessment.
    api/v2/assessment/banks/<bank_id>/assessmentstaken/<taken_id>/questions/

    GET only
    """

    def get(self, request, bank_id, taken_id, format='json'):
        try:
            set_user(request)
            activate_managers(request)

            params = get_data_from_request(request)

            am = get_session_data(request, 'am')

            bank = am.get_bank(clean_id(bank_id))
            first_section = bank.get_first_assessment_section(clean_id(taken_id))
            questions = bank.get_questions(first_section.ident)
            data = extract_items(request, questions, bank, first_section)

            if 'files' in params:
                for question in data['data']['results']:
                    if 'fileIds' in question:
                        question['files'] = bank.get_question(first_section.ident,
                                                              clean_id(question['id'])).get_files()

            set_session_data(request, 'am', am)
            return Response(data)
        except PermissionDenied:
            raise exceptions.AuthenticationFailed('Permission denied. You do not '
                                                  'have rights to take assessments '
                                                  'in this bank.')
        except IllegalState:
            raise exceptions.APIException('Assessment already completed.')
        except NotFound:
            raise exceptions.APIException('AssessmentTaken or bank not found.')
        except Exception as ex:
            log_error('assessmentsv2.views.AssessmentTakenQuestions.get()', ex)
            raise Http404


class AssessmentTakenQuestionDetails(APIView):
    """
    Returns the specified question
    api/v2/assessment/banks/<bank_id>/assessmentstaken/<taken_id>/questions/<question_id>/

    GET only
    """

    def get(self, request, bank_id, taken_id, question_id, format='json'):
        try:
            set_user(request)
            activate_managers(request)
            am = get_session_data(request, 'am')

            bank = am.get_bank(clean_id(bank_id))
            first_section = bank.get_first_assessment_section(clean_id(taken_id))
            question = bank.get_question(first_section.ident, clean_id(question_id))
            data = convert_dl_object(question)

            status = get_question_status(bank, first_section, clean_id(question_id))
            data.update(status)

            data.update({
                '_links' : {
                    'self'      : build_safe_uri(request),
                    'edxml'     : build_safe_uri(request) + 'edxml/',
                    'files'     : build_safe_uri(request) + 'files/',
                    'status'    : build_safe_uri(request) + 'status/',
                    'submit'    : build_safe_uri(request) + 'submit/'
                }
            })

            if 'fileIds' in data:
                data['files'] = question.get_files()

            set_session_data(request, 'am', am)
            return Response(data)
        except PermissionDenied:
            raise exceptions.AuthenticationFailed('Permission denied. You do not '
                                                  'have rights to take assessments '
                                                  'in this bank.')
        except IllegalState:
            raise exceptions.APIException('Assessment already completed.')
        except NotFound:
            raise exceptions.APIException('AssessmentTaken not found.')
        except Exception as ex:
            log_error('assessmentsv2.views.AssessmentTakenQuestionDetails.get()', ex)
            raise Http404




class AssessmentTakenQuestionComments(APIView):
    """
    Gets the instructor comments for this question
    api/v2/assessment/banks/<bank_id>/assessmentstaken/<taken_id>/questions/<question_id>/comments/

    GET, POST

    Example (for an Ortho3D manipulatable - label type):

    """

    def get(self, request, bank_id, taken_id, question_id, format='json'):
        try:
            set_user(request)
            activate_managers(request)
            cm = get_session_data(request, 'cm')
            am = get_session_data(request, 'am')

            params = get_data_from_request(request)

            # try to get the book for this bank. If no book, create it using Jeff's work-around
            # try:
            #     book_id = bank_id.replace('assessment.Bank','commenting.Book')
            #     book = cm.get_book(Id(book_id))
            # except NotFound:
            #     book = cm.get_comment_lookup_session_for_book(Id(bank_id))
            book = cm.get_book(Id(bank_id))

            # should probably use something like get_comments_for_reference(), but
            # for now, just loop through...
            comments = book.get_comments()

            bank = am.get_bank(clean_id(bank_id))
            first_section = bank.get_first_assessment_section(clean_id(taken_id))
            try:
                response = bank.get_response(first_section.ident, clean_id(question_id))
            except NotFound:
                raise IntegrityError

            comments = [comment for comment in comments if comment.get_reference_id() == response.ident]

            data = extract_items(request, comments)

            if 'files' in params:
                for comment in data['data']['results']:
                    if 'fileId' in comment:
                        comment_obj = book.get_comment(Id(comment['id']))
                        comment['file'] = comment_obj.get_file_url()

            set_session_data(request, 'cm', cm)
            set_session_data(request, 'am', am)
            return Response(data)
        except PermissionDenied:
            raise exceptions.AuthenticationFailed('Permission denied. You do not '
                                                  'have rights to view comments.')
        except IntegrityError:
            raise exceptions.APIException('Student has not responded -- no comments yet.')
        except NotFound:
            raise exceptions.APIException('AssessmentTaken, bank, question, or response not found.')
        except Exception as ex:
            log_error('assessmentsv2.views.AssessmentTakenQuestionComments.get()', ex)
            raise Http404

    def post(self, request, bank_id, taken_id, question_id, format='json'):
        try:
            set_user(request)
            activate_managers(request)
            cm = get_session_data(request, 'cm')
            am = get_session_data(request, 'am')

            data = get_data_from_request(request)

            verify_keys_present(data, ['text'])

            # try to get the book for this bank. If no book, create it using Jeff's work-around
            # try:
            #     book_id = bank_id.replace('assessment.Bank','commenting.Book')
            #     book = cm.get_book(Id(book_id))
            # except NotFound:
            #     book = cm.get_comment_lookup_session_for_book(Id(bank_id))
            book = cm.get_book(Id(bank_id))

            bank = am.get_bank(clean_id(bank_id))
            first_section = bank.get_first_assessment_section(clean_id(taken_id))
            try:
                response = bank.get_response(first_section.ident, clean_id(question_id))
            except NotFound:
                raise IntegrityError

            if 'files' in data:
                comment_type = [FILE_COMMENT_RECORD_TYPE]
            else:
                comment_type = []
            form = book.get_comment_form_for_create(response.ident, comment_type)

            if 'text' in data:
                form.set_text(data['text'])
            # if 'rating' in data:
            #     form.set_rating(data['rating'])
            if 'files' in data:
                if len(data['files']) > 1:
                    raise ValueError('Only one file per comment')
                key = data['files'].keys()[0]
                form.set_file(DataInputStream(data['files'][key]), asset_name=key)

            new_comment = book.create_comment(form)

            data = new_comment.object_map

            # if 'files' in params:
            if 'fileId' in data:
                comment_obj = book.get_comment(Id(data['id']))
                data['file'] = comment_obj.get_file_url()

            set_session_data(request, 'cm', cm)
            set_session_data(request, 'am', am)
            return CreatedResponse(data)
        except IntegrityError:
            raise exceptions.APIException('Student has not responded -- you cannot comment yet.')
        except ValueError:
            raise exceptions.APIException('Only one file per comment allowed. Create multiple '
                                          'comments if you need to upload multiple files.')
        except KeyError as ex:
            raise exceptions.APIException(*ex.args)
        except PermissionDenied:
            raise exceptions.AuthenticationFailed('Permission denied. You do not '
                                                  'have rights to create comments.')
        except NotFound:
            raise exceptions.APIException('AssessmentTaken, bank, question, or response not found.')
        except Exception as ex:
            log_error('assessmentsv2.views.AssessmentTakenQuestionComments.post()', ex)
            raise Http404

class AssessmentTakenQuestionFiles(APIView):
    """
    Returns the files for the specified question
    api/v2/assessment/banks/<bank_id>/assessmentstaken/<taken_id>/questions/<question_id>/files/

    GET only
    """

    def get(self, request, bank_id, taken_id, question_id, format='json'):
        try:
            set_user(request)
            activate_managers(request)
            am = get_session_data(request, 'am')

            bank = am.get_bank(clean_id(bank_id))
            first_section = bank.get_first_assessment_section(clean_id(taken_id))
            question = bank.get_question(first_section.ident, clean_id(question_id))
            try:
                question_files = question.get_files()
                data = {
                    'manip' : question_files['manip'],
                    'front' : question_files['frontView'],
                    'side'  : question_files['sideView'],
                    'top'   : question_files['topView']
                }
            except:
                data = {'details': 'No files for this question.'}

            set_session_data(request, 'am', am)
            return Response(data)
        except PermissionDenied:
            raise exceptions.AuthenticationFailed('Permission denied. You do not '
                                                  'have rights to take assessments '
                                                  'in this bank.')
        except IllegalState:
            raise exceptions.APIException('Assessment already completed.')
        except NotFound:
            raise exceptions.APIException('AssessmentTaken not found.')
        except Exception as ex:
            log_error('assessmentsv2.views.AssessmentTakenQuestionFiles.get()', ex)
            raise Http404


class AssessmentTakenQuestionResponses(APIView):
    """
    Gets the student responses to a question
    api/v2/assessment/banks/<bank_id>/assessmentstaken/<taken_id>/questions/<question_id>/responses/

    GET only

    Example (for an Ortho3D manipulatable - label type):
        [{"integerValues": {
            "frontFaceValue" : 0,
            "sideFaceValue"  : 1,
            "topFaceValue"   : 2
        },{
            "frontFaceValue" : 3,
            "sideFaceValue"  : 1,
            "topFaceValue"   : 2
        }]
    """

    def get(self, request, bank_id, taken_id, question_id, format='json'):
        try:
            set_user(request)
            activate_managers(request)
            am = get_session_data(request, 'am')

            params = get_data_from_request(request)

            bank = am.get_bank(clean_id(bank_id))
            first_section = bank.get_first_assessment_section(clean_id(taken_id))
            response = bank.get_response(first_section.ident, clean_id(question_id))
            data = response.object_map

            # if 'files' in params:
            if 'fileIds' in data:
                data['files'] = response.get_files()  # return files by default, until we have a list

            set_session_data(request, 'am', am)
            return Response(data)
        except PermissionDenied:
            raise exceptions.AuthenticationFailed('Permission denied. You do not '
                                                  'have rights to take assessments '
                                                  'in this bank.')
        except NotFound:
            raise exceptions.APIException('AssessmentTaken, bank, question, or response not found.')
        except Exception as ex:
            log_error('assessmentsv2.views.AssessmentTakenQuestionResponses.get()', ex)
            raise Http404


class AssessmentTakenQuestionSolution(APIView):
    """
    Returns the solution / explanation when available
    api/v2/assessment/banks/<bank_id>/assessmentstaken/<taken_id>/questions/<question_id>/solution/

    GET only

    Example (for an Ortho3D manipulatable - label type):
        {}
    """

    def get(self, request, bank_id, taken_id, question_id, format='json'):
        try:
            set_user(request)
            activate_managers(request)
            am = get_session_data(request, 'am')

            bank = am.get_bank(clean_id(bank_id))
            taken = bank.get_assessment_taken(clean_id(taken_id))
            try:
                solution = taken.get_solution_for_question(clean_id(question_id))
            except IllegalState:
                solution = 'No solution available.'

            set_session_data(request, 'am', am)
            return Response(solution)
        except PermissionDenied:
            raise exceptions.AuthenticationFailed('Permission denied. You do not '
                                                  'have rights to take assessments '
                                                  'in this bank.')
        except IllegalState:
            raise exceptions.APIException('You need to submit a response first.')
        except NotFound:
            raise exceptions.APIException('AssessmentTaken or bank not found.')
        except InvalidArgument:
            raise exceptions.APIException('choiceIds should be a list for multiple-choice questions.')
        except Exception as ex:
            log_error('assessmentsv2.views.AssessmentTakenQuestionSolution.post()', ex)
            raise Http404




class AssessmentTakenQuestionStatus(APIView):
    """
    Gets the current status of a question in a taken -- responded to or not, correct or incorrect
    response (if applicable)
    api/v2/assessment/banks/<bank_id>/assessmentstaken/<taken_id>/questions/<question_id>/status/

    GET only

    Example (for an Ortho3D manipulatable - label type):
        {"responded": True,
         "correct"  : False
        }
    """

    def get(self, request, bank_id, taken_id, question_id, format='json'):
        try:
            set_user(request)
            activate_managers(request)
            am = get_session_data(request, 'am')

            bank = am.get_bank(clean_id(bank_id))
            first_section = bank.get_first_assessment_section(clean_id(taken_id))
            question = bank.get_question(first_section.ident, clean_id(question_id))

            data = get_question_status(bank, first_section, clean_id(question_id))

            set_session_data(request, 'am', am)
            return Response(data)
        except PermissionDenied:
            raise exceptions.AuthenticationFailed('Permission denied. You do not '
                                                  'have rights to take assessments '
                                                  'in this bank.')
        except NotFound:
            raise exceptions.APIException('AssessmentTaken, bank, or question not found.')
        except Exception as ex:
            log_error('assessmentsv2.views.AssessmentTakenQuestionStatus.get()', ex)
            raise Http404

class AssessmentTakenQuestionSubmit(APIView):
    """
    Submits a student response for the specified question
    Returns correct or not
    Does NOTHING to flag if the section is done or not...
    api/v2/assessment/banks/<bank_id>/assessmentstaken/<taken_id>/questions/<question_id>/submit/

    POST only

    Example (for an Ortho3D manipulatable - label type):
        {"integerValues":{
                "frontFaceValue" : 0,
                "sideFaceValue"  : 1,
                "topFaceValue"   : 2
            }
        }
    """

    def post(self, request, bank_id, taken_id, question_id, format='json'):
        try:
            set_user(request)
            activate_managers(request)
            am = get_session_data(request, 'am')
            data = get_data_from_request(request)

            bank = am.get_bank(clean_id(bank_id))
            first_section = bank.get_first_assessment_section(clean_id(taken_id))
            question = bank.get_question(first_section.ident, clean_id(question_id))
            response_form = bank.get_response_form(assessment_section_id=first_section.ident,
                                                   item_id=question.ident)

            if isinstance(data, QueryDict):
                data = data.copy()
                if len(request.FILES) > 0:
                    # for some reason files are only copied as '',
                    # so need to re-set this, if sent
                    data['files'] = request.FILES

            if 'type' not in data:
                # kind of a hack
                data['type'] = question.object_map['recordTypeIds'][0]
                data['type'] = data['type'].replace('question-record-type',
                                                    'answer-record-type')

            update_form = update_response_form(data, response_form)
            bank.submit_response(first_section.ident, question.ident, update_form)
            # the above code logs the response in Mongo
            
            # Now need to actually check the answers against the
            # item answers.
            answers = bank.get_answers(first_section.ident, question.ident)
            # compare these answers to the submitted response

            correct = validate_response(data, answers)

            feedback = 'No feedback available.'

            return_data = {
                'correct'  : correct,
                'feedback' : feedback
            }
            if correct:
                # update with item solution, if available
                try:
                    taken = bank.get_assessment_taken(clean_id(taken_id))
                    feedback = taken.get_solution_for_question(clean_id(question_id))['explanation']
                    return_data.update({
                        'feedback': feedback
                    })
                except (IllegalState, TypeError):
                    pass
            else:
                # update with answer feedback, if available
                # for now, just support this for multiple choice questions...
                if is_multiple_choice(data):
                    submissions = get_response_submissions(data)
                    answers = bank.get_answers(first_section.ident, question.ident)
                    wrong_answers = [a for a in answers
                                     if a.genus_type == Type(**ANSWER_GENUS_TYPES['wrong-answer'])]
                    feedback_strings = []
                    confused_los = []
                    for wrong_answer in wrong_answers:
                        if wrong_answer.get_choice_ids()[0] in submissions:
                            try:
                                feedback_strings.append(wrong_answer.feedback)
                            except KeyError:
                                pass
                            try:
                                confused_los += wrong_answer.confused_learning_objective_ids
                            except KeyError:
                                pass
                    if len(feedback_strings) > 0:
                        feedback = '; '.join(feedback_strings)
                        return_data.update({
                            'feedback': feedback
                        })
                    if len(confused_los) > 0:
                        return_data.update({
                            'confusedLearningObjectiveIds': confused_los
                        })

            set_session_data(request, 'am', am)
            return Response(return_data)
        except PermissionDenied:
            raise exceptions.AuthenticationFailed('Permission denied. You do not '
                                                  'have rights to take assessments '
                                                  'in this bank.')
        except IllegalState:
            raise exceptions.APIException('Assessment already completed.')
        except NotFound:
            raise exceptions.APIException('AssessmentTaken or bank not found.')
        except InvalidArgument:
            raise exceptions.APIException('choiceIds should be a list for multiple-choice questions.')
        except Exception as ex:
            log_error('assessmentsv2.views.AssessmentTakenQuestionSubmit.post()', ex)
            raise Http404


class AssessmentTakenQuestionSurrender(APIView):
    """
    Returns the answer if a student gives up and wants to just see the answer
    api/v2/assessment/banks/<bank_id>/assessmentstaken/<taken_id>/questions/<question_id>/surrender/

    POST only, no data

    Example (for an Ortho3D manipulatable - label type):
        {}
    """

    def post(self, request, bank_id, taken_id, question_id, format='json'):
        try:
            set_user(request)
            activate_managers(request)
            am = get_session_data(request, 'am')

            bank = am.get_bank(clean_id(bank_id))
            first_section = bank.get_first_assessment_section(clean_id(taken_id))
            question = bank.get_question(first_section.ident, clean_id(question_id))
            response_form = bank.get_response_form(assessment_section_id=first_section.ident,
                                                   item_id=question.ident)

            response_form.display_name = 'I surrendered'
            bank.submit_response(first_section.ident, question.ident, response_form)
            # the above code logs the response in Mongo

            answers = bank.get_answers(first_section.ident, question.ident)
            data = extract_items(request, answers)

            set_session_data(request, 'am', am)
            return Response(data)
        except PermissionDenied:
            raise exceptions.AuthenticationFailed('Permission denied. You do not '
                                                  'have rights to take assessments '
                                                  'in this bank.')
        except IllegalState:
            raise exceptions.APIException('Assessment already completed.')
        except NotFound:
            raise exceptions.APIException('AssessmentTaken or bank not found.')
        except Exception as ex:
            log_error('assessmentsv2.views.AssessmentTakenQuestionSurrender.post()', ex)
            raise Http404


class BankAuthorizations(APIView):
    """
    Gets the authorizations for the given assessment bank

    GET only
    """

    def get(self, request, bank_id, format='json'):
        try:
            set_user(request)
            activate_managers(request)
            am = get_session_data(request, 'am')

            bank = get_active_bank(request, bank_id)

            auths = {
                'assessments'       : {
                    'can_create': bank.can_author_assessments(),
                    'can_delete': bank.can_delete_assessments(),
                    'can_lookup': bank.can_lookup_assessments(),
                    'can_take'  : bank.can_take_assessments(),
                    'can_update': bank.can_update_assessments()
                },
                'assessments_offered'       : {
                    'can_create': bank.can_create_assessments_offered(),
                    'can_delete': bank.can_delete_assessments_offered(),
                    'can_lookup': bank.can_lookup_assessments_offered(),
                    'can_update': bank.can_update_assessments_offered()
                },
                'assessments_taken'       : {
                    'can_create': bank.can_create_assessments_taken(),
                    'can_delete': bank.can_delete_assessments_taken(),
                    'can_lookup': bank.can_lookup_assessments_taken(),
                    'can_update': bank.can_update_assessments_taken()
                },
                'assessment_banks'  : {
                    'can_create': am.can_create_banks(),
                    'can_delete': am.can_delete_banks(),
                    'can_lookup': am.can_lookup_banks(),
                    'can_update': am.can_update_banks()
                },
                'items'                 : {
                    'can_create': bank.can_create_items(),
                    'can_delete': bank.can_delete_items(),
                    'can_lookup': bank.can_lookup_items(),
                    'can_update': bank.can_update_items()
                }
            }

            set_session_data(request, 'bank', bank)
            set_session_data(request, 'am', am)
            return Response(auths)
        except PermissionDenied:
            raise exceptions.AuthenticationFailed('Permission denied. You do not '
                                                  'have rights to view authorizations '
                                                  'in this bank.')
        except Exception as ex:
            log_error('assessmentsv2.views.BankAuthorizations.get()', ex)
            raise Http404
