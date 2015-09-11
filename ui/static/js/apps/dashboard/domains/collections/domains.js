// app/dashboard/domains/collections/domains.js

define(["backbone",
    "apps/dashboard/domains/models/repository"],
    function(Backbone, RepositoryModel){

    var Domains = Backbone.Collection.extend({
        model: RepositoryModel,
        url: function () {
            return '/api/v1/repository/repositories/?domains&page=all';
        },
        parse: function (response) {
            return response.data.results;
        }
    });

    return Domains;
});