// app/dashboard/assets/models/assets.js

define(["backbone"],
    function(Backbone){

    var Asset = Backbone.Model.extend({
        url: function () {
            return this.id ? '/api/v1/repository/assets/' + this.id : '/api/v1/repository/assets/';
        }
    });
    return Asset;
});