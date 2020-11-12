from src.Socket_Singleton import Socket_Singleton, MultipleSingletonsError
from sys import argv


# This file is used for the test cases in test.py and for manual debugging / testing
# Functions defined here are not *all* neccessarily invoked by test.py


def default():
    Socket_Singleton()
    print("I am the singleton")


def cb(arg):
    print(arg)


def trace():
    app = Socket_Singleton()
    print("I am the singleton")
    app.trace(cb)
    input()


def different_port():
    Socket_Singleton(port=400)
    print("I am the singleton")


def no_client():
    Socket_Singleton(client=False)


def context():
    with Socket_Singleton():
        print("I am the singleton")


def context_no_strict():
    try:
        with Socket_Singleton(strict=False):
            print("I am the singleton")
    except MultipleSingletonsError:
        print("MultipleSingletonsError")


def no_strict():
    try:
        Socket_Singleton(strict=False)
        print("I am the singleton")

    except MultipleSingletonsError:
        print("MultipleSingletonsError")


def max_clients():
    app = Socket_Singleton(max_clients=3)
    app.trace(cb)
    input()


def main():
    if not argv[1]:
        print("Missing required argument. ex: default")

    if argv[1] == "default":
        default()

    if argv[1] == "trace":
        trace()

    if argv[1] == "different_port":
        different_port()

    if argv[1] == "no_client":
        no_client()

    if argv[1] == "context":
        context()

    if argv[1] == "context_no_strict":
        context_no_strict()

    if argv[1] == "no_strict":
        no_strict()

    if argv[1] == "max_clients":
        max_clients()


if __name__ == "__main__":
    main()
