// apps/curate/collections/asset_objectives.js

define(["backbone",
        "apps/curate/models/objective"],
    function(Backbone, ObjectiveModel){

    var AssetObjectives = Backbone.Collection.extend({
        initialize: function (models, options) {
            this.id = options.id;
        },
        model: ObjectiveModel,
        url: function () {
            return this.id ? '/api/v1/repository/assets/' + this.id + '/objectives/?page=all' : '/api/v1/learning/objectives/?page=all';
        },
        parse: function (response) {
            return response.data.results;
        }
    });

    return AssetObjectives;
});