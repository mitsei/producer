// Filename: router.js
define(['jquery',
        'underscore',
        'marionette',
        'apps/login/views/login',
        'apps/dashboard/views/dashboard'
], function ($, _, Marionette, LoginView, DashboardView) {
    var AppRouter = Marionette.AppRouter.extend({
        routes: {
            ''                              : 'login',
            'dashboard'                     : 'dashboard',
            // Default
            '*actions'                      : 'defaultAction'
        },
        login: function () {
            $('#login_tabs').tabs();
        },
        dashboard: function () {
            var dashboard = new DashboardView();

            dashboard.render();
        }
    });

    return AppRouter;
});