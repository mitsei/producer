// app/dashboard/domains/collections/user_courses.js

define(["backbone",
    "apps/dashboard/compositions/models/composition"],
    function(Backbone, CompositionModel){

    var UserCourses = Backbone.Collection.extend({
        initialize: function (models, options) {
            this.id = options.id;
        },
        model: CompositionModel,
        url: function () {
            return '/api/v1/repository/repositories/' + this.id + '/compositions/?course&page=all';
        },
        parse: function (response) {
            return response.data.results;
        }
    });

    return UserCourses;
});