from conan import ConanFile
from conan.tools.files import get, copy, replace_in_file
from conan.tools.scm import Version
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conans.errors import ConanInvalidConfiguration
import os
import re

required_conan_version = ">=1.53.0"


class IMGUIConan(ConanFile):
    name = "imgui"
    description = "Bloat-free Immediate Mode Graphical User interface for C++ with minimal dependencies"
    license = "MIT"
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://github.com/ocornut/imgui"
    topics = ("gui", "graphical", "bloat-free")
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "enable_cpp": [True, False],
        "with_freetype": [True, False],
        "with_lunasvg": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "enable_cpp": False,
        "with_freetype": False,
        "with_lunasvg": False
    }

    def requirements(self):
        if self.options.with_lunasvg and not self.options.with_freetype:
            raise ConanInvalidConfiguration("for imgui with_lunasvg also requires with_freetype");
        if self.options.with_freetype:
            self.requires("freetype/2.13.0")
        if self.options.with_lunasvg:
            self.requires("lunasvg/2.3.8")

    def export_sources(self):
        copy(self, "CMakeLists.txt", self.recipe_folder, self.export_sources_folder)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["IMGUI_SRC_DIR"] = self.source_folder.replace("\\", "/")
        tc.variables["IMGUI_ENABLE_CPP"] = "TRUE" if self.options.enable_cpp else "FALSE"
        tc.variables["IMGUI_WITH_FREETYPE"] = "TRUE" if self.options.with_freetype else "FALSE"
        tc.variables["IMGUI_WITH_LUNASVG"] = "TRUE" if self.options.with_lunasvg else "FALSE"
        tc.generate()

    def _patch_sources(self):
        # Ensure we take into account export_headers
        replace_in_file(self,
            os.path.join(self.source_folder, "imgui.h"),
            "#ifdef IMGUI_USER_CONFIG",
            "#include \"imgui_export_headers.h\"\n\n#ifdef IMGUI_USER_CONFIG"
        )

        # Enable optional features in imconfig.h when appropriate
        if self.options.with_freetype:
            replace_in_file(self,
                os.path.join(self.source_folder, "imconfig.h"),
                "#pragma once",
                "#pragma once\n\n#define IMGUI_ENABLE_FREETYPE\n"
            )
        if self.options.with_lunasvg:
            replace_in_file(self,
                os.path.join(self.source_folder, "imconfig.h"),
                "#pragma once",
                "#pragma once\n\n#define IMGUI_ENABLE_FREETYPE_LUNASVG\n"
            )

    def build(self):
        self._patch_sources()
        cmake = CMake(self)
        cmake.configure(build_script_folder=os.path.join(self.source_folder, os.pardir))
        cmake.build()

    def _match_docking_branch(self):
        return re.match(r'cci\.\d{8}\+(?P<version>\d+\.\d+(?:\.\d+))\.docking', str(self.version))

    def package(self):
        copy(self, pattern="LICENSE.txt", dst=os.path.join(self.package_folder, "licenses"), src=self.source_folder)
        m = self._match_docking_branch()
        version = Version(m.group('version')) if m else Version(self.version)
        backends_folder = os.path.join(
            self.source_folder,
            "backends" if version >= "1.80" else "examples"
        )
        copy(self, pattern="imgui_impl_*",
            dst=os.path.join(self.package_folder, "res", "bindings"),
            src=backends_folder)
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.conf_info.define("user.imgui:with_docking", bool(self._match_docking_branch()))

        self.cpp_info.libs = ["imgui"]
        if self.settings.os == "Linux":
            self.cpp_info.system_libs.append("m")
        if self.settings.os == "Windows":
            self.cpp_info.system_libs.append("imm32")
        self.cpp_info.srcdirs = [os.path.join("res", "bindings")]

        bin_path = os.path.join(self.package_folder, "bin")
        self.output.info("Appending PATH env var with : {}".format(bin_path))
        self.env_info.PATH.append(bin_path)
