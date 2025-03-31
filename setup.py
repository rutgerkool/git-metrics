import os
import sys
from setuptools import setup

try:
    from setuptools_rust import Binding, RustExtension
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "setuptools-rust"])
    from setuptools_rust import Binding, RustExtension

setup(
    rust_extensions=[
        RustExtension(
            "gitsect.gitsect",
            path="rust/Cargo.toml",
            binding=Binding.PyO3,
            debug=False,
        )
    ],
)
