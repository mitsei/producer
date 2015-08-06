from bson.errors import InvalidId

from dlkit_django.errors import PermissionDenied, InvalidArgument, IllegalState, NotFound
from dlkit_django.primordium import Id

from producer.views import ProducerAPIViews

from rest_framework.response import Response

from utilities import general as gutils
from utilities import grading as grutils


class GradebookDetails(ProducerAPIViews):
    """
    Shows details for a specific gradebook.
    api/v1/grading/gradebooks/<gradebook_id>/

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
            return gutils.DeletedResponse()
        except (PermissionDenied, NotFound) as ex:
            gutils.handle_exceptions(ex)
        except IllegalState as ex:
            modified_ex = type(ex)('Gradebook is not empty.')
            gutils.handle_exceptions(modified_ex)

    def get(self, request, gradebook_id, format=None):
        try:
            gradebook = self.gm.get_gradebook(gutils.clean_id(gradebook_id))
            gradebook = gutils.convert_dl_object(gradebook)
            gutils.update_links(request, gradebook)
            return Response(gradebook)
        except (PermissionDenied, InvalidId, NotFound) as ex:
            gutils.handle_exceptions(ex)

    def put(self, request, gradebook_id, format=None):
        try:
            form = self.gm.get_gradebook_form_for_update(gutils.clean_id(gradebook_id))

            gutils.verify_at_least_one_key_present(self.data,
                                                   ['displayName', 'description'])

            form = gutils.set_form_basics(form, self.data)

            updated_gradebook = self.gm.update_gradebook(form)
            updated_gradebook = gutils.convert_dl_object(updated_gradebook)

            return gutils.UpdatedResponse(updated_gradebook)
        except (PermissionDenied, KeyError, InvalidArgument, NotFound) as ex:
            gutils.handle_exceptions(ex)


class GradeSystemDetails(ProducerAPIViews):
    """
    Get grade system details
    api/v1/grading/gradesystems/<gradesystem_id>/

    GET, PUT, DELETE
    PUT to modify an existing grade system (name or settings). Include only the changed parameters.
    DELETE to remove the grade system.

    Note that for RESTful calls, you need to set the request header
    'content-type' to 'application/json'

    Example (note the use of double quotes!!):
       {"name" : "an updated item"}
    """

    def delete(self, request, gradesystem_id, format=None):
        try:
            gradebook = grutils.get_object_gradebook(self.gm,
                                                     gradesystem_id,
                                                     'grade_system')
            gradebook.delete_grade_system(gutils.clean_id(gradesystem_id))

            return gutils.DeletedResponse()
        except (PermissionDenied, InvalidArgument) as ex:
            gutils.handle_exceptions(ex)
        except IllegalState as ex:
            modified_ex = type(ex)('Grade system is being used.')
            gutils.handle_exceptions(modified_ex)

    def get(self, request, gradesystem_id, format=None):
        try:
            gradebook = grutils.get_object_gradebook(self.gm,
                                                     gradesystem_id,
                                                     'grade_system')
            grade_system = gradebook.get_grade_system(gutils.clean_id(gradesystem_id))
            grade_system_map = grade_system.object_map

            gutils.update_links(request, grade_system_map)

            return Response(grade_system_map)
        except (PermissionDenied, NotFound) as ex:
            gutils.handle_exceptions(ex)

    def put(self, request, gradesystem_id, format=None):
        try:
            gutils.verify_at_least_one_key_present(self.data,
                                                   ['displayName', 'description', 'basedOnGrades',
                                                    'grades', 'highestScore', 'lowestScore',
                                                    'scoreIncrement'])

            gradebook = grutils.get_object_gradebook(self.gm,
                                                     gradesystem_id,
                                                     'grade_system')
            grade_system = gradebook.get_grade_system(gutils.clean_id(gradesystem_id))

            if 'basedOnGrades' in self.data:
                # do this first, so methods below work
                form = gradebook.get_grade_system_form_for_update(grade_system.ident)
                form.set_based_on_grades(bool(self.data['basedOnGrades']))

                if self.data['basedOnGrades']:
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
                    'grades' in self.data):
                # user wants to update the grades
                # here, wipe out all previous grades and over-write
                grutils.check_grade_inputs(self.data)
                if len(self.data['grades']) > 0:
                    for grade in grade_system.get_grades():
                        gradebook.delete_grade(grade.ident)
                    grutils.add_grades_to_grade_system(gradebook,
                                                       grade_system,
                                                       self.data)

            score_inputs = ['highestScore', 'lowestScore', 'scoreIncrement']
            if (not grade_system.is_based_on_grades() and
                    any(i in self.data for i in score_inputs)):
                form = gradebook.get_grade_system_form_for_update(grade_system.ident)

                if 'highestScore' in self.data:
                    form.set_highest_numeric_score(float(self.data['highestScore']))

                if 'lowestScore' in self.data:
                    form.set_lowest_numeric_score(float(self.data['lowestScore']))

                if 'scoreIncrement' in self.data:
                    form.set_numeric_score_increment(float(self.data['scoreIncrement']))

                gradebook.update_grade_system(form)

            if 'name' in self.data or 'description' in self.data:
                form = gradebook.get_grade_system_form_for_update(grade_system.ident)

                form = gutils.set_form_basics(form, self.data)

                gradebook.update_grade_system(form)

            grade_system = gradebook.get_grade_system(grade_system.ident)

            return gutils.UpdatedResponse(grade_system.object_map)
        except (PermissionDenied, InvalidArgument, KeyError) as ex:
            gutils.handle_exceptions(ex)


class GradebookColumnDetails(ProducerAPIViews):
    """
    Get grade system details
    api/v1/grading/columns/<column_id>/

    GET, PUT, DELETE
    PUT to modify an existing gradebook column (name or gradeSystemId).
        Include only the changed parameters.
    DELETE to remove the gradebook column.

    Note that for RESTful calls, you need to set the request header
    'content-type' to 'application/json'

    Example (note the use of double quotes!!):
       {"name" : "an updated item"}
    """

    def delete(self, request, column_id, format=None):
        try:
            gradebook = grutils.get_object_gradebook(self.gm,
                                                     column_id,
                                                     'gradebook_column')
            gradebook.delete_gradebook_column(gutils.clean_id(column_id))

            return gutils.DeletedResponse()
        except (PermissionDenied) as ex:
            gutils.handle_exceptions(ex)
        except IllegalState as ex:
            modified_ex = type(ex)('Gradebook column is not empty.')
            gutils.handle_exceptions(modified_ex)

    def get(self, request, column_id, format=None):
        try:
            gradebook = grutils.get_object_gradebook(self.gm,
                                                     column_id,
                                                     'gradebook_column')
            gradebook_column = gradebook.get_gradebook_column(gutils.clean_id(column_id))
            gradebook_column_map = gradebook_column.object_map

            gutils.update_links(request, gradebook_column_map)

            return Response(gradebook_column_map)
        except (PermissionDenied, NotFound) as ex:
            gutils.handle_exceptions(ex)

    def put(self, request, column_id, format=None):
        try:
            gutils.verify_at_least_one_key_present(self.data,
                                                   ['displayName', 'description', 'gradeSystemId'])

            gradebook = grutils.get_object_gradebook(self.gm,
                                                     column_id,
                                                     'gradebook_column')
            gradebook_column = gradebook.get_gradebook_column(gutils.clean_id(column_id))

            form = gradebook.get_gradebook_column_form_for_update(gradebook_column.ident)

            form = gutils.set_form_basics(form, self.data)
            if 'gradeSystemId' in self.data:
                form.set_grade_system(gutils.clean_id(self.data['gradeSystemId']))

            gradebook.update_gradebook_column(form)

            gradebook_column = gradebook.get_gradebook_column(gradebook_column.ident)

            return gutils.UpdatedResponse(gradebook_column.object_map)
        except (PermissionDenied, InvalidArgument, KeyError) as ex:
            gutils.handle_exceptions(ex)
        except IllegalState as ex:
            modified_ex = type(ex)('Entries exist in this gradebook column. ' +
                                   'Cannot change the grade system.')
            gutils.handle_exceptions(modified_ex)


class GradebookColumnsList(ProducerAPIViews):
    """
    Get or add column to a gradebook
    api/v1/grading/columns/

    GET, POST
    GET to view current columns.
    POST to create a new column

    Note that for RESTful calls, you need to set the request header
    'content-type' to 'application/json'

    Example (note the use of double quotes!!):
       {"gradeSystemId" : "grading.GradeSystem%3A123%40MIT-ODL"}
    """

    def get(self, request, gradebook_id=None, format=None):
        try:
            if gradebook_id is None:
                column_lookup_session = grutils.get_session(self.gm, 'gradebook_column', 'lookup')
                column_query_session = grutils.get_session(self.gm, 'gradebook_column', 'query')

                column_lookup_session.use_federated_gradebook_view()
                column_query_session.use_federated_gradebook_view()
            else:
                column_query_session = column_lookup_session = self.gm.get_gradebook(
                    gutils.clean_id(gradebook_id))

            if len(self.data) == 0 and gradebook_id is None:
                columns = column_lookup_session.get_gradebook_columns()
            else:
                allowable_query_terms = ['displayName', 'description']
                if any(term in self.data for term in allowable_query_terms):
                    querier = column_query_session.get_gradebook_column_query()
                    querier = gutils.config_osid_object_querier(querier, self.data)
                    columns = column_query_session.get_gradebook_columns_by_query(querier)
                else:
                    columns = column_lookup_session.get_grade_entries()

            data = gutils.extract_items(request, columns)

            return Response(data)
        except (PermissionDenied, NotFound) as ex:
            gutils.handle_exceptions(ex)

    def post(self, request, gradebook_id=None, format=None):
        try:
            if gradebook_id is None:
                gutils.verify_keys_present(self.data, ['gradebookId'])
                gradebook_id = self.data['gradebookId']

            gutils.verify_keys_present(self.data, ['gradeSystemId'])

            gradebook = self.gm.get_gradebook(gutils.clean_id(gradebook_id))

            form = gradebook.get_gradebook_column_form_for_create([])

            form = gutils.set_form_basics(form, self.data)

            form.set_grade_system(gutils.clean_id(self.data['gradeSystemId']))

            column = gradebook.create_gradebook_column(form)

            return gutils.CreatedResponse(column.object_map)
        except (PermissionDenied, InvalidArgument, KeyError) as ex:
            gutils.handle_exceptions(ex)


class GradebookColumnSummary(ProducerAPIViews):
    """
    Get grade system details
    api/v1/grading/columns/<column_id>/summary/

    GET

    Note that for RESTful calls, you need to set the request header
    'content-type' to 'application/json'
    """
    def get(self, request, column_id, format=None):
        try:
            gradebook = grutils.get_object_gradebook(self.gm,
                                                     column_id,
                                                     'gradebook_column')
            if gradebook.get_grade_entries_for_gradebook_column(gutils.clean_id(column_id)).available() > 0:
                gradebook_column_summary = gradebook.get_gradebook_column_summary(
                    gutils.clean_id(column_id))
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


class GradeSystemsList(ProducerAPIViews):
    """
    Get or add gradesystems to a gradebook
    api/v1/grading/gradesystems/

    GET, POST
    GET to view current gradesystems.
    POST to create a new gradesystem

    Note that for RESTful calls, you need to set the request header
    'content-type' to 'application/json'

    Example (note the use of double quotes!!):
       {"name" : "Letters", "description": "Letter grades A - F"}
    """

    def get(self, request, gradebook_id=None, format=None):
        try:
            if gradebook_id is None:
                grade_system_lookup_session = grutils.get_session(self.gm,
                                                                  'grade_system',
                                                                  'lookup')
                grade_system_query_session = grutils.get_session(self.gm,
                                                                 'grade_system',
                                                                 'query')

                grade_system_lookup_session.use_federated_gradebook_view()
                grade_system_query_session.use_federated_gradebook_view()
            else:
                grade_system_query_session = grade_system_lookup_session = self.gm.get_gradebook(
                    gutils.clean_id(gradebook_id))

            if len(self.data) == 0:
                grade_systems = grade_system_lookup_session.get_grade_systems()
            else:
                allowable_query_terms = ['displayName', 'description']
                if any(term in self.data for term in allowable_query_terms):
                    querier = grade_system_query_session.get_grade_system_query()
                    querier = gutils.config_osid_object_querier(querier, self.data)
                    grade_systems = grade_system_query_session.get_grade_systems_by_query(querier)
                else:
                    grade_systems = grade_system_query_session.get_grade_systems()

            data = gutils.extract_items(request, grade_systems)

            return Response(data)
        except (PermissionDenied, NotFound) as ex:
            gutils.handle_exceptions(ex)

    def post(self, request, gradebook_id=None, format=None):
        try:
            if gradebook_id is None:
                gutils.verify_keys_present(self.data, ['gradebookId'])
                gradebook_id = self.data['gradebookId']

            gutils.verify_at_least_one_key_present(self.data,
                                                   ['displayName', 'description'])

            gradebook = self.gm.get_gradebook(gutils.clean_id(gradebook_id))

            form = gradebook.get_grade_system_form_for_create([])

            form = gutils.set_form_basics(form, self.data)

            check_scores = True

            if 'basedOnGrades' in self.data:
                form.set_based_on_grades(bool(self.data['basedOnGrades']))
                if self.data['basedOnGrades']:
                    check_scores = False

            if check_scores:
                grutils.check_numeric_score_inputs(self.data)

                form.set_highest_numeric_score(float(self.data['highestScore']))
                form.set_lowest_numeric_score(float(self.data['lowestScore']))
                form.set_numeric_score_increment(float(self.data['scoreIncrement']))

            grade_system = gradebook.create_grade_system(form)

            if not check_scores:
                grutils.check_grade_inputs(self.data)
                grutils.add_grades_to_grade_system(gradebook,
                                                   grade_system,
                                                   self.data)

            grade_system = gradebook.get_grade_system(grade_system.ident)

            return gutils.CreatedResponse(grade_system.object_map)
        except (PermissionDenied, InvalidArgument, KeyError) as ex:
            try:
                gradebook.delete_grade_system(grade_system.ident)
            except NameError:
                pass
            gutils.handle_exceptions(ex)


class GradebooksList(ProducerAPIViews):
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
            if 'bankId' not in self.data:
                gutils.verify_keys_present(self.data, ['displayName', 'description'])
                form = self.gm.get_gradebook_form_for_create([])
                finalize_method = self.gm.create_gradebook
            else:
                gradebook = self.gm.get_gradebook(Id(self.data['bankId']))
                form = self.gm.get_gradebook_form_for_update(gradebook.ident)
                finalize_method = self.gm.update_gradebook

            form = gutils.set_form_basics(form, self.data)

            new_gradebook = gutils.convert_dl_object(finalize_method(form))

            return gutils.CreatedResponse(new_gradebook)
        except (PermissionDenied, InvalidArgument, NotFound, KeyError) as ex:
            gutils.handle_exceptions(ex)


class GradeEntriesList(ProducerAPIViews):
    """
    Get or add grade entry to a gradebook column
    api/v1/grading/entries

    GET, POST
    GET to view current grade entries (in whole gradebook or single gradebook column).
    POST to create a new grade entry (only to a specific gradebook)

    Note that for RESTful calls, you need to set the request header
    'content-type' to 'application/json'

    Example (note the use of double quotes!!):
       {"grade" : "grading.Grade%3A123%40MIT-ODL"}
    """

    def get(self, request, column_id=None, format=None):
        try:
            if column_id is None:
                entry_lookup_session = grutils.get_session(self.gm, 'grade_entry', 'lookup')
                entry_query_session = grutils.get_session(self.gm, 'grade_entry', 'query')

                entry_lookup_session.use_federated_gradebook_view()
                entry_query_session.use_federated_gradebook_view()
            else:
                entry_query_session = entry_lookup_session = grutils.get_object_gradebook(self.gm,
                                                                                          column_id,
                                                                                          'gradebook_column')

            if len(self.data) == 0 and column_id is None:
                entries = entry_lookup_session.get_grade_entries()
            elif column_id is not None:
                if len(self.data) == 0:
                    entries = entry_lookup_session.get_grade_entries_for_gradebook_column(
                        gutils.clean_id(column_id))
                else:
                    allowable_query_terms = ['displayName', 'description']
                    if any(term in self.data for term in allowable_query_terms):
                        querier = entry_query_session.get_grade_entry_query()
                        querier = gutils.config_osid_object_querier(querier, self.data)
                        querier.match_gradebook_column_id(gutils.clean_id(column_id))
                        entries = entry_query_session.get_grade_entries_by_query(querier)
                    else:
                        entries = entry_lookup_session.get_grade_entries_for_gradebook_column(
                            gutils.clean_id(column_id))
            else:
                allowable_query_terms = ['displayName', 'description']
                if any(term in self.data for term in allowable_query_terms):
                    querier = entry_query_session.get_grade_entry_query()
                    querier = gutils.config_osid_object_querier(querier, self.data)
                    entries = entry_query_session.get_grade_entries_by_query(querier)
                else:
                    entries = entry_lookup_session.get_grade_entries()

            data = gutils.extract_items(request, entries)

            return Response(data)
        except (PermissionDenied, NotFound) as ex:
            gutils.handle_exceptions(ex)

    def post(self, request, column_id=None, format=None):
        try:
            if column_id is None:
                gutils.verify_keys_present(self.data, ['gradebookColumnId'])
                column_id = self.data['gradebookColumnId']

            gutils.verify_at_least_one_key_present(self.data,
                                                   ['grade', 'score', 'ignoredForCalculations'])
            gutils.verify_keys_present(self.data, ['resourceId'])

            gradebook = grutils.get_object_gradebook(self.gm,
                                                     column_id,
                                                     'gradebook_column')
            column = gradebook.get_gradebook_column(gutils.clean_id(column_id))

            grutils.validate_score_and_grades_against_system(column.get_grade_system(),
                                                             self.data)

            form = gradebook.get_grade_entry_form_for_create(column.ident,
                                                             gutils.clean_id(self.data['resourceId']),
                                                             [])

            form = gutils.set_form_basics(form, self.data)

            if 'ignoredForCalculations' in self.data:
                form.set_ignored_for_calculations(bool(self.data['ignoredForCalculations']))

            if 'grade' in self.data:
                form.set_grade(gutils.clean_id(self.data['grade']))

            if 'score' in self.data:
                form.set_score(float(self.data['score']))

            entry = gradebook.create_grade_entry(form)

            return gutils.CreatedResponse(entry.object_map)
        except (PermissionDenied, InvalidArgument, IllegalState, KeyError) as ex:
            gutils.handle_exceptions(ex)


class GradeEntryDetails(ProducerAPIViews):
    """
    Get grade entry details
    api/v1/grading/entries/<entry_id>/

    GET, PUT, DELETE
    PUT to modify an existing grade entry (name, score / grade, etc.).
        Include only the changed parameters.
    DELETE to remove the grade entry.

    Note that for RESTful calls, you need to set the request header
    'content-type' to 'application/json'

    Example (note the use of double quotes!!):
       {"score" : 98.2}
    """

    def delete(self, request, entry_id, format=None):
        try:
            gradebook = grutils.get_object_gradebook(self.gm,
                                                     entry_id,
                                                     'grade_entry')
            gradebook.delete_grade_entry(gutils.clean_id(entry_id))

            return gutils.DeletedResponse()
        except (PermissionDenied, IllegalState) as ex:
            gutils.handle_exceptions(ex)

    def get(self, request, entry_id, format=None):
        try:
            gradebook = grutils.get_object_gradebook(self.gm,
                                                     entry_id,
                                                     'grade_entry')
            entry = gradebook.get_grade_entry(gutils.clean_id(entry_id))
            entry_map = entry.object_map

            gutils.update_links(request, entry_map)

            return Response(entry_map)
        except (PermissionDenied, NotFound) as ex:
            gutils.handle_exceptions(ex)

    def put(self, request, entry_id, format=None):
        try:
            gutils.verify_at_least_one_key_present(self.data,
                                                   ['displayName', 'description', 'grade',
                                                    'score', 'ignoredForCalculations'])

            gradebook = grutils.get_object_gradebook(self.gm,
                                                     entry_id,
                                                     'grade_entry')
            entry = gradebook.get_grade_entry(gutils.clean_id(entry_id))
            grade_system = entry.get_gradebook_column().get_grade_system()

            grutils.validate_score_and_grades_against_system(grade_system, self.data)

            form = gradebook.get_grade_entry_form_for_update(entry.ident)

            form = gutils.set_form_basics(form, self.data)

            if 'grade' in self.data:
                form.set_grade(gutils.clean_id(self.data['grade']))

            if 'score' in self.data:
                form.set_score(float(self.data['score']))

            if 'ignoredForCalculations' in self.data:
                form.set_ignored_for_calculations(bool(self.data['ignoredForCalculations']))

            gradebook.update_grade_entry(form)

            entry = gradebook.get_grade_entry(entry.ident)

            return gutils.UpdatedResponse(entry.object_map)
        except (PermissionDenied, InvalidArgument, KeyError) as ex:
            gutils.handle_exceptions(ex)
