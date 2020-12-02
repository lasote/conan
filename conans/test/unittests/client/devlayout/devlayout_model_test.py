import unittest

from conans import DefaultLayout
from conans.test.utils.mocks import MockSettings, MockConanfile


class DevLayoutModelTest(unittest.TestCase):

    def base_class_defaults_test(self):
        settings = MockSettings({})
        cf = MockConanfile(settings)
        ly = DefaultLayout(cf)
        self.assertEqual(ly.build, "build")
        self.assertEqual(ly.src, "")
        self.assertEqual(ly.build_libdir, "")
        self.assertEqual(ly.build_bindir, "")
        self.assertEqual(ly.build_includedirs, [ly.build, ly.src])
        self.assertIsNone(ly.build_installdir)
        self.assertEqual(ly.pkg_libdir, "lib")
        self.assertEqual(ly.pkg_bindir, "bin")
        self.assertEqual(ly.pkg_includedir, "include")
        self.assertEqual(ly.pkg_builddir, "")
        self.assertEqual(ly.pkg_resdir, "")

    def cmake_defaults_test(self):
        # Depending on build type
        # TODO
        pass

    def folders_test(self):
        # TODO: default install dir, other composed...
        pass

    def package_test(self):
        # TODO: COMPLETE layout with patterns and test
        pass

    def package_test(self):
        # TODO: COMPLETE layout with patterns and test
        pass