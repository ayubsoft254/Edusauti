from .base import *

# Import development settings by default
try:
    from .development import *
except ImportError:
    pass