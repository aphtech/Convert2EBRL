#  Copyright (c) 2024. American Printing House for the Blind.
#
# This file is part of Convert2EBRL.
# Convert2EBRL is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# Convert2EBRL is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with Convert2EBRL. If not, see <https://www.gnu.org/licenses/>.
import hashlib
import os.path
import sys
from collections.abc import Iterable


def get_file_hash(filenames: Iterable[str]) -> str:
    hasher = hashlib.sha256()
    for filename in filenames:
        if os.path.exists(filename) and os.path.isfile(filename):
            with open(filename, "rb") as f:
                while data := f.read(1024):
                    hasher.update(data)
    return hasher.hexdigest()

if __name__ == "__main__":
    print(get_file_hash(sys.argv[1:]))
