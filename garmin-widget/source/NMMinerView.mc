using Toybox.WatchUi;
using Toybox.Graphics;
using Toybox.Communications;
using Toybox.Application;
using Toybox.Application.Storage;
using Toybox.Timer;
using Toybox.Lang;
using Toybox.Attention;

class NMMinerView extends WatchUi.View {

    // Display data fields (only updated atomically after all fetches complete)
    private var _hashRate = "--";
    private var _bestDiff = "--";
    private var _shares = "--";
    private var _shareAcceptance = "--";
    private var _hits = "--";
    private var _rssi = "--";
    private var _uptimeSession = "--";

    // Temp buffer for in-flight fetch (not displayed until complete)
    private var _tmp = null;

    private var _hitAlert = false;
    private var _isLoading = false;
    private var _errorMsg = null;
    private var _refreshTimer = null;
    private var _fetchStep = 0;
    private var _fetchGen = 0;
    private var _recvGen = 0;

    private const HA_URL = "https://assi.ngrok.io";
    private const HA_TOKEN = "PASTE_HA_LONG_LIVED_TOKEN_HERE";

    private const SENSORS = [
        "sensor.nmminer_device_hashrate",
        "sensor.nmminer_best_difficulty",
        "sensor.nmminer_shares",
        "sensor.nmminer_share_acceptance",
        "sensor.nmminer_hits",
        "sensor.nmminer_rssi",
        "sensor.nmminer_uptime"
    ];

    // Colors — 64-color MIP palette (FR935)
    private const COLOR_BG       = 0x000000;
    private const COLOR_ACCENT   = 0xFFAA00;
    private const COLOR_TEXT     = 0xFFFFFF;
    private const COLOR_LABEL    = 0xAAAAAA;
    private const COLOR_DIVIDER  = 0x555555;

    function initialize() {
        View.initialize();
        loadStoredData();
    }

    function onShow() {
        fetchData();
        _refreshTimer = new Timer.Timer();
        _refreshTimer.start(method(:onTimerRefresh), 60000, true);
    }

    function onHide() {
        if (_refreshTimer != null) {
            _refreshTimer.stop();
            _refreshTimer = null;
        }
    }

    function onTimerRefresh() {
        fetchData();
    }

    //--------------------------------------------------------------
    // Persistent storage
    //--------------------------------------------------------------

    private function loadStoredData() {
        var stored = Storage.getValue("md");
        if (stored != null) {
            _hashRate        = valOr(stored["hr"], "--");
            _bestDiff        = valOr(stored["bd"], "--");
            _shares          = valOr(stored["sh"], "--");
            _shareAcceptance = valOr(stored["sc"], "--");
            _hits            = valOr(stored["hi"], "--");
            _rssi            = valOr(stored["rs"], "--");
            _uptimeSession   = valOr(stored["up"], "--");
        }
    }

    private function saveData() {
        Storage.setValue("md", {
            "hr" => _hashRate,
            "bd" => _bestDiff,
            "sh" => _shares,
            "sc" => _shareAcceptance,
            "hi" => _hits,
            "rs" => _rssi,
            "up" => _uptimeSession
        });
    }

    //--------------------------------------------------------------
    // HTTP — sequential fetch into temp buffer, atomic swap at end
    //--------------------------------------------------------------

    function fetchData() {
        _fetchGen++;
        _fetchStep = 0;
        _tmp = new [7];
        _isLoading = true;
        WatchUi.requestUpdate();
        fetchNext();
    }

    private function fetchNext() {
        if (_fetchStep >= SENSORS.size()) {
            // All done — atomic swap from temp to display vars
            _hashRate        = _tmp[0];
            _bestDiff        = _tmp[1];
            _shares          = trimShares(_tmp[2]);
            _shareAcceptance = _tmp[3];

            // Check for new hits before overwriting
            var newHitsVal = _tmp[4];
            if (!newHitsVal.equals(_hits) && !newHitsVal.equals("0") && !newHitsVal.equals("--")) {
                var newHits = newHitsVal.toNumber();
                var oldHits = _hits.toNumber();
                if (newHits != null && (oldHits == null || newHits > oldHits)) {
                    _hitAlert = true;
                    if (Attention has :vibrate) {
                        Attention.vibrate([
                            new Attention.VibeProfile(100, 500),
                            new Attention.VibeProfile(0, 200),
                            new Attention.VibeProfile(100, 500)
                        ]);
                    }
                }
            }
            _hits            = newHitsVal;
            _rssi            = _tmp[5];
            _uptimeSession   = _tmp[6];

            _tmp = null;
            _isLoading = false;
            _errorMsg = null;
            saveData();
            WatchUi.requestUpdate();
            return;
        }

        _recvGen = _fetchGen;
        var url = HA_URL + "/api/states/" + SENSORS[_fetchStep];
        Communications.makeWebRequest(
            url,
            null,
            {
                :method       => Communications.HTTP_REQUEST_METHOD_GET,
                :headers      => {
                    "Authorization" => "Bearer " + HA_TOKEN,
                    "Content-Type"  => "application/json"
                },
                :responseType => Communications.HTTP_RESPONSE_CONTENT_TYPE_JSON
            },
            method(:onReceive)
        );
    }

    function onReceive(responseCode, data) {
        if (_tmp == null || _recvGen != _fetchGen) {
            // Stale callback from cancelled fetch — ignore
            return;
        }

        if (responseCode == 200 && data != null && data instanceof Dictionary) {
            var state = data["state"];
            if (state != null) {
                _tmp[_fetchStep] = state.toString();
            } else {
                _tmp[_fetchStep] = "--";
            }
        } else {
            _tmp[_fetchStep] = "--";
            _errorMsg = "Err " + responseCode.toString();
        }

        _fetchStep++;
        fetchNext();
    }

    //--------------------------------------------------------------
    // Drawing — Premier pkl04 inspired layout
    //--------------------------------------------------------------

    function onUpdate(dc) {
        dc.setColor(COLOR_BG, COLOR_BG);
        dc.clear();

        var w  = dc.getWidth();
        var h  = dc.getHeight();
        var cx = w / 2;

        // --- Setup / error screen (no data yet) ---
        if (_errorMsg != null && _hashRate.equals("--")) {
            drawSetupScreen(dc, cx, h);
            return;
        }

        // --- Title bar ---
        dc.setColor(COLOR_ACCENT, Graphics.COLOR_TRANSPARENT);
        dc.drawText(cx, 15, Graphics.FONT_XTINY, "NMMiner", Graphics.TEXT_JUSTIFY_CENTER);

        // Loading dot
        if (_isLoading) {
            dc.setColor(COLOR_LABEL, Graphics.COLOR_TRANSPARENT);
            dc.fillCircle(w - 32, 22, 3);
        }

        // Top separator
        dc.setColor(COLOR_DIVIDER, Graphics.COLOR_TRANSPARENT);
        dc.drawLine(55, 33, w - 55, 33);

        // --- HashRate (prominent, orange) ---
        dc.setColor(COLOR_ACCENT, Graphics.COLOR_TRANSPARENT);
        dc.drawText(cx, 38, Graphics.FONT_MEDIUM, _hashRate, Graphics.TEXT_JUSTIFY_CENTER);

        // Separator below hashrate
        dc.setColor(COLOR_DIVIDER, Graphics.COLOR_TRANSPARENT);
        dc.drawLine(35, 70, w - 35, 70);

        // Column positions
        var lx = w / 4 + 2;
        var rx = 3 * w / 4 - 2;

        // ROW 1: Best Diff | Shares
        drawLabel(dc, lx, 76, "BEST DIFF");
        drawLabel(dc, rx, 76, "SHARES");

        drawValue(dc, lx, 92, _bestDiff);
        drawValue(dc, rx, 92, _shares);

        dc.setColor(COLOR_DIVIDER, Graphics.COLOR_TRANSPARENT);
        dc.drawLine(cx, 76, cx, 112);
        dc.drawLine(35, 115, w - 35, 115);

        // ROW 2: Uptime | WiFi
        drawLabel(dc, lx, 121, "UPTIME");
        drawLabel(dc, rx, 121, "WIFI");

        drawValue(dc, lx, 137, formatUptime(_uptimeSession));
        var rssiDisplay = _rssi.equals("--") ? "--" : _rssi + "dB";
        drawValue(dc, rx, 137, rssiDisplay);

        dc.setColor(COLOR_DIVIDER, Graphics.COLOR_TRANSPARENT);
        dc.drawLine(cx, 121, cx, 157);
        dc.drawLine(35, 160, w - 35, 160);

        // ROW 3: Hits | Accept
        drawLabel(dc, lx, 166, "HITS");
        drawLabel(dc, rx, 166, "ACCEPT");

        if (_hitAlert) {
            dc.setColor(COLOR_ACCENT, Graphics.COLOR_TRANSPARENT);
            dc.drawText(lx, 182, Graphics.FONT_SMALL, _hits + " HIT!", Graphics.TEXT_JUSTIFY_CENTER);
            _hitAlert = false;
        } else {
            drawValue(dc, lx, 182, _hits);
        }
        var accDisplay = _shareAcceptance.equals("--") ? "--" : _shareAcceptance + "%";
        drawValue(dc, rx, 182, accDisplay);

        dc.setColor(COLOR_DIVIDER, Graphics.COLOR_TRANSPARENT);
        dc.drawLine(cx, 166, cx, 202);
        dc.drawLine(55, 205, w - 55, 205);

        // --- Error indicator at bottom ---
        if (_errorMsg != null) {
            dc.setColor(0xFF5555, Graphics.COLOR_TRANSPARENT);
            dc.drawText(cx, 210, Graphics.FONT_XTINY, _errorMsg, Graphics.TEXT_JUSTIFY_CENTER);
        }
    }

    //--------------------------------------------------------------
    // Drawing helpers
    //--------------------------------------------------------------

    private function drawLabel(dc, x, y, text) {
        dc.setColor(COLOR_LABEL, Graphics.COLOR_TRANSPARENT);
        dc.drawText(x, y, Graphics.FONT_XTINY, text, Graphics.TEXT_JUSTIFY_CENTER);
    }

    private function drawValue(dc, x, y, text) {
        dc.setColor(COLOR_TEXT, Graphics.COLOR_TRANSPARENT);
        dc.drawText(x, y, Graphics.FONT_SMALL, text, Graphics.TEXT_JUSTIFY_CENTER);
    }

    private function drawSetupScreen(dc, cx, h) {
        dc.setColor(COLOR_ACCENT, Graphics.COLOR_TRANSPARENT);
        dc.drawText(cx, h / 2 - 35, Graphics.FONT_SMALL, "NMMiner", Graphics.TEXT_JUSTIFY_CENTER);

        dc.setColor(COLOR_LABEL, Graphics.COLOR_TRANSPARENT);
        if (_errorMsg != null) {
            dc.drawText(cx, h / 2, Graphics.FONT_XTINY, _errorMsg, Graphics.TEXT_JUSTIFY_CENTER);
        }
        dc.drawText(cx, h / 2 + 18, Graphics.FONT_XTINY, "Loading...", Graphics.TEXT_JUSTIFY_CENTER);
    }

    //--------------------------------------------------------------
    // Utility functions
    //--------------------------------------------------------------

    // "64/3739/98.3%" → "64/3739"
    private function trimShares(val) {
        var parts = splitStr(val, "/");
        if (parts.size() >= 2) {
            return parts[0] + "/" + parts[1];
        }
        return val;
    }

    private function formatUptime(uptime) {
        if (uptime.equals("--")) {
            return "--";
        }
        // Input format: "000d 04:38:32"
        var spaceIdx = uptime.find(" ");
        if (spaceIdx == null) {
            return uptime;
        }

        var daysPart = uptime.substring(0, spaceIdx);
        var timePart = uptime.substring(spaceIdx + 1, uptime.length());

        var dIdx = daysPart.find("d");
        if (dIdx != null) {
            daysPart = daysPart.substring(0, dIdx);
        }

        var parts = splitStr(timePart, ":");
        if (parts.size() < 2) {
            return uptime;
        }

        var days  = daysPart.toNumber();
        var hours = parts[0].toNumber();
        var mins  = parts[1];

        if (days != null && days > 0) {
            return days.toString() + "d " + hours.toString() + "h";
        }
        return hours.toString() + "h" + mins + "m";
    }

    private function splitStr(str, delim) {
        var result = [];
        var remaining = str;
        var idx = remaining.find(delim);
        while (idx != null) {
            result.add(remaining.substring(0, idx));
            remaining = remaining.substring(idx + delim.length(), remaining.length());
            idx = remaining.find(delim);
        }
        result.add(remaining);
        return result;
    }

    private function valOr(val, fallback) {
        if (val != null) {
            return val.toString();
        }
        return fallback;
    }
}
