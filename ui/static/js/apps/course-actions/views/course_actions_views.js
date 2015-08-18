// apps/course-actions/views/course_actions_views.js

define(["app",
        "apps/common/utilities",
        "jquery-ui",
        "bootstrap-drawer"],
       function(ProducerManager, Utils){
  ProducerManager.module("CourseActionsApp.View", function(View, ProducerManager, Backbone, Marionette, $, _){
    View.CourseActionsView = Marionette.ItemView.extend({
        template: false,
        el: '.action-btns',
        events: {
            'click #add-new-components-btn' : 'toggleComponentSearchPane'
        },
        toggleComponentSearchPane: function () {
            var $searchMenu =$('#search-components-menu');
            $searchMenu.drawer('toggle');
            if (!$searchMenu.hasClass('open')) {
                // doesn't get the class "open" until after the drawer is opened...
                // load the first results
                $searchMenu.find('button.execute-keyword-search')
                    .trigger('click');
            }
        }
    });
  });

  return ProducerManager.CourseActionsApp.View;
});