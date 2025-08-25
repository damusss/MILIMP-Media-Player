print("MILIMP Media Player")
from ui.MILIMP import MILIMP
from ui.extra.ask_data_path import MILIMPAskDataPath
from ui.common import DATA_PATH, win_set_app_id
from ui.common.data import SafeRunningContext
import faulthandler

try:
    faulthandler.enable()
except RuntimeError:
    ...

win_set_app_id()

if __name__ == "__main__":
    if DATA_PATH is None:
        app = MILIMPAskDataPath()
        app.run()
    else:
        with SafeRunningContext(None):
            app = MILIMP()
        with SafeRunningContext(app):
            app.run()
