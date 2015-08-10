import os
import re
import json
from bs4 import BeautifulSoup
from dlkit_django.primordium import DataInputStream, Type, Id
from dlkit_django.proxy_example import TestRequest
from dlkit_django import RUNTIME, PROXY_SESSION


condition = PROXY_SESSION.get_proxy_condition()
condition.set_http_request(TestRequest())
proxy = PROXY_SESSION.get_proxy(condition)


am = RUNTIME.get_service_manager('ASSESSMENT', proxy=proxy)
rm = RUNTIME.get_service_manager('REPOSITORY', proxy=proxy)

EDX_QUESTION_TAGS = ['choiceresponse', 'customresponse', 'drag_and_drop',
                     'formularesponse', 'imageresponse', 'multiplechoiceresponse',
                     'numericalresponse', 'optionresponse', 'symbolicresponse']

BLANK_EDXML = """<?xml version="1.0"?>
<problem showanswer="past_due" rerandomize="per_student" display_name=" " weight="10">
  <text>
    <p>
      <solution>
        <font color="blue">Answer: </font>
        <font color="blue"/>
      </solution>
    </p>
  </text>
</problem>"""

ITEM_TEXTS_RECORD_TYPE = Type(**{
    'authority': 'ODL.MIT.EDU',
    'namespace': 'item-record-type',
    'identifier': 'item-texts',
    'display_name': 'Item Texts',
    'display_label': 'Item Texts',
    'description': 'Assessment Item record extension for Items with multiple texts',
    'domain': 'assessment.Item',
    })

ITEM_FILES_RECORD_TYPE = Type(**{
    'authority': 'ODL.MIT.EDU',
    'namespace': 'item-record-type',
    'identifier': 'edx_item',
    'display_name': 'Item Texts',
    'display_label': 'Item Texts',
    'description': 'Assessment Item record extension for Items with multiple texts',
    'domain': 'assessment.Item'
    })

EDX_ITEM_RECORD_TYPE = Type(**{
    'authority': 'ODL.MIT.EDU',
    'namespace': 'item-record-type',
    'identifier': 'edx_item',
    'display_name': 'edX Item',
    'display_label': 'edX Item',
    'description': 'Assessment Item record extension for edX based Items',
    'domain': 'assessment.Item',
    })

EDX_RAW_PROBLEM_TYPE = Type(**{
    'authority': 'ODL.MIT.EDU',
    'namespace': 'item-genus-type',
    'identifier': 'edx-raw-problem-type',
    'display_name': 'edX Raw Problem Type',
    'display_label': 'edX Raw Problem Type',
    'description': 'An assessment item that records a raw edX problem',
    'domain': 'assessment.Item'
    })

EDX_MULTI_CHOICE_PROBLEM_TYPE = Type(**{
    'authority': 'ODL.MIT.EDU',
    'namespace': 'item-genus-type',
    'identifier': 'edx-multi-choice-problem-type',
    'display_name': 'edX Multi-Choice Problem Type',
    'display_label': 'edX Multi-Choice Problem Type',
    'description': 'An assessment item for an edX multiple choice problem',
    'domain': 'assessment.Item'
    })

EDX_MULTI_CHOICE_QUESTION_RECORD_TYPE = Type(**{
    'authority': 'ODL.MIT.EDU',
    'namespace': 'question-record-type',
    'identifier': 'multi-choice-edx',
    'display_name': 'edX Multiple-Choice Question',
    'display_label': 'edX Multi-Choice Question',
    'description': 'Assessment Question record extension for multiple choice questions from edX',
    'domain': 'assessment.Question'
    })

EDX_MULTI_CHOICE_ANSWER_RECORD_TYPE = Type(**{
    'authority': 'ODL.MIT.EDU',
    'namespace': 'answer-record-type',
    'identifier': 'multi-choice-edx',
    'display_name': 'edX Multiple-Choice Answer',
    'display_label': 'edX Multi-Choice Answer',
    'description': 'Assessment Answer record extension for multiple choice questions from edX',
    'domain': 'assessment.Answer'
    })

EDX_NUMERICAL_RESPONSE_PROBLEM_TYPE = Type(**{
    'authority': 'ODL.MIT.EDU',
    'namespace': 'item-genus-type',
    'identifier': 'numeric-response-edx',
    'display_name': 'edX Numeric Response Problem Type',
    'display_label': 'edX Numeric Response Problem Type',
    'description': 'An assessment item for an edX numeric response problem',
    'domain': 'assessment.Item'
    })

EDX_NUMERICAL_RESPONSE_QUESTION_RECORD_TYPE = Type(**{
    'authority': 'ODL.MIT.EDU',
    'namespace': 'question-record-type',
    'identifier': 'numeric-response-edx',
    'display_name': 'edX Numeric Response Question',
    'display_label': 'edX Numeric Response Question',
    'description': 'Assessment Question record extension for numeric response questions from edX',
    'domain': 'assessment.Question'
})

EDX_NUMERICAL_RESPONSE_ANSWER_RECORD_TYPE = Type(**{
    'authority': 'ODL.MIT.EDU',
    'namespace': 'answer-record-type',
    'identifier': 'numeric-response-edx',
    'display_name': 'edX Numeric Response Answer',
    'display_label': 'edX Numeric Response Answer',
    'description': 'Assessment Answer record extension for numeric response questions from edX',
    'domain': 'assessment.Answer'
})

EDX_ASSET_TYPE = Type(**{
    'authority': 'ODL.MIT.EDU',
    'namespace': 'asset-record-type',
    'identifier': 'edx-asset',
    'display_name': 'edX Asset',
    'display_label': 'edX Asset',
    'description': 'Repository Asset record extension for edX content',
    'domain': 'repository.Asset'
})

EDX_TEXT_ASSET_CONTENT_RECORD_TYPE = Type(**{
    'authority': 'ODL.MIT.EDU',
    'namespace': 'asset-content-record-type',
    'identifier': 'asset-content-text',
    'display_name': 'Asset Content Text',
    'display_label': 'Asset Content Text',
    'description': 'Repository Asset Content record extension for Asset Contents with text',
    'domain': 'repository.AssetContent',
    'module_path': 'dlkit.mongo.repository.records.basic.simple_records',
    'object_record_class_name': 'AssetContentTextRecord',
    'form_record_class_name': 'AssetContentTextFormRecord'
})

EDX_TEXT_FILE_ASSET_CONTENT_RECORD_TYPE = Type(**{
    'authority': 'ODL.MIT.EDU',
    'namespace': 'edx-asset-content-record-type',
    'identifier': 'edx-asset-content-text-files',
    'display_name': 'edX Asset Content Text with Files',
    'display_label': 'edX Asset Content Text with Files',
    'description': 'Repository Asset Content record extension for Asset Contents with text and files',
    'domain': 'repository.AssetContent',
    'module_path': 'dlkit.mongo.repository.records.edx.edx_items',
    'object_record_class_name': 'edXAssetContentRecord',
    'form_record_class_name': 'edXAssetContentFormRecord'
})

EDX_IMAGE_ASSET_GENUS_TYPE = Type(**{
    'authority': 'ODL.MIT.EDU',
    'namespace': 'asset-genus-type',
    'identifier': 'edx-img',
    'display_name': 'edX Image',
    'display_label': 'edX Image',
    'description': 'An image found in an edx course',
    'domain': 'repository.Asset'
})

EDX_FILE_ASSET_GENUS_TYPE = Type(**{
    'authority': 'ODL.MIT.EDU',
    'namespace': 'asset-genus-type',
    'identifier': 'edx-file',
    'display_name': 'edX File',
    'display_label': 'edX File',
    'description': 'A file found in an edx course',
    'domain': 'repository.Asset'
})

REMOTE_FILE_ASSET_CONTENT_TYPE = Type(**{
    'authority': 'ODL.MIT.EDU',
    'namespace': 'remote-asset-content-record-type',
    'identifier': 'remote-file',
    'display_name': 'Remote File',
    'display_label': 'Remote File',
    'description': 'A file hosted remotely',
    'domain': 'repository.Asset'
})

PNG_ASSET_CONTENT_GENUS_TYPE = Type(**{
    'authority': 'iana.org',
    'namespace': 'asset-content-genus-type',
    'identifier': 'png',
    'display_name': 'Image/PNG',
    'display_label': 'Image/PNG',
    'description': 'A PNG image',
    'domain': 'repository.AssetContent'
})

JPG_ASSET_CONTENT_GENUS_TYPE = Type(**{
    'authority': 'iana.org',
    'namespace': 'asset-content-genus-type',
    'identifier': 'jpg',
    'display_name': 'Image/JPG',
    'display_label': 'Image/JPG',
    'description': 'A JPG image',
    'domain': 'repository.AssetContent'
})

LATEX_ASSET_CONTENT_GENUS_TYPE = Type(**{
    'authority': 'iana.org',
    'namespace': 'asset-content-genus-type',
    'identifier': 'latex',
    'display_name': 'application/x-tex',
    'display_label': 'application/x-tex',
    'description': 'LaTeX content',
    'domain': 'repository.AssetContent'
})

SVG_ASSET_CONTENT_GENUS_TYPE = Type(**{
    'authority': 'iana.org',
    'namespace': 'asset-content-genus-type',
    'identifier': 'svg',
    'display_name': 'image/svg+xml',
    'display_label': 'image/svg+xml',
    'description': 'SVG content',
    'domain': 'repository.AssetContent'
})

JSON_ASSET_CONTENT_GENUS_TYPE = Type(**{
    'authority': 'iana.org',
    'namespace': 'asset-content-genus-type',
    'identifier': 'json',
    'display_name': 'application/json',
    'display_label': 'application/json',
    'description': 'JSON content',
    'domain': 'repository.AssetContent'
})

JAVASCRIPT_ASSET_CONTENT_GENUS_TYPE = Type(**{
    'authority': 'iana.org',
    'namespace': 'asset-content-genus-type',
    'identifier': 'js',
    'display_name': 'application/javascript',
    'display_label': 'application/javascript',
    'description': 'JavaScript content',
    'domain': 'repository.AssetContent'
})

GENERIC_ASSET_CONTENT_GENUS_TYPE = Type(**{
    'authority': 'iana.org',
    'namespace': 'asset-content-genus-type',
    'identifier': 'generic',
    'display_name': 'Content/Generic',
    'display_label': 'Content/Generic',
    'description': 'Generic content',
    'domain': 'repository.AssetContent'
})

EDX_TEXT_ASSET_CONTENT_GENUS_TYPE = Type(**{
    'authority': 'ODL.MIT.EDU',
    'namespace': 'asset-content-type',
    'identifier': 'edx-text-asset-content',
    'display_name': 'edX Text Asset Content',
    'display_label': 'edX Text Asset Content',
    'description': 'An Asset Content that include text for edX',
    'domain': 'repository.AssetContent'
})

EDX_TEXT_ASSET_GENUS_TYPE = Type(**{
    'authority': 'ODL.MIT.EDU',
    'namespace': 'asset-type',
    'identifier': 'edx-text-asset',
    'display_name': 'edX Text Asset',
    'display_label': 'edX Text Asset',
    'description': 'An Asset that includes text for edX',
    'domain': 'repository.Asset'
})

COUNTS = {}
COUNTS['no_tag'] = 0
COUNTS['in_problem'] = 0
COUNTS['in_latex'] = 0
COUNTS['in_both'] = 0
COUNTS['file_not_found'] = 0
COUNTS['blank'] = 0
COUNTS['html'] = 0
COUNTS['problem_types'] = {}
COUNTS['mo_ids'] = []

XMLPATH = 'xCourse_801x/801x.xml'
BANKNAME = '801x Problems'
FILESDIR = './problems_801x/content-mit-801x-master'


def load_content(data):
    bank_name = data['bank_name']
    bank = None
    counts = dict(COUNTS)
    for b in am.banks:
        if b.display_name.text == bank_name:
            bank = b
            clear_edxml_probs(bank)
    if bank is None:
        bfc = am.get_bank_form_for_create([])
        bfc.set_display_name(bank_name)
        bfc.set_description('Assessment bank for ' + bank_name)
        bank = am.create_bank(bfc)

    data['bank'] = bank
    data['counts'] = counts

    load_problems(data)

    print 'No tag:', counts['no_tag']
    print 'in problem:', counts['in_problem']
    print 'in latex:', counts['in_latex']
    print 'in both:', counts['in_both']
    print 'file not found:', counts['file_not_found']
    print 'no useful content:', counts['blank']
    print 'html: ', counts['html']
    print 'problem types: ', counts['problem_types']
    print 'measurable outcomes: ', ','.join(counts['mo_ids'])
    return bank


def load_problems(data):
    course_dir = data['course_dir']
    edxml_file = data['edx_xml']
    bank = data['bank']
    counts = data['counts']

    global probs_in_vert
    probs_in_vert = []

    soup = BeautifulSoup(open(edxml_file), 'xml')
    for vertical in soup.find_all('vertical'):
        if len(vertical.find_all('problem')) > 0:
            load_problems_from_vertical(vertical, counts, bank, course_dir)
    
    for problem in soup.find_all('problem'):
        try:
            file_name = get_file_name(problem)
        except NotFound:
            file_name = 'NO_FILE_NAME_FOUND'
            counts['no_tag'] += 1
        if file_name not in probs_in_vert:
            load_problem(problem, counts, bank, course_dir)

def load_problems_from_vertical(vertical, counts, bank, course_dir):
    problems = vertical.find_all('problem')
    items = []
    for problem in problems:
        items.append(load_problem(problem, counts, bank, course_dir))
    return items

def load_problem(problem, counts, bank, course_dir):
    edxml_text = ''
    latex_text = ''
    solution = ''
    python_script = ''

    try:
        file_name = get_file_name(problem)
    except NotFound:
        file_name = 'NO_FILE_NAME_FOUND'
        # could be inline XML
        edxml_text = problem.prettify()

    display_name = get_display_name(problem, file_name)


    if os.path.isfile(course_dir + '/problem/' + file_name + '.xml'):
        edxml_text = open(course_dir + '/problem/' + file_name + '.xml').read().strip()
    if os.path.isfile(course_dir + '/latex/' + file_name + '.tex'):
        latex_text = open(course_dir + '/latex/' + file_name + '.tex').read().strip()

    files = dict()
    if edxml_text:
        p_soup = BeautifulSoup(edxml_text, 'xml')

        problem_element = p_soup.find('problem')
        try:
            for mo in problem_element['measurable_outcomes'].split(','):
                if mo not in counts['mo_ids']:
                    counts['mo_ids'].append(mo)
        except:
            pass

        if len(p_soup.find_all('script')) == 1:
            script = p_soup.find('script')
            if script['type'] == 'text/python':
                python_script = script.get_text().strip()

        if len(p_soup.find_all('solution')) == 1:
            solution = p_soup.find('solution').get_text().strip()

        # Expand this to find all files from the static/ folder, not just images
        # for image in p_soup.find_all('img'):
        #     src_path = image['src']
        #     if os.path.isfile(course_dir + src_path):
        #         img_data = DataInputStream(open(course_dir + src_path))
        #         images[src_path] = img_data
        #         edxml_text = edxml_text.replace(src_path, src_path.split('/')[-1].replace('.', '_'))
        static_regex = re.compile('[^http]')
        tag_source_combinations = {
            'draggable'             : 'icon',
            'drag_and_drop_input'   : 'img',
            'img'                   : 'src'
        }
        for tag, attr in tag_source_combinations.iteritems():
            search = {attr : static_regex}
            tags = p_soup.find_all(**search)
            for item in tags:
                if item.name == tag:
                    path = item[attr]
                    if os.path.isfile(course_dir + path):
                        file_data = DataInputStream(open(course_dir + path))
                        files[get_file_name_with_extension(path)] = file_data

                        # put the label into the edxml (not filename), because we will create
                        # the asset contents with that label below
                        edxml_text = edxml_text.replace(path, get_file_label(path))

        # find included files that are manually put in
        match_any_regex = re.compile('.*')
        included_files = p_soup.find_all(included_files=match_any_regex)
        if included_files:
            for item in included_files:
                paths = json.loads(item['included_files'])
                for label, path in paths.iteritems():
                    if os.path.isfile(course_dir + path):
                        file_data = DataInputStream(open(course_dir + path))
                        files[get_file_name_with_extension(path)] = file_data
                        edxml_text = edxml_text.replace(path, get_file_label(path))

        for va in p_soup.find_all('videoalpha'):
            print 'videoalpha found in problem', va['display_name']


    ifc = bank.get_item_form_for_create([EDX_ITEM_RECORD_TYPE])
    ifc.set_genus_type(EDX_RAW_PROBLEM_TYPE)
    ifc.set_display_name(display_name)
    ifc.add_text(file_name, 'urlname')
    ifc.add_text(latex_text, 'edxtex')
    ifc.add_text(edxml_text, 'edxml')
    ifc.add_text(python_script, 'python_script')
    ifc.add_text(solution, 'solution')
    # ifc = add_files_to_form(ifc, files)
    item = bank.create_item(ifc)

    file_ids = item.object_map['fileIds']

    # if can find the edX tags, then can separate out the
    # question from the answer (kind of)
    # also search for <responseparam type="tolerance"/>
    correct_answers = None
    if edxml_text:
        # need to make a qfc of the right TYPE here...
        question_type = []
        soup = BeautifulSoup(edxml_text, 'xml')
        qfc = bank.get_question_form_for_create(item.ident, [])
        for tag in EDX_QUESTION_TAGS:
            response_objects = soup.find_all(tag)

            if tag not in counts['problem_types']:
                counts['problem_types'][tag] = 0
            counts['problem_types'][tag] += len(response_objects)
            for response_object in response_objects:
                # now parse all the possible response types
                response = response_object.extract()
                # if response.name == 'numericalresponse':
                #     answer = response_object.get('answer')
                #     if response.find_all('responseparam'):
                #         tolerance = response.find_all('responseparam')[0].get('tolerance')
                #     afc = bank.get_answer_form_for_create(item.ident, [])
                #     pass  # not implemented yet in DLKit
                # elif response.name == 'multiplechoiceresponse':
                if response.name == 'multiplechoiceresponse':
                    # this will include the choices, plus which one(s) are right or wrong
                    qfc = bank.get_question_form_for_create(item.ident, [EDX_MULTI_CHOICE_QUESTION_RECORD_TYPE])
                    choices = response.find_all('choice')
                    correct_answers = []
                    for ind, choice in enumerate(choices):
                        qfc.add_choice(extract_choice(choice), choice.get('name'))
                        if choice.get('correct') == 'true':
                            correct_answers.append(ind)
                    qfc.set_text(soup.prettify())
                    qfc = add_file_ids_to_form(qfc, file_ids)
                else:
                    pass
        qfc.set_genus_type(EDX_RAW_PROBLEM_TYPE)
    else:
        qfc = bank.get_question_form_for_create(item.ident, [])
        # qfc = add_files_to_form(qfc, files)
        qfc.set_genus_type(EDX_RAW_PROBLEM_TYPE)
    q = bank.create_question(qfc)
    try:
        if correct_answers:
            choices = q.get_choices()
            for answer in correct_answers:
                afc = bank.get_answer_form_for_create(item.ident, [EDX_MULTI_CHOICE_ANSWER_RECORD_TYPE])
                choice_id = choices[int(answer)]    # not sure if we need the OSID Id or string
                afc.set_choice_id(choice_id['id'])  # just include the MongoDB ObjectId, not the whole dict
                bank.create_answer(afc)
    except:
        # for counting, I don't care if this part works or not.
        pass
    return item

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
    for file_name, file_data in files.iteritems():
        # default assume is a file
        prettify_type = 'file'
        genus = EDX_FILE_ASSET_GENUS_TYPE
        file_type = get_file_extension(file_name).lower()
        label = get_file_label(file_name)
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

        display_name = infer_display_name(label) + ' ' + prettify_type.title()
        description = 'Supporting ' + prettify_type + ' for assessment Question: ' + infer_display_name(label)

        form.add_file(file_data, clean(label), genus, ac_genus_type, display_name, description)
    return form

def clean(label):
    return re.sub(r'[^\w\d]', '_', label)

def clear_edxml_probs(bank=None, bank_name=BANKNAME):
    if not bank:
        try:
            bank = get_bank_by_name(bank_name)
        except NotFound:
            print 'bank name not found'
    for item in bank.get_items():
        bank.delete_item(item.get_id())

def extract_choice(choice):
    result = ''
    for string in choice.stripped_strings:
        result += string
    return result

def get_bank():
    return get_bank_by_name(BANKNAME)

def get_bank_by_name(bank_name):
    bank = None
    for b in am.banks:
        if b.display_name.text == bank_name:
            bank = b
    if bank is None:
        raise NotFound('No Bank named \'' + bank_name + '\' was found.')
    return bank

def get_file_label(file_path):
    # http://stackoverflow.com/questions/678236/how-to-get-the-filename-without-the-extension-from-a-path-in-python
    return os.path.splitext(os.path.basename(file_path))[0]

def get_file_extension(file_name):
    return os.path.splitext(os.path.basename(file_name))[-1]

def get_file_name(problem):
    try:
        file_name = '/'.join(problem['url_name_orig'].split(':'))
    except:
        try: 
            file_name = '/'.join(problem['url_name'].split(':'))
        except:
            raise NotFound('Problem file name not found')
    return file_name

def get_file_name_with_extension(path):
    return os.path.basename(path)

def get_display_name(problem, file_name):
    try:
        display_name = problem['display_name']
        if display_name.strip() == '':
            display_name = 'Unknown Display Name'
    except KeyError:
        display_name = 'Unknown Display Name'

    if (file_name != 'NO_FILE_NAME_FOUND' and
       (display_name == 'Unknown Display Name' or
        display_name.startswith('Question '))):
         display_name = infer_display_name(file_name)
    return display_name

def infer_display_name(text):
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

def get_item_by_name(item_name, bank=None, bank_name=BANKNAME):
    if not bank:
        try:
            bank = get_bank_by_name(bank_name)
        except NotFound:
            print 'bank name not found'
    for item in bank.get_items():
        if item.display_name.text == item_name:
            return item
    raise NotFound()


def parse_items(bank=None, bank_name=BANKNAME):
    if not bank:
        try:
            bank = get_bank_by_name(bank_name)
        except NotFound:
            print 'bank name not found'
    
    for item in bank.get_items():
        try:
            soup = BeautifulSoup(item.get_text('edxml'), 'xml')
        except:
            pass
        else:
            if len(soup.find_all('multiplechoiceresponse')) == 1:
                text_soup = None
                for child in soup.problem.children:
                    if child.name == 'text':
                        text_soup = child
                        break
                if text_soup is not None:
                    question_text = ''
                    for child in text_soup.children:
                        if child is not None and child.name is not None:
                            if len(child.find_all('multiplechoiceresponse')) == 0:
                                question_text += str(child)
                            elif len(child.find_all('multiplechoiceresponse')) == 1:
                                load_multi_choice(bank, item, question_text, soup.find_all('multiplechoiceresponse')[0])
            elif len(soup.find_all('multiplechoiceresponse')) == 3:
                print item.get_text('urlname')

def load_multi_choice(bank, item, text, tag):
    for answer in item.get_answers():
        bank.delete_answer(answer.ident)
    ifu = bank.get_item_form_for_update(item.ident)
    ifu.set_genus_type(EDX_MULTI_CHOICE_PROBLEM_TYPE)
    bank.update_item(ifu)
    qfc = bank.get_question_form_for_create(item.ident, [EDX_MULTI_CHOICE_QUESTION_RECORD_TYPE])
    afc = bank.get_answer_form_for_create(item.ident, [EDX_MULTI_CHOICE_ANSWER_RECORD_TYPE])
    qfc.set_text(text)
    for edx_choice in tag.choicegroup.find_all('choice'):
        choice = qfc.add_choice(text = edx_choice.text.strip(), name = edx_choice['name'].strip())
        if edx_choice['correct'] == 'true':
            afc.add_choice_id(choice['id'])
    bank.create_question(qfc)
    bank.create_answer(afc)

def get_all_multi_choice(bank=None, bank_name=BANKNAME):
    if not bank:
        try:
            bank = get_bank_by_name(bank_name)
        except NotFound:
            print 'bank name not found'
    return bank.get_items_by_genus_type(EDX_MULTI_CHOICE_PROBLEM_TYPE)

def count_problems(bank=None, bank_name=BANKNAME):
    if not bank:
        try:
            bank = get_bank_by_name(bank_name)
        except NotFound:
            print 'bank name not found'
    num_items = 0
    num_mc = 0
    num_nr = 0
    mc_none = 0
    mc_one = 0
    mc_two = 0
    mc_three = 0
    mc_four = 0
    mc_five = 0
    nr_none = 0
    nr_one = 0
    nr_two = 0
    nr_three = 0
    nr_four = 0
    nr_five = 0
    for item in bank.get_items():
        num_items += 1
        try:
            soup = BeautifulSoup(item.get_text('edxml'), 'xml')
        except:
            pass
        else:
            num_mc_in_problem = len(soup.find_all('multiplechoiceresponse'))
            if num_mc_in_problem == 0:
                mc_none += 1
            elif num_mc_in_problem == 1:
                mc_one += 1
            elif num_mc_in_problem == 2:
                mc_two += 1
            elif num_mc_in_problem == 3:
                mc_three += 1
            elif num_mc_in_problem == 4:
                mc_four += 1
            elif num_mc_in_problem == 5:
                mc_five += 1
            if len(soup.find_all('script')) == 0:
                num_nr_in_problem = len(soup.find_all('numericalresponse'))
            else:
                num_nr_in_problem = 0
            if num_nr_in_problem == 0:
                nr_none += 1
            elif num_nr_in_problem == 1:
                nr_one += 1
            elif num_nr_in_problem == 2:
                nr_two += 1
            elif num_nr_in_problem == 3:
                nr_three += 1
            elif num_nr_in_problem == 4:
                nr_four += 1
            elif num_nr_in_problem == 5:
                nr_five += 1
    print 'Total number of problems:', num_items
    print 'Total multi-choice problems:', num_mc
    print 'Problems with no multi-choice:', mc_none
    print 'Problems with one multi-choice:', mc_one
    print 'Problems with two multi-choice:', mc_two
    print 'Problems with three multi-choice:', mc_three
    print 'Problems with four multi-choice:', mc_four
    print 'Problems with five multi-choice:', mc_five
    print 'Total numeric response problems:', num_nr
    print 'Problems with no numeric-response:', nr_none
    print 'Problems with one numeric-response:', nr_one
    print 'Problems with two numeric-response:', nr_two
    print 'Problems with three numeric-response:', nr_three
    print 'Problems with four numeric-response:', nr_four
    print 'Problems with five numeric-response:', nr_five

def get_question(item):

    if not item.get_text('python_script'):
        raise NotFound('no python script available')

    import sys, imp, re
    mymodule = imp.new_module('mymodule')
    exec(item.get_text('python_script'), mymodule.__dict__)
    text = item.get_text('edxml')
    done = False
    count = 0
    while not done:
        result = re.search(r'\$\w+', text)
        if result:
            replacement = str(getattr(mymodule, result.group()[1:]))
            text = text.replace(result.group(), replacement)
            count += 1
        else:
            done = True
    return text



class NotFound(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)
