import asyncio
import functools
import venusian


def wraps_with_context(func, context):
    """Return a wrapped partial(func, context)"""
    wrapped = functools.partial(func, context)
    wrapped = functools.wraps(func)(wrapped)
    if asyncio.iscoroutinefunction(func):
        wrapped = asyncio.coroutine(wrapped)
    return wrapped


class event(object):
    venusian = venusian
    def __init__(self, message_type, callback=None, venusian_category='slack.rtm'):
        self.message_type = message_type
        self.callback = callback
        self.venusian_category = venusian_category

    def __call__(self, func):
        def callback(context, name, ob):
            obj = context.context
            self.callback = wraps_with_context(func, obj)
            # a new instance is needed to keep this related to *one* bot
            # instance
            e = self.__class__(self.message_type, self.callback,
                        venusian_category=self.venusian_category)
            obj.attach_events(e)
        info = self.venusian.attach(func, callback,
                category=self.venusian_category)
        return func
