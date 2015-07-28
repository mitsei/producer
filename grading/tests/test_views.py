import os
import boto
import json
import envoy

from minimocktest import MockTestCase
from django.test.utils import override_settings
from rest_framework.test import APITestCase, APIClient

from assessments_users.models import APIUser

from copy import deepcopy

from utilities import assessment as autils
from utilities import general as gutils
from utilities import grading as grutils
from utilities import repository as rutils
from utilities import resource as resutils
from utilities.testing import configure_test_bucket, create_test_request, create_test_bank

from django.conf import settings

from dlkit_django.primordium import Id, DataInputStream

from boto.s3.key import Key


PROJECT_PATH = os.path.dirname(os.path.abspath(__file__))
ABS_PATH = os.path.abspath(os.path.join(PROJECT_PATH, os.pardir))


@override_settings(DLKIT_MONGO_DB_PREFIX='test_',
                   CLOUDFRONT_DISTRO='d1v4o60a4yrgi8.cloudfront.net',
                   CLOUDFRONT_DISTRO_ID='E1OEKZHRUO35M9',
                   S3_BUCKET='mitodl-repository-test')
class DjangoTestCase(APITestCase, MockTestCase):
    """
    A TestCase class that combines minimocktest and django.test.TestCase

    http://pykler.github.io/MiniMockTest/
    """
    def _pre_setup(self):
        APITestCase._pre_setup(self)
        MockTestCase.setUp(self)
        # optional: shortcut client handle for quick testing
        self.client = APIClient()

    def _post_teardown(self):
        MockTestCase.tearDown(self)
        APITestCase._post_teardown(self)

    def code(self, _req, _code):
        self.assertEqual(_req.status_code, _code)

    def create_new_gradebook(self):
        payload = {
            'name': 'my new gradebook',
            'description': 'for testing with'
        }
        req = self.new_gradebook_post(payload)
        return self.json(req)

    def created(self, _req):
        self.code(_req, 201)

    def deleted(self, _req):
        self.code(_req, 204)

    def filename(self, file_):
        try:
            return file_.name.split('/')[-1]
        except AttributeError:
            return file_.split('/')[-1]

    def is_cloudfront_url(self, _url):
        self.assertIn(
            'https://d1v4o60a4yrgi8.cloudfront.net/',
            _url
        )

        expected_params = ['?Expires=','&Signature=','&Key-Pair-Id=APKAIGRK7FPIAJR675NA']

        for param in expected_params:
            self.assertIn(
                param,
                _url
            )

    def json(self, _req):
        return json.loads(_req.content)

    def login(self, non_instructor=False):
        if non_instructor:
            self.client.login(username=self.student_name, password=self.student_password)
        else:
            self.client.login(username=self.username, password=self.password)

    def message(self, _req, _msg):
        self.assertIn(_msg, str(_req.content))

    def new_gradebook_post(self, payload):
        url = self.url + 'gradebooks/'
        self.login()
        return self.client.post(url, payload)

    def ok(self, _req):
        self.assertEqual(_req.status_code, 200)

    def setUp(self):
        configure_test_bucket()
        self.url = '/api/v2/grading/'
        self.username = 'cjshaw@mit.edu'
        self.password = 'jinxem'
        self.user = APIUser.objects.create_user(username=self.username,
                                                password=self.password)
        self.student_name = 'astudent'
        self.student_password = 'blahblah'
        self.student = APIUser.objects.create_user(username=self.student_name,
                                                   password=self.student_password)
        self.req = create_test_request(self.user)

        self.test_file = open(ABS_PATH + '/tests/files/Flexure_structure_with_hints.pdf')

        envoy.run('mongo test_grading --eval "db.dropDatabase()"')

    def setup_assessment(self):
        autils.activate_managers(self.req)
        am = gutils.get_session_data(self.req, 'am')
        bank = am.get_bank(Id(self.gradebook['id']))

        item_form = bank.get_item_form_for_create([])
        item_form.display_name = 'test item'
        item_form.description = 'for testing'
        item = bank.create_item(item_form)

        assessment_form = bank.get_assessment_form_for_create([])
        assessment_form.display_name = 'an assessment'
        assessment_form.description = 'for testing'
        assessment = bank.create_assessment(assessment_form)

        bank.add_item(assessment.ident, item.ident)

        offered_form = bank.get_assessment_offered_form_for_create(assessment.ident, [])
        offered = bank.create_assessment_offered(offered_form)

        taken_form = bank.get_assessment_taken_form_for_create(offered.ident, [])
        taken = bank.create_assessment_taken(taken_form)

        return taken.object_map

    def setup_column(self, gradebook_id, grade_system_id):
        grutils.activate_managers(self.req)
        gm = gutils.get_session_data(self.req, 'gm')

        gradebook = gm.get_gradebook(Id(gradebook_id))

        form = gradebook.get_gradebook_column_form_for_create([])
        form.display_name = 'test ing'
        form.description = 'foo'
        form.set_grade_system(Id(grade_system_id))

        new_column = gradebook.create_gradebook_column(form)

        return new_column.object_map

    def setup_entry(self, gradebook_id, column_id, resource_id, score=95.7, grade=None):
        grutils.activate_managers(self.req)
        gm = gutils.get_session_data(self.req, 'gm')

        gradebook = gm.get_gradebook(Id(gradebook_id))

        form = gradebook.get_grade_entry_form_for_create(Id(column_id), Id(resource_id), [])
        form.display_name = 'test ing'
        form.description = 'foo'

        if grade is None:
            form.set_score(score)
        else:
            if isinstance(grade, basestring):
                grade = Id(grade)
            form.set_grade(grade)

        new_entry = gradebook.create_grade_entry(form)

        return new_entry.object_map

    def setup_grade_system(self, gradebook_id, based_on_grades=False, set_scores=False):
        grutils.activate_managers(self.req)
        gm = gutils.get_session_data(self.req, 'gm')

        gradebook = gm.get_gradebook(Id(gradebook_id))

        form = gradebook.get_grade_system_form_for_create([])
        form.display_name = 'test ing'
        form.description = 'foo'

        if based_on_grades:
            form.set_based_on_grades(True)
        elif set_scores:
            form.set_highest_numeric_score(100.0)
            form.set_lowest_numeric_score(0.0)
            form.set_numeric_score_increment(1.0)

        new_grade_system = gradebook.create_grade_system(form)

        return new_grade_system.object_map

    def tearDown(self):
        self.test_file.close()
        envoy.run('mongo test_grading --eval "db.dropDatabase()"')

    def updated(self, _req):
        self.code(_req, 202)


class BasicServiceTests(DjangoTestCase):
    """Test the views for getting the basic service calls

    """
    def setUp(self):
        super(BasicServiceTests, self).setUp()

    def tearDown(self):
        super(BasicServiceTests, self).tearDown()

    def test_authenticated_users_can_see_available_services(self):
        self.login()
        url = self.url
        req = self.client.get(url)
        self.ok(req)
        self.message(req, 'documentation')
        self.message(req, 'gradebooks')

    def test_non_authenticated_users_cannot_see_available_services(self):
        url = self.url
        req = self.client.get(url)
        self.code(req, 403)

    def test_instructors_can_get_list_of_gradebooks(self):
        self.login()
        url = self.url + 'gradebooks/'
        req = self.client.get(url)
        self.ok(req)
        self.message(req, '"count": 0')

    def test_learners_cannot_see_list_of_gradebooks(self):
        self.login(non_instructor=True)
        url = self.url + 'gradebooks/'
        req = self.client.get(url)
        self.code(req, 403)
        # self.ok(req)
        # self.message(req, '"count": 0')


class DocumentationTests(DjangoTestCase):
    """Test the views for getting the documentation

    """
    def setUp(self):
        super(DocumentationTests, self).setUp()

    def tearDown(self):
        super(DocumentationTests, self).tearDown()

    def test_authenticated_users_can_view_docs(self):
        self.login()
        url = self.url + 'docs/'
        req = self.client.get(url)
        self.ok(req)
        self.message(req, 'Documentation for MIT Grading Service, V2')


    def test_non_authenticated_users_can_view_docs(self):
        url = self.url + 'docs/'
        req = self.client.get(url)
        self.ok(req)
        self.message(req, 'Documentation for MIT Grading Service, V2')


    def test_student_can_view_docs(self):
        self.login(non_instructor=True)
        url = self.url + 'docs/'
        req = self.client.get(url)
        self.ok(req)
        self.message(req, 'Documentation for MIT Grading Service, V2')


class GradebookColumnCrUDTests(DjangoTestCase):
    """Test the views for gradebook column crud

    """
    def num_columns(self, val):
        grutils.activate_managers(self.req)
        gm = gutils.get_session_data(self.req, 'gm')

        gradebook = gm.get_gradebook(Id(self.gradebook['id']))
        self.assertEqual(
            gradebook.get_gradebook_columns().available(),
            val
        )

    def setUp(self):
        super(GradebookColumnCrUDTests, self).setUp()
        self.bad_gradebook_id = 'assessment.Bank%3A55203f0be7dde0815228bb41%40bazzim.MIT.EDU'
        self.gradebook = self.create_new_gradebook()

        test_file = '/tests/files/ps_2015_beam_2gages.pdf'
        test_file2 = '/tests/files/Backstage_v2_quick_guide.docx'

        self.test_file = open(ABS_PATH + test_file, 'r')
        self.test_file2 = open(ABS_PATH + test_file2, 'r')

        self.student2_name = 'astudent2'
        self.student2_password = 'blahblah'
        self.student2 = APIUser.objects.create_user(username=self.student2_name,
                                                    password=self.student2_password)


        self.grade_system = self.setup_grade_system(self.gradebook['id'])

    def tearDown(self):
        super(GradebookColumnCrUDTests, self).tearDown()
        self.test_file.close()
        self.test_file2.close()

    def test_can_get_gradebook_columns(self):
        self.num_columns(0)
        self.setup_column(self.gradebook['id'], self.grade_system['id'])
        self.num_columns(1)
        self.login()

        url = self.url + 'gradebooks/' + self.gradebook['id'] + '/columns/'
        req = self.client.get(url)
        self.ok(req)
        columns = self.json(req)['data']['results']
        self.assertEqual(
            len(columns),
            1
        )
        self.assertEqual(
            columns[0]['displayName']['text'],
            'test ing'
        )
        self.assertEqual(
            columns[0]['description']['text'],
            'foo'
        )
        self.assertEqual(
            columns[0]['gradeSystemId'],
            self.grade_system['id']
        )

    def test_can_create_gradebook_column(self):
        self.num_columns(0)
        self.login()
        url = self.url + 'gradebooks/' + self.gradebook['id'] + '/columns/'

        payload = {
            'name': 'Letter grades',
            'description': 'A - F',
            'gradeSystemId': self.grade_system['id']
        }

        req = self.client.post(url, payload, format='json')
        self.created(req)
        column = self.json(req)
        self.assertEqual(
            column['displayName']['text'],
            payload['name']
        )
        self.assertEqual(
            column['description']['text'],
            payload['description']
        )
        self.assertEqual(
            column['gradeSystemId'],
            self.grade_system['id']
        )
        self.num_columns(1)

    def test_creating_gradebook_column_without_grade_system_throws_exception(self):
        self.num_columns(0)
        self.login()
        url = self.url + 'gradebooks/' + self.gradebook['id'] + '/columns/'

        payload = {
            'name': 'Letter grades',
            'description': 'A - F'
        }

        req = self.client.post(url, payload, format='json')
        self.code(req, 500)
        self.message(req,
                     '\\"gradeSystemId\\" required in input parameters but not provided.')
        self.num_columns(0)

    def test_can_update_gradebook_column(self):
        self.num_columns(0)
        column = self.setup_column(self.gradebook['id'], self.grade_system['id'])
        new_grade_system = self.setup_grade_system(self.gradebook['id'])

        self.login()
        url = self.url + 'gradebooks/' + self.gradebook['id'] + '/columns/' + column['id']

        test_cases = [
            {'name': 'Exam 1'},
            {'description': 'Practice'},
            {'gradeSystemId': new_grade_system['id']}
        ]

        for payload in test_cases:
            req = self.client.put(url, payload, format='json')
            self.updated(req)
            data = self.json(req)

            self.assertEqual(
                data['id'],
                column['id']
            )
            key = payload.keys()[0]
            if key == 'name':
                self.assertEqual(
                    data['displayName']['text'],
                    payload[key]
                )
            elif key == 'description':
                self.assertEqual(
                    data['description']['text'],
                    payload[key]
                )
            else:
                self.assertEqual(
                    data['gradeSystemId'],
                    payload[key]
                )

        self.num_columns(1)

    def test_trying_to_update_gradebook_column_grade_system_when_entries_present_throws_exception(self):
        self.num_columns(0)
        column = self.setup_column(self.gradebook['id'], self.grade_system['id'])
        taken = self.setup_assessment()
        self.setup_entry(self.gradebook['id'], column['id'], taken['id'])
        new_grade_system = self.setup_grade_system(self.gradebook['id'])

        self.num_columns(1)

        self.login()
        url = self.url + 'gradebooks/' + self.gradebook['id'] + '/columns/' + column['id']

        payload = {'gradeSystemId': new_grade_system['id']}

        req = self.client.put(url, payload, format='json')
        self.code(req, 500)
        self.message(req,
                     'Entries exist in this gradebook column. ' +
                     'Cannot change the grade system.')

        self.num_columns(1)

    def test_trying_to_update_gradebook_column_with_no_parameters_throws_exception(self):
        self.num_columns(0)
        column = self.setup_column(self.gradebook['id'], self.grade_system['id'])

        self.login()
        url = self.url + 'gradebooks/' + self.gradebook['id'] + '/columns/' + column['id']

        test_cases = [
            {'foo': 'bar'}
        ]

        for payload in test_cases:
            req = self.client.put(url, payload, format='json')
            self.code(req, 500)
            self.message(req,
                         'At least one of the following must be passed in: ' +
                         '[\\"name\\", \\"description\\", \\"gradeSystemId\\"]')
        self.num_columns(1)

    def test_can_get_gradebook_column(self):
        self.num_columns(0)
        self.login()
        column = self.setup_column(self.gradebook['id'], self.grade_system['id'])
        url = self.url + 'gradebooks/' + self.gradebook['id'] + '/columns/' + column['id']

        req = self.client.get(url)
        self.ok(req)
        data = self.json(req)
        self.assertEqual(
            column['displayName']['text'],
            data['displayName']['text']
        )
        self.assertEqual(
            column['description']['text'],
            data['description']['text']
        )
        self.assertEqual(
            column['gradeSystemId'],
            data['gradeSystemId']
        )
        self.assertEqual(
            column['id'],
            data['id']
        )
        self.num_columns(1)

    def test_getting_gradebook_column_with_invalid_id_throws_exception(self):
        self.num_columns(0)
        self.login()
        self.setup_column(self.gradebook['id'], self.grade_system['id'])
        url = self.url + 'gradebooks/' + self.gradebook['id'] + '/columns/' + self.bad_gradebook_id

        req = self.client.get(url)
        self.code(req, 500)
        self.message(req,
                     'Object not found.')
        self.num_columns(1)

    def test_can_delete_gradebook_column(self):
        self.num_columns(0)
        self.login()
        column = self.setup_column(self.gradebook['id'], self.grade_system['id'])
        self.num_columns(1)
        url = self.url + 'gradebooks/' + self.gradebook['id'] + '/columns/' + column['id']

        req = self.client.delete(url)
        self.deleted(req)
        self.num_columns(0)

    def test_trying_to_delete_gradebook_column_with_entries_throws_exception(self):
        self.num_columns(0)
        self.login()
        column = self.setup_column(self.gradebook['id'], self.grade_system['id'])
        taken = self.setup_assessment()
        self.setup_entry(self.gradebook['id'],
                         column['id'],
                         taken['id'])
        self.num_columns(1)
        url = self.url + 'gradebooks/' + self.gradebook['id'] + '/columns/' + column['id']

        req = self.client.delete(url)
        self.code(req, 500)
        self.message(req,
                     'Gradebook column is not empty.')
        self.num_columns(1)

    def test_can_get_gradebook_column_summary(self):
        self.grade_system = self.setup_grade_system(self.gradebook['id'], set_scores=True)
        self.login()
        column = self.setup_column(self.gradebook['id'], self.grade_system['id'])
        taken = self.setup_assessment()

        for score in range(0, 100):
            self.setup_entry(self.gradebook['id'],
                             column['id'],
                             taken['id'],
                             score=float(score))

        url = self.url + 'gradebooks/' + self.gradebook['id'] + '/columns/' + column['id'] + '/summary/'

        req = self.client.get(url)
        self.ok(req)
        data = self.json(req)

        test_keys = ['mean', 'median', 'mode', 'rootMeanSquared', 'standardDeviation', 'sum']
        for key in test_keys:
            self.assertIn(key, data)
            # don't worry about testing actual values -- those are tested
            # in dlkit_tests.functional.test_grading


class GradebookCrUDTests(DjangoTestCase):
    """Test the views for gradebook crud

    """
    def num_gradebooks(self, val):
        grutils.activate_managers(self.req)
        gm = gutils.get_session_data(self.req, 'gm')

        self.assertEqual(
            gm.gradebooks.available(),
            val
        )

    def setUp(self):
        super(GradebookCrUDTests, self).setUp()
        # also need a test assessment bank here to do orchestration with
        self.assessment_bank = create_test_bank(self)
        self.bad_gradebook_id = 'assessment.Bank%3A55203f0be7dde0815228bb41%40bazzim.MIT.EDU'

    def tearDown(self):
        super(GradebookCrUDTests, self).tearDown()

    def test_can_create_new_gradebook(self):
        payload = {
            'name': 'my new gradebook',
            'description': 'for testing with'
        }
        req = self.new_gradebook_post(payload)
        self.created(req)
        gradebook = self.json(req)
        self.assertEqual(
            gradebook['displayName']['text'],
            payload['name']
        )
        self.assertEqual(
            gradebook['description']['text'],
            payload['description']
        )


    def test_can_create_orchestrated_gradebook_with_default_attributes(self):
        url = self.url + 'gradebooks/'
        payload = {
            'bankId': self.assessment_bank['id']
        }
        self.login()
        req = self.client.post(url, payload)
        self.created(req)
        gradebook = self.json(req)
        self.assertEqual(
            gradebook['displayName']['text'],
            'Orchestrated assessment Gradebook'
        )
        self.assertEqual(
            gradebook['description']['text'],
            'Orchestrated Gradebook for the assessment service'
        )
        self.assertEqual(
            Id(self.assessment_bank['id']).identifier,
            Id(gradebook['id']).identifier
        )

    def test_can_create_orchestrated_gradebook_and_set_attributes(self):
        url = self.url + 'gradebooks/'
        payload = {
            'bankId': self.assessment_bank['id'],
            'name': 'my new orchestra',
            'description': 'for my assessment bank'
        }
        self.login()
        req = self.client.post(url, payload)
        self.created(req)
        gradebook = self.json(req)
        self.assertEqual(
            gradebook['displayName']['text'],
            payload['name']
        )
        self.assertEqual(
            gradebook['description']['text'],
            payload['description']
        )
        self.assertEqual(
            Id(self.assessment_bank['id']).identifier,
            Id(gradebook['id']).identifier
        )

    def test_missing_parameters_throws_exception_on_create(self):
        self.num_gradebooks(0)

        url = self.url + 'gradebooks/'
        basic_payload = {
            'name': 'my new gradebook',
            'description': 'for testing with'
        }
        blacklist = ['name', 'description']
        self.login()

        for item in blacklist:
            payload = deepcopy(basic_payload)
            del payload[item]
            req = self.client.post(url, payload)
            self.code(req, 500)
            self.message(req,
                         '\\"' + item + '\\" required in input parameters but not provided.')

        self.num_gradebooks(0)

    def test_can_get_gradebook_details(self):
        self.login()
        gradebook = self.create_new_gradebook()
        url = self.url + 'gradebooks/' + str(gradebook['id'])
        req = self.client.get(url)
        self.ok(req)
        gradebook_details = self.json(req)
        for attr, val in gradebook.iteritems():
            self.assertEqual(
                val,
                gradebook_details[attr]
            )
        self.message(req, '"gradeSystems":')
        self.message(req, '"gradebookColumns":')

    def test_invalid_gradebook_id_throws_exception(self):
        self.login()
        self.create_new_gradebook()
        url = self.url + 'gradebooks/x'
        req = self.client.get(url)
        self.code(req, 500)
        self.message(req, 'Invalid ID.')


    def test_bad_gradebook_id_throws_exception(self):
        self.login()
        self.create_new_gradebook()
        url = self.url + 'gradebooks/' + self.bad_gradebook_id
        req = self.client.get(url)
        self.code(req, 500)
        self.message(req, 'Object not found.')

    def test_can_delete_gradebook(self):
        self.num_gradebooks(0)

        self.login()

        gradebook = self.create_new_gradebook()

        self.num_gradebooks(1)

        url = self.url + 'gradebooks/' + str(gradebook['id'])
        req = self.client.delete(url)
        self.deleted(req)

        self.num_gradebooks(0)

    def test_trying_to_delete_gradebook_with_grade_system_throws_exception(self):
        self.num_gradebooks(0)

        self.login()

        gradebook = self.create_new_gradebook()
        self.setup_grade_system(gradebook['id'])

        self.num_gradebooks(1)

        url = self.url + 'gradebooks/' + str(gradebook['id'])
        req = self.client.delete(url)
        self.code(req, 500)
        self.message(req, 'Gradebook is not empty.')

        self.num_gradebooks(1)

    def test_trying_to_delete_gradebook_with_column_throws_exception(self):
        self.num_gradebooks(0)

        self.login()

        gradebook = self.create_new_gradebook()
        grade_system = self.setup_grade_system(gradebook['id'])

        self.num_gradebooks(1)
        self.setup_column(gradebook['id'], grade_system['id'])

        url = self.url + 'gradebooks/' + str(gradebook['id'])
        req = self.client.delete(url)
        self.code(req, 500)
        self.message(req, 'Gradebook is not empty.')

        self.num_gradebooks(1)

    def test_trying_to_delete_gradebook_with_invalid_id_throws_exception(self):
        self.num_gradebooks(0)

        self.login()

        self.create_new_gradebook()

        self.num_gradebooks(1)

        url = self.url + 'gradebooks/' + self.bad_gradebook_id
        req = self.client.delete(url)
        self.code(req, 500)
        self.message(req, 'Object not found.')

        self.num_gradebooks(1)


    def test_can_update_gradebook(self):
        self.num_gradebooks(0)

        self.login()

        gradebook = self.create_new_gradebook()

        self.num_gradebooks(1)

        url = self.url + 'gradebooks/' + str(gradebook['id'])

        test_cases = [('name', 'a new name'),
                      ('description', 'foobar')]
        for case in test_cases:
            payload = {
                case[0]: case[1]
            }
            req = self.client.put(url, payload, format='json')
            self.updated(req)
            updated_gradebook = self.json(req)
            if case[0] == 'name':
                self.assertEqual(
                    updated_gradebook['displayName']['text'],
                    case[1]
                )
            else:
                self.assertEqual(
                    updated_gradebook['description']['text'],
                    case[1]
                )

        self.num_gradebooks(1)

    def test_update_with_invalid_id_throws_exception(self):
        self.num_gradebooks(0)

        self.login()

        self.create_new_gradebook()

        self.num_gradebooks(1)

        url = self.url + 'gradebooks/' + self.bad_gradebook_id

        test_cases = [('name', 'a new name'),
                      ('description', 'foobar')]
        for case in test_cases:
            payload = {
                case[0]: case[1]
            }
            req = self.client.put(url, payload, format='json')
            self.code(req, 500)
            self.message(req, 'Object not found.')

        self.num_gradebooks(1)

    def test_update_with_no_params_throws_exception(self):
        self.num_gradebooks(0)

        self.login()

        gradebook = self.create_new_gradebook()

        self.num_gradebooks(1)

        url = self.url + 'gradebooks/' + str(gradebook['id'])

        test_cases = [('foo', 'bar'),
                      ('bankId', 'foobar')]
        for case in test_cases:
            payload = {
                case[0]: case[1]
            }
            req = self.client.put(url, payload, format='json')
            self.code(req, 500)
            self.message(req,
                         'At least one of the following must be passed in: ' +
                         '[\\"name\\", \\"description\\"]')

        self.num_gradebooks(1)
        req = self.client.get(url)
        gradebook_fresh = self.json(req)

        params_to_test = ['id', 'displayName', 'description']
        for param in params_to_test:
            self.assertEqual(
                gradebook[param],
                gradebook_fresh[param]
            )

    def test_student_cannot_view_gradebooks(self):
        self.create_new_gradebook()
        self.login(non_instructor=True)
        self.num_gradebooks(1)

        url = self.url + 'gradebooks/'
        req = self.client.get(url)
        self.code(req, 403)


class GradeEntryCrUDTests(DjangoTestCase):
    """Test the views for grade entries crud

    """
    def add_grades_to_grade_system(self, system_id=None):
        if system_id is None:
            system_id = self.grade_system['id']

        url = '{0}gradebooks/{1}/gradesystems/{2}'.format(self.url,
                                                          self.gradebook['id'],
                                                          system_id)
        payload = {
            'grades': [{
                'inputScoreStartRange': 90,
                'inputScoreEndRange': 100,
                'outputScore': 4,
                'name': 'low',
                'description': 'an easy problem'
            },{
                'inputScoreStartRange': 80,
                'inputScoreEndRange': 89,
                'outputScore': 3,
                'name': 'high',
                'description': 'a hard problem'
            }]
        }

        req = self.client.put(url, payload, format='json')
        data = self.json(req)
        return data['grades']

    def num_entries(self, val):
        grutils.activate_managers(self.req)
        gm = gutils.get_session_data(self.req, 'gm')

        gradebook = gm.get_gradebook(Id(self.gradebook['id']))
        self.assertEqual(
            gradebook.get_grade_entries_for_gradebook_column(Id(self.column['id'])).available(),
            val
        )

    def setUp(self):
        super(GradeEntryCrUDTests, self).setUp()
        self.bad_gradebook_id = 'assessment.Bank%3A55203f0be7dde0815228bb41%40bazzim.MIT.EDU'
        self.gradebook = self.create_new_gradebook()
        self.grade_system = self.setup_grade_system(self.gradebook['id'])
        self.column = self.setup_column(self.gradebook['id'], self.grade_system['id'])

        test_file = '/tests/files/ps_2015_beam_2gages.pdf'
        test_file2 = '/tests/files/Backstage_v2_quick_guide.docx'

        self.test_file = open(ABS_PATH + test_file, 'r')
        self.test_file2 = open(ABS_PATH + test_file2, 'r')

        self.student2_name = 'astudent2'
        self.student2_password = 'blahblah'
        self.student2 = APIUser.objects.create_user(username=self.student2_name,
                                                    password=self.student2_password)

    def tearDown(self):
        super(GradeEntryCrUDTests, self).tearDown()
        self.test_file.close()
        self.test_file2.close()

    def test_can_get_grade_entries_for_column(self):
        self.num_entries(0)
        taken = self.setup_assessment()
        self.setup_entry(self.gradebook['id'], self.column['id'], taken['id'])
        self.num_entries(1)
        self.login()

        url = '{0}gradebooks/{1}/columns/{2}/entries'.format(self.url,
                                                             self.gradebook['id'],
                                                             self.column['id'])
        req = self.client.get(url)
        self.ok(req)
        entries = self.json(req)['data']['results']
        self.assertEqual(
            len(entries),
            1
        )
        self.assertEqual(
            entries[0]['displayName']['text'],
            'test ing'
        )
        self.assertEqual(
            entries[0]['description']['text'],
            'foo'
        )
        self.assertEqual(
            entries[0]['score'],
            95.7
        )

    def test_can_get_grade_entries_for_gradebook(self):
        self.num_entries(0)
        taken = self.setup_assessment()
        self.setup_entry(self.gradebook['id'], self.column['id'], taken['id'])
        self.num_entries(1)
        self.login()

        url = '{0}gradebooks/{1}/entries'.format(self.url,
                                                self.gradebook['id'])
        req = self.client.get(url)
        self.ok(req)
        entries = self.json(req)['data']['results']
        self.assertEqual(
            len(entries),
            1
        )
        self.assertEqual(
            entries[0]['displayName']['text'],
            'test ing'
        )
        self.assertEqual(
            entries[0]['description']['text'],
            'foo'
        )
        self.assertEqual(
            entries[0]['score'],
            95.7
        )

    def test_can_create_grade_entry_with_score(self):
        self.num_entries(0)
        taken = self.setup_assessment()
        self.login()
        url = '{0}gradebooks/{1}/columns/{2}/entries/'.format(self.url,
                                                              self.gradebook['id'],
                                                              self.column['id'])

        payload = {
            'name': 'a grade',
            'description': 'entry',
            'ignoredForCalculations': True,
            'resourceId': taken['id'],
            'score': 52.1
        }

        req = self.client.post(url, payload, format='json')
        self.created(req)

        data = self.json(req)
        self.assertEqual(
            data['score'],
            payload['score']
        )
        self.assertEqual(
            data['displayName']['text'],
            payload['name']
        )
        self.assertEqual(
            data['description']['text'],
            payload['description']
        )
        self.assertEqual(
            data['resourceId'],
            payload['resourceId']
        )
        self.assertEqual(
            data['ignoredForCalculations'],
            payload['ignoredForCalculations']
        )

        self.num_entries(1)

    def test_can_create_grade_entry_against_gradebook(self):
        self.num_entries(0)
        taken = self.setup_assessment()
        self.login()
        url = '{0}gradebooks/{1}/entries/'.format(self.url,
                                                  self.gradebook['id'])

        payload = {
            'name': 'a grade',
            'description': 'entry',
            'columnId': self.column['id'],
            'ignoredForCalculations': True,
            'resourceId': taken['id'],
            'score': 52.1
        }

        req = self.client.post(url, payload, format='json')
        self.created(req)

        data = self.json(req)
        self.assertEqual(
            data['score'],
            payload['score']
        )
        self.assertEqual(
            data['displayName']['text'],
            payload['name']
        )
        self.assertEqual(
            data['description']['text'],
            payload['description']
        )
        self.assertEqual(
            data['resourceId'],
            payload['resourceId']
        )
        self.assertEqual(
            data['ignoredForCalculations'],
            payload['ignoredForCalculations']
        )

        self.num_entries(1)

    def test_creating_grade_entry_against_gradebook_requires_column_id_parameter(self):
        self.num_entries(0)
        taken = self.setup_assessment()
        self.login()
        url = '{0}gradebooks/{1}/entries/'.format(self.url,
                                                  self.gradebook['id'])

        payload = {
            'name': 'a grade',
            'description': 'entry',
            'ignoredForCalculations': True,
            'resourceId': taken['id'],
            'score': 52.1
        }

        req = self.client.post(url, payload, format='json')
        self.code(req, 500)
        self.message(req,
                     '\\"columnId\\" required in input parameters but not provided.')
        self.num_entries(0)

    def test_creating_score_grade_entry_with_grade_based_system_throws_exception(self):
        self.num_entries(0)
        self.grade_system = self.setup_grade_system(self.gradebook['id'], based_on_grades=True)
        self.column = self.setup_column(self.gradebook['id'], self.grade_system['id'])
        self.add_grades_to_grade_system()

        taken = self.setup_assessment()
        self.login()
        url = '{0}gradebooks/{1}/columns/{2}/entries/'.format(self.url,
                                                              self.gradebook['id'],
                                                              self.column['id'])

        payload = {
            'name': 'a grade',
            'description': 'entry',
            'resourceId': taken['id'],
            'score': 52.1
        }

        req = self.client.post(url, payload, format='json')
        self.code(req, 500)
        self.message(req,
                     'You cannot set a numeric score when using a grade-based system.')

        self.num_entries(0)

    def test_can_create_grade_entry_with_grade(self):
        self.num_entries(0)
        self.grade_system = self.setup_grade_system(self.gradebook['id'], based_on_grades=True)
        self.column = self.setup_column(self.gradebook['id'], self.grade_system['id'])
        grades = self.add_grades_to_grade_system()

        taken = self.setup_assessment()
        self.login()
        url = '{0}gradebooks/{1}/columns/{2}/entries/'.format(self.url,
                                                              self.gradebook['id'],
                                                              self.column['id'])

        payload = {
            'name': 'a grade',
            'description': 'entry',
            'ignoredForCalculations': False,
            'resourceId': taken['id'],
            'grade': grades[0]['id']
        }
        req = self.client.post(url, payload, format='json')
        self.created(req)

        data = self.json(req)

        self.assertEqual(
            data['gradeId'],
            payload['grade']
        )
        self.assertEqual(
            data['displayName']['text'],
            payload['name']
        )
        self.assertEqual(
            data['description']['text'],
            payload['description']
        )
        self.assertEqual(
            data['resourceId'],
            payload['resourceId']
        )
        self.assertEqual(
            data['ignoredForCalculations'],
            payload['ignoredForCalculations']
        )

        self.num_entries(1)

    def test_creating_grade_entry_with_invalid_grade_id_throws_exception(self):
        self.num_entries(0)
        self.grade_system = self.setup_grade_system(self.gradebook['id'], based_on_grades=True)
        self.column = self.setup_column(self.gradebook['id'], self.grade_system['id'])
        self.add_grades_to_grade_system()

        taken = self.setup_assessment()
        self.login()
        url = '{0}gradebooks/{1}/columns/{2}/entries/'.format(self.url,
                                                              self.gradebook['id'],
                                                              self.column['id'])

        payload = {
            'name': 'a grade',
            'description': 'entry',
            'ignoredForCalculations': False,
            'resourceId': taken['id'],
            'grade': self.bad_gradebook_id
        }
        req = self.client.post(url, payload, format='json')
        self.code(req, 500)
        self.message(req,
                     'Grade ID not in the acceptable set.')
        self.num_entries(0)

    def test_creating_grade_grade_entry_with_score_based_system_throws_exception(self):
        self.num_entries(0)

        grade_system = self.setup_grade_system(self.gradebook['id'], based_on_grades=True)
        grades = self.add_grades_to_grade_system(grade_system['id'])

        taken = self.setup_assessment()
        self.login()
        url = '{0}gradebooks/{1}/columns/{2}/entries/'.format(self.url,
                                                              self.gradebook['id'],
                                                              self.column['id'])

        payload = {
            'name': 'a grade',
            'description': 'entry',
            'ignoredForCalculations': True,
            'resourceId': taken['id'],
            'grade': grades[0]['id']
        }

        req = self.client.post(url, payload, format='json')
        self.code(req, 500)
        self.message(req,
                     'You cannot set a grade when using a numeric score-based system.')
        self.num_entries(0)

    def test_creating_grade_entry_without_result_value_or_resource_throws_exception(self):
        self.num_entries(0)
        taken = self.setup_assessment()
        self.login()
        url = '{0}gradebooks/{1}/columns/{2}/entries/'.format(self.url,
                                                              self.gradebook['id'],
                                                              self.column['id'])

        payload = {
            'name': 'Letter grades',
            'description': 'A - F',
            'resourceId': taken['id'],
            'score': 55.0
        }

        blacklist = ['resourceId', 'score']
        for item in blacklist:
            modified_payload = deepcopy(payload)
            del modified_payload[item]
            req = self.client.post(url, modified_payload, format='json')
            self.code(req, 500)
            if item == 'resourceId':
                self.message(req,
                             '\\"{0}\\" required in input parameters but not provided.'.format(item))
            else:
                self.message(req,
                             'At least one of the following must be passed in: [\\"grade\\", ' +
                             '\\"score\\", \\"ignoredForCalculations\\"')
            self.num_entries(0)

    def test_can_update_score_based_grade_entry(self):
        self.num_entries(0)
        taken = self.setup_assessment()
        entry = self.setup_entry(self.gradebook['id'], self.column['id'], taken['id'])

        self.login()
        url = '{0}gradebooks/{1}/entries/{2}/'.format(self.url,
                                                      self.gradebook['id'],
                                                      entry['id'])

        test_cases = [
            {'name': 'Exam 1'},
            {'description': 'Practice'},
            {'ignoredForCalculations': False},
            {'score': 5.0}
        ]

        for payload in test_cases:
            req = self.client.put(url, payload, format='json')
            self.updated(req)
            data = self.json(req)

            self.assertEqual(
                data['id'],
                entry['id']
            )
            key = payload.keys()[0]
            if key == 'name':
                self.assertEqual(
                    data['displayName']['text'],
                    payload[key]
                )
            elif key == 'description':
                self.assertEqual(
                    data['description']['text'],
                    payload[key]
                )
            else:
                self.assertEqual(
                    data[key],
                    payload[key]
                )

        self.num_entries(1)

    def test_can_update_grade_based_grade_entry(self):
        self.num_entries(0)
        self.grade_system = self.setup_grade_system(self.gradebook['id'], based_on_grades=True)
        self.column = self.setup_column(self.gradebook['id'], self.grade_system['id'])
        grades = self.add_grades_to_grade_system()
        taken = self.setup_assessment()
        entry = self.setup_entry(self.gradebook['id'],
                                 self.column['id'],
                                 taken['id'],
                                 grade=grades[0]['id'])

        self.login()
        url = '{0}gradebooks/{1}/entries/{2}'.format(self.url,
                                                     self.gradebook['id'],
                                                     entry['id'])

        payload = {
            'grade': grades[1]['id']
        }
        req = self.client.put(url, payload, format='json')
        self.updated(req)

        data = self.json(req)

        self.assertEqual(
            data['gradeId'],
            payload['grade']
        )
        self.assertEqual(
            data['displayName']['text'],
            entry['displayName']['text']
        )
        self.assertEqual(
            data['description']['text'],
            entry['description']['text']
        )
        self.assertEqual(
            data['resourceId'],
            entry['resourceId']
        )
        self.assertEqual(
            data['ignoredForCalculations'],
            entry['ignoredForCalculations']
        )

        self.num_entries(1)

    def test_trying_to_update_grade_entry_with_invalid_grade_id_throws_exception(self):
        self.num_entries(0)
        self.grade_system = self.setup_grade_system(self.gradebook['id'], based_on_grades=True)
        self.column = self.setup_column(self.gradebook['id'], self.grade_system['id'])
        grades = self.add_grades_to_grade_system()
        taken = self.setup_assessment()
        entry = self.setup_entry(self.gradebook['id'],
                                 self.column['id'],
                                 taken['id'],
                                 grade=grades[0]['id'])

        self.login()
        url = '{0}gradebooks/{1}/entries/{2}'.format(self.url,
                                                     self.gradebook['id'],
                                                     entry['id'])

        payload = {
            'grade': self.bad_gradebook_id
        }
        req = self.client.put(url, payload, format='json')
        self.code(req, 500)
        self.message(req,
                     'Grade ID not in the acceptable set.')
        self.num_entries(1)

    def test_updating_score_grade_entry_with_grade_throws_exception(self):
        self.num_entries(0)
        taken = self.setup_assessment()
        entry = self.setup_entry(self.gradebook['id'], self.column['id'], taken['id'])

        grade_system = self.setup_grade_system(self.gradebook['id'], based_on_grades=True)
        grades = self.add_grades_to_grade_system(grade_system['id'])

        self.login()
        url = '{0}gradebooks/{1}/entries/{2}/'.format(self.url,
                                                      self.gradebook['id'],
                                                      entry['id'])

        payload = {'grade': grades[0]['id']}

        req = self.client.put(url, payload, format='json')
        self.code(req, 500)
        self.message(req,
                     'You cannot set a grade when using a numeric score-based system.')

        self.num_entries(1)

    def test_updating_grade_grade_entry_with_score_throws_exception(self):
        self.num_entries(0)
        self.grade_system = self.setup_grade_system(self.gradebook['id'], based_on_grades=True)
        self.column = self.setup_column(self.gradebook['id'], self.grade_system['id'])
        grades = self.add_grades_to_grade_system()
        taken = self.setup_assessment()
        entry = self.setup_entry(self.gradebook['id'],
                                 self.column['id'],
                                 taken['id'],
                                 grade=grades[0]['id'])

        self.login()
        url = '{0}gradebooks/{1}/entries/{2}'.format(self.url,
                                                     self.gradebook['id'],
                                                     entry['id'])

        payload = {
            'score': 21.5
        }
        req = self.client.put(url, payload, format='json')
        self.code(req, 500)
        self.message(req,
                     'You cannot set a numeric score when using a grade-based system.')

        self.num_entries(1)

    def test_can_delete_grade_entry(self):
        self.num_entries(0)
        taken = self.setup_assessment()
        entry = self.setup_entry(self.gradebook['id'], self.column['id'], taken['id'])

        self.num_entries(1)

        self.login()
        url = '{0}gradebooks/{1}/entries/{2}/'.format(self.url,
                                                      self.gradebook['id'],
                                                      entry['id'])

        req = self.client.delete(url)
        self.deleted(req)

        self.num_entries(0)


class GradeSystemCrUDTests(DjangoTestCase):
    """Test the views for grade system crud

    """
    def num_grade_systems(self, val):
        grutils.activate_managers(self.req)
        gm = gutils.get_session_data(self.req, 'gm')

        gradebook = gm.get_gradebook(Id(self.gradebook['id']))
        self.assertEqual(
            gradebook.get_grade_systems().available(),
            val
        )

    def setUp(self):
        super(GradeSystemCrUDTests, self).setUp()
        self.bad_gradebook_id = 'assessment.Bank%3A55203f0be7dde0815228bb41%40bazzim.MIT.EDU'
        self.gradebook = self.create_new_gradebook()

        test_file = '/tests/files/ps_2015_beam_2gages.pdf'
        test_file2 = '/tests/files/Backstage_v2_quick_guide.docx'

        self.test_file = open(ABS_PATH + test_file, 'r')
        self.test_file2 = open(ABS_PATH + test_file2, 'r')

        self.student2_name = 'astudent2'
        self.student2_password = 'blahblah'
        self.student2 = APIUser.objects.create_user(username=self.student2_name,
                                                    password=self.student2_password)

    def tearDown(self):
        super(GradeSystemCrUDTests, self).tearDown()
        self.test_file.close()
        self.test_file2.close()

    def verify_numeric_scores(self, expected, data):
        for key, value in expected.iteritems():
            if key == 'highestScore':
                attr = 'highestNumericScore'
            elif key == 'lowestScore':
                attr = 'lowestNumericScore'
            else:
                attr = 'numericScoreIncrement'
            self.assertEqual(
                data[attr],
                float(value)
            )

    def test_can_get_gradebook_grade_systems(self):
        self.setup_grade_system(self.gradebook['id'])
        self.login()
        url = self.url + 'gradebooks/' + self.gradebook['id'] + '/gradesystems/'
        req = self.client.get(url)
        self.ok(req)
        grade_systems = self.json(req)['data']['results']
        self.assertEqual(
            len(grade_systems),
            1
        )
        self.assertEqual(
            grade_systems[0]['displayName']['text'],
            'test ing'
        )
        self.assertEqual(
            grade_systems[0]['description']['text'],
            'foo'
        )

    def test_can_create_grade_system_with_numeric_scores(self):
        self.num_grade_systems(0)
        self.login()
        url = self.url + 'gradebooks/' + self.gradebook['id'] + '/gradesystems/'

        payload = {
            'name': 'Letter grades',
            'description': 'A - F',
            'highestScore': 100,
            'lowestScore': 0,
            'scoreIncrement': 20
        }

        req = self.client.post(url, payload, format='json')
        self.created(req)
        grade_system = self.json(req)
        self.assertEqual(
            grade_system['displayName']['text'],
            payload['name']
        )
        self.assertEqual(
            grade_system['description']['text'],
            payload['description']
        )
        self.assertEqual(
            grade_system['highestNumericScore'],
            payload['highestScore']
        )
        self.assertEqual(
            grade_system['lowestNumericScore'],
            payload['lowestScore']
        )
        self.assertEqual(
            grade_system['numericScoreIncrement'],
            payload['scoreIncrement']
        )
        self.num_grade_systems(1)

    def test_can_create_grade_system_with_grades(self):
        self.num_grade_systems(0)
        self.login()
        url = self.url + 'gradebooks/' + self.gradebook['id'] + '/gradesystems/'

        payload = {
            'name': '4.0 grades',
            'description': '2.0 to 4.0',
            'basedOnGrades': True,
            'grades': [{
                'inputScoreStartRange': 90,
                'inputScoreEndRange': 100,
                'outputScore': 4,
                'name': 'low',
                'description': 'an easy problem'
            },{
                'inputScoreStartRange': 80,
                'inputScoreEndRange': 89,
                'outputScore': 3,
                'name': 'high',
                'description': 'a hard problem'
            }]
        }

        req = self.client.post(url, payload, format='json')
        self.created(req)
        grade_system = self.json(req)
        self.assertEqual(
            grade_system['displayName']['text'],
            payload['name']
        )
        self.assertEqual(
            grade_system['description']['text'],
            payload['description']
        )
        self.assertEqual(
            grade_system['basedOnGrades'],
            payload['basedOnGrades']
        )

        for index, grade in enumerate(payload['grades']):
            self.assertEqual(
                grade_system['grades'][index]['inputScoreEndRange'],
                float(grade['inputScoreEndRange'])
            )
            self.assertEqual(
                grade_system['grades'][index]['inputScoreStartRange'],
                float(grade['inputScoreStartRange'])
            )
            self.assertEqual(
                grade_system['grades'][index]['outputScore'],
                float(grade['outputScore'])
            )
            self.assertEqual(
                grade_system['grades'][index]['displayName']['text'],
                str(grade['name'])
            )
            self.assertEqual(
                grade_system['grades'][index]['description']['text'],
                str(grade['description'])
            )
        self.num_grade_systems(1)

    def test_creating_grade_system_with_missing_numeric_parameters_throws_exception(self):
        self.num_grade_systems(0)
        self.login()
        url = self.url + 'gradebooks/' + self.gradebook['id'] + '/gradesystems/'

        payload = {
            'name': 'Letter grades',
            'description': 'A - F',
            'highestScore': 100,
            'lowestScore': 0,
            'scoreIncrement': 20
        }

        blacklist = ['highestScore', 'lowestScore', 'scoreIncrement']
        for item in blacklist:
            modified_payload = deepcopy(payload)
            del modified_payload[item]
            req = self.client.post(url, modified_payload, format='json')
            self.code(req, 500)
            self.message(req, '\\"{0}\\" required in input parameters but not provided.'.format(item))
            self.num_grade_systems(0)

    # Deprecated...
    # def test_creating_grade_system_with_missing_grade_parameters_throws_exception(self):
    #     self.num_grade_systems(0)
    #     self.login()
    #     url = self.url + 'gradebooks/' + self.gradebook['id'] + '/gradesystems/'
    #
    #     payload = {
    #         'name': '4.0 grades',
    #         'description': '2.0 to 4.0',
    #         'basedOnGrades': True,
    #         'grades': [{
    #             'inputScoreStartRange': 90,
    #             'inputScoreEndRange': 100,
    #             'outputScore': 4
    #         },{
    #             'inputScoreStartRange': 80,
    #             'inputScoreEndRange': 89,
    #             'outputScore': 3
    #         }]
    #     }
    #
    #     blacklist = ['inputScoreStartRange', 'inputScoreEndRange', 'outputScore']
    #     for item in blacklist:
    #         modified_payload = deepcopy(payload)
    #         del modified_payload['grades'][0][item]
    #         req = self.client.post(url, modified_payload, format='json')
    #         self.code(req, 500)
    #         self.message(req, '\\"{}\\" expected in grade object.'.format(item))
    #         self.num_grade_systems(0)

    def test_creating_grade_system_with_non_list_grade_throws_exception(self):
        self.num_grade_systems(0)
        self.login()
        url = self.url + 'gradebooks/' + self.gradebook['id'] + '/gradesystems/'

        payload = {
            'name': '4.0 grades',
            'description': '2.0 to 4.0',
            'basedOnGrades': True,
            'grades': {
                'inputScoreStartRange': 90,
                'inputScoreEndRange': 100,
                'outputScore': 4
            }
        }

        req = self.client.post(url, payload, format='json')
        self.code(req, 500)
        self.message(req, 'Grades must be a list of objects.')
        self.num_grade_systems(0)

    def test_can_update_grade_system_with_numeric_scores(self):
        grade_system = self.setup_grade_system(self.gradebook['id'])
        self.login()
        url = self.url + 'gradebooks/' + self.gradebook['id'] + '/gradesystems/' + grade_system['id']

        test_cases = [{
            'highestScore': 42
        }, {
            'lowestScore': -5
        }, {
            'scoreIncrement': 27.5
        }]

        for payload in test_cases:
            req = self.client.put(url, payload, format='json')
            self.updated(req)
            data = self.json(req)

            self.assertEqual(
                data['id'],
                grade_system['id']
            )
            key = payload.keys()[0]
            if key == 'highestScore':
                attr = 'highestNumericScore'
            elif key == 'lowestScore':
                attr = 'lowestNumericScore'
            else:
                attr = 'numericScoreIncrement'
            self.assertEqual(
                data[attr],
                float(payload[key])
            )

    def test_can_update_grade_system_with_grades(self):
        grade_system = self.setup_grade_system(self.gradebook['id'], True)

        self.assertEqual(
            grade_system['grades'],
            []
        )

        self.login()
        url = self.url + 'gradebooks/' + self.gradebook['id'] + '/gradesystems/' + grade_system['id']

        test_cases = [{
            'grades': [{
                'inputScoreStartRange': 90,
                'inputScoreEndRange': 100,
                'outputScore': 4,
                'name': 'new grade',
                'description': 'here to stay'
            }]
        }]

        for payload in test_cases:
            req = self.client.put(url, payload, format='json')
            self.updated(req)
            data = self.json(req)

            self.assertEqual(
                data['id'],
                grade_system['id']
            )
            self.assertEqual(
                len(payload['grades']),
                len(data['grades'])
            )
            for index, grade in enumerate(payload['grades']):
                for key, value in grade.iteritems():
                    if key in ['inputScoreStartRange', 'inputScoreEndRange', 'outputScore']:
                        self.assertEqual(
                            data['grades'][index][key],
                            float(value)
                        )
                    elif key == 'name':
                        self.assertEqual(
                            data['grades'][index]['displayName']['text'],
                            str(value)
                        )
                    else:
                        self.assertEqual(
                            data['grades'][index]['description']['text'],
                            str(value)
                        )

    def test_can_update_based_on_grade(self):
        grade_system = self.setup_grade_system(self.gradebook['id'])

        self.assertIsNone(grade_system['basedOnGrades'])
        self.login()
        url = self.url + 'gradebooks/' + self.gradebook['id'] + '/gradesystems/' + grade_system['id']

        payload = {
            'basedOnGrades': True
        }

        req = self.client.put(url, payload, format='json')
        self.updated(req)
        updated_grade_system = self.json(req)
        self.assertTrue(updated_grade_system['basedOnGrades'])

        payload = {
            'basedOnGrades': False
        }

        req = self.client.put(url, payload, format='json')
        self.updated(req)
        updated_grade_system = self.json(req)
        self.assertFalse(updated_grade_system['basedOnGrades'])

    def test_can_change_based_on_grade_and_add_grades_in_same_update(self):
        grade_system = self.setup_grade_system(self.gradebook['id'])

        self.assertEqual(
            grade_system['grades'],
            []
        )
        self.assertIsNone(grade_system['basedOnGrades'])

        self.login()
        url = self.url + 'gradebooks/' + self.gradebook['id'] + '/gradesystems/' + grade_system['id']

        score_payload = {
            'highestScore': 100,
            'lowestScore': 0,
            'scoreIncrement': 20
        }

        req = self.client.put(url, score_payload, format='json')
        self.updated(req)
        data = self.json(req)

        self.verify_numeric_scores(score_payload, data)

        payload = {
            'basedOnGrades': True,
            'grades': [{
                'inputScoreStartRange': 90,
                'inputScoreEndRange': 100,
                'outputScore': 4,
                'name': 'foo',
                'description': 'bar'
            }]
        }

        req = self.client.put(url, payload, format='json')
        self.updated(req)
        data = self.json(req)

        self.assertTrue(data['basedOnGrades'])

        self.assertEqual(
            data['id'],
            grade_system['id']
        )
        self.assertEqual(
            len(payload['grades']),
            len(data['grades'])
        )

        self.assertIsNone(data['highestNumericScore'])
        self.assertIsNone(data['lowestNumericScore'])
        self.assertIsNone(data['numericScoreIncrement'])

        for index, grade in enumerate(payload['grades']):
            for key, value in grade.iteritems():
                if key in ['inputScoreStartRange', 'inputScoreEndRange', 'outputScore']:
                    self.assertEqual(
                        data['grades'][index][key],
                        float(value)
                    )
                elif key == 'name':
                    self.assertEqual(
                        data['grades'][index]['displayName']['text'],
                        str(value)
                    )
                else:
                    self.assertEqual(
                        data['grades'][index]['description']['text'],
                        str(value)
                    )

    def test_can_change_based_on_grade_and_add_scores_in_same_update(self):
        grade_system = self.setup_grade_system(self.gradebook['id'], True)

        self.assertEqual(
            grade_system['grades'],
            []
        )
        self.assertTrue(grade_system['basedOnGrades'])

        self.login()
        url = self.url + 'gradebooks/' + self.gradebook['id'] + '/gradesystems/' + grade_system['id']

        payload = {
            'basedOnGrades': False,
            'highestScore': 100,
            'lowestScore': 0,
            'scoreIncrement': 20
        }

        req = self.client.put(url, payload, format='json')
        self.updated(req)
        data = self.json(req)

        self.assertFalse(data['basedOnGrades'])

        self.assertEqual(
            data['id'],
            grade_system['id']
        )
        self.assertEqual(
            [],
            data['grades']
        )
        for key, value in payload.iteritems():
            if key != 'basedOnGrades':
                if key == 'highestScore':
                    attr = 'highestNumericScore'
                elif key == 'lowestScore':
                    attr = 'lowestNumericScore'
                else:
                    attr = 'numericScoreIncrement'
                self.assertEqual(
                    data[attr],
                    float(value)
                )

    def test_can_update_name_and_description(self):
        grade_system = self.setup_grade_system(self.gradebook['id'])

        self.login()
        url = self.url + 'gradebooks/' + self.gradebook['id'] + '/gradesystems/' + grade_system['id']

        payload = {
            'name': 'new name',
            'description': 'baz'
        }

        req = self.client.put(url, payload, format='json')
        self.updated(req)
        updated_grade_system = self.json(req)

        self.assertEqual(
            updated_grade_system['displayName']['text'],
            payload['name']
        )
        self.assertEqual(
            updated_grade_system['description']['text'],
            payload['description']
        )

    def test_update_with_no_parameters_throws_exception(self):
        self.num_grade_systems(0)
        grade_system = self.setup_grade_system(self.gradebook['id'])

        self.login()
        url = self.url + 'gradebooks/' + self.gradebook['id'] + '/gradesystems/' + grade_system['id']

        self.num_grade_systems(1)

        payload = {
            'foo': 'bar'
        }

        req = self.client.put(url, payload, format='json')
        self.code(req, 500)
        self.message(req,
                     ('At least one of the following must be passed in: [\\"name\\", ' +
                     '\\"description\\", \\"basedOnGrades\\", \\"grades\\", ' +
                     '\\"highestScore\\", \\"lowestScore\\", \\"scoreIncrement\\"'))
        self.num_grade_systems(1)

    def test_can_delete_grade_system(self):
        self.num_grade_systems(0)
        self.login()
        grade_system = self.setup_grade_system(self.gradebook['id'])
        url = self.url + 'gradebooks/' + self.gradebook['id'] + '/gradesystems/' + grade_system['id']

        req = self.client.delete(url)
        self.deleted(req)
        self.num_grade_systems(0)

    def test_trying_to_delete_grade_system_with_columns_throws_exception(self):
        self.num_grade_systems(0)
        grade_system = self.setup_grade_system(self.gradebook['id'])
        self.num_grade_systems(1)
        column = self.setup_column(self.gradebook['id'], grade_system['id'])

        url = self.url + 'gradebooks/' + self.gradebook['id'] + '/gradesystems/' + grade_system['id']

        req = self.client.delete(url)
        self.code(req, 500)
        self.message(req,
                     'Grade system being used by gradebook columns. ' +
                     'Cannot delete it.')
        self.num_grade_systems(1)
