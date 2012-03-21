import sys
from recursive import ForwardRequestException


class StatusPersist(object):

    def __init__(self, app, status, url):
        self.app = app
        self.status = status
        self.url = url

    def __call__(self, environ, start_response):
        def keep_status_start_response(status, headers, exc_info=None):
            return start_response(self.status, headers, exc_info)
        parts = self.url.split('?')
        environ['PATH_INFO'] = parts[0]
        if len(parts) > 1:
            environ['QUERY_STRING'] = parts[1]
        else:
            environ['QUERY_STRING'] = ''

        try:
            return self.app(environ, keep_status_start_response)
        except RecursionLoop, e:
            environ['wsgi.errors'].write(
                'Recursion error getting error page: %s\n' % e
            )
            keep_status_start_response(
                '500 Server Error',
                [('Content-type', 'text/plain')],
                sys.exc_info()
            )
            return [
                'Error: %s.  (Error page could not be fetched)' % self.status
            ]


class ErrorDocumentMiddleware(object):

    def __init__(self, app, error_map):
        self.app = app
        self.error_map = error_map

    def __call__(self, environ, start_response):

        def replacement_start_response(status, headers, exc_info=None):
            try:
                status_code = status.split(' ')[0]
            except (ValueError, TypeError):
                raise Exception((
                    'ErrorDocumentMiddleware received an invalid '
                    'status %s' % status
                ))

            if status_code in self.error_map:
                def factory(app):
                    return StatusPersist(
                        app,
                        status,
                        self.error_map[status_code]
                    )
                raise ForwardRequestException(factory=factory)

            return start_response(status, headers, exc_info)

        app_iter = self.app(environ, replacement_start_response)
        return app_iter
