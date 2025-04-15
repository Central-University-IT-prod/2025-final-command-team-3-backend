from enum import Enum

class MovieStatus(str, Enum):
    WILL_WATCH = "will_watch"
    WATCHED = "watched"
    DROPPED = "dropped"