"""Topic Tagger: tag survey variables by topic with a language model.

Use it from the command line (``topic-tagger tag …``) or from Python::

    from topic_tagger import tag
    results = tag(["Do you smoke?"], "my-scheme.toml")

The names in ``__all__`` are the public Python API; every other module is internal.
"""

from topic_tagger.api import RemoteModelError, Result, Results, Tag, Tagger, classify, tag
from topic_tagger.providers import OptionLimitError, ProviderError
from topic_tagger.scheme import Scheme, SchemeError, load_scheme, parse_scheme
from topic_tagger.variables import Variable

__version__ = "0.1.0"

__all__ = [
    "OptionLimitError",
    "ProviderError",
    "RemoteModelError",
    "Result",
    "Results",
    "Scheme",
    "SchemeError",
    "Tag",
    "Tagger",
    "Variable",
    "classify",
    "load_scheme",
    "parse_scheme",
    "tag",
]
