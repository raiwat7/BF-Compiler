# BF_compiler

Compiles brainf*ck code to LLVM IR, and potentially runs it with McJIT.

## Requirements

- Python 3
- `llvmlite` (install with `python3 -m pip install --user llvmlite`)

## Usage

Place some brainf*ck code into a file, and name it what you want. For the sake
of simplicity, we'll assume your file is named `example.bf`.

After installing the requirements, you can choose to:

- Run your brainf*ck code directly by running `python3 bf_compiler.py --run
  examples/example.bf`.
- If you want to store output in a txt file, in the terminal, write: `python3 bf_compiler.py --run examples/example.bf > output/example.txt`
- If you want to see the bitcode of any BF program, write: `python3 bf_compiler.py --bitcode examples/example.bf`. The bitcode file will be stored in your local device as `example.bc`
- If you want to see the llvm Intermediate Representation of the corresponding BF program, write: `python3 bf_compiler.py --ir examples/example.bf` OR `python3 bf_compiler.py -i examples/example.bf`
