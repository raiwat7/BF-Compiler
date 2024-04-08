# BF_compiler

Compiles brainf*ck code to LLVM IR, and potentially runs it with McJIT.

## Requirements

- Python 3
- `llvmlite` (install with `python3 -m pip install --user llvmlite`)

## Usage

Place some brainf*ck code into a file, and name it what you want. For the sake
of simplicity, we'll assume your file is named `example.bf`.

After installing the requirements, you can choose to:

- Run your brainf*ck code directly by running `python3 bf-compiler.py --run
  example.bf`.
