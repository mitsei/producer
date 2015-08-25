// app/dashboard/assets/models/assets.js

define(["backbone"],
    function(Backbone){

    var Asset = Backbone.Model.extend({
        initialize: function (options) {
            if (options.hasOwnProperty('id')) {
                this.set('id', options.id);
            }
            this.options = options;
            return this;
        },
        url: function () {
            var url;

            if (this.id.indexOf('repository.Asset') >= 0) {
                url = this.id ? '/api/v1/repository/assets/' + this.id : '/api/v1/repository/assets/';
            } else {
                url = this.id ? '/api/v1/assessment/items/' + this.id : '/api/v1/assessment/items/';
            }
            if (this.options.renderable) {
                return url + '?renderable_edxml';
            } else {
                return url;
            }
        }
    });
    return Asset;
});