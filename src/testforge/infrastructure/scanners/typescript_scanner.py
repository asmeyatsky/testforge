"""TypeScript/JavaScript scanner — regex-based parsing (no external deps)."""

from __future__ import annotations

import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

from testforge.domain.entities import CodebaseAnalysis
from testforge.domain.value_objects import (
    APIEndpoint,
    ClassInfo,
    DependencyGraph,
    FilePath,
    FunctionSignature,
    ModuleInfo,
)

# Regex patterns for TS/JS extraction
_FUNCTION_RE = re.compile(
    r"(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\(([^)]*)\)(?:\s*:\s*([^\s{]+))?"
)
_ARROW_RE = re.compile(
    r"(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\(([^)]*)\)(?:\s*:\s*([^\s=]+))?\s*=>"
)
_CLASS_RE = re.compile(
    r"(?:export\s+)?class\s+(\w+)(?:\s+extends\s+([\w.]+))?\s*\{"
)
_METHOD_RE = re.compile(
    r"(?:async\s+)?(\w+)\s*\(([^)]*)\)(?:\s*:\s*([^\s{]+))?\s*\{"
)
_IMPORT_RE = re.compile(
    r"import\s+.*?from\s+['\"]([^'\"]+)['\"]"
)
_ROUTE_RE = re.compile(
    r"(?:app|router)\.(get|post|put|delete|patch)\s*\(\s*['\"]([^'\"]+)['\"]"
)
_DECORATOR_RE = re.compile(
    r"@(\w+)\s*\(([^)]*)\)"
)


class TypeScriptScanner:
    """Scans TypeScript and JavaScript files using regex patterns."""

    def scan(self, root_path: Path) -> CodebaseAnalysis:
        logger.info("Scanning TypeScript/JavaScript files in %s", root_path)
        ts_files = sorted(
            f for ext in ("*.ts", "*.tsx", "*.js", "*.jsx")
            for f in root_path.rglob(ext)
        )
        ts_files = [
            f for f in ts_files
            if not any(
                part.startswith(".") or part in ("node_modules", "dist", "build", ".next")
                for part in f.parts
            )
            and ".d.ts" not in f.name
        ]

        modules: list[ModuleInfo] = []
        all_endpoints: list[APIEndpoint] = []
        edges: list[tuple[str, str]] = []

        for ts_file in ts_files:
            try:
                source = ts_file.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue

            rel_path = str(ts_file.relative_to(root_path))
            functions, classes, imports, endpoints = self._extract(source, rel_path)

            modules.append(
                ModuleInfo(
                    file_path=FilePath(ts_file.relative_to(root_path)),
                    functions=tuple(functions),
                    classes=tuple(classes),
                    imports=tuple(imports),
                    endpoints=tuple(endpoints),
                )
            )
            all_endpoints.extend(endpoints)

            for imp in imports:
                if not imp.startswith("."):
                    edges.append((rel_path, imp))
                else:
                    edges.append((rel_path, imp))

        languages = set()
        for f in ts_files:
            if f.suffix in (".ts", ".tsx"):
                languages.add("typescript")
            else:
                languages.add("javascript")

        return CodebaseAnalysis(
            root_path=str(root_path),
            modules=tuple(modules),
            dependency_graph=DependencyGraph(edges=tuple(edges)),
            endpoints=tuple(all_endpoints),
            languages=tuple(sorted(languages)) or ("typescript",),
        )

    def _extract(
        self, source: str, file_path: str
    ) -> tuple[list[FunctionSignature], list[ClassInfo], list[str], list[APIEndpoint]]:
        functions = self._extract_functions(source)
        classes = self._extract_classes(source)
        imports = self._extract_imports(source)
        endpoints = self._extract_endpoints(source, file_path)
        return functions, classes, imports, endpoints

    def _extract_functions(self, source: str) -> list[FunctionSignature]:
        functions: list[FunctionSignature] = []
        seen: set[str] = set()

        for match in _FUNCTION_RE.finditer(source):
            name = match.group(1)
            if name not in seen:
                seen.add(name)
                params = self._parse_params(match.group(2))
                is_async = "async" in source[max(0, match.start() - 10):match.start()]
                line_num = source[:match.start()].count("\n") + 1
                functions.append(FunctionSignature(
                    name=name, parameters=tuple(params),
                    return_type=match.group(3),
                    is_async=is_async, line_number=line_num,
                ))

        for match in _ARROW_RE.finditer(source):
            name = match.group(1)
            if name not in seen:
                seen.add(name)
                params = self._parse_params(match.group(2))
                is_async = "async" in source[max(0, match.start() - 10):match.start() + 30]
                line_num = source[:match.start()].count("\n") + 1
                functions.append(FunctionSignature(
                    name=name, parameters=tuple(params),
                    return_type=match.group(3),
                    is_async=is_async, line_number=line_num,
                ))

        return functions

    def _extract_classes(self, source: str) -> list[ClassInfo]:
        classes: list[ClassInfo] = []

        for match in _CLASS_RE.finditer(source):
            name = match.group(1)
            base = match.group(2)
            bases = (base,) if base else ()
            line_num = source[:match.start()].count("\n") + 1

            # Extract methods within the class body
            class_start = match.end()
            class_body = self._extract_block(source, class_start - 1)
            methods: list[FunctionSignature] = []
            for m_match in _METHOD_RE.finditer(class_body):
                m_name = m_match.group(1)
                if m_name in ("if", "for", "while", "switch", "catch"):
                    continue
                params = self._parse_params(m_match.group(2))
                m_async = "async" in class_body[max(0, m_match.start() - 10):m_match.start()]
                methods.append(FunctionSignature(
                    name=m_name, parameters=tuple(params),
                    return_type=m_match.group(3), is_async=m_async,
                ))

            classes.append(ClassInfo(
                name=name, methods=tuple(methods),
                bases=bases, line_number=line_num,
            ))

        return classes

    def _extract_imports(self, source: str) -> list[str]:
        return [m.group(1) for m in _IMPORT_RE.finditer(source)]

    def _extract_endpoints(self, source: str, file_path: str) -> list[APIEndpoint]:
        endpoints: list[APIEndpoint] = []
        for match in _ROUTE_RE.finditer(source):
            method = match.group(1).upper()
            path = match.group(2)
            # Try to find handler name (next function-like pattern or inline)
            after = source[match.end():match.end() + 100]
            handler_match = re.search(r"(\w+)\s*[),]", after)
            handler_name = handler_match.group(1) if handler_match else f"handler_{path.strip('/').replace('/', '_')}"
            endpoints.append(APIEndpoint(
                method=method, path=path,
                handler_name=handler_name, file_path=file_path,
            ))
        return endpoints

    @staticmethod
    def _parse_params(params_str: str) -> list[str]:
        if not params_str.strip():
            return []
        params: list[str] = []
        for p in params_str.split(","):
            p = p.strip()
            # Remove type annotations (e.g., "name: string")
            name = p.split(":")[0].split("=")[0].split("?")[0].strip()
            if name:
                params.append(name)
        return params

    @staticmethod
    def _extract_block(source: str, start: int) -> str:
        """Extract a brace-delimited block starting from the { at position start."""
        depth = 0
        i = start
        while i < len(source):
            if source[i] == "{":
                depth += 1
            elif source[i] == "}":
                depth -= 1
                if depth == 0:
                    return source[start:i + 1]
            i += 1
        return source[start:]
