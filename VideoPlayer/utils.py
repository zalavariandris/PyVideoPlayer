def on(signal):
    def wrap(fn):
        signal.connect(fn)
    return wrap