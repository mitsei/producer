import os
import re
import json

from assessments.types import *

from records.registry import ANSWER_GENUS_TYPES, ANSWER_RECORD_TYPES

from dlkit_django import PROXY_SESSION, RUNTIME
from dlkit_django.errors import NotFound, InvalidArgument, Unsupported, NullArgument
from dlkit_django.primitives import Type, DataInputStream, Id
from dlkit_django.proxy_example import TestRequest

from django.utils.http import quote

from utilities import general as gutils


def add_file_ids_to_form(form, file_ids):
    """
    Add existing asset_ids to a form
    :param form:
    :param image_ids:
    :return:
    """
    for label, file_id in file_ids.iteritems():
        form.add_asset(Id(file_id['assetId']), label, Id(file_id['assetContentTypeId']))
    return form

def add_files_to_form(form, files):
    """
    Whether an item form or a question form
    :param form:
    :return:
    """
    def _clean(label):
        return re.sub(r'[^\w\d]', '_', label)

    def _get_file_label(file_path):
        # http://stackoverflow.com/questions/678236/how-to-get-the-filename-without-the-extension-from-a-path-in-python
        return os.path.splitext(os.path.basename(file_path))[0]

    def _get_file_extension(file_name):
        return os.path.splitext(os.path.basename(file_name))[-1]

    def _infer_display_name(text):
        text = text.strip()
        if text == '':
            return 'Unknown Display Name'
        if '_' not in text:
            return text

        if text.split('_')[0].startswith('lec'):
            first_part = text.split('_')[0]
            text = 'Lecture ' + first_part.split('lec')[-1] + '_' + text.split('_')[-1]
        elif text.split('_')[0].startswith('ps'):
            first_part = text.split('_')[0]
            text = 'Problem Set ' + first_part.split('ps')[-1] + '_' + text.split('_')[-1]
        elif text.split('_')[0].startswith('ex'):
            first_part = text.split('_')[0]
            text = 'Exam ' + first_part.split('ex')[-1] + '_' + text.split('_')[-1]

        if text.split('_')[-1].startswith('p'):
            second_part = text.split('_')[-1]
            text = text.split('_')[0] + ': Problem ' + second_part.split('p')[-1]
        elif text.split('_')[-1].startswith('Q'):
            second_part = text.split('_')[-1]
            text = text.split('_')[0] + ': Question ' + second_part.split('Q')[-1]
        return text

    for file_name, file_data in files.iteritems():
        # default assume is a file
        prettify_type = 'file'
        genus = EDX_FILE_ASSET_GENUS_TYPE
        file_type = _get_file_extension(file_name).lower()
        label = _get_file_label(file_name)
        if file_type:
            if 'png' in file_type:
                ac_genus_type = PNG_ASSET_CONTENT_GENUS_TYPE
                genus = EDX_IMAGE_ASSET_GENUS_TYPE
                prettify_type = 'image'
            elif 'jpg' in file_type:
                ac_genus_type = JPG_ASSET_CONTENT_GENUS_TYPE
                genus = EDX_IMAGE_ASSET_GENUS_TYPE
                prettify_type = 'image'
            elif 'json' in file_type:
                ac_genus_type = JSON_ASSET_CONTENT_GENUS_TYPE
            elif 'tex' in file_type:
                ac_genus_type = LATEX_ASSET_CONTENT_GENUS_TYPE
            elif 'javascript' in file_type:
                ac_genus_type = JAVASCRIPT_ASSET_CONTENT_GENUS_TYPE
            else:
                ac_genus_type = GENERIC_ASSET_CONTENT_GENUS_TYPE
        else:
            ac_genus_type = GENERIC_ASSET_CONTENT_GENUS_TYPE

        display_name = _infer_display_name(label) + ' ' + prettify_type.title()
        description = ('Supporting ' + prettify_type + ' for assessment Question: ' +
                       _infer_display_name(label))
        form.add_file(file_data, _clean(label), genus, ac_genus_type, display_name, description)
    return form

def create_new_item(bank, data):
    if ('question' in data and
        'genusTypeId' in data['question'] and
        'edx' in data['question']['genusTypeId']):
        # should have body / setup
        # should have list of choices
        # should have set of right answers
        # metadata (if not present, it is okay):
        #  * max attempts
        #  * weight
        #  * showanswer
        #  * rerandomize
        #  * author username
        #  * student display name
        #  * author comments
        #  * extra python script
        # any files?
        form = bank.get_item_form_for_create([EDX_ITEM_RECORD_TYPE])
        form.display_name = data['displayName']
        form.description = data['description']
        form.set_genus_type(EDX_MULTI_CHOICE_PROBLEM_TYPE)

        if 'learningObjectiveIds' in data:
            form = set_item_learning_objectives(data, form)

        expected = ['question']
        gutils.verify_keys_present(data, expected)

        expected = ['questionString']
        gutils.verify_keys_present(data['question'], expected)

        form.add_text(data['question']['questionString'], 'questionString')

        optional = ['python_script','latex','edxml','solution']
        for opt in optional:
            if opt in data:
                form.add_text(data[opt], opt)

        metadata = ['attempts','markdown','rerandomize','showanswer','weight']
                    # 'author','author_comments','student_display_name']
        for datum in metadata:
            if datum in data:
                method = getattr(form, 'add_' + datum)
                method(data[datum])

        irt = ['difficulty','discrimination']
        for datum in irt:
            if datum in data:
                method = getattr(form, 'set_' + datum + '_value')
                method(data[datum])

        if 'files' in data:
            files_list = {}
            for filename, file in data['files'].iteritems():
                files_list[filename] = DataInputStream(file)
            form = add_files_to_form(form, files_list)
    else:
        form = bank.get_item_form_for_create([])
        form.display_name = str(data['displayName'])
        form.description = str(data['description'])
        if 'genusTypeId' in data:
            form.set_genus_type(Type(data['genusTypeId']))

        if 'learningObjectiveIds' in data:
            form = set_item_learning_objectives(data, form)

    new_item = bank.create_item(form)
    return new_item

def get_answer_records(answer):
    """answer is a dictionary"""
    # check for wrong-answer genus type to get the right
    # record types for feedback
    a_type = Type(answer['type'])
    if 'genus' in answer and answer['genus'] == str(Type(**ANSWER_GENUS_TYPES['wrong-answer'])):
        a_types = [a_type, Type(**ANSWER_RECORD_TYPES['answer-with-feedback'])]
    else:
        a_types = [a_type]
    return a_types

def get_choice_files(files):
    """
    Adapted from http://stackoverflow.com/questions/4558983/slicing-a-dictionary-by-keys-that-start-with-a-certain-string
    :param files:
    :return:
    """
    # return {k:v for k,v in files.iteritems() if k.startswith('choice')}
    return dict((k, files[k]) for k in files.keys() if k.startswith('choice'))

def get_object_bank(manager, object_id, object_type='item', bank_id=None):
    """Get the object's bank even without the bankId"""
    # primarily used for Item and AssessmentsOffered
    if bank_id is None:
        lookup_session = get_session(manager, object_type, 'lookup')
        object_ = getattr(lookup_session, 'get_{0}'.format(object_type))(gutils.clean_id(object_id))
        bank_id = object_.object_map['bankId']
    return manager.get_bank(gutils.clean_id(bank_id))

def get_object_bank_from_request(request):
    """parse out the right params before passing to get_object_bank
    Do NOT use the convenience methods here with session, etc."""
    valid_params = ['/assessment/items/']
    path = request.path
    if any(p in path for p in valid_params):
        test_request = TestRequest(username=request.user.username)
        condition = PROXY_SESSION.get_proxy_condition()
        condition.set_http_request(test_request)
        proxy = PROXY_SESSION.get_proxy(condition)
        am = RUNTIME.get_service_manager('ASSESSMENT', proxy=proxy)
        try:
            if '/items/' in path:
                object_id = path.split('/items/')[-1]
                return get_object_bank(am, object_id, object_type='item')
        except NotFound:
            return None
    else:
        return None

def get_ovs_file_set(files, index):
    choice_files = get_choice_files(files)
    if len(choice_files.keys()) % 2 != 0:
        raise NullArgument('Large and small image files')
    small_file = choice_files['choice' + str(index) + 'small']
    big_file = choice_files['choice' + str(index) + 'big']
    return small_file, big_file

def get_question_status(bank, section, question_id):
    """
    Return the question status of answered or not, and if so, right or wrong
    :param bank:
    :param section:
    :param question:
    :return:
    """
    try:
        student_response = bank.get_response(section.ident, question_id)
    except NotFound:
        student_response = None

    if student_response:
        # Now need to actually check the answers against the
        # item answers.
        answers = bank.get_answers(section.ident, question_id)
        # compare these answers to the submitted response
        response = student_response._my_map
        response.update({
            'type' : str(response['recordTypeIds'][0]).replace('answer-record-type', 'answer-record-type')
        })
        correct = validate_response(student_response._my_map, answers)
        data = {
            'responded' : True,
            'correct'   : correct
        }
    else:
        data = {
            'responded' : False
        }
    return data

def get_response_submissions(response):
    if response['type'] == 'answer-record-type%3Alabel-ortho-faces%40ODL.MIT.EDU':
        submission = response['integerValues']
    elif is_multiple_choice(response):
        if isinstance(response, dict):
            submission = response['choiceIds']
        else:
            submission = response.getlist('choiceIds')
    else:
        raise Unsupported
    return submission

def get_session(manager, object_type, session_type):
    """get session type for object, using the manager"""
    session = getattr(manager, 'get_{0}_{1}_session'.format(object_type, session_type))()
    session.use_federated_bank_view()
    return session

def is_multiple_choice(response):
    return any(mc in response['type'] for mc in ['multi-choice-ortho', 'multi-choice-edx'])

def is_right_answer(answer):
    return (answer.genus_type == Type(**ANSWER_GENUS_TYPES['right-answer']) or
            str(answer.genus_type) == 'GenusType%3ADEFAULT%40dlkit.mit.edu')

def set_answer_form_genus_and_feedback(answer, answer_form):
    """answer is a dictionary"""
    if 'genus' in answer:
        answer_form.genus_type = Type(answer['genus'])
        if answer['genus'] == str(Type(**ANSWER_GENUS_TYPES['wrong-answer'])):
            if 'feedback' in answer:
                answer_form._init_record(str(Type(**ANSWER_RECORD_TYPES['answer-with-feedback'])))
                answer_form.set_feedback(str(answer['feedback']))
            if 'confusedLearningObjectiveIds' in answer:
                if not isinstance(answer['confusedLearningObjectiveIds'], list):
                    los = [answer['confusedLearningObjectiveIds']]
                else:
                    los = answer['confusedLearningObjectiveIds']
                answer_form.set_confused_learning_objective_ids(los)
    else:
        # default is correct answer, if not supplied
        answer_form.set_genus_type(Type(**ANSWER_GENUS_TYPES['right-answer']))
        try:
            # remove the feedback components
            del answer_form._my_map['texts']['feedback']
            del answer_form._my_map['recordTypeIds'][str(Type(**ANSWER_RECORD_TYPES['answer-with-feedback']))]
        except KeyError:
            pass
    return answer_form

def set_item_learning_objectives(data, form):
    # over-writes current ID list
    id_list = []
    if not isinstance(data['learningObjectiveIds'], list):
        data['learningObjectiveIds'] = [data['learningObjectiveIds']]
    for _id in data['learningObjectiveIds']:
        if '@' in _id:
            id_list.append(Id(quote(_id)))
        else:
            id_list.append(Id(_id))
    form.set_learning_objectives(id_list)
    return form

def update_answer_form(answer, form, question=None):
    if answer['type'] == 'answer-record-type%3Ashort-text-answer%40ODL.MIT.EDU':
        form.set_text(answer['responseString'])
    elif answer['type'] == 'answer-record-type%3Alabel-ortho-faces%40ODL.MIT.EDU':
        if 'integerValues' in answer:
            form.set_face_values(front_face_value=answer['integerValues']['frontFaceValue'],
                                 side_face_value=answer['integerValues']['sideFaceValue'],
                                 top_face_value=answer['integerValues']['topFaceValue'])
    elif answer['type'] == 'answer-record-type%3Aeuler-rotation%40ODL.MIT.EDU':
        if 'integerValues' in answer:
            form.set_euler_angle_values(x_angle=answer['integerValues']['xAngle'],
                                        y_angle=answer['integerValues']['yAngle'],
                                        z_angle=answer['integerValues']['zAngle'])
    elif (answer['type'] == 'answer-record-type%3Amulti-choice-ortho%40ODL.MIT.EDU' or
          answer['type'] == 'answer-record-type%3Amulti-choice-edx%40ODL.MIT.EDU'):
        if question is None and 'choiceId' in answer:
            raise InvalidArgument('Missing question parameter for multi-choice')
        if not form.is_for_update():
            gutils.verify_keys_present(answer, ['choiceId'])
        if 'choiceId' in answer:
            # need to find the actual choiceIds (MC3 IDs), and match the index
            # to the one(s) passed in as part of the answer
            choices = question.get_choices()
            if int(answer['choiceId']) > len(choices):
                raise KeyError('Correct answer ' + str(answer['choiceId']) + ' is not valid. '
                               'Not that many choices!')
            elif int(answer['choiceId']) < 1:
                raise KeyError('Correct answer ' + str(answer['choiceId']) + ' is not valid. '
                               'Must be between 1 and # of choices.')

            # choices are 0 indexed
            choice_id = choices[int(answer['choiceId']) - 1]  # not sure if we need the OSID Id or string
            form.add_choice_id(choice_id['id'])  # just include the MongoDB ObjectId, not the whole dict
    elif answer['type'] == 'answer-record-type%3Afiles-submission%40ODL.MIT.EDU':
        # no correct answers here...
        return form
    else:
        raise Unsupported()

    return form


def update_item_metadata(data, form):
    """Update the metadata / IRT for an edX item

    :param request:
    :param data:
    :param form:
    :return:
    """
    if ('genusTypeId' in data and
            'edx' in data['genusTypeId']):
        valid_fields = ['attempts', 'markdown', 'rerandomize', 'showanswer', 'weight',
                        'difficulty', 'discrimination']
        for field in valid_fields:
            if field in data:
                if hasattr(form, 'add_' + field):
                    update_method = getattr(form, 'add_' + field)
                elif hasattr(form, 'set_' + field):
                    update_method = getattr(form, 'set_' + field)
                else:
                    update_method = getattr(form, 'set_' + field + '_value')
                # These forms are very strict (Java), so
                # have to know the exact input type. We
                # can't predict, so try a couple variations
                # if this fails...yes we're silly.
                val = data[field]
                try:
                    try:
                        try:
                            update_method(str(val))
                        except:
                            update_method(int(val))
                    except:
                        update_method(float(val))
                except:
                    raise LookupError
    else:
        # do nothing here for other types of problems
        pass

    return form

def update_question_form(request, question, form, create=False):
    """
    Check the create flag--if creating the question, then all 3 viewset files
    are needed. If not creating, can update only a single file.
    """
    if question['type'] == 'question-record-type%3Ashort-text-answer%40ODL.MIT.EDU':
        form.set_text(question['questionString'])
    elif (question['type'] == 'question-record-type%3Alabel-ortho-faces%40ODL.MIT.EDU' or
          question['type'] == 'question-record-type%3Aeuler-rotation%40ODL.MIT.EDU'):
        # need to differentiate on create here because update might not use all
        # the fields, whereas we need to enforce a minimum of data on create
        if create:
            if 'questionString' in question:
                form.set_text(question['questionString'])
            else:
                raise NullArgument('questionString')

            if 'firstAngle' in question:
                form.set_first_angle_projection(question['firstAngle'])

            files = request.FILES
            if 'manip' in files:
                form.set_manip(DataInputStream(files['manip']))
            else:
                raise NullArgument('manip file')
            if not ('frontView' in files and 'sideView' in files and 'topView' in files):
                raise NullArgument('All three view set attribute(s) required for Ortho-3D items.')
            else:
                form.set_ortho_view_set(front_view=DataInputStream(files['frontView']),
                                        side_view=DataInputStream(files['sideView']),
                                        top_view=DataInputStream(files['topView']))
        else:
            if 'questionString' in question:
                form.set_text(question['questionString'])
            if 'firstAngle' in question:
                form.set_first_angle_projection(question['firstAngle'])
            files = request.FILES
            if 'manip' in files:
                form.set_manip(DataInputStream(files['manip']))
            if 'frontView' in files:
                form.set_ovs_view(DataInputStream(files['frontView']), 'frontView')
            if 'sideView' in files:
                form.set_ovs_view(DataInputStream(files['sideView']), 'sideView')
            if 'topView' in files:
                form.set_ovs_view(DataInputStream(files['topView']), 'topView')
    elif question['type'] == 'question-record-type%3Amulti-choice-ortho%40ODL.MIT.EDU':
        # need to differentiate on create here because update might not use all
        # the fields, whereas we need to enforce a minimum of data on create
        if create:
            if 'questionString' in question:
                form.set_text(question['questionString'])
            else:
                raise NullArgument('questionString')

            if 'firstAngle' in question:
                form.set_first_angle_projection(question['firstAngle'])

            files = request.FILES
            if 'manip' in files:
                if 'promptName' in question:
                    manip_name = question['promptName']
                else:
                    manip_name = 'A manipulatable'

                # TODO set the manip name to the question['promptName']
                # and find the right choice / ovs to go with it
                if 'rightAnswer' in question:
                    right_answer_sm, right_answer_lg = get_ovs_file_set(files,
                                                                        question['rightAnswer'])
                    form.set_manip(DataInputStream(files['manip']),
                                   DataInputStream(right_answer_sm),
                                   DataInputStream(right_answer_lg),
                                   manip_name)
                else:
                    form.set_manip(DataInputStream(files['manip']),
                                   name=manip_name)

                if not ('choice0small' in files and 'choice0big' in files):
                    raise NullArgument('At least two choice set attribute(s) required for Ortho-3D items.')
                elif not ('choice1small' in files and 'choice1big' in files):
                    raise NullArgument('At least two choice set attribute(s) required for Ortho-3D items.')
                else:
                    choice_files = get_choice_files(files)
                    if len(choice_files.keys()) % 2 != 0:
                        raise NullArgument('Large and small image files')
                    num_files = len(choice_files.keys()) / 2
                    for i in range(0,num_files):
                        # this goes with the code ~20 lines above, where
                        # the right choice files are saved with the manip...
                        # but, regardless, make a choice for each provided
                        # viewset. Trust the consumer to pair things up
                        # properly. Need the choiceId to set the answer
                        if 'rightAnswer' in question and i == int(question['rightAnswer']):
                            # save this as a choice anyways
                            small_file = DataInputStream(choice_files['choice' + str(i) + 'small'])
                            big_file = DataInputStream(choice_files['choice' + str(i) + 'big'])
                        else:
                            small_file = DataInputStream(choice_files['choice' + str(i) + 'small'])
                            big_file = DataInputStream(choice_files['choice' + str(i) + 'big'])
                        if 'choiceNames' in question:
                            name = question['choiceNames'][i]
                        else:
                            name = ''
                        form.set_ortho_choice(small_asset_data=small_file,
                                              large_asset_data=big_file,
                                              name=name)
            else:
                # is a match the ortho manip, so has choice#manip and
                # primary object of viewset
                raise NullArgument('manip file')

        else:
            if 'questionString' in question:
                form.set_text(question['questionString'])
            if 'firstAngle' in question:
                form.set_first_angle_projection(question['firstAngle'])
            files = request.FILES
            if 'manip' in files:
                form.set_manip(DataInputStream(files['manip']))

            # TODO: change a choice set
    elif question['type'] == 'question-record-type%3Amulti-choice-edx%40ODL.MIT.EDU':
        if create:
            expected = ['questionString','choices']
            gutils.verify_keys_present(question, expected)

            should_be_list = ['choices']
            gutils.verify_min_length(question, should_be_list, 2)

            form.set_text(str(question['questionString']))
            # files get set after the form is returned, because
            # need the new_item
            # now manage the choices
            for ind, choice in enumerate(question['choices']):
                if isinstance(choice, dict):
                    form.add_choice(choice.get('text', ''),
                                    choice.get('name', 'Choice ' + str(int(ind) + 1)))
                else:
                    form.add_choice(choice, 'Choice ' + str(int(ind) + 1))
        else:
            if 'questionString' in question:
                form.set_text(str(question['questionString']))
            if 'choices' in question:
                # delete the old choices first
                for current_choice in form.my_osid_object_form._my_map['choices']:
                    form.clear_choice(current_choice)
                # now add the new ones
                for ind, choice in enumerate(question['choices']):
                    if isinstance(choice, dict):
                        form.add_choice(choice.get('text', ''),
                                        choice.get('name', 'Choice ' + str(int(ind) + 1)))
                    else:
                        form.add_choice(choice, 'Choice ' + str(int(ind) + 1))
    elif question['type'] == 'question-record-type%3Afiles-submission%40ODL.MIT.EDU':
        form.set_text(str(question['questionString']))
    else:
        raise Unsupported()

    return form

def validate_response(response, answers):
    correct = False
    # for longer submissions / multi-answer questions, need to make
    # sure that all of them match...
    if response['type'] == 'answer-record-type%3Afiles-submission%40ODL.MIT.EDU':
        return True  # always say True because the file was accepted

    submission = get_response_submissions(response)

    if is_multiple_choice(response):
        right_answers = [a for a in answers
                         if is_right_answer(a)]
        num_total = len(right_answers)

        if num_total != len(submission):
            pass
        else:
            num_right = 0
            for answer in right_answers:
                if answer.get_choice_ids()[0] in submission:
                    num_right += 1
                else:
                    break
            if num_right == num_total:
                correct = True
    else:
        for answer in answers:
            ans_type = answer.object_map['recordTypeIds'][0]
            if ans_type == 'answer-record-type%3Alabel-ortho-faces%40ODL.MIT.EDU':
                if isinstance(submission, basestring):
                    submission = json.loads(submission)
                if (int(answer.get_front_face_value()) == int(submission['frontFaceValue']) and
                    int(answer.get_side_face_value()) == int(submission['sideFaceValue']) and
                    int(answer.get_top_face_value()) == int(submission['topFaceValue'])):
                    correct = True
                    break
            elif (ans_type == 'answer-record-type%3Amulti-choice-ortho%40ODL.MIT.EDU' or
                  ans_type == 'answer-record-type%3Amulti-choice-edx%40ODL.MIT.EDU'):
                if not isinstance(submission, list):
                    raise InvalidArgument('ChoiceIds should be a list, in a student response.')
                if len(submission) == 1:
                    if answer.get_choice_ids()[0] == submission[0]:
                        correct = True
                        break
    return correct
