# Error Making Modules

## Requirements

Some of the modules require a CUDA-enabled environment. To set everything up, follow the [instructions](https://docs.nvidia.com/cuda/) from the official NVIDIA website.

## Installation

First, you need to initialize the helper submodule directory:

`git submodule update --init`

Then, run the following command to install all necessary packages:

`pip install -r requirements.txt`

The project was tested using Python 3.7.

## Errorification

To run any of the modules, initialize an object instance and run the `main` function with the input file and output folder provided.
