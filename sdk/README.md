# AdPulse SDK

JavaScript Web SDK for the AdPulse publisher platform — ad serving, mediation, in-app bidding, and attribution.

## Quick Start

### 1. Include the SDK

```html
<script src="https://cdn.adpulse.com/sdk/adpulse.js"></script>
<script>
  AdPulse.init("YOUR_PUBLISHER_KEY", {
    baseUrl: "https://api.adpulse.com",     // optional, defaults to production
  });
</script>
```

### 2. Add ad placements (auto-scan)

```html
<div data-adpulse data-slot="AD_UNIT_ID"></div>
```

The SDK automatically scans `[data-adpulse]` elements after init and loads ads into them.

### 3. Or load ads imperatively

```html
<div id="my-ad-slot"></div>
<script>
  AdPulse.showAd("#my-ad-slot", {
    slot: "AD_UNIT_ID",
  });
</script>
```

### 4. Track events

```javascript
// Post-install events for attribution
AdPulse.trackEvent("purchase", { value: 29.99, currency: "USD" });
AdPulse.trackEvent("signup", { value: 0 });
AdPulse.trackEvent("level_up", { value: 0 });
```

## Core API

### `AdPulse.init(publisherKey, options)`

| Param | Type | Description |
|-------|------|-------------|
| `publisherKey` | `string` | Your publisher API key |
| `options.baseUrl` | `string` | API base URL (default: production) |

Initializes the SDK, starts auto-scanning for ad placements, and begins event buffering.

### `AdPulse.showAd(container, options)`

| Param | Type | Description |
|-------|------|-------------|
| `container` | `string \| Element` | CSS selector or DOM element |
| `options.slot` | `string` | AdUnit ID |
| `options.onImpression` | `function` | Callback on impression |
| `options.onClick` | `function` | Callback on click |

Loads an ad via mediation + bidding, renders it, and tracks impressions/clicks.

### `AdPulse.trackEvent(eventName, data)`

| Param | Type | Description |
|-------|------|-------------|
| `eventName` | `string` | Event type (e.g., "purchase", "install") |
| `data.value` | `number` | Event value (for revenue tracking) |
| `data.currency` | `string` | Currency code (default: "USD") |

Tracks a conversion/event for attribution matching.

### `AdPulse.getDeviceId()`

Returns the persistent device identifier (stored in `_adp_device` cookie).

## Architecture

```
Publisher Page
    ↓
AdPulse SDK (adpulse.js)
    ↓
├── Bidding (POST /v1/bid — 500ms timeout)
│   └── Server-side auction (waterfall + bidding networks)
│
├── Impression Tracking (IntersectionObserver)
│   └── POST /v1/events/batch (sendBeacon)
│
├── Click Tracking (capture + redirect)
│   └── POST /v1/events/batch
│
└── Conversion Tracking
    └── POST /v1/events/conversion
         → Attribution Engine (InstallMatcher)
```

## Ad Unit Configuration

Configure mediation sources for each AdUnit via the platform API:

```json
{
  "waterfall": [
    { "network": "AdMob", "eCPM": 4.50, "priority": 1 },
    { "network": "Unity Ads", "eCPM": 3.20, "priority": 2 }
  ],
  "bidding": {
    "enabled": true,
    "timeout_ms": 500,
    "networks": ["Meta", "AppLovin"]
  }
}
```

## Attribution

Attribution matching is handled server-side:

1. SDK tracks clicks → stored as `ClickEvent` with `device_id`
2. SDK tracks conversions → stored as `ConversionEvent` with `device_id`
3. `InstallMatcher` matches conversions to clicks by `device_id` within 7-day window
4. Attribution results → `ConversionEvent.attributed_network`

Supports last-click, first-click, linear, and time-decay models.

## Tracking Pixels

For server-side attribution, use the pixel helper:

```html
<script src="https://cdn.adpulse.com/sdk/pixel.js"></script>

<!-- Impression pixel -->
<img src="https://t.adpulse.com/pixel/imp?aduid=AD_UNIT_ID&uid=USER_ID">

<!-- Click pixel -->
<img src="https://t.adpulse.com/pixel/click?aduid=AD_UNIT_ID&uid=USER_ID">

<!-- Conversion pixel -->
<img src="https://t.adpulse.com/pixel/conv?aduid=AD_UNIT_ID&uid=USER_ID&ev=install&val=1.00">
```

Or use the JavaScript API:

```javascript
AdPulsePixel.impression({ ad_unit_id: "au_xxx", device_id: "dev_xxx" });
AdPulsePixel.conversion({ ad_unit_id: "au_xxx", device_id: "dev_xxx", event_type: "install" });
```