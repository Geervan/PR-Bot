"""
Multi-language code parser using Tree-sitter.
Supports: Python, JavaScript, TypeScript, Java, C, C++, Go, Rust
"""

from tree_sitter import Language, Parser
from typing import Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class CodeSymbols:
    """Represents symbols extracted from a source file."""
    language: str = ""
    imports: List[str] = field(default_factory=list)
    from_imports: List[Dict[str, str]] = field(default_factory=list)
    functions: List[str] = field(default_factory=list)
    classes: List[str] = field(default_factory=list)
    function_calls: List[str] = field(default_factory=list)


class MultiLanguageParser:
    """
    Parses code in multiple languages using Tree-sitter.
    
    Supported languages:
    - Python (.py)
    - JavaScript (.js, .jsx, .mjs)
    - TypeScript (.ts, .tsx)
    - Java (.java)
    - C (.c, .h)
    - C++ (.cpp, .cc, .cxx, .hpp)
    - Go (.go)
    - Rust (.rs)
    """
    
    # Map file extensions to language names
    EXTENSION_MAP = {
        '.py': 'python',
        '.js': 'javascript',
        '.jsx': 'javascript',
        '.mjs': 'javascript',
        '.ts': 'typescript',
        '.tsx': 'typescript',
        '.java': 'java',
        '.c': 'c',
        '.h': 'c',
        '.cpp': 'cpp',
        '.cc': 'cpp',
        '.cxx': 'cpp',
        '.hpp': 'cpp',
        '.go': 'go',
        '.rs': 'rust',
    }
    
    def __init__(self):
        self._parsers: Dict[str, Parser] = {}
        self._languages: Dict[str, Language] = {}
        self._load_languages()
    
    def _load_languages(self):
        """Load all available language grammars."""
        language_modules = {
            'python': 'tree_sitter_python',
            'javascript': 'tree_sitter_javascript',
            'typescript': 'tree_sitter_typescript',
            'java': 'tree_sitter_java',
            'c': 'tree_sitter_c',
            'cpp': 'tree_sitter_cpp',
            'go': 'tree_sitter_go',
            'rust': 'tree_sitter_rust',
        }
        
        for lang_name, module_name in language_modules.items():
            try:
                module = __import__(module_name)
                # TypeScript module has separate language() functions
                if lang_name == 'typescript':
                    self._languages['typescript'] = Language(module.language_typescript())
                    self._languages['tsx'] = Language(module.language_tsx())
                else:
                    self._languages[lang_name] = Language(module.language())
                
                # Create parser
                parser = Parser(self._languages[lang_name])
                self._parsers[lang_name] = parser
                
            except ImportError:
                print(f"Warning: {module_name} not installed, {lang_name} support disabled")
            except Exception as e:
                print(f"Warning: Failed to load {lang_name}: {e}")
    
    def get_language(self, file_path: str) -> Optional[str]:
        """Detect language from file extension."""
        ext = '.' + file_path.split('.')[-1].lower() if '.' in file_path else ''
        return self.EXTENSION_MAP.get(ext)
    
    def parse(self, code: str, file_path: str) -> CodeSymbols:
        """Parse code and extract symbols based on file type."""
        language = self.get_language(file_path)
        
        if not language or language not in self._parsers:
            return CodeSymbols(language=language or "unknown")
        
        symbols = CodeSymbols(language=language)
        
        # Handle TSX separately
        if file_path.endswith('.tsx') and 'tsx' in self._languages:
            parser = Parser(self._languages['tsx'])
        else:
            parser = self._parsers[language]
        
        tree = parser.parse(bytes(code, "utf8"))
        root = tree.root_node
        
        # Language-specific extraction
        if language == 'python':
            self._extract_python(root, symbols, code)
        elif language in ('javascript', 'typescript'):
            self._extract_js_ts(root, symbols, code)
        elif language == 'java':
            self._extract_java(root, symbols, code)
        elif language in ('c', 'cpp'):
            self._extract_c_cpp(root, symbols, code)
        elif language == 'go':
            self._extract_go(root, symbols, code)
        elif language == 'rust':
            self._extract_rust(root, symbols, code)
        
        return symbols
    
    def _get_text(self, node, code: str) -> str:
        """Get text content of a node."""
        return code[node.start_byte:node.end_byte]
    
    def _extract_python(self, root, symbols: CodeSymbols, code: str):
        """Extract symbols from Python code."""
        self._traverse_python(root, symbols, code)
    
    def _traverse_python(self, node, symbols: CodeSymbols, code: str):
        """Recursively traverse Python AST."""
        if node.type == "import_statement":
            for child in node.children:
                if child.type == "dotted_name":
                    symbols.imports.append(self._get_text(child, code))
        
        elif node.type == "import_from_statement":
            module_name = None
            found_import = False
            for child in node.children:
                if child.type == "import":
                    found_import = True
                elif child.type == "dotted_name":
                    if not found_import:
                        module_name = self._get_text(child, code)
                    else:
                        if module_name:
                            symbols.from_imports.append({
                                "module": module_name,
                                "name": self._get_text(child, code)
                            })
        
        elif node.type == "function_definition":
            for child in node.children:
                if child.type == "identifier":
                    symbols.functions.append(self._get_text(child, code))
                    break
        
        elif node.type == "class_definition":
            for child in node.children:
                if child.type == "identifier":
                    symbols.classes.append(self._get_text(child, code))
                    break
        
        elif node.type == "call":
            if node.children:
                symbols.function_calls.append(self._get_text(node.children[0], code))
        
        for child in node.children:
            self._traverse_python(child, symbols, code)
    
    def _extract_js_ts(self, root, symbols: CodeSymbols, code: str):
        """Extract symbols from JavaScript/TypeScript code."""
        self._traverse_js_ts(root, symbols, code)
    
    def _traverse_js_ts(self, node, symbols: CodeSymbols, code: str):
        """Recursively traverse JS/TS AST."""
        # Import declarations: import X from 'Y'
        if node.type == "import_statement":
            for child in node.children:
                if child.type == "string":
                    symbols.imports.append(self._get_text(child, code).strip("'\""))
        
        # Function declarations
        elif node.type == "function_declaration":
            for child in node.children:
                if child.type == "identifier":
                    symbols.functions.append(self._get_text(child, code))
                    break
        
        # Method definitions (class methods)
        elif node.type == "method_definition":
            for child in node.children:
                if child.type in ("identifier", "property_identifier"):
                    symbols.functions.append(self._get_text(child, code))
                    break
        
        # Arrow functions with variable declaration
        elif node.type == "variable_declarator":
            name = None
            has_arrow = False
            for child in node.children:
                if child.type == "identifier":
                    name = self._get_text(child, code)
                elif child.type == "arrow_function":
                    has_arrow = True
            if name and has_arrow:
                symbols.functions.append(name)
        
        # Class declarations (works for both JS and TS)
        elif node.type == "class_declaration":
            for child in node.children:
                if child.type in ("identifier", "type_identifier"):
                    symbols.classes.append(self._get_text(child, code))
                    break
        
        # Function calls
        elif node.type == "call_expression":
            if node.children:
                symbols.function_calls.append(self._get_text(node.children[0], code))
        
        for child in node.children:
            self._traverse_js_ts(child, symbols, code)
    
    def _extract_java(self, root, symbols: CodeSymbols, code: str):
        """Extract symbols from Java code."""
        self._traverse_java(root, symbols, code)
    
    def _traverse_java(self, node, symbols: CodeSymbols, code: str):
        """Recursively traverse Java AST."""
        # Import declarations
        if node.type == "import_declaration":
            for child in node.children:
                if child.type == "scoped_identifier":
                    symbols.imports.append(self._get_text(child, code))
        
        # Class declarations
        elif node.type == "class_declaration":
            for child in node.children:
                if child.type == "identifier":
                    symbols.classes.append(self._get_text(child, code))
                    break
        
        # Interface declarations
        elif node.type == "interface_declaration":
            for child in node.children:
                if child.type == "identifier":
                    symbols.classes.append(self._get_text(child, code))
                    break
        
        # Method declarations
        elif node.type == "method_declaration":
            for child in node.children:
                if child.type == "identifier":
                    symbols.functions.append(self._get_text(child, code))
                    break
        
        # Method invocations
        elif node.type == "method_invocation":
            for child in node.children:
                if child.type == "identifier":
                    symbols.function_calls.append(self._get_text(child, code))
                    break
        
        for child in node.children:
            self._traverse_java(child, symbols, code)
    
    def _extract_c_cpp(self, root, symbols: CodeSymbols, code: str):
        """Extract symbols from C/C++ code."""
        self._traverse_c_cpp(root, symbols, code)
    
    def _traverse_c_cpp(self, node, symbols: CodeSymbols, code: str):
        """Recursively traverse C/C++ AST."""
        # Include directives
        if node.type == "preproc_include":
            for child in node.children:
                if child.type in ("string_literal", "system_lib_string"):
                    symbols.imports.append(self._get_text(child, code).strip('<>"'))
        
        # Function definitions
        elif node.type == "function_definition":
            for child in node.children:
                if child.type == "function_declarator":
                    for subchild in child.children:
                        if subchild.type == "identifier":
                            symbols.functions.append(self._get_text(subchild, code))
                            break
        
        # Class/struct definitions (C++)
        elif node.type in ("class_specifier", "struct_specifier"):
            for child in node.children:
                if child.type == "type_identifier":
                    symbols.classes.append(self._get_text(child, code))
                    break
        
        # Function calls
        elif node.type == "call_expression":
            if node.children:
                symbols.function_calls.append(self._get_text(node.children[0], code))
        
        for child in node.children:
            self._traverse_c_cpp(child, symbols, code)
    
    def _extract_go(self, root, symbols: CodeSymbols, code: str):
        """Extract symbols from Go code."""
        self._traverse_go(root, symbols, code)
    
    def _traverse_go(self, node, symbols: CodeSymbols, code: str):
        """Recursively traverse Go AST."""
        # Import declarations
        if node.type == "import_spec":
            for child in node.children:
                if child.type == "interpreted_string_literal":
                    symbols.imports.append(self._get_text(child, code).strip('"'))
        
        # Function declarations
        elif node.type == "function_declaration":
            for child in node.children:
                if child.type == "identifier":
                    symbols.functions.append(self._get_text(child, code))
                    break
        
        # Method declarations
        elif node.type == "method_declaration":
            for child in node.children:
                if child.type == "field_identifier":
                    symbols.functions.append(self._get_text(child, code))
                    break
        
        # Type declarations (structs, interfaces)
        elif node.type == "type_spec":
            for child in node.children:
                if child.type == "type_identifier":
                    symbols.classes.append(self._get_text(child, code))
                    break
        
        # Function calls
        elif node.type == "call_expression":
            if node.children:
                symbols.function_calls.append(self._get_text(node.children[0], code))
        
        for child in node.children:
            self._traverse_go(child, symbols, code)
    
    def _extract_rust(self, root, symbols: CodeSymbols, code: str):
        """Extract symbols from Rust code."""
        self._traverse_rust(root, symbols, code)
    
    def _traverse_rust(self, node, symbols: CodeSymbols, code: str):
        """Recursively traverse Rust AST."""
        # Use declarations
        if node.type == "use_declaration":
            for child in node.children:
                if child.type in ("scoped_identifier", "identifier"):
                    symbols.imports.append(self._get_text(child, code))
        
        # Function definitions
        elif node.type == "function_item":
            for child in node.children:
                if child.type == "identifier":
                    symbols.functions.append(self._get_text(child, code))
                    break
        
        # Struct definitions
        elif node.type == "struct_item":
            for child in node.children:
                if child.type == "type_identifier":
                    symbols.classes.append(self._get_text(child, code))
                    break
        
        # Impl blocks (trait implementations)
        elif node.type == "impl_item":
            for child in node.children:
                if child.type == "type_identifier":
                    symbols.classes.append(self._get_text(child, code))
                    break
        
        # Function calls
        elif node.type == "call_expression":
            if node.children:
                symbols.function_calls.append(self._get_text(node.children[0], code))
        
        for child in node.children:
            self._traverse_rust(child, symbols, code)
    
    def get_summary(self, code: str, file_path: str) -> str:
        """Returns a compact summary of the code suitable for LLM context."""
        symbols = self.parse(code, file_path)
        
        lines = [f"Language: {symbols.language}"]
        
        if symbols.imports:
            lines.append(f"Imports: {', '.join(symbols.imports[:10])}")
        
        if symbols.from_imports:
            from_str = [f"{fi['module']}.{fi['name']}" for fi in symbols.from_imports[:10]]
            lines.append(f"From Imports: {', '.join(from_str)}")
        
        if symbols.classes:
            lines.append(f"Classes/Types: {', '.join(symbols.classes[:10])}")
        
        if symbols.functions:
            lines.append(f"Functions: {', '.join(symbols.functions[:15])}")
        
        if symbols.function_calls:
            unique_calls = list(set(symbols.function_calls))[:15]
            lines.append(f"Calls: {', '.join(unique_calls)}")
        
        return "\n".join(lines)
    
    def is_supported(self, file_path: str) -> bool:
        """Check if a file type is supported."""
        return self.get_language(file_path) is not None


# Singleton instance
code_parser = MultiLanguageParser()

# For backwards compatibility
python_parser = code_parser
