def on(signal):
    def wrap(fn):
        signal.connect(fn)
    return wrap


def setInterval(interval, func, *asrgs):
    stopped = Event()
    def loop():
        while not stopped.wait(interval): # the first call is in `interval` secs
            func(*args)
    Thread(target=loop).start()    
    return stopped.set


