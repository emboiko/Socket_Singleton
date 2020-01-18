from sys import argv
from socket import socket
from threading import Thread


class Socket_Singleton:
    """
        Allows a single instance of a python application to run at a time.
        First one that binds to the specified port wins, and will collect
        the arguments from subsequent calls to the application. 

        address: (string) An IP address - Localhost by default.

        port: (int) An available port we can simulate a mutex with. 
        1337 by default, though prefer the use of range(49152, 65536).
        Doing this dynamically would be better, and will be implemented soon. 

        client: (bool) If we don't care about collecting arguments from subsequent
        calls to the application via trace(), this can be specified False.
        True by default.

        strict: (bool) This controls how strongly we enforce our singleton status.
        If set to False, we'll raise a specific exception instead of a hard,
        immediate raise of SystemExit (MultipleSingletonsError).
    """
    
    def __init__(
        self,
        address:str="127.0.0.1",
        port:int=1337,
        client:bool=True,
        strict:bool=True
        ):
        """
            Initializer uses exception handler control flow to determine
            what kind of object it's going to be. Either we can bind to 
            the port, or we can connect to it, thus we are either a host
            or a client. 
            
            Host (first process) will live on as a threaded daemon listening
            for connections & data (arguments) from subsequent clients. 
            
            Clients are single threaded, and based on constructor arguments 
            will either:

                -Raise a custom exception if we're not in strict mode
                -Silently & immediately die.
                -Immediately die after sending their arguments to the host.
        """

        self.address = address
        self.port = port
        self.arguments = [arg for arg in argv[1:]]
    
        self._client = client
        self._strict = strict
        self._observers = dict()

        self._sock = socket()
        try:
            self._sock.bind((self.address, self.port))
        except OSError as err:
            if err.args[0] != 10048:
                raise
            if self._client:
                self._create_client()
            if self._strict:
                raise SystemExit
            else:
                raise MultipleSingletonsError(
                    "\nApplication is already bound & listening "\
                    f"@ {self.address} on port {self.port}. Multiple "\
                    f"instances are disallowed in the current context."
                ) from None
        else:
            self._running = True
            self._thread = Thread(target=self._create_server, daemon=True)
            self._thread.start()


    def __str__(self):
        """Minimal identification"""

        return "Socket Singleton "\
        f"@ {self.address} on port {self.port}"


    def __repr__(self):
        """Verbose identification, all kwargs + memory address"""

        return "Socket Singleton "\
        f"@ {self.address} on port {self.port}\n"\
        f"@ {hex(id(self))} "\
        f"w/ {len(self._observers.keys())} registered observer(s)\n"\
        f"client={self._client}, strict={self._strict}"


    def __enter__(self):
        """
            Get more control with a context manager => Equally clean
            interface without calls to close()
        """

        return self


    def __exit__(self, ex_type, ex_value, ex_traceback):
        """Cleanup self._thread & allow any exceptions to bubble up"""

        self.close()
        return False


    def _create_server(self):
        """
            If the socket bound successfully, a threaded server will
            continuously listen for & receive connections & data from
            potential clients. Arguments passed from clients are 
            collected into self.arguments
        """

        with self._sock as s:
            s.listen()
            while self._running:
                connection, address = s.accept()
                with connection:
                    data = connection.recv(1024)
                    args = data.decode().split("\n")
                    [self._append_args(arg) for arg in args if arg]


    def _create_client(self):
        """
            If the server can't be created, it is assumed one already
            exists. A non-threaded client sends its arguments to the 
            existing server.
        """

        with self._sock as s:
            s.connect(("127.0.0.1", self.port))
            for arg in argv[1:]:
                s.send(arg.encode())
                s.send("\n".encode())


    def _append_args(self, arg):
        """Pseudo-setter for self._arguments"""

        self.arguments.append(arg)
        self._update_observers()


    def _update_observers(self):
        """Call all observers with their respective args, kwargs"""

        [
            observer(self.arguments, *args[0], **args[1])
            for observer, args 
            in self._observers.items()
        ]


    def trace(self, observer, *args, **kwargs):
        """Attach a callback w/ arbitrary # of args & kwargs"""

        self._observers[observer] = args, kwargs


    def untrace(self, observer):
        """Detach a callback"""

        self._observers.pop(observer)


    def close(self):
        """
            If we want to prematurely release the port:
            Create a dummy socket and send a falsy string to the server.
            Artificially satisfies the blocking call to accept() in
            self._create_server()
        """
        
        self._running = False
        dummy_socket = socket()
        with dummy_socket as ds:
            ds.connect(("127.0.0.1", self.port))
            ds.send("".encode())


class MultipleSingletonsError(Exception):
    """
        An existing copy of our application has already bound to the port
        & opened a listening server.
    """
