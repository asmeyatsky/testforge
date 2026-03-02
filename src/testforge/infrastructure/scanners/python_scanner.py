"""Python AST scanner — fully working."""

from __future__ import annotations

import ast
from pathlib import Path

from testforge.domain.entities import CodebaseAnalysis
from testforge.domain.value_objects import (
    APIEndpoint,
    ClassInfo,
    DependencyGraph,
    FilePath,
    FunctionSignature,
    ModuleInfo,
)


_ROUTE_DECORATORS = frozenset({
    "route", "get", "post", "put", "delete", "patch",
    "app.route", "app.get", "app.post", "app.put", "app.delete",
    "router.get", "router.post", "router.put", "router.delete",
    "api_view",
})


class PythonScanner:
    """Scans Python files using the ast module."""

    def scan(self, root_path: Path) -> CodebaseAnalysis:
        py_files = sorted(root_path.rglob("*.py"))
        # Skip hidden dirs, __pycache__, venvs, node_modules
        py_files = [
            f for f in py_files
            if not any(
                part.startswith(".") or part in ("__pycache__", "venv", ".venv", "node_modules")
                for part in f.parts
            )
        ]

        modules: list[ModuleInfo] = []
        all_endpoints: list[APIEndpoint] = []
        edges: list[tuple[str, str]] = []

        for py_file in py_files:
            try:
                source = py_file.read_text(encoding="utf-8")
                tree = ast.parse(source, filename=str(py_file))
            except (SyntaxError, UnicodeDecodeError):
                continue

            rel_path = str(py_file.relative_to(root_path))
            functions, classes, imports, endpoints = self._extract(tree, rel_path)

            modules.append(
                ModuleInfo(
                    file_path=FilePath(py_file.relative_to(root_path)),
                    functions=tuple(functions),
                    classes=tuple(classes),
                    imports=tuple(imports),
                    endpoints=tuple(endpoints),
                )
            )
            all_endpoints.extend(endpoints)

            for imp in imports:
                edges.append((rel_path, imp))

        return CodebaseAnalysis(
            root_path=str(root_path),
            modules=tuple(modules),
            dependency_graph=DependencyGraph(edges=tuple(edges)),
            endpoints=tuple(all_endpoints),
            languages=("python",),
        )

    def _extract(
        self, tree: ast.Module, file_path: str
    ) -> tuple[
        list[FunctionSignature],
        list[ClassInfo],
        list[str],
        list[APIEndpoint],
    ]:
        functions: list[FunctionSignature] = []
        classes: list[ClassInfo] = []
        imports: list[str] = []
        endpoints: list[APIEndpoint] = []

        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)
            elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                func = self._parse_function(node)
                functions.append(func)
                ep = self._check_endpoint(node, file_path)
                if ep:
                    endpoints.append(ep)
            elif isinstance(node, ast.ClassDef):
                cls = self._parse_class(node, file_path)
                classes.append(cls)
                # Check class methods for endpoints
                for item in ast.iter_child_nodes(node):
                    if isinstance(item, ast.FunctionDef | ast.AsyncFunctionDef):
                        ep = self._check_endpoint(item, file_path)
                        if ep:
                            endpoints.append(ep)

        return functions, classes, imports, endpoints

    def _parse_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> FunctionSignature:
        params = []
        for arg in node.args.args:
            params.append(arg.arg)

        decorators = [self._decorator_name(d) for d in node.decorator_list]
        return_type = ast.unparse(node.returns) if node.returns else None
        docstring = ast.get_docstring(node)

        return FunctionSignature(
            name=node.name,
            parameters=tuple(params),
            return_type=return_type,
            decorators=tuple(decorators),
            is_async=isinstance(node, ast.AsyncFunctionDef),
            docstring=docstring,
            line_number=node.lineno,
        )

    def _parse_class(self, node: ast.ClassDef, file_path: str) -> ClassInfo:
        methods: list[FunctionSignature] = []
        for item in ast.iter_child_nodes(node):
            if isinstance(item, ast.FunctionDef | ast.AsyncFunctionDef):
                methods.append(self._parse_function(item))

        bases = [ast.unparse(b) for b in node.bases]
        decorators = [self._decorator_name(d) for d in node.decorator_list]
        docstring = ast.get_docstring(node)

        return ClassInfo(
            name=node.name,
            methods=tuple(methods),
            bases=tuple(bases),
            decorators=tuple(decorators),
            docstring=docstring,
            line_number=node.lineno,
        )

    def _check_endpoint(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef, file_path: str
    ) -> APIEndpoint | None:
        for dec in node.decorator_list:
            dec_name = self._decorator_name(dec)
            if any(route in dec_name for route in _ROUTE_DECORATORS):
                method, path = self._extract_route_info(dec, dec_name)
                return APIEndpoint(
                    method=method,
                    path=path,
                    handler_name=node.name,
                    file_path=file_path,
                )
        return None

    def _extract_route_info(self, dec: ast.expr, dec_name: str) -> tuple[str, str]:
        method = "GET"
        path = "/"

        # Determine HTTP method from decorator name
        name_lower = dec_name.lower()
        for m in ("post", "put", "delete", "patch"):
            if m in name_lower:
                method = m.upper()
                break

        # Extract path from first argument
        if isinstance(dec, ast.Call) and dec.args:
            first_arg = dec.args[0]
            if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
                path = first_arg.value

        return method, path

    @staticmethod
    def _decorator_name(node: ast.expr) -> str:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            return ast.unparse(node)
        if isinstance(node, ast.Call):
            return PythonScanner._decorator_name(node.func)
        return ast.unparse(node)
