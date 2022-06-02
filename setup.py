from setuptools import setup

setup(
    name="uploading",
    version="0.1.0",
    packages=["uploading"],
    package_dir={"uploading": "uploading"},
    description="Uploading integration",
    entry_points={
        "saleor.plugins": ["uploading = uploading.plugin:UploadingPlugin"],
    },
)
