import os
import json

from django.db import IntegrityError
from django.http import HttpResponse

from dlkit_django.errors import *
from dlkit_django.primitives import Type

from rest_framework.response import Response
from rest_framework.renderers import BrowsableAPIRenderer

from utilities import assessment as autils
from utilities import general as gutils
from producer.views import ProducerAPIViews, DLJSONRenderer


class AssessmentBanksList(ProducerAPIViews):
    """
    List all available assessment banks.
    api/v1/assessment/banks/

    POST allows you to create a new assessment bank, requires two parameters:
      * name
      * description

    Note that for RESTful calls, you need to set the request header
    'content-type' to 'application/json'

    Example (note the use of double quotes!!):
      {"name" : "a new bank","description" : "this is a test"}
    """
    renderer_classes = (DLJSONRenderer, BrowsableAPIRenderer)

    def get(self, request, format=None):
        """
        List all available assessment banks
        """
        try:
            if len(self.data) == 0:
                assessment_banks = self.am.banks
            else:
                querier = self.am.get_bank_query()

                allowable_query_terms = ['displayName', 'description']
                if any(term in self.data for term in allowable_query_terms):
                    querier = gutils.config_osid_object_querier(querier, self.data)
                    assessment_banks = self.am.get_banks_by_query(querier)
                else:
                    assessment_banks = self.am.banks

            banks = gutils.extract_items(request, assessment_banks)
            return Response(banks)
        except PermissionDenied as ex:
            gutils.handle_exceptions(ex)

    def post(self, request, format=None):
        """
        Create a new assessment bank, if authorized
        Create a new group in IS&T Membership service

        """
        try:
            form = self.am.get_bank_form_for_create([])

            form = gutils.set_form_basics(form, self.data)

            new_bank = gutils.convert_dl_object(self.am.create_bank(form))

            return gutils.CreatedResponse(new_bank)
        except (PermissionDenied, InvalidArgument) as ex:
            gutils.handle_exceptions(ex)


class AssessmentBanksDetail(ProducerAPIViews):
    """
    Shows details for a specific assessment bank.
    api/v1/assessment/banks/<bank_id>/

    GET, PUT, DELETE
    PUT will update the assessment bank. Only changed attributes need to be sent.
    DELETE will remove the assessment bank.

    Note that for RESTful calls, you need to set the request header
    'content-type' to 'application/json'

    Example (note the use of double quotes!!):
       {"name" : "a new bank"}
    """
    renderer_classes = (DLJSONRenderer,BrowsableAPIRenderer)

    def delete(self, request, bank_id, format=None):
        try:
            data = self.am.delete_bank(gutils.clean_id(bank_id))
            return gutils.DeletedResponse(data)
        except (PermissionDenied, IllegalState) as ex:
            gutils.handle_exceptions(ex)

    def get(self, request, bank_id, format=None):
        try:
            assessment_bank = self.am.get_bank(gutils.clean_id(bank_id))
            bank = gutils.convert_dl_object(assessment_bank)
            gutils.update_links(request, bank)
            return Response(bank)
        except (PermissionDenied, NotFound) as ex:
            gutils.handle_exceptions(ex)

    def put(self, request, bank_id, format=None):
        try:
            form = self.am.get_bank_form_for_update(gutils.clean_id(bank_id))

            form = gutils.set_form_basics(form, self.data)

            updated_bank = self.am.update_bank(form)
            bank = gutils.convert_dl_object(updated_bank)
            gutils.update_links(request, bank)
            return gutils.UpdatedResponse(bank)
        except (PermissionDenied, InvalidArgument) as ex:
            gutils.handle_exceptions(ex)


class ItemsList(ProducerAPIViews):
    """
    Return list of items the user has access to. Make sure to embed
    the question and answers in the JSON.
    api/v1/assessment/items/

    GET, POST
    POST creates a new item. You need to specify the bankId for this

    Note that for RESTful calls, you need to set the request header
    'content-type' to 'application/json'

    Example (note the use of double quotes!!):
       This UI: {"name" : "an assessment item","description" : "this is a hard quiz problem","question":{"type":"question-record-type%3Aresponse-string%40ODL.MIT.EDU","questionString":"Where am I?"},"answers":[{"type":"answer-record-type%3Aresponse-string%40ODL.MIT.EDU","responseString":"Here"}]}
   """
    renderer_classes = (DLJSONRenderer,BrowsableAPIRenderer)

    def get(self, request, bank_id=None, format=None):
        try:
            if bank_id is None:
                item_lookup_session = autils.get_session(self.am, 'item', 'lookup')
                item_query_session = autils.get_session(self.am, 'item', 'query')

                item_lookup_session.use_federated_bank_view()
                item_query_session.use_federated_bank_view()
            else:
                item_query_session = item_lookup_session = self.am.get_bank(gutils.clean_id(bank_id))

            if (len(self.data) == 0 or
                    (len(self.data) == 1 and self.data.keys()[0] == 'files')):
                items = item_lookup_session.get_items()
            else:
                allowable_query_terms = ['maximumDifficulty', 'minimumDifficulty',
                                         'maximumDiscrimination', 'mininumDiscrimination',
                                         'displayName', 'learningObjectiveId',
                                         'description']
                if any(term in self.data for term in allowable_query_terms):
                    querier = item_query_session.get_item_query()
                    querier = gutils.config_osid_object_querier(querier, self.data)
                    items = item_query_session.get_items_by_query(querier)
                else:
                    items = item_lookup_session.get_items()

            data = gutils.extract_items(request, items)
            if 'files' in self.data:
                for item in data['data']['results']:
                    # Without complete authz, not a great way to handle
                    # this -- ignore ?files on items where user has no permissions.
                    # Ideally, they wouldn't even have these items in their list...
                    bank = autils.get_object_bank(self.am, gutils.clean_id(item['id']), 'item')
                    try:
                        dlkit_item = bank.get_item(gutils.clean_id(item['id']))

                        if 'fileIds' in item:
                            item['files'] = dlkit_item.get_files()
                        if item['question'] and 'fileIds' in item['question']:
                            item['question']['files'] = dlkit_item.get_question().get_files()
                    except PermissionDenied:
                        pass

            return Response(data)
        except (PermissionDenied, IntegrityError) as ex:
            gutils.handle_exceptions(ex)

    def post(self, request, bank_id=None, format=None):
        try:
            if bank_id is None:
                expected = ['bankId']
                gutils.verify_keys_present(self.data, expected)
                bank_id = self.data['bankId']

            bank = self.am.get_bank(gutils.clean_id(bank_id))
            new_item = autils.create_new_item(bank, self.data)
            # create questions and answers if they are part of the
            # input data. There must be a better way to figure out
            # which attributes I should set, given the
            # question type?
            if 'question' in self.data:
                question = self.data['question']
                if isinstance(question, basestring):
                    question = json.loads(question)
                q_type = Type(question['type'])
                qfc = bank.get_question_form_for_create(item_id=new_item.ident,
                                                        question_record_types=[q_type])
                qfc = autils.update_question_form(request, question, qfc, create=True)

                if 'genus' in question:
                    qfc.genus_type = Type(question['genus'])

                if ('fileIds' in new_item.object_map and
                    len(new_item.object_map['fileIds'].keys()) > 0):
                    # add these files to the question, too
                    file_ids = new_item.object_map['fileIds']
                    qfc = autils.add_file_ids_to_form(qfc, file_ids)

                new_question = bank.create_question(qfc)

            if 'answers' in self.data:
                answers = self.data['answers']
                if isinstance(answers, basestring):
                    answers = json.loads(answers)
                for answer in answers:
                    a_types = autils.get_answer_records(answer)

                    afc = bank.get_answer_form_for_create(new_item.ident,
                                                          a_types)

                    if 'multi-choice' in answer['type']:
                        # because multiple choice answers need to match to
                        # the actual MC3 ChoiceIds, NOT the index passed
                        # in by the consumer.
                        if not new_question:
                            raise NullArgument('Question')
                        afc = autils.update_answer_form(answer, afc, new_question)
                    else:
                        afc = autils.update_answer_form(answer, afc)

                    afc = autils.set_answer_form_genus_and_feedback(answer, afc)
                    new_answer = bank.create_answer(afc)

            full_item = bank.get_item(new_item.ident)
            data = gutils.convert_dl_object(full_item)
            return gutils.CreatedResponse(data)
        except (KeyError, IntegrityError, PermissionDenied, Unsupported, InvalidArgument,
                NullArgument) as ex:
            gutils.handle_exceptions(ex)


class ItemDetails(ProducerAPIViews):
    """
    Get item details for the given bank
    api/v1/assessment/items/<item_id>/

    GET, PUT, DELETE
    PUT to modify an existing item. Include only the changed parameters.
    DELETE to remove from the repository.

    Note that for RESTful calls, you need to set the request header
    'content-type' to 'application/json'

    Example (note the use of double quotes!!):
       {"name" : "an updated item"}
    """
    renderer_classes = (DLJSONRenderer, BrowsableAPIRenderer)

    def delete(self, request, item_id, format=None):
        try:
            bank = autils.get_object_bank(self.am,
                                          item_id,
                                          object_type='item',
                                          bank_id=None)
            data = bank.delete_item(gutils.clean_id(item_id))
            return gutils.DeletedResponse(data)
        except PermissionDenied as ex:
            gutils.handle_exceptions(ex)
        except IllegalState as ex:
            gutils.handle_exceptions(type(ex)('This Item is being used in one or more '
                                              'Assessments. Delink it first, before '
                                              'deleting it.'))

    def get(self, request, item_id, format=None):
        try:
            bank = autils.get_object_bank(self.am,
                                          item_id,
                                          object_type='item',
                                          bank_id=None)

            item = bank.get_item(gutils.clean_id(item_id))
            data = gutils.convert_dl_object(item)

            gutils.update_links(request, data)

            if 'fileIds' in data:
                data['files'] = item.get_files()
            if data['question'] and 'fileIds' in data['question']:
                data['question']['files'] = item.get_question().get_files()

            try:
                if 'renderable_edxml' in self.data:
                    data['texts']['edxml'] = item.get_edxml_with_aws_urls()
            except AttributeError:
                pass

            return Response(data)
        except (PermissionDenied, NotFound) as ex:
            gutils.handle_exceptions(ex)

    def put(self, request, item_id, format=None):
        try:
            bank = autils.get_object_bank(self.am,
                                          item_id,
                                          object_type='item',
                                          bank_id=None)

            if any(attr in self.data for attr in ['displayName', 'description', 'learningObjectiveIds',
                                                  'attempts', 'markdown', 'rerandomize', 'showanswer',
                                                  'weight', 'difficulty', 'discrimination']):
                form = bank.get_item_form_for_update(gutils.clean_id(item_id))

                form = gutils.set_form_basics(form, self.data)

                if 'learningObjectiveIds' in self.data:
                    form = autils.set_item_learning_objectives(self.data, form)

                # update the item before the questions / answers,
                # because otherwise the old form will over-write the
                # new question / answer data

                # for edX items, update any metadata passed in
                if 'genusTypeId' not in self.data:
                    if len(form._my_map['recordTypeIds']) > 0:
                        self.data['type'] = form._my_map['recordTypeIds'][0]
                    else:
                        self.data['type'] = ''

                form = autils.update_item_metadata(self.data, form)

                updated_item = bank.update_item(form)
            else:
                updated_item = bank.get_item(gutils.clean_id(item_id))

            if 'question' in self.data:
                question = self.data['question']
                existing_question = updated_item.get_question()
                q_id = existing_question.ident

                if 'genusTypeId' not in question:
                    question['genusTypeId'] = existing_question.object_map['recordTypeIds'][0]

                qfu = bank.get_question_form_for_update(q_id)
                qfu = autils.update_question_form(request, question, qfu)
                updated_question = bank.update_question(qfu)

            if 'answers' in self.data:
                for answer in self.data['answers']:
                    if 'id' in answer:
                        a_id = gutils.clean_id(answer['id'])
                        afu = bank.get_answer_form_for_update(a_id)
                        afu = autils.update_answer_form(answer, afu)
                        bank.update_answer(afu)
                    else:
                        a_types = autils.get_answer_records(answer)
                        afc = bank.get_answer_form_for_create(gutils.clean_id(item_id),
                                                              a_types)
                        afc = autils.set_answer_form_genus_and_feedback(answer, afc)
                        if 'multi-choice' in answer['genusTypeId']:
                            # because multiple choice answers need to match to
                            # the actual MC3 ChoiceIds, NOT the index passed
                            # in by the consumer.
                            question = updated_item.get_question()
                            afc = autils.update_answer_form(answer, afc, question)
                        else:
                            afc = autils.update_answer_form(answer, afc)
                        bank.create_answer(afc)

            full_item = bank.get_item(gutils.clean_id(item_id))

            data = gutils.convert_dl_object(full_item)
            return gutils.UpdatedResponse(data)
        except (PermissionDenied, Unsupported, InvalidArgument) as ex:
            gutils.handle_exceptions(ex)


class ItemDownload(ProducerAPIViews):
    """
    Download a single item.
    api/v1/assessment/items/<item_id>/download/

    GET
    """
    def get(self, request, item_id, format=None):
        try:
            bank = autils.get_object_bank(self.am,
                                          item_id,
                                          'item')
            item = bank.get_item(gutils.clean_id(item_id))

            filename, olx = item.export_standalone_olx()

            response = HttpResponse(content_type="application/tar")
            response['Content-Disposition'] = 'attachment; filename=%s' % filename
            olx.seek(0, os.SEEK_END)
            response.write(olx.getvalue())
            olx.close()

            return response
        except (PermissionDenied, InvalidArgument, NotFound) as ex:
            gutils.handle_exceptions(ex)


class ItemObjectives(ProducerAPIViews):
    """
    Get item learning objectives for the given bank
    api/v1/assessment/items/<item_id>/objectives/

    GET

    Note that for RESTful calls, you need to set the request header
    'content-type' to 'application/json'

    Example (note the use of double quotes!!):
       {"name" : "an updated item"}
    """
    renderer_classes = (DLJSONRenderer, BrowsableAPIRenderer)

    def get(self, request, item_id, format=None):
        try:
            bank = autils.get_object_bank(self.am,
                                          item_id,
                                          object_type='item',
                                          bank_id=None)

            item = bank.get_item(gutils.clean_id(item_id))
            try:
                data = gutils.extract_items(request, item.get_learning_objectives())
            except KeyError:
                pass
            return Response(data)
        except (PermissionDenied, NotFound) as ex:
            gutils.handle_exceptions(ex)