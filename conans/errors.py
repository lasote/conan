"""
    Exceptions raised and handled in Conan server.
    These exceptions are mapped between server (as an HTTP response) and client
    through the REST API. When an error happens in server its translated to an HTTP
    error code that its sent to client. Client reads the server code and raise the
    matching exception.

    see return_plugin.py

"""

from contextlib import contextmanager


@contextmanager
def conanfile_exception_formatter(conanfile_name, func_name):
    """
    Decorator to throw an exception formatted with the line of the conanfile where the error ocurrs.
    :param reference: Reference of the conanfile
    :return:
    """
    try:
        yield
    except Exception as exc:
        msg = _format_conanfile_exception(conanfile_name, func_name, exc)
        raise ConanExceptionInUserConanfileMethod(msg)


def _format_conanfile_exception(scope, method, exception):
    """
    It will iterate the traceback lines, when it finds that the source code is inside the users
    conanfile it "start recording" the messages, when the trace exits the conanfile we return
    the traces.
    """
    import sys
    import traceback
    try:
        conanfile_reached = 0  # To know if the trace has reached the code from the conanfile
        content_lines = ["%s: Error in %s() method" % (scope, method)]
        tb = sys.exc_info()[2]
        index = 0

        while True:  # If out of index will raise and will be captured later
            # 40 levels of nested functions max, get the latest
            filepath, line, name, contents = traceback.extract_tb(tb, 40)[index]
            if not "conanfile.py" in filepath:  # Avoid show trace from internal conan source code
                if conanfile_reached:  # The traceback now is into the conan code
                    break
            else:
                msg = "%sIn '%s'" % (" " * conanfile_reached, name)
                msg += " (line %d): %s" % (line, contents) if line else "\n\t%s" % contents
                content_lines.append(msg)
                conanfile_reached += 1
            index += 1
    except:
        pass
    ret = "\n".join(content_lines)
    ret += "\n\n%s: %s" % (exception.__class__.__name__, str(exception))
    return ret


class ConanException(Exception):
    """
         Generic conans exception
    """
    pass


class InvalidNameException(ConanException):
    pass


class ConanConnectionError(ConanException):
    pass


class ConanOutdatedClient(ConanException):
    pass


class ConanExceptionInUserConanfileMethod(ConanException):
    pass

# Remote exceptions #

class InternalErrorException(ConanException):
    """
         Generic 500 error
    """
    pass


class RequestErrorException(ConanException):
    """
         Generic 400 error
    """
    pass


class AuthenticationException(ConanException):  # 401
    """
        401 error
    """
    pass


class ForbiddenException(ConanException):  # 403
    """
        403 error
    """
    pass


class NotFoundException(ConanException):  # 404
    """
        404 error
    """
    pass


class UserInterfaceErrorException(RequestErrorException):
    """
        420 error
    """
    pass


EXCEPTION_CODE_MAPPING = {InternalErrorException: 500,
                          RequestErrorException: 400,
                          AuthenticationException: 401,
                          ForbiddenException: 403,
                          NotFoundException: 404,
                          UserInterfaceErrorException: 420}
