"""py2app spec for the standalone FairPlay Decrypt.app.

Build on macOS with the transform binary present:

    make transform
    python setup.py py2app

The bundle ships its own Python interpreter, so the GUI runs the
decryptor in-process (see mac_gui.InProcessRunner).
"""

from setuptools import setup

OPTIONS = {
    "argv_emulation": False,
    "includes": ["decrypt", "core"],
    "packages": ["cryptography"],
    "plist": {
        "CFBundleName": "FairPlay Decrypt",
        "CFBundleDisplayName": "FairPlay Decrypt",
        "CFBundleIdentifier": "io.github.ziqzav.fairplay-decrypt",
        "CFBundleVersion": "1.0.0",
        "CFBundleShortVersionString": "1.0.0",
        "LSMinimumSystemVersion": "11.0",
        "NSHighResolutionCapable": True,
    },
}

setup(
    name="FairPlayDecrypt",
    app=["mac_gui.py"],
    data_files=[("", ["transform", "transform_const_data.bin"])],
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
