import inflection

from assessments.tests.test_views import AssessmentTestCase

from copy import deepcopy

from dlkit.runtime.primordium import Id

from django.utils.http import unquote

from utilities import general as gutils
from utilities.testing import DjangoTestCase


class GradingTestCase(DjangoTestCase):
    """

    """
    def create_new_gradebook(self):
        gm = gutils.get_session_data(self.req, 'gm')
        form = gm.get_gradebook_form_for_create([])
        form.display_name = 'my new gradebook'
        form.description = 'for testing with'
        return gm.create_gradebook(form)

    def num_columns(self, val):
        self.assertEqual(
            self.gradebook.get_gradebook_columns().available(),
            val
        )

    def num_entries(self, val):
        self.assertEqual(
            self.gradebook.get_grade_entries_for_gradebook_column(self.column.ident).available(),
            val
        )

    def num_gradebooks(self, val):
        gm = gutils.get_session_data(self.req, 'gm')

        self.assertEqual(
            gm.gradebooks.available(),
            val
        )

    def num_grade_systems(self, val):
        self.assertEqual(
            self.gradebook.get_grade_systems().available(),
            val
        )

    def setUp(self):
        super(GradingTestCase, self).setUp()
        self.url = self.base_url + 'grading/'
        self.gradebook = self.create_new_gradebook()

    def setup_column(self, gradebook_id, grade_system_id):
        if not isinstance(gradebook_id, Id):
            gradebook_id = Id(gradebook_id)
        if not isinstance(grade_system_id, Id):
            grade_system_id = Id(grade_system_id)

        gm = gutils.get_session_data(self.req, 'gm')

        gradebook = gm.get_gradebook(gradebook_id)

        form = gradebook.get_gradebook_column_form_for_create([])
        form.display_name = 'test ing'
        form.description = 'foo'
        form.set_grade_system(grade_system_id)

        new_column = gradebook.create_gradebook_column(form)

        return new_column

    def setup_entry(self, gradebook_id, column_id, resource_id, score=95.7, grade=None):
        if not isinstance(gradebook_id, Id):
            gradebook_id = Id(gradebook_id)
        if not isinstance(column_id, Id):
            column_id = Id(column_id)
        if not isinstance(resource_id, Id):
            resource_id = Id(resource_id)
        gm = gutils.get_session_data(self.req, 'gm')

        gradebook = gm.get_gradebook(gradebook_id)

        form = gradebook.get_grade_entry_form_for_create(column_id, resource_id, [])
        form.display_name = 'test ing'
        form.description = 'foo'

        if grade is None:
            form.set_score(score)
        else:
            if isinstance(grade, basestring):
                grade = Id(grade)
            form.set_grade(grade)

        new_entry = gradebook.create_grade_entry(form)

        return new_entry

    def setup_grade_system(self, gradebook_id, based_on_grades=False, set_scores=False):
        if not isinstance(gradebook_id, Id):
            gradebook_id = Id(gradebook_id)

        gm = gutils.get_session_data(self.req, 'gm')

        gradebook = gm.get_gradebook(gradebook_id)

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

        return new_grade_system

    def tearDown(self):
        super(GradingTestCase, self).tearDown()


class BasicServiceTests(GradingTestCase):
    """Test the views for getting the basic service calls

    """
    def setUp(self):
        super(BasicServiceTests, self).setUp()
        self.url += 'gradebooks/'

    def tearDown(self):
        super(BasicServiceTests, self).tearDown()

    def test_instructors_can_get_list_of_gradebooks(self):
        self.login()
        url = self.url
        req = self.client.get(url)
        self.ok(req)
        self.message(req, '"count": 1')


class GradebookColumnCrUDTests(AssessmentTestCase, GradingTestCase):
    """Test the views for gradebook column crud

    """

    def setUp(self):
        super(GradebookColumnCrUDTests, self).setUp()
        self.url = self.base_url + 'grading/columns/'
        self.bad_gradebook_id = 'assessment.Bank%3A55203f0be7dde0815228bb41%40bazzim.MIT.EDU'

        self.grade_system = self.setup_grade_system(self.gradebook.ident)
        self.login()

    def tearDown(self):
        super(GradebookColumnCrUDTests, self).tearDown()

    def test_can_get_gradebook_columns(self):
        self.num_columns(0)
        self.setup_column(self.gradebook.ident, self.grade_system.ident)
        self.num_columns(1)

        url = self.url
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
            str(self.grade_system.ident)
        )

    def test_can_create_gradebook_column(self):
        self.num_columns(0)
        url = self.url

        payload = {
            'displayName': 'Letter grades',
            'description': 'A - F',
            'gradeSystemId': str(self.grade_system.ident),
            'gradebookId': str(self.gradebook.ident)
        }

        req = self.client.post(url, payload, format='json')
        self.created(req)
        column = self.json(req)
        self.assertEqual(
            column['displayName']['text'],
            payload['displayName']
        )
        self.assertEqual(
            column['description']['text'],
            payload['description']
        )
        self.assertEqual(
            column['gradeSystemId'],
            str(self.grade_system.ident)
        )
        self.num_columns(1)

    def test_creating_gradebook_column_without_grade_system_throws_exception(self):
        self.num_columns(0)
        url = self.url

        payload = {
            'displayName': 'Letter grades',
            'description': 'A - F',
            'gradebookId': str(self.gradebook.ident)
        }

        req = self.client.post(url, payload, format='json')
        self.code(req, 500)
        self.message(req,
                     '\\"gradeSystemId\\" required in input parameters but not provided.')
        self.num_columns(0)

    def test_can_update_gradebook_column(self):
        self.num_columns(0)
        column = self.setup_column(self.gradebook.ident, self.grade_system.ident)
        new_grade_system = self.setup_grade_system(self.gradebook.ident)

        url = self.url + unquote(str(column.ident))

        test_cases = [
            {'displayName': 'Exam 1'},
            {'description': 'Practice'},
            {'gradeSystemId': str(new_grade_system.ident)}
        ]

        for payload in test_cases:
            req = self.client.put(url, payload, format='json')
            self.updated(req)
            data = self.json(req)

            self.assertEqual(
                data['id'],
                str(column.ident)
            )
            key = payload.keys()[0]
            if key == 'displayName':
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
        column = self.setup_column(self.gradebook.ident, self.grade_system.ident)
        taken = self.setup_assessment()
        self.setup_entry(self.gradebook.ident, column.ident, taken.ident)
        new_grade_system = self.setup_grade_system(self.gradebook.ident)

        self.num_columns(1)

        url = self.url + unquote(str(column.ident))

        payload = {'gradeSystemId': str(new_grade_system.ident)}

        req = self.client.put(url, payload, format='json')
        self.code(req, 500)
        self.message(req,
                     'Entries exist in this gradebook column. ' +
                     'Cannot change the grade system.')

        self.num_columns(1)

    def test_trying_to_update_gradebook_column_with_no_parameters_throws_exception(self):
        self.num_columns(0)
        column = self.setup_column(self.gradebook.ident, self.grade_system.ident)

        url = self.url + str(column.ident)

        test_cases = [
            {'foo': 'bar'}
        ]

        for payload in test_cases:
            req = self.client.put(url, payload, format='json')
            self.code(req, 500)
            self.message(req,
                         'At least one of the following must be passed in: ' +
                         '[\\"displayName\\", \\"description\\", \\"gradeSystemId\\"]')
        self.num_columns(1)

    def test_can_get_gradebook_column(self):
        self.num_columns(0)
        column = self.setup_column(self.gradebook.ident, self.grade_system.ident)
        url = self.url + str(column.ident)

        req = self.client.get(url)
        self.ok(req)
        data = self.json(req)
        self.assertEqual(
            column.display_name.text,
            data['displayName']['text']
        )
        self.assertEqual(
            column.description.text,
            data['description']['text']
        )
        self.assertEqual(
            str(column.grade_system.ident),
            data['gradeSystemId']
        )
        self.assertEqual(
            str(column.ident),
            data['id']
        )
        self.num_columns(1)

    def test_getting_gradebook_column_with_invalid_id_throws_exception(self):
        self.num_columns(0)
        self.setup_column(self.gradebook.ident, self.grade_system.ident)
        url = self.url + self.bad_gradebook_id

        req = self.client.get(url)
        self.code(req, 500)
        self.message(req,
                     'Object not found.')
        self.num_columns(1)

    def test_can_delete_gradebook_column(self):
        self.num_columns(0)
        column = self.setup_column(self.gradebook.ident, self.grade_system.ident)
        self.num_columns(1)
        url = self.url + str(column.ident)

        req = self.client.delete(url)
        self.deleted(req)
        self.num_columns(0)

    def test_trying_to_delete_gradebook_column_with_entries_throws_exception(self):
        self.num_columns(0)
        column = self.setup_column(self.gradebook.ident, self.grade_system.ident)
        taken = self.setup_assessment()
        self.setup_entry(self.gradebook.ident,
                         column.ident,
                         taken.ident)
        self.num_columns(1)
        url = self.url + str(column.ident)

        req = self.client.delete(url)
        self.code(req, 500)
        self.message(req,
                     'Gradebook column is not empty.')
        self.num_columns(1)

    def test_can_get_gradebook_column_summary(self):
        self.grade_system = self.setup_grade_system(self.gradebook.ident, set_scores=True)
        column = self.setup_column(self.gradebook.ident, self.grade_system.ident)
        taken = self.setup_assessment()

        for score in range(0, 100):
            self.setup_entry(self.gradebook.ident,
                             column.ident,
                             taken.ident,
                             score=float(score))

        url = self.url + str(column.ident) + '/summary/'

        req = self.client.get(url)
        self.ok(req)
        data = self.json(req)

        test_keys = ['mean', 'median', 'mode', 'rootMeanSquared', 'standardDeviation', 'sum']
        for key in test_keys:
            self.assertIn(key, data)
            # don't worry about testing actual values -- those are tested
            # in dlkit_tests.functional.test_grading


class GradebookCrUDTests(AssessmentTestCase, GradingTestCase):
    """Test the views for gradebook crud

    """
    def setUp(self):
        super(GradebookCrUDTests, self).setUp()
        self.url = self.base_url + 'grading/gradebooks/'
        # also need a test assessment bank here to do orchestration with
        self.assessment_bank = self.create_assessment_bank()
        self.bad_gradebook_id = 'assessment.Bank%3A55203f0be7dde0815228bb41%40bazzim.MIT.EDU'

        self.login()

    def tearDown(self):
        super(GradebookCrUDTests, self).tearDown()

    def test_can_create_new_gradebook(self):
        payload = {
            'displayName': 'my new gradebook',
            'description': 'for testing with'
        }
        req = self.client.post(self.url, payload, format='json')
        self.created(req)
        gradebook = self.json(req)
        self.assertEqual(
            gradebook['displayName']['text'],
            payload['displayName']
        )
        self.assertEqual(
            gradebook['description']['text'],
            payload['description']
        )


    def test_can_create_orchestrated_gradebook_with_default_attributes(self):
        url = self.url
        payload = {
            'bankId': str(self.assessment_bank.ident)
        }
        req = self.client.post(url, payload)
        self.created(req)
        gradebook = self.json(req)
        self.assertEqual(
            gradebook['displayName']['text'],
            'Orchestrated assessment Gradebook'
        )
        self.assertEqual(
            gradebook['description']['text'],
            'Orchestrated assessment Gradebook'
        )
        self.assertEqual(
            self.assessment_bank.ident.identifier,
            Id(gradebook['id']).identifier
        )

    def test_can_create_orchestrated_gradebook_and_set_attributes(self):
        url = self.url
        payload = {
            'bankId': str(self.assessment_bank.ident),
            'displayName': 'my new orchestra',
            'description': 'for my assessment bank'
        }
        req = self.client.post(url, payload)
        self.created(req)
        gradebook = self.json(req)
        self.assertEqual(
            gradebook['displayName']['text'],
            payload['displayName']
        )
        self.assertEqual(
            gradebook['description']['text'],
            payload['description']
        )
        self.assertEqual(
            self.assessment_bank.ident.identifier,
            Id(gradebook['id']).identifier
        )

    def test_missing_parameters_throws_exception_on_create(self):
        self.num_gradebooks(1)

        url = self.url
        basic_payload = {
            'displayName': 'my new gradebook',
            'description': 'for testing with'
        }
        blacklist = ['displayName', 'description']

        for item in blacklist:
            payload = deepcopy(basic_payload)
            del payload[item]
            req = self.client.post(url, payload)
            self.code(req, 500)
            self.message(req,
                         '\\"' + item + '\\" required in input parameters but not provided.')

        self.num_gradebooks(1)

    def test_can_get_gradebook_details(self):
        url = self.url + str(self.gradebook.ident)
        req = self.client.get(url)
        self.ok(req)
        gradebook_details = self.json(req)
        for attr, val in self.gradebook.object_map.iteritems():
            self.assertEqual(
                val,
                gradebook_details[attr]
            )
        self.message(req, '"gradeSystems":')
        self.message(req, '"gradebookColumns":')

    def test_invalid_gradebook_id_throws_exception(self):
        url = self.url + 'x'
        req = self.client.get(url)
        self.code(req, 500)
        self.message(req, 'Invalid ID.')

    def test_bad_gradebook_id_throws_exception(self):
        url = self.url + self.bad_gradebook_id
        req = self.client.get(url)
        self.code(req, 500)
        self.message(req, 'Object not found.')

    def test_can_delete_gradebook(self):
        self.num_gradebooks(1)

        url = self.url + str(self.gradebook.ident)
        req = self.client.delete(url)
        self.deleted(req)

        self.num_gradebooks(0)

    def test_trying_to_delete_gradebook_with_grade_system_throws_exception(self):
        self.setup_grade_system(self.gradebook.ident)

        self.num_gradebooks(1)

        url = self.url + str(self.gradebook.ident)
        req = self.client.delete(url)
        self.code(req, 500)
        self.message(req, 'Gradebook is not empty.')

        self.num_gradebooks(1)

    def test_trying_to_delete_gradebook_with_column_throws_exception(self):
        grade_system = self.setup_grade_system(self.gradebook.ident)

        self.num_gradebooks(1)
        self.setup_column(self.gradebook.ident, grade_system.ident)

        url = self.url + str(self.gradebook.ident)
        req = self.client.delete(url)
        self.code(req, 500)
        self.message(req, 'Gradebook is not empty.')

        self.num_gradebooks(1)

    def test_trying_to_delete_gradebook_with_invalid_id_throws_exception(self):
        self.num_gradebooks(1)

        url = self.url + self.bad_gradebook_id
        req = self.client.delete(url)
        self.code(req, 500)
        self.message(req, 'Object not found.')

        self.num_gradebooks(1)


    def test_can_update_gradebook(self):
        self.num_gradebooks(1)

        url = self.url + str(self.gradebook.ident)

        test_cases = [('displayName', 'a new name'),
                      ('description', 'foobar')]
        for case in test_cases:
            payload = {
                case[0]: case[1]
            }
            req = self.client.put(url, payload, format='json')
            self.updated(req)
            updated_gradebook = self.json(req)
            self.assertEqual(
                updated_gradebook[case[0]]['text'],
                case[1]
            )

        self.num_gradebooks(1)

    def test_update_with_invalid_id_throws_exception(self):
        self.num_gradebooks(1)

        url = self.url + self.bad_gradebook_id

        test_cases = [('displayName', 'a new name'),
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
        self.num_gradebooks(1)

        url = self.url + str(self.gradebook.ident)

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
                         '[\\"displayName\\", \\"description\\"]')

        self.num_gradebooks(1)
        req = self.client.get(url)
        gradebook_fresh = self.json(req)

        params_to_test = ['id', 'displayName', 'description']
        for param in params_to_test:
            if param in ['id']:
                expected = str(self.gradebook.ident)
                returned = gradebook_fresh[param]
            else:
                expected = getattr(getattr(self.gradebook, inflection.underscore(param)),
                                   'text')
                returned = gradebook_fresh[param]['text']
            self.assertEqual(
                expected,
                returned
            )


class GradeEntryCrUDTests(AssessmentTestCase, GradingTestCase):
    """Test the views for grade entries crud

    """
    def add_grades_to_grade_system(self, system_id=None):
        if system_id is None:
            system_id = str(self.grade_system.ident)
        if isinstance(system_id, Id):
            system_id = str(system_id)

        url = '{0}grading/gradesystems/{1}'.format(self.base_url,
                                                   system_id)
        payload = {
            'gradebookId': str(self.gradebook.ident),
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

    def setUp(self):
        super(GradeEntryCrUDTests, self).setUp()
        self.bad_gradebook_id = 'assessment.Bank%3A55203f0be7dde0815228bb41%40bazzim.MIT.EDU'
        self.grade_system = self.setup_grade_system(self.gradebook.ident)
        self.column = self.setup_column(self.gradebook.ident, self.grade_system.ident)

        self.login()

        self.url = self.base_url + 'grading/entries/'

        self.taken = self.setup_assessment()

    def tearDown(self):
        super(GradeEntryCrUDTests, self).tearDown()

    def test_can_get_grade_entries_for_column(self):
        self.num_entries(0)
        self.setup_entry(self.gradebook.ident, self.column.ident, self.taken.ident)
        self.num_entries(1)

        url = '{0}grading/columns/{1}/entries'.format(self.base_url,
                                                      str(self.column.ident))
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
        self.setup_entry(self.gradebook.ident, self.column.ident, self.taken.ident)
        self.num_entries(1)

        req = self.client.get(self.url)
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
        url = self.url

        payload = {
            'displayName': 'a grade',
            'description': 'entry',
            'ignoredForCalculations': True,
            'resourceId': str(self.taken.ident),
            'score': 52.1,
            'gradebookColumnId': str(self.column.ident)
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
            payload['displayName']
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
        payload = {
            'displayName': 'a grade',
            'description': 'entry',
            'gradebookColumnId': str(self.column.ident),
            'gradebookId': str(self.gradebook.ident),
            'ignoredForCalculations': True,
            'resourceId': str(self.taken.ident),
            'score': 52.1
        }

        req = self.client.post(self.url, payload, format='json')
        self.created(req)

        data = self.json(req)
        self.assertEqual(
            data['score'],
            payload['score']
        )
        self.assertEqual(
            data['displayName']['text'],
            payload['displayName']
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

        payload = {
            'displayName': 'a grade',
            'description': 'entry',
            'ignoredForCalculations': True,
            'resourceId': str(self.taken.ident),
            'score': 52.1
        }

        req = self.client.post(self.url, payload, format='json')
        self.code(req, 500)
        self.message(req,
                     '\\"gradebookColumnId\\" required in input parameters but not provided.')
        self.num_entries(0)

    def test_creating_score_grade_entry_with_grade_based_system_throws_exception(self):
        self.num_entries(0)
        self.grade_system = self.setup_grade_system(self.gradebook.ident, based_on_grades=True)
        self.column = self.setup_column(self.gradebook.ident, self.grade_system.ident)
        self.add_grades_to_grade_system()


        payload = {
            'displayName': 'a grade',
            'description': 'entry',
            'resourceId': str(self.taken.ident),
            'score': 52.1,
            'gradebookColumnId': str(self.column.ident)
        }

        req = self.client.post(self.url, payload, format='json')
        self.code(req, 500)
        self.message(req,
                     'You cannot set a numeric score when using a grade-based system.')

        self.num_entries(0)

    def test_can_create_grade_entry_with_grade(self):
        self.num_entries(0)
        self.grade_system = self.setup_grade_system(self.gradebook.ident, based_on_grades=True)
        self.column = self.setup_column(self.gradebook.ident, self.grade_system.ident)
        grades = self.add_grades_to_grade_system()

        payload = {
            'displayName': 'a grade',
            'description': 'entry',
            'ignoredForCalculations': False,
            'resourceId': str(self.taken.ident),
            'grade': grades[0]['id'],
            'gradebookColumnId': str(self.column.ident)
        }
        req = self.client.post(self.url, payload, format='json')
        self.created(req)

        data = self.json(req)

        self.assertEqual(
            data['gradeId'],
            payload['grade']
        )
        self.assertEqual(
            data['displayName']['text'],
            payload['displayName']
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
        self.grade_system = self.setup_grade_system(self.gradebook.ident, based_on_grades=True)
        self.column = self.setup_column(self.gradebook.ident, self.grade_system.ident)
        self.add_grades_to_grade_system()

        payload = {
            'displayName': 'a grade',
            'description': 'entry',
            'ignoredForCalculations': False,
            'resourceId': str(self.taken.ident),
            'grade': self.bad_gradebook_id,
            'gradebookColumnId': str(self.column.ident)
        }
        req = self.client.post(self.url, payload, format='json')
        self.code(req, 500)
        self.message(req,
                     'Grade ID not in the acceptable set.')
        self.num_entries(0)

    def test_creating_grade_grade_entry_with_score_based_system_throws_exception(self):
        self.num_entries(0)

        grade_system = self.setup_grade_system(self.gradebook.ident, based_on_grades=True)
        grades = self.add_grades_to_grade_system(grade_system.ident)

        payload = {
            'displayName': 'a grade',
            'description': 'entry',
            'ignoredForCalculations': True,
            'resourceId': str(self.taken.ident),
            'grade': grades[0]['id'],
            'gradebookColumnId': str(self.column.ident)
        }

        req = self.client.post(self.url, payload, format='json')
        self.code(req, 500)
        self.message(req,
                     'You cannot set a grade when using a numeric score-based system.')
        self.num_entries(0)

    def test_creating_grade_entry_without_result_value_or_resource_throws_exception(self):
        self.num_entries(0)

        payload = {
            'displayName': 'Letter grades',
            'description': 'A - F',
            'gradebookColumnId': str(self.column.ident),
            'resourceId': str(self.taken.ident),
            'score': 55.0
        }

        blacklist = ['resourceId', 'score']
        for item in blacklist:
            modified_payload = deepcopy(payload)
            del modified_payload[item]
            req = self.client.post(self.url, modified_payload, format='json')
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
        entry = self.setup_entry(self.gradebook.ident, self.column.ident, self.taken.ident)

        url = '{0}{1}'.format(self.url,
                               str(entry.ident))

        test_cases = [
            {'displayName': 'Exam 1'},
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
                str(entry.ident)
            )
            key = payload.keys()[0]
            if key == 'displayName':
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
        self.grade_system = self.setup_grade_system(self.gradebook.ident, based_on_grades=True)
        self.column = self.setup_column(self.gradebook.ident, self.grade_system.ident)
        grades = self.add_grades_to_grade_system()
        entry = self.setup_entry(self.gradebook.ident,
                                 self.column.ident,
                                 self.taken.ident,
                                 grade=grades[0]['id'])

        url = '{0}{1}'.format(self.url,
                              str(entry.ident))

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
            entry.display_name.text
        )
        self.assertEqual(
            data['description']['text'],
            entry.description.text
        )
        self.assertEqual(
            data['resourceId'],
            str(entry.get_key_resource_id())
        )
        self.assertEqual(
            bool(data['ignoredForCalculations']),
            entry.is_ignored_for_calculations()
        )

        self.num_entries(1)

    def test_trying_to_update_grade_entry_with_invalid_grade_id_throws_exception(self):
        self.num_entries(0)
        self.grade_system = self.setup_grade_system(self.gradebook.ident, based_on_grades=True)
        self.column = self.setup_column(self.gradebook.ident, self.grade_system.ident)
        grades = self.add_grades_to_grade_system()
        entry = self.setup_entry(self.gradebook.ident,
                                 self.column.ident,
                                 self.taken.ident,
                                 grade=grades[0]['id'])

        url = '{0}{1}'.format(self.url,
                              str(entry.ident))

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
        entry = self.setup_entry(self.gradebook.ident, self.column.ident, self.taken.ident)

        grade_system = self.setup_grade_system(self.gradebook.ident, based_on_grades=True)
        grades = self.add_grades_to_grade_system(grade_system.ident)

        url = '{0}{1}/'.format(self.url,
                               str(entry.ident))

        payload = {'grade': grades[0]['id']}

        req = self.client.put(url, payload, format='json')
        self.code(req, 500)
        self.message(req,
                     'You cannot set a grade when using a numeric score-based system.')

        self.num_entries(1)

    def test_updating_grade_grade_entry_with_score_throws_exception(self):
        self.num_entries(0)
        self.grade_system = self.setup_grade_system(self.gradebook.ident, based_on_grades=True)
        self.column = self.setup_column(self.gradebook.ident, self.grade_system.ident)
        grades = self.add_grades_to_grade_system()
        entry = self.setup_entry(self.gradebook.ident,
                                 self.column.ident,
                                 self.taken.ident,
                                 grade=grades[0]['id'])

        url = '{0}{1}'.format(self.url,
                              str(entry.ident))

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
        entry = self.setup_entry(self.gradebook.ident, self.column.ident, self.taken.ident)

        self.num_entries(1)

        url = '{0}{1}/'.format(self.url,
                               str(entry.ident))

        req = self.client.delete(url)
        self.deleted(req)

        self.num_entries(0)


class GradeSystemCrUDTests(GradingTestCase):
    """Test the views for grade system crud

    """
    def setUp(self):
        super(GradeSystemCrUDTests, self).setUp()
        self.bad_gradebook_id = 'assessment.Bank%3A55203f0be7dde0815228bb41%40bazzim.MIT.EDU'
        self.url += 'gradesystems/'

        self.login()

    def tearDown(self):
        super(GradeSystemCrUDTests, self).tearDown()

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
        self.setup_grade_system(self.gradebook.ident)
        req = self.client.get(self.url)
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
        payload = {
            'displayName': 'Letter grades',
            'description': 'A - F',
            'gradebookId': str(self.gradebook.ident),
            'highestScore': 100,
            'lowestScore': 0,
            'scoreIncrement': 20
        }

        req = self.client.post(self.url, payload, format='json')
        self.created(req)
        grade_system = self.json(req)
        self.assertEqual(
            grade_system['displayName']['text'],
            payload['displayName']
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

        payload = {
            'displayName': '4.0 grades',
            'description': '2.0 to 4.0',
            'basedOnGrades': True,
            'gradebookId': str(self.gradebook.ident),
            'grades': [{
                'inputScoreStartRange': 90,
                'inputScoreEndRange': 100,
                'outputScore': 4,
                'displayName': 'low',
                'description': 'an easy problem'
            },{
                'inputScoreStartRange': 80,
                'inputScoreEndRange': 89,
                'outputScore': 3,
                'displayName': 'high',
                'description': 'a hard problem'
            }]
        }

        req = self.client.post(self.url, payload, format='json')
        self.created(req)
        grade_system = self.json(req)
        self.assertEqual(
            grade_system['displayName']['text'],
            payload['displayName']
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
                str(grade['displayName'])
            )
            self.assertEqual(
                grade_system['grades'][index]['description']['text'],
                str(grade['description'])
            )
        self.num_grade_systems(1)

    def test_creating_grade_system_with_missing_numeric_parameters_throws_exception(self):
        self.num_grade_systems(0)

        payload = {
            'displayName': 'Letter grades',
            'description': 'A - F',
            'gradebookId': str(self.gradebook.ident),
            'highestScore': 100,
            'lowestScore': 0,
            'scoreIncrement': 20
        }

        blacklist = ['highestScore', 'lowestScore', 'scoreIncrement']
        for item in blacklist:
            modified_payload = deepcopy(payload)
            del modified_payload[item]
            req = self.client.post(self.url, modified_payload, format='json')
            self.code(req, 500)
            self.message(req, '\\"{0}\\" required in input parameters but not provided.'.format(item))
            self.num_grade_systems(0)

    def test_creating_grade_system_with_non_list_grade_throws_exception(self):
        self.num_grade_systems(0)

        payload = {
            'displayName': '4.0 grades',
            'description': '2.0 to 4.0',
            'basedOnGrades': True,
            'gradebookId': str(self.gradebook.ident),
            'grades': {
                'inputScoreStartRange': 90,
                'inputScoreEndRange': 100,
                'outputScore': 4
            }
        }

        req = self.client.post(self.url, payload, format='json')
        self.code(req, 500)
        self.message(req, 'Grades must be a list of objects.')
        self.num_grade_systems(0)

    def test_can_update_grade_system_with_numeric_scores(self):
        grade_system = self.setup_grade_system(self.gradebook.ident)
        url = self.url + str(grade_system.ident)

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
                str(grade_system.ident)
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
        grade_system = self.setup_grade_system(self.gradebook.ident, True)

        self.assertEqual(
            grade_system['grades'].available(),
            0
        )

        url = self.url + str(grade_system.ident)

        test_cases = [{
            'grades': [{
                'inputScoreStartRange': 90,
                'inputScoreEndRange': 100,
                'outputScore': 4,
                'displayName': 'new grade',
                'description': 'here to stay'
            }]
        }]

        for payload in test_cases:
            req = self.client.put(url, payload, format='json')
            self.updated(req)
            data = self.json(req)

            self.assertEqual(
                data['id'],
                str(grade_system.ident)
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
                    elif key == 'displayName':
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
        grade_system = self.setup_grade_system(self.gradebook.ident)

        self.assertIsNone(grade_system.object_map['basedOnGrades'])
        url = self.url + str(grade_system.ident)

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
        grade_system = self.setup_grade_system(self.gradebook.ident)

        self.assertEqual(
            grade_system.object_map['grades'],
            []
        )
        self.assertIsNone(grade_system.object_map['basedOnGrades'])

        url = self.url + str(grade_system.ident)

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
                'displayName': 'foo',
                'description': 'bar'
            }]
        }

        req = self.client.put(url, payload, format='json')
        self.updated(req)
        data = self.json(req)

        self.assertTrue(data['basedOnGrades'])

        self.assertEqual(
            data['id'],
            str(grade_system.ident)
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
                elif key == 'displayName':
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
        grade_system = self.setup_grade_system(self.gradebook.ident, True)

        self.assertEqual(
            grade_system.object_map['grades'],
            []
        )
        self.assertTrue(grade_system.object_map['basedOnGrades'])

        url = self.url + str(grade_system.ident)

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
            str(grade_system.ident)
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
        grade_system = self.setup_grade_system(self.gradebook.ident)

        url = self.url + str(grade_system.ident)

        payload = {
            'displayName': 'new name',
            'description': 'baz'
        }

        req = self.client.put(url, payload, format='json')
        self.updated(req)
        updated_grade_system = self.json(req)

        self.assertEqual(
            updated_grade_system['displayName']['text'],
            payload['displayName']
        )
        self.assertEqual(
            updated_grade_system['description']['text'],
            payload['description']
        )

    def test_update_with_no_parameters_throws_exception(self):
        self.num_grade_systems(0)
        grade_system = self.setup_grade_system(self.gradebook.ident)

        url = self.url + str(grade_system.ident)

        self.num_grade_systems(1)

        payload = {
            'foo': 'bar'
        }

        req = self.client.put(url, payload, format='json')
        self.code(req, 500)
        self.message(req,
                     ('At least one of the following must be passed in: [\\"displayName\\", ' +
                     '\\"description\\", \\"basedOnGrades\\", \\"grades\\", ' +
                     '\\"highestScore\\", \\"lowestScore\\", \\"scoreIncrement\\"'))
        self.num_grade_systems(1)

    def test_can_delete_grade_system(self):
        self.num_grade_systems(0)
        grade_system = self.setup_grade_system(self.gradebook.ident)
        url = self.url + str(grade_system.ident)

        req = self.client.delete(url)
        self.deleted(req)
        self.num_grade_systems(0)

    def test_trying_to_delete_grade_system_with_columns_throws_exception(self):
        self.num_grade_systems(0)
        grade_system = self.setup_grade_system(self.gradebook.ident)
        self.num_grade_systems(1)
        self.setup_column(self.gradebook.ident, grade_system.ident)

        url = self.url + str(grade_system.ident)

        req = self.client.delete(url)
        self.code(req, 500)
        self.message(req,
                     'Grade system being used by gradebook columns. ' +
                     'Cannot delete it.')
        self.num_grade_systems(1)
