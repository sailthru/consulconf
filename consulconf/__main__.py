"""
Convert a directory into an executable
"""
from consulconf.main import build_arg_parser, main


def go():
    NS = build_arg_parser().parse_args()
    main(NS)

if __name__ == '__main__':
    go()
