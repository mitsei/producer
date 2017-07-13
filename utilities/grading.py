import inflection

from dlkit.runtime import RUNTIME, PROXY_SESSION
from dlkit.runtime.errors import IllegalState

from .general import *


def activate_managers(request):
    """
    Create an initial grading manager and store it in the user session
    """
    if 'gm' not in request.session:
        condition = PROXY_SESSION.get_proxy_condition()
        condition.set_http_request(request)
        proxy = PROXY_SESSION.get_proxy(condition)
        set_session_data(request, 'gm', RUNTIME.get_service_manager('GRADING', proxy=proxy))

    return request

def add_grades_to_grade_system(gradebook, grade_system, data):
    try:
        attrs_to_check = ['inputScoreStartRange', 'inputScoreEndRange', 'outputScore',
                          'displayName', 'description']
        for grade in data['grades']:
            form = gradebook.get_grade_form_for_create(grade_system.ident, [])
            for attr in attrs_to_check:
                if attr in grade:
                    if attr in ['inputScoreStartRange', 'inputScoreEndRange', 'outputScore']:
                        val = float(grade[attr])
                        getattr(form, 'set_' + inflection.underscore(attr))(val)
                    else:
                        val = str(grade[attr])
                        if attr == 'displayName':
                            form.display_name = val
                        else:
                            form.description = val
            gradebook.create_grade(form)
    except KeyError as ex:
        raise InvalidArgument('"{0}" expected in grade object.'.format(str(ex.args[0])))

def check_grade_inputs(data):
    verify_keys_present(data, 'grades')
    if not isinstance(data['grades'], list):
        raise InvalidArgument('Grades must be a list of objects.')

def check_numeric_score_inputs(data):
    expected_score_inputs = ['highestScore', 'lowestScore', 'scoreIncrement']
    verify_keys_present(data, expected_score_inputs)

def get_object_gradebook(manager, object_id, object_type='gradebook_column', gradebook_id=None):
    """Get the object's repository even without the repositoryId"""
    # primarily used for Asset
    if gradebook_id is None:
        lookup_session = get_session(manager, object_type, 'lookup')
        object_ = getattr(lookup_session, 'get_{0}'.format(object_type))(clean_id(object_id))
        gradebook_id = object_.object_map['gradebookId']
    return manager.get_gradebook(clean_id(gradebook_id))

def get_session(manager, object_type, session_type):
    """get session type for object, using the manager"""
    if manager._proxy is not None:
        session = getattr(manager, 'get_{0}_{1}_session'.format(object_type, session_type))(proxy=manager._proxy)
    else:
        session = getattr(manager, 'get_{0}_{1}_session'.format(object_type, session_type))()
    session.use_federated_gradebook_view()
    return session

def validate_score_and_grades_against_system(grade_system, data):
    if grade_system.is_based_on_grades() and 'score' in data:
        raise InvalidArgument('You cannot set a numeric score when using a grade-based system.')
    if not grade_system.is_based_on_grades() and 'grade' in data:
        raise InvalidArgument('You cannot set a grade when using a numeric score-based system.')
