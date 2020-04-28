## Socket_Singleton.py

### Socket-based, single-instance Python applications with a clean interface

###### *Without lockfiles, mutexes, dependencies, or tomfoolery*

**Install:**

`pip install Socket_Singleton`

**Import:**

`From Socket_Singleton import Socket_Singleton`

**Constructor:**

`Socket_Singleton(address="127.0.0.1", port=1337, timeout=0, client=True, strict=True)`

**Usage:**

`Socket_Singleton()`

or, keep a reference:

`app = Socket_Singleton()`

then attach a callback, and capture arguments from subsequent calls to your application:

```
def my_callback(arg):
    print(arg)

app.trace(my_callback)
```

**See also:**

[Common TCP/UDP Port Numbers](https://en.wikipedia.org/wiki/List_of_TCP_and_UDP_port_numbers)

It is recommended to specify a port in the constructor*


Examples:
---

Say we have an application, app.py, that we want to restrict to a single instance.
```
#app.py

from Socket_Singleton import Socket_Singleton
Socket_Singleton()
input() #Blocking call to simulate your_business_logic() 
```
The first time app.py is launched:
```
>> C:\current\working\directory λ python app.py
>> 
```
app.py executes normally. (Here, app.py blocks until we satisfy input(). Replace this with your own logic. The examples and basic recipes on this page contain these calls simply for demonstration purposes.)

Now, in another shell, if we try:
```
>> C:\current\working\directory λ python app.py
>> C:\current\working\directory λ
```
The interpreter exits immediately and we end up back at the prompt.

---
We can also get access to **arguments** passed from subsequent attempts to run `python app.py` with the `arguments` attribute.
This attribute is not intended to be accessed directly- it's most likely more convenient to use the `trace()` method. This allows you to **register a callback**, which gets called when `arguments` is appended (as other instances *try* to run).

`Socket_Singleton.trace(observer, *args, **kwargs)`

```
#app.py

from Socket_Singleton import Socket_Singleton

def callback(argument, *args, **kwargs):
    print(argument)
    #do_a_thing(argument)

def main():
    app = Socket_Singleton()
    app.trace(callback, *args, **kwargs)
    input() #Blocking call to simulate your_business_logic() 

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
>> foo
>> bar
>> baz
```

We can also **detach a given observer / callback** via `untrace()` with a similar interface. 

`Socket_Singleton.untrace(observer)`

---
If you'd prefer to **disconnect** from the port prematurely, thus releasing the "lock", there's a `close()` method:

```
#app.py

from Socket_Singleton import Socket_Singleton

def main():
    app = Socket_Singleton()
    app.close()
    print("Running!")
    input()

if __name__ == "__main__":
    main()
```
At the terminal:
```
>> C:\current\working\directory λ python app.py
>> Running!
>> 
```
And in a new shell:
```
>> C:\current\working\directory λ python app.py
>> Running!
>> 
```

---

**Context manager** protocol is implemented as well:

```
with Socket_Singleton():
    input() #Blocking call to simulate your_business_logic()
```

`Socket_Singleton.__enter__()` returns self so we can can have access to the object if needed:

```
with Socket_Singleton() as ss:
    ss.trace(callback)
    input() #Blocking call to simulate your_business_logic()
```

---
**Timeout**

A duration in seconds, specifying how long to hold the socket. Defaults to 0 (no timeout, keep-alive). Countdown starts at the end of initialization, immediately after the socket is bound successfully. 

---

If we specify the kwarg `strict=False`, we can raise and capture a **custom exception**, `MultipleSingletonsError`, rather than entirely destroying the process which fails to become the singleton.

```
from Socket_Singleton import Socket_Singleton, MultipleSingletonsError

def callback(arg):
    print(f"callback: {arg}")

def main():
    try:
        app = Socket_Singleton(strict=False)
    except MultipleSingletonsError as err:
        print("We are not the singleton.")
        print(err)
    else:
        print("We are the singleton!")
        app.trace(callback)
        [print(arg) for arg in app.arguments]
        # print(app)
        # print(repr(app))
        # help(app)

    input()

if __name__ == "__main__":
    main()
```
