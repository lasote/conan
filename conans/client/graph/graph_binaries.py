import os

from conans.client.graph.graph import (BINARY_BUILD, BINARY_UPDATE, BINARY_CACHE,
                                       BINARY_DOWNLOAD, BINARY_MISSING, BINARY_SKIP,
                                       BINARY_WORKSPACE)
from conans.client.output import ScopedOutput
from conans.errors import NotFoundException, NoRemoteAvailable
from conans.model.info import ConanInfo
from conans.model.manifest import FileTreeManifest
from conans.model.ref import PackageReference
from conans.util.env_reader import get_env
from conans.util.files import rmdir, is_dirty


class GraphBinariesAnalyzer(object):
    def __init__(self, client_cache, output, remote_manager, registry, workspace):
        self._client_cache = client_cache
        self._out = output
        self._remote_manager = remote_manager
        self._registry = registry
        self._workspace = workspace

    def _get_package_info(self, package_ref, remote):
        try:
            remote_info = self._remote_manager.get_package_info(package_ref, remote)
            return remote_info
        except (NotFoundException, NoRemoteAvailable):  # 404 or no remote
            return False

    def _check_update(self, package_folder, package_ref, remote, output, node):

        revisions_enabled = get_env("CONAN_CLIENT_REVISIONS_ENABLED", False)
        if revisions_enabled:
            metadata = self._client_cache.load_metadata(package_ref.conan)
            rec_rev = metadata.packages[package_ref.package_id].recipe_revision
            if rec_rev != node.conan_ref.revision:
                output.warn("Outdated package! The package doesn't belong "
                            "to the installed recipe revision: %s" % str(package_ref))

        try:  # get_conan_digest can fail, not in server
            # FIXME: This can iterate remotes to get and associate in registry
            upstream_manifest = self._remote_manager.get_package_manifest(package_ref, remote)
        except NotFoundException:
            output.warn("Can't update, no package in remote")
        except NoRemoteAvailable:
            output.warn("Can't update, no remote defined")
        else:
            read_manifest = FileTreeManifest.load(package_folder)
            if upstream_manifest != read_manifest:
                if upstream_manifest.time > read_manifest.time:
                    output.warn("Current package is older than remote upstream one")
                    node.update_manifest = upstream_manifest
                    return True
                else:
                    output.warn("Current package is newer than remote upstream one")

    def _evaluate_node(self, node, build_mode, update, evaluated_references, remote_name):
        assert node.binary is None

        conan_ref, conanfile = node.conan_ref, node.conanfile
        package_id = conanfile.info.package_id()
        package_ref = PackageReference(conan_ref, package_id)
        # Check that this same reference hasn't already been checked
        previous_node = evaluated_references.get(package_ref)
        if previous_node:
            node.binary = previous_node.binary
            node.binary_remote = previous_node.binary_remote
            return
        evaluated_references[package_ref] = node

        output = ScopedOutput(str(conan_ref), self._out)
        if build_mode.forced(conanfile, conan_ref):
            output.warn('Forced build from source')
            node.binary = BINARY_BUILD
            return

        package_folder = self._client_cache.package(package_ref,
                                                    short_paths=conanfile.short_paths)

        # Check if dirty, to remove it
        local_project = self._workspace[conan_ref] if self._workspace else None
        if local_project:
            node.binary = BINARY_WORKSPACE
            return

        with self._client_cache.package_lock(package_ref):
            if is_dirty(package_folder):
                output.warn("Package is corrupted, removing folder: %s" % package_folder)
                rmdir(package_folder)

        if remote_name:
            remote = self._registry.remotes.get(remote_name)
        else:
            # If the remote_name is not given, follow the binary remote, or
            # the recipe remote
            # If it is defined it won't iterate (might change in conan2.0)
            remote = self._registry.prefs.get(package_ref) or self._registry.refs.get(conan_ref)
        remotes = self._registry.remotes.list

        if os.path.exists(package_folder):
            if update:
                if remote:
                    if self._check_update(package_folder, package_ref, remote, output, node):
                        node.binary = BINARY_UPDATE
                        if build_mode.outdated:
                            package_hash = self._get_package_info(package_ref, remote).recipe_hash
                elif remotes:
                    pass
                else:
                    output.warn("Can't update, no remote defined")
            if not node.binary:
                node.binary = BINARY_CACHE
                package_hash = ConanInfo.load_from_package(package_folder).recipe_hash
        else:  # Binary does NOT exist locally
            revisions_enabled = get_env("CONAN_CLIENT_REVISIONS_ENABLED", False)
            if revisions_enabled:
                # If revisions enabled, even if the "remote" has no the binary search it in the
                # rest of remotes. It will look for the binary for the same recipe revision
                iterate_remotes = [r for r in remotes if r != remote] if remotes else []
            else:
                if remote:
                    # Search only in the current remote, do not iterate
                    iterate_remotes = []
                else:
                    # No revisions but no current remote, search everywhere
                    iterate_remotes = remotes

            remote_info = None
            if remote:
                remote_info = self._get_package_info(package_ref, remote)

            if not remote_info:
                for r in iterate_remotes:
                    remote_info = self._get_package_info(package_ref, r)
                    if remote_info:
                        remote = r
                        break

            if remote_info:
                node.binary = BINARY_DOWNLOAD
                package_hash = remote_info.recipe_hash
            else:
                if build_mode.allowed(conanfile, conan_ref):
                    node.binary = BINARY_BUILD
                else:
                    node.binary = BINARY_MISSING

        if build_mode.outdated:
            if node.binary in (BINARY_CACHE, BINARY_DOWNLOAD, BINARY_UPDATE):
                local_recipe_hash = self._client_cache.load_manifest(package_ref.conan).summary_hash
                if local_recipe_hash != package_hash:
                    output.info("Outdated package!")
                    node.binary = BINARY_BUILD
                else:
                    output.info("Package is up to date")

        node.binary_remote = remote

    def evaluate_graph(self, deps_graph, build_mode, update, remote_name):
        evaluated_references = {}
        for node in deps_graph.nodes:
            if not node.conan_ref or node.binary:  # Only value should be SKIP
                continue
            private_neighbours = node.private_neighbors()
            if private_neighbours:
                self._evaluate_node(node, build_mode, update, evaluated_references, remote_name)
                if node.binary in (BINARY_CACHE, BINARY_DOWNLOAD, BINARY_UPDATE):
                    for neigh in private_neighbours:
                        neigh.binary = BINARY_SKIP
                        closure = deps_graph.full_closure(neigh, private=True)
                        for n in closure:
                            n.binary = BINARY_SKIP

        for node in deps_graph.nodes:
            if not node.conan_ref or node.binary:
                continue
            self._evaluate_node(node, build_mode, update, evaluated_references, remote_name)
