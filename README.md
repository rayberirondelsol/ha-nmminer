# NMMiner Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

Monitor your NMMiner Bitcoin solo miner directly in Home Assistant.

![NMMiner Dashboard](docs/dashboard.png)

## Features

- **Auto-discovery of all sensors** — just enter your miner's IP address
- **24 sensor entities** including HashRate, Shares, Difficulty, Temperature, WiFi, Uptime and more
- **Device grouping** — all sensors appear under one device in HA
- **Multi-device support** — if your swarm has multiple miners, each gets its own device
- **Pre-built dashboard** included (optional)
- **German & English** translations

## Installation

### HACS (Recommended)

1. Open HACS in your Home Assistant
2. Click the three dots menu (top right) → **Custom repositories**
3. Add `rayberirondelsol/ha-nmminer` with category **Integration**
4. Click **Install**
5. Restart Home Assistant

### Manual

1. Copy the `custom_components/nmminer` folder to your `config/custom_components/` directory
2. Restart Home Assistant

## Setup

1. Go to **Settings → Devices & Services → Add Integration**
2. Search for **NMMiner**
3. Enter the IP address of your miner (e.g. `192.168.1.100`)
4. Done! All sensors are created automatically.

## Sensors

| Sensor | Description | Unit |
|--------|-------------|------|
| HashRate | Current device hash rate | — |
| Total HashRate | Combined hash rate (all workers) | — |
| Active Workers | Number of active mining workers | — |
| Best Difficulty | Best difficulty found (summary) | — |
| Shares | Share string (accepted/total/rate) | — |
| Shares Accepted | Number of accepted shares | — |
| Shares Total | Total number of shares | — |
| Share Acceptance | Acceptance rate | % |
| Pool | Mining pool address | — |
| Net Difficulty | Current Bitcoin network difficulty | — |
| Pool Difficulty | Pool-assigned difficulty | — |
| Last Difficulty | Last share difficulty | — |
| Best Diff Session | Best difficulty this session | — |
| Best Diff All-Time | Best difficulty all-time | — |
| Hits | Valid block hits | — |
| Temperature | Device temperature | °C |
| WiFi Signal | WiFi RSSI | dBm |
| Free Memory | Available heap memory | KB |
| Uptime Session | Current session uptime | — |
| Uptime Total | Total device uptime | — |
| Firmware | Firmware version | — |
| Board | Board type / model | — |
| IP Address | Device IP address | — |
| Last Seen | Last communication timestamp | — |

## Dashboard

A pre-built dashboard YAML is included in `dashboard/nmminer-dashboard.yaml`. To use it:

1. Copy `dashboard/nmminer-dashboard.yaml` to your HA `config/` directory
2. Add to your `configuration.yaml`:

```yaml
lovelace:
  mode: storage
  dashboards:
    nm-miner:
      mode: yaml
      title: NMMiner
      icon: mdi:pickaxe
      show_in_sidebar: true
      filename: nmminer-dashboard.yaml
```

3. Restart Home Assistant

> **Tip:** If you have `mini-graph-card` installed via HACS, you can replace the `history-graph` cards with `custom:mini-graph-card` for nicer visualizations.

## How it works

The integration polls the miner every 30 seconds:

- **Firmware 2.x:** `GET /api/system/info`
- **Firmware 1.x:** `GET /swarm` (the API behind the built-in `/static` dashboard)

It tries `/api/system/info` first and falls back to `/swarm`. The 2.x response is translated into the 1.x format, so the same sensors are created for both. Values that 2.x does not provide show as `unknown`.

> **2.x support is built from the official firmware API docs and has not yet been verified on real 2.x hardware.** If a sensor looks wrong, please open an issue and include the output of `http://<miner-ip>/api/system/info`.

**Required network access:** Your Home Assistant instance must be able to reach the NMMiner device on your local network via HTTP (port 80).

## Compatibility

- **Home Assistant:** 2024.1+
- **NMMiner firmware:** 1.8.x (tested on v1.8.28), 2.x (experimental, see above)
- **NMMiner models:** Any ESP32-based miner with the `/swarm` (1.x) or `/api/system/info` (2.x) endpoint

## Development

`py -m pip install pytest && py -m pytest` runs the endpoint-mapping tests (no Home Assistant needed).

## License

MIT
