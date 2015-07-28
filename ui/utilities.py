def log_error(module, ex):
    import logging
    template = "An exception of type {0} occurred in {1}. Arguments:\n{2!r}"
    message = template.format(type(ex).__name__, module, ex.args)
    logging.info(message)
    return message
