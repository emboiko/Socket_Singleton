"""
Test suite for Socket_Singleton.

Tests are organized into separate classes by concern:
- InProcess: Tests that can run in the same process
- SingletonEnforcement: Tests requiring separate processes for singleton behavior
- ArgumentPassing: Tests for argument passing between processes
- Timeouts: Tests for timeout and release functionality
- Thresholds: Tests for max_clients and release_threshold
"""

import socket
import unittest
from subprocess import PIPE, STDOUT, Popen, run
from time import sleep

from src.Socket_Singleton import MultipleSingletonsError, Socket_Singleton


def get_free_port():
    """Find an available port for testing."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def run_test_app(command, wait=True, capture_output=False):
    """
    Run test_app.py with the given command.

    Args:
        command: Full command string to pass to test_app.py (e.g., "default 1337 foo bar")
        wait: If True, wait for process to complete. If False, return Popen object.
        capture_output: If True and wait=False, capture stdout/stderr in Popen.

    Returns:
        CompletedProcess if wait=True, Popen if wait=False
    """
    cmd = f"python test_app.py {command}"

    if wait:
        return run(cmd, shell=True, capture_output=True, text=True)
    else:
        if capture_output:
            return Popen(cmd, shell=True, stdout=PIPE, stderr=STDOUT, text=True)
        else:
            return Popen(cmd, shell=True, stdout=None, stderr=None)


class TestInProcess(unittest.TestCase):
    """Tests that can run in-process without separate processes."""

    def setUp(self):
        """Use a unique port for each test to avoid conflicts."""
        self.port = get_free_port()
        self.app = Socket_Singleton(port=self.port)
        self.traced_args = []

    def tearDown(self):
        """Clean up after each test."""
        self.app.release()
        sleep(0.1)  # Brief pause for port release

    def test_properties(self):
        """Test that properties are accessible and have correct types."""
        self.assertIsInstance(self.app.arguments, tuple)
        self.assertIsInstance(self.app.clients, int)
        self.assertEqual(self.app.clients, 0)

        # Test that arguments property returns tuple of tuples
        args = self.app.arguments
        if args:  # If there are any arguments
            for arg_tuple in args:
                self.assertIsInstance(arg_tuple, tuple)

        # Manually add some arguments (simulates clients sending arguments)
        initial_count = len(self.app._arguments)
        self.app._append_args(("foo", "bar"))
        self.app._append_args(("baz",))

        args = self.app.arguments
        self.assertIsInstance(args, tuple)
        # Should have initial args (if any) plus the 2 we added
        self.assertEqual(len(args), initial_count + 2)
        # Check the last two are what we added
        self.assertEqual(args[-2], ("foo", "bar"))
        self.assertEqual(args[-1], ("baz",))

    def test_trace_untrace(self):
        """Test registering and unregistering observers."""

        def callback(args_tuple):
            self.traced_args.append(args_tuple)

        # Register observer
        self.app.trace(callback)
        self.assertEqual(len(self.app._observers), 1)

        # Register the same observer again (should not raise, just overwrites)
        self.app.trace(callback)
        self.assertEqual(len(self.app._observers), 1)

        # Unregister observer
        self.app.untrace(callback)
        self.assertEqual(len(self.app._observers), 0)

        # Untrace non-existent observer (should not raise)
        self.app.untrace(callback)

    def test_trace_with_stored_args(self):
        """Test trace() with stored args and kwargs."""

        def callback(args_tuple, prefix, suffix="", debug=False):
            result = f"{prefix}{' '.join(args_tuple)}{suffix}"
            if debug:
                result += " [DEBUG]"
            self.traced_args.append(result)

        self.app.trace(callback, ">>> ", suffix=" <<<", debug=True)

        # Simulate receiving arguments (manually trigger)
        self.app._append_args(("foo", "bar", "baz"))

        self.assertEqual(len(self.traced_args), 1)
        self.assertEqual(self.traced_args[0], ">>> foo bar baz <<< [DEBUG]")

    def test_release_idempotency(self):
        """Test that release() can be called multiple times safely."""
        self.app.release()
        self.assertFalse(self.app._listening)

        # Should not raise or cause issues
        self.app.release()
        self.app.release()

    def test_context_manager(self):
        """Test context manager protocol."""
        port = get_free_port()
        with Socket_Singleton(port=port) as app:
            self.assertTrue(app._listening)
            self.assertIsInstance(app, Socket_Singleton)

        # Should be able to bind again
        app2 = Socket_Singleton(port=port)
        self.assertTrue(app2._listening)
        app2.release()

    def test_secret_verification(self):
        """Test that secret parameter prevents unauthorized connections."""
        port = get_free_port()
        secret = "test-secret-123"

        # Create host with secret
        host = Socket_Singleton(port=port, secret=secret)
        received_args = []

        def callback(args_tuple):
            received_args.append(args_tuple)

        host.trace(callback)

        # Test 1: Authorized client (correct secret)
        # We need to manually create a client with the secret
        # Since test_app.py doesn't support secret yet, we'll use a raw socket
        import socket as sock

        # Authorized connection
        client_sock = sock.socket(sock.AF_INET, sock.SOCK_STREAM)
        try:
            client_sock.connect(("127.0.0.1", port))
            # Send secret + arguments (using null byte delimiter)
            message = f"{secret}\x00foo\x00bar\x00"
            client_sock.send(message.encode("utf-8"))
        finally:
            client_sock.close()

        sleep(0.2)  # Give time for processing

        # Should receive arguments
        self.assertEqual(len(received_args), 1)
        self.assertEqual(received_args[0], ("foo", "bar"))

        # Test 2: Unauthorized connection (wrong secret)
        client_sock2 = sock.socket(sock.AF_INET, sock.SOCK_STREAM)
        try:
            client_sock2.connect(("127.0.0.1", port))
            # Send wrong secret + arguments
            message = f"wrong-secret\x00baz\x00qux\x00"
            client_sock2.send(message.encode("utf-8"))
        finally:
            client_sock2.close()

        sleep(0.2)  # Give time for processing

        # Should NOT receive new arguments (secret mismatch)
        self.assertEqual(len(received_args), 1)  # Still only the first one

        # Test 3: Unauthorized connection (no secret)
        client_sock3 = sock.socket(sock.AF_INET, sock.SOCK_STREAM)
        try:
            client_sock3.connect(("127.0.0.1", port))
            # Send arguments without secret
            message = "unauthorized\x00args\x00"
            client_sock3.send(message.encode("utf-8"))
        finally:
            client_sock3.close()

        sleep(0.2)  # Give time for processing

        # Should NOT receive new arguments (no secret)
        self.assertEqual(len(received_args), 1)  # Still only the first one

        host.release()

    def test_arguments_with_newlines(self):
        """Test that arguments containing newlines are handled correctly."""
        port = get_free_port()
        host = Socket_Singleton(port=port)
        received_args = []

        def callback(args_tuple):
            received_args.append(args_tuple)

        host.trace(callback)

        # Send arguments that contain newlines using raw socket
        # This simulates an edge case where an argument might contain a newline
        import socket as sock

        client_sock = sock.socket(sock.AF_INET, sock.SOCK_STREAM)
        try:
            client_sock.connect(("127.0.0.1", port))
            # Send arguments with newlines - using null byte delimiter, newlines are preserved
            # Argument 1: "hello\nworld" (contains newline)
            # Argument 2: "foo"
            message = "hello\nworld\x00foo\x00"
            client_sock.send(message.encode("utf-8"))
        finally:
            client_sock.close()

        sleep(0.2)  # Give time for processing

        # Should receive arguments correctly, with newline preserved
        self.assertEqual(len(received_args), 1)
        self.assertEqual(received_args[0], ("hello\nworld", "foo"))

        host.release()

    def test_string_representations(self):
        """Test __str__ and __repr__ methods."""
        port = get_free_port()
        app = Socket_Singleton(port=port, timeout=10, verbose=True)

        # Test __str__ - should be human-readable
        str_repr = str(app)
        self.assertIn("Socket_Singleton", str_repr)
        self.assertIn("address=", str_repr)
        self.assertIn("port=", str_repr)
        self.assertIn(str(port), str_repr)
        self.assertIn("127.0.0.1", str_repr)

        # Test __repr__ - should be unambiguous and include all parameters
        repr_str = repr(app)
        self.assertIn("Socket_Singleton", repr_str)
        self.assertIn("address=", repr_str)
        self.assertIn("port=", repr_str)
        self.assertIn("timeout=", repr_str)
        self.assertIn("client=", repr_str)
        self.assertIn("strict=", repr_str)
        self.assertIn("release_threshold=", repr_str)
        self.assertIn("max_clients=", repr_str)
        self.assertIn("verbose=", repr_str)
        self.assertIn("observers=", repr_str)
        self.assertIn("clients=", repr_str)
        self.assertIn("listening=", repr_str)
        self.assertIn(str(port), repr_str)
        self.assertIn("10", repr_str)  # timeout value
        self.assertIn("True", repr_str)  # verbose value

        # Verify __repr__ can be used to reconstruct (at least conceptually)
        # It should include all the key information
        self.assertIn("observers=0", repr_str)  # No observers initially
        self.assertIn("clients=0", repr_str)  # No clients initially
        self.assertIn("listening=True", repr_str)  # Should be listening
        self.assertIn("secret=None", repr_str)  # No secret by default

        app.release()

        # Test __repr__ with secret (should be masked)
        app_with_secret = Socket_Singleton(port=get_free_port(), secret="my-secret")
        repr_with_secret = repr(app_with_secret)
        self.assertIn("secret=***", repr_with_secret)  # Secret should be masked
        self.assertNotIn("my-secret", repr_with_secret)  # Actual secret should not appear
        app_with_secret.release()


class TestValidation(unittest.TestCase):
    """Tests for input validation and error handling."""

    def test_invalid_port_too_low(self):
        """Test that port < 0 raises ValueError."""
        with self.assertRaises(ValueError) as context:
            Socket_Singleton(port=-1)
        self.assertIn("port must be between 0 and 65535", str(context.exception))

    def test_invalid_port_too_high(self):
        """Test that port > 65535 raises ValueError."""
        with self.assertRaises(ValueError) as context:
            Socket_Singleton(port=65536)
        self.assertIn("port must be between 0 and 65535", str(context.exception))

    def test_invalid_timeout(self):
        """Test that timeout < 0 raises ValueError."""
        with self.assertRaises(ValueError) as context:
            Socket_Singleton(port=get_free_port(), timeout=-1)
        self.assertIn("timeout must be greater than or equal to 0", str(context.exception))

    def test_invalid_release_threshold(self):
        """Test that release_threshold < 0 raises ValueError."""
        with self.assertRaises(ValueError) as context:
            Socket_Singleton(port=get_free_port(), release_threshold=-1)
        self.assertIn(
            "release_threshold must be greater than or equal to 0", str(context.exception)
        )

    def test_invalid_max_clients(self):
        """Test that max_clients < 0 raises ValueError."""
        with self.assertRaises(ValueError) as context:
            Socket_Singleton(port=get_free_port(), max_clients=-1)
        self.assertIn("max_clients must be greater than or equal to 0", str(context.exception))


class TestSingletonEnforcement(unittest.TestCase):
    """Tests for singleton enforcement requiring separate processes."""

    def setUp(self):
        """Use a unique port for each test."""
        self.port = get_free_port()
        # Create a singleton in this process
        self.app = Socket_Singleton(port=self.port)

    def tearDown(self):
        """Clean up after each test."""
        self.app.release()
        sleep(0.2)  # Give port time to release

    def test_singleton_enforcement(self):
        """Test that a second instance cannot bind to the same port."""
        # Give the setUp singleton time to fully bind

        # Try to bind to the same port from another process
        result = run_test_app(f"default {self.port}")

        # Should fail - SystemExit means no output and process exits
        # On Windows, SystemExit may return 0, so check for empty stdout
        self.assertFalse(result.stdout.strip(), f"Expected empty stdout but got: {result.stdout}")

    def test_different_port_allowed(self):
        """Test that different ports allow separate instances."""
        other_port = get_free_port()
        result = run_test_app(f"default {other_port}")

        # Should succeed
        self.assertIn("Singleton locked", result.stdout)
        self.assertEqual(result.returncode, 0)

    def test_strict_mode(self):
        """Test that strict=True (default) causes SystemExit."""
        # Give the setUp singleton time to fully bind

        result = run_test_app(f"default {self.port}")

        # SystemExit means no output (process exits immediately)
        # Note: SystemExit can return 0 on some systems, so check stdout
        self.assertFalse(result.stdout.strip(), f"Expected empty stdout but got: {result.stdout}")

    def test_no_strict_mode(self):
        """Test that strict=False raises MultipleSingletonsError."""

        # Test 1: From another process (client side)
        # Try to bind to the same port with strict=False
        result = run_test_app(f"no_strict {self.port}")

        # Should catch and print the error (not become singleton)
        self.assertIn("MultipleSingletonsError", result.stdout)
        self.assertNotIn("Singleton locked", result.stdout)
        self.assertEqual(result.returncode, 0)

        # Test 2: From this process (host side)
        # Try to create another instance in the same process with strict=False
        # This should raise MultipleSingletonsError
        with self.assertRaises(MultipleSingletonsError) as context:
            Socket_Singleton(port=self.port, strict=False)

        # Verify the error message
        self.assertIn("already bound & listening", str(context.exception))
        self.assertIn(str(self.port), str(context.exception))

        # Verify the original singleton is still working
        self.assertTrue(self.app._listening)
        self.assertEqual(self.app.port, self.port)


class TestArgumentPassing(unittest.TestCase):
    """Tests for argument passing between processes."""

    def setUp(self):
        """Set up singleton with observer."""
        self.port = get_free_port()
        self.app = Socket_Singleton(port=self.port)
        self.received_args = []

        def callback(args_tuple):
            self.received_args.append(args_tuple)

        self.app.trace(callback)

    def tearDown(self):
        """Clean up after each test."""
        self.app.release()
        sleep(0.2)

    def test_single_argument(self):
        """Test receiving a single argument from a client."""
        run_test_app(f"default {self.port} foo")

        self.assertEqual(len(self.received_args), 1)
        self.assertEqual(self.received_args[0], ("foo",))

    def test_multiple_arguments(self):
        """Test receiving multiple arguments as a tuple."""
        run_test_app(f"default {self.port} foo bar baz")

        self.assertEqual(len(self.received_args), 1)
        self.assertEqual(self.received_args[0], ("foo", "bar", "baz"))

    def test_no_arguments(self):
        """Test client with no arguments."""
        run_test_app(f"default {self.port}")

        # Should receive empty tuple or no callback
        # (empty tuples are filtered out in _create_server)
        self.assertEqual(len(self.received_args), 0)

    def test_multiple_clients(self):
        """Test receiving arguments from multiple clients."""
        run_test_app(f"default {self.port} foo bar")
        run_test_app(f"default {self.port} baz qux")

        self.assertEqual(len(self.received_args), 2)
        self.assertEqual(self.received_args[0], ("foo", "bar"))
        self.assertEqual(self.received_args[1], ("baz", "qux"))

    def test_no_client_mode(self):
        """Test that client=False prevents argument sending."""
        self.app.release()

        # Create new host singleton (normal, client=True doesn't matter for host)
        self.app = Socket_Singleton(port=self.port)
        self.received_args = []

        def callback(args_tuple):
            self.received_args.append(args_tuple)

        self.app.trace(callback)

        # Test 1: Client with client=False should NOT send arguments
        run_test_app(f"no_client {self.port} foo bar baz")

        # Should not receive any arguments because client had client=False
        self.assertEqual(
            len(self.received_args), 0, "Client with client=False should not send arguments"
        )

        # Test 2: Normal client (client=True, default) SHOULD send arguments
        # This verifies our test setup is working correctly
        run_test_app(f"default {self.port} qux quux")

        # Should receive arguments from the normal client
        self.assertEqual(len(self.received_args), 1, "Normal client should send arguments")
        self.assertEqual(self.received_args[0], ("qux", "quux"))

    def test_multiple_observers(self):
        """Test that multiple observers all receive arguments from client processes."""
        received_args_1 = []
        received_args_2 = []
        received_args_3 = []

        def callback1(args_tuple):
            received_args_1.append(args_tuple)

        def callback2(args_tuple):
            received_args_2.append(args_tuple)

        def callback3(args_tuple):
            received_args_3.append(args_tuple)

        # Register multiple observers
        self.app.trace(callback1)
        self.app.trace(callback2)
        self.app.trace(callback3)

        # Send arguments from a client
        run_test_app(f"default {self.port} foo bar baz")

        # All observers should have been called
        self.assertEqual(len(received_args_1), 1)
        self.assertEqual(len(received_args_2), 1)
        self.assertEqual(len(received_args_3), 1)

        # All should have received the same arguments
        self.assertEqual(received_args_1[0], ("foo", "bar", "baz"))
        self.assertEqual(received_args_2[0], ("foo", "bar", "baz"))
        self.assertEqual(received_args_3[0], ("foo", "bar", "baz"))

    def test_observer_exceptions(self):
        """Test that observer exceptions don't crash the server or prevent other observers."""
        # Clear the observer from setUp for this test
        self.app._observers.clear()

        received_args_good = []
        received_args_bad = []

        def good_callback(args_tuple):
            received_args_good.append(args_tuple)

        def bad_callback(args_tuple):
            received_args_bad.append(args_tuple)
            raise ValueError("Intentional test exception")

        # Register both observers
        self.app.trace(good_callback)
        self.app.trace(bad_callback)

        # Send arguments from a client
        run_test_app(f"default {self.port} test args")

        # Good observer should have been called
        self.assertEqual(len(received_args_good), 1)
        self.assertEqual(received_args_good[0], ("test", "args"))

        # Bad observer should also have been called (exception caught internally)
        self.assertEqual(len(received_args_bad), 1)
        self.assertEqual(received_args_bad[0], ("test", "args"))

        # Verify observers are still registered (server thread didn't crash)
        self.assertEqual(len(self.app._observers), 2)

        # Send another argument to verify server is still working
        run_test_app(f"default {self.port} more args")

        # Both observers should be called again
        self.assertEqual(len(received_args_good), 2)
        self.assertEqual(len(received_args_bad), 2)
        self.assertEqual(received_args_good[1], ("more", "args"))
        self.assertEqual(received_args_bad[1], ("more", "args"))

    def test_observer_exception_verbose(self):
        """Test that observer exceptions print verbose messages when verbose=True."""
        self.app.release()
        sleep(0.1)

        # Host wait time - how long the host process will run
        HOST_WAIT_SECONDS = 1
        # Timeout buffer - extra time beyond host wait for cleanup/processing
        TIMEOUT_BUFFER = 1

        # Start a host subprocess with verbose=True and a "bad" callback that raises an exception
        # Use run_test_app with wait=False and capture_output=True
        host_proc = run_test_app(
            f"verbose_host {self.port} {HOST_WAIT_SECONDS}", wait=False, capture_output=True
        )
        sleep(0.2)  # Give host time to start and print "Host ready"

        # Send arguments from a client - this will trigger the exception
        run_test_app(f"default {self.port} test args")

        # Give time for the server thread to process and print verbose message
        sleep(0.3)

        # Terminate and capture output
        # Timeout should be longer than host wait time to avoid premature timeout
        host_proc.terminate()
        stdout, stderr = host_proc.communicate(timeout=HOST_WAIT_SECONDS + TIMEOUT_BUFFER)

        # Handle case where stdout might be None
        output = stdout or stderr or ""

        # Should contain verbose message about observer exception
        self.assertIn("Socket_Singleton: Observer", output)
        self.assertIn("raised exception", output)
        self.assertIn("ValueError", output)
        self.assertIn("Intentional test exception", output)


class TestTimeouts(unittest.TestCase):
    """Tests for timeout and release functionality."""

    def test_timeout_releases_port(self):
        """Test that timeout automatically releases the port."""
        port = get_free_port()
        timeout_seconds = 1

        # Start process with timeout
        proc = run_test_app(f"timeout {timeout_seconds} {port}", wait=False)

        # Give it time to start and bind
        sleep(0.2)

        # Try to bind - should fail (port in use)
        result1 = run_test_app(f"default {port}")
        self.assertFalse(
            result1.stdout.strip(), f"Expected port to be in use, but got: {result1.stdout}"
        )

        # Wait for timeout to expire
        sleep(timeout_seconds + 0.3)

        # Try to bind again - should succeed (port released)
        result2 = run_test_app(f"default {port}")
        self.assertIn("Singleton locked", result2.stdout)

        # Clean up
        proc.wait()

    def test_manual_release(self):
        """Test that manual release() releases the port."""
        port = get_free_port()

        # Start process that releases immediately (then waits 1 second)
        proc = run_test_app(f"release 1 {port}", wait=False)

        # Give it time to bind and release
        sleep(0.3)

        # Should be able to bind (port released)
        result = run_test_app(f"default {port}")
        self.assertIn("Singleton locked", result.stdout)

        # Clean up
        proc.wait()


class TestThresholds(unittest.TestCase):
    """Tests for max_clients and release_threshold."""

    def setUp(self):
        """Set up singleton with observer."""
        self.port = get_free_port()
        self.received_args = []

        def callback(args_tuple):
            self.received_args.append(args_tuple)

        self.app = Socket_Singleton(port=self.port)
        self.app.trace(callback)

    def tearDown(self):
        """Clean up after each test."""
        self.app.release()
        sleep(0.2)

    def test_max_clients(self):
        """Test that max_clients stops processing arguments after threshold."""
        self.app.release()

        # Create new singleton with max_clients=2
        self.app = Socket_Singleton(port=self.port, max_clients=2)
        self.received_args = []

        def callback(args_tuple):
            self.received_args.append(args_tuple)

        self.app.trace(callback)

        # Send arguments from 3 clients
        run_test_app(f"default {self.port} foo")
        run_test_app(f"default {self.port} bar")
        run_test_app(f"default {self.port} baz")

        # Should only receive arguments from first 2 clients
        self.assertEqual(len(self.received_args), 2)
        self.assertEqual(self.received_args[0], ("foo",))
        self.assertEqual(self.received_args[1], ("bar",))

    def test_release_threshold(self):
        """Test that release_threshold releases port after N clients."""
        self.app.release()

        # Create singleton with release_threshold=2
        self.app = Socket_Singleton(port=self.port, release_threshold=2)
        self.received_args = []

        def callback(args_tuple):
            self.received_args.append(args_tuple)

        self.app.trace(callback)

        # Send arguments from 2 clients
        run_test_app(f"default {self.port} foo")
        run_test_app(f"default {self.port} bar")

        # Port should be released, new instance should be able to bind
        result = run_test_app(f"default {self.port}")
        self.assertIn("Singleton locked", result.stdout)

    def test_combined_thresholds(self):
        """Test interaction between max_clients and release_threshold when used together."""
        self.app.release()

        # Create singleton with both thresholds set
        # max_clients=3: stop processing arguments after 3 clients
        # release_threshold=5: release port after 5 clients
        # This tests that max_clients stops processing args, but connections continue
        # until release_threshold is reached
        self.app = Socket_Singleton(port=self.port, max_clients=3, release_threshold=5)
        self.received_args = []

        def callback(args_tuple):
            self.received_args.append(args_tuple)

        self.app.trace(callback)

        # Send arguments from 5 clients
        run_test_app(f"default {self.port} client1")
        run_test_app(f"default {self.port} client2")
        run_test_app(f"default {self.port} client3")
        run_test_app(f"default {self.port} client4")
        run_test_app(f"default {self.port} client5")

        # Should only receive arguments from first 3 clients (max_clients limit)
        self.assertEqual(len(self.received_args), 3)
        self.assertEqual(self.received_args[0], ("client1",))
        self.assertEqual(self.received_args[1], ("client2",))
        self.assertEqual(self.received_args[2], ("client3",))

        # But all 5 clients should have connected (release_threshold reached)
        self.assertEqual(self.app.clients, 5)

        # Port should be released (release_threshold=5 was reached)
        sleep(0.2)  # Give time for release to complete
        result = run_test_app(f"default {self.port}")
        self.assertIn("Singleton locked", result.stdout)


class TestConcurrency(unittest.TestCase):
    """Tests for concurrent launches and argument collection scenarios."""

    def setUp(self):
        """Set up singleton with observer."""
        self.port = get_free_port()
        self.app = Socket_Singleton(port=self.port)
        self.received_args = []

        def callback(args_tuple):
            self.received_args.append(args_tuple)

        self.app.trace(callback)

    def tearDown(self):
        """Clean up after each test."""
        self.app.release()
        sleep(0.2)

    def test_slam_scenario(self):
        """
        Test the core use case: multiple applications launch simultaneously.

        One becomes the host, the others become clients and send their arguments.
        This simulates the real-world scenario where 10 apps launch at once.
        """
        num_clients = 9  # 9 clients + 1 host = 10 total processes

        # Launch multiple client processes in quick succession
        # Each client sends unique arguments to identify them
        processes = []
        for i in range(num_clients):
            # Each client sends its index and some test data
            cmd = f"default {self.port} client{i} arg1 arg2 arg3"
            proc = run_test_app(cmd, wait=False)
            processes.append(proc)

        # Wait for all processes to complete
        for proc in processes:
            proc.wait()

        # Give a moment for all arguments to be received and processed
        sleep(0.3)

        # Should receive arguments from all 9 clients
        self.assertEqual(
            len(self.received_args),
            num_clients,
            f"Expected {num_clients} argument sets, got {len(self.received_args)}",
        )

        # Verify each client's arguments were received correctly
        received_indices = set()
        for args_tuple in self.received_args:
            # Each tuple should be: ("client0", "arg1", "arg2", "arg3"), etc.
            self.assertEqual(
                len(args_tuple),
                4,
                f"Expected 4 arguments per client, got {len(args_tuple)}: {args_tuple}",
            )
            self.assertTrue(
                args_tuple[0].startswith("client"),
                f"First arg should start with 'client', got: {args_tuple[0]}",
            )

            # Extract client number
            client_num = int(args_tuple[0].replace("client", ""))
            received_indices.add(client_num)

            # Verify the other arguments
            self.assertEqual(args_tuple[1:], ("arg1", "arg2", "arg3"))

        # Verify we got arguments from all clients (0-8)
        expected_indices = set(range(num_clients))
        self.assertEqual(
            received_indices,
            expected_indices,
            f"Missing arguments from some clients. Expected {expected_indices}, got {received_indices}",
        )

        # Verify clients count matches
        self.assertEqual(
            self.app.clients, num_clients, f"Expected {num_clients} client connections"
        )

    def test_rapid_successive_launches(self):
        """
        Test rapid successive launches (not truly simultaneous, but close).

        This tests the race condition handling and ensures all arguments
        are collected even when clients connect in quick succession.
        """
        num_clients = 5

        # Launch clients one after another very quickly
        for i in range(num_clients):
            run_test_app(f"default {self.port} rapid{i} data{i}")

        # Should receive all arguments
        self.assertEqual(len(self.received_args), num_clients)
        self.assertEqual(self.app.clients, num_clients)

        # Verify all were received
        for i in range(num_clients):
            found = any(args[0] == f"rapid{i}" for args in self.received_args)
            self.assertTrue(found, f"Missing arguments from rapid{i}")


if __name__ == "__main__":
    unittest.main()
