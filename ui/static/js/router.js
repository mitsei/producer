// Filename: router.js
define(['jquery',
        'underscore',
        'backbone',
        'views/navbar/navbarHome',
        'views/footer/footer',
        'views/project/dashboard'
], function ($, _, Backbone, NavbarHomeView, FooterView, DashboardView) {
    var AppRouter = Backbone.Router.extend({
        routes: {
            ''                              : 'home',
            // Default
            '*actions'                      : 'defaultAction'
        }
    });

    var initialize = function () {
        var app_router = new AppRouter;
        app_router.on('route:home', function () {
            var dashboardView = new DashboardView();
            dashboardView.render();
        });

        app_router.on('route:defaultAction', function (actions) {
            // no configured route
            console.log('No route: ' + actions);
        });


        Backbone.View.prototype.goTo = function (loc) {
            app_router.navigate(loc, {trigger: true});
        };

        var navView = new NavbarHomeView();
        navView.render();

        var footerView = new FooterView();
        Backbone.history.start();
    };
    return {
        initialize: initialize
    };
});