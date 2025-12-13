import errno
from socket import socket
from sys import argv
from threading import Thread, Timer

_WSAEADDRINUSE = 10048


class Socket_Singleton:
    """
    Enforces a single instance of a Python application using socket binding.

    The first process to successfully bind to the specified port becomes the host
    and collects arguments from subsequent client processes. Client processes
    either exit immediately or raise an exception depending on configuration.

    Args:
        address: IP address to bind to. Defaults to "127.0.0.1" (localhost).
            Useful for containers, VMs, and multi-homed environments.
        port: Port number for the socket listener. Defaults to 1337.
            Prefer using ports in the range 49152-65535 (ephemeral ports).
        timeout: Duration in seconds to hold the socket. Defaults to 0 (no timeout).
            If > 0, countdown starts immediately after successful binding.
        client: If False, client processes won't send arguments to the host. Defaults to True.
        strict: If False, raises MultipleSingletonsError instead of SystemExit. Defaults to True.
        release_threshold: Release the port after this many client connections.
            Defaults to 0 (never release). Once released, no new connections accepted.
        max_clients: Stop processing arguments after this many client connections.
            Defaults to 0 (process all arguments). Connections still accepted but
            arguments ignored. Useful for rudimentary rate limiting/throttling..
        verbose: If True, print warnings for connection failures, encoding errors,
            and observer exceptions. Defaults to False (silent operation).
        secret: Optional secret string for client verification. If provided, clients
            must send this secret before their arguments. Defaults to None (no verification).
            Useful for preventing unauthorized applications from injecting arguments.
    """

    def __init__(
        self,
        address: str = "127.0.0.1",
        port: int = 1337,
        timeout: int = 0,
        client: bool = True,
        strict: bool = True,
        release_threshold: int = 0,
        max_clients: int = 0,
        verbose: bool = False,
        secret: str = None,
    ):
        """
        Initialize the singleton instance.

        Uses exception handling to determine if this instance becomes a host
        (first process, binds successfully) or a client (port already in use).

        Host instances:
            - Start a daemon thread listening for client connections
            - Collect and process arguments from client processes
            - Optionally release after timeout or client threshold

        Client instances:
            - Send arguments to existing host (if client=True)
            - Exit immediately (if strict=True) or raise MultipleSingletonsError
            - Never become a host or start a server thread
        """

        self.address = str(address)
        self.port = int(port)
        self.timeout = int(timeout)
        self.client = bool(client)
        self.strict = bool(strict)
        self.release_threshold = int(release_threshold)
        self.max_clients = int(max_clients)
        self.verbose = bool(verbose)
        self.secret = str(secret) if secret is not None else None

        if not (0 <= self.port <= 65535):
            raise ValueError("port must be between 0 and 65535 (inclusive)")
        if self.timeout < 0:
            raise ValueError("timeout must be greater than or equal to 0")
        if self.release_threshold < 0:
            raise ValueError("release_threshold must be greater than or equal to 0")
        if self.max_clients < 0:
            raise ValueError("max_clients must be greater than or equal to 0")

        # Store arguments as tuples - each tuple represents one client's complete argument set
        # Internally, this functions as a queue. See self.arguments() for external access.
        # Note: Host's own arguments are not stored here - only arguments from client processes.
        self._arguments = []
        self._observers = {}
        self._clients = 0
        self._listening = False
        self._thread = None
        self._timer = None
        self._sock = socket()

        try:
            self._sock.bind((self.address, self.port))

        except OSError as err:
            if err.errno not in (errno.EADDRINUSE, _WSAEADDRINUSE):
                raise

            if self.client:
                self._create_client()

            if self.strict:
                raise SystemExit
            else:
                raise MultipleSingletonsError(
                    "\nApplication is already bound & listening "
                    f"@ {self.address} on port {self.port}. Multiple "
                    f"instances are disallowed in the current context."
                ) from None

        else:
            self._listening = True
            self._thread = Thread(target=self._create_server, daemon=True)
            self._timer = Timer(self.timeout, self.release)
            self._thread.start()

            if self.timeout > 0:
                self._timer.start()

    def __str__(self):
        """Human-readable string representation."""

        return f"Socket_Singleton(address={self.address!r}, port={self.port})"

    def __repr__(self):
        """
        Unambiguous string representation for developers.

        Includes all configuration parameters and current state for debugging.
        """

        return (
            f"Socket_Singleton("
            f"address={self.address!r}, "
            f"port={self.port}, "
            f"timeout={self.timeout}, "
            f"client={self.client}, "
            f"strict={self.strict}, "
            f"release_threshold={self.release_threshold}, "
            f"max_clients={self.max_clients}, "
            f"verbose={self.verbose}, "
            f"secret={'***' if self.secret else None}, "
            f"observers={len(self._observers)}, "
            f"clients={self._clients}, "
            f"listening={getattr(self, '_listening', False)})"
        )

    def __enter__(self):
        """Context manager protocol - returns self for use in 'with' statements."""

        return self

    def __exit__(self, ex_type, ex_value, ex_traceback):
        """
        Context manager cleanup - releases the port and allows exceptions to propagate.

        Returns False to allow exceptions to propagate (standard context manager behavior)
        """

        self.release()
        return False

    def _create_server(self):
        """
        Server thread that listens for client connections and processes arguments.

        Continuously accepts connections from client processes, receives their
        arguments, and publishes them to registered observers. Runs in a daemon
        thread until release() is called or thresholds are reached.
        """

        with self._sock as sock:
            sock.listen()
            while self._listening:
                connection, _ = sock.accept()
                with connection:
                    self._clients += 1

                    # We can release the port after a certain number of clients have connected.
                    # Singleton will be unlocked:
                    if (self.release_threshold) and (self._clients >= self.release_threshold):
                        self.release()
                        break  # Exit immediately - release() sets _listening=False but accept() blocks

                    # We can stop processing arguments after a certain number of clients have connected.
                    # Singleton will remain locked:
                    within_max_clients = (not self.max_clients) or (
                        self._clients <= self.max_clients
                    )
                    has_observers = len(self._observers) > 0
                    should_process_args = within_max_clients and has_observers

                    data = connection.recv(1024)
                    if should_process_args:
                        # Defensively decode:
                        try:
                            # Receive all arguments from this client as a single package
                            # Use null byte (\x00) as delimiter to avoid issues with newlines
                            decoded = data.decode("utf-8", errors="replace").rstrip("\x00")
                            # Split by null byte to get individual args
                            parts = decoded.split("\x00")

                            # If secret is required, verify it
                            if self.secret is not None:
                                if not parts or parts[0] != self.secret:
                                    # Secret mismatch - silently ignore this connection
                                    if self.verbose:
                                        print(
                                            f"Socket_Singleton: Client verification failed "
                                            f"on port {self.port}, ignoring connection"
                                        )
                                    continue
                                # Remove secret from parts, keep only arguments
                                parts = parts[1:]

                            # Filter out empty strings
                            args = tuple(arg for arg in parts if arg)
                            if args:
                                self._append_args(args)
                        except (UnicodeDecodeError, AttributeError):
                            # Invalid data received - skip this client's arguments
                            if self.verbose:
                                print(
                                    f"Socket_Singleton: Failed to decode data from client "
                                    f"on port {self.port}, skipping arguments"
                                )
                            pass

    def _create_client(self):
        """
        Client behavior when port is already bound.

        Connects to the existing host server and sends this process's command-line
        arguments. Called automatically when binding fails due to port already in use.
        """

        try:
            with self._sock as sock:
                sock.connect((self.address, self.port))
                # Build message: secret (if required) + arguments, joined by null bytes
                # Use null byte (\x00) as delimiter to avoid issues with newlines
                parts = []
                if self.secret is not None:
                    parts.append(self.secret)
                parts.extend(argv[1:])
                # Empty if no arguments (just a null byte terminator)
                message = "\x00".join(parts) + "\x00"
                sock.send(message.encode("utf-8"))
        except (OSError, ConnectionRefusedError):
            # Connection failures can occur due to race conditions (especially with
            # rapid successive launches), port conflicts with other applications,
            # erroneous manual release() calls, timeouts, etc.
            #
            # Some uncommon but possible scenarios:
            # 1. Host releases port between our bind() attempt and connect() attempt
            # 2. Host timeout expires between bind() and connect()
            # 3. Host process crashes/killed before we can connect
            # 4. Port in use by non-singleton application
            #
            # Silently handle these failures - the client will exit/raise exception
            # as expected regardless. The important singleton enforcement behavior
            # (preventing multiple instances) is already achieved by the failed bind().
            if self.verbose:
                print(
                    f"Socket_Singleton: Failed to connect to existing instance "
                    f"on {self.address}:{self.port} (port may have been released)"
                )
            pass

    def _append_args(self, args):
        """
        Append a complete argument set from a client to the queue and notify observers.
        """

        self._arguments.append(args)
        self._update_observers()

    def _update_observers(self):
        """
        Publish the most recent argument set to all registered observers.

        Implements the observer pattern - notifies all registered callbacks with
        the latest argument set (as a tuple) and their stored args/kwargs.
        Arguments are consumed (popped) as they're published.

        Each observer receives a tuple containing all arguments from a single
        client process, allowing them to be processed in the correct context.
        """
        if not self._arguments or not self._observers:
            return

        args = self._arguments.pop()
        # Copy observers dict to avoid RuntimeError if untrace() is called during iteration.
        # The list() creates a snapshot of (observer, (args, kwargs)) tuples at this moment.
        # This is safe because: observer callables are immutable references, args are tuples
        # (immutable), and kwargs dicts are only read (not modified) during callback execution.
        for observer, (observer_args, observer_kwargs) in list(self._observers.items()):
            try:
                # Pass the complete argument tuple as the first parameter
                observer(args, *observer_args, **observer_kwargs)
            except Exception as exc:
                # Observer exceptions shouldn't crash the server thread
                if self.verbose:
                    # fmt: off
                    observer_name = (
                        observer.__name__
                        if hasattr(observer, "__name__")
                        else observer
                    )
                    # fmt: on
                    print(
                        f"Socket_Singleton: Observer {observer_name} "
                        f"raised exception: {type(exc).__name__}: {exc}"
                    )
                pass

    def trace(self, observer, *args, **kwargs):
        """
        Register an observer callback to receive arguments from client processes.

        When arguments arrive from client processes, the observer will be called
        with a tuple containing all arguments from that client as the first parameter,
        followed by any args/kwargs provided here.

        Args:
            observer: Callable to invoke when arguments arrive. Receives a tuple
                of arguments from a single client process as the first parameter.
            *args: Additional positional arguments to pass to observer
            **kwargs: Additional keyword arguments to pass to observer

        Example:
            def my_callback(args_tuple, prefix, suffix="<<<"):
                # args_tuple is a tuple like ("foo", "bar", "baz")
                print(f"{prefix}{' '.join(args_tuple)}{suffix}")
                do_a_thing(args_tuple)

            app.trace(my_callback, ">>> ", suffix=" - Received")
        """

        self._observers[observer] = (args, kwargs)

    def untrace(self, observer):
        """Detach (unsubscribe) a callback. Does nothing if the observer is not registered."""

        self._observers.pop(observer, None)

    def release(self):
        """
        Release the port, allowing other instances to bind.

        Stops the server thread, cancels any active timeout timer, clears all
        registered observers, and releases the socket port. Safe to call multiple
        times (idempotent).

        Note:
            After release(), this instance can no longer accept client connections.
            Use the context manager protocol for automatic cleanup.
        """
        if not hasattr(self, "_listening") or not self._listening:
            return

        self._listening = False

        if hasattr(self, "_timer"):
            self._timer.cancel()

        # No new arguments will arrive after release
        self._observers.clear()

        # Unblock accept() in server thread
        try:
            dummy_socket = socket()
            with dummy_socket as dummy:
                dummy.connect((self.address, self.port))
                dummy.send("".encode("utf-8"))
        except (OSError, ConnectionRefusedError):
            # Socket may already be closed or port released - this is fine
            # The server thread will exit due to _listening = False above
            # pass here for idempotency
            pass

    @property
    def arguments(self):
        """
        Read-only snapshot of arguments received from client processes.

        Returns a tuple of tuples, where each inner tuple represents the complete
        argument set from a single client process. Note that arguments are typically
        consumed immediately by registered observers, so this will often be empty.
        Useful for debugging or inspecting pending arguments.

        Example:
            If two clients sent ("foo", "bar") and ("baz",), this returns:
            (("foo", "bar"), ("baz",))
        """
        return tuple(self._arguments)

    @property
    def clients(self):
        """
        Number of client processes that have connected since this singleton was created.

        Useful for monitoring singleton usage, debugging, or implementing
        custom logic based on connection count.
        """
        return self._clients


class MultipleSingletonsError(Exception):
    """
    Raised when attempting to create a singleton instance but one already exists.

    This exception is only raised when strict=False. When strict=True (default),
    SystemExit is raised instead.
    """
