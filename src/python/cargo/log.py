"""
cargo/log.py

Application-wide logging configuration.

@author: Bryan Silverthorn <bcs@cargo-cult.org>
"""

import os.path
import sys
import curses
import logging
import datetime

from itertools import count
from logging import (
    INFO,
    DEBUG,
    ERROR,
    NOTSET,
    Filter,
    Logger,
    WARNING,
    CRITICAL,
    Formatter,
    FileHandler,
    StreamHandler,
    )
from cargo.flags import (
    Flag,
    FlagSet,
    )

class DefaultLogger(logging.getLoggerClass()):
    """
    Simple standard logging.
    """

    def __init__(self, name, level = logging.NOTSET):
        """
        Initialize.
        """

        if name == "__main__":
            name = "main"

        Logger.__init__(self, name, level)

    def detail(self, message, *args, **kwargs):
        """
        Write a log message at the DETAIL level.
        """

        return self.log(logging.DETAIL, *args, **kwargs)

    def note(self, message, *args, **kwargs):
        """
        Write a log message at the NOTE level.
        """

        return self.log(logging.NOTE, *args, **kwargs)

# use our logger class by default
logging.setLoggerClass(DefaultLogger)

def get_logger(name, level = logging.WARNING):
    """
    Get or create a logger.
    """

    logger = logging.getLogger(name)

    logger.setLevel(level)

    return logger

log = get_logger(__name__)

class Flags(FlagSet):
    """
    Module-level flags.
    """

    flag_set_title = "Logging"

#    log_to_console_flag = \
#        Flag(
#            "--log-to-console",
#            action = "store_true",
#            help = "force console-style logging to stdout [%default]",
#            )
#    log_to_file_flag = \
#        Flag(
#            "--log-to-file",
#            action = "store_true",
#            help = "force logging to script.log.N",
#            )
    log_file_prefix_flag = \
        Flag(
            "--log-file-prefix",
            default = "script.log",
            metavar = "PREFIX",
            help = "file logging will write to PREFIX.N [script.log]",
            )
    verbosity_flag = \
        Flag(
            "-v",
            "--verbosity",
            default = logging.INFO,
            metavar = "N",
            help = "log messages of at least level N [%default]",
            )

flags = Flags.given

class TTY_ConciseFormatter(Formatter):
    """
    A concise log formatter for console output.
    """

    _DATE_FORMAT = "%y%m%d%H%M%S"

    def __init__(self, stream = None):
        """
        Construct this formatter.
        """

        # construct the format string
        format = "%(message)s"

        # initialize this formatter
        Formatter.__init__(self, format, TTY_ConciseFormatter._DATE_FORMAT)

class TTY_VerboseFormatter(Formatter):
    """
    A verbose log formatter for console output.
    """

    _DATE_FORMAT = "%y%m%d%H%M%S"
    _TIME_COLOR = "\x1b[34m"
    _NAME_COLOR = "\x1b[35m"
    _LEVEL_COLOR = "\x1b[33m"
    _COLOR_END = "\x1b[00m"

    def __init__(self, stream = None):
        """
        Construct this formatter.

        Provides colored output if the stream parameter is specified and is an acceptable TTY.
        We print hardwired escape sequences, which will probably break in some circumstances;
        for this unfortunate shortcoming, we apologize.
        """

        # select and construct format string
        format = None

        if stream and hasattr(stream, "isatty") and stream.isatty():
            curses.setupterm()

            # FIXME do nice block formatting, increasing column sizes as necessary
            if curses.tigetnum("colors") > 2:
                format = \
                    "%s%%(name)s%s - %s%%(levelname)s%s - %%(message)s" % (
                        TTY_VerboseFormatter._NAME_COLOR,
                        TTY_VerboseFormatter._COLOR_END,
                        TTY_VerboseFormatter._LEVEL_COLOR,
                        TTY_VerboseFormatter._COLOR_END)

        if format is None:
            format = "%(name)s - %(levelname)s - %(message)s"

        # initialize this formatter
        Formatter.__init__(self, format, TTY_VerboseFormatter._DATE_FORMAT)

class VerboseFileFormatter(Formatter):
    """
    A verbose log formatter for file output.
    """

    _FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    _DATE_FORMAT = "%y%m%d%H%M%S"

    def __init__(self):
        """
        Construct this formatter.
        """

        Formatter.__init__(self, VerboseFileFormatter._FORMAT, VerboseFileFormatter._DATE_FORMAT)

class OpaqueFilter(Filter):
    """
    Exclude all records.
    """

    def __init__(self):
        """
        Initialize.
        """

        Filter.__init__(self)

    def filter(self, record):
        """
        Allow no records.
        """

        return False

class ExactExcludeFilter(Filter):
    """
    Exclude records with a specific name.
    """

    def __init__(self, exclude):
        """
        Initialize this filter.
        """

        # members
        self.__exclude = exclude

        # base
        Filter.__init__(self)

    def filter(self, record):
        """
        Allow all records save those with the excluded name.
        """

        if record.name != self.__exclude:
            return True
        else:
            return False

def enable_console(level = logging.NOTSET, verbose = True):
    """
    Enable typical logging to the console.
    """

    handler = StreamHandler(sys.stdout)

    if verbose:
        formatter = TTY_VerboseFormatter
    else:
        formatter = TTY_ConciseFormatter

    handler.setFormatter(formatter(sys.stdout))
    handler.setLevel(level)

    logging.root.addHandler(handler)

    log.debug("enabled logging to stdout at %s", datetime.datetime.today().isoformat())

    return handler

def enable_disk(prefix = None, level = logging.NOTSET):
    """
    Enable typical logging to disk.
    """

    # generate an unused log file path
    if prefix is None:
        #prefix = flags.log_file_prefix
        prefix = "script.log" # FIXME use the flag

    for i in count():
        path = "%s.%i" % (prefix, i)

        if not os.path.lexists(path):
            break

    # set up logging
    handler = FileHandler(path)

    handler.setFormatter(VerboseFileFormatter())
    handler.setLevel(level)

    logging.root.addHandler(handler)

    log.debug("enabled logging to %s at %s", path, datetime.datetime.today().isoformat())

    return handler

# enable logging by default
def defaults():
    # by default, be moderately verbose
    logging.root.setLevel(logging.NOTSET) # FIXME should use flag

    # add a few more levels
    logging.DETAIL = 15
    logging.NOTE = 25

    logging.addLevelName(logging.DETAIL, "DETAIL")
    logging.addLevelName(logging.NOTE, "NOTE")

    # default setup (FIXME which is silly: should enable the disk log via flag or environment)
    if sys.stdout.isatty():
        enable_console()
    else:
        enable_disk()

defaults()

