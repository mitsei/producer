//Filename: views/project/login.js

define([
    'jquery',
    'underscore',
    'backbone',
    'jquery-ui'
], function ($, _, Backbone) {
    var LoginView = Backbone.View.extend({
        el: $('#login_container'),
        initialize: function () {
            $('#login_tabs').tabs();
            return this;
        }
    });
    new LoginView();
    return LoginView;
});