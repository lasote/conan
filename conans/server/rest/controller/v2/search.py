from bottle import request

from conans.model.ref import ConanFileReference
from conans.server.rest.bottle_routes import BottleRoutes
from conans.server.rest.controller.controller import Controller
from conans.server.service.common.search import SearchService


class SearchControllerV2(Controller):
    """
        Serve requests related with Conan
    """
    def attach_to(self, app):

        r = BottleRoutes(self.route)

        @app.route('%s/search' % r.base_url, method=["GET"])
        def search(auth_user):
            pattern = request.params.get("q", None)
            ignorecase = request.params.get("ignorecase", True)
            if isinstance(ignorecase, str):
                ignorecase = False if 'false' == ignorecase.lower() else True
            search_service = SearchService(app.authorizer, app.server_store, auth_user)
            references = [ref.full_repr() for ref in search_service.search(pattern, ignorecase)]
            return {"results": references}

        @app.route('%s/search' % r.recipe, method=["GET"])
        @app.route('%s/search' % r.recipe_revision, method=["GET"])
        def search_packages(name, version, username, channel, auth_user, revision=None):
            query = request.params.get("q", None)
            search_service = SearchService(app.authorizer, app.server_store, auth_user)
            ref = ConanFileReference(name, version, username, channel, revision)
            info = search_service.search_packages(ref, query, look_in_all_rrevs=False)
            return info