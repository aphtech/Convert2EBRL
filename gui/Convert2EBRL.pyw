# nuitka-project: --mode=standalone
# nuitka-project: --windows-console-mode=disable
# nuitka-project: --enable-plugins=pyside6
# nuitka-project: --include-package-data=brf2ebrl
# nuitka-project: --include-package=brf2ebrl_bana
# nuitka-project: --include-package=brf2ebrl_nfb

import sys

from convert2ebrl.__main__ import run_app

if __name__ == "__main__":
    run_app(sys.argv)
