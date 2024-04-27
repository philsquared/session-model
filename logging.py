
def log_error(*args, **kwargs):
    try:
        from glassware.logging import log_error
    except:
        pass


def log_warn(*args, **kwargs):
    try:
        from glassware.logging import log_warn
    except:
        pass

