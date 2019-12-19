import textwrap
import unittest

from conans.paths import LAYOUT_PY
from conans.test.utils.tools import TestClient


class LayoutLoadTest(unittest.TestCase):

    def test_method_layout_load(self):
        client = TestClient()
        conanfile = textwrap.dedent("""
              from conans import ConanFile, CMake, CMakeLayout

              class Pkg(ConanFile):
                  settings = "os", "compiler", "arch", "build_type"
                  
                  def layout(self):
                      the_ly = CMakeLayout(self)
                      the_ly.build = "mybuild"
                      the_ly.src = "mysrc"
                      return the_ly

                  def assert_layout(self):
                      assert self.lyt.build == "mybuild"
                      assert self.lyt.src == "mysrc"

                  def build(self):
                      self.assert_layout()

                  def package(self):
                      self.assert_layout()

                  def package_info(self):
                      self.assert_layout()
                  """)
        client.save({"conanfile.py": conanfile})

        client.run("create . lib/1.0@")
        self.assertIn("Created package revision", client.out)

        # Virtual load
        client.run("install lib/1.0@")

    def test_text_layout_load(self):
        """Declare the layout using the layout text attribute"""
        client = TestClient()
        conanfile = textwrap.dedent("""
           from conans import ConanFile, CMake
    
           class Pkg(ConanFile):
               settings = "os", "compiler", "arch", "build_type"
               layout = "cmake"
               
               def assert_layout(self):
                   assert self.layout == "cmake"
                   assert self.lyt.build == "build"
                   assert self.lyt.src == ""
    
               def build(self):
                   self.assert_layout()
    
               def package(self):
                   self.assert_layout()
    
               def package_info(self):
                   self.assert_layout()
               """)
        client.save({"conanfile.py": conanfile})

        client.run("create . lib/1.0@")
        self.assertIn("Created package revision", client.out)

        # Virtual load
        client.run("install lib/1.0@")

    def load_layout_py_local_methods_test(self):
        client = TestClient()
        conanfile = textwrap.dedent("""
           from conans import ConanFile, CMake

           class Pkg(ConanFile):
               settings = "os", "compiler", "arch", "build_type"
               layout = "cmake"

               def build(self):
                   assert self.lyt.build == "overwritten_build"
                   assert self.lyt.src == "overwritten_src"
                   self.output.warn("Here, building")
               """)
        override_layout = textwrap.dedent("""
        from conans import Layout
        
        def layout(self):
            ly = Layout(self)
            ly.build = "overwritten_build"
            ly.src = "overwritten_src"
            return ly
        """)
        client.save({"conanfile.py": conanfile, LAYOUT_PY: override_layout})
        client.run("install .")
        # If not specified in the layout, layout.build_installdir is defauted to layout.build
        client.run("build . -if=overwritten_build")
        self.assertIn("Here, building", client.out)

    def not_load_layout_create_test(self):
        """The LAYOUT_PY file is not used with a Conan create because the package is in the cache
           and this is only intended to work only for packages being edited (local methods +
           editables) Otherwise a package in the cache would have been generated with a "patchy"
           conanfile.
           """
        client = TestClient()
        conanfile = textwrap.dedent("""
           from conans import ConanFile, CMake

           class Pkg(ConanFile):
               settings = "os", "compiler", "arch", "build_type"
               layout = "cmake"

               def build(self):
                   assert self.lyt.build != "overwritten_build"
                   self.output.warn("Here, building")
               """)
        override_layout = textwrap.dedent("""
        from conans import Layout

        def layout(self):
            ly = Layout(self)
            ly.build = "overwritten_build"
            ly.src = "overwritten_src"
            return ly
        """)
        client.save({"conanfile.py": conanfile, LAYOUT_PY: override_layout})
        client.run("create . lib/1.0@")
        self.assertIn("Here, building", client.out)

    def editable_load_layout_create_test(self):
        """If the package is in editable mode, the LAYOUT_PY is also used"""
        client = TestClient()
        conanfile = textwrap.dedent("""
           from conans import ConanFile, CMake

           class Pkg(ConanFile):
               settings = "os", "compiler", "arch", "build_type"
               layout = "cmake"

               def build(self):
                   assert self.lyt.build == "overwritten_build"
                   assert self.lyt.src == "overwritten_src"
                   self.output.warn("Here, building")
                   
               def package_info(self):
                    self.output.warn("Here, being reused: {}".format(self.lyt.build))
               """)
        override_layout = textwrap.dedent("""
        from conans import Layout

        def layout(self):
            ly = Layout(self)
            ly.build = "overwritten_build"
            ly.src = "overwritten_src"
            return ly
        """)
        client.save({"conanfile.py": conanfile, LAYOUT_PY: override_layout})
        client.run("install . ")
        client.run("build . -if=overwritten_build")
        client.run("editable add . lib/1.0@")
        client.run("install lib/1.0@")
        self.assertIn("Here, being reused: overwritten_build", client.out)

    def layout_available_methods_test(self):
        """Test the available methods from the layout, even without declared settings"""
        client = TestClient()
        conanfile = textwrap.dedent("""
           import os
           from conans import ConanFile, CMake

           class Pkg(ConanFile):
               layout = "cmake"

               def build(self):
                   assert os.path.join(self.build_folder, self.lyt.build) == self.lyt.build_folder
                   assert os.path.join(self.source_folder, self.lyt.src) == self.lyt.source_folder
                   assert self.lyt.build_lib_folder == \
                          os.path.join(self.lyt.build, self.lyt.build_libdir)
                   assert self.lyt.build_bin_folder == \
                          os.path.join(self.lyt.build, self.lyt.build_bindir)

               """)
        client.save({"conanfile.py": conanfile})
        client.run("create . lib/1.0@")

    def returning_non_layout_in_method_test(self):
        """If you forget to return the layout in the method..."""
        client = TestClient()
        conanfile = textwrap.dedent("""
                   import os
                   from conans import ConanFile, CMake

                   class Pkg(ConanFile):
                       def layout(self):
                           pass
                           
                       def build(self):
                           self.lyt.build_folder
                           
                       """)
        client.save({"conanfile.py": conanfile})
        client.run("create . lib/1.0@", assert_error=True)
        self.assertIn("The layout() method is not returning a Layout object", client.out)

    def invalid_layout_type_test(self):
        """If you forget to return the layout in the method..."""
        client = TestClient()
        conanfile = textwrap.dedent("""
                   import os
                   from conans import ConanFile, CMake

                   class Pkg(ConanFile):
                       layout = 34

                       def build(self):
                           self.lyt.build_folder

                       """)
        client.save({"conanfile.py": conanfile})
        client.run("create . lib/1.0@", assert_error=True)
        self.assertIn("Unexpected layout type declared in the conanfile: <class 'int'>",
                      client.out)

    def invalid_layout_override_test(self):
        # TODO: - without function
        #       - returning other stuff
        pass

    def check_layout_override_py2_only_test(self):
        # TODO: Also skip the others with override for py2
        pass