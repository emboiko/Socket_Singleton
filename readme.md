## Socket_Singleton.py

### Socket-based, single-instance Python applications with a clean interface

##### *Without lockfiles, mutexes, dependencies, or tomfoolery*

**Import:**

`From Socket_Singleton import Socket_Singleton`

**Constructor:**

`Socket_Singleton(address="127.0.0.1", port=1337, client=True, strict=True)`

**Usage:**

`Socket_Singleton()`

or, keep a reference:

`app = Socket_Singleton()`

then attach a callback:

```
def my_callback(args):
    print(args)

app.trace(my_callback)
```

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

def callback(arguments, *args, **kwargs):
    print(arguments)
    #arg = arguments.pop()
    #do_a_thing(arg)

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
>> ["foo"]
>> ["foo", "bar"]
>> ["foo", "bar", "baz"]
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

If we specify the kwarg `strict=False`, we can raise and capture a **custom exception**, `MultipleSingletonsError`, rather than entirely destroying the process which fails to become the singleton.

```
from Socket_Singleton import Socket_Singleton, MultipleSingletonsError

try:
    Socket_Singleton(strict=False)
    input("We are the Socket Singleton.")
except MultipleSingletonsError:
    input("We are not the Socket Singleton.")
else:
    #Do your very_exclusive_thing() here. 
finally:
    print("Done.")

```