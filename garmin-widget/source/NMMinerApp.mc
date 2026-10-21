using Toybox.Application;
using Toybox.WatchUi;

class NMMinerApp extends Application.AppBase {

    function initialize() {
        AppBase.initialize();
    }

    function getInitialView() {
        var view = new NMMinerView();
        var delegate = new NMMinerDelegate(view);
        return [view, delegate];
    }
}
