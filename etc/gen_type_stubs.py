import inspect
from operator import attrgetter
from textwrap import dedent

from catalyst import api, TradingAlgorithm


def main():
    with open(api.__file__.rstrip('c') + 'i', 'w') as stub:
        # Imports so that Asset et al can be resolved.
        # "from MOD import *" will re-export the imports from the stub, so
        # explicitly importing.
        stub.write(dedent("""\
        import collections
        from catalyst.assets import Asset, Equity, Future
        from catalyst.assets.futures import FutureChain
        from catalyst.finance.asset_restrictions import Restrictions
        from catalyst.finance.cancel_policy import CancelPolicy
        from catalyst.pipeline import Pipeline
        from catalyst.protocol import Order
        from catalyst.utils.events import EventRule
        from catalyst.utils.security_list import SecurityList


        """))

        # Sort to generate consistent stub file:
        for api_func in sorted(TradingAlgorithm.all_api_methods(),
                               key=attrgetter('__name__')):
            sig = inspect._signature_bound_method(inspect.signature(api_func))

            indent = ' ' * 4
            stub.write(dedent('''\
                def {func_name}{func_sig}:
                    """'''.format(func_name=api_func.__name__,
                                  func_sig=sig)))
            stub.write(dedent('{indent}{func_doc}'.format(
                func_doc=api_func.__doc__ or '\n',  # handle None docstring
                indent=indent,
            )))
            stub.write('{indent}"""\n\n'.format(indent=indent))


if __name__ == '__main__':
    main()
