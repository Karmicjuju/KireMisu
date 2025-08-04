#!/usr/bin/env python3
"""
Coverage Comparison Script for KireMisu

This script analyzes coverage reports from different test suites and generates
a comprehensive comparison showing:
- Which lines are covered by unit vs integration tests
- Coverage gaps that only integration tests fill
- Redundant coverage areas
- Overall coverage statistics by test type
"""
import json
import os
import sys
from pathlib import Path
from typing import Dict, Set, List, Optional
import coverage


def load_coverage_data(context: str) -> Optional[coverage.CoverageData]:
    """Load coverage data for a specific context."""
    coverage_file = Path(".coverage")
    if not coverage_file.exists():
        return None
    
    try:
        cov_data = coverage.CoverageData()
        cov_data.read_file(str(coverage_file))
        return cov_data
    except Exception as e:
        print(f"Error loading coverage data for {context}: {e}")
        return None


def analyze_coverage_overlap(contexts: List[str]) -> Dict:
    """Analyze coverage overlap between different test contexts."""
    coverage_by_context = {}
    all_files = set()
    
    # Load coverage data for each context
    for context in contexts:
        # Try to find coverage file for this context
        coverage_file = Path(f".coverage.{context}")
        if not coverage_file.exists():
            # Fallback to main coverage file if context-specific doesn't exist
            coverage_file = Path(".coverage")
            
        if coverage_file.exists():
            try:
                cov_data = coverage.CoverageData()
                cov_data.read_file(str(coverage_file))
                
                files = cov_data.measured_files()
                coverage_by_context[context] = {}
                
                for file_path in files:
                    # Get line coverage for this file
                    lines = cov_data.lines(file_path)
                    if lines:
                        coverage_by_context[context][file_path] = set(lines)
                        all_files.add(file_path)
                        
            except Exception as e:
                print(f"Warning: Could not load coverage for {context}: {e}")
                coverage_by_context[context] = {}
    
    # Analyze overlaps
    analysis = {
        "contexts": contexts,
        "total_files": len(all_files),
        "coverage_by_context": {},
        "overlaps": {},
        "unique_coverage": {},
        "summary": {}
    }
    
    # Calculate coverage statistics for each context
    for context in contexts:
        if context in coverage_by_context:
            context_data = coverage_by_context[context]
            total_lines = sum(len(lines) for lines in context_data.values())
            analysis["coverage_by_context"][context] = {
                "files_covered": len(context_data),
                "total_lines": total_lines,
                "files": list(context_data.keys())
            }
        else:
            analysis["coverage_by_context"][context] = {
                "files_covered": 0,
                "total_lines": 0,
                "files": []
            }
    
    # Find overlaps between contexts
    context_pairs = [(contexts[i], contexts[j]) 
                    for i in range(len(contexts)) 
                    for j in range(i+1, len(contexts))]
    
    for ctx1, ctx2 in context_pairs:
        if ctx1 in coverage_by_context and ctx2 in coverage_by_context:
            overlap_key = f"{ctx1}_vs_{ctx2}"
            common_files = (set(coverage_by_context[ctx1].keys()) & 
                          set(coverage_by_context[ctx2].keys()))
            
            overlap_lines = 0
            unique_ctx1 = 0
            unique_ctx2 = 0
            
            for file_path in all_files:
                lines1 = coverage_by_context[ctx1].get(file_path, set())
                lines2 = coverage_by_context[ctx2].get(file_path, set())
                
                overlap_lines += len(lines1 & lines2)
                unique_ctx1 += len(lines1 - lines2)
                unique_ctx2 += len(lines2 - lines1)
            
            analysis["overlaps"][overlap_key] = {
                "common_files": len(common_files),
                "overlapping_lines": overlap_lines,
                "unique_to_first": unique_ctx1,
                "unique_to_second": unique_ctx2
            }
    
    # Calculate unique coverage for each context
    for context in contexts:
        if context in coverage_by_context:
            other_contexts = [c for c in contexts if c != context and c in coverage_by_context]
            unique_lines = 0
            
            for file_path in all_files:
                context_lines = coverage_by_context[context].get(file_path, set())
                other_lines = set()
                
                for other_ctx in other_contexts:
                    other_lines.update(coverage_by_context[other_ctx].get(file_path, set()))
                
                unique_lines += len(context_lines - other_lines)
            
            analysis["unique_coverage"][context] = unique_lines
    
    return analysis


def generate_html_report(analysis: Dict, output_dir: Path) -> None:
    """Generate an HTML report from the coverage analysis."""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>KireMisu Coverage Comparison Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background-color: #f0f0f0; padding: 20px; border-radius: 5px; }}
        .section {{ margin: 20px 0; }}
        .context-stats {{ display: flex; flex-wrap: wrap; gap: 20px; }}
        .stat-card {{ 
            border: 1px solid #ddd; 
            padding: 15px; 
            border-radius: 5px; 
            min-width: 200px;
            background-color: #f9f9f9;
        }}
        .overlap-section {{ margin: 20px 0; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        .high-overlap {{ background-color: #ffeeee; }}
        .low-overlap {{ background-color: #eeffee; }}
        code {{ background-color: #f5f5f5; padding: 2px 4px; border-radius: 3px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🧪 KireMisu Coverage Comparison Report</h1>
        <p>Generated on {analysis.get('timestamp', 'unknown')}</p>
        <p>Analyzing coverage across test suites: <code>{', '.join(analysis['contexts'])}</code></p>
    </div>
    
    <div class="section">
        <h2>📊 Coverage by Test Suite</h2>
        <div class="context-stats">
"""
    
    for context, stats in analysis["coverage_by_context"].items():
        html_content += f"""
            <div class="stat-card">
                <h3>{context.title()}</h3>
                <p><strong>Files Covered:</strong> {stats['files_covered']}</p>
                <p><strong>Total Lines:</strong> {stats['total_lines']}</p>
            </div>
"""
    
    html_content += """
        </div>
    </div>
    
    <div class="section">
        <h2>🔗 Coverage Overlaps</h2>
        <table>
            <tr>
                <th>Comparison</th>
                <th>Common Files</th>
                <th>Overlapping Lines</th>
                <th>Unique to First</th>
                <th>Unique to Second</th>
            </tr>
"""
    
    for overlap_key, overlap_data in analysis["overlaps"].items():
        ctx1, ctx2 = overlap_key.split("_vs_")
        html_content += f"""
            <tr>
                <td><code>{ctx1}</code> vs <code>{ctx2}</code></td>
                <td>{overlap_data['common_files']}</td>
                <td>{overlap_data['overlapping_lines']}</td>
                <td>{overlap_data['unique_to_first']}</td>
                <td>{overlap_data['unique_to_second']}</td>
            </tr>
"""
    
    html_content += """
        </table>
    </div>
    
    <div class="section">
        <h2>🎯 Unique Coverage</h2>
        <p>Lines covered exclusively by each test suite:</p>
        <div class="context-stats">
"""
    
    for context, unique_lines in analysis["unique_coverage"].items():
        html_content += f"""
            <div class="stat-card">
                <h3>{context.title()}</h3>
                <p><strong>Unique Lines:</strong> {unique_lines}</p>
            </div>
"""
    
    html_content += """
        </div>
    </div>
    
    <div class="section">
        <h2>💡 Insights & Recommendations</h2>
        <ul>
            <li><strong>High Unit Coverage:</strong> Indicates good isolated testing practices</li>
            <li><strong>Integration-Only Coverage:</strong> May indicate brittle tests - consider adding unit tests</li>
            <li><strong>API-Only Coverage:</strong> Endpoint-specific logic that should have focused unit tests</li>
            <li><strong>Security Test Coverage:</strong> Critical paths that need dedicated security validation</li>
        </ul>
    </div>
    
    <div class="section">
        <h2>🛠️ Usage</h2>
        <p>To regenerate this report:</p>
        <pre><code>./scripts/dev.sh test-coverage-compare</code></pre>
        
        <p>To run specific test suites:</p>
        <pre><code>./scripts/dev.sh test-coverage-unit
./scripts/dev.sh test-coverage-integration
./scripts/dev.sh test-coverage-api
./scripts/dev.sh test-coverage-security</code></pre>
    </div>
    
    <footer style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; color: #666;">
        <p>Generated by KireMisu Coverage Comparison Tool</p>
    </footer>
</body>
</html>
"""
    
    # Write the HTML report
    report_file = output_dir / "index.html"
    with open(report_file, "w") as f:
        f.write(html_content)
    
    print(f"✅ Coverage comparison report generated: {report_file}")


def main():
    """Main function to run coverage comparison."""
    # Define the contexts to analyze
    contexts = ["unit", "integration", "api", "security", "combined"]
    
    print("🔍 Analyzing coverage data...")
    
    # Add timestamp to analysis
    from datetime import datetime
    analysis = analyze_coverage_overlap(contexts)
    analysis["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Generate HTML report
    output_dir = Path("htmlcov/comparison")
    generate_html_report(analysis, output_dir)
    
    # Print summary to console
    print("\\n📊 Coverage Summary:")
    for context, stats in analysis["coverage_by_context"].items():
        print(f"  {context:12}: {stats['total_lines']:6} lines in {stats['files_covered']:3} files")
    
    print("\\n🔗 Unique Coverage:")
    for context, unique_lines in analysis["unique_coverage"].items():
        print(f"  {context:12}: {unique_lines:6} unique lines")
    
    print(f"\\n📄 Full report: htmlcov/comparison/index.html")


if __name__ == "__main__":
    main()