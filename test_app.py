from src.Socket_Singleton import Socket_Singleton, MultipleSingletonsError
from sys import argv


def defaults():
    app = Socket_Singleton()
    print("I am the singleton")


def different_port():
    app = Socket_Singleton(port=1338)
    print("I am the singleton")


def no_client():
    app = Socket_Singleton(client=False)


def context():
    with Socket_Singleton() as ss:
        print("I am the singleton")


def context_no_strict():
    try:
        with Socket_Singleton(strict=False):
            print("I am the singleton")
    except MultipleSingletonsError as err:
        print("MultipleSingletonsError")


def no_strict():
    try:
        app = Socket_Singleton(strict=False)

    except MultipleSingletonsError as err:
        print("MultipleSingletonsError")


if argv[1] == "defaults":
    defaults()

if argv[1] == "context":
    context()

if argv[1] == "different_port":
    different_port()

if argv[1] == "no_client":
    no_client()

if argv[1] == "no_strict":
    no_strict()

if argv[1] == "context_no_strict":
    context_no_strict()
