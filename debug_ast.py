"""Debug script to understand Tree-sitter AST structure."""
import os
os.environ["GEMINI_API_KEYS"] = "fake_key"
os.environ["APP_ID"] = "123"
os.environ["PRIVATE_KEY_PATH"] = "fake_path"
os.environ["WEBHOOK_SECRET"] = "fake_secret"

import tree_sitter_python as tspython
from tree_sitter import Language, Parser

lang = Language(tspython.language())
parser = Parser(lang)

code = '''from typing import List, Dict
from app.utils import helper_function'''

tree = parser.parse(bytes(code, 'utf8'))

def print_tree(node, indent=0):
    print("  " * indent + f"{node.type}: '{code[node.start_byte:node.end_byte][:50]}'")
    for child in node.children:
        print_tree(child, indent + 1)

print_tree(tree.root_node)
