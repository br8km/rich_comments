from pathlib import Path


class Config:
    """Config."""

    private = False

    dir_app = Path(__file__).parent

    dir_out = dir_app / "out"
    dir_debug = dir_out / "debug"
    dir_log = dir_out / "log"
    dir_tmp = dir_out / "tmp"

    @property
    def dir_dat(self) -> Path:
        """Get dir_dat."""
        dir_app = self.dir_app / "dat"
        if self.private:
            return dir_app / "private"
        return dir_app