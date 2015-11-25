// apps/curate/collections/objectives.js

define(["backbone",
        "apps/curate/models/objective"],
    function(Backbone, ObjectiveModel){

    var Objectives = Backbone.Collection.extend({
        initialize: function (models, options) {
            this.id = options.id;
        },
        model: ObjectiveModel,
        url: function () {
            return '/api/v1/learning/objectives/?page=all';
        },
        parse: function (response) {
            return response.data.results;
        }
    });

    return Objectives;
});