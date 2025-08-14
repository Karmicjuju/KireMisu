#!/usr/bin/env python3
"""
Coverage Comparison Script for KireMisu

Generates side-by-side comparison showing:
- Which lines are covered by unit vs integration tests
- Coverage gaps that only integration tests fill
- Redundant coverage areas
- Overall coverage statistics by test suite
"""

import html
import os
import sys

try:
    import coverage
except ImportError:
    print("Error: coverage package not found. Please install with: pip install coverage")
    sys.exit(1)


def load_coverage_data(context: str) -> dict[str, set[int]]:
    """Load coverage data for a specific context using coverage.py API."""
    coverage_file = f".coverage.{context}"
    if not os.path.exists(coverage_file):
        return {}

    try:
        # Use coverage.py API for proper data parsing
        cov = coverage.Coverage(data_file=coverage_file)
        cov.load()

        coverage_data = {}

        # Get list of measured files
        measured_files = cov.get_data().measured_files()

        for file_path in measured_files:
            # Get executed lines for this file
            analysis = cov.analysis2(file_path)
            if analysis:
                _, executed_lines, _, _ = analysis
                # Convert relative paths to project-relative paths
                rel_path = os.path.relpath(file_path, os.getcwd())
                coverage_data[rel_path] = set(executed_lines)

        return coverage_data

    except Exception as e:
        print(f"Error loading coverage data for {context}: {e}")
        print(f"Make sure to run: make test-coverage-{context}")
        return {}


def get_coverage_files() -> list[str]:
    """Get list of available coverage files."""
    # Define allowed contexts for security
    allowed_contexts = {"unit", "integration", "api", "security", "performance", "combined"}

    coverage_files = []
    for file in os.listdir("."):
        if file.startswith(".coverage.") and not file.endswith(".lock"):
            context = file.replace(".coverage.", "")
            # Validate context name for security
            if context in allowed_contexts:
                coverage_files.append(context)
            else:
                print(f"Warning: Skipping unknown coverage context: {context}")
    return sorted(coverage_files)


def analyze_coverage_overlap(contexts: list[str]) -> dict:
    """Analyze coverage overlap between different test contexts."""
    coverage_data = {}

    # Load coverage for each context
    for context in contexts:
        coverage_data[context] = load_coverage_data(context)

    # Find all files covered by any context
    all_files = set()
    for context_data in coverage_data.values():
        all_files.update(context_data.keys())

    analysis = {
        "contexts": contexts,
        "total_files": len(all_files),
        "coverage_by_context": {},
        "overlap_analysis": {},
        "unique_coverage": {},
        "files": {},
    }

    # Analyze each context
    for context in contexts:
        context_data = coverage_data[context]
        analysis["coverage_by_context"][context] = {
            "files_covered": len(context_data),
            "total_lines": sum(len(lines) for lines in context_data.values()),
        }

    # Analyze each file
    for file_path in all_files:
        file_analysis = {"covered_by": [], "line_coverage": {}}

        for context in contexts:
            if file_path in coverage_data[context]:
                file_analysis["covered_by"].append(context)
                file_analysis["line_coverage"][context] = len(coverage_data[context][file_path])

        analysis["files"][file_path] = file_analysis

    return analysis


def generate_html_report(analysis: dict, output_dir: str) -> None:
    """Generate HTML comparison report."""
    os.makedirs(output_dir, exist_ok=True)

    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>KireMisu Coverage Comparison Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .summary {{ background: #f5f5f5; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
        .context {{ margin: 10px 0; }}
        .file-table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        .file-table th, .file-table td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        .file-table th {{ background-color: #f2f2f2; }}
        .covered {{ background-color: #d4edda; }}
        .not-covered {{ background-color: #f8d7da; }}
        .partial {{ background-color: #fff3cd; }}
        .context-badge {{
            display: inline-block; padding: 2px 6px; margin: 2px;
            border-radius: 3px; font-size: 0.8em; color: white;
        }}
        .unit {{ background-color: #007bff; }}
        .integration {{ background-color: #28a745; }}
        .api {{ background-color: #ffc107; color: black; }}
        .security {{ background-color: #dc3545; }}
        .combined {{ background-color: #6c757d; }}
    </style>
</head>
<body>
    <h1>KireMisu Coverage Comparison Report</h1>

    <div class="summary">
        <h2>Summary</h2>
        <p><strong>Total Files Analyzed:</strong> {analysis["total_files"]}</p>
        <p><strong>Test Contexts:</strong> {", ".join(analysis["contexts"])}</p>
    </div>

    <div class="summary">
        <h2>Coverage by Context</h2>"""

    for context, data in analysis["coverage_by_context"].items():
        html_content += f"""
        <div class="context">
            <span class="context-badge {context}">{context}</span>
            Files: {data["files_covered"]}, Lines: {data["total_lines"]}
        </div>"""

    html_content += """
    </div>

    <h2>File Coverage Analysis</h2>
    <table class="file-table">
        <thead>
            <tr>
                <th>File</th>"""

    for context in analysis["contexts"]:
        html_content += f"<th>{context.title()}</th>"

    html_content += """
                <th>Coverage Status</th>
            </tr>
        </thead>
        <tbody>"""

    for file_path, file_data in analysis["files"].items():
        html_content += f"""
            <tr>
                <td>{html.escape(file_path)}</td>"""

        for context in analysis["contexts"]:
            if context in file_data["covered_by"]:
                lines = file_data["line_coverage"].get(context, 0)
                html_content += f'<td class="covered">✓ ({lines} lines)</td>'
            else:
                html_content += '<td class="not-covered">✗</td>'

        # Determine coverage status
        covered_by_count = len(file_data["covered_by"])
        if covered_by_count == 0:
            status = "No Coverage"
            status_class = "not-covered"
        elif covered_by_count == 1:
            status = f"Only {file_data['covered_by'][0]}"
            status_class = "partial"
        else:
            status = "Multiple Contexts"
            status_class = "covered"

        html_content += f'<td class="{status_class}">{status}</td>'
        html_content += "</tr>"

    html_content += """
        </tbody>
    </table>

    <div class="summary">
        <h2>Recommendations</h2>
        <ul>
            <li><strong>Files with only integration coverage:</strong> Consider adding unit tests for better isolation</li>
            <li><strong>Files with only unit coverage:</strong> Consider adding integration tests for real-world validation</li>
            <li><strong>Files with no coverage:</strong> High priority for test coverage improvement</li>
        </ul>
    </div>

    <footer style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; color: #666;">
        <p>Generated by KireMisu Coverage Comparison Tool</p>
    </footer>
</body>
</html>"""

    with open(os.path.join(output_dir, "index.html"), "w") as f:
        f.write(html_content)


def main():
    """Main function to generate coverage comparison report."""
    print("KireMisu Coverage Comparison Tool")
    print("=" * 40)

    # Check if we're in the right directory
    if not os.path.exists("pyproject.toml"):
        print("Error: Must be run from the project root directory")
        sys.exit(1)

    # Get available coverage files
    coverage_files = get_coverage_files()
    if not coverage_files:
        print("\nNo coverage files found. Please run coverage tests first:")
        print("\nAvailable commands:")
        print("  make test-coverage-unit       # Generate unit test coverage")
        print("  make test-coverage-integration # Generate integration test coverage")
        print("  make test-coverage-api        # Generate API test coverage")
        print("  make test-coverage-security   # Generate security test coverage")
        print("  make test-coverage-all        # Generate combined coverage")
        print("\nThen run: make test-coverage-compare")
        sys.exit(1)

    print(f"Found coverage data for contexts: {', '.join(coverage_files)}")

    # Validate that we have actual coverage data
    total_coverage_files = 0
    for context in coverage_files:
        data = load_coverage_data(context)
        if data:
            total_coverage_files += 1
        else:
            print(f"Warning: No coverage data found for context '{context}'")
            print(f"Run: make test-coverage-{context}")

    if total_coverage_files == 0:
        print("\nError: No valid coverage data found in any context.")
        print("Please run the coverage commands listed above first.")
        sys.exit(1)

    # Analyze coverage
    analysis = analyze_coverage_overlap(coverage_files)

    # Validate analysis results
    if analysis["total_files"] == 0:
        print("\nWarning: No files found in coverage analysis.")
        print("This may indicate an issue with coverage data collection.")

    # Generate HTML report
    output_dir = "htmlcov/comparison"
    generate_html_report(analysis, output_dir)

    print(f"\\nComparison report generated: {output_dir}/index.html")
    print("\\nSummary:")
    print(f"  Total files analyzed: {analysis['total_files']}")

    for context, data in analysis["coverage_by_context"].items():
        print(f"  {context}: {data['files_covered']} files, {data['total_lines']} lines")

    # Find files with unique coverage
    unique_to_unit = 0
    unique_to_integration = 0
    no_coverage = 0

    for file_data in analysis["files"].values():
        covered_by = set(file_data["covered_by"])
        if len(covered_by) == 0:
            no_coverage += 1
        elif covered_by == {"unit"}:
            unique_to_unit += 1
        elif covered_by == {"integration"}:
            unique_to_integration += 1

    print("\\nCoverage Analysis:")
    if unique_to_unit > 0:
        print(f"  Files only covered by unit tests: {unique_to_unit}")
    if unique_to_integration > 0:
        print(f"  Files only covered by integration tests: {unique_to_integration}")
    if no_coverage > 0:
        print(f"  Files with no coverage: {no_coverage}")

    print(f"\\nOpen {output_dir}/index.html in your browser to view the detailed report.")


if __name__ == "__main__":
    main()
