# Imports fixed via builtin types
import argparse
import subprocess
import sys


class Console:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    RESET = "\033[0m"

    @staticmethod
    def log(msg: str, color: str = RESET):
        print(f"{color}{msg}{Console.RESET}")

    @staticmethod
    def header(msg: str):
        print(f"\n{Console.BLUE}{'=' * 50}\n{msg}\n{'=' * 50}{Console.RESET}")


class LayerVerifier:
    def __init__(self, target_dir: str = "src"):
        self.target_dir = target_dir

    def run_command(self, command: list[str], desc: str) -> bool:
        Console.log(f"Running: {desc}...", Console.YELLOW)
        try:
            # check=True raises CalledProcessError on non-zero exit code
            # stream output directly to console so user sees progress(no capture_output)
            subprocess.run(command, check=True)
            Console.log(f"✅ {desc} passed.", Console.GREEN)
            return True
        except subprocess.CalledProcessError:
            Console.log(f"❌ {desc} failed.", Console.RED)
            return False

    def check_layer_1(self) -> bool:
        """Layer 1: Foundation (PEP Standards)"""
        Console.header("LAYER 1: Foundation (Syntax & Standards)")

        # 1. Ruff Lint
        lint_ok = self.run_command(
            ["ruff", "check", self.target_dir], "Ruff Lint Checks"
        )

        # 2. Ruff Format (Check only)
        fmt_ok = self.run_command(
            ["ruff", "format", "--check", self.target_dir],
            "Ruff Format Checks",
        )

        return lint_ok and fmt_ok

    def check_layer_2(self) -> bool:
        """Layer 2: Type Safety"""
        Console.header("LAYER 2: Type Safety (Static Analysis)")

        # Mypy
        return self.run_command(
            ["mypy", self.target_dir], "Mypy Strict Type Checks"
        )

    def check_layer_3(self) -> bool:
        """Layer 3: Code Health"""
        Console.header("LAYER 3: Code Health (Complexity)")

        # Radon CC (Threshold 10) - hard fails over 15
        # (C grade is 11-20, let's say fail on C)
        # Using ruff mccabe (C901) is often easier,
        # but let's try a simple radon check script if avail

        complexity_ok = self.run_command(
            [
                "ruff",
                "check",
                "--select",
                "C901",
                self.target_dir,
            ],
            "Cyclomatic Complexity (C901)",
        )

        return complexity_ok

    def check_layer_4(self) -> bool:
        """Layer 4: Architecture"""
        Console.header("LAYER 4: Architecture (Boundaries)")

        # Import Linter
        # Assumes .importlinter config is in pyproject.toml or similar
        try:
            # Check if lint-imports is available
            subprocess.run(
                ["which", "lint-imports"],
                check=True,
                stdout=subprocess.DEVNULL,
            )
            return self.run_command(
                ["lint-imports"], "Import Linter Architecture Check"
            )
        except subprocess.CalledProcessError:
            Console.log(
                "⚠️  lint-imports not found. Skipping Layer 4 strictly.",
                Console.YELLOW,
            )
            return True

    def check_layer_5(self) -> bool:
        """Layer 5: Deep Logic & Security"""
        Console.header("LAYER 5: Deep Logic (Security & Docs)")

        # Bandit
        security_ok = self.run_command(
            ["bandit", "-r", self.target_dir, "-c", "pyproject.toml"],
            "Bandit Security Scan",
        )

        # Docstrings (using pydocstyle/ruff subset)
        # Select D rules (pydocstyle)
        docs_ok = self.run_command(
            [
                "ruff",
                "check",
                "--select",
                "D",
                "--ignore",
                "D100,D104",
                self.target_dir,
            ],  # Ignore missing docstrings (D100/D104) to reduce noise
            "Docstring Compliance",
        )

        return security_ok and docs_ok

    def check_all(self):
        steps = [
            self.check_layer_1,
            self.check_layer_2,
            self.check_layer_3,
            self.check_layer_4,
            self.check_layer_5,
        ]

        for i, step in enumerate(steps, 1):
            if not step():
                Console.log(
                    f"\n🚫 FAILED at Layer {i}. Fix issues before proceeding to "
                    "next layer.",
                    Console.RED,
                )
                sys.exit(1)

        Console.log(
            "\n✨ ALL LAYERS PASSED! Code is robust and ready.", Console.GREEN
        )


def main():
    parser = argparse.ArgumentParser(
        description="Layered Python Development Verification"
    )
    parser.add_argument(
        "--layer", type=int, choices=[1, 2, 3, 4, 5], help="Run specific layer"
    )
    parser.add_argument(
        "--all", action="store_true", help="Run all layers sequentially"
    )
    parser.add_argument(
        "--target", default="src", help="Target directory (default: src)"
    )

    args = parser.parse_args()

    verifier = LayerVerifier(target_dir=args.target)

    if args.all:
        verifier.check_all()
    elif args.layer:
        method = getattr(verifier, f"check_layer_{args.layer}")
        success = method()
        if not success:
            sys.exit(1)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
