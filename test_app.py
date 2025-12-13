import sys
from sys import argv
from time import sleep

from src.Socket_Singleton import MultipleSingletonsError, Socket_Singleton

# This file is used for the test cases in test.py and for manual
# debugging / testing, primarily as a subprocess helper.
# Functions defined here are not all neccessarily invoked by tests.py


def default(port=None):
    # Modify argv in-place to remove "default" and port, keeping only args to send
    # This works because Socket_Singleton uses 'from sys import argv', which is a reference
    # to the same list object, so modifying it in-place updates the reference

    # Calculate what to keep: everything after "default" and port (if present)
    if len(sys.argv) > 1 and sys.argv[1] == "default":
        if port is not None and len(sys.argv) > 2:
            # Remove "default" (index 1) and port (index 2), keep rest
            # Structure: ["test_app.py", "default", port, ...args]
            # Result: ["test_app.py", ...args]
            sys.argv[1:] = sys.argv[3:]
        else:
            # Remove just "default", keep rest
            # Structure: ["test_app.py", "default", ...args]
            # Result: ["test_app.py", ...args]
            sys.argv[1:] = sys.argv[2:]

    # Create singleton - it will read the modified argv[1:]
    try:
        if port is not None:
            Socket_Singleton(port=port)
        else:
            Socket_Singleton()
    finally:
        # Note: We don't restore argv here because the modification is intentional
        # and needed for _create_client() to send the correct arguments
        pass

    print("Singleton locked")


def timeout(seconds, port):
    Socket_Singleton(timeout=seconds, port=port)


def callback(args_tuple):
    print(" ".join(args_tuple))


def trace(seconds):
    # Manual testing helper - blocks thread on purpose
    app = Socket_Singleton()
    print("Singleton locked")
    app.trace(callback)
    sleep(seconds)


def no_strict(port=None):
    try:
        if port is not None:
            Socket_Singleton(port=port, strict=False)
        else:
            Socket_Singleton(strict=False)
        print("Singleton locked")

    except MultipleSingletonsError:
        print("MultipleSingletonsError")


def release(seconds, port):
    app = Socket_Singleton(port=port)
    app.release()
    sleep(seconds)


def verbose_host(port, wait_seconds=1):
    """Create a verbose host with a bad callback that raises exceptions.

    Args:
        port: Port to bind to
        wait_seconds: How long to wait for client connections before exiting
    """

    def bad_callback(args_tuple):
        raise ValueError("Intentional test exception")

    app = Socket_Singleton(port=port, verbose=True)
    app.trace(bad_callback)
    print("Host ready")
    # Keep running momentarily to receive client connections
    sleep(wait_seconds)


def context():
    with Socket_Singleton():
        print("Singleton locked")


def no_client(port=None):
    # Modify argv in-place to remove "no_client" and port, keeping only args to send
    # (Even though client=False means they won't be sent, we still filter for consistency)
    if len(sys.argv) > 1 and sys.argv[1] == "no_client":
        if port is not None and len(sys.argv) > 2:
            # Remove "no_client" (index 1) and port (index 2), keep rest
            sys.argv[1:] = sys.argv[3:]
        else:
            # Remove just "no_client", keep rest
            sys.argv[1:] = sys.argv[2:]

    # Create singleton with client=False
    if port is not None:
        Socket_Singleton(port=port, client=False)
    else:
        Socket_Singleton(client=False)


def max_clients():
    app = Socket_Singleton(max_clients=3)
    app.trace(callback)
    input()


def main():
    if len(argv) < 2:
        print("Missing required argument. ex: default")
        return

    command = argv[1]

    if command == "default":
        # First arg after "default" can be port, rest are arguments to send
        if len(argv) > 2:
            try:
                port = int(argv[2])
                default(port=port)
            except ValueError:
                # Not a port number, treat all as arguments to send (no port specified)
                default()
        else:
            default()
    elif command == "timeout":
        seconds = int(argv[2]) if len(argv) > 2 else 2
        port = int(argv[3]) if len(argv) > 3 else 1338
        timeout(seconds, port)
    elif command == "release":
        seconds = int(argv[2]) if len(argv) > 2 else 2
        port = int(argv[3]) if len(argv) > 3 else 1338
        release(seconds, port)
    elif command == "no_strict":
        # First arg after "no_strict" can be port
        if len(argv) > 2:
            try:
                port = int(argv[2])
                no_strict(port=port)
            except ValueError:
                no_strict()
        else:
            no_strict()
    elif command == "no_client":
        # First arg after "no_client" can be port, rest are arguments (won't be sent due to client=False)
        if len(argv) > 2:
            try:
                port = int(argv[2])
                no_client(port=port)
            except ValueError:
                no_client()
        else:
            no_client()
    elif command == "context":
        context()
    elif command == "trace":
        seconds = int(argv[2]) if len(argv) > 2 else 1
        trace(seconds)
    elif command == "max_clients":
        max_clients()
    elif command == "verbose_host":
        port = int(argv[2]) if len(argv) > 2 else 1337
        wait_seconds = int(argv[3]) if len(argv) > 3 else 1
        verbose_host(port, wait_seconds)


if __name__ == "__main__":
    main()
