// apps/navbar/views/navbar.js

define(["app"],
       function(ProducerManager){
  ProducerManager.module("NavbarApp.View", function(View, ProducerManager, Backbone, Marionette, $, _){
    View.NavbarView = Marionette.ItemView.extend({
        template: false,
        el: 'nav.navbar',
        events: {
            'click .repositories-menu li a' : 'loadRepoCourses'
        },
        loadRepoCourses: function () {
            require(["apps/common/utilities"], function (Utils) {
              $(".repositories-menu li a").on('click', function () {
                  Utils.fixDomainSelector($(this).attr('href'));
              });
            });
        }
    });
  });

  return ProducerManager.NavbarApp.View;
});