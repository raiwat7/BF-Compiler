import argparse
import ctypes
import sys
import os

from llvmlite import ir, binding as llvm

INDEX_BIT_SIZE = 16


def generateAbstractSyntaxTree(bf_code):
    bf_code = iter(bf_code)
    abstractSyntaxTree = []
    for c in bf_code:
        if c == "[":
            abstractSyntaxTree.append(generateAbstractSyntaxTree(bf_code))
        elif c == "]":
            break
        else:
            abstractSyntaxTree.append(c)
    return abstractSyntaxTree


def bfToIntermediateRepresentation(bf_code):
    abstractSyntaxTree = generateAbstractSyntaxTree(bf_code)

    # These lines define different types such as byte, int32, size_t, and void using
    #  the ir.IntType() and ir.VoidType() functions provided by the llvmlite module.
    byte = ir.IntType(8)
    int32 = ir.IntType(32)
    size_t = ir.IntType(64)

    void = ir.VoidType()

    # This line creates an LLVM module with the name of the current file
    module = ir.Module(name=__file__)

    # It defines the main() function with no arguments and returns an int32 value.
    # An entry basic block named entry is appended to this function.
    main_type = ir.FunctionType(int32, ())
    main_func = ir.Function(module, main_type, name="main")

    # we are appending a basic block to the main function. In LLVM IR, a basic block is a
    # sequence of instructions with a single entry point and a single exit point. The
    # append_basic_block method is used to add a basic block to the function
    entry = main_func.append_basic_block(name="entry")

    # This line creates an LLVM IR builder that will be used to build instructions within
    # the entry basic block.
    builder = ir.IRBuilder(entry)

    # These lines define LLVM functions for putchar, getchar, and bzero, which correspond
    # to printing a character, reading a character, and zeroing out memory, respectively.
    putchar_type = ir.FunctionType(int32, (int32,))
    putchar = ir.Function(module, putchar_type, name="putchar")
    getchar_type = ir.FunctionType(int32, ())
    getchar = ir.Function(module, getchar_type, name="getchar")
    bzero_type = ir.FunctionType(void, (byte.as_pointer(), size_t))
    bzero = ir.Function(module, bzero_type, name="bzero")

    # These lines define an LLVM variable (index) to store the index pointer used in the
    # Brainfuck program.
    index_type = ir.IntType(INDEX_BIT_SIZE)
    index = builder.alloca(index_type)
    builder.store(ir.Constant(index_type, 0), index)

    # These lines define an LLVM variable (tape) to store the tape used in the
    # Brainfuck program.
    tape_type = byte
    # allocating memory
    tape = builder.alloca(tape_type, size=2 ** INDEX_BIT_SIZE)
    # filling zero in each byte of tape
    builder.call(bzero, (tape, size_t(2 ** INDEX_BIT_SIZE)))

    # 00000000
    zero8 = byte(0)
    # 11111111
    one8 = byte(1)

    # 11111111 11111111 11111111 11111111
    eof = int32(-1)

    # This defines a helper function get_tape_location(), which calculates the memory
    # location on the tape based on the current index value.
    def get_tape_location():
        index_value = builder.load(index)
        # index_value = builder.zext(index_value, int32)

        # This line computes the memory location on the tape based on the index value.
        # builder.gep() stands for "get element pointer" and is used to calculate a memory
        # address. Here, it calculates the memory address of the element on the tape at
        # the position indicated by the index_value. The tape variable represents the memory
        # space allocated for the tape in the Brainfuck program. The inbounds=True
        # parameter indicates that the generated pointer will not result in an out-of-bounds
        # memory access.
        location = builder.gep(tape, (index_value,), inbounds=True)
        return location

    def compile_instruction(single_instruction):
        # checking if the given instruction has loop
        if isinstance(single_instruction, list):
            # creating a basic block for beginning of the loop
            preloop = builder.append_basic_block(name="preloop")

            # In the LLVM IR, every block needs to be terminated. Our builder
            # is still at the end of the previous block, so we can just insert
            # an unconditional branching to the preloop branch.

            # branches control flow to the preloop block
            builder.branch(preloop)

            # This sets the insertion point for new instructions to the beginning of the
            # preloop block
            builder.position_at_start(preloop)

            # load tape value
            location = get_tape_location()
            tape_value = builder.load(location)

            # check tape value
            is_zero = builder.icmp_unsigned("==", tape_value, zero8)

            # We'll now create *another* block, but we won't terminate the
            # "preloop" block until later. This is because we need a reference
            # to both the "body" and the "postloop" block to know where to
            # jump.

            # This creates a basic block body for the loop body and sets the insertion
            # point for new instructions to the beginning of the boy block
            body = builder.append_basic_block(name="body")
            builder.position_at_start(body)
            for inner_instruction in single_instruction:
                # iterating over each single_instruction in the loop and compiling it recursively
                compile_instruction(inner_instruction)

            # branches control flow to the preloop block
            builder.branch(preloop)

            # create a basic block for the end of the loop
            postloop = builder.append_basic_block(name="postloop")

            # sets the insertion point for new instructions to the end of the preloop block
            # Termination of preloop
            builder.position_at_end(preloop)

            # conditional branch....if is zero, go to post loop....else continue in loop
            builder.cbranch(is_zero, postloop, body)

            # sets the insertion point for new instructions to the start of the postloop block
            builder.position_at_start(postloop)
        elif single_instruction == "+" or single_instruction == "-":
            location = get_tape_location()
            value = builder.load(location)

            if single_instruction == "+":
                new_value = builder.add(value, one8)
            else:
                new_value = builder.sub(value, one8)

            builder.store(new_value, location)
        elif single_instruction == ">" or single_instruction == "<":
            index_value = builder.load(index)

            if single_instruction == ">":
                index_value = builder.add(index_value, index_type(1))
            else:
                index_value = builder.sub(index_value, index_type(1))

            builder.store(index_value, index)

        elif single_instruction == ".":
            location = get_tape_location()
            tape_value = builder.load(location)
            tape_value = builder.zext(tape_value, int32)

            builder.call(putchar, (tape_value,))
        elif single_instruction == ",":
            location = get_tape_location()

            char = builder.call(getchar, ())
            is_eof = builder.icmp_unsigned("==", char, eof)
            with builder.if_else(is_eof) as (then, otherwise):
                with then:
                    builder.store(zero8, location)

                with otherwise:
                    char = builder.trunc(char, tape_type)
                    builder.store(char, location)

    for instruction in abstractSyntaxTree:
        compile_instruction(instruction)

    builder.ret(int32(0))

    return module


# courtesy of the llvmlite docs
def create_execution_engine():
    """
    Create an ExecutionEngine suitable for JIT code generation on
    the host CPU.  The engine is reusable for an arbitrary number of
    modules.
    """
    # Create a target machine representing the host
    target = llvm.Target.from_default_triple()
    target_machine = target.create_target_machine()
    # And an execution engine with an empty backing module
    backing_mod = llvm.parse_assembly("")
    engine = llvm.create_mcjit_compiler(backing_mod, target_machine)
    return engine


def main():
    argp = argparse.ArgumentParser()

    argp.add_argument("filename",
                      help="The brainfuck code file.")
    argp.add_argument("-i", "--ir", action="store_true",
                      help="Print out the human-readable LLVM IR to stderr")
    argp.add_argument('-r', '--run', action="store_true",
                      help="Run the brainfuck code with McJIT.")
    argp.add_argument('-c', '--bitcode', action="store_true",
                      help="Emit a bitcode file.")

    argv = argp.parse_args()

    llvm.initialize()
    llvm.initialize_native_target()
    llvm.initialize_native_asmprinter()

    with open(argv.filename) as bf_file:
        ir_module = bfToIntermediateRepresentation(bf_file.read())

    basename = os.path.basename(argv.filename)
    basename = os.path.splitext(basename)[0]

    if argv.ir:
        with open(basename + ".ll", "w") as f:
            f.write(str(ir_module))

        print("Wrote IR to", basename + ".ll")

    binding_module = llvm.parse_assembly(str(ir_module))
    binding_module.verify()

    if argv.bitcode:
        bitcode = binding_module.as_bitcode()

        with open(basename + ".bc", "wb") as output_file:
            output_file.write(bitcode)

        print("Wrote bitcode to", basename + ".bc")

    if argv.run:
        with create_execution_engine() as engine:
            engine.add_module(binding_module)
            engine.finalize_object()
            engine.run_static_constructors()

            func_ptr = engine.get_function_address("main")
            asm_main = ctypes.CFUNCTYPE(ctypes.c_int)(func_ptr)
            result = asm_main()
            sys.exit(result)


if __name__ == "__main__":
    main()
