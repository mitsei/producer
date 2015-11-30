// apps/curate/collections/item_objectives.js

define(["backbone",
        "apps/curate/models/objective"],
    function(Backbone, ObjectiveModel){

    var ItemObjectives = Backbone.Collection.extend({
        initialize: function (models, options) {
            this.id = options.id;
        },
        model: ObjectiveModel,
        url: function () {
            return this.id ? '/api/v1/assessment/items/' + this.id + '/objectives/?page=all' : '/api/v1/learning/objectives/?page=all';
        },
        parse: function (response) {
            return response.data.results;
        }
    });

    return ItemObjectives;
});