"""Tests for TypeScript scanner."""

import textwrap
from pathlib import Path

from testforge.infrastructure.scanners.typescript_scanner import TypeScriptScanner


class TestTypeScriptScanner:
    def test_scan_empty_dir(self, tmp_path: Path):
        scanner = TypeScriptScanner()
        analysis = scanner.scan(tmp_path)
        assert analysis.total_modules == 0

    def test_scan_extracts_functions(self, tmp_path: Path):
        (tmp_path / "utils.ts").write_text(textwrap.dedent("""\
            export function greet(name: string): string {
                return `Hello ${name}`;
            }

            export async function fetchData(url: string): Promise<any> {
                return fetch(url);
            }

            const add = (a: number, b: number): number => a + b;
        """))
        scanner = TypeScriptScanner()
        analysis = scanner.scan(tmp_path)
        assert analysis.total_modules == 1
        func_names = {f.name for f in analysis.modules[0].functions}
        assert "greet" in func_names
        assert "add" in func_names

    def test_scan_extracts_classes(self, tmp_path: Path):
        (tmp_path / "service.ts").write_text(textwrap.dedent("""\
            export class UserService extends BaseService {
                async getUser(id: string): Promise<User> {
                    return this.db.find(id);
                }

                deleteUser(id: string): void {
                    this.db.remove(id);
                }
            }
        """))
        scanner = TypeScriptScanner()
        analysis = scanner.scan(tmp_path)
        classes = analysis.modules[0].classes
        assert len(classes) == 1
        assert classes[0].name == "UserService"
        assert classes[0].bases == ("BaseService",)
        assert len(classes[0].methods) >= 2

    def test_scan_extracts_routes(self, tmp_path: Path):
        (tmp_path / "routes.ts").write_text(textwrap.dedent("""\
            import express from "express";
            const app = express();
            app.get("/users", getUsers);
            app.post("/users", createUser);
            app.delete("/users/:id", deleteUser);
        """))
        scanner = TypeScriptScanner()
        analysis = scanner.scan(tmp_path)
        assert len(analysis.endpoints) == 3
        methods = {ep.method for ep in analysis.endpoints}
        assert methods == {"GET", "POST", "DELETE"}

    def test_scan_extracts_imports(self, tmp_path: Path):
        (tmp_path / "app.ts").write_text(textwrap.dedent("""\
            import express from "express";
            import { UserService } from "./services/user";
            import axios from "axios";
        """))
        scanner = TypeScriptScanner()
        analysis = scanner.scan(tmp_path)
        imports = set(analysis.modules[0].imports)
        assert "express" in imports
        assert "axios" in imports
        assert "./services/user" in imports

    def test_scan_skips_node_modules(self, tmp_path: Path):
        nm = tmp_path / "node_modules" / "pkg"
        nm.mkdir(parents=True)
        (nm / "index.ts").write_text("export function hidden(): void {}")
        (tmp_path / "app.ts").write_text("export function visible(): void {}")

        scanner = TypeScriptScanner()
        analysis = scanner.scan(tmp_path)
        assert analysis.total_modules == 1

    def test_scan_languages_detection(self, tmp_path: Path):
        (tmp_path / "app.ts").write_text("export function a(): void {}")
        (tmp_path / "legacy.js").write_text("function b() {}")

        scanner = TypeScriptScanner()
        analysis = scanner.scan(tmp_path)
        assert "typescript" in analysis.languages
        assert "javascript" in analysis.languages
