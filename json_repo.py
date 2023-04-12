#
# Make data I need persist over a restart by storing it on disk in json format.
#
# I need:
#   temp:   float - the temperature last displayed to the screen.
#   error:  int    - error code for last detected error
#   feeder: int    - indication of last watchdog feeder
#   count:  int    - number of restarts with no display update
#

import json
import os
from micropython import const
from sys import exit

class JSON_REPO :
    
    json_repo_file = const("/repo.json")
    
    def __init__(self) :
        try :
            # Read file into cache
            self.read_cache()
        except OSError :
            # file does not exist populate with default values.
            self._repo_cache = {"temp": 0.0, "error": 0, "feeder": 0, "count": 0}
            self.write_cache()

    def write_cache(self) :
        with open(json_repo_file, "w") as f :
            f.write(json.dumps(self._repo_cache))
            f.flush()
            f.close()

    def read_cache(self) :
        with open(json_repo_file, "r") as f :
            self._repo_cache = json.loads(f.read())
            f.close()

    def set_temp(self, value) :
        self._repo_cache ["temp"] = value

    def set_error(self, value) :
        self._repo_cache ["error"] = value

    def set_feeder(self, value) :
        self._repo_cache ["feeder"] = value
        
    def set_count(self, value) :
        self._repo_cache ["count"] = value

    def get_temp(self) :
        return self._repo_cache ["temp"]

    def get_error(self) :
        return self._repo_cache ["error"]

    def get_feeder(self) :
        return self._repo_cache ["feeder"]
    
    def get_count(self) :
        return self._repo_cache ["count"]
    
