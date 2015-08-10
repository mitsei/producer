import os
import re
import csv
import sys
import json
import codecs
import shutil
import logging
import tarfile
import zipfile
import requests

from copy import deepcopy
from decimal import Decimal

from edx_utils import EDX_ASSET_TYPE, \
    EDX_FILE_ASSET_GENUS_TYPE, \
    EDX_IMAGE_ASSET_GENUS_TYPE, \
    EDX_RAW_PROBLEM_TYPE, \
    EDX_MULTI_CHOICE_ANSWER_RECORD_TYPE, \
    EDX_ITEM_RECORD_TYPE, \
    EDX_QUESTION_TAGS, \
    EDX_MULTI_CHOICE_QUESTION_RECORD_TYPE, \
    EDX_MULTI_CHOICE_PROBLEM_TYPE, \
    EDX_NUMERICAL_RESPONSE_QUESTION_RECORD_TYPE, \
    EDX_NUMERICAL_RESPONSE_ANSWER_RECORD_TYPE, \
    PNG_ASSET_CONTENT_GENUS_TYPE, \
    JAVASCRIPT_ASSET_CONTENT_GENUS_TYPE, \
    JSON_ASSET_CONTENT_GENUS_TYPE, \
    JPG_ASSET_CONTENT_GENUS_TYPE, \
    LATEX_ASSET_CONTENT_GENUS_TYPE, \
    SVG_ASSET_CONTENT_GENUS_TYPE, \
    GENERIC_ASSET_CONTENT_GENUS_TYPE, \
    EDX_TEXT_ASSET_CONTENT_GENUS_TYPE, \
    EDX_TEXT_ASSET_CONTENT_RECORD_TYPE, \
    EDX_TEXT_ASSET_GENUS_TYPE, \
    EDX_TEXT_FILE_ASSET_CONTENT_RECORD_TYPE
from xbundle import XBundle

from bs4 import BeautifulSoup

from pymongo import MongoClient
from bson import ObjectId

from dlkit_django import PROXY_SESSION, RUNTIME
from dlkit_django.primordium import *
from dlkit_django.errors import NotFound
from dlkit_django.proxy_example import TestRequest

from dlkit.mongo.utilities import now_map

from dlkit.mongo.records.types import EDX_COMPOSITION_GENUS_TYPES,\
    COMPOSITION_RECORD_TYPES, ITEM_RECORD_TYPES, ASSET_RECORD_TYPES,\
    ASSET_CONTENT_RECORD_TYPES, ASSET_CONTENT_GENUS_TYPES, REPOSITORY_RECORD_TYPES,\
    REPOSITORY_GENUS_TYPES, EDX_ASSET_CONTENTS_GENUS_TYPES, EDX_ASSESSMENT_ITEM_GENUS_TYPES

from lxml import etree

from xbundle import DESCRIPTOR_TAGS

LORE_REPOSITORY = Type(**REPOSITORY_RECORD_TYPES['lore-repo'])
COURSE_REPOSITORY = Type(**REPOSITORY_RECORD_TYPES['course-repo'])
COURSES_PARENT_REPOSITORY_GENUS = Type(**REPOSITORY_GENUS_TYPES['courses-root-repo'])
USERS_PARENT_REPOSITORY_GENUS = Type(**REPOSITORY_GENUS_TYPES['users-root-repo'])
DOMAIN_REPO_GENUS = Type(**REPOSITORY_GENUS_TYPES['domain-repo'])
COURSE_REPO_GENUS = Type(**REPOSITORY_GENUS_TYPES['course-repo'])
COURSE_RUN_REPO_GENUS = Type(**REPOSITORY_GENUS_TYPES['course-run-repo'])
USER_REPO_GENUS = Type(**REPOSITORY_GENUS_TYPES['user-repo'])

EDX_COMPOSITION_GENUS_TYPES_STR = [str(Type(**genus_type))
                                   for k, genus_type in EDX_COMPOSITION_GENUS_TYPES.iteritems()]

EDX_COMPOSITION = Type(**COMPOSITION_RECORD_TYPES['edx-composition'])
EDX_ITEM = Type(**ITEM_RECORD_TYPES['edx_item'])
EDX_ITEM_GENUS = Type(**EDX_ASSESSMENT_ITEM_GENUS_TYPES['problem'])
EDX_ASSET = Type(**ASSET_RECORD_TYPES['edx-asset'])
EDX_ASSET_CONTENT = Type(**ASSET_CONTENT_RECORD_TYPES['edx-asset-content-text-files'])
EDX_ASSET_CONTENT_GENUS = Type(**ASSET_CONTENT_GENUS_TYPES['edx-text-asset'])

CHILDLESS_TAGS = ['problem', 'html']

PROJECT_PATH = os.path.dirname(os.path.abspath(__file__))
ABS_PATH = os.path.abspath(os.path.join(PROJECT_PATH, os.pardir))


LEARN_COG_PROC = Id("mc3.grade.system.cognitive.processes.bloom.revised%3Amc3.grade.bloom.learn%40MIT-OEIT")
OUTCOME_GENUS = Type("mc3-objective%3Amc3.learning.generic.outcome%40MIT-OEIT")


def _get_asset_content_genus_type(type_label):
    return Type(**EDX_ASSET_CONTENTS_GENUS_TYPES[type_label])

def _get_genus_type(type_label):
    return Type(**EDX_COMPOSITION_GENUS_TYPES[type_label])

def _get_manager(manager, userid):
    test_request = TestRequest(username=userid)
    condition = PROXY_SESSION.get_proxy_condition()
    condition.set_http_request(test_request)
    proxy = PROXY_SESSION.get_proxy(condition)
    return RUNTIME.get_service_manager(manager.upper(), proxy=proxy)

def _get_or_create_root_repo(rm, repo_type):
    """get or create a generic "course repository" as a root repo, to hang all
    other LORE stuff off of"""
    if repo_type.lower() == 'courses':
        target_genus = COURSES_PARENT_REPOSITORY_GENUS
    elif repo_type.lower() == 'users':
        target_genus = USERS_PARENT_REPOSITORY_GENUS
    else:
        raise ValueError()
    for root in rm.get_root_repositories():
        if root.genus_type == target_genus:
            return root
    # no parent repo, so might as well make our own
    form = rm.get_repository_form_for_create([LORE_REPOSITORY])
    form.set_genus_type(target_genus)
    form.display_name = 'Root repository for all LORE {0}'.format(repo_type)
    form.description = 'Contains all LORE {0}'.format(repo_type)
    root = rm.create_repository(form)
    rm.add_root_repository(root.ident)
    return root

def _subs_filename(subs_id, lang='en'):
    """
    Generate proper filename for storage.

    Function copied from:
    edx-platform/common/lib/xmodule/xmodule/video_module/transcripts_utils.py

    Args:
        subs_id (str): Subs id string
        lang (str): Locale language (optional) default: en

    Returns:
        filename (str): Filename of subs file
    """
    if lang in ('en', "", None):
        return u'subs_{0}.srt.sjson'.format(subs_id)
    else:
        return u'{0}_subs_{1}.srt.sjson'.format(lang, subs_id)

def clean_text(string):
    without_author = re.sub('celieber@mit.edu|Lieberman', '', string)
    without_class_id = re.sub('16.101|16101', 'AA100', without_author)
    return re.sub('2013_SOND', '2015_FALL', without_class_id)

def convert_time_dict_to_str(time):
    return '{0}:{1}:{2}'.format(str(time['hours'].zfill(2)),
                                str(time['minutes'].zfill(2)),
                                str(time['seconds'].zfill(2)))

def get_file_text(path):
    if os.path.isfile(path):
        return open(path).read().decode('utf-8').strip()
    else:
        return ''

def get_or_create_user_repo(user_id):
    """
    Get or create a user-controlled repository to dump assets / assessments in.

    Args:
        user_id (int): Primary key of user
    Raises:
        ValueError: Duplicate course
    Returns:
        repository (osid.repository.Repository): The created repository

    """
    # Check on unique values before attempting a get_or_create, because
    # items such as import_date will always make it non-unique.
    user_id = str(user_id)
    rm = _get_manager('repository', user_id)
    users_repo = _get_or_create_root_repo(rm, 'users')
    # need to test if this exists already. If it does, just
    # return it.
    for user_repo in rm.get_child_repositories(users_repo.ident):
        if user_repo.provider_id == rm.effective_agent_id:
            return rm.get_repository(user_repo.ident)

    form = rm.get_repository_form_for_create([LORE_REPOSITORY])
    form.display_name = 'Repository for user {0}'.format(str(user_id))
    form.description = 'Personal repository for the specified user'
    form.set_provider(rm.effective_agent_id)
    form.set_genus_type(USER_REPO_GENUS)
    repo = rm.create_repository(form)
    rm.add_child_repository(users_repo.ident, repo.ident)
    # roles_init_new_repo(repo)
    return repo

def get_runtime_parameter(runtime, param, provider='handcar_mc3'):
    try:
        config = runtime.get_configuration()
        parameter_id = Id('parameter:{0}@{1}'.format(param, provider))
        return config.get_value_by_parameter(parameter_id).get_string_value()
    except (AttributeError, KeyError):
        return ''

def get_video_sub(xml):
    """
    Get subtitle IDs from <video> XML.

    Args:
        xml (lxml.etree): xml for a LearningResource
    Returns:
        sub string: subtitle string
    """
    subs = xml.xpath("@sub")
    # It's not possible to have more than one.
    if len(subs) == 0:
        return ""
    return _subs_filename(subs[0])

def remove_extra_slashes(path):
    return path.replace('///','/').replace('//','/')


class DysonXUtil(object):
    """
    More manual, less automated / bulk than the DysonX class

    """
    def __init__(self, am=None, rm=None, lm=None, gm=None, request=None):
        self.counts = {}
        self.counts['no_tag'] = 0
        self.counts['in_problem'] = 0
        self.counts['in_latex'] = 0
        self.counts['in_both'] = 0
        self.counts['file_not_found'] = 0
        self.counts['blank'] = 0
        self.counts['html'] = 0
        self.counts['problem_types'] = {}
        self.counts['compositions'] = {}
        self.counts['mo_ids'] = []

        self.edx_map = {}
        self._assessment_map = {}
        self._offered_map = {}

        self._mitoces_id = 'mc3-objectivebank%3A11%40MIT-OEIT'
        self.qbank_host = 'assessments-dev.mit.edu'

        # self.lo_mc3_map_file = ABS_PATH + '/lo_mc3_map2.csv'
        # self.grade_file = ABS_PATH + '/grades_131213_deid2.csv'
        #
        # self.lo_mc3_map = self._process_lo_mc3_map()
        self.lo_mc3_map = {}

        if am:
            self._am = am
        else:
            if request:
                self._am = self._get_manager(request, 'assessment')
            else:
                raise Exception('Needs a request object')
        if rm:
            self._rm = rm
        else:
            if request:
                self._rm = self._get_manager(request, 'repository')
            else:
                raise Exception('Needs a request object')
        if lm:
            self._lm = lm
        else:
            if request:
                self._lm = self._get_manager(request, 'learning')
            else:
                raise Exception('Needs a request object')

        if gm:
            self._gm = gm
        else:
            if request:
                self._gm = self._get_manager(request, 'grading')
            else:
                raise Exception('Needs a request object')
        self._root_bank = 24 * '0'  # 24 0's for root assessment bank

    def _add_file_ids_to_form(self, form, file_ids):
        """
        Add existing asset_ids to a form
        :param form:
        :param image_ids:
        :return:
        """
        for label, file_id in file_ids.iteritems():
            form.add_asset(Id(file_id['assetId']), label, Id(file_id['assetContentTypeId']))
        return form

    def _add_files_to_form(self, form, files):
        """
        Whether an item form or a question form
        :param form:
        :return:
        """
        for file_name, file_data in files.iteritems():
            # default assume is a file
            prettify_type = 'file'
            genus = EDX_FILE_ASSET_GENUS_TYPE
            file_type = self._get_file_extension(file_name).lower()
            label = self._get_file_label(file_name)
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
                elif 'svg' in file_type:
                    ac_genus_type = SVG_ASSET_CONTENT_GENUS_TYPE
                else:
                    ac_genus_type = GENERIC_ASSET_CONTENT_GENUS_TYPE
            else:
                ac_genus_type = GENERIC_ASSET_CONTENT_GENUS_TYPE

            display_name = self._infer_display_name(label) + ' ' + prettify_type.title()
            description = ('Supporting ' + prettify_type + ' for assessment Question: ' +
                           self._infer_display_name(label))

            form.add_file(file_data, self._clean(label), genus, ac_genus_type, display_name, description)
        return form

    def _create_file_asset(self, label, file_data):
        afc = self.repo.get_asset_form_for_create([EDX_ASSET_TYPE])
        afc.set_display_name(label)
        asset = self.repo.create_asset(afc)

        # now add the text as a content inside this asset
        asset_content_type_list = []
        try:
            config = self.repo._RUNTIME.get_configuration()
            parameter_id = Id('parameter:assetContentRecordTypeForFiles@mongo')
            asset_content_type_list.append(config.get_value_by_parameter(parameter_id).get_type_value())
        except:
            pass
        acfc = self.repo.get_asset_content_form_for_create(asset.ident,
                                                           asset_content_type_list)

        acfc.set_data(file_data)
        content = self.repo.create_asset_content(acfc)
        return asset.ident

    def _clean(self, label):
        return re.sub(r'[^\w\d]', '_', label)

    def _clear_edxml_probs(self, bank):
        for assessment in bank.get_assessments():
            for offered in bank.get_assessments_offered_for_assessment(assessment.ident):
                for taken in bank.get_assessments_taken_for_assessment_offered(offered.ident):
                    bank.delete_assessment_taken(taken.ident)
                bank.delete_assessment_offered(offered.ident)
            bank.delete_assessment(assessment.ident)
        for item in bank.get_items():
            bank.delete_item(item.get_id())

    def _extract_choice(self, choice):
        result = ''
        for string in choice.stripped_strings:
            result += string
        return result

    def _get_display_name(self, problem, file_name):
        try:
            display_name = problem['display_name']
            if display_name.strip() == '':
                display_name = 'Unknown Display Name'
        except KeyError:
            display_name = 'Unknown Display Name'

        if (file_name != 'NO_FILE_NAME_FOUND' and
               (display_name == 'Unknown Display Name' or
                display_name.startswith('Question '))):
            display_name = self._infer_display_name(file_name)
        return display_name

    def _get_file_label(self, file_path):
        # http://stackoverflow.com/questions/678236/how-to-get-the-filename-without-the-extension-from-a-path-in-python
        return os.path.splitext(os.path.basename(file_path))[0]

    def _get_file_extension(self, file_name):
        return os.path.splitext(os.path.basename(file_name))[-1]

    def _get_file_name(self, problem):
        try:
            file_name = '/'.join(problem['url_name_orig'].split(':'))
        except KeyError:
            try:
                file_name = '/'.join(problem['url_name'].split(':'))
            except KeyError:
                try:
                    file_name = '/'.join(problem['filename'].split(':'))
                except KeyError:
                    raise NotFound('Problem file name not found')
        return file_name

    def _get_file_name_with_extension(self, path):
        return os.path.basename(path)

    def _get_manager(self, request, manager):
        condition = PROXY_SESSION.get_proxy_condition()
        condition.set_http_request(request)
        proxy = PROXY_SESSION.get_proxy(condition)

        return RUNTIME.get_service_manager(manager.upper(), proxy)

    def _get_new_id(self, mo_link):
        original_resource_id = clean_text(mo_link['href'].replace('/jump_to_id/', ''))
        return self.edx_map[original_resource_id]

    def _get_repository(self, bank):
        """
        Get or create a repository with the same name as bank
        # Instantiate a RM session (get_asset_admin_session_for_repository(Id(bank_id)))
        # This automatically creates a repo or gets the existing one
        # Then do a RM.get_repository(Id('repository.Repository%3Abank_identifier%40ODL-MIT))

        """
        aas = self._rm.get_asset_admin_session_for_repository(bank.ident)
        repo_id = 'repository.Repository%3A' + bank.ident.get_identifier() + '%40' + bank.ident.get_authority()
        repo = self._rm.get_repository(Id(repo_id))
        return repo

    def _get_video_file_label(self, file_path):
        # http://stackoverflow.com/questions/678236/how-to-get-the-filename-without-the-extension-from-a-path-in-python
        return file_path.replace('static/subs_', '').replace('.srt.sjson', '')

    def _infer_display_name(self, text):
        text = text.strip()
        if text == '':
            return 'Unknown Display Name'
        if '_' not in text:
            return text
        file_first_part = text.split('_')[0].lower()
        file_last_part = text.split('_')[-1]

        for prefix in [('lec', 'Lecture'),
                       ('ps', 'Problem Set'),
                       ('ex', 'Exam')]:
            if file_first_part.startswith(prefix[0]):
                text = '{0} {1}_{2}'.format(prefix[1],
                                            file_first_part.split(prefix[0])[-1],
                                            file_last_part)

        second_part = text.split('_')[-1].lower()
        for suffix in [('p', 'Problem'),
                       ('q', 'Question')]:
            if second_part.startswith(suffix[0]):
                text = '{0}: {1} {2}'.format(text.split('_')[0],
                                             suffix[1],
                                             second_part.split(suffix[0])[-1])

        return text

    def _is_problem(self, item_id):
        if not isinstance(item_id, basestring):
            item_id = str(item_id)
        if 'assessment.Item' in item_id:
            return True
        else:
            return False

    def _item_exists(self, item_id):
        """
        Sometimes stale IDs get passed in...need to check if
        the item still exists in MongoDB

        :param item_id:
        :return:
        """
        from dlkit.mongo.utilities import MongoClientValidated
        from dlkit_django.configs import MONGO_1
        return_val = False

        try:
            if not item_id:
                raise LookupError
            db_prefix = MONGO_1['parameters']['mongoDBNamePrefix']['values'][0]['value']
            if self._is_problem(item_id):
                db_items = MongoClientValidated('assessment',
                                                collection='Item',
                                                runtime=self._rm._runtime)
            else:
                db_items = MongoClientValidated('repository',
                                                collection='Asset',
                                                runtime=self._rm._runtime)
            if db_items.find({"_id": ObjectId(Id(item_id).identifier)}).count() == 0:
                raise LookupError
            return_val = True
        except LookupError:
            return_val = False
        finally:
            return return_val

    def _load_html(self, data):
        edxml_file = data['edx_xml']
        soup = BeautifulSoup(open(edxml_file), 'xml')
        for html in soup.find_all('html'):
            data['resource'] = html
            asset = self._load_repository_object(data)
            self.edx_map[asset.get_text('urlname')] = str(asset.ident)

    def _load_problem(self, data):
        """
        problem should be BeautifulSoup object
        course_dir is location on harddrive
        """
        problem = data['resource']
        course_dir = data['course_path']
        edxml_text = ''
        latex_text = ''
        solution = ''
        python_script = ''

        try:
            file_name = self._get_file_name(problem)
        except NotFound:
            file_name = 'NO_FILE_NAME_FOUND'
            # could be inline XML
            edxml_text = problem.prettify()

        if 'file_contents' in data:
            edxml_text = data['file_contents']

        display_name = self._get_display_name(problem, file_name)

        edxml_text = get_file_text(course_dir + '/problem/' + file_name + '.xml')
        latex_text = get_file_text(course_dir + '/latex/' + file_name + '.tex')

        # latex2edx puts the latex source file in the problem attribute "source_file"
        try:
            prob = BeautifulSoup(edxml_text, 'xml').find('problem')
            if prob.get('source_file'):
                latex_text = get_file_text(course_dir + '/' + prob.get('source_file'))
        except:
            pass

        files = dict()

        measurable_outcomes = None

        if edxml_text:
            p_soup = BeautifulSoup(edxml_text, 'xml')

            if len(p_soup.find_all('script')) >= 1:
                scripts = p_soup.find_all('script')
                for script in scripts:
                    if 'type' in script.attrs and 'python' in script['type']:
                        python_script = script.get_text().strip()
                        break

            if len(p_soup.find_all('solution')) == 1:
                solution = p_soup.find('solution').encode_contents()

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
                        orig_path = deepcopy(path)
                        path_with_spaces = deepcopy(path).replace('_', ' ')
                        # still need to replace all / after /static/ with _...
                        # Studio does this to the static file,
                        # but doesn't update the include tags. Let's do better.
                        path_without_static = path.replace('/static/', '')
                        underscored_path = re.sub(r'[^\w.:-]', '_', path_without_static)
                        path = '/static/' + underscored_path

                        fixed_path = remove_extra_slashes(course_dir + path).replace('drafts/','')
                        if os.path.isfile(fixed_path):
                            file_data = DataInputStream(open(fixed_path))
                            files[self._get_file_name_with_extension(path)] = file_data

                            # put the label into the edxml (not filename), because we will create
                            # the asset contents with that label below
                            # edxml_text = edxml_text.replace(orig_path, self._get_file_label(path))
                            edxml_text = re.sub(orig_path, self._get_file_label(path), edxml_text)
                        else:
                            # try it with a path with spaces (Studio does weird things to
                            # files but is not consistent with the names in static/
                            fixed_path = remove_extra_slashes(course_dir + path_with_spaces).replace('drafts/','')
                            if os.path.isfile(fixed_path):
                                # revert to path here to we are consistent in terms of _, etc.
                                file_data = DataInputStream(open(fixed_path))
                                files[self._get_file_name_with_extension(path)] = file_data

                                # put the label into the edxml (not filename), because we will create
                                # the asset contents with that label below
                                edxml_text = edxml_text.replace(orig_path, self._get_file_label(path))
                            else:
                                # try it with the original name
                                fixed_path = remove_extra_slashes(course_dir + orig_path).replace('drafts/','')
                                if os.path.isfile(fixed_path):
                                    # revert to path here to we are consistent in terms of _, etc.
                                    file_data = DataInputStream(open(fixed_path))
                                    files[self._get_file_name_with_extension(path)] = file_data

                                    # put the label into the edxml (not filename), because we will create
                                    # the asset contents with that label below
                                    edxml_text = edxml_text.replace(orig_path, self._get_file_label(path))
                                else:
                                    # should throw an exception?
                                    logging.error('Tried getting file: ' + fixed_path + ', but it was not found.' +
                                                  ' Make sure the name is correct.')
                                    extension = self._get_file_extension(path)
                                    filename = self._clean(self._get_file_label(path))
                                    edxml_text = edxml_text.replace(path, '/static/' + filename + '.' + extension)

            # find included files that are manually put in
            match_any_regex = re.compile('.*')
            included_files = p_soup.find_all(included_files=match_any_regex)
            if included_files:
                for item in included_files:
                    paths = item['included_files'].split(';')
                    # paths = json.loads(item['included_files'])
                    for path in paths:
                        if os.path.isfile(course_dir + path):
                            file_data = DataInputStream(open(course_dir + path))
                            files[self._get_file_name_with_extension(path)] = file_data
                            edxml_text = edxml_text.replace(path, self._get_file_label(path))

            for va in p_soup.find_all('videoalpha'):
                print 'videoalpha found in problem', va['display_name']

            try:
                measurable_outcomes = p_soup.find('problem')['measurable_outcomes']
            except KeyError:
                measurable_outcomes = None

        ifc = self.bank.get_item_form_for_create([EDX_ITEM_RECORD_TYPE])
        ifc.set_genus_type(EDX_RAW_PROBLEM_TYPE)
        ifc.set_display_name(clean_text(display_name))
        ifc.add_text(clean_text(file_name), 'urlname')
        ifc.add_text(clean_text(latex_text), 'latex')
        ifc.add_text(clean_text(edxml_text), 'edxml')
        ifc.add_text(clean_text(python_script), 'python_script')
        ifc.add_text(clean_text(solution), 'solution')

        # add in the problem metadata like weight, attempts
        metadata = ['attempts', 'markdown', 'rerandomize', 'showanswer', 'weight']
        for attr in metadata:
            if attr in data:
                if attr == 'attempts':
                    data[attr] = int(data[attr])
                elif attr == 'weight':
                    data[attr] = float(data[attr])
                getattr(ifc, 'add_' + attr)(data[attr])

        if measurable_outcomes is not None:
            mo_list = measurable_outcomes.split(',')
            converted_mo_list = []
            for mo in mo_list:
                mc3_mos = self.lo_mc3_map[mo]
                mc3_mos = [Id(mo) for mo in mc3_mos]
                converted_mo_list += mc3_mos
            ifc.set_learning_objectives(converted_mo_list)

        ifc = self._add_files_to_form(ifc, files)
        item = self.bank.create_item(ifc)

        file_ids = item.object_map['fileIds']

        # if can find the edX tags, then can separate out the
        # question from the answer (kind of)
        # also search for <responseparam type="tolerance"/>
        correct_answers = []
        tolerances = []
        answer_type = []
        responses = []
        if edxml_text:
            # need to make a qfc of the right TYPE here...
            question_type = []
            soup = BeautifulSoup(edxml_text, 'xml')
            qfc = self.bank.get_question_form_for_create(item.ident, [])
            for tag in EDX_QUESTION_TAGS:
                response_objects = soup.find_all(tag)
                if tag not in self.counts['problem_types']:
                    self.counts['problem_types'][tag] = 0

                self.counts['problem_types'][tag] += len(response_objects)
                for response_object in response_objects:
                    # now parse all the possible response types
                    placeholder = soup.new_tag(tag)
                    response = response_object.replace_with(placeholder)
                    response_type = None
                    if response.name == 'multiplechoiceresponse':
                        response_type = EDX_MULTI_CHOICE_QUESTION_RECORD_TYPE
                    elif response.name == 'numericalresponse':
                        response_type = EDX_NUMERICAL_RESPONSE_QUESTION_RECORD_TYPE

                    responses.append({
                        'soup'      : response,
                        'type'      : response_type
                    })
            qfc.set_genus_type(EDX_RAW_PROBLEM_TYPE)

            # set the response types here
            if responses:
                types = [r['type'] for r in responses if r['type']]
                if len(types) > 0:
                    qfc = self.bank.get_question_form_for_create(item.ident, types)
                    # qfc.set_text(soup.prettify())
                    if len(soup.find_all('solution')) == 1:
                        solution = soup.find('solution').extract()
                    qfc.set_text(clean_text(soup.find('problem').encode_contents()))
                    qfc = self._add_file_ids_to_form(qfc, file_ids)
                    for response in responses:
                        no_tolerance = True
                        if response['type'] == EDX_MULTI_CHOICE_QUESTION_RECORD_TYPE:
                            # this will include the choices, plus which one(s) are right or wrong
                            choices = response['soup'].find_all('choice')
                            all_my_correct = []
                            for ind, choice in enumerate(choices):
                                qfc.add_choice(self._extract_choice(choice), choice.get('name'))
                                if choice.get('correct') == 'true':
                                    all_my_correct.append(ind)
                            correct_answers.append(all_my_correct)
                            answer_type.append(EDX_MULTI_CHOICE_ANSWER_RECORD_TYPE)
                        elif response['type'] == EDX_NUMERICAL_RESPONSE_QUESTION_RECORD_TYPE:
                            # parse out the correct answer, plus tolerance
                            # because parameterized response can have a string here, cast
                            # to float later
                            correct_answers.append(response['soup'].get('answer'))
                            params = response['soup'].find_all('responseparam')
                            for param in params:
                                if param.get('type') == 'tolerance':
                                    tolerances.append(param.get('default'))
                                    no_tolerance = False
                            answer_type.append(EDX_NUMERICAL_RESPONSE_ANSWER_RECORD_TYPE)
                        else:
                            answer_type.append(None)
                            correct_answers.append(None)
                        if no_tolerance:
                            # need to give it a default?
                            tolerances.append(None)
        else:
            qfc = self.bank.get_question_form_for_create(item.ident, [])
            qfc = self._add_files_to_form(qfc, files)
            qfc.set_genus_type(EDX_RAW_PROBLEM_TYPE)

        question = self.bank.create_question(qfc)
        if correct_answers != []:
            for answer_index, correct_answer in enumerate(correct_answers):
                if correct_answer != None:
                    if answer_type[answer_index] == EDX_MULTI_CHOICE_ANSWER_RECORD_TYPE:
                        choices = question.get_choices()
                        if isinstance(correct_answer, list):
                            for one_possible_answer in correct_answer:
                                afc = self.bank.get_answer_form_for_create(item.ident, [EDX_MULTI_CHOICE_ANSWER_RECORD_TYPE])
                                choice_id = choices[int(one_possible_answer)]    # not sure if we need the OSID Id or string
                                afc.add_choice_id(choice_id['id'])  # just include the MongoDB ObjectId, not the whole dict
                                self.bank.create_answer(afc)
                        else:
                            afc = self.bank.get_answer_form_for_create(item.ident, [EDX_MULTI_CHOICE_ANSWER_RECORD_TYPE])
                            choice_id = choices[int(correct_answer)]    # not sure if we need the OSID Id or string
                            afc.add_choice_id(choice_id['id'])  # just include the MongoDB ObjectId, not the whole dict
                            self.bank.create_answer(afc)
                    elif answer_type[answer_index] == EDX_NUMERICAL_RESPONSE_ANSWER_RECORD_TYPE:
                        afc = self.bank.get_answer_form_for_create(item.ident, [EDX_NUMERICAL_RESPONSE_ANSWER_RECORD_TYPE])
                        try:
                            afc.set_decimal_value(float(correct_answer))
                        except:
                            # must be parameterized answer
                            afc.set_text(clean_text(correct_answer))

                        # similarly for tolerances, can specify % or actual number
                        try:
                            afc.set_tolerance_value(float(tolerances[answer_index]))
                        except:
                            # tolerance can be left blank / None
                            if tolerances[answer_index] is None:
                                afc.add_text('', 'tolerance')
                            else:
                                afc.add_text(tolerances[answer_index], 'tolerance')
                        self.bank.create_answer(afc)
        return item

    def _load_problems(self, data):
        edxml_file = data['edx_xml']

        soup = BeautifulSoup(open(edxml_file), 'xml')
        for problem in soup.find_all('problem'):
            data['resource'] = problem
            item = self._load_problem(data)
            self.edx_map[item.get_text('urlname')] = str(item.ident)

            # map problems to assessment groups --
            # make some assumptions about the parent tags
            try:
                parent_name = problem.parent['display_name']
            except KeyError:
                parent_name = 'Unknown assessment name'
            if parent_name not in self._assessment_map:
                self._assessment_map[parent_name] = []
            self._assessment_map[parent_name].append(item.get_text('urlname'))

    def _load_repository_object(self, data):
        item = data['resource']
        course_dir = data['course_path']

        edxml_text = ''

        tag = item.name

        try:
            file_name = self._get_file_name(item)
        except NotFound:
            file_name = 'NO_FILE_NAME_FOUND'
            # could be inline XML
            edxml_text = item.prettify()


        if 'file_contents' in data:
            edxml_text = data['file_contents']

        display_name = self._get_display_name(item, file_name)

        if os.path.isfile(course_dir + '/' + tag + '/' + file_name + '.html'):
            edxml_text = codecs.open(course_dir + '/' + tag + '/' + file_name + '.html', encoding='utf-8').read()
        elif os.path.isfile(course_dir + '/' + tag + '/' + file_name + '.xml'):
            edxml_text = open(course_dir + '/' + tag + '/' + file_name + '.xml').read().strip()


        # files = dict()
        if edxml_text:
            if tag == 'html':
                p_soup = BeautifulSoup(edxml_text, 'html5lib')
                self.counts['html'] += 1
            else:
                p_soup = BeautifulSoup(edxml_text, 'xml')

            # TODO: this seems buggy -- there is a problem in non-split-test
            # where the third image is not sucked in.
            static_regex = re.compile('static/')
            video_regex = re.compile('.')
            tag_source_combinations = [
                {'img'                 : 'src'},
                {'video'               : 'sub'},     # for transcript files
                {'video'               : 'youtube'}  # for transcript files
            ]
            # TODO: REDO THIS FOR VIDEO...NEED TO CONSIDER A NEW FILENAME (NOT THE EXISTING METHOD)
            # SO MIGHT AS WELL MAKE A SEPARATE VIDEO BLOCK...
            for file_pair in tag_source_combinations:
                tag = file_pair.keys()[0]
                attr = file_pair[tag]
                if tag != 'video':
                    search = {attr : static_regex}
                else:
                    search = {attr : video_regex}
                tags = p_soup.find_all(**search)
                for item in tags:
                    if item.name == tag:
                        path = item[attr]
                        if tag == 'video' and attr == 'sub':
                            new_path = 'static/subs_' + path + '.srt.sjson'
                        elif tag == 'video' and attr == 'youtube':
                            new_path = 'static/subs_' + path.split(':')[1] + '.srt.sjson'
                        else:
                            new_path = path

                        if os.path.isfile(course_dir + new_path):
                            file_data = DataInputStream(open(course_dir + new_path))
                            if tag != 'video':
                                file_asset_id = self._create_file_asset(self._get_file_label(new_path), file_data)
                                edxml_text = edxml_text.replace(path, str(file_asset_id))
                            else:
                                file_asset_id = self._create_file_asset(self._get_video_file_label(new_path), file_data)
                                edxml_text = edxml_text.replace('"' + path + '"', '"' + str(file_asset_id) + '"')

                            # files[self._get_file_name_with_extension(path)] = file_data
                            # put the label into the edxml (not filename), because we will create
                            # the asset contents with that label below
                            # edxml_text = edxml_text.replace(path, self._get_file_label(path))

            # find included files that are manually put in
            match_any_regex = re.compile('.*')
            included_files = p_soup.find_all(included_files=match_any_regex)
            if included_files:
                for item in included_files:
                    paths = item['included_files'].split(';')
                    # paths = json.loads(item['included_files'])
                    for path in paths:
                        if os.path.isfile(course_dir + path):
                            file_data = DataInputStream(open(course_dir + path))
                            file_asset_id = self._create_file_asset(self._get_file_label(path), file_data)
                            edxml_text = edxml_text.replace(path, str(file_asset_id))

                            # files[self._get_file_name_with_extension(path)] = file_data
                            # edxml_text = edxml_text.replace(path, self._get_file_label(path))
        else:
            # pure XML header with no "inside" content
            edxml_text = item.prettify()

        # make an asset first, to house all the contents
        # this asset is what we return to the calling method
        afc = self.repo.get_asset_form_for_create([EDX_ASSET_TYPE])
        afc.set_genus_type(EDX_TEXT_ASSET_GENUS_TYPE)
        afc.set_display_name(clean_text(display_name))
        afc.add_text(clean_text(file_name), 'urlname')
        asset = self.repo.create_asset(afc)

        # now add the text as a content inside this asset
        asset_content_type_list = [EDX_TEXT_FILE_ASSET_CONTENT_RECORD_TYPE]
        # try:
        #     config = self.repo._RUNTIME.get_configuration()
        #     parameter_id = Id('parameter:assetContentRecordTypeForFiles@mongo')
        #     asset_content_type_list.append(config.get_value_by_parameter(parameter_id).get_type_value())
        # except:
        #     pass
        acfc = self.repo.get_asset_content_form_for_create(asset.ident,
                                                           asset_content_type_list)
        
        acfc.set_text(clean_text(edxml_text))
        # acfc = self._add_files_to_form(acfc, files)
        content = self.repo.create_asset_content(acfc)
        asset = self.repo.get_asset(asset.ident)
        return asset

    def _process_lo_mc3_map(self):
        """
        Parse the CSV file and put it into self
        :return:
        """
        mapping = {}
        with open(self.lo_mc3_map_file, 'rb') as map_file:
            reader = csv.reader(map_file)
            for row in reader:
                mapping[row[0]] = row[1::]
                mapping[row[0]] = [id_ for id_ in mapping[row[0]] if id_ != ""]
        return mapping

    def _set_bank_from_item_id(self, item_id):
        if not hasattr(self, 'bank') or not hasattr(self, 'repo'):
            # in case we use global search / root bank, need to find the item
            # first, and then attach the bank / repo object to here
            item = self.get_item(item_id)
            if self._is_problem(item_id):
                bank_id = item.object_map['bankId']
                self.bank = self._am.get_bank(Id(bank_id))
                self.repo = self._get_repository(self.bank)
            else:
                repo_id = item.object_map['repositoryId']
                bank_id = repo_id.replace('repository.Repository','assessment.Bank')
                self.bank = self._am.get_bank(Id(bank_id))
                self.repo = self._get_repository(self.bank)

    def create_assessments(self):
        # create assessments for each individual problem, with an assessment,
        # assessment offered (assumed start date of now, because it seems
        # difficult to assume from the policy file)
        # will need to modify the edx_map for problemIds
        for assessment_name, problem_names in self._assessment_map.iteritems():
        # problems = [(k, v) for k, v in self.edx_map.iteritems() if 'assessment.Item' in v]
        # for problem in problems:
            form = self.bank.get_assessment_form_for_create([])
            form.display_name = assessment_name
            form.description = 'Canonical assessment'
            assessment = self.bank.create_assessment(form)

            form = self.bank.get_assessment_offered_form_for_create(assessment.ident, [])
            form.display_name = 'Assessment offered for {0}'.format(assessment_name)
            form.description = 'Single offered'
            form.start_time = DateTime(**now_map())
            offered = self.bank.create_assessment_offered(form)
            for problem_name in problem_names:
                problem_id = self.edx_map[problem_name]
                self.bank.add_item(assessment.ident, Id(problem_id))

                self._offered_map[problem_name] = str(offered.ident)

    def create_course_and_run(self, domain_repo, course_number, course_run, org):
        """
        Add a course to the database.
        DLKit -- course maps to repository with genus type COURSE_REPO_GENUS

        Args:
            org (unicode): Organization
            repo (osid.repository.Repository): Domain knowledge repo for the course
            course_number (unicode): Course number
            run (unicode): Run
            user_id (int): Primary key of user creating the course
        Raises:
            ValueError: Duplicate course
        Returns:
            course (learningresource.Course): The created course

        """
        # Check on unique values before attempting a get_or_create, because
        # items such as import_date will always make it non-unique.
        rm = self._rm

        # check if course number + run exists. If course exists but run
        # does not, create just the run and use the existing course.
        # If both exist, throw ValueError for duplicate course.
        course = None
        for repo in rm.repositories:
            if repo.display_name.text == str(course_number):
                for child in rm.get_child_repositories(repo.ident):
                    if child.display_name.text == str(course_run):
                        raise ValueError('Duplicate Course -- already uploaded.')
                course = repo
                break

        if course is None:
            form = rm.get_repository_form_for_create([LORE_REPOSITORY, COURSE_REPOSITORY])
            form.display_name = str(course_number)
            form.description = 'An edX course'
            form.set_genus_type(COURSE_REPO_GENUS)
            form.set_org(str(org))
            course = rm.create_repository(form)
            rm.add_child_repository(domain_repo.ident, course.ident)

        form = rm.get_repository_form_for_create([LORE_REPOSITORY])
        form.display_name = str(course_run)
        form.description = 'A specific run of the course'
        form.set_genus_type(COURSE_RUN_REPO_GENUS)
        run = rm.create_repository(form)
        rm.add_child_repository(course.ident, run.ident)
        return run

    def create_resource(self, course_path, repo, parent, resource, mpath, user_repo):
        """
        Create a learning resource.
        DLKit -- let's separate the organizational units like sequential, vertical
                 from the content.
                 Into course run repo:
                    Chapter, sequential, split_test, vertical -> compositions

                 Into user repo:
                     Problems -> assessment
                     HTML, video, other -> assets

        Args:
            repo (osid.repository.Repository): course run Repo ID
            parent (osid.repository.): Parent LearningResource
            resource_type (unicode): Name of LearningResourceType
            title (unicode): Title of resource
            content_xml (unicode): XML
            course_path (unicode): Path on disk to the course files
            user_repo (osid.repository.Repository): user repository for personal content

        Returns:
            resource (learningresources.LearningResource): New LearningResource
        """
        COMPOSITIONS = ['chapter', 'sequential', 'split_test', 'vertical']
        PROBLEMS = ['problem']
        ASSETS = ['html', 'video', 'videoalpha', 'wiki', 'discussion']

        resource_type = resource.tag
        username = user_repo.effective_agent_id.identifier

        if resource_type == 'course':
            # let's not duplicate this
            return parent
        elif resource_type in COMPOSITIONS:
            form = repo.get_composition_form_for_create([EDX_COMPOSITION])
            form.display_name = resource.get("display_name", "MISSING")
            form.description = ''
            form.set_genus_type(_get_genus_type(resource_type))
            form.set_file_name(str(mpath))
            child_composition = repo.create_composition(form)

            if resource_type != 'chapter' and parent is not None:
                current_children_ids = parent.get_children_ids()
                child_ids_str = [str(i) for i in current_children_ids]
                child_ids_str.append(str(child_composition.ident))
                current_children_ids = [Id(i) for i in child_ids_str]
                form = repo.get_composition_form_for_update(parent.ident)
                form.set_children(current_children_ids)
                repo.update_composition(form)

            if resource_type not in self.counts['compositions']:
                self.counts['compositions'][resource_type] = 0
            self.counts['compositions'][resource_type] += 1

            return child_composition
        elif resource_type in PROBLEMS:
            am = _get_manager('assessment', username)
            bank = am.get_bank(user_repo.ident)

            # form = bank.get_item_form_for_create([EDX_ITEM])
            # form.display_name = title
            # form.add_text(content_xml, 'edxml')
            # form.set_genus_type(EDX_ITEM_GENUS)
            # item = bank.create_item(form)

            item = self._load_problem({
                'course_path': course_path,
                'resource': BeautifulSoup(etree.tostring(resource), 'xml').find('problem')
            })

            form = bank.get_assessment_form_for_create([])
            form.display_name = 'Assessment for {0}'.format(item.display_name.text)
            assessment = bank.create_assessment(form)
            bank.add_item(assessment.ident, item.ident)

            repo.add_asset(assessment.ident, parent.ident)
            return assessment
        elif resource_type in ASSETS:
            # form = user_repo.get_asset_form_for_create([EDX_ASSET])
            # form.display_name = '{0}'.format(title)
            # asset = user_repo.create_asset(form)
            #
            # form = user_repo.get_asset_content_form_for_create(asset.ident, [EDX_ASSET_CONTENT])
            # form.display_name = title
            # form.set_text(content_xml)
            # form.set_genus_type(_get_asset_content_genus_type(resource_type))
            # user_repo.create_asset_content(form)
            #
            # asset = user_repo.get_asset(asset.ident)
            asset = self._load_repository_object({
                'course_path': course_path,
                'resource': BeautifulSoup(etree.tostring(resource), 'xml').find(resource_type)
            })

            repo.add_asset(asset.ident, parent.ident)
            return asset

    def copy_item(self, item_id):
        item = self.get_item(item_id)

        self._set_bank_from_item_id(item_id)

        if self._is_problem(item_id):
            # need to copy questions and answers, too...
            ifc = self.bank.get_item_form_for_create([EDX_ITEM_RECORD_TYPE])
            ifc.set_genus_type(EDX_RAW_PROBLEM_TYPE)
            ifc.set_display_name(item.display_name.text)
            ifc.add_text(item.urlname, 'urlname')
            ifc.add_text(item.latex, 'latex')
            ifc.add_text(item.edxml, 'edxml')
            ifc.add_text(item.python, 'python_script')
            ifc.add_text(item.solution, 'solution')

            # add in the problem metadata like weight, attempts
            ifc.add_attempts(int(item.attempts))
            ifc.add_markdown(item.markdown)
            ifc.add_rerandomize(item.rerandomize)
            ifc.add_showanswer(item.showanswer)
            ifc.add_weight(float(item.weight))

            # add in the IRT stuff
            ifc.set_difficulty_value(float(item.difficulty))
            ifc.set_discrimination_value(float(item.discrimination))
            ifc.set_pseudo_guessing_value(float(item.guessing))
            ifc.set_time_value(Duration(seconds=int(item.time['seconds']),
                                        minutes=int(item.time['minutes']),
                                        hours=int(item.time['hours'])))

            # add provenance so we have tracking history
            ifc.set_provenance(item_id)

            # attach the current files to this item
            ifc = self._add_file_ids_to_form(ifc, item.get_asset_ids_map())

            new_item = self.bank.create_item(ifc)
        else:
            afc = self.repo.get_asset_form_for_create([])
            afc.set_genus_type(EDX_TEXT_ASSET_GENUS_TYPE)
            afc.set_display_name(item.display_name.text)
            new_item = self.repo.create_asset(afc)

            # now add the text as a content inside this asset
            acfc = self.repo.get_asset_content_form_for_create(new_item.ident,
                                                               [EDX_TEXT_FILE_ASSET_CONTENT_RECORD_TYPE])
            acfc.set_text(self.get_item_text(item_id))

            acfc.set_provenance(item_id)

            acfc = self._add_file_ids_to_form(acfc, item.get_asset_ids_map())
            content = self.repo.create_asset_content(acfc)
        return new_item

    def filter_problems_by_difficulty(self, item_ids, max, min):
        results = []
        for item_id in item_ids:
            if self._item_exists(item_id):
                if not self._is_problem(item_id):
                    pass  # fail silently if something non-problem is passed in
                else:
                    item = self.get_item(item_id)
                    if float(min) <= float(item.difficulty) <= float(max):
                        results.append(item)
        return results

    def get_bank(self):
        return self.bank

    def get_downloadable_item_text(self, item_id):
        """Formats static URLs to point locally instead of AWS

        :param item_id:
        :return:
        """
        file_regex = re.compile('[cloudfront.net]')
        attrs = {
            'draggable'             : 'icon',
            'drag_and_drop_input'   : 'img',
            'files'                 : 'included_files',
            'img'                   : 'src'
        }
        item_text = self.get_item_text(item_id, aws_urls=True)

        if self._is_problem(item_id):
            soup = BeautifulSoup(item_text, 'xml')
            _type = 'problem'
        else:
            soup = BeautifulSoup(item_text, 'html5lib')
            _type = 'html'

        for key, attr in attrs.iteritems():
            search = {attr: file_regex}
            tags = soup.find_all(**search)
            if tags:
                for tag in tags:
                    if key != 'files' and tag.name == key:
                        filename = tag[attr].split('/')[-1].split('?')[0]
                        tag[attr] = '/static/' + filename
        try:
            new_text = soup.find(_type).prettify()
            return new_text
        except:
            return item_text

    def get_file_map(self, item_id):
        item = self.get_item(item_id)
        if self._is_problem(item_id):
            map_ = item.get_files()
        else:
            # We now store image files as separate assets for HTML assets,
            # and just stick the assetIds into the HTML. So need to
            # extract the images...
            asset_content = item.get_asset_contents().next()
            try:
                map_ = asset_content.get_associated_image_files_map()
            except:
                map_ = {}
        return map_

    def get_item(self, item_id):
        if self._is_problem(item_id):
            bank = self._am.get_bank(Id(self._root_bank))
            # need to check that the ils is federated view
            bank.use_federated_bank_view()
            item = bank.get_item(Id(item_id))
            return item
        else:
            repo = self._rm.get_repository(Id(self._root_bank))
            repo.use_federated_repository_view()
            item = repo.get_asset(Id(item_id))
            return item

    def get_item_text(self, item_id, aws_urls=False):
        item = self.get_item(item_id)
        if self._is_problem(item_id):
            # need to get "prettified" edxml, with the image labels replaced
            # with paths
            if aws_urls:
                return item.get_edxml_with_aws_urls()
            else:
                return item.get_edxml()
        else:
            # TODO: what about items with multiple contents? Is a LIST the right format?
            contents = item.get_asset_contents()
            results = []
            for content in contents:
                # need to get "prettified" text, with the image labels replaced
                # with paths
                try:
                    if aws_urls:
                        prettified = content.get_text_with_aws_urls()
                    else:
                        prettified = content.get_text().text
                except:
                    prettified = content.get_text().text
                results.append(prettified)

            return results[0]  # only return the first one for now...assume only 1 per item

    def get_namespaced_item_text(self, item_id, namespace, _type):
        return self.get_item_text(item_id)

    def has_provenance_children(self, item_id):
        try:
            item = self.get_item(item_id)
            try:
                test = item.provenance_children
                return True
            except:
                return False
        except:
            return False

    def import_children(self, data):
        """
        Create LearningResource instances for each element
        of an XML tree.

        Args:
            repo (osid.repository.Repository): The course run repo
            element (lxml.etree): XML element within xbundle
            parent (osid.repository.Composition): Parent composition
            user_repo (osid.repository.Repository): User repo for personal content
        Returns:
            None
        """
        course_path = data['course_path']
        element = data['resource']
        parent = data['parent']
        repo = data['run_repo']
        user_repo = data['user_repo']

        mpath = etree.ElementTree(element).getpath(element)
        resource = self.create_resource(
            course_path=course_path,
            repo=repo, parent=parent, resource=element,
            mpath=mpath, user_repo=user_repo
        )
        target = "/static/"
        # if element.tag == "video":
        #     subname = get_video_sub(element)
        #     if subname != "":
        #         # replace the subtitle element in
        #         # the XML with a pointer to the
        #         # Asset ID
        #         # Query for the Asset in the user_repo with
        #         # displayName == subname
        #         querier = user_repo.get_asset_query()
        #         querier.match_display_name(subname)
        #         assets = user_repo.get_assets_by_query(querier)
        #
        #         # assets = StaticAsset.objects.filter(
        #         #     course__id=resource.course_id,
        #         #     asset=course_asset_basepath(course, subname),
        #         # )
        #         # for asset in assets:
        #         #     resource.static_assets.add(asset)
        # else:
        #     # Recursively find all sub-elements, looking for anything which
        #     # refers to /static/. Then make the association between the
        #     # LearningResource and StaticAsset if the StaticAsset exists.
        #     # This is like doing soup.findAll("a") and checking for whether
        #     # "/static/" is in the href, which would work but also requires
        #     # more code to check for link, img, iframe, script, and others,
        #     # and within those, check for href or src existing.
        #     soup = BeautifulSoup(etree.tostring(element), 'lxml')
        #     for child in soup.findAll():
        #         for _, val in child.attrs.items():
        #             try:
        #                 if val.startswith(target):
        #                     path = val[len(target):]
        #                     try:
        #                         asset = StaticAsset.objects.get(
        #                             course__id=resource.course_id,
        #                             asset=course_asset_basepath(course, path),
        #                         )
        #                         resource.static_assets.add(asset)
        #                     except StaticAsset.DoesNotExist:
        #                         continue
        #             except AttributeError:
        #                 continue  # not a string

        for child in element.getchildren():
            if (child.tag in DESCRIPTOR_TAGS and
                    element.tag not in CHILDLESS_TAGS):  # to prevent nested <html> tags, for example
                data = {
                    'course_path': course_path,
                    'parent': resource,
                    'resource': child,
                    'run_repo': repo,
                    'user_repo': user_repo
                }
                self.import_children(data)

    def load_content(self, data):
        self._load_problems(data)
        self._load_html(data)

        print 'No tag:', self.counts['no_tag']
        print 'in problem:', self.counts['in_problem']
        print 'in latex:', self.counts['in_latex']
        print 'in both:', self.counts['in_both']
        print 'file not found:', self.counts['file_not_found']
        print 'no useful content:', self.counts['blank']
        print 'html: ', self.counts['html']
        print 'problem types: ', self.counts['problem_types']
        print 'measurable outcomes: ', ','.join(self.counts['mo_ids'])
        print '=' * 16
        print self.edx_map

        # create assessments for each individual problem, with an assessment,
        # assessment offered (assumed start date of now, because it seems
        # difficult to assume from the policy file)
        # will need to modify the edx_map for problemIds
        self.create_assessments()

        # Now map the learning objectives in MIToces to these items...
        # make some major assumptions about the tags/moindex.html file
        # NOTE: Problems are already mapped back to LOs in QBank
        self.map_handcar(data)

        # Now create and populate assessments taken from the grades.csv
        self.populate_grades()

    def load_item(self, data):
        """
        Abstract out the need to separate problems (assessment manager)
        from other resources like HTML, video (repository manager).
        """
        item = data['resource']

        if item.name == 'problem':
            item = self._load_problem(data)
        else:
            item = self._load_repository_object(data)
        return item

    def map_handcar(self, data):
        course_files = data['course_path']
        moindex = '{0}/tabs/moindex.html'.format(course_files)
        bank = self._lm.get_objective_bank(Id(self._mitoces_id))
        repo = self.repo
        with open(moindex, 'rb') as moindex_file:
            soup = BeautifulSoup(moindex_file, 'html5lib')
            for mo in soup.find_all(itemtype="measurable_outcome"):
                mo_short_name = mo['id']

                if mo_short_name in self.lo_mc3_map:
                    handcar_ids = self.lo_mc3_map[mo_short_name]
                    learn = mo.find_all('ul', 'MOlearn')[0]
                    learn_resources = learn.find_all('a')
                    # tag the resource in Handcar
                    # create a generic "Learn" child objective, if does not
                    # exist
                    for handcar_id in handcar_ids:
                        obj_id = Id(handcar_id)
                        if bank.get_child_objectives(obj_id).available() > 0:
                            children = bank.get_child_objectives(obj_id)
                            learn_children = [c for c in children
                                              if str(c.get_cognitive_process_id()) == str(LEARN_COG_PROC)]
                            if len(learn_children) == 0:
                                obj = bank.get_objective(obj_id)
                                form = bank.get_objective_form_for_create([])
                                form.display_name = "Learn {0}".format(obj.display_name.text)
                                form.description = "Resources to learn this objective"
                                form.set_genus_type(OUTCOME_GENUS)
                                form.set_cognitive_process(LEARN_COG_PROC)
                                learn_obj = bank.create_objective(form)
                                bank.add_child_objective(obj.ident, learn_obj.ident)
                            else:
                                learn_obj = learn_children[0]
                        else:
                            obj = bank.get_objective(obj_id)
                            form = bank.get_objective_form_for_create([])
                            form.display_name = "Learn {0}".format(obj.display_name.text)
                            form.description = "Resources to learn this objective"
                            form.set_genus_type(OUTCOME_GENUS)
                            form.set_cognitive_process(LEARN_COG_PROC)
                            learn_obj = bank.create_objective(form)
                            bank.add_child_objective(obj.ident, learn_obj.ident)

                        asset_list = []

                        for resource in learn_resources:
                            try:
                                new_resource_id = self._get_new_id(resource)

                                # hack this because need to create a Handcar asset...
                                # create one locally, but take the object map and create
                                # the Handcar version
                                asset_url = 'https://{0}/api/v2/repository/repositories/{1}/assets/{2}'.format(self.qbank_host,
                                                                                                            str(self.repo.ident),
                                                                                                            new_resource_id)

                                asset_map = {
                                    "current" : True,
                                    "displayName" : {
                                        "text" : str(resource.contents[0])
                                    },
                                    "genusTypeId" : "mc3-asset%3Amc3.learning.asset.url%40MIT-OEIT",
                                    "assetContents" : [ {
                                        "current" : True,
                                        "displayName" : {
                                            "text" : str(resource.contents[0])
                                        },
                                        "genusTypeId" : "mc3-asset-content%3Amc3.learning.asset.content.unknown%40MIT-OEIT",
                                        "assetId" : "",
                                        "url" : str(asset_url),
                                        "description" : {
                                            "text" : ""
                                        }
                                    } ],
                                    "canDistributeAlterations" : False,
                                    "canDistributeCompositions" : False,
                                    "canDistributeVerbatim" : False,
                                    "composition" : False,
                                    "compositionId" : "",
                                    "copyrightStatusKnown" : False,
                                    "providerLinkIds" : [],
                                    "publicDomain" : False,
                                    "published" : False,
                                    "description" : {
                                        "text" : ""
                                    }
                                }

                                runtime = bank._provider_manager._runtime
                                url = 'https://{0}/handcar/services/learning/objectivebanks/{1}/assets?proxyname={2}'.format(get_runtime_parameter(runtime, 'hostName'),
                                                                                                                          self._mitoces_id,
                                                                                                                          get_runtime_parameter(runtime, 'appKey'))
                                handcar_asset_req = requests.post(url,
                                                                  data=json.dumps(asset_map),
                                                                  headers={'Content-Type': 'application/json'})
                                handcar_asset = handcar_asset_req.json()
                                asset_list.append(Id(handcar_asset['id']))
                            except KeyError:
                                pass

                        # delete existing activities, because the way that the
                        # moindex.html file is structured, you should only run into each MO
                        # once, hence only one set of learning activities
                        for activity in bank.get_activities_for_objective(learn_obj.ident):
                            bank.delete_activity(activity.ident)

                        activity_form = bank.get_activity_form_for_create(learn_obj.ident, [])
                        activity_form.display_name = 'Activity for learning the objective'
                        activity_form.description = 'Learn assets'
                        activity_form.set_assets(asset_list)
                        bank.create_activity(activity_form)

                        # now tag the LO with problems
                        assess = mo.find_all('ul', 'MOassess')[0]
                        assess_resources = assess.find_all('a')
                        if len(assess_resources) > 0:
                            try:
                                assessment_ids = [Id(self._get_new_id(a)) for a in assess_resources]

                                activity_form = bank.get_activity_form_for_create(obj_id, [])
                                activity_form.display_name = 'Activity for assessing the objective'
                                activity_form.description = 'Assess assessment items'
                                activity_form.set_assessments(assessment_ids)

                                bank.create_activity(activity_form)
                            except KeyError:
                                pass

    def max(self, field):
        from django.conf import settings
        default_time = '00:00:00'
        default_max = 0
        try:
            db = MongoClient()
            db_items = db[settings.DLKIT_MONGO_DB_PREFIX + 'assessment']['Item']
        except:
            if field == 'time':
                return_val = default_time
            else:
                return_val = default_max

        if field != 'time':
            try:
                item = db_items.find_one({"decimalValues": {"$exists": True}},
                                   sort=[("decimalValues." + field, -1)])
                return_val = item['decimalValues'][field]
            except:
                return_val = default_max
        else:
            try:
                # need to do some hokey stuff with the timeValue key because
                # it is a dict
                potential = db_items.find_one({"timeValue": {"$exists": True}},
                                        sort=[("timeValue.hours", -1)])
                if potential['timeValue']['hours'] == 0:
                    # try looking at minutes
                    potential2 = db_items.find_one({"timeValue"       : {"$exists": True},
                                              "timeValue.hours" : 0},
                                             sort=[("timeValue.minutes", -1)])
                    if potential2['timeValue']['minutes'] == 0:
                        # look at seconds
                        item = db_items.find_one({"timeValue"         : {"$exists": True},
                                            "timeValue.hours"   : 0,
                                            "timeValue.minutes" : 0},
                                           sort=[("timeValue.seconds", -1)])
                    else:
                        item = potential2
                else:
                    item = potential
                return_val = convert_time_dict_to_str(item['timeValue'])
            except:
                return_val = default_time
        if db:
            db.close()
        return return_val

    def min(self, field):
        from django.conf import settings
        default_time = '00:00:00'
        default_min = 0
        try:
            db = MongoClient()
            db_items = db[settings.DLKIT_MONGO_DB_PREFIX + 'assessment']['Item']
        except:
            if field == 'time':
                return_val = default_time
            else:
                return_val = default_min

        if field != 'time':
            try:
                item = db_items.find_one({"decimalValues": {"$exists": True}},
                                   sort=[("decimalValues." + field, 1)])

                return_val = item['decimalValues'][field]
            except:
                return_val = default_min
        else:
            try:
                # need to do some hokey stuff with the timeValue key because
                # it is a dict
                potential = db_items.find_one({"timeValue": {"$exists": True}},
                                        sort=[("timeValue.hours", 1)])
                if int(potential['timeValue']['hours']) == 0:
                    # try looking at minutes
                    potential2 = db_items.find_one({
                        "timeValue"         : {"$exists": True},
                        "timeValue.hours"   : 0
                    },sort=[("timeValue.minutes", 1)])
                    if int(potential2['timeValue']['minutes']) == 0:
                        # look at seconds
                        item = db_items.find_one({
                            "timeValue"         : {"$exists": True},
                            "timeValue.hours"   : 0,
                            "timeValue.minutes" : 0
                        },sort=[("timeValue.seconds", 1)])
                    else:
                        item = potential2
                else:
                    item = potential
                return_val = convert_time_dict_to_str(item['timeValue'])
            except:
                return_val = default_time
        if db:
            db.close()
        return return_val

    def populate_grades(self):
        # Now create and populate assessments taken from the grades.csv
        # use the self._offering_map dict
        gradebook = self._gm.get_gradebook(self.bank.ident)

        # clear out the gradebook
        for gradebook_column in gradebook.get_gradebook_columns():
            for entry in gradebook.get_grade_entries_for_gradebook_column(gradebook_column.ident):
                gradebook.delete_grade_entry(entry.ident)
            gradebook.delete_gradebook_column(gradebook_column.ident)
        for system in gradebook.get_grade_systems():
            gradebook.delete_grade_system(system.ident)

        form = gradebook.get_grade_system_form_for_create([])
        form.set_lowest_numeric_score(Decimal('0.00'))
        form.set_highest_numeric_score(Decimal('1.00'))
        form.set_numeric_score_increment(Decimal('0.01'))
        grade_system = gradebook.create_grade_system(form)

        with open(self.grade_file, 'rU') as grades:
            index_to_offered = {}
            index_to_gradebook_column = {}
            row_indices_to_read = []
            rows = csv.reader(grades)
            for row_index, row in enumerate(rows):
                if row_index == 0:
                    for index, header in enumerate(row):
                        if header in self._offered_map:
                            gradebook_column_form = gradebook.get_gradebook_column_form_for_create([])
                            gradebook_column_form.display_name = 'Gradebook column for {0}'.format(header)
                            gradebook_column_form.set_grade_system(grade_system.ident)
                            gradebook_column = gradebook.create_gradebook_column(gradebook_column_form)

                            index_to_gradebook_column[index] = gradebook_column.ident
                            problem_id = Id(self.edx_map[header])
                            index_to_offered[index] = Id(self._offered_map[header])

                            gradebook.alias_gradebook_column(gradebook_column.ident, problem_id)

                            row_indices_to_read.append(index)
                elif row[1] != '':  # this means there is a user ID in this row, and hence data
                    user_id = row[1]
                    print "Reading in grades for user {0}".format(user_id)
                    user_request = TestRequest(username=user_id)
                    user_am = self._get_manager(user_request, 'assessment')
                    user_bank = user_am.get_bank(self.bank.ident)

                    for index in row_indices_to_read:
                        data = row[index]
                        # now make a taken form
                        # and also add in grades
                        user_score = Decimal(str(round(Decimal(data), 2)))
                        if user_score != Decimal('-1.0'):
                            offered_id = index_to_offered[index]
                            if user_bank.get_assessments_taken_for_taker_and_assessment_offered(user_am.effective_agent_id,
                                                                                                offered_id).available() == 0:
                                taken_form = user_bank.get_assessment_taken_form_for_create(offered_id, [])
                                taken_form.display_name = 'Taken for user {0}'.format(user_id)
                                user_bank.create_assessment_taken(taken_form)

                            column_id = index_to_gradebook_column[index]
                            grade_entry_form = gradebook.get_grade_entry_form_for_create(column_id,
                                                                                         user_am.effective_agent_id,
                                                                                         [])
                            grade_entry_form.set_score(user_score)

                            gradebook.create_grade_entry(grade_entry_form)

    def set_bank_by_id(self, id):
        if isinstance(id, basestring):
            id = Id(id)
        bank = self._am.get_bank(id)
        repo = self._get_repository(bank)
        self.bank = bank
        self.repo = repo
        return self.get_bank()

    def set_bank_by_name(self, name):
        bank = None
        repo = None
        for b in self._am.banks:
            if b.display_name.text == name:
                bank = b
                self._clear_edxml_probs(bank)
                repo = self._get_repository(bank)
                break
        if not bank:
            bfc = self._am.get_bank_form_for_create([])
            bfc.set_display_name(name)
            bfc.set_description('Assessment bank for ' + name)
            bank = self._am.create_bank(bfc)
            repo = self._get_repository(bank)
        self.bank = bank
        self.repo = repo
        return self.get_bank()

    def update_item(self, item_id, data):
        """
        Per the attr:value in data, update the item
        """
        if not isinstance(item_id, basestring):
            try:
                item_id = str(item_id.ident)  # pass in the assessmentItem object
            except:
                item_id = str(item_id)  # pass in the Id() object

        self._set_bank_from_item_id(item_id)

        if self._is_problem(item_id):
            ifu = self.bank.get_item_form_for_update(Id(item_id))
            # method can be "add_" or "set_"
            for key, val in data.iteritems():
                if hasattr(ifu, 'add_' + key):
                    update_method = getattr(ifu, 'add_' + key)
                elif hasattr(ifu, 'set_' + key):
                    update_method = getattr(ifu, 'set_' + key)
                else:
                    update_method = getattr(ifu, 'set_' + key + '_value')
                # These forms are very strict (Java), so
                # have to know the exact input type. We
                # can't predict, so try a couple variations
                # if this fails...yes we're silly.
                try:
                    try:
                        try:
                            if key == 'text':
                                # somehow need to pick the label?
                                # for now, default to edxml because
                                # users can only change the main text...
                                update_method(str(val), 'edxml')
                            else:
                                update_method(str(val))
                        except:
                            update_method(int(val))
                    except:
                        update_method(float(val))
                except:
                    raise LookupError
            self.bank.update_item(ifu)
            updated_item = self.bank.get_item(Id(item_id))
        else:
            # for this, can only update the text right now,
            # so directly update the asset content
            asset = self.get_item(item_id)
            contents = asset.get_asset_contents()
            # assume one content / data['text']
            for content in contents:
                acfu = self.repo.get_asset_content_form_for_update(content.ident)
                acfu.set_text(data['text'])
                self.repo.update_asset_content(acfu)
            updated_item = self.repo.get_asset(asset.ident)
        return updated_item

    def vacuum(self, course_path, domain_repo=None, user=None):
        # unpack the .tar.gz or .zip file
        # run XBundle on the new directory
        # grab the course name / semester from the policy file / course
        # create the necessary LORE-ish repos (course, run) if necessary
        # Create compositions for each unit in the run repo
        # run load_problems
        # run load_html
        # delete the unpacked directory
        with open(course_path, 'rb') as course_file:
            if course_path.find('.zip') > 0:
                file_handle = zipfile.ZipFile(course_file)
                path = file_handle.infolist()[0].filename
                extract_path = course_path.split('.zip')[0] + '/'
            elif course_path.find('.tar.gz') > 0 or course_path.find('.tar') > 0:
                file_handle = tarfile.open(mode='r:gz', fileobj=course_file)
                path = file_handle.getnames()[0].split('/')[0]
                extract_path = course_path.split('.tar')[0] + '/'
            else:
                raise Exception('Non .zip / .tar.gz file passed in.')

            xb = XBundle(keep_urls=True, force_studio_format=True)
            file_handle.extractall(extract_path)

            file_handle.close()
            course_path = extract_path + path + '/'
            course_path = remove_extra_slashes(course_path)
            xb.import_from_directory(course_path)
            metadata = xb.metadata
            course = xb.course

            semester = course.get('semester', 'Unidentified semester')
            name = course.get('course', 'Unidentified course')
            org = course.get('org', 'Unidentified org')
            full_xml = extract_path + name + '.xml'

            xb.save(full_xml)

            if domain_repo is not None:
                # do LORE-ish things
                run_repo = self.create_course_and_run(domain_repo, name, semester, org)

                user_repo = get_or_create_user_repo(user.username)
                self.set_bank_by_id(user_repo.ident)
                data = {
                    'resource': course,
                    'course_path': course_path,
                    'parent': None,
                    'run_repo': run_repo,
                    'user_repo': user_repo
                }
                self.import_children(data)
            else:
                self.set_bank_by_name('{0}, {1}'.format(name, semester))
                data = {
                    'course_path'   : course_path,
                    'edx_xml'       : full_xml
                }
                self.load_content(data)

            shutil.rmtree(extract_path)
            return self.counts
#-----------------------------------------------------------------------------
# main

if __name__=='__main__':

    def usage():
        print "Usage: python dysonx.py [/path/to/course.tar.gz] [/path/to/course.zip] [/additional/courses]"
        print "where:"
        print "  each course.tar.gz / course.zip file should be a Studio export (.tar.gz) or "
        print "  Github XML course (.zip), compatible with edX."
        print ""
        print "examples:"
        print "  python dysonx.py ./content-mit-801x-master.zip ./content-mit-mrev.tar.gz"

    if len(sys.argv)<1:
        usage()
        sys.exit(0)

    request = TestRequest()

    for course_bundle in sys.argv[1::]:
        try:
            if ABS_PATH not in course_bundle:
                if '/' != course_bundle[0]:
                    course_bundle = '/' + course_bundle
                course_bundle = ABS_PATH + course_bundle
            dyson = DysonXUtil(request=request)
            dyson.vacuum(course_bundle)
        except Exception as ex:
            template = "An exception of type {0} occurred with {1}. Arguments:\n{2!r}"
            print template.format(type(ex).__name__, course_bundle, ex.args)
