using Toybox.WatchUi;

class NMMinerDelegate extends WatchUi.BehaviorDelegate {

    private var _view;

    function initialize(view) {
        BehaviorDelegate.initialize();
        _view = view;
    }

    function onSelect() {
        _view.fetchData();
        return true;
    }
}
