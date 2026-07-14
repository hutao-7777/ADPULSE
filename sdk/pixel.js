/**
 * AdPulse Tracking Pixel Helper
 *
 * <img src="https://t.adpulse.com/pixel/imp?pid=PUB_KEY&aduid=AD_UNIT_ID&uid=USER_ID">
 * <img src="https://t.adpulse.com/pixel/click?pid=PUB_KEY&aduid=AD_UNIT_ID&uid=USER_ID">
 * <img src="https://t.adpulse.com/pixel/conv?pid=PUB_KEY&aduid=AD_UNIT_ID&uid=USER_ID&ev=install&val=1.00">
 *
 * Server-side integration example:
 *   curl "https://t.adpulse.com/api/v1/pixel/conv?ad_unit_id=...&device_id=...&event_type=install"
 */
!function(global){
  'use strict';
  var PIXEL_BASE = 'https://t.adpulse.com/pixel';

  function pixel(endpoint, params) {
    var query = [];
    for (var key in params) {
      if (params.hasOwnProperty(key) && params[key] != null) {
        query.push(encodeURIComponent(key) + '=' + encodeURIComponent(params[key]));
      }
    }
    var url = PIXEL_BASE + '/' + endpoint + '?' + query.join('&');
    new Image().src = url;
  }

  global.AdPulsePixel = {
    impression: function(opts) { pixel('imp', opts); },
    click: function(opts) { pixel('click', opts); },
    conversion: function(opts) { pixel('conv', opts); },
  };
}(window);
/** End AdPulse Pixel Helper **/
