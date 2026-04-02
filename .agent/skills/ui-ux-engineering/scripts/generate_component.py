#!/usr/bin/env python3
"""
Component Generator Script for Vitruviano Frontend

Generates React component boilerplate following the project's
design system and accessibility standards.
"""

import sys
from pathlib import Path
from textwrap import dedent


def generate_component(name: str, category: str) -> str:
    """Generate a React component with proper structure."""
    return dedent(f"""
        /**
         * @component {name}
         * @description TODO: Add component description
         */

        import {{ type ReactNode, forwardRef }} from "react";

        // Types
        interface {name}Props {{
          /** Children elements */
          children?: ReactNode;
          /** Optional className for customization */
          className?: string;
          /** Variant style */
          variant?: "primary" | "secondary" | "ghost";
          /** Size variant */
          size?: "sm" | "md" | "lg";
          /** Disabled state */
          disabled?: boolean;
        }}

        // Variant styles
        const variantStyles = {{
          primary: "bg-[var(--accent-teal)] text-[#06151a] hover:bg-[var(--accent-teal)]/80",
          secondary: "bg-[var(--surface-2)] text-[var(--text-primary)] hover:bg-[var(--surface-3)]",
          ghost: "bg-transparent text-[var(--text-secondary)] hover:bg-[var(--surface-2)]",
        }} as const;

        // Size styles
        const sizeStyles = {{
          sm: "px-3 py-1.5 text-xs",
          md: "px-4 py-2 text-sm",
          lg: "px-6 py-3 text-base",
        }} as const;

        /**
         * {name} component
         *
         * @example
         * ```tsx
         * <{name} variant="primary" size="md">
         *   Content
         * </{name}>
         * ```
         */
        const {name} = forwardRef<HTMLDivElement, {name}Props>(
          ({{ children, className = "", variant = "primary", size = "md", disabled = false }}, ref) => {{
            const baseStyles = `
              inline-flex items-center justify-center
              rounded-[var(--radius-md)]
              font-medium
              transition-[var(--transition-fast)]
              focus-visible:outline-2 focus-visible:outline-[var(--accent-teal)] focus-visible:outline-offset-2
              disabled:opacity-50 disabled:cursor-not-allowed
            `;

            return (
              <div
                ref={{ref}}
                className={{`${{baseStyles}} ${{variantStyles[variant]}} ${{sizeStyles[size]}} ${{className}}`}}
                aria-disabled={{disabled}}
              >
                {{children}}
              </div>
            );
          }}
        );

        {name}.displayName = "{name}";

        export default {name};
    """).strip()


def generate_index(name: str) -> str:
    """Generate index.ts export file."""
    return f'export {{ default as {name} }} from "./{name}";\n'


def main() -> None:
    """Main entry point."""
    if len(sys.argv) < 3:
        print("Usage: python generate_component.py <ComponentName> <category>")
        print("Categories: common, layout, viewer, study")
        sys.exit(1)

    name = sys.argv[1]
    category = sys.argv[2]

    # Validate name
    if not name[0].isupper():
        print("Error: Component name must be PascalCase")
        sys.exit(1)

    # Validate category
    valid_categories = ["common", "layout", "viewer", "study"]
    if category not in valid_categories:
        print(f"Error: Category must be one of {valid_categories}")
        sys.exit(1)

    # Determine output path
    base_path = Path("frontend/src/components") / category
    component_path = base_path / f"{name}.tsx"

    if component_path.exists():
        print(f"Error: Component {component_path} already exists")
        sys.exit(1)

    # Create directory if needed
    base_path.mkdir(parents=True, exist_ok=True)

    # Write component
    component_path.write_text(
        generate_component(name, category), encoding="utf-8"
    )
    print(f"✅ Created {component_path}")

    # Update index.ts
    index_path = base_path / "index.ts"
    if index_path.exists():
        with open(index_path, "a", encoding="utf-8") as f:
            f.write(generate_index(name))
    else:
        index_path.write_text(generate_index(name), encoding="utf-8")

    print(f"✅ Updated {index_path}")
    print(f"\n📦 Component '{name}' created in '{category}' category")


if __name__ == "__main__":
    main()
