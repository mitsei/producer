// apps/notification/views/notification_views.js

define(["app",
        "text!apps/notification/templates/error_notification.html",
        "text!apps/notification/templates/status_notification.html",
        "text!apps/notification/templates/success_notification.html"],
       function(ProducerManager, ErrorTemplate, StatusTemplate, SuccessTemplate){
  ProducerManager.module("NotificationApp.View", function(View, ProducerManager, Backbone, Marionette, $, _){
    var notifier;

    var BaseView = Marionette.ItemView.extend({
        initialize: function (options) {
            this.options = options;
            return this;
        },
        serializeData: function () {
            return {
                options: this.options
            };
        },
        events: {
            'click .dismiss-notification': 'removeNotification'
        },
        onShow: function () {
            if (notifier) {
                clearTimeout(notifier);
            }
            notifier = setTimeout(this.removeNotification, 30000);
        },
        removeNotification: function () {
            try{
                this.fadeOut("slow", function () {
                    ProducerManager.regions.notifications.$el.empty();
                });
            } catch (e) {
                ProducerManager.regions.notifications.$el.fadeOut("slow", function () {
                    ProducerManager.regions.notifications.$el.empty();
                });
            }
        }
    });

    View.ErrorView = BaseView.extend({
        template: function (serializedModel) {
            return _.template(ErrorTemplate)({
                msg: serializedModel.options.msg
            })
        }
    });

      View.StatusView = BaseView.extend({
        template: function (serializedModel) {
            return _.template(StatusTemplate)({
                msg: serializedModel.options.msg
            })
        }
      });

      View.SuccessView = BaseView.extend({
        template: function (serializedModel) {
            return _.template(SuccessTemplate)({
                msg: serializedModel.options.msg
            })
        }
    });

  });

  return ProducerManager.NotificationApp.View;
});