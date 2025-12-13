## Socket_Singleton.py

### Socket-based, single-instance Python applications with a clean interface

###### _Without lockfiles, mutexes, dependencies, or tomfoolery_

### Installation & Basic Usage

**Install:**

`pip install Socket_Singleton -U`

**Import:**

`from Socket_Singleton import Socket_Singleton`

**Basic Usage:**

```python
# Simple singleton enforcement
Socket_Singleton()
```

or, keep a reference:

```python
app = Socket_Singleton()
```

**Basic Example:**

We have an application, `app.py` that we want to restrict to a single instance:

```python
#app.py

from Socket_Singleton import Socket_Singleton
Socket_Singleton()
input()  # Blocking call to simulate your_business_logic()
```

The first time `app.py` is launched:

```
>> C:\current\working\directory λ python app.py
>>
```

`app.py` executes normally. (Here, `app.py` blocks until we satisfy `input()`. Replace this with your own logic. The examples and basic recipes on this page contain these calls simply for demonstration purposes.)

Now, in another shell, if we try:

```
>> C:\current\working\directory λ python app.py
>> C:\current\working\directory λ
```

The interpreter exits immediately and we end up back at the prompt.

**See also:**

[Common TCP/UDP Port Numbers](https://en.wikipedia.org/wiki/List_of_TCP_and_UDP_port_numbers)  
[Windows Socket Error Code 10048](https://learn.microsoft.com/en-us/windows/win32/winsock/windows-sockets-error-codes-2#WSAEADDRINUSE)

It is recommended to specify a port in the constructor\*

## Constructor Parameters

**Constructor:**

`Socket_Singleton(address="127.0.0.1", port=1337, timeout=0, client=True, strict=True, release_threshold=0, max_clients=0, verbose=False, secret=None)`

### `address`

The IP address to bind the socket to. Defaults to `"127.0.0.1"` (localhost). This parameter allows you to control which network interface the singleton binds to, which is useful in a variety of cases such as containers, VMs, multi-homed environments, etc.

**Default behavior (localhost):**

```python
# Binds to localhost - machine-wide singleton
app = Socket_Singleton()
# or explicitly:
app = Socket_Singleton(address="127.0.0.1")
```

**Multi-homed systems example:**

On a system with multiple network interfaces, you can create separate singleton instances per interface:

```python
# Server with two network cards
# Interface 1: 192.168.1.100 (internal company network)
# Interface 2: 10.0.0.50 (VPN network)

# Internal network singleton
internal_app = Socket_Singleton(address="192.168.1.100", port=1337)

# VPN network singleton (separate instance)
vpn_app = Socket_Singleton(address="10.0.0.50", port=1337)

# These can coexist because they're on different interfaces!
```

**Docker/Container environments:**

In containerized environments, you might want per-container singletons:

```python
# Container A
app_a = Socket_Singleton(address="172.17.0.2", port=1337)

# Container B
app_b = Socket_Singleton(address="172.17.0.3", port=1337)

# Host machine
host_app = Socket_Singleton(address="127.0.0.1", port=1337)

# All three can run simultaneously on different addresses
```

**Binding to all interfaces:**

You can bind to all available interfaces using `"0.0.0.0"`:

```python
# Binds to all network interfaces
app = Socket_Singleton(address="0.0.0.0", port=1337)
```

Note: For most applications, the default `127.0.0.1` (localhost) is what you want - a machine-wide singleton instance. The `address` parameter provides flexibility for specialized network configurations.

### `port`

Port number for the socket listener. Defaults to `1337`. Prefer using ports in the range 49152-65535 (ephemeral ports).

### `timeout`

A duration in seconds, specifying how long to hold the socket. Defaults to `0` (no timeout, keep-alive). Countdown starts at the end of initialization, immediately after the socket is bound successfully.

### `client`

If `False`, client processes won't send arguments to the host. Defaults to `True`.

### `strict`

If `False`, raises `MultipleSingletonsError` instead of `SystemExit` when a second instance tries to run. Defaults to `True`.

```python
from Socket_Singleton import Socket_Singleton, MultipleSingletonsError

def main():
    try:
        app = Socket_Singleton(strict=False)
    except MultipleSingletonsError as err:
        print("We are not the singleton.")
        print(err)
    else:
        print("We are the singleton!")
        app.trace(callback)
        input()

if __name__ == "__main__":
    main()
```

### `release_threshold`

Release the port after this many client connections. Defaults to `0` (never release). Once the threshold is reached, the port is released and no new connections will be accepted.

```python
# Stop accepting connections after 10 clients
app = Socket_Singleton(release_threshold=10)
```

### `max_clients`

Stop processing arguments after this many client connections. Defaults to `0` (process all arguments). Connections are still accepted, but their arguments are ignored after the threshold. Useful for rudimentary rate limiting or throttling.

```python
# Rate limit: ignore arguments after 5 clients, but keep accepting connections
app = Socket_Singleton(max_clients=5)
```

**Combined usage:**

You can use both parameters together for more complex scenarios:

```python
# Throttle arguments at 5 clients, stop accepting at 10 clients
app = Socket_Singleton(max_clients=5, release_threshold=10)
```

**Important:** When using both parameters together:

- If `release_threshold < max_clients`: The `max_clients` parameter becomes effectively irrelevant, as connections stop being accepted before the argument threshold is reached.
- If `release_threshold > max_clients`: Both work as intended - arguments are throttled first, then connections stop being accepted.
- If `release_threshold == max_clients`: Both thresholds trigger simultaneously (release happens first, so the last client's arguments may not be processed).

### `verbose`

Enable verbose output for debugging. When `True`, prints warnings for connection failures, encoding errors, and observer exceptions. Defaults to `False` (silent operation).

```python
# Silent operation (default)
app = Socket_Singleton()

# Verbose mode - prints warnings for errors
app = Socket_Singleton(verbose=True)
```

**When verbose mode is enabled, you'll see warnings for:**

1. **Connection failures**: When a client process fails to connect to an existing host (e.g., due to race conditions or port releases)
2. **Encoding errors**: When received data cannot be decoded as UTF-8
3. **Observer exceptions**: When a registered observer callback raises an exception
4. **Client verification failures**: When a client fails secret verification (if `secret` is set)

### `secret`

Optional secret string for client verification. If provided, clients must send this secret before their arguments. Defaults to `None` (no verification). Useful for preventing unauthorized applications from injecting arguments into your singleton, which may or may not have registered callbacks that themselves may or may not handle those injected arguments gracefully.

**Security Note:**

By default, `Socket_Singleton` accepts connections from any process that can connect to the port. This is fine for localhost-only singleton enforcement, but if you're concerned about unauthorized applications connecting and injecting arguments, you can use the `secret` parameter.

**Basic usage:**

```python
# Host process
app = Socket_Singleton(secret="my-secret-key")
app.trace(callback)

# Client processes (must use same secret)
Socket_Singleton(secret="my-secret-key")  # Will send secret + args from the process
```

**Using environment variables:**

```python
import os
from Socket_Singleton import Socket_Singleton

# Read secret from environment variable
secret = os.getenv("SOCKET_SINGLETON_SECRET")
app = Socket_Singleton(secret=secret)
```

**How it works interally:**

- If `secret` is `None` (default): No verification - any connection is accepted by the host
- If `secret` is provided to the host: Clients must send the secret as the first part of their message over the socket (before a null byte `\x00`), followed by arguments from their process
- Invalid secrets are silently ignored (or logged if `verbose=True`)

**Important:** Both host and client processes must use the same `secret` value. If they don't match, the client's arguments will be ignored.


## Methods

### `trace(observer, *args, **kwargs)`

Register an observer callback to receive arguments from client processes.

**How it works:**

When you register an observer with `trace()`, you can optionally provide additional `*args` and `**kwargs` that will be stored and automatically passed to your observer callback when it's invoked. This allows you to configure your observer at registration time.

**Observer signature:**

Your observer callback receives arguments in this order:
1. **First parameter**: A tuple containing all arguments from a single client process
2. **Followed by**: Any `*args` you provided to `trace()` (unpacked)
3. **Followed by**: Any `**kwargs` you provided to `trace()` (unpacked)

**Important:** Arguments from each client are sent as a **complete package**. If a client runs `python app.py foo bar baz`, your observer will be called **once** with the tuple `("foo", "bar", "baz")`, not three separate times. This preserves the context of each client's complete command-line invocation.

```python
#app.py

from Socket_Singleton import Socket_Singleton

def callback(client_args, prefix="Received: "):
    # client_args is a tuple like ("foo", "bar", "baz")
    # This preserves the complete context of the client's command
    print(f"{prefix}{' '.join(client_args)}")
    # do_a_thing(client_args)

def main():
    app = Socket_Singleton()
    app.trace(callback, prefix=">>> ")  # Store "prefix" to be passed later
    input()  # Blocking call to simulate your_business_logic()

if __name__ == "__main__":
    main()
```

At the terminal:

```
>> C:\current\working\directory λ python app.py
>>
```

In another shell, subsequent attempts to `python app.py` now look like this:

```
>> C:\current\working\directory λ python app.py foo bar baz
>> C:\current\working\directory λ
```

Meanwhile, our output for the original `python app.py` shell looks like this:

```
>> C:\current\working\directory λ python app.py
>> >>> foo bar baz
```

**More advanced example with stored args/kwargs:**

```python
def my_callback(client_args, prefix, suffix, debug=False):
    """Observer receives: client_args, then stored args/kwargs"""
    print(f"{prefix}{' '.join(client_args)}{suffix}")
    if debug:
        print(f"Debug: received {len(client_args)} arguments")

# Register with stored configuration
app.trace(my_callback, ">>> ", " <<<", debug=True)
#                      ^^^^^^  ^^^^^^  ^^^^^^^^
#                      stored  stored  stored
#                      *args   *args   **kwargs

# When client runs: python app.py foo bar baz
# Observer gets called as:
#   my_callback(("foo", "bar", "baz"), ">>> ", " <<<", debug=True)
#   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^  ^^^^^^  ^^^^^^  ^^^^^^^^^
#   client args (first param)          stored   stored  stored
#                                      *args    *args   **kwargs
```

### `untrace(observer)`

Detach (unsubscribe) a callback. Does nothing if the observer is not registered.

```python
app.untrace(my_callback)
```

### `release()`

Release the port, allowing other instances to bind. Stops the server thread, cancels any active timeout timer, clears all registered observers, and releases the socket port.

```python
#app.py

from Socket_Singleton import Socket_Singleton

def main():
    app = Socket_Singleton()
    # Do some work...
    app.release()  # Release the port, allowing other instances to run
    print("Port released - other instances can now bind!")
    input()

if __name__ == "__main__":
    main()
```

At the terminal:

```
>> C:\current\working\directory λ python app.py
>> Port released - other instances can now bind!
>>
```

And in a new shell (after `release()` was called):

```
>> C:\current\working\directory λ python app.py
>>
```

**Important notes about `release()`:**

- **Idempotent**: Safe to call multiple times. If the port is already released, subsequent calls do nothing.
- **Manual control**: Useful for more complex scenarios where you need fine-grained control over when the singleton releases the port.
- **Context manager alternative**: For most use cases, the context manager protocol (see below) is cleaner and automatically handles cleanup.
- **Timer cancellation**: If a timeout was set, calling `release()` will cancel it prematurely.


## Properties

### `arguments`

Read-only snapshot of arguments received from client processes. Returns a tuple of tuples, where each inner tuple represents the complete argument set from a single client process. Arguments are typically consumed immediately by registered observers, so this will often be empty. Useful for debugging or inspecting pending arguments.

```python
# If two clients sent ("foo", "bar") and ("baz",), this returns:
app.arguments  # (("foo", "bar"), ("baz",))
```

### `clients`

An integer property describing how many client processes have connected since instantiation. Useful for monitoring singleton usage, debugging, or implementing custom logic based on connection count.

```python
print(f"Connected clients: {app.clients}")
```


## Context Manager

The context manager protocol is implemented for automatic resource cleanup:

```python
with Socket_Singleton():
    input()  # Blocking call to simulate your_business_logic()
```

`Socket_Singleton.__enter__()` returns `self` so you can have access to the object if needed:

```python
with Socket_Singleton() as ss:
    ss.trace(callback)
    input()  # Blocking call to simulate your_business_logic()
```

The port is automatically released when exiting the `with` block.


## Testing

The project includes a comprehensive test suite using Python's built-in `unittest` framework.

**Run all tests:**

```bash
python -m unittest tests
```

**Run tests with verbose output:**

```bash
python -m unittest -v tests
```

**Run a specific test class:**

```bash
python -m unittest tests.TestInProcess
python -m unittest tests.TestArgumentPassing
python -m unittest tests.TestConcurrency
```

**Run a specific test method:**

```bash
python -m unittest tests.TestArgumentPassing.test_multiple_observers
```

**Test structure:**

- `tests.py` - Main test suite with organized test classes
- `test_app.py` - Helper script for subprocess-based tests

Tests are organized by concern:
- **TestInProcess**: Fast in-process tests (properties, trace/untrace, context manager)
- **TestSingletonEnforcement**: Singleton behavior requiring separate processes
- **TestArgumentPassing**: Argument passing between processes
- **TestTimeouts**: Timeout and release functionality
- **TestThresholds**: `max_clients` and `release_threshold` behavior
- **TestConcurrency**: Concurrent launch scenarios

---

## FAQ

### Why Sockets?

Socket-based singleton enforcement offers several advantages over traditional approaches:

- **No lockfiles**: No filesystem clutter or permission issues
- **No mutexes**: No OS-specific synchronization primitives required
- **Cross-platform**: Works identically on Windows, Linux, and macOS
- **Portable**: No dependencies beyond Python's standard library
- **Fast**: Socket binding is a lightweight, atomic operation
- **Reliable**: OS-level port binding provides strong guarantees
- **Network-aware**: Can be configured for multi-homed systems, containers, and VMs

The socket approach leverages the operating system's built-in port binding mechanism, which naturally enforces exclusivity - only one process can bind to a given port at a time. This makes it an elegant, dependency-free solution for singleton enforcement with options for rudimentary IPC.
