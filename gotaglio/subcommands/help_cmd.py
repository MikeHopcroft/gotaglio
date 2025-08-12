import argparse

def show_help(parser, args):
    subcommand = args.subcommand
    if subcommand:
        # Find the subparsers action
        subparsers_action = next(
            action for action in parser._actions if isinstance(action, argparse._SubParsersAction)
        )
        
        # Find the subcommand parser
        subcommand_parser = subparsers_action.choices.get(subcommand)
        
        if subcommand_parser:
            subcommand_parser.print_help()
        else:
            print(f"No help available for subcommand: {subcommand}")
    else:
        parser.print_help()