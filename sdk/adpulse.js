(function (global) {
  'use strict';

  var API_BASE = 'https://api.adpulse.com';
  var SDK_VERSION = '1.0.0';
  var BATCH_INTERVAL_MS = 2000;
  var BID_TIMEOUT_MS = 500;

  var state = {
    initialized: false,
    publisherKey: null,
    options: {},
    eventQueue: [],
    batchTimer: null,
    configCache: {},
    _scanTimer: null,
  };

  function noop() {}

  /* ---- 工具函数 ---- */
  function generateId() {
    return 'xxxx-xxxx-4xxx-yxxx-xxxx'.replace(/[xy]/g, function (c) {
      var r = (Math.random() * 16) | 0;
      return (c === 'x' ? r : (r & 0x3) | 0x8).toString(16);
    });
  }

  function getCookie(name) {
    var match = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'));
    return match ? decodeURIComponent(match[2]) : null;
  }

  function setCookie(name, value, days) {
    var expires = new Date(Date.now() + days * 864e5).toUTCString();
    document.cookie = name + '=' + encodeURIComponent(value) + '; expires=' + expires + '; path=/';
  }

  function getDeviceId() {
    var id = getCookie('_adp_device');
    if (!id) {
      id = 'w-' + generateId();
      setCookie('_adp_device', id, 365);
    }
    return id;
  }

  function fetchJSON(url, body) {
    return fetch(url, {
      method: body ? 'POST' : 'GET',
      headers: { 'Content-Type': 'application/json' },
      body: body ? JSON.stringify(body) : undefined,
      credentials: 'omit',
    }).then(function (r) { return r.json(); });
  }

  /* ---- 批量事件上报 ---- */
  function flushEvents() {
    if (state.eventQueue.length === 0) return;
    var batch = state.eventQueue.splice(0, state.eventQueue.length);
    try {
      navigator.sendBeacon(API_BASE + '/v1/events/batch', new Blob([JSON.stringify(batch)], { type: 'application/json' }));
    } catch (e) {
      fetchJSON(API_BASE + '/v1/events/batch', batch).catch(noop);
    }
  }

  function enqueueEvent(event) {
    state.eventQueue.push(event);
    if (!state.batchTimer) {
      state.batchTimer = setInterval(flushEvents, BATCH_INTERVAL_MS);
    }
  }

  /* ---- SDK 配置拉取 ---- */
  function fetchAdUnitConfig(adUnitId, callback) {
    if (state.configCache[adUnitId]) {
      return callback(state.configCache[adUnitId]);
    }
    fetchJSON(API_BASE + '/v1/sdk/config/' + adUnitId + '?publisher=' + state.publisherKey + '&device_id=' + getDeviceId())
      .then(function (config) {
        state.configCache[adUnitId] = config;
        callback(config);
      })
      .catch(function () { callback(null); });
  }

  /* ---- Bidding + Mediation 请求 ---- */
  function requestBid(adUnitId, callback) {
    var timeout = setTimeout(function () {
      callback(null);
    }, BID_TIMEOUT_MS);

    fetchJSON(API_BASE + '/v1/bid', {
      publisher_key: state.publisherKey,
      ad_unit_id: adUnitId,
      device_id: getDeviceId(),
      user_agent: navigator.userAgent,
      url: location.href,
      sdk_version: SDK_VERSION,
    }).then(function (resp) {
      clearTimeout(timeout);
      callback(resp);
    }).catch(function () {
      clearTimeout(timeout);
      callback(null);
    });
  }

  /* ---- 展示跟踪 ---- */
  function trackImpression(adUnitId, ad, element) {
    var impId = 'imp-' + generateId();

    enqueueEvent({
      event: 'impression',
      impression_id: impId,
      ad_unit_id: adUnitId,
      device_id: getDeviceId(),
      network_name: ad ? ad.network_name : 'fallback',
      revenue: ad ? ad.price : 0,
      currency: ad ? ad.currency : 'USD',
      url: location.href,
      user_agent: navigator.userAgent,
      timestamp: Date.now(),
    });

    element.setAttribute('data-adp-impression-id', impId);
    return impId;
  }

  /* ---- 点击跟踪 ---- */
  function handleClick(e, adUnitId, ad, impId, element) {
    var clickId = 'clk-' + generateId();
    var redirectUrl = ad && ad.click_url ? ad.click_url : (element.getAttribute('href') || '#');

    enqueueEvent({
      event: 'click',
      click_id: clickId,
      impression_id: impId,
      ad_unit_id: adUnitId,
      device_id: getDeviceId(),
      network_name: ad ? ad.network_name : 'fallback',
      redirect_url: redirectUrl,
      timestamp: Date.now(),
    });

    if (!redirectUrl || redirectUrl === '#') {
      e.preventDefault();
      return;
    }

    e.preventDefault();
    // 先上报点击，再执行跳转
    flushEvents();
    setTimeout(function () {
      location.href = redirectUrl;
    }, 50);
  }

  /* ---- 广告渲染 ---- */
  function renderAd(container, adUnitId, config) {
    requestBid(adUnitId, function (bidResult) {
      var ad = bidResult;
      var html = '';
      var clickUrl = '#';

      if (ad && ad.creative_html) {
        html = ad.creative_html;
        clickUrl = ad.click_url || '#';
      } else if (config && config.fallback_html) {
        html = config.fallback_html;
        clickUrl = config.fallback_click_url || '#';
      }

      container.innerHTML = html;

      /* ---- 展示检测 (IntersectionObserver) ---- */
      var impId = null;
      var hasImpression = false;
      if ('IntersectionObserver' in window) {
        var observer = new IntersectionObserver(function (entries) {
          entries.forEach(function (entry) {
            if (entry.isIntersecting && !hasImpression) {
              hasImpression = true;
              impId = trackImpression(adUnitId, ad, container);
              observer.disconnect();
            }
          });
        }, { threshold: 0.5 });
        observer.observe(container);
      } else {
        impId = trackImpression(adUnitId, ad, container);
      }

      /* ---- 点击跟踪 ---- */
      var links = container.querySelectorAll('a');
      if (links.length > 0) {
        links.forEach(function (link) {
          link.addEventListener('click', function (e) {
            handleClick(e, adUnitId, ad, impId, container);
          });
        });
      } else {
        container.style.cursor = 'pointer';
        container.addEventListener('click', function (e) {
          handleClick(e, adUnitId, ad, impId, container);
        });
      }
    });
  }

  /* ---- 自动扫描 data-adpulse 元素 ---- */
  function scanElements() {
    var elements = document.querySelectorAll('[data-adpulse]');
    elements.forEach(function (el) {
      if (el.getAttribute('data-adp-loaded')) return;
      el.setAttribute('data-adp-loaded', 'true');
      var adUnitId = el.getAttribute('data-slot');
      if (!adUnitId) return;

      fetchAdUnitConfig(adUnitId, function (config) {
        renderAd(el, adUnitId, config);
      });
    });
  }

  /* ---- 公开 API ---- */
  var AdPulse = {
    VERSION: SDK_VERSION,

    init: function (publisherKey, options) {
      if (state.initialized) return;
      state.initialized = true;
      state.publisherKey = publisherKey;
      state.options = options || {};

      if (state.options.baseUrl) {
        API_BASE = state.options.baseUrl;
      }

      // DOM 就绪后扫描
      if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', scanElements);
      } else {
        scanElements();
      }

      // 监听动态插入
      if (global.MutationObserver) {
        var observer = new MutationObserver(function () { scanElements(); });
        observer.observe(document.body, { childList: true, subtree: true });
      }
    },

    showAd: function (containerOrSelector, options) {
      var container = (typeof containerOrSelector === 'string')
        ? document.querySelector(containerOrSelector)
        : containerOrSelector;
      if (!container) return;

      var adUnitId = options.slot || container.getAttribute('data-slot');
      if (!adUnitId) return;

      fetchAdUnitConfig(adUnitId, function (config) {
        renderAd(container, adUnitId, config);
      });
    },

    trackEvent: function (eventName, data) {
      enqueueEvent({
        event: 'conversion',
        event_type: eventName,
        device_id: getDeviceId(),
        publisher_key: state.publisherKey,
        value: (data && data.value) || 0,
        currency: (data && data.currency) || 'USD',
        metadata: data || {},
        timestamp: Date.now(),
      });
      flushEvents();
    },

    getDeviceId: function () {
      return getDeviceId();
    },

    setBaseUrl: function (url) {
      API_BASE = url;
    },
  };

  global.AdPulse = AdPulse;
})(window);
