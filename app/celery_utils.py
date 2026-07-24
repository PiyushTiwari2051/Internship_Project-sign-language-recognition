try:
    from celery import Celery
except ImportError:
    class DummyConf:
        def update(self, *args, **kwargs):
            pass

    class DummyCelery:
        def __init__(self):
            self.conf = DummyConf()

        def task(self, *args, **kwargs):
            def decorator(f):
                return f
            return decorator

    Celery = None


def make_celery(app_name=__name__):
    if Celery is not None:
        return Celery(app_name)
    return DummyCelery()
