// app/dashboard/domains/collections/domain_courses.js

define(["backbone",
    "apps/dashboard/domains/models/repository"],
    function(Backbone, RepositoryModel){

    var DomainCourses = Backbone.Collection.extend({
        initialize: function (models, options) {
            this.id = options.id;
        },
        model: RepositoryModel,
        url: function () {
            return '/api/v1/repository/repositories/' + this.id + '/children/?page=all';
        },
        parse: function (response) {
            return response.data.results;
        }
    });

    return DomainCourses;
});