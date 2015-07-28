from django.conf.urls import patterns, url
from rest_framework.urlpatterns import format_suffix_patterns
from assessmentsv2 import views

urlpatterns = patterns('',
    url(r'^$',
        views.AssessmentService.as_view()),
    url(r'^assessmentsoffered/(?P<offering_id>[-.:@%\d\w]+)/?$',
        views.AssessmentOfferedDetails.as_view()),
    url(r'^banks/?$',
        views.AssessmentBanksList.as_view()),
    url(r'^banks/(?P<bank_id>[-.:@%\d\w]+)/?$',
        views.AssessmentBanksDetail.as_view()),
    url(r'^banks/(?P<bank_id>[-.:@%\d\w]+)/assessments/?$',
        views.AssessmentsList.as_view()),
    url(r'^banks/(?P<bank_id>[-.:@%\d\w]+)/authorizations/?$',
        views.BankAuthorizations.as_view()),
    url(r'^banks/(?P<bank_id>[-.:@%\d\w]+)/items/?$',
        views.ItemsList.as_view()),
    url(r'^banks/(?P<bank_id>[-.:@%\d\w]+)/items/(?P<sub_id>[-.:@%\d\w]+)/?$',
        views.ItemDetails.as_view()),
    url(r'^banks/(?P<bank_id>[-.:@%\d\w]+)/items/(?P<sub_id>[-.:@%\d\w]+)/question/?$',
        views.ItemQuestion.as_view()),
    # url(r'^assessment/banks/(?P<bank_id>[-.:@%\d\w]+)/items/(?P<sub_id>[-.:@%\d\w]+)/submit/$',
    #     views.ItemSubmissionCheck.as_view()),
    url(r'^banks/(?P<bank_id>[-.:@%\d\w]+)/items/(?P<sub_id>[-.:@%\d\w]+)/files/?$',
        views.ItemFilesList.as_view()),
    # url(r'^assessment/banks/(?P<bank_id>[-.:@%\d\w]+)/items/(?P<sub_id>[-.:@%\d\w]+)/files/(?P<file_key>[-.:@%\d\w]+)/$',  # Disable this for AWS -- we aren't hosting locally anyways, and more security via CloudFront
    #     views.ItemFile.as_view()),
    url(r'^banks/(?P<bank_id>[-.:@%\d\w]+)/items/(?P<sub_id>[-.:@%\d\w]+)/answers/?$',
        views.ItemAnswers.as_view()),
    url(r'^banks/(?P<bank_id>[-.:@%\d\w]+)/items/(?P<sub_id>[-.:@%\d\w]+)/answers/(?P<ans_id>[-.:@%\d\w]+)/?$',
        views.ItemAnswerDetails.as_view()),
    url(r'^banks/(?P<bank_id>[-.:@%\d\w]+)/items/(?P<sub_id>[-.:@%\d\w]+)/(?P<output_format>[\w]+)/?$',
        views.ItemTextAsFormat.as_view()),
    url(r'^banks/(?P<bank_id>[-.:@%\d\w]+)/assessments/(?P<sub_id>[-.:@%\d\w]+)/?$',
        views.AssessmentDetails.as_view()),
    url(r'^banks/(?P<bank_id>[-.:@%\d\w]+)/assessments/(?P<sub_id>[-.:@%\d\w]+)/items/?$', # do not link this to canonical /items/ because need to DELETE items from assessments without DELETing them from the repository
        views.AssessmentItemsList.as_view()),
    url(r'^banks/(?P<bank_id>[-.:@%\d\w]+)/assessments/(?P<sub_id>[-.:@%\d\w]+)/items/(?P<item_id>[-.:@%\d\w]+)/?$', # don't try to shorten this!
        views.AssessmentItemDetails.as_view()),
    url(r'^banks/(?P<bank_id>[-.:@%\d\w]+)/assessments/(?P<sub_id>[-.:@%\d\w]+)/assessmentsoffered/?$',
        views.AssessmentsOffered.as_view()),
    url(r'^banks/(?P<bank_id>[-.:@%\d\w]+)/assessmentsoffered/(?P<offering_id>[-.:@%\d\w]+)/?$',
        views.AssessmentOfferedDetails.as_view()),
    url(r'^banks/(?P<bank_id>[-.:@%\d\w]+)/assessmentsoffered/(?P<sub_id>[-.:@%\d\w]+)/assessmentstaken/?$',
        views.AssessmentsTaken.as_view()),
    url(r'^banks/(?P<bank_id>[-.:@%\d\w]+)/assessments/(?P<sub_id>[-.:@%\d\w]+)/assessmentstaken/?$', #takens POST builds off of offerings (above), not assessments. takens GET can be from /assessments/, /offerings/
        views.AssessmentsTaken.as_view()),
    url(r'^banks/(?P<bank_id>[-.:@%\d\w]+)/assessmentstaken/(?P<taken_id>[-.:@%\d\w]+)/?$',
        views.AssessmentTakenDetails.as_view()),
    url(r'^banks/(?P<bank_id>[-.:@%\d\w]+)/assessmentstaken/(?P<taken_id>[-.:@%\d\w]+)/take/?$',
        views.TakeAssessment.as_view()),
    url(r'^banks/(?P<bank_id>[-.:@%\d\w]+)/assessmentstaken/(?P<taken_id>[-.:@%\d\w]+)/files/?$',
        views.TakeAssessmentFiles.as_view()),
    url(r'^banks/(?P<bank_id>[-.:@%\d\w]+)/assessmentstaken/(?P<taken_id>[-.:@%\d\w]+)/finish/?$',
        views.FinishAssessmentTaken.as_view()),
    url(r'^banks/(?P<bank_id>[-.:@%\d\w]+)/assessmentstaken/(?P<taken_id>[-.:@%\d\w]+)/submit/?$',
        views.SubmitAssessment.as_view()),
    url(r'^banks/(?P<bank_id>[-.:@%\d\w]+)/assessmentstaken/(?P<taken_id>[-.:@%\d\w]+)/questions/?$',
        views.AssessmentTakenQuestions.as_view()),
    url(r'^banks/(?P<bank_id>[-.:@%\d\w]+)/assessmentstaken/(?P<taken_id>[-.:@%\d\w]+)/questions/(?P<question_id>[-.:@%\d\w]+)/?$',
        views.AssessmentTakenQuestionDetails.as_view()),
    url(r'^banks/(?P<bank_id>[-.:@%\d\w]+)/assessmentstaken/(?P<taken_id>[-.:@%\d\w]+)/questions/(?P<question_id>[-.:@%\d\w]+)/comments/?$',
        views.AssessmentTakenQuestionComments.as_view()),
    url(r'^banks/(?P<bank_id>[-.:@%\d\w]+)/assessmentstaken/(?P<taken_id>[-.:@%\d\w]+)/questions/(?P<question_id>[-.:@%\d\w]+)/files/?$',
        views.AssessmentTakenQuestionFiles.as_view()),
    url(r'^banks/(?P<bank_id>[-.:@%\d\w]+)/assessmentstaken/(?P<taken_id>[-.:@%\d\w]+)/questions/(?P<question_id>[-.:@%\d\w]+)/responses/?$',
        views.AssessmentTakenQuestionResponses.as_view()),
    url(r'^banks/(?P<bank_id>[-.:@%\d\w]+)/assessmentstaken/(?P<taken_id>[-.:@%\d\w]+)/questions/(?P<question_id>[-.:@%\d\w]+)/solution/?$',
        views.AssessmentTakenQuestionSolution.as_view()),
    url(r'^banks/(?P<bank_id>[-.:@%\d\w]+)/assessmentstaken/(?P<taken_id>[-.:@%\d\w]+)/questions/(?P<question_id>[-.:@%\d\w]+)/status/?$',
        views.AssessmentTakenQuestionStatus.as_view()),
    url(r'^banks/(?P<bank_id>[-.:@%\d\w]+)/assessmentstaken/(?P<taken_id>[-.:@%\d\w]+)/questions/(?P<question_id>[-.:@%\d\w]+)/submit/?$',
        views.AssessmentTakenQuestionSubmit.as_view()),
    url(r'^banks/(?P<bank_id>[-.:@%\d\w]+)/assessmentstaken/(?P<taken_id>[-.:@%\d\w]+)/questions/(?P<question_id>[-.:@%\d\w]+)/surrender/?$',
        views.AssessmentTakenQuestionSurrender.as_view()),
    # CANNOT support the following, yet. Permissions will not work, because
    # need the Item (usually to fill in the right answer), yet learners who
    # access takens only cannot get to the item, only the question.
    # url(r'^assessment/banks/(?P<bank_id>[-.:@%\d\w]+)/assessmentstaken/(?P<taken_id>[-.:@%\d\w]+)/questions/(?P<question_id>[-.:@%\d\w]+)/(?P<output_format>[\w]+)/$',
    #     views.ItemTextAsFormat.as_view()),
    url(r'^hierarchies/$',
        views.AssessmentHierarchiesList.as_view()),
    url(r'^hierarchies/(?P<bank_id>[-.:@%\d\w]+)/?$',
        views.AssessmentHierarchiesRootDetails.as_view()),
    url(r'^hierarchies/(?P<bank_id>[-.:@%\d\w]+)/children/?$',
        views.AssessmentHierarchiesRootChildrenList.as_view()),
    url(r'^hierarchies/(?P<bank_id>[-.:@%\d\w]+)/children/(?P<child_id>[-.:@%\d\w]+)/?$',
        views.AssessmentHierarchiesRootChildDetails.as_view()),
    url(r'^items/(?P<sub_id>[-.:@%\d\w]+)/?$',
        views.ItemDetails.as_view()),
    url(r'^types/items/?$',
        views.SupportedItemTypes.as_view()),
    url(r'^docs/?$',
        views.Documentation.as_view()),
)

urlpatterns = format_suffix_patterns(urlpatterns)