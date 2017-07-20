
MANAGER_PATHS = {

    'service': {
        'ASSESSMENT': ('dlkit.services.assessment.AssessmentManager',
                       'dlkit.services.assessment.AssessmentManager'),
        'REPOSITORY': ('dlkit.services.repository.RepositoryManager',
                       'dlkit.services.repository.RepositoryManager'),
        'LEARNING': ('dlkit.services.learning.LearningManager',
                     'dlkit.services.learning.LearningManager'),
        'COMMENTING': ('dlkit.services.commenting.CommentingManager',
                       'dlkit.services.commenting.CommentingManager'),
        'RESOURCE': ('dlkit.services.resource.ResourceManager',
                     'dlkit.services.resource.ResourceManager'),
        'GRADING': ('dlkit.services.grading.GradingManager',
                    'dlkit.services.grading.GradingManager')
    },
    'json': {
        'ASSESSMENT': ('dlkit.json_.assessment.managers.AssessmentManager',
                       'dlkit.json_.assessment.managers.AssessmentProxyManager'),
        'REPOSITORY': ('dlkit.json_.repository.managers.RepositoryManager',
                       'dlkit.json_.repository.managers.RepositoryProxyManager'),
        'LEARNING': ('dlkit.json_.learning.managers.LearningManager',
                     'dlkit.json_.learning.managers.LearningProxyManager'),
        'COMMENTING': ('dlkit.json_.commenting.managers.CommentingManager',
                       'dlkit.json_.commenting.managers.CommentingProxyManager'),
        'RESOURCE': ('dlkit.json_.resource.managers.ResourceManager',
                     'dlkit.json_.resource.managers.ResourceProxyManager'),
        'GRADING': ('dlkit.json_.grading.managers.GradingManager',
                     'dlkit.json_.grading.managers.GradingProxyManager')
    },
    'authz_adapter': {
        'ASSESSMENT': ('dlkit.authz_adapter.assessment.managers.AssessmentManager',
                       'dlkit.authz_adapter.assessment.managers.AssessmentProxyManager'),
        'REPOSITORY': ('dlkit.authz_adapter.repository.managers.RepositoryManager',
                       'dlkit.authz_adapter.repository.managers.RepositoryProxyManager'),
        'LEARNING': ('dlkit.authz_adapter.learning.managers.LearningManager',
                     'dlkit.authz_adapter.learning.managers.LearningProxyManager'),
        'COMMENTING': ('dlkit.authz_adapter.commenting.managers.CommentingManager',
                       'dlkit.authz_adapter.commenting.managers.CommentingProxyManager'),
        'RESOURCE': ('dlkit.authz_adapter.resource.managers.ResourceManager',
                     'dlkit.authz_adapter.resource.managers.ResourceProxyManager'),
        'GRADING': ('dlkit.authz_adapter.grading.managers.GradingManager',
                    'dlkit.authz_adapter.grading.managers.GradingProxyManager')
    },
    'time_based_authz': {
        'AUTHORIZATION': ('dlkit.stupid_authz_impls.time_based_authz.AuthorizationManager',
                          'dlkit.stupid_authz_impls.time_based_authz.AuthorizationProxyManager')
    },
    'ask_me_authz': {
        'AUTHORIZATION': ('dlkit.stupid_authz_impls.ask_me_authz.AuthorizationManager',
                          'dlkit.stupid_authz_impls.ask_me_authz.AuthorizationProxyManager')
    },
    'handcar': {
        'LEARNING': ('dlkit.handcar.learning.managers.LearningManager',
                     'dlkit.handcar.learning.managers.LearningProxyManager'),
        'TYPE': ('dlkit.handcar.type.managers.TypeManager',
                 'dlkit.handcar.type.managers.TypeManager'),
        'REPOSITORY': ('dlkit.handcar.repository.managers.RepositoryManager',
                       'dlkit.handcar.repository.managers.RepositoryProxyManager'),
    },
    'aws_adapter': {
        'REPOSITORY': ('dlkit.aws_adapter.repository.managers.RepositoryManager',
                       'dlkit.aws_adapter.repository.managers.RepositoryProxyManager')
    },
    'qbank_authz': {
        'AUTHORIZATION': ('qbank_authz.authorization.managers.AuthorizationManager',
                          'qbank_authz.authorization.managers.AuthorizationProxyManager')
    },
    'resource_agent_authz_adapter': {
        'RESOURCE': ('resource_agent_authz_adapter.managers.ResourceManager',
                     'resource_agent_authz_adapter.managers.ResourceProxyManager')
    },
}


