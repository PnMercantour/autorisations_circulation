
import sys
import argparse

from IPython import embed

from autcircu.db.models import ( # noqa
    RequestMotive, RestrictedPlace, LetterTemplate,
    AuthRequest, db
)
from autcircu.db.utils import (
    start_app_context, init_db, delete_db, create_test_user, populate_db
)

from autcircu.conf import app  # noqa

from pypnusershub.db.models import (  # noqa
    User, Application, AppUser, ApplicationRight, UserApplicationRight
)


def call_init_db(args):
    print('Initialize DB')
    init_db(app)
    print('Done')
    if args.populate:
        call_populate_db(args)


def call_delete_db(args):
    if not args.yes:
        confirm = input("This will delete all the content of "
                        " the db. Are you sure ? [N/y] ")
    else:
        confirm = "y"

    if confirm != "y":
        print('Abort')
        sys.exit(0)

    print('Deleting schema')
    delete_db(app)
    print('Done')


def reset_db(args):
    call_delete_db(args)
    call_init_db(args)


def call_populate_db(args):
    print('Populating db')
    start_app_context()
    for request in populate_db():
        print('.', end='')
    print('\nDone')


def shell(args):
    start_app_context()
    session = db.session  # noqa
    embed()


def call_create_test_user(args):
    print('Creating user')
    start_app_context()
    try:
        create_test_user(
            app,
            username=args.username,
            password=args.password,
            access_rights=args.access_rights
        )
    except ValueError as e:
        sys.exit(e)
    print('Done')


def make_cmd_parser():
    """ Create a CMD parser with subcommands """
    parser = argparse.ArgumentParser('python -m autcircu')

    parser.set_defaults(func=lambda x: parser.print_usage(sys.stderr))

    subparsers = parser.add_subparsers()

    parser_init_schema = subparsers.add_parser('populate_db')
    parser_init_schema.set_defaults(func=call_populate_db)

    parser_init_db = subparsers.add_parser('init_db')
    parser_init_db.set_defaults(func=call_init_db)
    parser_init_db.add_argument('--populate', action='store_true',
                                help='Populate the db with legacy auth')
    parser_init_db.add_argument('--yes', action='store_true',
                                help='Skip the confirmation')

    parser_delete_db = subparsers.add_parser('delete_db')
    parser_delete_db.set_defaults(func=call_delete_db)

    parser_reset_db = subparsers.add_parser('reset_db')
    parser_reset_db.set_defaults(func=reset_db)
    parser_reset_db.add_argument('--populate', action='store_true',
                                 help='Populate the db with legacy auth')
    parser_reset_db.add_argument('--yes', action='store_true',
                                 help='Skip the confirmation')

    parser_create_user = subparsers.add_parser('create_test_user')
    parser_create_user.set_defaults(func=call_create_test_user)
    parser_create_user.add_argument('username', help='The user\'s login')
    parser_create_user.add_argument('password', help='The user\'s password')

    def access_rights(x):
        msg = "Access rights must be a number between 0 and 6"
        try:
            x = int(x)
        except (ValueError, TypeError):
            raise argparse.ArgumentTypeError(msg)
        if not 0 <= x <= 6:
            raise argparse.ArgumentTypeError(msg)
        return x

    parser_create_user.add_argument('--access-rights', type=access_rights,
                                    help='The level of rights of this user',
                                    default=6)

    parser_shell = subparsers.add_parser('shell')
    parser_shell.set_defaults(func=shell)

    return parser


if __name__ == '__main__':
    parser = make_cmd_parser()
    args = parser.parse_args()
    args.func(args)
