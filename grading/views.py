from bson.errors import InvalidId

from django.template import RequestContext
from django.shortcuts import render_to_response


from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, exceptions
from rest_framework.permissions import AllowAny

from dlkit_django.errors import PermissionDenied, InvalidArgument, IllegalState, NotFound
from dlkit_django.primordium import Id

from utilities import general as gutils
from utilities import grading as grutils


class CreatedResponse(Response):
    def __init__(self, *args, **kwargs):
        super(CreatedResponse, self).__init__(status=status.HTTP_201_CREATED, *args, **kwargs)


class DeletedResponse(Response):
    def __init__(self, *args, **kwargs):
        super(DeletedResponse, self).__init__(status=status.HTTP_204_NO_CONTENT, *args, **kwargs)


class UpdatedResponse(Response):
    def __init__(self, *args, **kwargs):
        super(UpdatedResponse, self).__init__(status=status.HTTP_202_ACCEPTED, *args, **kwargs)


class DLKitSessionsManager(APIView):
    """ base class to handle all the dlkit session management
    """
    def initial(self, request, *args, **kwargs):
        """set up the resource manager"""
        super(DLKitSessionsManager, self).initial(request, *args, **kwargs)
        gutils.set_user(request)
        grutils.activate_managers(request)
        self.gm = gutils.get_session_data(request, 'gm')

    def finalize_response(self, request, response, *args, **kwargs):
        """save the updated repository manager"""
        try:
            gutils.set_session_data(request, 'gm', self.gm)
        except AttributeError:
            pass  # with an exception, the RM may not be set
        return super(DLKitSessionsManager, self).finalize_response(request,
                                                                   response,
                                                                   *args,
                                                                   **kwargs)


class Documentation(DLKitSessionsManager):
    """
    Shows the user documentation for talking to the RESTful service
    """
    permission_classes = (AllowAny,)

    def get(self, request, format=None):
        return render_to_response('grading/documentation.html',
                                  {},
                                  RequestContext(request))


class GradebookDetails(DLKitSessionsManager):
    """
    Shows details for a specific gradebook.
    api/v2/grading/gradebooks/<gradebook_id>/

    GET, PUT, DELETE
    PUT will update the gradebook. Only changed attributes need to be sent.
    DELETE will remove the gradebook.

    Note that for RESTful calls, you need to set the request header
    'content-type' to 'application/json'

    Example (note the use of double quotes!!):
       PUT {"name" : "a new gradebook"}
    """
    def delete(self, request, gradebook_id, format=None):
        try:
            self.gm.delete_gradebook(gutils.clean_id(gradebook_id))
            return DeletedResponse()
        except (PermissionDenied, NotFound) as ex:
            gutils.handle_exceptions(ex)
        except IllegalState as ex:
            modified_ex = type(ex)('Gradebook is not empty.')
            gutils.handle_exceptions(modified_ex)

    def get(self, request, gradebook_id, format=None):
        try:
            gradebook = self.gm.get_gradebook(gutils.clean_id(gradebook_id))
            gradebook = gutils.convert_dl_object(gradebook)
            gradebook = gutils.add_links(request,
                                         gradebook,
                                         {
                                             'gradeSystems': 'gradesystems/',
                                             'gradebookColumns': 'columns/'
                                         })
            return Response(gradebook)
        except (PermissionDenied, InvalidId, NotFound) as ex:
            gutils.handle_exceptions(ex)

    def put(self, request, gradebook_id, format=None):
        try:
            form = self.gm.get_gradebook_form_for_update(gutils.clean_id(gradebook_id))

            data = gutils.get_data_from_request(request)

            gutils.verify_at_least_one_key_present(data, ['name', 'description'])

            # should work for a form or json data
            if 'name' in data:
                form.display_name = data['name']
            if 'description' in data:
                form.description = data['description']

            updated_gradebook = self.gm.update_gradebook(form)
            updated_gradebook = gutils.convert_dl_object(updated_gradebook)
            updated_gradebook = gutils.add_links(request,
                                                 updated_gradebook,
                                                 {
                                                     'gradeSystems': 'gradesystems/',
                                                     'gradebookColumns': 'columns/'
                                                 })

            return UpdatedResponse(updated_gradebook)
        except (PermissionDenied, KeyError, InvalidArgument, NotFound) as ex:
            gutils.handle_exceptions(ex)


class GradebookGradeSystemDetails(DLKitSessionsManager):
    """
    Get grade system details
    api/v2/grading/gradebooks/<gradebook_id>/gradesystems/<gradesystem_id>/

    GET, PUT, DELETE
    PUT to modify an existing grade system (name or settings). Include only the changed parameters.
    DELETE to remove the grade system.

    Note that for RESTful calls, you need to set the request header
    'content-type' to 'application/json'

    Example (note the use of double quotes!!):
       {"name" : "an updated item"}
    """

    def delete(self, request, gradebook_id, gradesystem_id, format=None):
        try:
            gradebook = self.gm.get_gradebook(gutils.clean_id(gradebook_id))
            gradebook.delete_grade_system(gutils.clean_id(gradesystem_id))

            return DeletedResponse()
        except (PermissionDenied, InvalidArgument) as ex:
            gutils.handle_exceptions(ex)
        except IllegalState as ex:
            modified_ex = type(ex)('Grade system is being used.')
            gutils.handle_exceptions(modified_ex)

    def get(self, request, gradebook_id, gradesystem_id, format=None):
        try:
            gradebook = self.gm.get_gradebook(gutils.clean_id(gradebook_id))
            grade_system = gradebook.get_grade_system(gutils.clean_id(gradesystem_id))
            grade_system_map = grade_system.object_map

            grade_system_map.update({
                '_links': {
                    'self': gutils.build_safe_uri(request),
                }
            })

            return Response(grade_system_map)
        except (PermissionDenied, NotFound) as ex:
            gutils.handle_exceptions(ex)

    def put(self, request, gradebook_id, gradesystem_id, format=None):
        try:
            data = gutils.get_data_from_request(request)

            gutils.verify_at_least_one_key_present(data,
                                                   ['name', 'description', 'basedOnGrades',
                                                    'grades', 'highestScore', 'lowestScore',
                                                    'scoreIncrement'])

            gradebook = self.gm.get_gradebook(gutils.clean_id(gradebook_id))
            grade_system = gradebook.get_grade_system(gutils.clean_id(gradesystem_id))

            if 'basedOnGrades' in data:
                # do this first, so methods below work
                form = gradebook.get_grade_system_form_for_update(grade_system.ident)
                form.set_based_on_grades(bool(data['basedOnGrades']))

                if data['basedOnGrades']:
                    # clear out the numeric score fields
                    form.clear_highest_numeric_score()
                    form.clear_lowest_numeric_score()
                    form.clear_numeric_score_increment()
                else:
                    # clear out grades
                    for grade in grade_system.get_grades():
                        gradebook.delete_grade(grade.ident)

                grade_system = gradebook.update_grade_system(form)

            if (grade_system.is_based_on_grades() and
                    'grades' in data):
                # user wants to update the grades
                # here, wipe out all previous grades and over-write
                grutils.check_grade_inputs(data)
                if len(data['grades']) > 0:
                    for grade in grade_system.get_grades():
                        gradebook.delete_grade(grade.ident)
                    grutils.add_grades_to_grade_system(gradebook,
                                                       grade_system,
                                                       data)

            score_inputs = ['highestScore', 'lowestScore', 'scoreIncrement']
            if (not grade_system.is_based_on_grades() and
                    any(i in data for i in score_inputs)):
                form = gradebook.get_grade_system_form_for_update(grade_system.ident)

                if 'highestScore' in data:
                    form.set_highest_numeric_score(float(data['highestScore']))

                if 'lowestScore' in data:
                    form.set_lowest_numeric_score(float(data['lowestScore']))

                if 'scoreIncrement' in data:
                    form.set_numeric_score_increment(float(data['scoreIncrement']))

                gradebook.update_grade_system(form)

            if 'name' in data or 'description' in data:
                form = gradebook.get_grade_system_form_for_update(grade_system.ident)

                if 'name' in data:
                    form.display_name = data['name']
                if 'description' in data:
                    form.description = data['description']

                gradebook.update_grade_system(form)

            grade_system = gradebook.get_grade_system(grade_system.ident)

            return UpdatedResponse(grade_system.object_map)
        except (PermissionDenied, InvalidArgument, KeyError) as ex:
            gutils.handle_exceptions(ex)


class GradebookColumnDetails(DLKitSessionsManager):
    """
    Get grade system details
    api/v2/grading/gradebooks/<gradebook_id>/columns/<column_id>/

    GET, PUT, DELETE
    PUT to modify an existing gradebook column (name or gradeSystemId).
        Include only the changed parameters.
    DELETE to remove the gradebook column.

    Note that for RESTful calls, you need to set the request header
    'content-type' to 'application/json'

    Example (note the use of double quotes!!):
       {"name" : "an updated item"}
    """

    def delete(self, request, gradebook_id, column_id, format=None):
        try:
            gradebook = self.gm.get_gradebook(gutils.clean_id(gradebook_id))
            gradebook.delete_gradebook_column(gutils.clean_id(column_id))

            return DeletedResponse()
        except (PermissionDenied) as ex:
            gutils.handle_exceptions(ex)
        except IllegalState as ex:
            modified_ex = type(ex)('Gradebook column is not empty.')
            gutils.handle_exceptions(modified_ex)

    def get(self, request, gradebook_id, column_id, format=None):
        try:
            gradebook = self.gm.get_gradebook(gutils.clean_id(gradebook_id))
            gradebook_column = gradebook.get_gradebook_column(gutils.clean_id(column_id))
            gradebook_column_map = gradebook_column.object_map

            gradebook_column_map.update({
                '_links': {
                    'self': gutils.build_safe_uri(request),
                    'entries': gutils.build_safe_uri(request) + 'entries/',
                    'summary': gutils.build_safe_uri(request) + 'summary/'
                }
            })

            return Response(gradebook_column_map)
        except (PermissionDenied, NotFound) as ex:
            gutils.handle_exceptions(ex)

    def put(self, request, gradebook_id, column_id, format=None):
        try:
            data = gutils.get_data_from_request(request)

            gutils.verify_at_least_one_key_present(data,
                                                   ['name', 'description', 'gradeSystemId'])

            gradebook = self.gm.get_gradebook(gutils.clean_id(gradebook_id))
            gradebook_column = gradebook.get_gradebook_column(gutils.clean_id(column_id))

            form = gradebook.get_gradebook_column_form_for_update(gradebook_column.ident)

            if 'name' in data:
                form.display_name = data['name']
            if 'description' in data:
                form.description = data['description']
            if 'gradeSystemId' in data:
                form.set_grade_system(gutils.clean_id(data['gradeSystemId']))

            gradebook.update_gradebook_column(form)

            gradebook_column = gradebook.get_gradebook_column(gradebook_column.ident)

            return UpdatedResponse(gradebook_column.object_map)
        except (PermissionDenied, InvalidArgument, KeyError) as ex:
            gutils.handle_exceptions(ex)
        except IllegalState as ex:
            modified_ex = type(ex)('Entries exist in this gradebook column. ' +
                                   'Cannot change the grade system.')
            gutils.handle_exceptions(modified_ex)


class GradebookColumnsList(DLKitSessionsManager):
    """
    Get or add column to a gradebook
    api/v2/grading/gradebooks/<gradebook_id>/columns/

    GET, POST
    GET to view current columns.
    POST to create a new column

    Note that for RESTful calls, you need to set the request header
    'content-type' to 'application/json'

    Example (note the use of double quotes!!):
       {"gradeSystemId" : "grading.GradeSystem%3A123%40MIT-ODL"}
    """

    def get(self, request, gradebook_id, format=None):
        try:
            gradebook = self.gm.get_gradebook(gutils.clean_id(gradebook_id))

            columns = gradebook.get_gradebook_columns()
            data = gutils.extract_items(request, columns)

            return Response(data)
        except (PermissionDenied, NotFound) as ex:
            gutils.handle_exceptions(ex)

    def post(self, request, gradebook_id, format=None):
        try:
            data = gutils.get_data_from_request(request)

            gutils.verify_keys_present(data, ['gradeSystemId'])

            gradebook = self.gm.get_gradebook(gutils.clean_id(gradebook_id))

            form = gradebook.get_gradebook_column_form_for_create([])

            if 'name' in data:
                form.display_name = data['name']

            if 'description' in data:
                form.description = data['description']

            form.set_grade_system(gutils.clean_id(data['gradeSystemId']))

            column = gradebook.create_gradebook_column(form)

            return CreatedResponse(column.object_map)
        except (PermissionDenied, InvalidArgument, KeyError) as ex:
            gutils.handle_exceptions(ex)


class GradebookColumnSummary(DLKitSessionsManager):
    """
    Get grade system details
    api/v2/grading/gradebooks/<gradebook_id>/columns/<column_id>/summary/

    GET

    Note that for RESTful calls, you need to set the request header
    'content-type' to 'application/json'
    """
    def get(self, request, gradebook_id, column_id, format=None):
        try:
            gradebook = self.gm.get_gradebook(gutils.clean_id(gradebook_id))
            if gradebook.get_grade_entries_for_gradebook_column(gutils.clean_id(column_id)).available() > 0:
                gradebook_column_summary = gradebook.get_gradebook_column_summary(gutils.clean_id(column_id))
                gradebook_column_summary_map = {
                    '_links': {
                        'self': gutils.build_safe_uri(request)
                    },
                    'mean': gradebook_column_summary.get_mean(),
                    'median': gradebook_column_summary.get_median(),
                    'mode': gradebook_column_summary.get_mode(),
                    'rootMeanSquared': gradebook_column_summary.get_rms(),
                    'standardDeviation': gradebook_column_summary.get_standard_deviation(),
                    'sum': gradebook_column_summary.get_sum()
                }
            else:
                gradebook_column_summary_map = {
                    '_links': {
                        'self': gutils.build_safe_uri(request)
                    },
                    'mean': 0.0,
                    'median': 0.0,
                    'mode': 0.0,
                    'rootMeanSquared': 0.0,
                    'standardDeviation': 0.0,
                    'sum': 0.0
                }

            return Response(gradebook_column_summary_map)
        except (PermissionDenied, NotFound) as ex:
            gutils.handle_exceptions(ex)


class GradebookGradeSystemsList(DLKitSessionsManager):
    """
    Get or add gradesystems to a gradebook
    api/v2/grading/gradebooks/<gradebook_id>/gradesystems/

    GET, POST
    GET to view current gradesystems.
    POST to create a new gradesystem

    Note that for RESTful calls, you need to set the request header
    'content-type' to 'application/json'

    Example (note the use of double quotes!!):
       {"name" : "Letters", "description": "Letter grades A - F"}
    """

    def get(self, request, gradebook_id, format=None):
        try:
            gradebook = self.gm.get_gradebook(gutils.clean_id(gradebook_id))

            grade_systems = gradebook.get_grade_systems()
            data = gutils.extract_items(request, grade_systems)

            return Response(data)
        except (PermissionDenied, NotFound) as ex:
            gutils.handle_exceptions(ex)

    def post(self, request, gradebook_id, format=None):
        try:
            data = gutils.get_data_from_request(request)

            gutils.verify_at_least_one_key_present(data,
                                                   ['name', 'description'])

            gradebook = self.gm.get_gradebook(gutils.clean_id(gradebook_id))

            form = gradebook.get_grade_system_form_for_create([])

            if 'name' in data:
                form.display_name = data['name']

            if 'description' in data:
                form.description = data['description']

            check_scores = True

            if 'basedOnGrades' in data:
                form.set_based_on_grades(bool(data['basedOnGrades']))
                if data['basedOnGrades']:
                    check_scores = False

            if check_scores:
                grutils.check_numeric_score_inputs(data)

                form.set_highest_numeric_score(float(data['highestScore']))
                form.set_lowest_numeric_score(float(data['lowestScore']))
                form.set_numeric_score_increment(float(data['scoreIncrement']))

            grade_system = gradebook.create_grade_system(form)

            if not check_scores:
                grutils.check_grade_inputs(data)
                grutils.add_grades_to_grade_system(gradebook,
                                                   grade_system,
                                                   data)

            grade_system = gradebook.get_grade_system(grade_system.ident)

            return CreatedResponse(grade_system.object_map)
        except (PermissionDenied, InvalidArgument, KeyError) as ex:
            try:
                gradebook.delete_grade_system(grade_system.ident)
            except NameError:
                pass
            gutils.handle_exceptions(ex)


class GradebooksList(DLKitSessionsManager):
    """
    List all available gradebooks.
    api/v2/grading/gradebooks/

    POST allows you to create a new gradebook, requires two parameters:
      * name
      * description

    Alternatively, if you provide an assessment bank ID,
    the gradebook will be orchestrated to have a matching internal identifier.
    The name and description will be set for you, but can optionally be set if
    provided.
      * bankId
      * name (optional)
      * description (optional)

    Note that for RESTful calls, you need to set the request header
    'content-type' to 'application/json'

    Example (note the use of double quotes!!):
      {"name" : "a new gradebook",
       "description" : "this is a test"}

       OR
       {"bankId": "assessment.Bank%3A5547c37cea061a6d3f0ffe71%40cs-macbook-pro"}
    """

    def get(self, request, format=None):
        """
        List all available gradebooks
        """
        try:
            gradebooks = self.gm.gradebooks
            gradebooks = gutils.extract_items(request, gradebooks)
            return Response(gradebooks)
        except PermissionDenied as ex:
            gutils.handle_exceptions(ex)

    def post(self, request, format=None):
        """
        Create a new bin, if authorized

        """
        try:
            data = gutils.get_data_from_request(request)

            if 'bankId' not in data:
                gutils.verify_keys_present(data, ['name', 'description'])
                form = self.gm.get_gradebook_form_for_create([])
                finalize_method = self.gm.create_gradebook
            else:
                gradebook = self.gm.get_gradebook(Id(data['bankId']))
                form = self.gm.get_gradebook_form_for_update(gradebook.ident)
                finalize_method = self.gm.update_gradebook

            if 'name' in data:
                form.display_name = data['name']
            if 'description' in data:
                form.description = data['description']

            new_gradebook = gutils.convert_dl_object(finalize_method(form))

            return CreatedResponse(new_gradebook)
        except (PermissionDenied, InvalidArgument, NotFound, KeyError) as ex:
            gutils.handle_exceptions(ex)


class GradeEntriesList(DLKitSessionsManager):
    """
    Get or add grade entry to a gradebook column
    api/v2/grading/gradebooks/<gradebook_id>/columns/<column_id>/entries

    OR view all entries in a gradebook
    api/v2/grading/gradebooks/<gradebook_id>/entries

    GET, POST
    GET to view current grade entries (in whole gradebook or single gradebook column).
    POST to create a new grade entry (only to a specific gradebook)

    Note that for RESTful calls, you need to set the request header
    'content-type' to 'application/json'

    Example (note the use of double quotes!!):
       {"grade" : "grading.Grade%3A123%40MIT-ODL"}
    """

    def get(self, request, gradebook_id, column_id=None, format=None):
        try:
            gradebook = self.gm.get_gradebook(gutils.clean_id(gradebook_id))
            if column_id is None:
                entries = gradebook.get_grade_entries()
            else:
                entries = gradebook.get_grade_entries_for_gradebook_column(gutils.clean_id(column_id))

            data = gutils.extract_items(request, entries)

            return Response(data)
        except (PermissionDenied, NotFound) as ex:
            gutils.handle_exceptions(ex)

    def post(self, request, gradebook_id, column_id=None, format=None):
        try:
            data = gutils.get_data_from_request(request)

            gutils.verify_at_least_one_key_present(data,
                                                   ['grade', 'score', 'ignoredForCalculations'])
            gutils.verify_keys_present(data, ['resourceId'])

            if column_id is None:
                gutils.verify_keys_present(data, ['columnId'])
                column_id = data['columnId']

            gradebook = self.gm.get_gradebook(gutils.clean_id(gradebook_id))
            column = gradebook.get_gradebook_column(gutils.clean_id(column_id))

            grutils.validate_score_and_grades_against_system(column.get_grade_system(),
                                                             data)

            form = gradebook.get_grade_entry_form_for_create(column.ident,
                                                             gutils.clean_id(data['resourceId']),
                                                             [])

            if 'name' in data:
                form.display_name = data['name']

            if 'description' in data:
                form.description = data['description']

            if 'ignoredForCalculations' in data:
                form.set_ignored_for_calculations(bool(data['ignoredForCalculations']))

            if 'grade' in data:
                form.set_grade(gutils.clean_id(data['grade']))

            if 'score' in data:
                form.set_score(float(data['score']))

            entry = gradebook.create_grade_entry(form)

            return CreatedResponse(entry.object_map)
        except (PermissionDenied, InvalidArgument, IllegalState, KeyError) as ex:
            gutils.handle_exceptions(ex)


class GradeEntryDetails(DLKitSessionsManager):
    """
    Get grade entry details
    api/v2/grading/gradebooks/<gradebook_id>/entries/<entry_id>/

    GET, PUT, DELETE
    PUT to modify an existing grade entry (name, score / grade, etc.).
        Include only the changed parameters.
    DELETE to remove the grade entry.

    Note that for RESTful calls, you need to set the request header
    'content-type' to 'application/json'

    Example (note the use of double quotes!!):
       {"score" : 98.2}
    """

    def delete(self, request, gradebook_id, entry_id, format=None):
        try:
            gradebook = self.gm.get_gradebook(gutils.clean_id(gradebook_id))
            gradebook.delete_grade_entry(gutils.clean_id(entry_id))

            return DeletedResponse()
        except (PermissionDenied, IllegalState) as ex:
            gutils.handle_exceptions(ex)

    def get(self, request, gradebook_id, entry_id, format=None):
        try:
            gradebook = self.gm.get_gradebook(gutils.clean_id(gradebook_id))
            entry = gradebook.get_grade_entry(gutils.clean_id(entry_id))
            entry_map = entry.object_map

            entry_map.update({
                '_links': {
                    'self': gutils.build_safe_uri(request),
                }
            })

            return Response(entry_map)
        except (PermissionDenied, NotFound) as ex:
            gutils.handle_exceptions(ex)

    def put(self, request, gradebook_id, entry_id, format=None):
        try:
            data = gutils.get_data_from_request(request)

            gutils.verify_at_least_one_key_present(data,
                                                   ['name', 'description', 'grade',
                                                    'score', 'ignoredForCalculations'])

            gradebook = self.gm.get_gradebook(gutils.clean_id(gradebook_id))
            entry = gradebook.get_grade_entry(gutils.clean_id(entry_id))
            grade_system = entry.get_gradebook_column().get_grade_system()

            grutils.validate_score_and_grades_against_system(grade_system, data)

            form = gradebook.get_grade_entry_form_for_update(entry.ident)

            if 'name' in data:
                form.display_name = data['name']
            if 'description' in data:
                form.description = data['description']
            if 'grade' in data:
                form.set_grade(gutils.clean_id(data['grade']))

            if 'score' in data:
                form.set_score(float(data['score']))

            if 'ignoredForCalculations' in data:
                form.set_ignored_for_calculations(bool(data['ignoredForCalculations']))

            gradebook.update_grade_entry(form)

            entry = gradebook.get_grade_entry(entry.ident)

            return UpdatedResponse(entry.object_map)
        except (PermissionDenied, InvalidArgument, KeyError) as ex:
            gutils.handle_exceptions(ex)


class GradingService(DLKitSessionsManager):
    """
    List all available grading services.
    api/v2/grading/
    """

    def get(self, request, format=None):
        """
        List all available grading services.
        """
        data = {}
        data = gutils.add_links(request,
                                data,
                                {
                                    'gradebooks': 'gradebooks/',
                                    'documentation': 'docs/'
                                })
        return Response(data)

