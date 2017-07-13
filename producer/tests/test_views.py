from dlkit.runtime.proxy_example import User

from repository.tests.test_views import RepositoryTestCase

from utilities import general as gutils
from utilities.testing import ABS_PATH


class ImportTests(RepositoryTestCase):
    """Test course import

    """
    def setUp(self):
        super(ImportTests, self).setUp()
        self.domain_repo = self.create_new_repo()
        self.test_file_path = ABS_PATH + '/producer/tests/files/content-mit-1805x-master.zip'

        self.user = User(username='cjshaw@mit.edu', authenticated=True)

    def tearDown(self):
        super(ImportTests, self).tearDown()

    def test_can_import_class(self):
        counts = gutils.upload_class(self.test_file_path, self.domain_repo, self.user)

        self.assertEqual(
            counts['html'],
            117
        )
        self.assertEqual(
            counts['compositions']['chapter'],
            12
        )
        self.assertEqual(
            counts['compositions']['sequential'],
            40
        )
        self.assertEqual(
            counts['compositions']['vertical'],
            35
        )
        self.assertEqual(
            counts['problem_types']['multiplechoiceresponse'],
            46
        )
        self.assertEqual(
            counts['problem_types']['numericalresponse'],
            222
        )
