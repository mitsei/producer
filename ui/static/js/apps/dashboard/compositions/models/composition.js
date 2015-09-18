// app/dashboard/compositions/models/composition.js

define(["backbone"],
    function(Backbone){

    var Composition = Backbone.Model.extend({
        initialize: function (options) {
            var children = this.get("children"),
                _this = this;
            if (children) {
                require(["apps/dashboard/compositions/collections/compositions"],
                    function (CompositionsCollection) {
                        _this.children = new CompositionsCollection(children);
                        _this.unset("children");
                });
            }
            this.options = options;
            return this;
        },
        url: function () {
            var url = this.id ? '/api/v1/repository/compositions/' + this.id : '/api/v1/repository/compositions/';

            if (this.options) {
                if (this.options.renderable) {
                    return url + '?fullMap';
                } else if (this.options.withChildren) {
                    return url + '?withChildren';
                } else {
                    return url;
                }
            } else {
                return url;
            }
        },
        unlock: function (parentId, _callback) {
            if (this.id) {
                var url = '/api/v1/repository/compositions/' + this.id + '/unlock/',
                    _this = this;

                Backbone.ajax({
                    url: url,
                    type: 'POST',
                    data: {
                        parentId: parentId
                    }
                }).success(function (data) {
                    _callback(data);
                }).error(function (xhr, status, msg) {
                    require(["app"], function (ProducerManager) {
                        ProducerManager.vent.trigger('msg:error',
                            'Unlock not successful...' + xhr.responseText);
                        console.log('Unlock not successful...');
                    });
                });
            }
        },
        updateAssets: function (assetIds) {
            // update the composition's assetIds via PUT to <compositionId>/assets/
            if (this.id) {
                var url = '/api/v1/repository/compositions/' + this.id + '/assets/';

            }
        }
    });
    return Composition;
});