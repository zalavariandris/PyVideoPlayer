# author: 9000, https://stackoverflow.com/users/223424/9000
# copy from: https://stackoverflow.com/questions/43788106/convert-a-list-of-numbers-to-ranges

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

def get_ranges(data):
    result = []
    if not data:
        return result
    idata = iter(sorted([int(v) for v in data]))
    first = prev = next(idata)
    for following in idata:
        if following - prev == 1:
            prev = following
        else:
            result.append((first, prev + 1))
            first = prev = following
    # There was either exactly 1 element and the loop never ran,
    # or the loop just normally ended and we need to account
    # for the last remaining range.
    result.append((first, prev+1))
    return result


