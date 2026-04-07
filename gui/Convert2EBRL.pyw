#  Copyright (c) 2024-2026. American Printing House for the Blind.
#
# This file is part of Convert2EBRL.
# Convert2EBRL is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# Convert2EBRL is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with Convert2EBRL. If not, see <https://www.gnu.org/licenses/>.

# nuitka-project-set: APP_VERSION = __import__("convert2ebrl").__version__
# nuitka-project: --mode=standalone
# nuitka-project: --windows-console-mode=disable
# nuitka-project: --enable-plugins=pyside6
# nuitka-project: --include-package-data=brf2ebrl
# nuitka-project: --include-package=brf2ebrl_bana
# nuitka-project: --include-package=brf2ebrl_nfb
# nuitka-project: --product-version={APP_VERSION}

import sys

from convert2ebrl.__main__ import run_app

if __name__ == "__main__":
    run_app(sys.argv)
