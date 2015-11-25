// app/curate/models/objective.js

define(["backbone"],
    function(Backbone){

    var Objective = Backbone.Model.extend({
        url: function () {
            return this.id ? '/api/v1/learning/objectives/' + this.id : '/api/v1/learning/objectives/';
        }
    });
    return Objective;
});