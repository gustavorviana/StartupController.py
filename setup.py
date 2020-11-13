from distutils.core import setup
import py2exe

setup(
    windows=[
        {
            "script": "__main__.py",  # Main Python script
            # "icon_resources": [(0, "favicon.ico")],  ### Icon to embed into the PE file.
            "dest_base": "StartupController"
        }
    ]
)
