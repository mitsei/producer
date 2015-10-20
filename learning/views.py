import json

from django.db import IntegrityError

from dlkit_django.errors import *
from dlkit_django.primitives import Type

from rest_framework.response import Response
from rest_framework.renderers import BrowsableAPIRenderer

from utilities import assessment as autils
from utilities import general as gutils
from producer.views import ProducerAPIViews, DLJSONRenderer

OUTCOME_GENUS_TYPE = Type('mc3-objective%3Amc3.learning.outcome%40MIT-OEIT')


class ObjectivesList(ProducerAPIViews):
    """
    Return list of objectives from MC3; gets from all banks...

    api/v1/learning/objectives/

    GET

    Note that for RESTful calls, you need to set the request header
    'content-type' to 'application/json'

    Example (note the use of double quotes!!):
       {"displayName" : "a learning objective",
        "description" : "Do XYZ"}
   """
    renderer_classes = (DLJSONRenderer,BrowsableAPIRenderer)

    def get(self, request, format=None):
        try:
            objectives = []
            for bank in self.lm.objective_banks:
                objectives += list(bank.get_objectives_by_genus_type(OUTCOME_GENUS_TYPE))

            objectives = gutils.extract_items(request, objectives)
            return Response(objectives)
        except (PermissionDenied, IntegrityError) as ex:
            gutils.handle_exceptions(ex)


class ObjectiveDetails(ProducerAPIViews):
    """
    Get objective details for the given ID
    api/v1/learning/objectives/<objective_id>/

    GET, PUT, DELETE
    PUT to modify an existing objective. Include only the changed parameters.
    DELETE to remove from the objective bank.

    Note that for RESTful calls, you need to set the request header
    'content-type' to 'application/json'

    Example (note the use of double quotes!!):
       {"displayName" : "an updated objective"}
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
