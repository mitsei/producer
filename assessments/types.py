from dlkit.services.primitives import Type
from dlkit.mongo.locale.types import String

EDX_ITEM_RECORD_TYPE = Type(**{
    'authority': 'ODL.MIT.EDU',
    'namespace': 'item-record-type',
    'identifier': 'edx_item',
    'display_name': 'edX Item',
    'display_label': 'edX Item',
    'description': 'Assessment Item record extension for edX based Items',
    'domain': 'assessment.Item',
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
    'identifier': 'javascript',
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

WORDIGNORECASE_STRING_MATCH_TYPE = Type(**String().get_type_data('WORDIGNORECASE'))


FILES_SUBMISSION_ANSWER_TYPE = Type(**{
    'authority': 'ODL.MIT.EDU',
    'namespace': 'answer-record-type',
    'identifier': 'files-submission',
    'display_name': 'Files Submission Answer',
    'display_label': 'Files Submission Answer',
    'description': 'Assessment Answer record for files submission',
    'domain': 'assessment.Answer'
})

FILES_SUBMISSION_QUESTION_TYPE = Type(**{
    'authority': 'ODL.MIT.EDU',
    'namespace': 'question-record-type',
    'identifier': 'files-submission',
    'display_name': 'Files Submission Question',
    'display_label': 'Files Submission Question',
    'description': 'Assessment Question record for files submission',
    'domain': 'assessment.Question'
})


UOC_PROBLEM_TYPE = Type(**{
    'authority': 'ODL.MIT.EDU',
    'namespace': 'item-genus-type',
    'identifier': 'multi-file-submission',
    'display_name': 'Files Submission Problem Type',
    'display_label': 'Files Submission Problem Type',
    'description': 'An assessment item with files submission as student response',
    'domain': 'assessment.Item'
})


FILE_COMMENT_RECORD_TYPE = Type(**{
    'authority': 'ODL.MIT.EDU',
    'namespace': 'comment-type',
    'identifier': 'file-comment',
    'display_name': 'File Comment',
    'display_label': 'File Comment',
    'description': 'Comment via file',
    'domain': 'commenting.Comment'
})

COLOR_BANK_RECORD_TYPE = Type(**{
    'authority': 'ODL.MIT.EDU',
    'namespace': 'bank-record-type',
    'identifier': 'bank-color',
    'display_name': 'Bank Color',
    'display_label': 'Bank Color',
    'description': 'Assessment Bank record extension for Banks of color',
    'domain': 'assessment.Bank'
})

REVIEWABLE_TAKEN = Type(**{
    'authority': 'MOODLE.ORG',
    'namespace': 'assessment-taken-record-type',
    'identifier': 'review-options'
})

REVIEWABLE_OFFERED = Type(**{
    'authority': 'MOODLE.ORG',
    'namespace': 'assessment-offered-record-type',
    'identifier': 'review-options'
})